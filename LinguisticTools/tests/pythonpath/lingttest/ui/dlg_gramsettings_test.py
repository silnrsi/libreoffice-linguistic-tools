# -*- coding: Latin-1 -*-
#
# This file created 27-Oct-2010 by Jim Kornelsen
#
# 11-May-13 JDK  Use testutil instead of inspection code here.
# 01-Mar-17 JDK  Word Line 1 and 2 instead of Orthographic and Text.

import logging
import unittest
import os

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent

from lingt.access.writer.uservars import UserVars
from lingt.ui.comp.gramsettings import DlgGramSettings
from lingt.utils import util

logger = logging.getLogger("lingttest.dlg_gramsettings_test")

def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'test1_enableDisable',
            'test2_enableDisable',
            'test3_enableDisable',
            'test4_interlinLines',
            'test5_fileList',
        ):
        suite.addTest(DlgGramSettingsTestCase(method_name))
    return suite

class DlgGramSettingsTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        testutil.modifyClass_showDlg(DlgGramSettings)

    @classmethod
    def setUpClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankWriterDoc(unoObjs)

    def setUp(self):
        logger.debug("DlgGramSettingsTestCase setUp()")
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        USERVAR_PREFIX = "LTg_"  # for LinguisticTools Grammar variables
        self.userVars = UserVars(
            USERVAR_PREFIX, self.unoObjs.document, logger)
        self.dlg = DlgGramSettings(self.unoObjs)

    def test1_enableDisable(self):
        # For this test, dialog should be set to its default settings.
        def useDialog(dummy_innerSelf):
            pass
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.dlgCtrls.enableDisable()
        self.assertEqual(
            self.dlg.dlgCtrls.chkMorphsSeparate.getModel().Enabled, True)
        self.assertEqual(
            self.dlg.dlgCtrls.chkPOS_aboveGloss.getModel().Enabled, False)

    def test2_enableDisable(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.chkMorphLine1.setState(0)
            innerSelf.dlgCtrls.chkPOS_Line.setState(1)
            innerSelf.dlgCtrls.chkOuterTable.setState(0)
            innerSelf.dlgCtrls.optTables.setState(0)
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.dlgCtrls.enableDisable()
        self.assertEqual(self.dlg.dlgCtrls.chkMorphLine1.getState(), 0)
        self.assertEqual(
            self.dlg.dlgCtrls.chkMorphLine1.getModel().Enabled, True)
        self.assertEqual(
            self.dlg.dlgCtrls.chkMorphsSeparate.getModel().Enabled, False)
        self.assertEqual(
            self.dlg.dlgCtrls.chkPOS_aboveGloss.getModel().Enabled, True)
        self.assertEqual(
            self.dlg.dlgCtrls.txtNumColWidth.getModel().Enabled, False)
        self.assertEqual(
            self.dlg.dlgCtrls.lblNumColWidth.getModel().Enabled, False)

    def test3_enableDisable(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.chkMorphLine1.setState(1)
            innerSelf.dlgCtrls.chkPOS_Line.setState(0)
            innerSelf.dlgCtrls.chkOuterTable.setState(1)
            innerSelf.dlgCtrls.optTables.setState(1)
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.dlgCtrls.enableDisable()
        self.assertEqual(
            self.dlg.dlgCtrls.chkMorphsSeparate.getModel().Enabled, True)
        self.assertEqual(
            self.dlg.dlgCtrls.chkPOS_aboveGloss.getModel().Enabled, False)
        self.assertEqual(
            self.dlg.dlgCtrls.txtNumColWidth.getModel().Enabled, True)
        self.assertEqual(
            self.dlg.dlgCtrls.lblNumColWidth.getModel().Enabled, True)

    def test4_interlinLines(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.chkWordLine1.setState(0)
            innerSelf.dlgCtrls.chkWordLine2.setState(1)
            innerSelf.dlgCtrls.chkMorphLine1.setState(1)
            innerSelf.dlgCtrls.chkMorphLine2.setState(1)
            innerSelf.dlgCtrls.chkPOS_Line.setState(1)
            innerSelf.dlgCtrls.optTables.setState(1)
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.assertEqual(self.dlg.dlgCtrls.chkPOS_Line.getState(), 1)
        self.assertEqual(self.dlg.dlgCtrls.chkWordLine2.getState(), 1)
        self.assertEqual(self.dlg.dlgCtrls.optFrames.getState(), 0)
        self.assertEqual(self.dlg.dlgCtrls.optTables.getState(), 1)
        self.dlg.evtHandler.actionPerformed(MyActionEvent("Ok"))
        self.dlg = None
        self.assertEqual(self.userVars.get("Method"), "tables")
        self.assertEqual(self.userVars.getInt("ShowPartOfSpeech"), 1)

    def test5_fileList(self):
        def useDialog(dummy_innerSelf):
            pass
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 0)
        filepath = os.path.join(util.TESTDATA_FOLDER, "testText1.xml")
        testutil.modifyFilePicker(filepath)
        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 1)
        self.assertEqual(len(self.dlg.fileItems), 1)

        filepath = os.path.join(util.TESTDATA_FOLDER, "testText2.xml")
        testutil.modifyFilePicker(filepath)
        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 2)
        self.assertEqual(len(self.dlg.fileItems), 2)
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getSelectedItemPos(), 1)

        filepath = os.path.join(util.TESTDATA_FOLDER, "a_testText3.xml")
        testutil.modifyFilePicker(filepath)
        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 3)
        self.assertEqual(len(self.dlg.fileItems), 3)
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getSelectedItemPos(), 0)

        self.dlg.dlgCtrls.listboxFiles.selectItemPos(1, True)    # testText1.xml
        self.dlg.dlgCtrls.txtPrefix.setText("PREF-")
        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileUpdate"))
        fileItem = self.dlg.fileItems[1]
        self.assertEqual(fileItem.prefix, "PREF-")
        self.assertEqual(str(fileItem), "PREF-    testText1.xml")

        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileRemove"))
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 2)
        self.assertEqual(len(self.dlg.fileItems), 2)
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getSelectedItemPos(), 1)
        fileItem = self.dlg.fileItems[1]
        self.assertEqual(str(fileItem), "testText2.xml")

        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileRemove"))
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 1)
        self.assertEqual(len(self.dlg.fileItems), 1)
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getSelectedItemPos(), 0)
        fileItem = self.dlg.fileItems[0]
        self.assertEqual(str(fileItem), "a_testText3.xml")

        self.dlg.evtHandler.actionPerformed(MyActionEvent("FileRemove"))
        self.assertEqual(self.dlg.dlgCtrls.listboxFiles.getItemCount(), 0)
        self.assertEqual(len(self.dlg.fileItems), 0)

    def tearDown(self):
        if self.dlg:
            if hasattr(self.dlg, "dlgDispose"):
                testutil.do_dispose(self.dlg)
                self.dlg = None

if __name__ == '__main__':
    testutil.run_suite(getSuite())
