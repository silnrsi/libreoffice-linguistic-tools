"""
Data structures for Bulk Conversion used by lower layer packages.
To avoid cyclic imports, these are not defined in the BulkConversion module.

This module exports:
    StyleItem
    StyleChange
"""
import functools
import logging

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions
from lingt.utils.fontsize import FontSize

logger = logging.getLogger("lingt.app.dataconversion")


class StyleType:
    """What type of style."""
    NO_CHANGE = 'NoChange'
    PARA = 'ParaStyle'
    CHAR = 'CharStyle'
    CUSTOM = 'CustomFormatting'  # also known as automatic style


class ScopeType:
    """How to search through the document.
    This will determine what items are shown in StyleItemList.
    """
    WHOLE_DOC = 0
    FONT_WITHOUT_STYLE = 1  # custom formatting regardless of named style
    FONT_WITH_STYLE = 2  # custom formatting or font of style
    PARASTYLE = 3
    CHARSTYLE = 4
    TO_STRING = {
        WHOLE_DOC : "Whole Document",
        FONT_WITHOUT_STYLE : "Font Not Including Style",
        FONT_WITH_STYLE : "Font Including Style",
        PARASTYLE : "Paragraph Style",
        CHARSTYLE : "Character Style",
        }


class StyleInfo:
    """Information about a particular font or named style."""

    def __init__(self):
        self.fontName = ""
        self.fontType = 'Western'  # 'Western' (Standard), 'Complex' or 'Asian'
        self.size = FontSize()
        self.styleType = StyleType.NO_CHANGE
        self.styleDisplayName = ""  # for example "Default Style"
        self.styleName = ""  # underlying name of styleDisplayName, "Standard"

    def __repr__(self):
        return repr([self.fontName, self.styleName])

    def getPropSuffix(self):
        """For use in UNO properties such as CharFontComplex."""
        if self.fontType == 'Western':
            return ""
        return self.fontType


@functools.total_ordering
class StyleItem(StyleInfo):
    """A structure to hold input data for one font.
    Used to display items in the main list box.
    """
    def __init__(self, scopeType=ScopeType.FONT_WITH_STYLE):
        StyleInfo.__init__(self)
        self.scopeType = scopeType
        self.fontName = "(Default)"  # either a standard name, complex or Asian
        self.inputData = []  # data that gets read from the file
        self.inputDataOrder = 0  # sort order this item occurred in the file
        self.change = None  # type StyleChange

    def create_change(self, userVars):
        """Create a new StyleChange for this item if it doesn't exist yet.
        Now this item will be recognized as having a change,
        even if the values aren't actually any different.
        """
        if not self.change:
            self.change = StyleChange(self, userVars)
        return self.change

    def set_change(self, styleChange):
        self.change = styleChange
        styleChange.styleItem = self

    def effective_info(self):
        """Gets the StyleInfo object that is currently effective."""
        if self.change:
            return self.change
        return self

    def __str__(self):
        if self.scopeType == ScopeType.WHOLE_DOC:
            strval = "Whole Document"
        elif self.scopeType in (
                ScopeType.FONT_WITH_STYLE, ScopeType.FONT_WITHOUT_STYLE):
            strval = str(self.fontName)
        elif self.scopeType in (ScopeType.CHARSTYLE, ScopeType.PARASTYLE):
            strval = str(self.styleName)
            if self.styleDisplayName:
                strval = self.styleDisplayName
        else:
            raise exceptions.LogicError(
                "Unexpected value %s", self.scopeType)
        if self.change:
            strval = "*  " + strval
        return strval

    def attrs(self):
        """Attributes that uniquely identify this object.
        Used for magic methods below.
        """
        #logger.debug("StyleItem.attrs()")
        if self.scopeType == ScopeType.WHOLE_DOC:
            return 'WholeDoc'  # only one unique value for all items
        if self.scopeType in (
                ScopeType.FONT_WITH_STYLE, ScopeType.FONT_WITHOUT_STYLE):
            return (self.fontName, self.fontType)
        if self.scopeType in (ScopeType.CHARSTYLE, ScopeType.PARASTYLE):
            return (self.styleName, self.styleType)
        raise exceptions.LogicError(
            "Unexpected value %s", self.scopeType)

    def __lt__(self, other):
        return (isinstance(other, StyleItem) and
                self.attrs() < other.attrs())

    def __eq__(self, other):
        """This method gets used when testing for membership using *in*,
        as odt_converter.py does.
        """
        return (isinstance(other, StyleItem) and
                self.attrs() == other.attrs())

    def __hash__(self):
        """Make instances with identical attributes use the same hash."""
        return hash(self.attrs())


class ProcessingStyleItem(StyleItem):
    """Used in the lingt.access layer for processing XML data."""

    def __init__(self, scopeType, named):
        StyleItem.__init__(self, scopeType)
        self.styleInternalName = ""  # with _20_ instead of spaces
        self.fontStandard = "(Default)"  # could be non-Unicode Devanagari
        self.fontComplex = "(Default)"  # CTL fonts such as Unicode Devanagari
        self.fontAsian = "(Default)"  # Chinese, Japanese, Korean (CJK) fonts
        self.sizeStandard = FontSize()
        self.sizeComplex = FontSize()
        self.sizeAsian = FontSize()
        self.named = named  # True = named style, False = automatic style

    def getStyleItem(self, scopeType):
        """Returns a StyleItem object useful for higher layers."""
        styleItem = StyleItem(scopeType)
        styleItem.inputData = self.inputData
        styleItem.inputDataOrder = self.inputDataOrder
        if scopeType == ScopeType.WHOLE_DOC:
            pass
        elif scopeType in (
                ScopeType.FONT_WITH_STYLE, ScopeType.FONT_WITHOUT_STYLE):
            styleItem.fontName = self.fontName
            styleItem.fontType = self.fontType
        elif self.scopeType in (ScopeType.CHARSTYLE, ScopeType.PARASTYLE):
            styleItem.styleType = self.styleType
            styleItem.styleDisplayName = self.styleDisplayName
            styleItem.styleName = self.styleName
        else:
            raise exceptions.LogicError("Unexpected value %s", scopeType)
        return styleItem

    def attrs(self):
        """Attributes that uniquely identify this object."""
        #logger.debug("ProcessingStyleItem.attrs()")
        return (
            self.fontName, self.fontType,
            self.styleName, self.styleType,
            self.fontStandard, self.fontComplex, self.fontAsian,
            self.sizeStandard, self.sizeComplex, self.sizeAsian)

    def __eq__(self, other):
        if isinstance(other, ProcessingStyleItem):
            return self.attrs() == other.attrs()
        if isinstance(other, StyleItem):
            return StyleItem.attrs(self) == other.attrs()
        return False


class StyleChange(StyleInfo, Syncable):
    """A structure to hold form data for changing one font."""

    def __init__(self, style_from, userVars, varNum=0):
        """
        :param style_from: StyleItem being converted from
        :param userVars: for persistent storage
        :param varNum: a user variable number unique to this change
        """
        StyleInfo.__init__(self)
        Syncable.__init__(self, userVars)
        self.styleItem = style_from
        self.varNum = varNum  # for storage in user variables
        self.converter = ConverterSettings(userVars)
        self.converted_data = {}  # key inputString, value convertedString
        self.remove_custom_formatting = True

    def setVarNum(self, varNum):
        self.varNum = varNum

    def varNumStr(self):
        """Many user variables for the class contain this substring,
        based on enumerating the font items.
        Specify varNum before calling this method.
        """
        return "%03d" % self.varNum

    def numberedVar(self, suffix=""):
        """Get a user variable name that includes the file number.
        :param suffix: Add this to the end of the string.
        """
        return "font%s_%s" % (self.varNumStr(), suffix)

    def loadUserVars(self):
        self.styleItem.fontName = self.userVars.get(
            self.numberedVar("fontNameFrom"))
        self.styleItem.styleDisplayName = self.userVars.get(
            self.numberedVar("styleNameFrom"))
        if not self.styleItem.fontName and not self.styleItem.styleDisplayName:
            raise self.noUserVarData(self.numberedVar("fontNameFrom"))
        self.fontName = self.userVars.get(self.numberedVar("fontNameTo"))
        self.styleDisplayName = self.userVars.get(
            self.numberedVar("styleNameTo"))
        self.fontType = self.userVars.get(self.numberedVar("fontType"))
        self.size = FontSize()
        if not self.userVars.isEmpty(self.numberedVar("size")):
            self.size.loadUserVar(self.userVars, self.numberedVar("size"))
        self.styleType = self.userVars.get(self.numberedVar("styleType"))
        self.styleDisplayName = self.userVars.get(
            self.numberedVar("styleName"))
        self.converter.convName = self.userVars.get(
            self.numberedVar("convName"))
        self.converter.normForm = self.userVars.getInt(
            self.numberedVar("normalize"))
        varname = self.numberedVar('forward')
        if (not self.userVars.isEmpty(varname) and
                self.userVars.getInt(varname) == 0):
            self.converter.forward = False
        varname = self.numberedVar('removeCustomFormatting')
        if (not self.userVars.isEmpty(varname) and
                self.userVars.getInt(varname) == 0):
            self.remove_custom_formatting = False

    def storeUserVars(self):
        """Sets the user vars for this item."""
        fontNameFrom = self.styleItem.fontName
        if fontNameFrom == "(None)":
            fontNameFrom = None  #TESTME
        self.userVars.store(self.numberedVar("fontNameFrom"), fontNameFrom)
        self.userVars.store(self.numberedVar("fontNameTo"), self.fontName)
        self.userVars.store(
            self.numberedVar("styleNameFrom"), self.styleItem.styleDisplayName)
        self.userVars.store(
            self.numberedVar("styleNameTo"), self.styleDisplayName)
        self.userVars.store(self.numberedVar("fontType"), self.fontType)
        self.userVars.store(self.numberedVar("styleType"), self.styleType)
        if self.size.isSpecified():
            self.userVars.store(
                self.numberedVar('size'), self.size.getString())
        self.userVars.store(
            self.numberedVar("convName"), self.converter.convName)
        self.userVars.store(
            self.numberedVar('forward'), str(int(self.converter.forward)))
        self.userVars.store(
            self.numberedVar("normalize"), str(self.converter.normForm))
        self.userVars.store(
            self.numberedVar('removeCustomFormatting'),
            str(int(self.remove_custom_formatting)))

    def cleanupUserVars(self):
        """Returns True if something was cleaned up."""
        foundSomething1 = self.userVars.delete(
            self.numberedVar("fontNameFrom"))
        foundSomething2 = self.userVars.delete(
            self.numberedVar("styleNameFrom"))
        self.userVars.delete(self.numberedVar("fontNameTo"))
        self.userVars.delete(self.numberedVar("styleNameTo"))
        self.userVars.delete(self.numberedVar("fontType"))
        self.userVars.delete(self.numberedVar('size'))
        self.userVars.delete(self.numberedVar("styleType"))
        self.userVars.delete(self.numberedVar("convName"))
        self.userVars.delete(self.numberedVar('forward'))
        self.userVars.delete(self.numberedVar("normalize"))
        self.userVars.delete(self.numberedVar('removeCustomFormatting'))
        return foundSomething1 or foundSomething2
