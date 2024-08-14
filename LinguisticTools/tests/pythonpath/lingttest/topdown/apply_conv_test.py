"""
Test all features accessed by Apply Converter dialog controls.
Start from UI which calls App and Access layers (top-down).
"""
from __future__ import unicode_literals
import collections
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
        testutil.blankSpreadsheet(unoObjs)

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
        Test1Data = collections.namedtuple('Test1Data', [
            'convName', 'reverse', 'sourceCol', 'targetCol',
            'skipRow', 'doIt'])
        dataSets = [
            Test1Data(convName_caps, False, "A", "B", False, True),
            Test1Data(convName_caps, False, "A", "B", False, False),
            Test1Data(convName_caps, False, "B", "D", False, True),
            Test1Data(convName_caps, True, "A", "B", True, True),
            Test1Data(convName_hex, False, "B", "A", False, True),
            ]
        outputter = spreadsheet_output.SpreadsheetOutput(self.calcUnoObjs)
        reader = spreadsheet_reader.SpreadsheetReader(self.calcUnoObjs)
        for dataSet in dataSets:
            self._test1_do_dataSet(dataSet, reader, outputter)

    def _test1_do_dataSet(self, data, reader, outputter):
        #print("[%s]" % data.convName)  # to see which data set we're on
        clear_sheet(self.calcUnoObjs)
        originalStrings = ["aBc", "DeF"]
        outputter.outputToColumn(
            data.sourceCol, originalStrings, data.skipRow)

        def useDialog(innerSelf):
            innerSelf.dlgCtrls.txtConverterName.setText(data.convName)
            innerSelf.dlgCtrls.chkDirectionReverse.setState(data.reverse)
            innerSelf.dlgCtrls.txtSourceCol.setText(data.sourceCol)
            innerSelf.dlgCtrls.txtTargetCol.setText(data.targetCol)
            innerSelf.dlgCtrls.chkSkipRow.setState(data.skipRow)
            if data.doIt:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("Close_and_Convert"))
            else:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("Cancel"))
        self.runDlg(useDialog)

        expectedResults = []
        for originalString in originalStrings:
            convName_hex = "Any-Hex"
            if data.convName == convName_hex:
                expectedVal = "".join(
                    [dataconv_test.anyToHex(originalChar)
                     for originalChar in list(originalString)])
            elif data.reverse:
                expectedVal = originalString.lower()
            else:
                expectedVal = originalString.upper()
            if data.doIt:
                expectedResults.append(expectedVal)
        resultStrings = reader.getColumnStringList(
            data.targetCol, data.skipRow)
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
