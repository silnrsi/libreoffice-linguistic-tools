"""
Grab phonology or interlinear examples and insert them.

This module exports:
    ExServices
    EXTYPE_PHONOLOGY
    EXTYPE_INTERLINEAR
"""
import logging
import re

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
EXTYPE_INTERLINEAR = 'interlinear'

def natural_sort(l):
    """Sort a list oF strings in natural sort order,
    for example "1.2" before "1.10".
    """
    def convert(text):
        """Convert text to integer if it is a digit, otherwise to lowercase."""
        if text.isdigit():
            return int(text)
        return text.lower()

    def alphanum_key(key):
        """Split the key into alphanumeric components,
        converting digits to integers and other parts to lowercase."""
        parts = re.split('([0-9]+)', key)
        return [convert(c) for c in parts]

    return sorted(l, key=alphanum_key)

class ExServices:
    """Services that can conveniently be called from other modules."""

    def __init__(self, exType, unoObjs):
        self.exType = exType
        self.unoObjs = unoObjs
        if self.exType == EXTYPE_PHONOLOGY:
            USERVAR_PREFIX = Prefix.PHONOLOGY
        else:
            USERVAR_PREFIX = Prefix.INTERLINEAR
        self.userVars = UserVars(
            USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.settings = ExSettings(self.exType, self.unoObjs, self.userVars)
        self.operations = ExOperations(
            self.exType, self.unoObjs, self.userVars, self.settings)
        self.replacingRefs = True  # find and replace ref numbers
        logger.debug("ExGrabber init() finished")

    def verifyRefnums(self):
        """Raises an exception if there are duplicates or no ref nums found."""
        try:
            self.operations.readData(force_read=True)
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)
            raise exceptions.DataNotFoundError("No data found.")
        if self.operations.duplicate_refnums:
            MAX_NUMS_IN_MESSAGE = 5
            refnums = natural_sort(self.operations.duplicate_refnums)
            refnumsString = ", ".join(refnums[:MAX_NUMS_IN_MESSAGE])
            additionalRefs = len(refnums) - MAX_NUMS_IN_MESSAGE
            if additionalRefs > 0:
                refnumsString += ", ...%d more." % additionalRefs
            message = exceptions.interpolate_message(
                "The following Ref Numbers have duplicates: %s", refnumsString)
            if self.exType == EXTYPE_INTERLINEAR:
                message += exceptions.interpolate_message(
                    "\n\nEither change the numbers or, if they are in "
                    "different texts, add a prefix for each text.\n"
                    "Press OK to use these settings anyway.")
            raise exceptions.DataInconsistentError(message)

    def getAllRefnums(self):
        """Returns an iterable of all ref numbers in the data.
        Items are in the order that they were read from the file.
        """
        try:
            self.operations.readData()
            return natural_sort(
                [ex.refText for ex in self.operations.examplesDict.values()])
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)
            raise exceptions.DataNotFoundError("No data found.")

    def insertByRefnum(self, refTextRough):
        try:
            self.operations.readData()
            if not refTextRough.strip():
                message = exceptions.interpolate_message(
                    "Please enter a ref number.")
                raise exceptions.ChoiceProblem(
                    self.operations.appendSuggestions(message))
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
        if (self.exType == EXTYPE_INTERLINEAR and self.isUpdatingExamples() and
                not self.settings.getOutconfig().makeOuterTable):
            self.msgbox.display(
                "To update examples, 'Outer table' must be "
                "marked in Interlinear Settings.")
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
        if (self.exType == EXTYPE_INTERLINEAR and self.isUpdatingExamples() and
                not self.settings.getOutconfig().makeOuterTable):
            self.msgbox.display(
                "To update examples, 'Outer table' must be "
                "marked in Interlinear Settings.")
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
        """Updated the same number twice.  It might be an infinite loop."""
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
    """Core operations for this module.
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
        self.duplicate_refnums = []

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

    def readData(self, force_read=False):
        """Read examples from data files."""
        if force_read:
            self.examplesDict = None
            self.settings.reset()
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
            self.duplicate_refnums = fileReader.getDuplicateRefNumbers()

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
            message = exceptions.interpolate_message(
                "Could not find ref number %s", [refnum])
            raise exceptions.DataNotFoundError(
                self.appendSuggestions(message))

    def appendSuggestions(self, message):
        """Append suggestion ref numbers to a message.

        :param message: the main part of the message
        :returns: the localized message string with suggestions added
        """
        if not self.suggestions:
            return message
        suggNum = 0
        suggString = ""
        MAX_SUGGESTIONS = 3
        for suggestion in self.suggestions:
            suggNum += 1
            if suggNum > MAX_SUGGESTIONS:
                break
            suggString += "\t%s\n" % suggestion
        suggestion_message = exceptions.interpolate_message(
            "\n\nSuggestions\n%s", [suggString])
        return message + suggestion_message

    def updateEx(self, refTextRough):
        """This method gets called after a ref number to update has been
        selected in the document.  The order of the next few steps is:
        1. Call gotoAfterEx() to move out of the table.
        2. Insert the new example without the example number.
        3. Call moveExNumber().
        Steps 1 and 2 are done in insertEx().
        """
        logger.debug(util.funcName('begin'))
        if self.exType == EXTYPE_INTERLINEAR:
            if not self.search.refInTable():
                raise exceptions.RangeError(
                    "Found a ref number, but it must be in an outer "
                    "table in order to be updated.")
        self.insertEx(refTextRough, False, True)
        if self.exType == EXTYPE_INTERLINEAR:
            if not self.settings.showCompDoc():
                self.exUpdater.doNotMakeCompDoc()
            self.exUpdater.moveExNumber()
            self.exUpdater.moveExamplesToNewDoc()
        else:
            self.exUpdater.deleteOldPhonEx()


class ExSettings:
    """Phonology or interlinear settings from user vars.  Loads on demand."""
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
                self.styles = styles.InterlinStyles(
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

    def reset(self):
        """Call this to allow settings to be reloaded."""
        self.inSettings = None
        self.outSettings = None

    def _loadSettings(self):
        if self.outSettings:
            return
        if self.exType == EXTYPE_PHONOLOGY:
            self._getPhonologySettings()
        else:
            self._getInterlinSettings()

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

    def _getInterlinSettings(self):
        """Get file paths, style names, and other options from user vars."""
        logger.debug(util.funcName('begin'))
        self.outSettings = lingex_structs.InterlinOutputSettings(self.userVars)
        self.outSettings.loadUserVars()
        self.inSettings = fileitemlist.InterlinInputSettings(self.userVars)
        self.inSettings.loadUserVars()
        self.inSettings.loadOutputSettings(self.outSettings)
        logger.debug("Using %d file(s).", len(self.inSettings.fileList))
        logger.debug(util.funcName('end'))
