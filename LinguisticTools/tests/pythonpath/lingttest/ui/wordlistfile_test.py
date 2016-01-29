# -*- coding: Latin-1 -*-
#
# This file created October 17, 2015 by Jim Kornelsen
#
# 09-Dec-15 JDK  list.clear() does not work in python 2.
# 12-Dec-15 JDK  Use listbox_items() instead of getItems().

"""
Test the Word List File dialog.
Test that the form works, including controls, events, and changing values.
Also test dialog results, both passing input arguments and getting output.

Creates file temp.odt which can be manually deleted later.
"""
from __future__ import unicode_literals
import logging
import unittest
import os
# pylint: disable=import-error
import uno
# pylint: enable=import-error

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent
from lingttest.topdown import phonology_test

from lingt.app import exceptions
from lingt.app.fileitemlist import WordListFileItem
from lingt.app.lingex_structs import LingPhonExample
from lingt.app.wordlist_structs import WhatToGrab
from lingt.ui import dutil
from lingt.ui.dep.wordlistfile import DlgWordListFile
from lingt.ui.dep.writingsystem import DlgWritingSystem
from lingt.utils import util

logger = logging.getLogger("lingttest.wordlistfile_test")


def getSuite():
    for klass in DlgWordListFile, DlgWritingSystem:
        testutil.modifyClass_showDlg(klass)
    testutil.modifyMsgboxDisplay()
    testutil.modifyMsgboxOkCancel(True)
    suite = unittest.TestSuite()
    for method_name in (
            'test1_currentdoc',
            'test2_document',
            'test3_fieldtypes',
            'test4_spellingStatus',
            'test5_writingSystem',
            'test6_results',
        ):
        suite.addTest(WordListFileTestCase(method_name))
    return suite


class WordListFileTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.unoObjs = None
        self.dlg = None

    @classmethod
    def setUpClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankWriterDoc(unoObjs)

    def setUp(self):
        fileItem = WordListFileItem(None)
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.dlg = DlgWordListFile(fileItem, self.unoObjs, None)

    def runDlg(self, useDialog=None, dispose=False, fileItem=None):
        if not useDialog:

            def useDialog(dummy_innerSelf):
                pass

        DlgWordListFile.useDialog = useDialog
        if not fileItem:
            fileItem = WordListFileItem(None)
        if self.dlg:
            testutil.do_dispose(self.dlg)
        self.dlg = DlgWordListFile(fileItem, self.unoObjs, None)
        try:
            self.dlg.showDlg()
        except testutil.MsgSentException:
            pass
        if dispose:
            testutil.do_dispose(self.dlg)
            self.dlg = None

    def test1_currentdoc(self):
        """Test the current document button."""

        def useDialog(innerSelf):
            innerSelf.evtHandler.actionPerformed(MyActionEvent("UseCurrent"))

        testutil.clear_messages_sent()
        self.runDlg(useDialog)
        self.assertEqual(len(testutil.messages_sent), 1)
        self.assertEqual(
            testutil.messages_sent[0][0],
            "Please save the current document first.")
        self.assertEqual(self.dlg.dlgCtrls.fileControl.getText(), "")
        with self.assertRaises(exceptions.ChoiceProblem):
            itemPos = dutil.get_selected_index(
                self.dlg.dlgCtrls.listboxFileType)

        OUT_FILEPATH = os.path.join(util.BASE_FOLDER, "temp.odt")
        OUT_FILEURL = uno.systemPathToFileUrl(OUT_FILEPATH)
        self.unoObjs.document.storeAsURL(OUT_FILEURL, ())
        testutil.clear_messages_sent()
        self.runDlg(useDialog)
        self.assertEqual(len(testutil.messages_sent), 0)
        self.assertEqual(self.dlg.dlgCtrls.fileControl.getText(), OUT_FILEPATH)
        try:
            itemPos = dutil.get_selected_index(
                self.dlg.dlgCtrls.listboxFileType)
            self.assertEqual(itemPos, 0)
        except exceptions.ChoiceProblem:
            self.fail("Expected an item to be selected.")

    def test2_document(self):
        """Test adding and removing fields when file type is document."""
        self.runDlg()
        self.dlg.dlgCtrls.listboxFileType.selectItemPos(0, True)
        for ctrl in (
                self.dlg.dlgCtrls.lblWS,
                self.dlg.dlgCtrls.txtWS,
                self.dlg.dlgCtrls.btnSelectWS,
                self.dlg.dlgCtrls.lblSFM,
                self.dlg.dlgCtrls.txtSFM,
                self.dlg.dlgCtrls.checkboxMiss,
                self.dlg.dlgCtrls.checkboxSkipRow):
            self.assertFalse(ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
        for ctrl in (
                self.dlg.dlgCtrls.lblAddItem,
                self.dlg.dlgCtrls.lblWhatToGrab,
                self.dlg.dlgCtrls.listWhatToGrab,
                self.dlg.dlgCtrls.lblParaStyle,
                self.dlg.dlgCtrls.comboParaStyle,
                self.dlg.dlgCtrls.lblCharStyle,
                self.dlg.dlgCtrls.comboCharStyle,
                self.dlg.dlgCtrls.lblFont,
                self.dlg.dlgCtrls.comboFont,
                self.dlg.dlgCtrls.lblFields,
                self.dlg.dlgCtrls.listboxFields,
                self.dlg.dlgCtrls.optFontTypeWestern,
                self.dlg.dlgCtrls.optFontTypeComplex,
                self.dlg.dlgCtrls.optFontTypeAsian,
                self.dlg.dlgCtrls.btnAdd,
                self.dlg.dlgCtrls.btnRemove):
            self.assertTrue(ctrl.getModel().Enabled, msg=ctrl.getModel().Name)

        dataSets = [
            ("Whole Document", "listWhatToGrab", 1),
            ("Paragraph Style", "comboParaStyle", "My Para Style"),
            ("Character Style", "comboCharStyle", "My Char Style"),
            ("Font", "optFontTypeWestern", "My Western Font"),
            ("Font (Complex)", "optFontTypeComplex", "My Complex Font"),
            ("Font (Asian)", "optFontTypeAsian", "My Asian Font"),
            ]

        def useDialog(innerSelf):
            num_expected_fields = 0
            self.assertEqual(
                innerSelf.dlgCtrls.listboxFields.getItemCount(),
                num_expected_fields)
            for field_prefix, ctrl_name, field_val in dataSets:
                innerSelf.dlgCtrls.listboxFileType.selectItemPos(0, True)
                ctrl = getattr(innerSelf.dlgCtrls, ctrl_name)
                if ctrl_name.startswith("optFontType"):
                    innerSelf.dlgCtrls.comboFont.setText(field_val)
                    ctrl.setState(True)
                elif ctrl_name == "listWhatToGrab":
                    dutil.select_index(ctrl, field_val)
                else:
                    ctrl.setText(field_val)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("AddItem"))

                testutil.clear_messages_sent()
                self.assertEqual(
                    len(testutil.messages_sent), 0, msg=field_prefix)
                num_expected_fields += 1
                self.assertEqual(
                    innerSelf.dlgCtrls.listboxFields.getItemCount(),
                    num_expected_fields, msg=field_prefix)
                found_something = False
                for fieldItem in dutil.listbox_items(
                        innerSelf.dlgCtrls.listboxFields):
                    if fieldItem.startswith(field_prefix):
                        found_something = True
                        if field_prefix != "Whole Document":
                            self.assertIn(field_val, fieldItem)
                self.assertTrue(found_something)

            dutil.select_index(
                innerSelf.dlgCtrls.listboxFileType, FileType.DOC)
            for dummy in range(num_expected_fields):
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("RemoveItem"))
                num_expected_fields -= 1
                self.assertEqual(
                    innerSelf.dlgCtrls.listboxFields.getItemCount(),
                    num_expected_fields)

            testutil.clear_messages_sent()
            innerSelf.evtHandler.actionPerformed(MyActionEvent("AddItem"))
            self.assertEqual(
                testutil.messages_sent[0][0],
                "Please select or enter something to find.")
            num_expected_fields = 0
            self.assertEqual(
                innerSelf.dlgCtrls.listboxFields.getItemCount(),
                num_expected_fields)

        self.runDlg(useDialog)

    def test3_fieldtypes(self):
        """Test adding fields when file type is a typical xml 'field' type;
        for example \\tx marks a part of speech field.
        Also test spreadsheets since they use similar controls.
        """
        dataSets = [
            (FileType.SPREADSHEET, "Column", 1, "A"),
            (FileType.SPREADSHEET, "Column", 4, "D"),
            (FileType.TBX_PHON, "Field", 2, "Phonetic"),
            (FileType.PAXML, "Field", 3, "Phonemic"),
            (FileType.LIFT, "Field", 1, "Ref. Number"),
            (FileType.FLEX, "Field", 2, "Free Translation"),
            (FileType.TBX_INTERLIN, "Field", 4, "Orthographic"),
            (FileType.SFM, "SFM Marker", -1, "\\tx \\ge"),
            (FileType.SFM, "SFM Marker", -1, "mb ps"),
            ]
        for filetype, field_prefix, field_index, field_val in dataSets:

            def useDialog(innerSelf):
                dutil.select_index(
                    innerSelf.dlgCtrls.listboxFileType, filetype)
                if filetype == FileType.SFM:
                    innerSelf.dlgCtrls.txtSFM.setText(field_val)
                else:
                    dutil.select_index(
                        innerSelf.dlgCtrls.listWhatToGrab, field_index)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("AddItem"))

            self.runDlg(useDialog)
            self.assertEqual(
                self.dlg.dlgCtrls.listboxFields.getItemCount(), 1,
                msg=filetype)
            fieldItem = dutil.listbox_items(
                self.dlg.dlgCtrls.listboxFields)[0]
            self.assertEqual(fieldItem, "%s: %s" % (field_prefix, field_val))

            for ctrl in (
                    self.dlg.dlgCtrls.lblAddItem,
                    self.dlg.dlgCtrls.lblFields,
                    self.dlg.dlgCtrls.listboxFields,
                    self.dlg.dlgCtrls.btnAdd,
                    self.dlg.dlgCtrls.btnRemove):
                self.assertTrue(
                    ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
            for ctrl in (
                    self.dlg.dlgCtrls.lblParaStyle,
                    self.dlg.dlgCtrls.comboParaStyle,
                    self.dlg.dlgCtrls.lblCharStyle,
                    self.dlg.dlgCtrls.comboCharStyle,
                    self.dlg.dlgCtrls.lblFont,
                    self.dlg.dlgCtrls.comboFont,
                    self.dlg.dlgCtrls.optFontTypeWestern,
                    self.dlg.dlgCtrls.optFontTypeComplex,
                    self.dlg.dlgCtrls.optFontTypeAsian,
                    self.dlg.dlgCtrls.checkboxMiss):
                self.assertFalse(
                    ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
            for ctrl in (
                    self.dlg.dlgCtrls.lblWS,
                    self.dlg.dlgCtrls.txtWS,
                    self.dlg.dlgCtrls.btnSelectWS):
                if filetype == FileType.LIFT:
                    self.assertTrue(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
                else:
                    self.assertFalse(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
            for ctrl in (self.dlg.dlgCtrls.checkboxSkipRow,):
                if filetype == FileType.SPREADSHEET:
                    self.assertTrue(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
                else:
                    self.assertFalse(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
            for ctrl in (
                    self.dlg.dlgCtrls.lblWhatToGrab,
                    self.dlg.dlgCtrls.listWhatToGrab):
                if filetype == FileType.SFM:
                    self.assertFalse(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
                else:
                    self.assertTrue(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
            for ctrl in (
                    self.dlg.dlgCtrls.lblSFM,
                    self.dlg.dlgCtrls.txtSFM):
                if filetype == FileType.SFM:
                    self.assertTrue(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
                else:
                    self.assertFalse(
                        ctrl.getModel().Enabled, msg=ctrl.getModel().Name)

    def test4_spellingStatus(self):
        """Paratext spelling status XML does not use a list of fields."""

        def useDialog(innerSelf):
            dutil.select_index(
                innerSelf.dlgCtrls.listboxFileType, FileType.PARATEXT)

        self.runDlg(useDialog)
        for ctrl in (
                self.dlg.dlgCtrls.checkboxMiss,
                self.dlg.dlgCtrls.checkboxSplit):
            self.assertTrue(
                ctrl.getModel().Enabled, msg=ctrl.getModel().Name)
        for ctrl in (
                self.dlg.dlgCtrls.lblAddItem,
                self.dlg.dlgCtrls.lblWhatToGrab,
                self.dlg.dlgCtrls.listWhatToGrab,
                self.dlg.dlgCtrls.lblFields,
                self.dlg.dlgCtrls.listboxFields,
                self.dlg.dlgCtrls.btnAdd,
                self.dlg.dlgCtrls.btnRemove,
                self.dlg.dlgCtrls.lblParaStyle,
                self.dlg.dlgCtrls.comboParaStyle,
                self.dlg.dlgCtrls.lblCharStyle,
                self.dlg.dlgCtrls.comboCharStyle,
                self.dlg.dlgCtrls.lblFont,
                self.dlg.dlgCtrls.comboFont,
                self.dlg.dlgCtrls.optFontTypeWestern,
                self.dlg.dlgCtrls.optFontTypeComplex,
                self.dlg.dlgCtrls.optFontTypeAsian,
                self.dlg.dlgCtrls.lblWS,
                self.dlg.dlgCtrls.txtWS,
                self.dlg.dlgCtrls.btnSelectWS,
                self.dlg.dlgCtrls.lblSFM,
                self.dlg.dlgCtrls.txtSFM,
                self.dlg.dlgCtrls.checkboxSkipRow):
            self.assertFalse(ctrl.getModel().Enabled, msg=ctrl.getModel().Name)

    def test5_writingSystem(self):
        """Verify that the writing system field is working."""
        filepath = os.path.join(util.TESTDATA_FOLDER, "FWlexicon.lift")

        def useDialog(innerSelf):
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            dutil.select_index(
                innerSelf.dlgCtrls.listboxFileType, FileType.LIFT)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("SelectWritingSys"))

        wsDisplay = "Vette Kada Irula (iru)"
        wsCode = "iru"
        DlgWritingSystem.useDialog = phonology_test.useDialog_writingSys(
            self, wsDisplay, wsIndex=3)
        self.runDlg(useDialog)
        self.assertEqual(self.dlg.dlgCtrls.txtWS.getText(), wsCode)

    def test6_results(self):
        """Set the form contents and dlg.fileItem.
        Verify resulting dlg.fileItem and dlg.ok.
        """
        initial_param = WordListFileItem(None)
        initial_param.filepath = r"C:\a\b\c.lift"
        initial_param.filetype = 'lift'
        initial_param.writingSystem = "iru"
        whatToGrab = WhatToGrab(None)
        whatToGrab.grabType = WhatToGrab.FIELD
        whatToGrab.whichOne = "phm"
        initial_param.thingsToGrab.append(whatToGrab)
        initial_param.splitByWhitespace = False

        stuff_to_add = WordListFileItem(None)
        stuff_to_add.filepath = r"/home/user1/a/b/c.LIFT"
        stuff_to_add.filetype = 'lift'
        stuff_to_add.writingSystem = "iru-x-X_ETIC"
        whatToGrab = WhatToGrab(None)
        whatToGrab.grabType = WhatToGrab.FIELD
        whatToGrab.whichOne = "pht"
        stuff_to_add.thingsToGrab.append(whatToGrab)
        stuff_to_add.splitByWhitespace = False

        dataSets = [
            (action, param_filled, do_ok)
            for action in ('no change', 'add', 'remove')
            for param_filled in (False, True)
            for do_ok in (True, False)]
        for dataSet in dataSets:
            action, param_filled, do_ok = dataSet
            if param_filled:
                fileItem_in = initial_param.getDeepCopy()
            else:
                fileItem_in = WordListFileItem(None)
            fileItem_in_out = fileItem_in.getDeepCopy()

            def useDialog(innerSelf):
                # Verify that form contents matches fileItem_in.
                formValues = WordListFileItem(None)
                formValues.filepath = innerSelf.dlgCtrls.fileControl.getText()
                formValues.filetype = FileType.INDEX_TO_NAME[
                    innerSelf.dlgCtrls.listboxFileType.getSelectedItemPos()]
                formValues.writingSystem = innerSelf.dlgCtrls.txtWS.getText()
                for grabDisp in dutil.listbox_items(
                        innerSelf.dlgCtrls.listboxFields):
                    whatToGrab = WhatToGrab(None)
                    whatToGrab.grabType = WhatToGrab.FIELD
                    for field in LingPhonExample.GRAB_FIELDS:
                        whatToGrab_candidate = WhatToGrab(None)
                        whatToGrab_candidate.grabType = WhatToGrab.FIELD
                        whatToGrab_candidate.whichOne = field[0]
                        if grabDisp == str(whatToGrab_candidate):
                            whatToGrab.whichOne = field[0]
                    self.assertNotEqual(
                        whatToGrab.whichOne, "",
                        msg=("[Error: could not parse %s]" % grabDisp))
                    formValues.thingsToGrab.append(whatToGrab)
                formValues.includeMisspellings = bool(
                    innerSelf.dlgCtrls.checkboxMiss.getState())
                formValues.skipFirstRow = bool(
                    innerSelf.dlgCtrls.checkboxSkipRow.getState())
                formValues.splitByWhitespace = bool(
                    innerSelf.dlgCtrls.checkboxSplit.getState())
                assert_fileitems_equal(
                    formValues, fileItem_in, self, msg=repr(dataSet))

                if action == 'add':
                    innerSelf.dlgCtrls.fileControl.setText(
                        stuff_to_add.filepath)
                    dutil.select_index(
                        innerSelf.dlgCtrls.listboxFileType,
                        FileType.NAME_TO_INDEX[stuff_to_add.filetype])
                    innerSelf.dlgCtrls.txtWS.setText(
                        stuff_to_add.writingSystem)
                    innerSelf.addWhatToGrab(stuff_to_add.thingsToGrab[0])
                    innerSelf.dlgCtrls.checkboxMiss.setState(
                        stuff_to_add.includeMisspellings)
                    innerSelf.dlgCtrls.checkboxSkipRow.setState(
                        stuff_to_add.skipFirstRow)
                    innerSelf.dlgCtrls.checkboxSplit.setState(
                        stuff_to_add.splitByWhitespace)
                elif action == 'remove':
                    if innerSelf.dlgCtrls.listboxFields.getItemCount() > 0:
                        innerSelf.dlgCtrls.listboxFields.selectItemPos(0, True)
                        innerSelf.evtHandler.actionPerformed(
                            MyActionEvent("RemoveItem"))
                if do_ok:
                    innerSelf.evtHandler.actionPerformed(MyActionEvent("Ok"))
                else:
                    innerSelf.evtHandler.actionPerformed(
                        MyActionEvent("Cancel"))

            try:
                self.runDlg(useDialog, fileItem=fileItem_in_out)
                self.assertEqual(
                    self.dlg.getResult(), do_ok, msg=repr(dataSet))
                if action == 'no change' or not do_ok:
                    assert_fileitems_equal(
                        fileItem_in_out, fileItem_in, self, msg=repr(dataSet))
                elif action == 'add':
                    verifyItem = stuff_to_add.getDeepCopy()
                    if param_filled:
                        verifyItem.thingsToGrab = list(
                            initial_param.thingsToGrab)
                        verifyItem.thingsToGrab.extend(
                            stuff_to_add.thingsToGrab)
                    assert_fileitems_equal(
                        fileItem_in_out, verifyItem, self, msg=repr(dataSet))
                    assert_fileitems_notequal(
                        fileItem_in_out, fileItem_in, self, msg=repr(dataSet))
                elif action == 'remove':
                    verifyItem = fileItem_in.getDeepCopy()
                    del verifyItem.thingsToGrab[:]
                    assert_fileitems_equal(
                        fileItem_in_out, verifyItem, self, msg=repr(dataSet))
            finally:
                testutil.do_dispose(self.dlg)
                self.dlg = None

    def tearDown(self):
        if self.dlg:
            if hasattr(self.dlg, "dlgDispose"):
                testutil.do_dispose(self.dlg)
                self.dlg = None


class FileType:
    (DOC, SPREADSHEET, PARATEXT, LIFT, TBX_PHON, PAXML, FLEX, TBX_INTERLIN,
     SFM) = range(9)
    INDEX_TO_NAME = {
        -1 : "",
        DOC : 'writerdoc',
        LIFT : 'lift',
        TBX_PHON : 'tbxphn',
        PAXML : 'paxml',
        }
    NAME_TO_INDEX = {v: k for k, v in INDEX_TO_NAME.items()}


def assert_fileitems_notequal(fileItem1, fileItem2, testObj, msg=""):
    assert_fileitems_equal(
        fileItem1, fileItem2, testObj, expect=False, msg=msg)

def assert_fileitems_equal(fileItem1, fileItem2, testObj, expect=True, msg=""):
    """Check if two file items are equal.
    :param expect: true to expect they equal, false to expect they do not
    """
    values = []
    if expect:
        assertFunc = testObj.assertEqual
    else:

        def append_ignore_kwargs(*args, **dummy_kwargs):
            values.append(args)

        assertFunc = append_ignore_kwargs

    assertFunc(fileItem1.filepath, fileItem2.filepath, msg=msg)
    assertFunc(fileItem1.filetype, fileItem2.filetype, msg=msg)
    assertFunc(fileItem1.writingSystem, fileItem2.writingSystem, msg=msg)
    assertFunc(
        len(fileItem1.thingsToGrab), len(fileItem2.thingsToGrab), msg=msg)
    for pair in zip(fileItem1.thingsToGrab, fileItem2.thingsToGrab):
        assertFunc(str(pair[0]), str(pair[1]), msg=msg)
    assertFunc(
        fileItem1.includeMisspellings, fileItem2.includeMisspellings, msg=msg)
    assertFunc(fileItem1.skipFirstRow, fileItem2.skipFirstRow, msg=msg)
    assertFunc(
        fileItem1.splitByWhitespace, fileItem2.splitByWhitespace, msg=msg)
    if not expect:
        # If any values do not match, then we have succeeded.
        for pair in values:
            if pair[0] != pair[1]:
                return
        testObj.fail(msg=msg)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
