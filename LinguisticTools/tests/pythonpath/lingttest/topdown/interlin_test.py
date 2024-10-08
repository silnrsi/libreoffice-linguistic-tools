"""
Test all features accessed by Interlinear Settings dialog controls.
Start from UI which calls App and Access layers (top-down).
"""
import collections
import logging
import unittest
import os

from lingt.access.writer import styles
from lingt.access.writer.uservars import InterlinTags
from lingt.app.svc.lingexamples import EXTYPE_INTERLINEAR
from lingt.ui.comp.grabex import DlgGrabExamples
from lingt.ui.comp.interlinsettings import DlgInterlinSettings
from lingt.utils import util

from lingttest.utils import testutil
from lingttest.utils.testutil import (
    TestCaseWithFixture, MyActionEvent, MyTextEvent, PARAGRAPH_BREAK)

logger = logging.getLogger("lingttest.interlin_test")

def getSuite():
    for klass in DlgInterlinSettings, DlgGrabExamples:
        testutil.modifyClass_showDlg(klass)
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_filetypes',
            'test2_surroundings',
            'test3_checkboxes',
            'test4_prefixAndColWidth',
            'test5_updating',
        ):
        suite.addTest(InterlinTestCase(method_name))
    return suite

class InterlinTestCase(TestCaseWithFixture):
    def __init__(self, testCaseName):
        super().__init__(testCaseName)
        self.surroundNum = 0  # number for surroundings
        self.prevFrameCount = 0
        self.prevTableCount = 0

    def setUp(self):
        super().setUp()
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.dlgSettings = None
        self.dlgGrabEx = None

    def runDlgSettings(self, dispose):
        self.dlgSettings = DlgInterlinSettings(self.unoObjs)
        self.dlgSettings.showDlg()
        if dispose:
            testutil.do_dispose(self.dlgSettings)
            self.dlgSettings = None

    def runDlgGrabEx(self, dispose):
        self.dlgGrabEx = DlgGrabExamples(EXTYPE_INTERLINEAR, self.unoObjs)
        self.dlgGrabEx.showDlg()
        if dispose:
            testutil.do_dispose(self.dlgGrabEx)
            self.dlgGrabEx = None

    def test1_filetypes(self):
        """Verify that toolbox and flextext files are read correctly."""
        Test1Data = collections.namedtuple(
            'Test1Data', [
            'filename', 'refNum', 'numFrames', 'firstWord', 'ft'])
        data_sets = [
            Test1Data(
                "TbxIntJPDN60.xml", "JPDN60.01", 9, "ceʋuɾu",
                "The wall is white."),
            Test1Data(
                "TbxIntJPDN60.xml", "JPDN61.08", 11, "ceɾɾune",
                "Bring the chair."),
            Test1Data(
                "Sena Int.flextext", "1.2", 13, "Tonsene",
                "[1.2 ft]"),
            Test1Data(
                "Sena Int.flextext", "1.1", 20, "Pisapha,",
                "Estas coisas doem mas o que é necessário é ter coragem. "
                "Pois nós todos vamos morrer.")]
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        for data in data_sets:
            DlgInterlinSettings.useDialog = (
                self._test1_useDialog_interlinSettings(data))
            DlgGrabExamples.useDialog = self.useDialog_insertEx(data.refNum)
            self.runDlgSettings(True)
            self.runDlgGrabEx(True)

            newFrameCount = self.unoObjs.document.getTextFrames().getCount()
            self.assertEqual(
                newFrameCount - self.prevFrameCount, data.numFrames)
            self.verifyFrame(1, data.firstWord)
            self.verifyFreeTrans(data.ft, True)
            self.prevFrameCount = newFrameCount

    def _test1_useDialog_interlinSettings(self, data):
        def useDialog(innerSelf):
            filepath = os.path.join(util.TESTDATA_FOLDER, data.filename)
            testutil.modifyFilePicker(filepath)
            if innerSelf.dlgCtrls.listboxFiles.getItemCount() > 0:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("FileRemove"))
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def test2_surroundings(self):
        """Test inserting and replacing examples, verifying that the
        examples are outputted where expected, checking the preceeding and
        following spacing, formatting and text.
        """
        testutil.blankWriterDoc(self.unoObjs)
        # Only test certain combinations in order to save time.
        Test2Data = collections.namedtuple(
            'Test2Data', [
            'outerTable', 'useFrames', 'numbering', 'ftQuoted'])
        data_sets = [
            Test2Data(True, True, True, True),  # 1 to 8
            Test2Data(True, False, False, False),  # 9 to 16
            Test2Data(False, True, True, True),  # 17 to 24
            Test2Data(False, True, False, False),  # 25 to 32
            Test2Data(False, False, True, True),  # 33 to 40  # fails
            Test2Data(False, False, True, False)  # 41 to 48
            ]
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        self.prevTableCount = self.unoObjs.document.getTextTables().getCount()
        for data in data_sets:
            DlgInterlinSettings.useDialog = (
                self._test2_useDialog_interlinSettings(data))
            self.runDlgSettings(True)
            for action in 'inserting', 'replacing':
                self.fixture_report = f"data={data}, action={action}"
                refNum = "1.1"
                DlgGrabExamples.useDialog = (
                    self._test2_useDialog_grabExamples(action, refNum))
                self._test2_do_grabExamples(data, action, refNum)

    def _test2_useDialog_interlinSettings(self, data):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "FWtextPigFox.xml")
            testutil.modifyFilePicker(filepath)
            if innerSelf.dlgCtrls.listboxFiles.getItemCount() > 0:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("FileRemove"))
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
            innerSelf.dlgCtrls.chkOuterTable.setState(
                1 if data.outerTable else 0)
            innerSelf.dlgCtrls.chkNumbering.setState(
                1 if data.numbering else 0)
            innerSelf.dlgCtrls.chkFT_inQuotes.setState(
                1 if data.ftQuoted else 0)
            if data.useFrames:
                innerSelf.dlgCtrls.optFrames.setState(1)
            else:
                innerSelf.dlgCtrls.optTables.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test2_useDialog_grabExamples(self, action, refNum):
        def useDialog(innerSelf):
            if action == 'inserting':
                innerSelf.dlgCtrls.chkSelectMultiple.setState(False)
                innerSelf.dlgCtrls.comboRefnum.setText(refNum)
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

    def _test2_do_grabExamples(self, data, action, refNum):
        changedAttrs = [
            ('ParaStyleName', "Caption"),
            ('CharStyleName', "Caption characters"),
            ('CharFontName', "Arial Black"),
            ('CharHeight', 9)]
        oVC = self.unoObjs.viewcursor
        for blankLine in True, False:
            for formatting in 'default', 'change':
                if formatting == 'change':
                    for attrName, attrVal in changedAttrs:
                        oVC.setPropertyValue(attrName, attrVal)
                self._test2_grabExInSurroundings(
                    action, blankLine, refNum, data)
                if formatting == 'default':
                    self.assertEqual(
                        oVC.getPropertyValue('ParaStyleName'), "Standard")
                    self.assertEqual(
                        oVC.getPropertyValue('CharStyleName'), "")
                    self.assertEqual(
                        oVC.getPropertyValue('CharFontName'),
                        testutil.getDefaultFont())
                else:
                    for attrName, attrVal in changedAttrs:
                        self.assertEqual(
                            oVC.getPropertyValue(attrName), attrVal)
                if blankLine:
                    oVC.goDown(1, False)
                oVC.gotoEndOfLine(False)
                oVC.getText().insertControlCharacter(
                    oVC, PARAGRAPH_BREAK, False)
                oVC.setPropertyValue('ParaStyleName', "Standard")
                oVC.setPropertyToDefault('CharStyleName')
                oVC.setPropertyToDefault('CharFontName')

    def _test2_grabExInSurroundings(self, action, blankLine, refNum, data):
        self._test2_insertSurroundings(action, refNum, blankLine)
        self.runDlgGrabEx(True)
        self._test2_verify_ex(data)
        self._test2_verify_surroundings(data, blankLine, action)

    def _test2_insertSurroundings(self, action, refNum, blankLine):
        oVC = self.unoObjs.viewcursor   # shorthand variable name
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

    def _test2_verify_ex(self, data):
        firstWord = "oɾu"
        ft = " ‎‎In a village there was a headman."
        numFrames = 11
        newTableCount = self.unoObjs.document.getTextTables().getCount()
        if data.useFrames:
            numTables = 1 if data.outerTable else 0
            self.assertEqual(newTableCount - self.prevTableCount, numTables)
            newFrameCount = self.unoObjs.document.getTextFrames().getCount()
            self.assertEqual(newFrameCount - self.prevFrameCount, numFrames)
            self.verifyFrame(1, firstWord)
            self.prevFrameCount = newFrameCount
        else:
            numTables = 2 if data.outerTable else 1
            self.assertEqual(newTableCount - self.prevTableCount, numTables)
            column = 0
            if not data.outerTable and not data.useFrames and data.numbering:
                column = 1
            row = 0
            self.verifyTable(numTables, column, row, firstWord)
        self.verifyFreeTrans(ft, data.ftQuoted)
        self.prevTableCount = newTableCount

    def _test2_verify_surroundings(self, data, blankLine, action):
        """Verify that beginning and ending strings were not changed."""
        # Vertical distance the view cursor moves over the example.
        ex_cursor_lines = 1
        if not data.outerTable:
            if not data.useFrames:
                # Test 2 inserts an example with 4 interlinear lines:
                # wordTx, morphTx, morphPoS, morphGloss.
                ex_cursor_lines += 3
            ex_cursor_lines += 1  # ft and ref no.
        oVC = self.unoObjs.viewcursor
        oVC.goUp(ex_cursor_lines + 2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        curs = oVC.getText().createTextCursorByRange(oVC)
        numStr = str(self.surroundNum)
        self.assertEqual(curs.getString(), "begin" + numStr)
        oVC.gotoStartOfLine(False)
        oVC.goDown(ex_cursor_lines + 2, False)
        if blankLine and action == 'inserting':
            oVC.goDown(1, False)
        oVC.gotoEndOfLine(True)
        curs = oVC.getText().createTextCursorByRange(oVC)
        self.assertEqual(curs.getString(), "end" + numStr)
        if blankLine and action == 'inserting':
            oVC.goUp(1, False)

    def test3_checkboxes(self):
        """Test most checkboxes in Interlinear Settings.
        This may ignore some controls that have already been sufficiently
        tested in test2_surroundings() or other places.
        """
        testutil.blankWriterDoc(self.unoObjs)
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        self.prevTableCount = self.unoObjs.document.getTextTables().getCount()
        for setting in [
                'wordTx1', 'wordTx2', 'wordGloss',
                'morphTx1', 'morphTx2', 'morphGloss', 'morphPos',
                'posBelow', 'sepCols', 'numbering']:
            for setVal in True, False:
                self.fixture_report = f"setting={setting}, setVal={setVal}"
                DlgInterlinSettings.useDialog = (
                    self._test3_useDialog_interlinSettings(setting, setVal))
                self.runDlgSettings(True)
                refNum = "Hunt01"
                DlgGrabExamples.useDialog = self.useDialog_insertEx(refNum)
                self.runDlgGrabEx(True)
                self._test3_verify(setting, setVal)

    def _test3_useDialog_interlinSettings(self, setting, setVal):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "TbxIntHunt06.xml")
            testutil.modifyFilePicker(filepath)
            if innerSelf.dlgCtrls.listboxFiles.getItemCount() > 0:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("FileRemove"))
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("FileAdd"))
            TAG_VARS = dict(InterlinTags.TAG_VARS)
            innerSelf.userVars.store(TAG_VARS['wordTx1'], 'or')
            innerSelf.userVars.store(TAG_VARS['wordTx2'], 'tx')
            innerSelf.userVars.store(TAG_VARS['morphTx1'], 'mbor')
            innerSelf.userVars.store(TAG_VARS['morphTx2'], 'mb')
            innerSelf.userVars.store("SFM_Baseline", "WordLine2")
            innerSelf.dlgCtrls.chkWordText1.setState(0)
            innerSelf.dlgCtrls.chkWordText2.setState(1)
            innerSelf.dlgCtrls.chkWordGloss.setState(0)
            innerSelf.dlgCtrls.chkMorphText1.setState(0)
            innerSelf.dlgCtrls.chkMorphText2.setState(1)
            innerSelf.dlgCtrls.chkMorphGloss.setState(1)
            innerSelf.dlgCtrls.chkMorphPos.setState(0)
            innerSelf.dlgCtrls.chkMorphsSeparate.setState(1)
            innerSelf.dlgCtrls.chkMorphPosBelowGloss.setState(0)
            innerSelf.dlgCtrls.chkNumbering.setState(1)
            newState = int(setVal)
            if setting == 'wordTx1':
                innerSelf.dlgCtrls.chkWordText1.setState(newState)
            elif setting == 'wordTx2':
                innerSelf.dlgCtrls.chkWordText2.setState(newState)
            elif setting == 'wordGloss':
                innerSelf.dlgCtrls.chkWordGloss.setState(newState)
            elif setting == 'morphTx1':
                innerSelf.dlgCtrls.chkMorphText1.setState(newState)
            elif setting == 'morphTx2':
                innerSelf.dlgCtrls.chkMorphText2.setState(newState)
            elif setting == 'morphGloss':
                innerSelf.dlgCtrls.chkMorphGloss.setState(newState)
            elif setting == 'morphPos':
                innerSelf.dlgCtrls.chkMorphPos.setState(newState)
            elif setting == 'posBelow':
                innerSelf.dlgCtrls.chkMorphGloss.setState(1)
                innerSelf.dlgCtrls.chkMorphPos.setState(1)
                innerSelf.dlgCtrls.chkMorphPosBelowGloss.setState(newState)
            elif setting == 'sepCols':
                innerSelf.dlgCtrls.chkMorphsSeparate.setState(newState)
            elif setting == 'numbering':
                innerSelf.dlgCtrls.chkNumbering.setState(newState)
            else:
                self.fail("Unexpected setting: %s" % setting)
            innerSelf.dlgCtrls.optTables.setState(1)
            self.setOrthographicFont(innerSelf.userVars)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test3_verify(self, setting, setVal):
        newTableCount = self.unoObjs.document.getTextTables().getCount()
        numTables = 2
        numTablesMax = numTables + 1  # some fonts cause wrapping
        tablesAdded = newTableCount - self.prevTableCount
        self.assertGreaterEqual(tablesAdded, numTables)
        self.assertLessEqual(tablesAdded, numTablesMax)
        class Lex1:  # only morph of first lexeme
            text1 = "ஒரு"
            text2 = "oɾu"
            morph1 = text1
            morph2 = text2  # second morph line (writing sys) of first morph
            ge = "a"
            wge = "a"
            pos = "det"
        class Lex2:  # first morph of second lexeme
            text1 = "ஊரிதி"
            text2 = "uːɾu-d̪i"
            morph1 = "ஊரு"
            morph2 = "uːɾu"
            ge = "village"
            wge = "village.in"
            pos = "n"
        class Lex2Morph2:
            morph1 = "-தி"
            morph2 = "-d̪i"
            ge = "-LOC.in"
            pos = "-case"
        # Lines set by default in _test3_useDialog_interlinSettings() are
        # WordText2, MorphText2, and MorphGloss.
        DEFAULT_ROWS = 3
        # If a line is not set by default, then turning on adds a row.
        MAX_ROWS_FOR_DEFAULT_OFF = DEFAULT_ROWS + 1
        # If a line is set by default, then turning off loses a row.
        MAX_ROWS_FOR_DEFAULT_ON = DEFAULT_ROWS
        def verifyColumn(forms, lines, row=0, col=0):
            for index, (form, line) in enumerate(zip(forms, lines)):
                base_fixture_report = self.fixture_report
                self.fixture_report += f" checking {line}"
                self.verifyTable(numTables, col, row + index, form)
                self.fixture_report = base_fixture_report
        if setting == 'wordTx1':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_OFF}", setVal)
            if setVal:
                verifyColumn(
                    [Lex1.text1, Lex1.text2],
                    [setting, "word text 2"])
            else:
                # This checks all default values.
                # Other checks are variations of this.
                verifyColumn(
                    [Lex1.text2, Lex1.morph2, Lex1.ge],
                    ["word text 2", "morph text 2", "morph gloss"])
        elif setting == 'wordTx2':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_ON}", setVal)
            if setVal:
                verifyColumn(
                    [Lex1.text2, Lex1.morph2],
                    [setting, "morph text 2"])
            else:
                verifyColumn(
                    [Lex1.text2, Lex1.ge],
                    ["morph text 2", "morph gloss"])
        elif setting == 'wordGloss':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_OFF}", setVal)
            if setVal:
                verifyColumn(
                    [Lex2.ge, Lex2.wge],
                    ["morph gloss", setting],
                    row=2, col=1)
        elif setting == 'morphTx1':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_OFF}", setVal)
            if setVal:
                verifyColumn(
                    [Lex2Morph2.morph1, Lex2Morph2.morph2],
                    [setting, "morph text 2"],
                    row=1, col=2)
            else:
                verifyColumn(
                    [Lex2Morph2.morph2],
                    ["morph text 2"],
                    row=1, col=2)
        elif setting == 'morphTx2':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_ON}", setVal)
            if setVal:
                verifyColumn([Lex1.morph2], [setting], row=1)
            else:
                verifyColumn([Lex1.ge], ["morph gloss"], row=1)
        elif setting == 'morphGloss':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_ON}", setVal)
            if setVal:
                verifyColumn([Lex1.ge], [setting], row=2)
        elif setting == 'morphPos':
            self.verifyTableHasCell(
                numTables, f"A{MAX_ROWS_FOR_DEFAULT_OFF}", setVal)
            if setVal:
                verifyColumn(
                    [Lex1.pos, Lex1.ge],
                    [setting, "morph gloss"],
                    row=2)
        elif setting == 'posBelow':
            self.verifyTableHasCell(numTables, "A4", True)
            if setVal:
                verifyColumn(
                    [Lex1.ge, Lex1.pos],
                    ["morph gloss", "morph part of speech"],
                    row=2)
            else:
                verifyColumn(
                    [Lex1.pos, Lex1.ge],
                    ["morph part of speech", "morph gloss"],
                    row=2)
        elif setting == 'sepCols':
            self.verifyTableHasCell(numTables, "F1", True)
            self.verifyTableHasCell(numTables, "G1", False)
            self.verifyTableHasCell(numTables, "F2", True)
            self.verifyTableHasCell(numTables, "I2", setVal)
            if setVal:
                verifyColumn(
                    [Lex2.morph2],
                    ["morph text 2"],
                    row=1, col=1)
            else:
                verifyColumn(
                    [Lex2.text2],
                    ["word text 1"],
                    row=1, col=1)
        elif setting == 'numbering':
            self.verifyTableHasCell(1, "A1", True)
            if setVal:
                tables = self.unoObjs.document.getTextTables()
                tableWanted = tables.getByIndex(self.prevTableCount)
                cellWanted = tableWanted.getCellByPosition(0, 0)
                cellCursor = cellWanted.createTextCursor()
                cellCursor.gotoEnd(True)
                celltext = cellCursor.getString().strip()
                self.assertRegex(celltext, r"^\(\d+\)$")
            else:
                self.verifyTable(1, 0, 0, "()")  # number
        else:
            self.fail("Unexpected setting: %s" % setting)
        self.prevTableCount = newTableCount

    def test4_prefixAndColWidth(self):
        """Test prefix and column width in Interlinear Settings."""
        testutil.blankWriterDoc(self.unoObjs)
        Test4Data = collections.namedtuple(
            'Test4Data', [
            'refNum', 'numFrames', 'firstWord', 'ft'])
        data_sets = [
            Test4Data(
                "A1.1", 20, "Pisapha,",
                "Estas coisas doem mas o que é necessário é ter coragem. "
                "Pois nós todos vamos morrer."),
            Test4Data(
                "BP1.S1", 11, "oɾu",
                " ‎‎In a village there was a headman.")]
        DlgInterlinSettings.useDialog = (
            self._test4_useDialog_interlinSettings())
        self.runDlgSettings(True)
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        oVC = self.unoObjs.viewcursor
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        for data in data_sets:
            self.fixture_report = f"data={data}"
            DlgGrabExamples.useDialog = self.useDialog_insertEx(data.refNum)
            self.runDlgGrabEx(True)
            newFrameCount = self.unoObjs.document.getTextFrames().getCount()
            self.assertEqual(
                newFrameCount - self.prevFrameCount, data.numFrames)
            self.verifyFrame(1, data.firstWord)
            self.verifyFreeTrans(data.ft, True)
            self.prevFrameCount = newFrameCount
        self._test4_verify_resize(data_sets)

    def _test4_useDialog_interlinSettings(self):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "Sena Int.flextext")
            testutil.modifyFilePicker(filepath)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
            innerSelf.dlgCtrls.txtPrefix.setText("A")
            innerSelf.dlgCtrls.chkDontUseSegnum.setState(True)
            innerSelf.evtHandler.textChanged(
                MyTextEvent(innerSelf.dlgCtrls.txtPrefix))
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "FWtextPigFox.xml")
            testutil.modifyFilePicker(filepath)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
            innerSelf.dlgCtrls.txtPrefix.setText("B")
            innerSelf.dlgCtrls.chkDontUseSegnum.setState(False)
            innerSelf.evtHandler.textChanged(
                MyTextEvent(innerSelf.dlgCtrls.txtPrefix))
            try:
                testutil.modifyMsgboxOkCancel(True)  # as if user clicked OK
                innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
            except testutil.MsgSentException as exc:
                self.assertTrue(exc.msg.startswith(
                    "The following Ref Numbers have duplicates"))
        return useDialog

    def _test4_verify_resize(self, data_sets):
        oVC = self.unoObjs.viewcursor
        oVC.goUp(2, False)   # move into second table
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:DeleteTable", "", 0, ())
        for resize in False, True:
            if resize:
                def useDialog_interlinSettings(innerSelf):
                    # This value may need to be adjusted depending on your
                    # default system settings.
                    # If the test fails, adjust the value until the table
                    # starts at 2 frames tall and resizes to 3 frames tall.
                    RESIZE_PERCENT = 50
                    innerSelf.dlgCtrls.txtNumColWidth.setText(RESIZE_PERCENT)
                    innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
                DlgInterlinSettings.useDialog = useDialog_interlinSettings
                self.runDlgSettings(True)
            oVC.goLeft(2, False)  # move into first table after ref num
            ft = data_sets[1].ft
            oVC.goLeft(len(ft), False)
            oVC.gotoStartOfLine(False)
            tableName = "Table1"
            oVC.goUp(2, False)
            self.assertIsNotNone(oVC.TextTable)
            self.assertEqual(oVC.TextTable.getName(), tableName)
            # Before the table is resized, this should move out of the table.
            oVC.goUp(1, False)
            if resize:
                self.assertIsNotNone(oVC.TextTable)
                self.assertEqual(oVC.TextTable.getName(), tableName)
            else:
                self.assertIsNone(oVC.TextTable)
            oVC.goDown(3, False)

    def test5_updating(self):
        """Test updating examples.  Verify that:
        - the example is actually updated
        - the correct example number is updated
        - the old example isn't still there
        - surrounding spacing, formatting and text doesn't get messed up
        """
        testutil.blankWriterDoc(self.unoObjs)
        Test5Data = collections.namedtuple(
            'Test5Data', [
            'refNum', 'numFrames', 'firstWord', 'attrName', 'attrVal'])
        data_sets = [
            Test5Data(
                "AJPDN60.01", 9, "ceʋuɾu", 'Default', ''),
            Test5Data(
                "AJPDN61.08", 11, "ceɾɾune", 'ParaStyleName',
                "Caption"),
            Test5Data(
                "B1.1", 11, "oɾu", 'CharStyleName',
                "Caption characters"),
            Test5Data(
                "B1.2", 21, "aʋant̪u", 'CharFontName',
                "Arial Black")]
        self._test5a_insert_original_examples(data_sets)
        self._test5b_update_examples()
        self._test5c_check_comparisondoc(data_sets)
        self._test5d_check_examples(data_sets)

    def _test5a_insert_original_examples(self, data_sets):
        DlgInterlinSettings.useDialog = (
            self._test5a_useDialog_interlinSettings())
        self.surroundNum = 0
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        oVC = self.unoObjs.viewcursor
        for data in data_sets:
            self.fixture_report = f"data={data}"
            DlgGrabExamples.useDialog = self.useDialog_insertEx(data.refNum)
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
            newFrameCount = self.unoObjs.document.getTextFrames().getCount()
            self.assertEqual(
                newFrameCount - self.prevFrameCount, data.numFrames)
            self.verifyFrame(1, data.firstWord)
            self.prevFrameCount = newFrameCount
            oVC.goDown(1, False)
            oVC.setPropertyValue("ParaStyleName", "Standard")
            oVC.setPropertyToDefault("CharStyleName")
            oVC.setPropertyToDefault("CharFontName")
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        tables = self.unoObjs.document.getTextTables()
        self.assertEqual(tables.getCount(), len(data_sets))

    def _test5a_useDialog_interlinSettings(self):
        def useDialog(innerSelf):
            if len(innerSelf.fileItems) == 0:
                filepath = os.path.join(
                    util.TESTDATA_FOLDER, "TbxIntJPDN60.xml")
                testutil.modifyFilePicker(filepath)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
                innerSelf.dlgCtrls.txtPrefix.setText("A")
                innerSelf.evtHandler.textChanged(
                    MyTextEvent(innerSelf.dlgCtrls.txtPrefix))
                filepath = os.path.join(
                    util.TESTDATA_FOLDER, "FWtextPigFox.xml")
                testutil.modifyFilePicker(filepath)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
                innerSelf.dlgCtrls.txtPrefix.setText("B")
                innerSelf.evtHandler.textChanged(
                    MyTextEvent(innerSelf.dlgCtrls.txtPrefix))
            innerSelf.dlgCtrls.optFrames.setState(1)
            # This size may need to be adjusted depending on system settings.
            RESIZE_PERCENT = 15
            innerSelf.dlgCtrls.txtNumColWidth.setText(RESIZE_PERCENT)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test5b_update_examples(self):
        def useDialog_interlinSettings(innerSelf):
            innerSelf.dlgCtrls.optTables.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        DlgInterlinSettings.useDialog = useDialog_interlinSettings
        self.runDlgSettings(True)
        def useDialog_grabExamples(innerSelf):
            innerSelf.dlgCtrls.optSearchExisting.setState(1)
            innerSelf.dlgCtrls.enableDisable(innerSelf.app, innerSelf.userVars)
            try:
                testutil.modifyMsgboxOkCancel(True)  # as if user clicked OK
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("ReplaceAll"))
            except testutil.MsgSentException as exc:
                self.assertTrue(exc.msg.startswith("Updated"))
            else:
                self.fail("Expected error message.")
        DlgGrabExamples.useDialog = useDialog_grabExamples
        self.runDlgGrabEx(False)

    def _test5c_check_comparisondoc(self, data_sets):
        compDoc = self.dlgGrabEx.app.operations.exUpdater.compDoc
        self.assertIsNotNone(compDoc)
        self.assertIsNotNone(compDoc.writerDoc)
        self.assertIsNotNone(compDoc.writerDoc.document)
        numTables = compDoc.writerDoc.document.getTextTables().getCount()
        multiLineExs = 1  # number of examples that have another line
        self.assertEqual(numTables, 3 * len(data_sets) + multiLineExs)
        self.fixture_report = f"len(data_sets)={len(data_sets)}"
        compDoc.writerDoc.document.close(True)
        testutil.do_dispose(self.dlgGrabEx)
        self.dlgGrabEx = None

    def _test5d_check_examples(self, data_sets):
        tables = self.unoObjs.document.getTextTables()
        multiLineExs = 1  # number of examples that have another line
        self.assertEqual(tables.getCount(), 2 * len(data_sets) + multiLineExs)
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        self.surroundNum = 0
        tableNum = 1
        for data in data_sets:
            self.fixture_report = f"data={data}"
            self.verifyTable(tableNum + 1, 0, 0, data.firstWord)
            self.surroundNum += 1
            numStr = str(self.surroundNum)
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            curs = oVC.getText().createTextCursorByRange(oVC)
            self.assertEqual(curs.getString(), "begin" + numStr)
            oVC.gotoStartOfLine(False)
            oVC.goDown(3, False)  # to "end" line
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            curs = oVC.getText().createTextCursorByRange(oVC)
            self.assertEqual(curs.getString(), "end" + numStr)
            oVC.collapseToEnd()
            oVC.gotoStartOfLine(False)
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
            tableNum += 2

    def verifyFrame(self, whichFrame, textExpected):
        """After interlin ex is created, verify text content of the text frame.
        whichFrame starts at 1 for the first frame created for an example.
        """
        exStartIndex = self.prevFrameCount - 1  # make it 0-based
        exIndex = exStartIndex + whichFrame
        frames = self.unoObjs.document.getTextFrames()
        frameWanted = frames.getByIndex(exIndex)
        framecursor = frameWanted.createTextCursor()
        framecursor.gotoEnd(True)
        frametext = framecursor.getString().strip()
        self.assertEqual(frametext, textExpected)

    def verifyTable(self, whichTable, col, row, textExpected):
        """After interlin ex is created, verify text content of table.
        Will check the first row of the specified column.
        whichTable starts at 1 for the first table created for an example.
        """
        exStartIndex = self.prevTableCount - 1  # make it 0-based
        exIndex = exStartIndex + whichTable
        tables = self.unoObjs.document.getTextTables()
        tableWanted = tables.getByIndex(exIndex)
        cellWanted = tableWanted.getCellByPosition(col, row)
        cellCursor = cellWanted.createTextCursor()
        cellCursor.gotoEnd(True)
        celltext = cellCursor.getString().strip()
        self.assertEqual(celltext, textExpected)

    def verifyTableHasCell(self, whichTable, whichCell, isExpected):
        """After interlin ex is created, verify that a table does or does not
        have a specific column such as A1.
        whichTable starts at 1 for the first table created for an example.
        """
        exStartIndex = self.prevTableCount - 1  # make it 0-based
        exIndex = exStartIndex + whichTable
        tables = self.unoObjs.document.getTextTables()
        tableWanted = tables.getByIndex(exIndex)
        cellNames = tableWanted.getCellNames()
        if isExpected:
            self.assertIn(whichCell, cellNames)
        else:
            self.assertNotIn(whichCell, cellNames)

    def verifyFreeTrans(self, ftExpected, quoted):
        """After interlin ex is created, verify free translation."""
        oVC = self.unoObjs.viewcursor
        oVC.goLeft(2, False)  # move up to end of FT line
        oVC.goLeft(len(ftExpected), False)  # prepare for gotoStartOfLine
        oVC.gotoStartOfLine(False)
        if quoted:
            oVC.goRight(1, False)  # pass over single quote
        oTextCurs = oVC.getText().createTextCursorByRange(oVC)
        oTextCurs.goRight(len(ftExpected), True)
        self.assertEqual(oTextCurs.getString(), ftExpected)
        oVC.gotoStartOfLine(False)
        spaceLen = 4
        oVC.goRight(len(ftExpected) + spaceLen, False)
        if quoted:
            oVC.goRight(2, False)
        oVC.gotoEndOfLine(False)
        oVC.goDown(2, False)

    def setOrthographicFont(self, userVars):
        """Font for several examples is Latha.
        They sometimes crash when using Mangal.
        """
        logger.debug(util.funcName('begin'))
        fontDef = styles.FontDefStruct(
            "Latha", "Complex", styles.FONT_ORTH.fontSize)
        interlinStyles = styles.InterlinStyles(self.unoObjs, userVars)
        interlinStyles.createStyles()
        logger.debug("%s: Created interlinear styles.", util.funcName())
        styleFonts = styles.StyleFonts(
            self.unoObjs, interlinStyles.styleNames)
        styleFonts.setParaStyleWithFont(fontDef, styleKey="wordTx2")
        styleFonts.setParaStyleWithFont(fontDef, styleKey="morphTx2")

    def useDialog_insertEx(self, refNum):
        def useDialog(innerSelf):
            try:
                innerSelf.dlgCtrls.chkSelectMultiple.setState(False)
                innerSelf.dlgCtrls.comboRefnum.setText(refNum)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("InsertEx"))
            except testutil.MsgSentException as exc:
                print(f"\nUnexpected MsgSentException: {exc}")
                if self.fixture_report:
                    logger.debug("Fixture: %s", self.fixture_report)
                    print(f"Fixture: {self.fixture_report}")
        return useDialog

if __name__ == '__main__':
    testutil.run_suite(getSuite())
