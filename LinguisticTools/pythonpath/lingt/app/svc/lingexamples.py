# -*- coding: Latin-1 -*-
#
# This file created Sept 14 2010 by Jim Kornelsen
#
# 02-Oct-10 JDK  Raise exception instead of returning an interrupt arg.
# 26-Oct-10 JDK  Optionally disable Comparison doc.
# 25-Oct-12 JDK  Use FileItemList class to load file items from user vars.
# 27-Apr-13 JDK  Remove testing functions.
# 05-Jul-13 JDK  Option to use Flex citation field for phonemic.
# 13-Jul-15 JDK  Refactor LingEx into three smaller classes.
# 14-Sep-15 JDK  Add module constants for example type.
# 14-Dec-15 JDK  Show suggestions when no ref number specified.

"""
Grab phonology or grammar examples and insert them.

This module exports:
    ExServices
    EXTYPE_PHONOLOGY
    EXTYPE_GRAMMAR
"""
import logging

from lingt.access.writer import outputmanager
from lingt.access.writer import search
from lingt.access.writer import styles
from lingt.access.writer.ex_updater import ExUpdater
from lingt.access.writer.uservars import Prefix, UserVars
from lingt.access.xml.interlin_reader import InterlinReader
from lingt.access.xml.phon_reader import PhonReader
from lingt.app import exceptions
from lingt.app.data import fileitemlist
from lingt.app.data import lingex_structs
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.app.lingexamples")

#  type of linguistic example
EXTYPE_PHONOLOGY = 'phonology'
EXTYPE_GRAMMAR = 'grammar'

class ExServices:
    """Services that can conveniently be called from other modules."""

    def __init__(self, exType, unoObjs):
        self.exType = exType
        self.unoObjs = unoObjs
        if self.exType == EXTYPE_PHONOLOGY:
            USERVAR_PREFIX = Prefix.PHONOLOGY
        else:
            USERVAR_PREFIX = Prefix.GRAMMAR
        self.userVars = UserVars(
            USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.settings = ExSettings(self.exType, self.unoObjs, self.userVars)
        self.operations = ExOperations(
            self.exType, self.unoObjs, self.userVars, self.settings)
        self.replacingRefs = True  # find and replace ref numbers
        logger.debug("ExGrabber init() finished")

    def insertByRefnum(self, refTextRough):
        try:
            self.operations.readData()
            if not refTextRough.strip():
                raise exceptions.ChoiceProblem(
                    *self.operations.messageAndSuggestions(
                        "Please enter a ref number."))
            logger.debug("do the insertion.")
            self.operations.insertEx(refTextRough, False, False)
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)

    def setUpdateExamples(self, newVal):
        self.replacingRefs = not newVal

    def isUpdatingExamples(self):
        return not self.replacingRefs

    def findNext(self, searchFromBeginning):
        """Returns true if a ref number is found."""
        logger.debug("findNext(%s)", searchFromBeginning)
        oldFoundString = self.operations.getFoundString()
        newFoundString = self.operations.doSearch(
            self.replacingRefs, searchFromBeginning)
        if oldFoundString and not newFoundString:
            return bool(oldFoundString)
        return bool(newFoundString)

    def replace(self, searchFromBeginning):
        """Returns True if another ref number is found after replacing."""
        logger.debug(util.funcName('begin'))
        if (self.exType == EXTYPE_GRAMMAR and self.isUpdatingExamples() and
                not self.settings.getOutconfig().makeOuterTable):
            self.msgbox.display(
                "To update examples, 'Outer table' must be "
                "marked in Grammar Settings.")
            return False
        if not self.operations.getFoundString():
            return self.findNext(searchFromBeginning)
        refnumFound = self.operations.getFoundString()
        try:
            self.operations.readData()
            if self.replacingRefs:
                self.operations.insertEx(refnumFound, True, False)
            else:
                self.operations.updateEx(refnumFound)
            self.operations.doSearch(self.replacingRefs, False)
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)
        return bool(self.operations.getFoundString())

    def replaceAll(self):
        """Replace all #ref no's or update all existing examples."""
        if (self.exType == EXTYPE_GRAMMAR and self.isUpdatingExamples() and
                not self.settings.getOutconfig().makeOuterTable):
            self.msgbox.display(
                "To update examples, 'Outer table' must be "
                "marked in Grammar Settings.")
            return
        try:
            self.operations.readData()
            repeater = ExRepeater(
                self.msgbox, self.settings, self.operations,
                self.replacingRefs)
            repeater.replaceAll()
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)

    def addExampleNumbers(self):
        self.operations.addExampleNumbers()


class ExRepeater:
    """For replacing or updating all."""

    def __init__(self, msgbox, settings, operations, replacingRefs):
        self.msgbox = msgbox
        self.settings = settings
        self.operations = operations
        self.replacingRefs = replacingRefs
        self.prevRefUpdated = ""
        self.repeatedCount = 0
        self.replacementsCount = 0
        self.messagesDisplayed = []  # don't keep displaying for updating all

    def replaceAll(self):
        startFromBeginning = True
        self.prevRefUpdated = ""
        self.repeatedCount = 0
        self.replacementsCount = 0
        while True:
            self.operations.doSearch(
                self.replacingRefs, startFromBeginning, True)
            refnumFound = self.operations.getFoundString()
            if not refnumFound:
                break
            startFromBeginning = False
            try:
                self.replaceAndAsk(refnumFound)
            except exceptions.UserInterrupt:
                break
            except exceptions.MessageError as exc:
                if exc.msg not in self.messagesDisplayed:
                    self.messagesDisplayed.append(exc.msg)
                    if not self.msgbox.displayOkCancel(exc.msg, *exc.msg_args):
                        # User pressed Cancel
                        break
        plural = "" if self.replacementsCount == 1 else "s"
        if self.replacingRefs:
            self.msgbox.display(
                "Replaced %d example%s.", self.replacementsCount, plural)
        else:
            self.msgbox.display(
                "Updated %d example%s.", self.replacementsCount, plural)

    def replaceAndAsk(self, refnumFound):
        if self.replacingRefs:
            self.operations.insertEx(refnumFound, True, False)
            self.replacementsCount += 1
        else:
            self.operations.updateEx(refnumFound)
            self.replacementsCount += 1
            if refnumFound == self.prevRefUpdated:
                self.askInterrupt(refnumFound)
            else:
                self.prevRefUpdated = refnumFound
                self.repeatedCount = 1

    def askInterrupt(self, refnumFound):
        """
        Updated the same number twice.  It might be an infinite loop.
        """
        logger.debug("Repeated ex %d times", self.repeatedCount)
        self.repeatedCount += 1
        MAX_REPETITIONS = 5
        dummy_div, mod = divmod(self.repeatedCount, MAX_REPETITIONS)
        if self.repeatedCount > 0 and mod == 0:
            refnumDisplay = refnumFound.strip()
            if not self.msgbox.displayOkCancel(
                    "Updated '%s' %d times in a row.  Keep going?",
                    refnumDisplay, self.repeatedCount):
                raise exceptions.UserInterrupt()


class ExOperations:
    """
    Core operations for this module.
    Calls the Access layer for input and output.
    """
    def __init__(self, exType, unoObjs, userVars, settings):
        self.exType = exType
        self.unoObjs = unoObjs
        self.userVars = userVars
        self.settings = settings
        self.search = search.ExampleSearch(unoObjs)
        self.interlinManager = None
        if self.exType == EXTYPE_PHONOLOGY:
            self.outputManager = outputmanager.PhonMgr(
                unoObjs, self.settings.getStyles())
        else:
            self.interlinManager = outputmanager.InterlinMgr(
                unoObjs, self.settings.getStyles())
            self.outputManager = self.interlinManager
        self.exUpdater = ExUpdater(
            unoObjs, self.outputManager, self.userVars.VAR_PREFIX)
        self.msgbox = MessageBox(unoObjs)
        self.examplesDict = None
        self.suggestions = []

    def addExampleNumbers(self):
        if self.interlinManager:
            self.interlinManager.addExampleNumbers()

    def doSearch(self, replacingRefs, startFromBeginning, findingAll=False):
        if replacingRefs:
            self.search.findRefNumber(startFromBeginning, findingAll)
        else:
            self.search.findRefCharStyle(
                self.settings.getStyles().getNames()['ref'],
                startFromBeginning, findingAll)
        return self.getFoundString()

    def getFoundString(self):
        return self.search.getFoundString()

    def readData(self):
        """
        Read examples from data files.
        """
        if self.examplesDict is None:
            logger.debug("Getting examples dict")
            if self.exType == EXTYPE_PHONOLOGY:
                fileReader = PhonReader(
                    self.unoObjs, self.userVars, self.settings.getInconfig())
            else:
                fileReader = InterlinReader(
                    self.unoObjs, self.userVars, self.settings.getInconfig())
            self.examplesDict = fileReader.read()
            self.suggestions = fileReader.getSuggestions()

    def insertEx(self, refTextRough, deleteRefNum, updatingEx):
        """Set updatingEx to True if updating the example."""
        logger.debug(util.funcName('begin', args=refTextRough))
        logger.debug("%d examples", len(self.examplesDict))
        refnum = refTextRough.strip()
        if refnum.startswith("#"):
            refnum = refnum[1:]  # keep all but first character

        ## Select the specified ref number

        refnum_key = refnum.lower()  # case insensitive
        if refnum_key in self.examplesDict:
            logger.debug(
                "Inserting '%s'", self.examplesDict[refnum_key].refText)

            ## Display the data in the Writer doc

            if updatingEx:
                self.exUpdater.gotoAfterEx()
            self.outputManager.setConfig(self.settings.getOutconfig())
            self.outputManager.outputExample(
                self.examplesDict[refnum_key], deleteRefNum, updatingEx)
        else:
            raise exceptions.DataNotFoundError(
                *self.messageAndSuggestions(
                    "Could not find ref number %s", [refnum]))

    def messageAndSuggestions(self, message, msg_args=None):
        """
        Append suggestion ref numbers to a message.

        :param message: the main part of the message
        :param msg_args: array of arguments needed for main part
        :returns: the message string and its argument array
        """
        if msg_args is None:
            msg_args = []
        suggNum = 0
        MAX_SUGGESTIONS = 3
        if len(self.suggestions) > 0:
            message += "\n\nSuggestions\n%s"
            suggString = ""
            for suggestion in self.suggestions:
                suggNum += 1
                if suggNum > MAX_SUGGESTIONS:
                    break
                suggString += "\t%s\n" % suggestion
            msg_args.append(suggString)
        return [message] + msg_args

    def updateEx(self, refTextRough):
        """
        This method gets called after a ref number to update has been selected
        in the document.  The order of the next few steps is as follows:
        1. Call gotoAfterEx() to move out of the table.
        2. Insert the new example without the example number.
        3. Call moveExNumber().
        Steps 1 and 2 are done in insertEx().
        """
        logger.debug(util.funcName('begin'))
        if self.exType == EXTYPE_GRAMMAR:
            if not self.search.refInTable():
                raise exceptions.RangeError(
                    "Found a ref number, but it must be in an outer "
                    "table in order to be updated.")
        self.insertEx(refTextRough, False, True)
        if self.exType == EXTYPE_GRAMMAR:
            if not self.settings.showCompDoc():
                self.exUpdater.doNotMakeCompDoc()
            self.exUpdater.moveExNumber()
            self.exUpdater.moveExamplesToNewDoc()
        else:
            self.exUpdater.deleteOldPhonEx()


class ExSettings:
    """
    Phonology or grammar settings from user vars.  Loads on demand.
    """
    def __init__(self, exType, unoObjs, userVars):
        self.exType = exType
        self.unoObjs = unoObjs
        self.userVars = userVars
        self.msgbox = MessageBox(unoObjs)
        self.styles = None
        self.inSettings = None
        self.outSettings = None
        self.showComparisonDoc = None
        self.fileList = []

    def getStyles(self):
        if not self.styles:
            if self.exType == EXTYPE_PHONOLOGY:
                self.styles = styles.PhonologyStyles(
                    self.unoObjs, self.userVars)
            else:
                self.styles = styles.GrammarStyles(
                    self.unoObjs, self.userVars)
        return self.styles

    def getInconfig(self):
        self._loadSettings()
        return self.inSettings

    def getOutconfig(self):
        self._loadSettings()
        return self.outSettings

    def showCompDoc(self):
        if self.showComparisonDoc is None:
            self.showComparisonDoc = True
            varname = "ComparisonDoc"
            if not self.userVars.isEmpty(varname):
                if self.userVars.getInt(varname) == 0:
                    self.showComparisonDoc = False
        return self.showComparisonDoc

    def _loadSettings(self):
        if self.outSettings:
            return
        if self.exType == EXTYPE_PHONOLOGY:
            self._getPhonologySettings()
        else:
            self._getGrammarSettings()

    def _getPhonologySettings(self):
        """Get file paths, style names, and other options that were
        set in the Phonology Settings dialog.
        """
        logger.debug(util.funcName('begin'))
        self.inSettings = lingex_structs.PhonInputSettings(self.userVars)
        self.inSettings.loadUserVars()
        self.outSettings = lingex_structs.PhonOutputSettings(self.userVars)
        self.outSettings.loadUserVars()
        logger.debug(util.funcName('end'))

    def _getGrammarSettings(self):
        """Get file paths, style names, and other options from user vars."""
        logger.debug(util.funcName('begin'))
        self.outSettings = lingex_structs.InterlinOutputSettings(self.userVars)
        self.outSettings.loadUserVars()
        self.inSettings = fileitemlist.InterlinInputSettings(self.userVars)
        self.inSettings.loadUserVars()
        self.inSettings.loadOutputSettings(self.outSettings)
        logger.debug("Using %d file(s).", len(self.inSettings.fileList))
        logger.debug(util.funcName('end'))

