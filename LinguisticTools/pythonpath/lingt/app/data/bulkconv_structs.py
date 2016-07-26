# -*- coding: Latin-1 -*-
#
# This file created Aug 8 2015 by Jim Kornelsen
#
# 24-Aug-15 JDK  Define __str__() instead of toItemText().
# 25-Aug-15 JDK  Add FontItem.numberedVar().
# 18-Dec-15 JDK  Use rich comparisons instead of getID().
# 24-Dec-15 JDK  Moved part of FontItem to a new FontChange class.
# 05-Feb-16 JDK  Show a mark in the list to indicate font changes.
# 19-Feb-16 JDK  Add fonts found of each type.
# 22-Jun-16 JDK  Add method to group items.
# 24-Jun-16 JDK  FontItemList holds FontItemGroup instead of FontItem.
# 13-Jul-16 JDK  Each kind of font can have its own size.
# 15-Jul-16 JDK  Instead of fonts, use StyleItems that depend on scope type.
# 21-Jul-16 JDK  Add ProcessingStyleItem, only needed for lingt.access layer.
# 22-Jul-16 JDK  Add StyleChange.removeCustomFormatting.

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
    FONT_WITH_STYLE = 1  # custom formatting or font of style
    FONT_WITHOUT_STYLE = 2  # custom formatting regardless of user style
    PARASTYLE = 3
    CHARSTYLE = 4


class StyleInfo:
    """Information about a particular font or user defined style."""

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
        else:
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
        self.inputData = list()  # data that gets read from the file
        self.inputDataOrder = 0  # sort order this item occurred in the file
        self.change = None  # type StyleChange

    def create_change(self, userVars):
        """Create a new StyleChange for this item if it doesn't exist yet.
        Now this item will be recognized as having a change,
        even if the values aren't actually any different.
        """
        if not self.change:
            self.change = StyleChange(self, userVars)

    def set_change(self, styleChange):
        self.change = styleChange
        styleChange.styleItem = self

    def effective_info(self):
        """Gets the StyleInfo object that is currently effective."""
        if self.change:
            return self.change
        else:
            return self

    def __str__(self):
        if self.scopeType == ScopeType.WHOLE_DOC:
            strval = "Whole Document"
        elif (self.scopeType == ScopeType.FONT_WITH_STYLE
              or self.scopeType == ScopeType.FONT_WITHOUT_STYLE):
            strval = str(self.fontName)
        elif (self.scopeType == ScopeType.CHARSTYLE
              or self.scopeType == ScopeType.PARASTYLE):
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
        logger.debug("StyleItem.attrs()")
        if self.scopeType == ScopeType.WHOLE_DOC:
            return 'WholeDoc'  # only one unique value for all items
        elif (self.scopeType == ScopeType.FONT_WITH_STYLE
              or self.scopeType == ScopeType.FONT_WITHOUT_STYLE):
            return (self.fontName, self.fontType)
        elif (self.scopeType == ScopeType.CHARSTYLE
              or self.scopeType == ScopeType.PARASTYLE):
            return (self.styleName, self.styleType)
        else:
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

    def __init__(self, scopeType=ScopeType.FONT_WITH_STYLE):
        StyleItem.__init__(self, scopeType)
        self.fontStandard = "(Default)"  # could be non-Unicode Devanagari
        self.fontComplex = "(Default)"  # CTL fonts such as Unicode Devanagari
        self.fontAsian = "(Default)"  # Chinese, Japanese, Korean (CJK) fonts
        self.sizeStandard = FontSize()
        self.sizeComplex = FontSize()
        self.sizeAsian = FontSize()

    def getStyleItem(self, scopeType):
        """Returns a StyleItem object useful for higher layers."""
        styleItem = StyleItem(scopeType)
        styleItem.inputData = self.inputData
        styleItem.inputDataOrder = self.inputDataOrder
        if scopeType == ScopeType.WHOLE_DOC:
            pass
        elif (scopeType == ScopeType.FONT_WITH_STYLE
              or scopeType == ScopeType.FONT_WITHOUT_STYLE):
            styleItem.fontName = self.fontName
            styleItem.fontType = self.fontType
        elif (scopeType == ScopeType.PARASTYLE or
              scopeType == ScopeType.CHARSTYLE):
            styleItem.styleType = self.styleType
            styleItem.styleDisplayName = self.styleDisplayName
            styleItem.styleName = self.styleName
        else:
            raise exceptions.LogicError("Unexpected value %s", scopeType)
        return styleItem

    def attrs(self):
        """Attributes that uniquely identify this object."""
        logger.debug("ProcessingStyleItem.attrs()")
        return (
            self.fontName, self.fontType,
            self.styleName, self.styleType,
            self.fontStandard, self.fontComplex, self.fontAsian,
            self.sizeStandard, self.sizeComplex, self.sizeAsian)

    def __eq__(self, other):
        if isinstance(other, ProcessingStyleItem):
            return self.attrs() == other.attrs()
        elif isinstance(other, StyleItem):
            return StyleItem.attrs(self) == other.attrs()
        return False


class StyleChange(StyleInfo, Syncable):
    """A structure to hold form data for changing one font."""

    def __init__(self, font_from, userVars, varNum=0):
        """
        :param font_from: StyleItem being converted from
        :param userVars: for persistent storage
        :param varNum: a user variable number unique to this change
        """
        StyleInfo.__init__(self)
        Syncable.__init__(self, userVars)
        self.styleItem = font_from
        self.varNum = varNum  # for storage in user variables
        self.converter = ConverterSettings(userVars)
        self.converted_data = dict()  # key inputString, value convertedString
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

    def setattr_from_other(self, other, attr_name):
        """
        :param other: StyleChange object to read from
        :param attr_name: for example 'styleName' or 'converter.name'
        """
        attr_names = attr_name.split('.')
        this_container = self._last_container(attr_names)
        # pylint: disable=protected-access
        other_container = other._last_container(attr_names)
        # pylint: enable=protected-access
        last_attr_name = attr_names[-1]
        other_value = getattr(other_container, last_attr_name)
        setattr(this_container, last_attr_name, other_value)

    def _last_container(self, attr_names):
        """Returns the object that contains the last attribute in
        attr_names.
        """
        if len(attr_names) == 1:
            return self
        if attr_names[0] == 'converter':
            return self.converter
        raise exceptions.LogicError(
            "Unexpected attribute names: %r", attr_names)

