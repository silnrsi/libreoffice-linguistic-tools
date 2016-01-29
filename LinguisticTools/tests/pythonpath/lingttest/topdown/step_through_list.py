# -*- coding: Latin-1 -*-
#
# This file created November 12, 2015 by Jim Kornelsen

"""
Exercise the Spelling Character Comparison and Spelling Step dialog controls,
and verify Calc contents.
"""
import logging
import unittest

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent

#from lingt.access.calc import spreadsheet_output
#from lingt.access.calc import spreadsheet_reader
from lingt.ui.comp.spellingadjustments import DlgSpellingAdjustments
from lingt.utils import util

logger = logging.getLogger("lingttest.step_through_list")


def getSuite():
    testutil.modifyClass_showDlg(DlgSpellingAdjustments)
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_checkboxes',
            #'test2_compareForm',
            #'test3_wordList',
        ):
        suite.addTest(CharCompareTestCase(method_name))
    for method_name in (
        ):
        suite.addTest(StepThroughTestCase(method_name))
    return suite


class CharCompareTestCase(unittest.TestCase):
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
        self.dlg = None

    def runDlg(self, useDialog, dispose=True):
        DlgSpellingAdjustments.useDialog = useDialog
        if self.dlg:
            testutil.do_dispose(self.dlg)
        self.dlg = DlgSpellingAdjustments(self.calcUnoObjs)
        try:
            self.dlg.showDlg()
        except testutil.MsgSentException:
            pass
        if dispose:
            testutil.do_dispose(self.dlg)
            self.dlg = None

    def test1_checkboxes(self):
        """Verify that all checkboxes affect the Characters to compare
        text box.
        """
        dataSets = [
            ('chkVowelLength', "CompareVowelLength",
             "\u0905  \u0906"),
            ('chkVowelGlides', "CompareVowelGlides",
             "\u0905  \u0910  \u0914"),
            ('chkNasals', "CompareNasals",
             "\u0919  \u091e  \u0923  \u0928  \u092e"),
            ('chkAspiration', "CompareAspiration",
             "\u0915  \u0916"),
            ('chkPOA', "ComparePOA",
             "\u0915  \u0916  \u0917  \u0918"),
            ('chkGeminates', "CompareGeminates",
             "\u0915  \u0915\u094d\u0915"),
            ('chkLiquids', "CompareLiquids",
             "\u0930  \u0932"),
            ]

        def useDialog(innerSelf):
            for dataSet in dataSets:
                ctrlname, varname, firstline_expected = dataSet
                innerSelf.dlgCtrls.comboScript.setText("DEVANAGARI")
                for chk in innerSelf.dlgCtrls.checkboxVarList:
                    chk.ctrl.setState(
                        chk.ctrl.getModel().Name == ctrlname)
                innerSelf.getFormResults()
                for chk in innerSelf.dlgCtrls.checkboxVarList:
                    self.assertEqual(
                        chk.varname == varname,
                        bool(innerSelf.userVars.getInt(chk.varname)),
                        msg=repr([chk.varname, varname]))
                innerSelf.updateCharCompOpts()
                ctrl = innerSelf.dlgCtrls.txtCharComp
                firstline = ctrl.getText().splitlines()[0]
                self.assertEqual(firstline, firstline_expected, msg=ctrlname)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("Close"))

        self.runDlg(useDialog)

    def test2_compareForm(self):
        """Verify other form controls."""
        pass

    def test3_wordList(self):
        """Verify changes in Calc contents."""
        pass

    def test1(self):
        pass
        #outputter = spreadsheet_output.SpreadsheetOutput(self.calcUnoObjs)
        #reader = spreadsheet_reader.SpreadsheetReader(self.calcUnoObjs)
        #for convName, reverse, sourceCol, targetCol, skipRow, doIt in dataSets:
        #    #print("[%s]" % convName)  # to see which data set we're on
        #    clear_sheet(self.calcUnoObjs)
        #    outputter.outputToColumn(sourceCol, originalStrings, skipRow)
        #    self.runDlg(useDialog)
        #    resultStrings = reader.getColumnStringList(targetCol, skipRow)
        #    self.assertEqual(resultStrings, expectedResults)

    def tearDown(self):
        # close() might throw exception, in which case try calling dispose().
        #self.calcUnoObjs.document.close(True)
        #unoObjs = testutil.unoObjsForCurrentDoc()
        #testutil.blankWriterDoc(unoObjs)
        pass


class StepThroughTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)


def clear_sheet(calcUnoObjs, numRows=100):
    """Deletes rows of the current sheet."""
    calcUnoObjs.sheet.Rows.removeByIndex(0, numRows)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
