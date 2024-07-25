"""
Manage outputting to Calc.
"""
import logging
from com.sun.star.uno import RuntimeException

from lingt.app import exceptions
from lingt.utils import util

logger = logging.getLogger("lingt.access.spreadsheet_output")

class SpreadsheetOutput:
    """Sends output to the Calc spreadsheet."""
    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs

    def outputToColumn(self, colLetter, stringList, skipFirstRow=True):
        """Takes a list of strings."""
        logger.debug(util.funcName('begin'))

        chunkSize = 25  # make this value bigger or smaller for optimization
        for i1 in range(0, len(stringList), chunkSize):
            i2 = i1 + chunkSize - 1
            if i2 >= len(stringList):
                i2 = len(stringList) - 1

            data = []
            for i in range(i1, i2 + 1):
                data.append((stringList[i],))
            if skipFirstRow:
                offset = 2  # start at second row
            else:
                offset = 1
            row1 = str(i1 + offset)
            row2 = str(i2 + offset)
            rangeName = colLetter + row1 + ":" + colLetter + row2
            logger.debug(rangeName)
            logger.debug(repr(data))
            try:
                oRange = self.unoObjs.sheet.getCellRangeByName(rangeName)
                oRange.setDataArray(tuple(data))
            except RuntimeException:
                raise exceptions.DocAccessError()
        logger.debug(util.funcName('end'))

    def outputString(self, colLetter, row, strval):
        """This will probably work fine for numbers too."""
        cellName = "%s%d" % (colLetter, row)
        logger.debug("Writing '%s' to %s", strval, cellName)
        try:
            cell = self.unoObjs.sheet.getCellRangeByName(cellName)
            cell.setString(strval)
        except RuntimeException:
            raise exceptions.DocAccessError()

    def createSpreadsheet(self):
        """
        Create an empty calc spreadsheet.
        """
        logger.debug("opening new spreadsheet")
        newDoc = self.unoObjs.desktop.loadComponentFromURL(
            "private:factory/scalc", "_blank", 0, ())
        newDocObjs = self.unoObjs.getDocObjs(
            newDoc, doctype=util.UnoObjs.DOCTYPE_CALC)
        logger.debug(util.funcName('end'))
        return newDocObjs
