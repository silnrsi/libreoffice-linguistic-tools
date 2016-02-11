# -*- coding: Latin-1 -*-
#
# This file created 11-Feb-2016 by Jim Kornelsen

"""
Tests the bulk conversion step 1 dialog.
Does not test the "Scan Files" button, because that goes beyond the UI.
"""
import logging
import unittest

from lingt.ui.comp.bulkconv import DlgBulkConversion
from lingt.ui.comp import bulkconv_step1

from lingttest.utils import testutil

logger = logging.getLogger("lingttest.dlg_bulkstep1_test")


def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'test1_',
            'test2_',
        ):
        suite.addTest(DlgBulkStep1TestCase(method_name))
    return suite


class DlgBulkStep1TestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        testutil.modifyClass_showDlg(DlgBulkConversion)

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()

    def runDlg(self, dispose):
        self.dlg = DlgBulkConversion(self.unoObjs)
        self.dlg.showDlg()
        self.evtHandler = self.dlg.evtHandler
        if dispose:
            testutil.do_dispose(self.dlg)
            self.dlg = None

    def test1(self):
        def useDialog(innerSelf):
            dlgCtrls = innerSelf.evtHandler.step1Ctrls
            stepForm = innerSelf.evtHandler.step1Form
            self.assertEqual(dlgCtrls.txtOutputTo.getText(), "")
            self.assertEqual(len(stepCtrls.fontItems), 0)
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "TbxIntJPDN60.xml")
            stepForm._addFile(filepath)
            dirname = os.path.dirname(filepath)
            #innerSelf.evtHandler.actionPerformed(
            #    MyActionEvent("FileUpdate"))
            self.assertEqual(dlgCtrls.txtOutputTo.getText(), dirname)
            self.assertEqual(len(stepCtrls.fontItems), 1)
        DlgBulkConversion.useDialog = useDialog
        #self.dlg.showDlg()
        self.runDlg(True)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
