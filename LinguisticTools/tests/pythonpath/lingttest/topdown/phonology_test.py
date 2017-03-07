# -*- coding: Latin-1 -*-
#
# This file created April 26, 2013 by Jim Kornelsen
#
# 05-Jul-13 JDK  Choose whether lexeme is phonetic or phonemic.
# 26-Oct-15 JDK  Move useDialog_writingSys() so other modules can use it.

# pylint: disable=no-self-use

"""
Test all features accessed by Phonology Settings dialog controls.
Start from UI which calls App and Access layers (top-down).
"""
import collections
import os
import unittest

from lingt.ui.comp.grabex import DlgGrabExamples
from lingt.ui.comp.phonsettings import DlgPhonSettings
from lingt.ui.dep.writingsystem import DlgWritingSystem
from lingt.utils import util
from lingt.utils.locale import Locale

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent, PARAGRAPH_BREAK

def getSuite():
    for klass in DlgPhonSettings, DlgWritingSystem, DlgGrabExamples:
        testutil.modifyClass_showDlg(klass)
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_flexSettings',
            'test2_nonLIFT',
            'test3_surroundings',
            'test4_settingsOptions',
            'test5_updating',
        ):
        suite.addTest(PhonologyTestCase(method_name))
    return suite

class PhonologyTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        testutil.verifyRegexMethods(self)
        self.surroundNum = 0  # number for surroundings

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.locale = Locale()
        testutil.blankWriterDoc(self.unoObjs)
        self.dlgSettings = None
        self.dlgGrabEx = None

    def runDlgSettings(self, dispose):
        self.dlgSettings = DlgPhonSettings(self.unoObjs)
        self.dlgSettings.showDlg()
        if dispose:
            testutil.do_dispose(self.dlgSettings)
            self.dlgSettings = None

    def runDlgGrabEx(self, dispose):
        self.dlgGrabEx = DlgGrabExamples("phonology", self.unoObjs)
        self.dlgGrabEx.showDlg()
        if dispose:
            testutil.do_dispose(self.dlgGrabEx)
            self.dlgGrabEx = None

    def test1_flexSettings(self):
        """Verify that selecting a writing system from the WS dialog works
        correctly, and that it correctly changes the example produced.
        Do likewise for selecting lexeme as phonetic or phonemic.
        """
        self._test1_lexPhonemic()
        self._test1_lexPhonetic()

    def _test1_lexPhonemic(self):
        """Lexeme Phonemic, Pronunciation Phonetic"""

        def useDialog(innerSelf):
            filepath = os.path.join(util.TESTDATA_FOLDER, "FWlexicon.lift")
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("SelectWritingSys"))
            innerSelf.dlgCtrls.optionLexemePhm.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        DlgPhonSettings.useDialog = useDialog
        DlgGrabExamples.useDialog = useDialog_insertEx("JPDN21.4")

        # Here is a quick line to get hex code points of unicode string s:
        # for c in s: print hex(ord(c))
        Test1AData = collections.namedtuple('Test1AData', [
            'wsDisplay', 'wsIndex', 'wsCode', 'phm'])
        dataSets = [
            Test1AData(
                # IPA
                "Irula (Phonetic) (iru-x-X_ETIC)", 2, "iru-x-X_ETIC",
                u"amman"),
            Test1AData(
                # Tamil script
                "Vette Kada Irula (iru)", 3, "iru",
                u"\u0b85\u0bae\u0bcd\u0bae\u0bc6"), # Tamil /amme/
            Test1AData(
                "(none)", 0, "",
                u"\u0b85\u0bae\u0bcd\u0bae\u0bc6")]  # Tamil /amme/
        pht = u"amm\u025b"
        for data in dataSets:
            DlgWritingSystem.useDialog = useDialog_writingSys(
                self, data.wsDisplay, data.wsIndex)
            self.runDlgSettings(False)
            self.assertEqual(
                self.dlgSettings.dlgCtrls.txtWritingSys.getText(), data.wsCode)
            testutil.do_dispose(self.dlgSettings)
            self.runDlgGrabEx(True)
            self.verifyString(1, data.phm)
            self.verifyString(2, pht)
            self.verifyString(3, "father")
            self.verifyString(4, "JPDN21.4")

    def _test1_lexPhonetic(self):
        """Lexeme Phonetic, Citation Phonemic"""

        def useDialog(innerSelf):
            filepath = os.path.join(util.TESTDATA_FOLDER, "FWlexicon.lift")
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("SelectWritingSys"))
            innerSelf.dlgCtrls.optionLexemePht.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        DlgPhonSettings.useDialog = useDialog
        DlgGrabExamples.useDialog = useDialog_insertEx("JPDN21.4")
        Test1BData = collections.namedtuple('Test1BData', [
            'wsDisplay', 'wsIndex', 'wsCode', 'pht', 'phm'])
        dataSets = [
            Test1BData(
                # IPA
                "Irula (Phonetic) (iru-x-X_ETIC)", 2, "iru-x-X_ETIC",
                u"amman",
                u"ammanCitForm"),
            Test1BData(
                # Tamil script
                "Vette Kada Irula (iru)", 3, "iru",
                u"\u0b85\u0bae\u0bcd\u0bae\u0bc6",  # Tamil /amme/
                u"\u0b85\u0bae\u0bcd\u0bae\u0bc7"),  # Tamil /ammee/
            Test1BData(
                "(none)", 0, "",
                u"\u0b85\u0bae\u0bcd\u0bae\u0bc6",  # Tamil /amme/
                u"\u0b85\u0bae\u0bcd\u0bae\u0bc7")]  # Tamil /ammee/
        for data in dataSets:
            DlgWritingSystem.useDialog = useDialog_writingSys(
                self, data.wsDisplay, data.wsIndex)
            self.runDlgSettings(False)
            self.assertEqual(
                self.dlgSettings.dlgCtrls.txtWritingSys.getText(), data.wsCode)
            testutil.do_dispose(self.dlgSettings)
            self.runDlgGrabEx(True)
            self.verifyString(1, data.phm)
            self.verifyString(2, data.pht)
            self.verifyString(3, "father")
            self.verifyString(4, "JPDN21.4")

    def test2_nonLIFT(self):
        """Verify that toolbox and paxml files are read correctly.
        Make sure that non-lift files do not show the WS dialog.
        """
        Test2Data = collections.namedtuple('Test2Data', [
            'filename', 'refNum', 'phm', 'pht', 'ge'])
        dataSets = [
            Test2Data(
                "TbxPhonCorpus.xml", "JPDN37.6", u"a\u0256upa",
                u"a\u0256\u0268pa", "kitchen.stove"),
            Test2Data(
                "TbxPhonCorpus.xml", "JPDN37.4", u"pane", u"pæne",
                "vessel.to.store.rice"),
            Test2Data(
                "PAdata.paxml", "JPDN23.1", u"mat\u0283t\u0283æ",
                u"m\u0259t\u0283\u025b", "unmarried cousin"),
            Test2Data(
                "PAdata.paxml", "JPDN58.02", u"bod\u032ae", u"boðe",
                "bush")]
        for data in dataSets:
            useDialog = self._test2_make_useDialog(data)
            DlgPhonSettings.useDialog = useDialog
            DlgGrabExamples.useDialog = useDialog_insertEx(data.refNum)
            self.runDlgSettings(False)
            wsCode = self.dlgSettings.dlgCtrls.txtWritingSys.getText()
            self.assertEqual(wsCode, "")
            testutil.do_dispose(self.dlgSettings)
            self.runDlgGrabEx(True)
            self.verifyString(1, data.phm)
            self.verifyString(2, data.pht)
            self.verifyString(3, data.ge)

    def _test2_make_useDialog(self, data):
        def useDialog(innerSelf):
            filepath = os.path.join(util.TESTDATA_FOLDER, data.filename)
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            try:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("SelectWritingSys"))
            except testutil.MsgSentException as exc:
                liftErrorMsg = self.locale.getText(
                    "If you want to use LIFT data, then first specify a "
                    "LIFT file exported from FieldWorks.")
                self.assertEqual(exc.msg, liftErrorMsg)
            else:
                self.fail("Expected error message.")
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def test3_surroundings(self):
        """Test inserting and replacing examples, verifying that the
        examples are outputted where expected, checking the preceeding and
        following spacing, formatting and text.
        """
        useDialog = self._test3_make_useDialog_phonSettings()
        DlgPhonSettings.useDialog = useDialog
        self.runDlgSettings(True)
        for action in 'inserting', 'replacing':
            refNum = "JPDN37.4"
            useDialog = self._test3_make_useDialog_grabExamples(action, refNum)
            DlgGrabExamples.useDialog = useDialog
            self._test3_do_grabExamples(action, refNum)

    def _test3_make_useDialog_phonSettings(self):
        def useDialog(innerSelf):
            filepath = os.path.join(util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test3_make_useDialog_grabExamples(self, action, refNum):
        def useDialog(innerSelf):
            if action == 'inserting':
                innerSelf.dlgCtrls.txtRefnum.setText(refNum)
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("InsertEx"))
            elif action == 'replacing':
                try:
                    innerSelf.evtHandler.actionPerformed(
                        MyActionEvent("ReplaceAll"))
                except testutil.MsgSentException as exc:
                    self.assertTrue(exc.msg.startswith("Replaced"))
                else:
                    self.fail("Expected error message.")
        return useDialog

    def _test3_do_grabExamples(self, action, refNum):
        firstStr = u"pane"
        oVC = self.unoObjs.viewcursor
        for blankLine in True, False:
            for attrName, attrVal in [
                    ('Default', ""),
                    ('ParaStyleName', "Caption"),
                    ('CharStyleName', "Caption characters"),
                    ('CharFontName', "Arial Black")]:
                if attrName != 'Default':
                    oVC.setPropertyValue(attrName, attrVal)
                self._test3_grabExInSurroundings(
                    action, blankLine, refNum, firstStr)
                if attrName == 'Default':
                    self.assertEqual(
                        oVC.getPropertyValue('ParaStyleName'), "Standard")
                    self.assertEqual(
                        oVC.getPropertyValue('CharStyleName'), "")
                    self.assertEqual(
                        oVC.getPropertyValue('CharFontName'),
                        testutil.getDefaultFont())
                else:
                    self.assertEqual(oVC.getPropertyValue(attrName), attrVal)
                if blankLine:
                    oVC.goDown(1, False)
                oVC.gotoEndOfLine(False)
                oVC.getText().insertControlCharacter(
                    oVC, PARAGRAPH_BREAK, False)
                oVC.setPropertyValue('ParaStyleName', "Standard")
                oVC.setPropertyToDefault('CharStyleName')
                oVC.setPropertyToDefault('CharFontName')

    def _test3_grabExInSurroundings(self, action, blankLine, refNum, firstStr):
        self._test3_insertSurroundings(action, refNum, blankLine)
        self.runDlgGrabEx(True)
        self.verifyString(1, firstStr)
        self._test3_verify_surroundings(blankLine, action)

    def _test3_insertSurroundings(self, action, refNum, blankLine):
        oVC = self.unoObjs.viewcursor
        self.surroundNum += 1
        numStr = str(self.surroundNum)
        oVC.getText().insertString(oVC, "begin" + numStr, False)
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        if action == 'replacing':
            oVC.getText().insertString(oVC, "#" + refNum, False)
            if not blankLine:
                oVC.getText().insertString(oVC, " ", False)
        if blankLine:
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        oVC.getText().insertString(oVC, "end" + numStr, False)
        if blankLine:
            oVC.goUp(1, False)
        else:
            oVC.gotoStartOfLine(False)

    def _test3_verify_surroundings(self, blankLine, action):
        """Verify that beginning and ending strings were not changed."""
        oVC = self.unoObjs.viewcursor
        oVC.goUp(2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        numStr = str(self.surroundNum)
        self.assertEqual(oVC.getString(), "begin" + numStr)
        oVC.goDown(2, False)
        if blankLine and action == 'inserting':
            oVC.goDown(1, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.assertEqual(oVC.getString(), "end" + numStr)
        if blankLine and action == 'inserting':
            oVC.goUp(1, False)

    def test4_settingsOptions(self):
        """Test phonology checkboxes and radio buttons."""
        oVC = self.unoObjs.viewcursor
        pht = u"age"  # phonetic
        phm = u"agge"  # phonemic
        for phonemicFirst in True, False:
            for brackets in True, False:
                useDialog = self._test4_make_useDialog(phonemicFirst, brackets)
                DlgPhonSettings.useDialog = useDialog
                DlgGrabExamples.useDialog = useDialog_insertEx("JPDN21.3")
                self.runDlgSettings(True)
                self.runDlgGrabEx(True)
                oVC.goUp(1, False)
                oVC.gotoStartOfLine(False)
                oVC.gotoEndOfLine(True)
                sVC = oVC.getString()
                oVC.goDown(1, False)
                if brackets:
                    if phonemicFirst:
                        self.assertRegex(sVC, r"^.+/.+/.+\[.+\].+'.+'.+$")
                        self.verifyString(1, phm)
                        self.verifyString(2, pht)
                    else:
                        self.assertRegex(sVC, r"^.+\[.+\].+/.+/.+'.+'.+$")
                        self.verifyString(1, pht)
                        self.verifyString(2, phm)
                else:
                    self.assertNotRegex(sVC, r"/|\[|\]|'")
                    if phonemicFirst:
                        self.assertRegex(sVC, phm + r".+" + pht)
                    else:
                        self.assertRegex(sVC, pht + r".+" + phm)

    def _test4_make_useDialog(self, phonemicFirst, brackets):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            if phonemicFirst:
                innerSelf.dlgCtrls.optionPhonemicFirst.setState(1)
            else:
                innerSelf.dlgCtrls.optionPhoneticFirst.setState(1)
            if brackets:
                innerSelf.dlgCtrls.checkboxBrackets.setState(1)
            else:
                innerSelf.dlgCtrls.checkboxBrackets.setState(0)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def test5_updating(self):
        """
        Test updating examples. Verify that:
        - the example is actually updated
        - the correct example number is updated
        - the old example isn't still there
        - surrounding spacing, formatting and text doesn't get messed up
        """
        testutil.blankWriterDoc(self.unoObjs)
        Test5Data = collections.namedtuple('Test5Data', [
            'pht', 'phm', 'refNum', 'attrName', 'attrVal'])
        dataSets = [
            Test5Data(
                u"a\u0256\u0268pa", u"a\u0256upa", "JPDN37.6", 'Default', ''),
            Test5Data(
                u"age", u"agge", "JPDN21.3", 'ParaStyleName', "Caption"),
            Test5Data(
                u"ak\u02b0e", u"akke", "JPDN21.5", 'CharStyleName',
                "Caption characters"),
            Test5Data(
                u"pæne", u"pane", "JPDN37.4", 'CharFontName', "Arial Black")]
        self._test5_insert_original_examples(dataSets)
        self._test5_update_examples()
        self._test5_check_examples(dataSets)

    def _test5_insert_original_examples(self, dataSets):
        self.surroundNum = 0
        oVC = self.unoObjs.viewcursor
        for data in dataSets:
            useDialog = self._test5_make_useDialog_phonSettings()
            DlgPhonSettings.useDialog = useDialog
            DlgGrabExamples.useDialog = useDialog_insertEx(data.refNum)
            self.runDlgSettings(True)

            self.surroundNum += 1
            numStr = str(self.surroundNum)
            if data.attrName != 'Default':
                oVC.setPropertyValue(data.attrName, data.attrVal)
            oVC.getText().insertString(oVC, "begin" + numStr, False)
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
            oVC.getText().insertString(oVC, "end" + numStr, False)
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
            oVC.goUp(1, False)
            oVC.gotoStartOfLine(False)
            self.runDlgGrabEx(True)
            self.verifyString(1, data.phm)
            self.verifyString(2, data.pht)
            oVC.goDown(1, False)
            oVC.setPropertyValue("ParaStyleName", "Standard")
            oVC.setPropertyToDefault("CharStyleName")
            oVC.setPropertyToDefault("CharFontName")
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)

    def _test5_make_useDialog_phonSettings(self):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            innerSelf.dlgCtrls.optionPhonemicFirst.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test5_update_examples(self):

        def useDialog_phonSettings(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
            innerSelf.dlgCtrls.fileControl.setText(filepath)
            innerSelf.dlgCtrls.optionPhoneticFirst.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))

        DlgPhonSettings.useDialog = useDialog_phonSettings
        self.runDlgSettings(True)

        def useDialog_grabExamples(innerSelf):
            innerSelf.dlgCtrls.optSearchExisting.setState(1)
            innerSelf.dlgCtrls.enableDisable(innerSelf.app, innerSelf.userVars)
            try:
                # as if user clicked OK
                testutil.modifyMsgboxOkCancel(True)
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("ReplaceAll"))
            except testutil.MsgSentException as exc:
                self.assertTrue(exc.msg.startswith("Updated"))
            else:
                self.fail("Expected error message.")

        DlgGrabExamples.useDialog = useDialog_grabExamples
        self.runDlgGrabEx(True)

    def _test5_check_examples(self, dataSets):
        self.surroundNum = 0
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        for data in dataSets:
            self.surroundNum += 1
            numStr = str(self.surroundNum)
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            self.assertEqual(oVC.getString(), "begin" + numStr)
            oVC.goDown(2, False)  # to "end" line
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            self.assertEqual(oVC.getString(), "end" + numStr)
            oVC.collapseToEnd()
            oVC.gotoStartOfLine(False)
            self.verifyString(1, data.pht)
            self.verifyString(2, data.phm)
            if data.attrName == 'Default':
                self.assertEqual(
                    oVC.getPropertyValue('ParaStyleName'), "Standard")
                self.assertEqual(
                    oVC.getPropertyValue('CharStyleName'), "")
                self.assertEqual(
                    oVC.getPropertyValue('CharFontName'),
                    testutil.getDefaultFont())
            else:
                self.assertEqual(
                    oVC.getPropertyValue(data.attrName), data.attrVal)
            oVC.goDown(1, False)  # to next "begin" line

    def verifyString(self, whichString, textExpected):
        """
        After phon example is created, verify string not including brackets.

        whichString=1 gives first  string, phonemic by default
        whichString=2 gives second string, phonetic by default
        whichString=3 gives gloss
        whichString=4 gives ref num

        These numbers will be offset if for example gloss has multiple words.
        """
        oVC = self.unoObjs.viewcursor
        oVC.goUp(1, False)
        oVC.gotoStartOfLine(False)
        wordCursor = oVC.getText().createTextCursorByRange(oVC)
        for dummy in range(whichString):
            wordCursor.gotoNextWord(False)  # move before string, after bracket
        oVC.gotoRange(wordCursor, False)
        oVC.goRight(len(textExpected), True)
        self.assertEqual(oVC.getString(), textExpected)
        oVC.goDown(1, False)

    @classmethod
    def tearDownClass(cls):
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)


def useDialog_insertEx(refNum):
    def useDialog(innerSelf):
        innerSelf.dlgCtrls.txtRefnum.setText(refNum)
        innerSelf.evtHandler.actionPerformed(MyActionEvent("InsertEx"))
    return useDialog


def useDialog_writingSys(testObj, wsDisplay, wsIndex):
    """
    :param testObj: a unittest object
    :param wsDisplay: value to select
    :param wsIndex: index we expect to be selected
    """
    def useDialog(innerSelf):
        innerSelf.listbox.selectItem(wsDisplay, True)
        testObj.assertEqual(innerSelf.listbox.getSelectedItemPos(), wsIndex)
        innerSelf.actionPerformed(MyActionEvent("OK"))
    return useDialog


if __name__ == '__main__':
    testutil.run_suite(getSuite())
