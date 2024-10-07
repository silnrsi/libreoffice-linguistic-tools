"""
Store persistent settings in user defined properties of a document.
The properties can be managed manually by going to
File > Properties > Custom Properties.

Previously, LOLT stored these settings in user field variables,
as shown under Insert > Fields > More Fields > Variables.
That's where this module's name comes from.
The reason for the change was that they could be stored in Writer but
not in some other components.
"""
import logging
import uno
from com.sun.star.beans.PropertyAttribute import REMOVEABLE
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK

from lingt.access.common import iteruno
from lingt.app import exceptions
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.access.uservars")

class Prefix:
    """For each module, we use a prefix to the user variable name.
    LT is short for Linguistic Tools.
    """
    PHONOLOGY = "LTp_"
    INTERLINEAR = "LTi_"
    ABBREVIATIONS = "LTa_"
    DATA_CONVERSION = "LTc_"
    DATA_CONV_DRAW = "LTd_"
    BULK_CONVERSION = "LTbc_"
    WORD_LIST = "LTw_"
    SPELLING = "LTsp_"
    SCRIPT_PRACTICE = "LTscr_"
    MAKE_OXT = "LTmk_"
    TESTING = "LTtest_"

class UserVars:
    """Access to the user defined properties of the document.
    These can be viewed using File > Properties > Custom Properties.
    """
    def __init__(self, VAR_PREFIX, oDoc, otherLogger):
        """
        :param VAR_PREFIX: member of the Prefix class
        :param oDoc: The UNO document object
        :param logger: Logger of the module that is using this class.
        """
        self.VAR_PREFIX = VAR_PREFIX
        self.otherLogger = otherLogger
        oDocProps = oDoc.getDocumentProperties()
        self.userProps = oDocProps.getUserDefinedProperties()

    def userPropsInfo(self):
        return self.userProps.getPropertySetInfo()

    def store(self, baseVarName, val):
        """Stores a value in a document. The value is persistent across macro
        calls.
        :param baseVarName: var name without "LTx_" prefix
        :param val: value to store
        """
        varName = self.getVarName(baseVarName)
        self.otherLogger.debug("storeUserVar %s", varName)
        #self.otherLogger.debug("storeUserVar %s=%s", varName, val)
        if val is None:
            stringVal = ""
        else:
            stringVal = str(val)
        if self.userPropsInfo().hasPropertyByName(varName):
            self.userProps.setPropertyValue(varName, stringVal)
        else:
            self.userProps.addProperty(varName, REMOVEABLE, stringVal)

    def get(self, baseVarName):
        """Returns the value of a user variable as a string"""
        varName = self.getVarName(baseVarName)
        self.otherLogger.debug("getUserVar %s", varName)
        if self.userPropsInfo().hasPropertyByName(varName):
            stringVal = self.userProps.getPropertyValue(varName)
            #self.otherLogger.debug("getUserVar =%s", stringVal)
            return stringVal
        return ""

    def getWithDefault(self, varName, defaultVal):
        """Returns default value if user var is empty."""
        if self.isEmpty(varName):
            return defaultVal
        return self.get(varName)

    def getVarName(self, baseVarName):
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
        if self.userPropsInfo().hasPropertyByName(varName):
            self.userProps.removeProperty(varName)
            self.otherLogger.debug("Property deleted")
            return True
        self.otherLogger.debug("Property not found")
        return False

    def __deepcopy__(self, memo):
        """UserVar objects are only one per document, so return this one."""
        return self

def setHasSettings(userVars):
    """Sets HasSettings. Returns True if HasSettings was set previously."""
    varname = "HasSettings"
    if userVars.isEmpty(varname):
        userVars.store(varname, "yes")
        return False
    return True

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
        userVars = UserVars(self.VAR_PREFIX, self.unoObjs.document, logger)
        alreadyHasSettings = setHasSettings(userVars)
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
        componentName = "LingTools"
        if self.VAR_PREFIX == Prefix.SCRIPT_PRACTICE:
            componentName = theLocale.getText("Script Practice")
        elif self.VAR_PREFIX == Prefix.WORD_LIST:
            componentName = theLocale.getText("Word Lists and Spelling")
        elif self.VAR_PREFIX == Prefix.SPELLING:
            componentName = theLocale.getText("Spelling")
        elif self.VAR_PREFIX == Prefix.BULK_CONVERSION:
            componentName = theLocale.getText("Bulk Conversion")
        elif self.VAR_PREFIX == Prefix.DATA_CONV_DRAW:
            componentName = theLocale.getText("Draw")
        elif self.VAR_PREFIX == Prefix.MAKE_OXT:
            componentName = theLocale.getText("Make OXT")
        message = theLocale.getText(
            "This document stores settings for %s.  "
            "Please leave it open while using %s.  "
            "If you want to keep the settings to use again later, "
            "then save this document.") % (componentName, componentName)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        self.unoObjs.text.insertString(oVC, message, 0)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)

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
            "Error parsing user defined property %s. Please go to File > "
            "Properties > Custom Properties and fix the problem.", varName)

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

class InterlinTags(FieldTags):
    TAG_VARS = [
        ['ref', "SFMarker_RefNum"],
        ['wordTx1', "SFMarker_WordText1"],
        ['wordTx2', "SFMarker_WordText2"],
        ['morphTx1', "SFMarker_MorphemeText1"],
        ['morphTx2', "SFMarker_MorphemeText2"],
        ['morphPos', "SFMarker_MorphemePOS"],
        ['morphGloss', "SFMarker_MorphemeGloss"],
        ['wordGloss', "SFMarker_WordGloss"],
        ['ft', "SFMarker_FreeTxln"]]
    DEFAULT_TAGS = {
        'ref' : "ref",
        'wordTx1' : "tx",
        'wordTx2' : "tor",
        'morphTx1' : "mb",
        'morphTx2' : "mor",
        'morphPos' : "ps",
        'morphGloss' : "ge",
        'wordGloss' : "wge",
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
