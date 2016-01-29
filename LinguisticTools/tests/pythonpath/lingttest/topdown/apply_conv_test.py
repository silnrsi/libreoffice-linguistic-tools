# -*- coding: Latin-1 -*-
#
# This file created October 16, 2015 by Jim Kornelsen

"""
Test all features accessed by Apply Converter dialog controls.
Start from UI which calls App and Access layers (top-down).
"""
from __future__ import unicode_literals
import logging
import unittest

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent
from lingttest.topdown import dataconv_test

from lingt.access.calc import spreadsheet_output
from lingt.access.calc import spreadsheet_reader
from lingt.ui.comp.applyconv import DlgApplyConverter
from lingt.utils import util

logger = logging.getLogger("lingttest.applyconv_test")


def getSuite():
    testutil.modifyClass_showDlg(DlgApplyConverter)
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    suite.addTest(ApplyConvTestCase('test1'))
    return suite


class ApplyConvTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.calcUnoObjs = None
        self.dlg = None

    @classmethod
    def setUpClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankCalcSpreadsheet(unoObjs)

    def setUp(self):
        self.calcUnoObjs = testutil.unoObjsForCurrentSpreadsheet()
        self.dlg = DlgApplyConverter(self.calcUnoObjs)

    def runDlg(self, useDialog):
        DlgApplyConverter.useDialog = useDialog
        self.dlg = DlgApplyConverter(self.calcUnoObjs)
        try:
            self.dlg.showDlg()
        except testutil.MsgSentException:
            pass
        testutil.do_dispose(self.dlg)

    def test1(self):
        """This might be the one and only test for this class."""
        convName_caps = "capsTest.tec"
        convName_hex = "Any-Hex"
        self.addConverter(convName_caps)
        self.addConverter(convName_hex)
        originalStrings = ["aBc", "DeF"]
        dataSets = [
            (convName_caps, False, "A", "B", False, True),
            (convName_caps, False, "A", "B", False, False),
            (convName_caps, False, "B", "D", False, True),
            (convName_caps, True, "A", "B", True, True),
            (convName_hex, False, "B", "A", False, True),
            ]
        outputter = spreadsheet_output.SpreadsheetOutput(self.calcUnoObjs)
        reader = spreadsheet_reader.SpreadsheetReader(self.calcUnoObjs)
        for convName, reverse, sourceCol, targetCol, skipRow, doIt in dataSets:
            #print("[%s]" % convName)  # to see which data set we're on
            clear_sheet(self.calcUnoObjs)
            outputter.outputToColumn(sourceCol, originalStrings, skipRow)

            def useDialog(innerSelf):
                innerSelf.dlgCtrls.txtConverterName.setText(convName)
                innerSelf.dlgCtrls.chkDirectionReverse.setState(reverse)
                innerSelf.dlgCtrls.txtSourceCol.setText(sourceCol)
                innerSelf.dlgCtrls.txtTargetCol.setText(targetCol)
                innerSelf.dlgCtrls.chkSkipRow.setState(skipRow)
                if doIt:
                    innerSelf.evtHandler.actionPerformed(
                        MyActionEvent("Close_and_Convert"))
                else:
                    innerSelf.evtHandler.actionPerformed(
                        MyActionEvent("Cancel"))

            self.runDlg(useDialog)
            expectedResults = []
            for originalString in originalStrings:
                if convName == convName_hex:
                    expectedVal = "".join(
                        [dataconv_test.anyToHex(originalChar)
                         for originalChar in list(originalString)])
                elif reverse:
                    expectedVal = originalString.lower()
                else:
                    expectedVal = originalString.upper()
                if doIt:
                    expectedResults.append(expectedVal)
            resultStrings = reader.getColumnStringList(targetCol, skipRow)
            self.assertEqual(resultStrings, expectedResults)

    def addConverter(self, convName):
        dataconv_test.addConverter(
            convName, self.dlg.msgbox, self.dlg.userVars)

    def tearDown(self):
        # close() might throw exception, in which case try calling dispose().
        self.calcUnoObjs.document.close(True)
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)


def clear_sheet(calcUnoObjs, numRows=100):
    """Deletes rows of the current sheet."""
    calcUnoObjs.sheet.Rows.removeByIndex(0, numRows)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
