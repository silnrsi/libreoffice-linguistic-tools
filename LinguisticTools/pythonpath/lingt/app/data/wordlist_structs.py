# -*- coding: Latin-1 -*-
#
# This file created Nov 19 2012 by Jim Kornelsen
#
# 26-Feb-13 JDK  Added PART field type.
# 18-Apr-13 JDK  Fixed bug: setIsCorrect() should set value, not return it.
# 16-Jul-15 JDK  Moved static fromStringList() into spellingcomparisons.
# 17-Jul-15 JDK  Use OrderedDict for ColumnOrder class.
# 15-Aug-15 JDK  Use Tribool for three-way value.
# 27-Aug-15 JDK  Added cleanupUserVars().

"""
Data structures used by other parts of the application.
To avoid cyclic imports, these are not defined in the WordList module.

This module exports:
    WordInList
    ColumnOrder
    WhatToGrab
"""
import collections
import logging
import os
import re
from grantjenks.tribool import Tribool

from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions
from lingt.app import lingex_structs
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.app.wordlist_structs")

class WordInList:
    """A word that can be used in word lists.
    It can be grouped to represent multiple occurences, or left single to
    represent a specific occurrence in a specific text.
    """

    def __init__(self):
        self.text = ""  # the word
        self.source = ""  # file name where it occurs, if not grouping
        self.sources = dict() # file names where it occurs and number of
                              # occurrences, if grouping
        self.occurrences = 0  # number of occurences, if grouping
        self.isCorrect = Tribool('Indeterminate')
        self.correction = ""  # corrected spelling
        self.similarWords = []  # candidates for corrected spelling
        self.converted1 = ""  # often used for romanizing the word
        self.converted2 = ""  # could be used for romanizing another field

    def similarWords_str(self):
        return "  ".join(self.similarWords)

    def setSimilarWords(self, delimitedString):
        self.similarWords = delimitedString.split()

    def isCorrect_str(self):
        if self.isCorrect is Tribool('Indeterminate'):
            return ""
        elif self.isCorrect is Tribool('True'):
            return "OK"
        elif self.isCorrect is Tribool('False'):
            return "X"
        raise exceptions.LogicError("Unexpected value %r", self.isCorrect)

    def setIsCorrect(self, strval):
        self.isCorrect = Tribool('Indeterminate')
        if strval.lower() in ("ok", "yes", "+"):
            self.isCorrect = Tribool('True')
        elif strval.lower() in ("x", "no", "-"):
            self.isCorrect = Tribool('False')

    def sources_str(self):
        if len(self.sources) == 1:
            filepath = next(iter(self.sources.keys()))  # iter for python2.x
            return os.path.basename(filepath)
        elif len(self.sources) > 1:
            strlist = []
            for filepath, fileoccur in self.sources.items():
                strlist.append(
                    "%s(%s)" % (os.path.basename(filepath), fileoccur))
            return ", ".join(sorted(strlist))
        return ""

    def setSources(self, delimitedString):
        self.sources.clear()
        strlist = delimitedString.split(",")
        for strval in strlist:
            strval = strval.strip()  # remove whitespace
            matchObj = re.match(r'(.+)\((\d+)\)', strval)
            if matchObj:
                filepath = matchObj.group(1)
                fileoccur = matchObj.group(2)
                self.sources[filepath] = fileoccur
            else:
                self.sources[strval] = self.occurrences


class ColumnOrder(Syncable):
    """Columns based on WordInList fields.
    While the order in self.sortOrder can be changed by the user,
    the order of the dictionary itself should not change.
    """
    COLUMNS = collections.OrderedDict([
        ('colWord', "Word"),
        ('colChange', "Correction"),
        ('colSimilar', "Similar Words"),
        ('colOccur', "Occurrences"),
        ('colSrc', "Sources"),
        ('colConv1', "Converted 1"),
        ('colConv2', "Converted 2"),
        ('colOk', "Correct?")])

    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.sortOrder = list(ColumnOrder.COLUMNS.keys())
        self.rowData = [""] * len(self.COLUMNS)
        self.rowTuple = ()

    def moveUp(self, elem_i):
        """
        Moves the specified element in self.sortOrder.
        Returns True if a change was made.
        """
        if elem_i == 0:
            return False
        return self.moveDown(elem_i - 1)

    def moveDown(self, elem_i):
        """
        Moves the specified element in self.sortOrder.
        Returns True if a change was made.
        """
        if elem_i == len(self.sortOrder) - 1:
            return False
        l = self.sortOrder  # shorthand variable name
        l[elem_i], l[elem_i + 1] = l[elem_i + 1], l[elem_i]  # swap
        return True

    def getColLetter(self, colKey):
        return chr(ord('A') + self.sortOrder.index(colKey))

    def maxColLetter(self):
        return chr(ord('A') + len(self.COLUMNS) - 1)

    def getTitles(self):
        return [ColumnOrder.COLUMNS[colKey] for colKey in self.sortOrder]

    def getTitle(self, elem_i):
        return ColumnOrder.COLUMNS[self.sortOrder[elem_i]]

    def resetRowData(self):
        self.rowData = [""] * len(self.COLUMNS)

    def setRowVal(self, colKey, newVal):
        sortedIndex = self.sortOrder.index(colKey)
        self.rowData[sortedIndex] = newVal

    def getRowTuple(self):
        """Returns a tuple."""
        return tuple(self.rowData)

    def setRowTuple(self, newTuple):
        """
        After calling this method, use getRowVal() to unpack.
        This is the reverse of resetRowData() and getRowTuple().
        """
        self.rowTuple = newTuple

    def getRowVal(self, colKey):
        sortedIndex = self.sortOrder.index(colKey)
        return self.rowTuple[sortedIndex]

    @staticmethod
    def getVarName(colKey):
        """We use the key as part of the user var name."""
        return "Spreadsheet_" + colKey

    def storeUserVars(self):
        colNum = 0
        for colKey in self.sortOrder:
            self.userVars.store(
                ColumnOrder.getVarName(colKey), chr(ord('A') + colNum))
            colNum += 1

    def loadUserVars(self):
        if self.userVars.isEmpty(ColumnOrder.getVarName('colWord')):
            # just use the default list
            return
        letters = [self.userVars.get(ColumnOrder.getVarName(colKey))
                   for colKey in self.COLUMNS.keys()]
        # sort by letters
        zippedList = sorted(zip(letters, self.COLUMNS.keys()))
        dummy, self.sortOrder = zip(*zippedList)
        self.sortOrder = list(self.sortOrder)


class WhatToGrab(Syncable):
    """Identifies a field to grab information from.
    Used for harvesting word list data from the field.
    """
    UNSPECIFIED = -1
    FIELD = 0  # Toolbox or FieldWorks field, or XML field
    PARASTYLE = 1  # style name
    CHARSTYLE = 2  # style name
    FONT = 3  # font name
    SFM = 4  # marker
    COLUMN = 5  # for spreadsheets
    PART = 6  # for Writer documents
    TITLES = {
        UNSPECIFIED : "(Unspecified)",
        FIELD : "Field",
        PARASTYLE : "Paragraph Style",
        CHARSTYLE : "Character Style",
        FONT : "Font",
        SFM : "SFM Marker",
        COLUMN : "Column",
        PART : "Part"
        }
    WHOLE_DOC = 'whole'  # possible value for whichOne when grabType is PART
    LINGEX_DICT = dict(
        lingex_structs.LingPhonExample.GRAB_FIELDS +
        lingex_structs.LingGramExample.GRAB_FIELDS)

    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.grabType = self.UNSPECIFIED
        self.whichOne = ""  # for example "\tx"
        self.fontType = ""  # needed when grabType is WhatToGrab.FONT
        self.prefix = ""    # user var prefix

    def __str__(self):
        """Used for list box displaying and sorting.
        Call theLocale.loadUnoObjs() before using this method.
        """
        logger.debug("str(WhatToGrab) %d %s", self.grabType, self.whichOne)
        if self.grabType == self.PART and self.whichOne == self.WHOLE_DOC:
            return theLocale.getText("Whole Document")
        if self.grabType in self.TITLES:
            display = theLocale.getText(self.TITLES[self.grabType])
            if (self.grabType == self.FONT and
                    self.fontType in ['Complex', 'Asian']):
                display += " (%s)" % theLocale.getText(self.fontType)
            val = self.whichOne
            if self.grabType == self.FIELD:
                val = self.LINGEX_DICT.get(val, val)
                val = theLocale.getText(val)
            return display + ": " + val
        return ""

    def setPrefix(self, prefix):
        self.prefix = prefix

    def loadUserVars(self):
        varname = self.prefix + "type"
        if self.userVars.isEmpty(varname):
            self.grabType = self.UNSPECIFIED
        else:
            self.grabType = self.userVars.getInt(varname)
        self.whichOne = self.userVars.get(self.prefix + "val")
        if self.grabType == WhatToGrab.FONT:
            self.fontType = self.userVars.get(self.prefix + "fontType")

    def storeUserVars(self):
        self.userVars.store(self.prefix + "type", str(self.grabType))
        self.userVars.store(self.prefix + "val", self.whichOne)
        if self.grabType == WhatToGrab.FONT:
            self.userVars.store(self.prefix + "fontType", self.fontType)

    def cleanupUserVars(self):
        cleaned_up_something = self.userVars.delete(self.prefix + "type")
        self.userVars.delete(self.prefix + "val")
        self.userVars.delete(self.prefix + "fontType")
        return cleaned_up_something

