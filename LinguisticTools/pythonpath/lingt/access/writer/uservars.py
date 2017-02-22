# -*- coding: Latin-1 -*-
#
# This file created Oct 23 2012 by Jim Kornelsen
#
# 29-Oct-12 JDK  Return 0.0 from getFloat() to make return types consistent.
# 15-Nov-12 JDK  Add methods for calc docs to use writer settings.
# 19-Nov-12 JDK  Remove punctuation from var names.
# 19-Dec-12 JDK  getUserVarDoc returns the new unoObjs instead of mod by ref.
# 30-Jan-13 JDK  getUserVarDoc does not open a new writer doc.
# 20-Mar-13 JDK  Move package level methods inside new classes.
# 29-Mar-13 JDK  Separate into a new method setHasSettings.
# 11-May-13 JDK  Add content to document even if not entirely empty.
# 07-Jul-15 JDK  Remove getFloat() as it is only needed in util.fontsize.
# 13-Jul-15 JDK  Added FieldTags.
# 14-Jul-15 JDK  Rename set() to setv() to avoid shadowing builtin.
# 15-Jul-15 JDK  Remove ConfigOptions class.
# 10-Aug-15 JDK  Use generator to enumerate UNO collections.
# 18-Aug-15 JDK  Don't call FieldTags.loadNames() from constructor.
# 27-Aug-15 JDK  Added Syncable.cleanupUserVars().
# 08-Oct-15 JDK  Removed UNO imports.
# 23-Mar-16 JDK  Added Prefix class.
# 29-Jul-16 JDK  Documents with one long line are not considered empty.
# 17-Feb-17 JDK  Word Line 1 and 2 instead of Orthographic and Text.

"""
Store persistent settings in user variables of a Writer document.

Note that this cannot be done in the same way in Calc.
So for Calc we open a minimized Writer document to store settings.

User variables can be edited manually from within Writer by
going to Insert -> Field -> More Fields,
then choosing User Field under the Variables tab.
"""
import logging
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK

from lingt.access.common import iteruno
from lingt.app import exceptions
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.access.uservars")


class Prefix:
    """For each module, we use a prefix to the user variable name.
    LT is short for Linguistic Tools.
    """
    PHONOLOGY = "LTp_"
    GRAMMAR = "LTg_"
    ABBREVIATIONS = "LTa_"
    DATA_CONVERSION = "LTc_"
    BULK_CONVERSION = "LTbc_"
    WORD_LIST = "LTw_"
    SPELLING = "LTsp_"
    SCRIPT_PRACTICE = "LTscr_"


class UserVars:
    """Access to the user variables of the Writer document.
    These can be viewed using Insert -> Field -> More Fields.
    """
    def __init__(self, VAR_PREFIX, writer_document, otherLogger):
        """
        :param VAR_PREFIX: member of the Prefix class
        :param writer_document: The UNO document object, not available for
                                Calc.
        :param logger: Logger of the module that is using this class.
        """
        self.VAR_PREFIX = VAR_PREFIX
        self.document = writer_document
        self.otherLogger = otherLogger

    def store(self, baseVarName, stringVal):
        """
        Stores a value in a Writer doc that is persistent across macro calls.
        """
        varName = self.getVarName(baseVarName)
        self.otherLogger.debug("storeUserVar %s", varName)
        if stringVal is None:
            stringVal = ""
        fieldMasters = self.document.getTextFieldMasters()
        fieldName = "com.sun.star.text.FieldMaster.User." + varName
        if fieldMasters.hasByName(fieldName):
            field = fieldMasters.getByName(fieldName)
            field.setPropertyValue("Content", stringVal)
        else:
            xMaster = self.document.createInstance(
                "com.sun.star.text.fieldmaster.User")
            xMaster.Name = varName
            xMaster.Content = stringVal
            xUserField = self.document.createInstance(
                "com.sun.star.text.textfield.User")
            xUserField.attachTextFieldMaster(xMaster)

    def get(self, baseVarName):
        """Returns the value of a user variable as a string"""
        varName = self.getVarName(baseVarName)
        self.otherLogger.debug("getUserVar %s", varName)
        fieldMasters = self.document.getTextFieldMasters()
        fieldName = "com.sun.star.text.FieldMaster.User." + varName
        if fieldMasters.hasByName(fieldName):
            field = fieldMasters.getByName(fieldName)
            stringVal = field.getPropertyValue("Content")
            return stringVal
        else:
            return ""

    def getVarName(self, baseVarName):
        """Punctuation shouldn't be used in names, because Writer doesn't
        always handle it correctly.
        """
        varName = baseVarName.replace("?", "")
        return self.VAR_PREFIX + varName

    def getInt(self, varName):
        """Returns the value of a user variable as an integer.
        If string is empty or not numeric, returns 0.
        """
        val = self.get(varName)
        try:
            return int(val)
        except ValueError:
            # raised for strings like "" and "5a"
            return 0

    def isEmpty(self, varName):
        """Returns True if string is empty, otherwise False."""
        val = self.get(varName)
        return val == ""

    def delete(self, varName):
        """Deletes a user variable if it exists.
        Returns True if a variable was deleted.
        """
        varName = self.VAR_PREFIX + varName
        self.otherLogger.debug("delUserVar %s", varName)
        fieldMasters = self.document.getTextFieldMasters()
        fieldName = "com.sun.star.text.FieldMaster.User." + varName
        if fieldMasters.hasByName(fieldName):
            field = fieldMasters.getByName(fieldName)
            field.setPropertyValue("Content", "")
            field.dispose()
            self.otherLogger.debug("Field deleted")
            return True
        else:
            self.otherLogger.debug("Field not found")
            return False

    def __deepcopy__(self, memo):
        """UserVar objects are only one per document, so return this one."""
        return self


def setHasSettings(userVars, maxHasSettings, twoDocsHaveMax):
    """Sets HasSettings to the highest value of any open documents.
    Returns True if HasSettings was set previously.
    """
    varname = "HasSettings"
    alreadyHasSettings = False
    if not userVars.isEmpty(varname):
        alreadyHasSettings = True
        currentSettingsVal = userVars.getInt(varname)
        if currentSettingsVal == maxHasSettings and not twoDocsHaveMax:
            # No need to make any changes
            return alreadyHasSettings
    if maxHasSettings == -1:
        newVal = 1
    else:
        newVal = maxHasSettings + 1
    userVars.store(varname, str(newVal))
    return alreadyHasSettings

class SettingsDocPreparer:
    """Prepares a Writer document to contain user variables."""
    def __init__(self, VAR_PREFIX, writerUnoObjs):
        self.VAR_PREFIX = VAR_PREFIX
        self.unoObjs = writerUnoObjs
        theLocale.loadUnoObjs(self.unoObjs)

    def prepare(self):
        """Called from a Writer doc.
        Make sure the current document is ready to use for settings.

        Any item in the Writer Linguistics menu that doesn't require document
        contents but uses user var settings should call this method.
        """
        finder = SettingsDocFinder(self.VAR_PREFIX, self.unoObjs)
        maxHasSettings, twoDocsHaveMax, dummy = finder.findBestDoc()
        userVars = UserVars(self.VAR_PREFIX, self.unoObjs.document, logger)
        alreadyHasSettings = setHasSettings(
            userVars, maxHasSettings, twoDocsHaveMax)
        if alreadyHasSettings:
            return
        if self._doc_is_empty():
            self.addContents()

    def _doc_is_empty(self):
        """Returns true if the current document is practically empty.
        This may not recognize some objects such as frames.
        However it does work for tables.
        """
        oTextEnum = iteruno.byEnum(self.unoObjs.text)
        paragraphs = list(oTextEnum)
        parCount = len(paragraphs)
        logger.debug("Found %d paragraphs in current doc.", parCount)
        if parCount > 2:
            return False
        for oPar in paragraphs:
            oParEnum = iteruno.byEnum(oPar)
            par_elems = list(oParEnum)
            parElemCount = len(par_elems)
            logger.debug("Found %d paragraph elements.", parElemCount)
            if parElemCount > 2:
                return False
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        CHARS_REQUIRED = 10
        for dummy in range(CHARS_REQUIRED):
            if not oVC.goRight(1, False):
                return True
        logger.debug("Document has at least %d characters.", CHARS_REQUIRED)
        return False

    def addContents(self):
        """Add explanation text to the document."""
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        oVC.gotoEnd(False)
        componentName = ""
        if self.VAR_PREFIX == Prefix.SCRIPT_PRACTICE:
            componentName = theLocale.getText("Script Practice")
        elif self.VAR_PREFIX == Prefix.WORD_LIST:
            componentName = theLocale.getText("Word List and Spelling")
        elif self.VAR_PREFIX == Prefix.SPELLING:
            componentName = theLocale.getText("Spelling")
        elif self.VAR_PREFIX == Prefix.BULK_CONVERSION:
            componentName = theLocale.getText("Bulk Conversion")
        message = theLocale.getText(
            "This document stores %s settings.  "
            "Please leave it open while using %s.  "
            "If you want to keep the settings to use again later, "
            "then save this document.") % (componentName, componentName)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        self.unoObjs.text.insertString(oVC, message, 0)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)


class SettingsDocFinder:
    """Helps a Calc document that references user variables."""
    def __init__(self, VAR_PREFIX, genericUnoObjs):
        self.VAR_PREFIX = VAR_PREFIX
        self.unoObjs = genericUnoObjs

    def getWriterDoc(self):
        """Typically called from a Calc spreadsheet.
        Make sure we have a Writer document ready for user variables.

        Takes an object of type util.UnoObjs that has service objs but
        probably not writer doc objs.
        Returns unoObjs of a writer document to hold UserVars settings.

        Finds the best candidate found to store user variables.
        If no candidate is found, opens a blank document.
        """
        maxHasSettings, twoDocsHaveMax, docFound = self.findBestDoc()
        if docFound:
            return docFound
        else:
            ## Open a blank document in the background.
            uno_args = (
                util.createProp("Minimized", True),
            )
            newDoc = self.unoObjs.desktop.loadComponentFromURL(
                "private:factory/swriter", "_blank", 0, uno_args)
            # this won't modify the original reference kept by calling code
            writerUnoObjs = self.unoObjs.getDocObjs(newDoc)
            writerUnoObjs.window.setVisible(True)
            userVars = UserVars(
                self.VAR_PREFIX, writerUnoObjs.document, logger)
            setHasSettings(userVars, maxHasSettings, twoDocsHaveMax)
            preparer = SettingsDocPreparer(self.VAR_PREFIX, writerUnoObjs)
            preparer.addContents()
            return writerUnoObjs

    def findBestDoc(self):
        """Searches all open documents for a Writer document.
        If more than one is found, chooses the one with the highest value of
        HasSettings, which will usually be the most recent.

        :return arg1: highest value found of HasSettings
        :return arg2: true if two or more docs have the same highest value
        :return arg3: UNO objects of document with highest value
        """
        maxVal = -1
        bestDoc = None
        twoDocsHaveMax = False  # if two or more docs have the same max value
        doclist = self.unoObjs.getOpenDocs(util.UnoObjs.DOCTYPE_WRITER)
        for docUnoObjs in doclist:
            logger.debug("Checking writer document for settings.")
            userVars = UserVars(
                self.VAR_PREFIX, docUnoObjs.document, logger)
            val = userVars.getInt("HasSettings")
            if val > 0 and val > maxVal:
                logger.debug("Found doc with HasSettings value %s.", val)
                maxVal = val
                bestDoc = docUnoObjs
                twoDocsHaveMax = False
            elif val == maxVal:
                twoDocsHaveMax = True
        return maxVal, twoDocsHaveMax, bestDoc


class Syncable:
    """Interface for classes that are able to be synced with user vars."""
    def __init__(self, userVars):
        if self.__class__ is Syncable:
            # The base class should not be instantiated.
            raise NotImplementedError
        self.userVars = userVars

    def loadUserVars(self):
        """Load this item's attributes from user variables."""
        # All derived classes should implement this method.
        raise NotImplementedError()

    def storeUserVars(self):
        """Store user variable values for this item."""
        # All derived classes should implement this method.
        raise NotImplementedError()

    def cleanupUserVars(self):
        """Delete everything that was stored by storeUserVars().
        Returns True if something was cleaned up.

        Some derived classes never delete their user variables,
        so they are not required to override this method.
        """
        return False

    @staticmethod
    def noUserVarData(varName):
        return exceptions.DataNotFoundError(
            u"Error parsing %s user variable.  Please go to \"Insert -> "
            u"Field -> More Fields\" and fix the problem.", varName)


class FieldTags:
    """Handle various names for markers and fields.
    This is handled when reading XML tags.

    This may be useful only for Toolbox,
    because Phonology Assistant and FieldWorks seem to be more complex,
    making it more than just a matter of renaming markers.
    """
    TAG_VARS = []
    DEFAULT_TAGS = {}

    def __init__(self, userVars):
        if self.__class__ is FieldTags:
            # The base class should not be instantiated.
            raise NotImplementedError
        self.userVars = userVars
        self.tags = {}

    def loadUserVars(self):
        """Sets self.tags from user vars and defaults.
        Returns dictionary where values are standard format marker names.
        """
        for key, varName in self.TAG_VARS:
            markerName = self.userVars.get(varName)
            if not markerName:
                markerName = self.DEFAULT_TAGS[key]
                self.userVars.store(varName, markerName)
            self.tags[key] = markerName
        return self.tags


class GrammarTags(FieldTags):
    TAG_VARS = [
        ['ref', "SFMarker_RefNum"],
        ['word1', "SFMarker_Word1"],  # corresponds with check box for line 1
        ['word2', "SFMarker_Word2"],
        ['morph1', "SFMarker_Morpheme1"],
        ['morph2', "SFMarker_Morpheme2"],
        ['gloss', "SFMarker_Gloss"],
        ['pos', "SFMarker_POS"],
        ['ft', "SFMarker_FreeTxln"]]

    DEFAULT_TAGS = {
        'ref' : "ref",
        'word1' : "tx",
        'word2' : "tor",
        'morph1' : "mb",
        'morph2' : "mor",
        'gloss' : "ge",
        'pos' : "ps",
        'ft' : "ft"}


class PhonologyTags(FieldTags):
    TAG_VARS = [
        ['phonemic', "SFMarker_Phonemic"],
        ['phonetic', "SFMarker_Phonetic"],
        ['gloss', "SFMarker_Gloss"],
        ['ref', "SFMarker_RefNum"]]

    DEFAULT_TAGS = {
        'phonemic' : "phm",
        'phonetic' : "pht",
        'gloss' : "ge",
        'ref' : "ref"}
