# -*- coding: Latin-1 -*-
#
# This file created 23-Oct-2010 by Jim Kornelsen
#
# 23-Apr-13 JDK  Font names are different on Linux.
# 29-Sep-15 JDK  Verify font name in test_scope2().

import logging
import platform
import unittest

from lingt.ui.comp.dataconv import DlgDataConversion

from lingttest.utils import testutil

logger = logging.getLogger("lingttest.dlg_dataconv_test")


def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'test_scope1',
            'test_scope2',
            'test_scope3',
            'test_scope4',
            'test_target1',
            'test_target2',
            'test_target3',
            'test_target4',
            'test_target5',
        ):
        suite.addTest(DlgDataConvTestCase(method_name))
    return suite


class DlgDataConvTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        testutil.modifyClass_showDlg(DlgDataConversion)

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.dlg = DlgDataConversion(self.unoObjs)

    def test_scope1(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.optScopeWholeDoc.setState(1)
            innerSelf.dlgCtrls.optScopeFont.setState(1)
            innerSelf.dlgCtrls.optScopeParaStyle.setState(1)
            innerSelf.dlgCtrls.optScopeCharStyle.setState(1)
            innerSelf.dlgCtrls.optScopeSFMs.setState(1)
            innerSelf.dlgCtrls.optScopeSelection.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.assertEqual(self.dlg.dlgCtrls.optScopeWholeDoc.getState(), 0)
        self.assertEqual(self.dlg.dlgCtrls.optScopeSelection.getState(), 1)
        self.assertEqual(self.dlg.dlgCtrls.optScopeFont.getState(), 0)
        self.assertEqual(self.dlg.dlgCtrls.optScopeParaStyle.getState(), 0)
        self.assertEqual(self.dlg.dlgCtrls.optScopeCharStyle.getState(), 0)
        self.assertEqual(self.dlg.dlgCtrls.optScopeSFMs.getState(), 0)
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichScope, "Selection")
        self.assertEqual(self.dlg.config.searchConfig.fontName, "")
        self.assertEqual(self.dlg.config.searchConfig.style, "")
        self.assertEqual(self.dlg.config.searchConfig.SFMs, "")

    def test_scope2(self):
        def useDialog(innerSelf):
            fillDefaultValues(innerSelf)
            innerSelf.dlgCtrls.optScopeFont.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichScope, 'Font')
        self.assertEqual(
            self.dlg.config.searchConfig.fontName, testutil.getDefaultFont())

    def test_scope3(self):
        def useDialog(innerSelf):
            fillDefaultValues(innerSelf)
            innerSelf.dlgCtrls.optScopeParaStyle.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichScope, 'ParaStyle')
        self.assertEqual(
            self.dlg.config.searchConfig.style,
            testutil.getDefaultStyle())

    def test_scope4(self):
        def useDialog(innerSelf):
            fillDefaultValues(innerSelf)
            innerSelf.dlgCtrls.optScopeCharStyle.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichScope, 'CharStyle')
        self.assertEqual(
            self.dlg.config.searchConfig.style,
            testutil.getDefaultStyle())

    def test_target1(self):

        ## Define a function to manipulate dialog controls
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.optTargetParaStyle.setState(1)
            innerSelf.dlgCtrls.optTargetCharStyle.setState(1)
        DlgDataConversion.useDialog = useDialog

        ## Now run the modified code
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "CharStyle")

    def test_target2(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.optTargetCharStyle.setState(1)
            innerSelf.dlgCtrls.optTargetParaStyle.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "ParaStyle")

    def test_target3(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.optTargetParaStyle.setState(1)
            innerSelf.dlgCtrls.optTargetFontComplex.setState(1)
            #for paraStyleName in ["Default Style", "Default"]:
            paraStyleName = testutil.getDefaultStyle()
            if paraStyleName in innerSelf.paraStyleNames:
                innerSelf.dlgCtrls.comboTargetParaStyle.setText(paraStyleName)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "ParaStyle")
        if platform.system() == "Windows":
            self.assertEqual(self.dlg.config.targetFont.fontName, "Mangal")
        else:
            self.assertEqual(
                #self.dlg.config.targetFont.fontName, "Lohit Hindi")
                self.dlg.config.targetFont.fontName, "FreeSans")
        self.assertEqual(self.dlg.config.targetFont.fontSize.size, 12.)

    def test_target4(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.optTargetParaStyle.setState(1)
            innerSelf.dlgCtrls.optTargetFontWestern.setState(1)
            innerSelf.dlgCtrls.comboTargetParaStyle.setText(
                "Preformatted Text")
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()

        self.assertEqual(self.dlg.config.whichTarget, "ParaStyle")
        if testutil.stored.getProductName() == "LibreOffice":
            self.assertEqual(
                self.dlg.config.targetFont.fontName, "Liberation Mono")
        elif platform.system() == "Windows":
            self.assertEqual(
                self.dlg.config.targetFont.fontName, "Courier New")
        else:
            self.assertEqual(
                self.dlg.config.targetFont.fontName, "DejaVu Sans Mono")
        self.assertEqual(self.dlg.config.targetFont.fontSize.size, 10.)

    def test_target5(self):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.optTargetFontOnly.setState(1)
            innerSelf.dlgCtrls.listTargetStyleFont.selectItem(
                "Arial Black", True)
            innerSelf.dlgCtrls.txtFontSize.setText("15")
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "FontOnly")
        self.assertEqual(self.dlg.config.targetFont.fontName, "Arial Black")
        self.assertEqual(self.dlg.config.targetFont.fontSize.size, 15.)

    def tearDown(self):
        if self.dlg:
            if hasattr(self.dlg, "dlgDispose"):
                testutil.do_dispose(self.dlg)


def fillDefaultValues(innerSelf):
    innerSelf.dlgCtrls.comboScopeFont.setText(testutil.getDefaultFont())
    defaultStyleName = testutil.getDefaultStyle()
    if defaultStyleName in innerSelf.paraStyleNames:
        innerSelf.dlgCtrls.comboScopeParaStyle.setText(defaultStyleName)
    if defaultStyleName in innerSelf.charStyleNames:
        innerSelf.dlgCtrls.comboScopeCharStyle.setText(defaultStyleName)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
