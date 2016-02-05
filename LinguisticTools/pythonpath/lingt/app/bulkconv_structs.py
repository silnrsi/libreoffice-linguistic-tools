# -*- coding: Latin-1 -*-
#
# This file created Aug 8 2015 by Jim Kornelsen
#
# 24-Aug-15 JDK  Define __str__() instead of toItemText().
# 25-Aug-15 JDK  Add FontItem.numberedVar().
# 18-Dec-15 JDK  Use rich comparisons instead of getID().
# 24-Dec-15 JDK  Moved part of FontItem to a new FontChange class.
# 05-Feb-16 JDK  Show a mark in the list to indicate font changes.

"""
Data structures for Bulk Conversion used by lower layer packages.
To avoid cyclic imports, these are not defined in the BulkConversion module.

This module exports:
    FontItem
    FontChange
"""
import functools

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.writer.uservars import Syncable
from lingt.utils.fontsize import FontSize


class FontInfo:
    def __init__(self):
        self.name = ""  # font name
        self.fontType = 'Western'
        self.size = FontSize()
        self.styleType = 'CustomFormatting'
        self.styleName = ""

    def __repr__(self):
        return repr(self.name, self.styleName)


@functools.total_ordering
class FontItem(FontInfo):
    """A structure to hold input data for one font."""

    def __init__(self):
        FontInfo.__init__(self)
        self.name = "(None)"
        self.inputData = list()
        self.fontChange = None  # type FontChange

    def __str__(self):
        strval = str(self.name)
        if self.styleName:
            strval += " (%s)" % self.styleName
        if self.fontChange:
            strval = "*  " + strval
        return strval

    def attrs(self):
        """Attributes used for magic methods below."""
        return (
            self.name, self.styleName,
            self.fontType, self.styleType)

    def __lt__(self, other):
        return (isinstance(other, FontItem) and
                self.attrs() < other.attrs())

    def __eq__(self, other):
        """This method gets used when testing for membership using *in*,
        as odt_converter.py does.
        """
        #pylint: disable=protected-access
        return (isinstance(other, FontItem) and
                self.attrs() == other.attrs())
        #pylint: enable=protected-access

    def __hash__(self):
        """Make instances with identical attributes use the same hash."""
        return hash(self.attrs())


class FontChange(FontInfo, Syncable):
    """A structure to hold form data for changing one font."""

    def __init__(self, font_from, userVars, varNum=0):
        """
        :param font_from: FontItem being converted from
        :param userVars: for persistent storage
        :param varNum: a user variable number unique to this change
        """
        FontInfo.__init__(self)
        Syncable.__init__(self, userVars)
        self.fontItem = font_from
        self.varNum = varNum  # for storage in user variables
        self.converter = ConverterSettings(userVars)
        self.converted_data = dict()  # key inputString, value convertedString

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
        self.fontItem.name = self.userVars.get(
            self.numberedVar("fontNameFrom"))
        self.fontItem.styleName = self.userVars.get(
            self.numberedVar("styleNameFrom"))
        if not self.fontItem.name and not self.fontItem.styleName:
            raise self.noUserVarData(self.numberedVar("fontNameFrom"))
        self.name = self.userVars.get(self.numberedVar("fontNameTo"))
        self.styleName = self.userVars.get(self.numberedVar("styleNameTo"))
        self.fontType = self.userVars.get(self.numberedVar("fontType"))
        self.size = FontSize()
        if not self.userVars.isEmpty(self.numberedVar("size")):
            self.size.loadUserVar(self.userVars, self.numberedVar("size"))
        self.styleType = self.userVars.get(self.numberedVar("styleType"))
        self.styleName = self.userVars.get(self.numberedVar("styleName"))
        self.converter.convName = self.userVars.get(
            self.numberedVar("convName"))
        self.converter.normForm = self.userVars.getInt(
            self.numberedVar("normalize"))
        varname = self.numberedVar('forward')
        if (not self.userVars.isEmpty(varname) and
                self.userVars.getInt(varname) == 0):
            self.converter.forward = False

    def storeUserVars(self):
        """Sets the user vars for this item."""
        fontNameFrom = self.fontItem.name
        if fontNameFrom == "(None)":
            fontNameFrom = None  #TESTME
        self.userVars.store(self.numberedVar("fontNameFrom"), fontNameFrom)
        self.userVars.store(self.numberedVar("fontNameTo"), self.name)
        self.userVars.store(
            self.numberedVar("styleNameFrom"), self.fontItem.styleName)
        self.userVars.store(self.numberedVar("styleNameTo"), self.styleName)
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
        return foundSomething1 or foundSomething2
