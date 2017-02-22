# -*- coding: Latin-1 -*-
#
# This file created Sept 16 2010 by Jim Kornelsen
#
# 25-Oct-12 JDK  New class for word list data files.
# 26-Feb-13 JDK  Override deepcopy for WordListFileItem.
# 11-Apr-13 JDK  Get writing system from user vars.
# 16-Apr-15 JDK  New class for bulk conversion.  FileItem class.
# 12-Aug-15 JDK  Define __len__() instead of Java-style getCount().
# 22-Aug-15 JDK  Define __str__() instead of toItemText().
# 25-Aug-15 JDK  Add FileItem.numberedVar().
# 27-Aug-15 JDK  Clean up unused word list field user variables.
# 09-Sep-15 JDK  Add ItemList class.
# 04-Nov-15 JDK  Moved InterlinInputSettings from lingex_structs module.
# 08-Dec-15 JDK  Add use_segnum.
# 18-Dec-15 JDK  Use __eq__ instead of getID().
# 17-Feb-17 JDK  Word Line 1 and 2 instead of Orthographic and Text.

"""
Maintain a list of files.

This module exports:
    FileItemList
    BulkFileItem
    LingExFileItem
    WordListFileItem
    InterlinInputSettings
"""
import copy
import logging
import os
import re

from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions
from lingt.app.data import wordlist_structs
from lingt.utils import util

logger = logging.getLogger("lingt.app.fileitemlist")

class FileItem(Syncable):
    """Abstract base class for objects used in FileItemList."""

    FILE_COUNT_VAR = None     # user variable name for the number of files

    def __init__(self, userVars, filenum=0):
        if self.__class__ is FileItem:
            # The base class should not be instantiated.
            raise NotImplementedError
        Syncable.__init__(self, userVars)
        self.userVars = userVars
        self.filenum = filenum
        self.filepath = ""

    def varNumStr(self):
        """Many user variables for the class contain this substring,
        based on enumerating the files.
        """
        return "%02d" % self.filenum

    def numberedVar(self, suffix=""):
        """Get a user variable name that includes the file number.
        :param suffix: Add this to the end of the string.
        """
        return "%s_%s" % (self.varNumStr(), suffix)

    def setFilenum(self, filenum):
        self.filenum = filenum

    def getNumFiles(self):
        return self.userVars.getInt(self.FILE_COUNT_VAR)

    def setNumFiles(self, numFiles):
        self.userVars.store(self.FILE_COUNT_VAR, str(numFiles))

    def cleanupUserVars(self):
        """Returns True if something was cleaned up."""
        # All derived classes should implement this method.
        raise NotImplementedError()

    def __str__(self):
        return os.path.basename(self.filepath)

    def __eq__(self, other):
        return self.filepath.lower() == other.filepath.lower()


class BulkFileItem(FileItem):
    """Stores information about a document file for bulk conversion."""

    FILE_COUNT_VAR = "infile_count"

    def __init__(self, userVars):
        FileItem.__init__(self, userVars)
        self.fileEditor = None  # type DocToXml

    def numberedVar(self, suffix=""):
        return "infile%s" % (FileItem.numberedVar(self, suffix))

    def loadUserVars(self):
        filepath = self.userVars.get(self.numberedVar("path"))
        if not filepath:
            raise self.noUserVarData(self.numberedVar("path"))
        self.filepath = filepath

    def storeUserVars(self):
        """Sets the user vars for this item."""
        self.userVars.store(self.numberedVar("path"), self.filepath)

    def cleanupUserVars(self):
        """Returns True if something was cleaned up."""
        return self.userVars.delete(self.numberedVar("path"))


class WordListFileItem(FileItem):
    """Stores information about a file to read from to make a word list."""

    FILE_COUNT_VAR = "datafile_count"

    def __init__(self, userVars):
        FileItem.__init__(self, userVars)
        self.filetype = ""
        self.writingSystem = ""
        self.thingsToGrab = []  # element type wordlist_structs.WhatToGrab
        self.includeMisspellings = True
        self.skipFirstRow = True  # first spreadsheet row has headings
        self.splitByWhitespace = True  # split into words
        self.grabnum = 0  # part of the user variable name

    def numberedVar(self, suffix=""):
        return "datafile" + FileItem.numberedVar(self, suffix)

    def varGrabNumStr(self):
        """Longer string enumerating each thing to grab for each file."""
        return "%02d" % self.grabnum

    def numberedGrabVar(self, suffix=""):
        """Get a user variable name that includes the file number and
        the grab number.
        :param suffix: Add this to the end of the string.
        """
        field_suffix = "f%s_%s" % (self.varGrabNumStr(), suffix)
        return self.numberedVar(field_suffix)

    def loadUserVars(self):
        filepath = self.userVars.get(self.numberedVar("path"))
        if not filepath:
            raise self.noUserVarData(self.numberedVar("path"))
        self.filepath = filepath
        self.filetype = self.userVars.get(self.numberedVar("type"))
        self.writingSystem = self.userVars.get(self.numberedVar("writingSys"))
        grabCount = self.userVars.getInt(self.numberedVar("grabCount"))
        for self.grabnum in range(grabCount):
            whatToGrab = wordlist_structs.WhatToGrab(self.userVars)
            whatToGrab.setPrefix(self.numberedGrabVar())
            whatToGrab.loadUserVars()
            self.thingsToGrab.append(whatToGrab)
        self.includeMisspellings = (
            self.userVars.getInt(self.numberedVar("includeMisspell")) == 1)
        self.skipFirstRow = (
            self.userVars.getInt(self.numberedVar("skipFirstRow")) == 1)
        self.splitByWhitespace = (
            self.userVars.getInt(self.numberedVar("splitPhrases")) == 1)

    def storeUserVars(self):
        """Sets the user vars for this item."""
        self.userVars.store(self.numberedVar("path"), self.filepath)
        self.userVars.store(self.numberedVar("type"), self.filetype)
        self.userVars.store(
            self.numberedVar("writingSys"), self.writingSystem)
        self.userVars.store(
            self.numberedVar("grabCount"), str(len(self.thingsToGrab)))
        self.userVars.store(
            self.numberedVar("includeMisspell"),
            str(int(self.includeMisspellings)))
        self.userVars.store(
            self.numberedVar("skipFirstRow"), str(int(self.skipFirstRow)))
        self.userVars.store(
            self.numberedVar("splitPhrases"), str(int(self.splitByWhitespace)))
        for self.grabnum, whatToGrab in enumerate(self.thingsToGrab):
            whatToGrab.setPrefix(self.numberedGrabVar())
            whatToGrab.storeUserVars()

        ## Delete unused variables

        self.grabnum = len(self.thingsToGrab)
        while True:
            whatToGrab = wordlist_structs.WhatToGrab(self.userVars)
            whatToGrab.setPrefix(self.numberedGrabVar())
            cleaned_up_something = whatToGrab.cleanupUserVars()
            if not cleaned_up_something:
                break
            self.grabnum += 1

    def cleanupUserVars(self):
        """Returns True if something was cleaned up."""
        cleaned_up_something1 = self.userVars.delete(self.numberedVar("path"))
        self.userVars.delete(self.numberedVar("type"))
        self.userVars.delete(self.numberedVar("grabCount"))
        self.userVars.delete(self.numberedVar("includeMisspell"))
        self.userVars.delete(self.numberedVar("skipFirstRow"))
        self.userVars.delete(self.numberedVar("splitPhrases"))
        MAX_CLEAN = 100  # should be more than enough
        for self.grabnum in range(0, MAX_CLEAN):
            whatToGrab = wordlist_structs.WhatToGrab(self.userVars)
            whatToGrab.setPrefix(self.numberedGrabVar())
            cleaned_up_something2 = whatToGrab.cleanupUserVars()
            if not cleaned_up_something2:
                break
        return cleaned_up_something1

    def getDeepCopy(self):
        """Returns a deep copy of self.
        Using copy.deepcopy() will fail to copy this object correctly.
        """
        newItem = self.__class__(self.userVars)
        newItem.filepath = self.filepath
        newItem.filetype = self.filetype
        newItem.writingSystem = self.writingSystem
        for whatToGrab in self.thingsToGrab:
            newItem.thingsToGrab.append(copy.copy(whatToGrab))
        newItem.includeMisspellings = self.includeMisspellings
        newItem.skipFirstRow = self.skipFirstRow
        newItem.splitByWhitespace = self.splitByWhitespace
        return newItem


class LingExFileItem(FileItem):
    """Stores information about a ling example file item in the list."""

    FILE_COUNT_VAR = "XML_fileCount"

    def __init__(self, userVars, filenum=0):
        FileItem.__init__(self, userVars, filenum)
        self.prefix = ""  # ref number prefix
        self.use_segnum = False  # use segnum field for ref num or autonumber

    def numberedVar(self, prefix=""):
        return prefix + self.varNumStr()

    def loadUserVars(self):
        filepath = self.userVars.get(self.numberedVar("XML_filePath"))
        prefix = self.userVars.get(self.numberedVar("XML_filePrefix"))
        if not filepath:
            raise self.noUserVarData(self.numberedVar("XML_filePath"))
        self.filepath = filepath
        self.setPrefixNoSpaces(prefix)
        self.use_segnum = bool(
            self.userVars.getInt(self.numberedVar("SegnumRefNumber")))

    def storeUserVars(self):
        """Sets the user vars for this item."""
        self.userVars.store(self.numberedVar("XML_filePath"), self.filepath)
        self.userVars.store(self.numberedVar("XML_filePrefix"), self.prefix)
        self.userVars.store(
            self.numberedVar("SegnumRefNumber"), str(int(self.use_segnum)))

    def cleanupUserVars(self):
        """Returns True if something was cleaned up."""
        deleted_all = True
        for varname in ("XML_filePath", "XML_filePrefix", "SegnumRefNumber"):
            if not self.userVars.delete(self.numberedVar(varname)):
                deleted_all = False
        return deleted_all

    def setPrefixNoSpaces(self, newFilePrefix):
        self.prefix = ""
        if not newFilePrefix:
            return
        # remove any spaces
        newFilePrefix = re.sub(r"\s", r"", newFilePrefix)
        self.prefix = newFilePrefix

    def __str__(self):
        """Overrides the base class method to add prefix."""
        itemtext = os.path.basename(self.filepath)
        if self.prefix:
            itemtext = "%s    %s" % (self.prefix, itemtext)
        return itemtext


class ItemList:
    """Maintains a list of items for an UNO listbox control."""

    ITEM_DESC_GENERIC = "an item"
    ITEM_DESC_SPECIFIC = "Item"

    def __init__(self):
        if self.__class__ is ItemList:
            # The base class should not be instantiated.
            raise NotImplementedError
        self.itemList = []  # an object for each listbox row
        self.changed = False  # the control needs updating when changed

    def __len__(self):
        return len(self.itemList)

    def __getitem__(self, index):
        """This method allows iteration over the list like __iter__
        as well as random access to elements.
        """
        return self.itemList[index]

    def getItemTextList(self):
        """Returns a list of strings."""
        logger.debug(util.funcName())
        return [str(item) for item in self]

    def sortItems(self):
        self.itemList.sort(key=lambda item: str(item).lower())

    def updateItem(self, itemPos, newItem):
        if self.alreadyContains(newItem, excludeItemPos=itemPos):
            raise self.alreadyInList()
        logger.debug("Updating item.")
        try:
            self.itemList[itemPos] = newItem
        except IndexError:
            raise self.noItemSelected()
        self.sortItems()
        self.changed = True

    def addItem(self, newItem, allowDuplicates=False):
        if not allowDuplicates:
            if self.alreadyContains(newItem):
                raise self.alreadyInList()
        logger.debug("Adding item.")
        self.itemList.append(newItem)
        self.sortItems()
        self.changed = True

    def alreadyContains(self, newItem, excludeItemPos=-1):
        """Make the list unique."""
        for itemPos, item in enumerate(self.itemList):
            if excludeItemPos > -1:
                if itemPos == excludeItemPos:
                    continue
            if item == newItem:
                return True
        return False

    def deleteItem(self, itemPos):
        logger.debug("Deleting item.")
        try:
            del self.itemList[itemPos]
        except IndexError:
            raise self.noItemSelected()
        self.changed = True

    def noItemSelected(self):
        return exceptions.ChoiceProblem(
            "Please select %s in the list." % self.ITEM_DESC_GENERIC)

    def alreadyInList(self):
        return exceptions.ChoiceProblem(
            "%s is already in the list." % self.ITEM_DESC_SPECIFIC)


class FileItemList(ItemList, Syncable):
    """Maintains a list of file items."""

    ITEM_DESC_GENERIC = "a file"
    ITEM_DESC_SPECIFIC = "File"

    def __init__(self, fileItemClass, userVars):
        """:param fileItemClass: type of items in self.itemList"""
        ItemList.__init__(self)
        Syncable.__init__(self, userVars)
        self.fileItemClass = fileItemClass

    def loadUserVars(self):
        """Loads from user vars into self.itemList."""
        logger.debug("Loading list from user vars.")
        self.itemList = []
        for filenum in range(0, self.makeNewItem().getNumFiles()):
            newItem = self.makeNewItem()
            newItem.setFilenum(filenum)
            try:
                newItem.loadUserVars()
                self.itemList.append(newItem)
            except exceptions.DataNotFoundError:
                pass
        self.sortItems()

    def storeUserVars(self):
        logger.debug(util.funcName('begin'))
        self.makeNewItem().setNumFiles(len(self))
        for filenum, aFileItem in enumerate(self.itemList):
            aFileItem.setFilenum(filenum)
            aFileItem.storeUserVars()

        ## Delete unused variables

        filenum = len(self.itemList)
        while True:
            cleanupItem = self.makeNewItem()
            cleanupItem.setFilenum(filenum)
            cleaned_up_something = cleanupItem.cleanupUserVars()
            if not cleaned_up_something:
                break
            filenum += 1
        logger.debug(util.funcName('end'))

    def makeNewItem(self):
        return self.fileItemClass(self.userVars)


class InterlinInputSettings(Syncable):
    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.fileList = FileItemList(LingExFileItem, self.userVars)
        self.showMorphLine1 = True
        self.showMorphLine2 = False
        self.separateMorphColumns = False
        self.SFM_baseline_word1 = True  # typically the \tx line

    def loadUserVars(self):
        self.fileList.loadUserVars()
        varname = "SFM_Baseline"
        if self.userVars.get(varname).lower() == "wordline2":
            self.SFM_baseline_word1 = False

    def storeUserVars(self):
        self.fileList.storeUserVars()
        varname = "SFM_Baseline"
        if self.SFM_baseline_word1:
            self.userVars.store(varname, "WordLine1")
        else:
            self.userVars.store(varname, "WordLine2")

    def loadOutputSettings(self, outconfig):
        """Param should be of type InterlinOutputSettings."""
        for attr in (
                'showMorphLine1', 'showMorphLine2', 'separateMorphColumns'):
            setattr(self, attr, getattr(outconfig, attr))
