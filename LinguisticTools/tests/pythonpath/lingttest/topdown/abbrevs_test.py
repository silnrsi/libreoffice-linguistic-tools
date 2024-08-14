"""
Test all features accessed by Abbreviations dialog controls.
Start from UI which calls App and Access layers (top-down).
"""
import logging
import unittest

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent, PARAGRAPH_BREAK

from lingt.ui.comp.abbrevs import DlgAbbreviations
from lingt.utils import util

logger = logging.getLogger("lingttest.topdown.abbrevs_test")

ABL_I = 4  # index of Ablative abbreviation in list

def getSuite():
    klass = DlgAbbreviations
    testutil.modifyClass_showDlg(klass)
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_listbox',
            'test2_search',
            'test3_insertList',
            'test4_listbox_updateAndSelect',
        ):
        suite.addTest(AbbrevsTestCase(method_name))
    return suite

class AbbrevsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankWriterDoc(unoObjs)

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.dlg = DlgAbbreviations(self.unoObjs)

    def runDlg(self, useDialog):
        DlgAbbreviations.useDialog = useDialog
        self.dlg.showDlg()
        testutil.do_dispose(self.dlg)

    def test1_listbox(self):
        """Verify that the list box showing abbreviations can be updated
        correctly.
        Make sure it works across calls as well, that is, when writing to and
        reading from user vars.
        """
        testutil.modifyMsgboxOkCancel(True)
        def useDialog_add_abl2(innerSelf):
            self.verifyItems(innerSelf, ABL_I, ["ABL   ablative"])
            updateAbbrev(innerSelf, "ABL2", "ablativ", 1)
            self.verifySelectedItem(innerSelf, ">  ABL2  ablativ")
            self.verifyItems(innerSelf, ABL_I + 1, ["ABS   absolutive"])
        self.runDlg(useDialog_add_abl2)

        def useDialog_add_abn(innerSelf):
            addAbbrev(innerSelf, "ABM", "abominableSnowman", 0)
            addAbbrev(innerSelf, "ABN", "abnegate", 1)
            expected_strings = [
                ">  ABL2  ablativ",
                "ABM   abominableSnowman",
                ">  ABN   abnegate",
                "ABS   absolutive"
                ]
            self.verifyItems(innerSelf, ABL_I, expected_strings)
            innerSelf.dlgCtrls.listboxAbbrevs.selectItemPos(ABL_I + 1, True)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("DeleteAbbrev"))
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("ChangeAllCaps"))
        self.runDlg(useDialog_add_abn)

        def useDialog_verify_lowercase(innerSelf):
            expected_strings = [
                ">  abl2  ablativ",
                ">  abn   abnegate",
                "abs   absolutive"
                ]
            self.verifyItems(innerSelf, ABL_I, expected_strings)
        self.runDlg(useDialog_verify_lowercase)

    def test2_search(self):
        """Test controls that search for new abbreviations."""
        testutil.modifyMsgboxYesNoCancel("yes")
        dataSets = [
            ("Quotations", 'any', 5, 0, ["DIG", "pig"]),
            ("Caption", 'any', 5, 0, ["BIG", "Fig"]),
            ("Quotations", 'any', 5, 1, ["DIG"]),
            ("Quotations", 'any', 6, 0, ["DIG", "pig", "wiggle"]),
            ("Quotations", 'suffix', 5, 0, ["DIG"]),
            ("Quotations", 'prefix', 5, 0, ["DIG", "pig"])]
        for dataSet in dataSets:
            self.setDocContentsForSearch()
            func = self.make_test2_useDialog(*dataSet)
            self.runDlg(func)

        ## Search from beginning

        self.setDocContentsForSearch()
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        oVC.goDown(1, False)
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.cmbxSearchParaStyle.setText("Caption")
            innerSelf.dlgCtrls.optSearchAny.setState(1)
            innerSelf.dlgCtrls.chkSearchUpperCase.setState(0)
            innerSelf.dlgCtrls.txtMaxSearchLength.setText("5")
            innerSelf.dlgCtrls.chkStartFromBeginning.setState(0)
            self.findAndAddNext(innerSelf, 0)
            innerSelf.dlgCtrls.chkStartFromBeginning.setState(1)
            self.findAndAddNext(innerSelf, 2)
        self.runDlg(useDialog)

    def make_test2_useDialog(self, paraStyle, affix, abbrevLen, upperCase,
                             displays):
        def useDialog(innerSelf):
            self.clear_list(innerSelf, ABL_I + 1)
            innerSelf.dlgCtrls.cmbxSearchParaStyle.setText(paraStyle)
            if affix == 'any':
                innerSelf.dlgCtrls.optSearchAny.setState(1)
            elif affix == 'suffix':
                innerSelf.dlgCtrls.optSearchSuffix.setState(1)
            elif affix == 'prefix':
                innerSelf.dlgCtrls.optSearchPrefix.setState(1)
            innerSelf.dlgCtrls.txtMaxSearchLength.setText(abbrevLen)
            innerSelf.dlgCtrls.chkSearchUpperCase.setState(upperCase)
            self.findAndAddNext(innerSelf, len(displays))
            expected_strings = ["+  " + display for display in displays]
            self.verifyItems(innerSelf, ABL_I + 1, expected_strings)
        return useDialog

    def test3_insertList(self):
        """
        Test scanning for occurrences and inserting the list into the document.
        """
        self.setDocContentsForSearch()
        oVC = self.unoObjs.viewcursor
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        def useDialog(innerSelf):
            self.clear_list(innerSelf, ABL_I + 1)
            addAbbrev(innerSelf, "DIG", "shovel action")
            self.verifySelectedItem(innerSelf, "DIG   shovel action")
            self.assertEqual(innerSelf.dlgCtrls.txtOccurrences.getText(), "0")
            innerSelf.evtHandler.actionPerformed(MyActionEvent("Rescan"))
            self.verifySelectedItem(innerSelf, "+  DIG   shovel action")
            self.assertEqual(innerSelf.dlgCtrls.txtOccurrences.getText(), "1")

            innerSelf.dlgCtrls.listboxAbbrevs.selectItemPos(ABL_I, True)
            self.assertEqual(innerSelf.dlgCtrls.chkForceOutput.getState(), 0)
            updateAbbrev(innerSelf, None, None, 1)
            self.verifySelectedItem(innerSelf, ">  ABL   ablative")
            self.assertEqual(innerSelf.dlgCtrls.txtOccurrences.getText(), "0")

            addAbbrev(innerSelf, "FIG", "tasty fruit to pick and eat", 0)

            innerSelf.evtHandler.actionPerformed(MyActionEvent("InsertList"))
        self.runDlg(useDialog)

        ## verify inserted list

        oVC.goUp(5, True)
        text = testutil.normalize_newlines(
            oVC.getString().strip())
        textExpected = testutil.normalize_newlines(
            "ABL\tablative\n"
            "DIG\tshovel action\n"
            "FIG\ttasty fruit to pick and eat")
        self.assertEqual(text, textExpected)
        oVC.goRight(0, False)   # deselect

    def test4_listbox_updateAndSelect(self):
        testutil.modifyMsgboxOkCancel(True)
        def useDialog(innerSelf):
            self.clear_list(innerSelf)
            addAbbrev(innerSelf, "I", "i")
            addAbbrev(innerSelf, "J", "j")
            addAbbrev(innerSelf, "K", "k")
            self.assertEqual(
                innerSelf.dlgCtrls.listboxAbbrevs.getItemCount(), 3)
            addAbbrev(innerSelf, "L", "l")
            innerSelf.dlgCtrls.txtAbbrev.setText("H")
            innerSelf.dlgCtrls.listboxAbbrevs.selectItemPos(1, True)
            innerSelf.viewAbbrev(True)
            self.assertEqual(
                innerSelf.dlgCtrls.listboxAbbrevs.getItemCount(), 4)
            self.verifySelectedItem(innerSelf, "J     j")
            innerSelf.dlgCtrls.listboxAbbrevs.selectItemPos(0, True)
            self.verifySelectedItem(innerSelf, "H     l")

            innerSelf.evtHandler.actionPerformed(MyActionEvent("AddAbbrev"))
            self.assertEqual(
                innerSelf.dlgCtrls.listboxAbbrevs.getItemCount(), 5)
            innerSelf.dlgCtrls.txtAbbrev.setText("M")
            innerSelf.dlgCtrls.txtFullName.setText("m")
            innerSelf.dlgCtrls.listboxAbbrevs.selectItemPos(4, True)
            innerSelf.viewAbbrev(True)
            self.assertEqual(
                innerSelf.dlgCtrls.listboxAbbrevs.getSelectedItemPos(), 3)
            expected_strings = [
                "H     l",
                "I     i",
                "J     j",
                "K     k",
                "M     m"]
            for listbox_index, listbox_value in enumerate(expected_strings):
                innerSelf.dlgCtrls.listboxAbbrevs.selectItemPos(
                    listbox_index, True)
                self.verifySelectedItem(innerSelf, listbox_value)

        self.runDlg(useDialog)

    def setDocContentsForSearch(self):
        testutil.blankWriterDoc(self.unoObjs)
        self.dlg = DlgAbbreviations(self.unoObjs)
        oVC = self.unoObjs.viewcursor
        oVC.setPropertyValue("ParaStyleName", "Caption")
        oVC.getText().insertString(oVC, "BIG Fig", 0)
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        oVC.setPropertyValue("ParaStyleName", "Quotations")
        oVC.getText().insertString(oVC, "pig-DIG-wiggle", 0)
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)

    def verifySelectedItem(self, dlg, displayStripped):
        logger.debug("hi there! %r", displayStripped)
        #print("listbox_value=" + repr(displayStripped))
        strDisplay = dlg.dlgCtrls.listboxAbbrevs.getSelectedItem()
        self.assertEqual(strDisplay.strip(), displayStripped)

    def verifyItems(self, dlg, listbox_start_index, expected_strings):
        """Verify a list of items in the listbox, and verify fields.
        Listbox strings are built from several values that are displayed in
        textbox and checkbox fields.
        To simplify testing, we can parse the string in order to figure out
        what the values of each field must have been.
        """
        for expected_index, listbox_value in enumerate(expected_strings):
            listbox_index = listbox_start_index + expected_index
            dlg.dlgCtrls.listboxAbbrevs.selectItemPos(listbox_index, True)
            self.verifySelectedItem(dlg, listbox_value)
            values = listbox_value.split()
            forceOutputDict = {">" : 1, "+" : 0}
            if values[0] in forceOutputDict:
                forceOutput = forceOutputDict[values[0]]
                values.pop(0)
            else:
                forceOutput = 0
            try:
                abbrevText, fullName = values
            except ValueError:
                try:
                    abbrevText = values[0]
                    fullName = ""
                except IndexError:
                    abbrevText = ""
                    fullName = ""
            self.assertEqual(dlg.dlgCtrls.txtAbbrev.getText(), abbrevText)
            self.assertEqual(dlg.dlgCtrls.txtFullName.getText(), fullName)
            self.assertEqual(
                dlg.dlgCtrls.chkForceOutput.getState(), forceOutput)

    def clear_list(self, dlg, start_index=0):
        """
        :param start_index: removes all items at start_index and higher
        """
        numToRemove = (
            dlg.dlgCtrls.listboxAbbrevs.getItemCount() - start_index)
        dlg.dlgCtrls.listboxAbbrevs.removeItems(
            start_index, numToRemove)
        for dummy in range(numToRemove):
            dlg.abbrevList.deleteItem(start_index)
        self.assertEqual(
            dlg.dlgCtrls.listboxAbbrevs.getItemCount(), start_index)

    def findAndAddNext(self, dlg, count):
        noMoreMsg = "No more possible abbreviations found."
        initialCount = dlg.dlgCtrls.listboxAbbrevs.getItemCount()
        try:
            for dummy in range(count + 1):
                dlg.evtHandler.actionPerformed(MyActionEvent("FindNext"))
        except testutil.MsgSentException as exc:
            dlg.evtHandler.handling_event = False
            self.assertEqual(exc.msg, noMoreMsg)
        else:
            self.fail("Expected error message.")
        self.assertEqual(
            dlg.dlgCtrls.listboxAbbrevs.getItemCount(), initialCount + count)

    def tearDown(self):
        self.dlg = None

    #@classmethod
    #def tearDownClass(cls):
    #    unoObjs = testutil.unoObjsForCurrentDoc()
    #    testutil.blankWriterDoc(unoObjs)

def addAbbrev(*args, **kwargs):
    dlg = args[0]
    dlg.evtHandler.actionPerformed(MyActionEvent("AddAbbrev"))
    updateAbbrev(*args, **kwargs)

def updateAbbrev(dlg, abbrevText, fullName, forceOutput=-1):
    if abbrevText is not None:
        dlg.dlgCtrls.txtAbbrev.setText(abbrevText)
    if fullName is not None:
        dlg.dlgCtrls.txtFullName.setText(fullName)
    if forceOutput > -1:
        dlg.dlgCtrls.chkForceOutput.setState(forceOutput)
    dlg.evtHandler.actionPerformed(MyActionEvent("UpdateAbbrev"))

if __name__ == '__main__':
    testutil.run_suite(getSuite())
