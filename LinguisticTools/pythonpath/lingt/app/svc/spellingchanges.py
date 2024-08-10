"""
Make spelling changes.

This module exports:
    getChangeList()
    ChangerMaker
"""
import logging

from lingt.access.calc import spreadsheet_reader
from lingt.access.text.cct_writer import CCT_Writer
from lingt.access.text.xslt_writer import XSLT_Writer
from lingt.app import exceptions
from lingt.app.data.wordlist_structs import ColumnOrder
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.progressbar import ProgressBar
from lingt.utils import util

logger = logging.getLogger("lingt.app.ChangerMaker")

def getChangeList(calcUnoObjs, columnOrder):
    """Grabs a 'from' and 'to' list of words."""
    colLetterWord = columnOrder.getColLetter('colWord')
    colLetterCorrection = columnOrder.getColLetter('colChange')
    reader = spreadsheet_reader.SpreadsheetReader(calcUnoObjs)
    listFrom = reader.getColumnStringList(colLetterWord, skipFirstRow=True)
    listTo = reader.getColumnStringListByLen(
        colLetterCorrection, True, len(listFrom))
    changeList = []
    for fromVal, toVal in zip(listFrom, listTo):
        if (not fromVal) or (not toVal) or (toVal == fromVal):
            continue
        changeList.append([fromVal, toVal])
    return changeList

class ChangerMaker:
    """Save a CC table or XSLT file from data in the spreadsheet."""

    def __init__(self, calcUnoObjs, userVars):
        self.unoObjs = calcUnoObjs
        self.userVars = userVars
        self.msgbox = MessageBox(self.unoObjs)
        self.filepath = ""
        self.matchPartial = False
        self.exportType = ""
        self.xpathExprs = ""
        self.sfMarkers = ""

    def setFilepath(self, newVal):
        self.filepath = newVal

    def setExportType(self, newVal):
        self.exportType = newVal

    def setSFM(self, newVal):
        self.sfMarkers = newVal

    def setMatchPartial(self, newVal):
        self.matchPartial = newVal

    def setXpathExprs(self, newVal):
        """Value should be an iterable containing strings."""
        self.xpathExprs = newVal

    def make(self):
        logger.debug(util.funcName('begin'))
        progressBar = ProgressBar(self.unoObjs, "Getting data...")
        progressBar.show()
        progressBar.updateBeginning()
        try:
            columnOrder = ColumnOrder(self.userVars)
            columnOrder.loadUserVars()
            changeList = getChangeList(self.unoObjs, columnOrder)
            progressBar.updateFinishing()
        except exceptions.DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
        progressBar.close()
        progressBar = ProgressBar(self.unoObjs, "Saving file...")
        progressBar.show()
        progressBar.updatePercent(50)
        if self.exportType == "ReplacementCCT":
            outputter = CCT_Writer(self.filepath)
            outputter.writeSimpleReplacements(changeList)
        elif self.exportType == "SFM_CCT":
            outputter = CCT_Writer(self.filepath)
            outputter.writeComplete(changeList, self.sfMarkers)
        elif self.exportType == "XSLT":
            outputter = XSLT_Writer(self.filepath)
            outputter.write(changeList, self.xpathExprs, self.matchPartial)
        progressBar.updateFinishing()
        progressBar.close()
        logger.debug(util.funcName('end'))
