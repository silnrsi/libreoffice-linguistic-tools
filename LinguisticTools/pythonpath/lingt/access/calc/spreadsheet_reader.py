# -*- coding: Latin-1 -*-
#
# This file created Nov 17 2012 by Jim Kornelsen
#
# 20-Feb-13 JDK  Added getSpreadsheetReader() method.
# 01-Mar-13 JDK  Fixed bug: Don't skip second row if first row is empty.
# 01-Apr-13 JDK  Handle exceptions if document cannot be opened.
# 08-Apr-13 JDK  Add filepath arg to loadDoc.
# 15-Apr-13 JDK  queryContentCells() is faster than Cells enumeration.

"""
Manage reading data from a Calc spreadsheet.
"""

import logging
import os
import uno
from com.sun.star.sheet.CellFlags import VALUE as NUM_VAL, DATETIME, STRING
from com.sun.star.uno import RuntimeException

from lingt.access.common.file_reader import FileReader
from lingt.app import exceptions
from lingt.app.data import wordlist_structs
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.access.spreadsheet_reader")

class SpreadsheetReader:
    """Methods to read from an open spreadsheet."""

    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        theLocale.loadUnoObjs(calcUnoObjs)

    def getColumnStringList(self, colLetter, skipFirstRow):
        """Returns a list of strings.
        Stops when no more strings are below in that column.
        """
        logger.debug(util.funcName('begin'))

        colNum = ord(colLetter) - ord('A')
        try:
            oColumn = self.unoObjs.sheet.getColumns().getByIndex(colNum)
            logger.debug("Using column %s", oColumn.getName())
            oRanges = self.unoObjs.document.createInstance(
                "com.sun.star.sheet.SheetCellRanges")
            oRanges.insertByName("", oColumn)
            cellFlags = STRING | NUM_VAL | DATETIME   # any string or number
            oCellRanges = oRanges.queryContentCells(cellFlags)
            if oCellRanges.getCount() == 0:
                logger.debug("No data found.")
                return []
            rangeAddress = oCellRanges.getRangeAddresses()[-1]
            rowEnd = rangeAddress.EndRow + 1   # EndRow is 0-based
            logger.debug("Found data up to row %d", rowEnd)
            rowStart = 1
            if skipFirstRow:
                rowStart = 2
            listLen = rowEnd - rowStart + 1
        except RuntimeException:
            raise exceptions.DocAccessError()
        return self.getColumnStringListByLen(colLetter, skipFirstRow, listLen)

    def getColumnStringListByLen(self, colLetter, skipFirstRow, listLen):
        """Returns a list of length listLen of strings.
        Cells may be empty.
        """
        logger.debug(util.funcName('begin'))
        row1 = 1
        if skipFirstRow:
            row1 = 2
        row2 = row1 + listLen - 1
        if row2 < row1:
            logger.debug("Range too small to contain data.")
            return []
        rangeName = "%s%d:%s%d" % (colLetter, row1, colLetter, row2)
        logger.debug(rangeName)
        try:
            oRange = self.unoObjs.sheet.getCellRangeByName(rangeName)
            rowTuples = oRange.getDataArray()
        except RuntimeException:
            raise exceptions.DocAccessError()
        if len(rowTuples) == 0:
            logger.debug("Could not get data.")
            return []
        columnTuples = list(zip(*rowTuples))  # arrange the data by columns
        logger.debug(util.funcName('end'))
        return list(columnTuples[0])


class CalcFileReader(FileReader):
    """Use Calc to read a file such as .ods"""

    SUPPORTED_FORMATS = [
        ('spreadsheet', "Spreadsheet (.ods .xls .xlsx .csv) for Calc")]

    def __init__(self, genericUnoObjs):
        FileReader.__init__(self, genericUnoObjs)
        self.calcUnoObjs = None
        self.fileconfig = None

    def setFileConfig(self, fileconfig):
        self.fileconfig = fileconfig
        self.filepath = self.fileconfig.filepath

    def _initData(self):
        """Elements are of type wordlist_structs.WordInList."""
        self.data = []

    def _read(self):
        """Harvest data by grabbing word strings from one or more columns."""
        try:
            self.loadDoc(self.filepath)
        except (exceptions.FileAccessError, exceptions.DocAccessError):
            raise exceptions.FileAccessError(
                "Error reading file %s", self.filepath)
        reader = SpreadsheetReader(self.calcUnoObjs)
        self.progressBar.updatePercent(60)
        for whatToGrab in self.fileconfig.thingsToGrab:
            if whatToGrab.grabType == wordlist_structs.WhatToGrab.COLUMN:
                stringList = reader.getColumnStringList(
                    whatToGrab.whichOne, self.fileconfig.skipFirstRow)
                for text in stringList:
                    if text != "":
                        ## Add word
                        word = wordlist_structs.WordInList()
                        word.text = text
                        word.source = self.filepath
                        self.data.append(word)
        logger.debug("Setting visible.")
        self.calcUnoObjs.window.setVisible(True)

    def getSpreadsheetReader(self):
        """Use this method as an alternative to read().
        This is a more general approach for loading data, not just for
        harvesting data to make a word list.
        """
        if self.calcUnoObjs is None:
            return None
        return SpreadsheetReader(self.calcUnoObjs)

    def loadDoc(self, filepath):
        """Sets self.calcUnoObjs to a loaded Calc doc.
        File will open minimized if not already open.
        """
        logger.debug("Opening file %s", filepath)
        if not os.path.exists(filepath):
            raise exceptions.FileAccessError(
                "Cannot find file %s", filepath)
        fileUrl = uno.systemPathToFileUrl(os.path.realpath(filepath))
        uno_args = (
            util.createProp("Minimized", True),
        )
        newDoc = self.unoObjs.desktop.loadComponentFromURL(
            fileUrl, "_default", 0, uno_args)
        try:
            self.calcUnoObjs = self.unoObjs.getDocObjs(
                newDoc, doctype=util.UnoObjs.DOCTYPE_CALC)
        except AttributeError:
            raise exceptions.DocAccessError()
        self.calcUnoObjs.window.setVisible(True)  # otherwise it will be hidden
        logger.debug("Opened file.")
