# -*- coding: Latin-1 -*-
#
# This file created May 6, 2013 by Jim Kornelsen
#
# 15-Sep-15 JDK  Use Latin-1 encoding for this file.
# 28-Sep-15 JDK  Added getSuite().
# 21-May-16 JDK  Move useDialog definitions out of for loops.
# 01-Mar-17 JDK  Word Line 1 and 2 instead of Orthographic and Text.

# pylint: disable=no-self-use

"""
Test all features accessed by Grammar Settings dialog controls.
Start from UI which calls App and Access layers (top-down).
"""
import collections
import logging
import unittest
import os

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent, PARAGRAPH_BREAK

from lingt.access.writer import styles
from lingt.access.writer.uservars import GrammarTags
from lingt.ui.comp.grabex import DlgGrabExamples
from lingt.ui.comp.gramsettings import DlgGramSettings
from lingt.utils import util

logger = logging.getLogger("lingttest.grammar_test")

def getSuite():
    for klass in DlgGramSettings, DlgGrabExamples:
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
        suite.addTest(GrammarTestCase(method_name))
    return suite

class GrammarTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        testutil.verifyRegexMethods(self)
        self.surroundNum = 0  # number for surroundings
        self.prevFrameCount = 0
        self.prevTableCount = 0

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.dlgSettings = None
        self.dlgGrabEx = None

    def runDlgSettings(self, dispose):
        self.dlgSettings = DlgGramSettings(self.unoObjs)
        self.dlgSettings.showDlg()
        if dispose:
            testutil.do_dispose(self.dlgSettings)
            self.dlgSettings = None

    def runDlgGrabEx(self, dispose):
        self.dlgGrabEx = DlgGrabExamples("grammar", self.unoObjs)
        self.dlgGrabEx.showDlg()
        if dispose:
            testutil.do_dispose(self.dlgGrabEx)
            self.dlgGrabEx = None

    def test1_filetypes(self):
        """Verify that toolbox and flextext files are read correctly."""
        Test1Data = collections.namedtuple('Test1Data', [
            'filename', 'refNum', 'numFrames', 'firstWord', 'ft'])
        dataSets = [
            Test1Data(
                "TbxIntJPDN60.xml", "JPDN60.01", 9, u"ce\u028bu\u027eu",
                "The wall is white."),
            Test1Data(
                "TbxIntJPDN60.xml", "JPDN61.08", 11, u"ce\u027e\u027eune",
                "Bring the chair."),
            Test1Data(
                "Sena Int.flextext", "1.2", 13, u"Tonsene",
                u"[1.2 ft]"),
            Test1Data(
                "Sena Int.flextext", "1.1", 20, u"Pisapha,",
                u"Estas coisas doem mas o que é necessário é ter coragem. "
                u"Pois nós todos vamos morrer.")]
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        for dataSet in dataSets:
            useDialog = self._test1_make_useDialog(dataSet)
            DlgGramSettings.useDialog = useDialog
            DlgGrabExamples.useDialog = useDialog_insertEx(dataSet.refNum)
            self.runDlgSettings(True)
            self.runDlgGrabEx(True)

            newFrameCount = self.unoObjs.document.getTextFrames().getCount()
            self.assertEqual(
                newFrameCount - self.prevFrameCount, dataSet.numFrames)
            self.verifyFrame(1, dataSet.firstWord)
            self.verifyFreeTrans(dataSet.ft, True)
            self.prevFrameCount = newFrameCount

    def _test1_make_useDialog(self, data):
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
        Test2Data = collections.namedtuple('Test2Data', [
            'outerTable', 'useFrames', 'numbering', 'ftQuoted'])
        dataSets = [
            Test2Data(True, True, True, True),
            Test2Data(True, False, False, False),
            Test2Data(False, True, True, True),
            Test2Data(False, True, False, False),
            Test2Data(False, False, True, True),
            Test2Data(False, False, True, False)]
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        self.prevTableCount = self.unoObjs.document.getTextTables().getCount()
        for dataSet in dataSets:
            useDialog = self._test2_make_useDialog_gramSettings(dataSet)
            DlgGramSettings.useDialog = useDialog
            self.runDlgSettings(True)
            for action in 'inserting', 'replacing':
                refNum = "1.1"
                useDialog = self._test2_make_useDialog_grabExamples(
                    action, refNum)
                DlgGrabExamples.useDialog = useDialog
                self._test2_do_grabExamples(dataSet, action, refNum)

    def _test2_make_useDialog_gramSettings(self, data):
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

    def _test2_make_useDialog_grabExamples(self, action, refNum):
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
        firstWord = u"o\u027eu"
        ft = u" \u200e\u200eIn a village there was a headman."
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
        exLines = 1  # number of lines used by example according to viewcursor
        if not data.outerTable:
            exLines += 1
            if not data.useFrames:
                exLines += 2
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        oVC.goUp(exLines + 2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        curs = oVC.getText().createTextCursorByRange(oVC)
        numStr = str(self.surroundNum)
        self.assertEqual(curs.getString(), "begin" + numStr)
        oVC.gotoStartOfLine(False)
        oVC.goDown(exLines + 2, False)
        if blankLine and action == 'inserting':
            oVC.goDown(1, False)
        oVC.gotoEndOfLine(True)
        curs = oVC.getText().createTextCursorByRange(oVC)
        self.assertEqual(curs.getString(), "end" + numStr)
        if blankLine and action == 'inserting':
            oVC.goUp(1, False)

    def test3_checkboxes(self):
        """Test most checkboxes in Grammar Settings.
        This may ignore some controls that have already been sufficiently
        tested in test2_surroundings() or other places.
        """
        testutil.blankWriterDoc(self.unoObjs)
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        self.prevTableCount = self.unoObjs.document.getTextTables().getCount()
        for setting in ['word1', 'word2', 'morph1', 'morph2', 'ps', 'sepCols',
                        'psAbove', 'numbering']:
            for setVal in True, False:
                useDialog = self._test3_make_useDialog(setting, setVal)
                DlgGramSettings.useDialog = useDialog
                self.runDlgSettings(True)
                refNum = "Hunt01"
                DlgGrabExamples.useDialog = useDialog_insertEx(refNum)
                self.runDlgGrabEx(True)
                self._test3_verify(setting, setVal)

    def _test3_make_useDialog(self, setting, setVal):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "TbxIntHunt06.xml")
            testutil.modifyFilePicker(filepath)
            if innerSelf.dlgCtrls.listboxFiles.getItemCount() > 0:
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("FileRemove"))
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("FileAdd"))
            TAG_VARS = dict(GrammarTags.TAG_VARS)
            innerSelf.userVars.store(TAG_VARS['word1'], 'or')
            innerSelf.userVars.store(TAG_VARS['word2'], 'tx')
            innerSelf.userVars.store(TAG_VARS['morph1'], 'mbor')
            innerSelf.userVars.store(TAG_VARS['morph2'], 'mb')
            innerSelf.userVars.store("SFM_Baseline", "WordLine2")
            innerSelf.dlgCtrls.chkWordLine1.setState(0)
            innerSelf.dlgCtrls.chkWordLine2.setState(1)
            innerSelf.dlgCtrls.chkMorphLine1.setState(0)
            innerSelf.dlgCtrls.chkMorphLine2.setState(1)
            innerSelf.dlgCtrls.chkPOS_Line.setState(0)
            innerSelf.dlgCtrls.chkMorphsSeparate.setState(1)
            innerSelf.dlgCtrls.chkPOS_aboveGloss.setState(0)
            innerSelf.dlgCtrls.chkNumbering.setState(1)
            newState = int(setVal)
            if setting == 'word1':
                innerSelf.dlgCtrls.chkWordLine1.setState(newState)
            elif setting == 'word2':
                innerSelf.dlgCtrls.chkWordLine2.setState(newState)
            elif setting == 'morph1':
                innerSelf.dlgCtrls.chkMorphLine1.setState(newState)
            elif setting == 'morph2':
                innerSelf.dlgCtrls.chkMorphLine2.setState(newState)
            elif setting == 'ps':
                innerSelf.dlgCtrls.chkPOS_Line.setState(newState)
            elif setting == 'sepCols':
                innerSelf.dlgCtrls.chkMorphsSeparate.setState(newState)
            elif setting == 'psAbove':
                innerSelf.dlgCtrls.chkPOS_Line.setState(1)
                innerSelf.dlgCtrls.chkPOS_aboveGloss.setState(newState)
            elif setting == 'numbering':
                innerSelf.dlgCtrls.chkNumbering.setState(newState)
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
        ipaOru = u"o\u027eu"  # used in text and mb lines
        if setting == 'word1':
            self.verifyTableHasCell(numTables, "A4", setVal)
            if setVal:
                tamOru = u"\u0b92\u0bb0\u0bc1"  # Tamil /oru/
                self.verifyTable(numTables, 0, 0, tamOru)  # orth
                self.verifyTable(numTables, 0, 1, ipaOru)  # text
            else:
                self.verifyTableHasCell(numTables, "A4", False)
                self.verifyTable(numTables, 0, 0, ipaOru)  # text
        elif setting == 'word2':
            self.verifyTableHasCell(numTables, "A3", setVal)
            if setVal:
                self.verifyTable(numTables, 0, 0, ipaOru)  # text
                self.verifyTable(numTables, 0, 1, ipaOru)  # mb
            else:
                self.verifyTable(numTables, 0, 0, ipaOru)  # mb
                self.verifyTable(numTables, 0, 1, "a")  # gloss
        elif setting == 'morph1':
            self.verifyTableHasCell(numTables, "A4", setVal)
            if setVal:
                tamTi = u"-\u0ba4\u0bbf"  # Tamil /-ti/
                self.verifyTable(numTables, 2, 1, tamTi)  # mb orth
            else:
                self.verifyTable(numTables, 2, 1, u"-d\u032ai")  # mb
        elif setting == 'morph2':
            self.verifyTableHasCell(numTables, "A3", setVal)
            if setVal:
                self.verifyTable(numTables, 0, 1, ipaOru)  # mb
            else:
                self.verifyTable(numTables, 0, 1, "a")  # gloss
        elif setting == 'ps':
            self.verifyTableHasCell(numTables, "A4", setVal)
            if setVal:
                self.verifyTable(numTables, 0, 3, "det")  # ps
        elif setting == 'sepCols':
            self.verifyTableHasCell(numTables, "F1", True)
            self.verifyTableHasCell(numTables, "G1", False)
            self.verifyTableHasCell(numTables, "F2", True)
            self.verifyTableHasCell(numTables, "I2", setVal)
            if setVal:
                self.verifyTable(
                    numTables, 1, 1, u"u\u02d0\u027eu")  # mb
            else:
                self.verifyTable(
                    numTables, 1, 1, u"u\u02d0\u027eu-d\u032ai")  # mb
        elif setting == 'psAbove':
            self.verifyTableHasCell(numTables, "A4", True)
            if setVal:
                self.verifyTable(numTables, 0, 2, "det")  # ps
                self.verifyTable(numTables, 0, 3, "a")  # gloss
            else:
                self.verifyTable(numTables, 0, 2, "a")  # gloss
                self.verifyTable(numTables, 0, 3, "det")  # ps
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
        self.prevTableCount = newTableCount

    def test4_prefixAndColWidth(self):
        """Test prefix and column width in Grammar Settings."""
        testutil.blankWriterDoc(self.unoObjs)
        Test4Data = collections.namedtuple('Test4Data', [
            'refNum', 'numFrames', 'firstWord', 'ft'])
        dataSets = [
            Test4Data(
                "A1.1", 20, u"Pisapha,",
                u"Estas coisas doem mas o que é necessário é ter coragem. "
                u"Pois nós todos vamos morrer."),
            Test4Data(
                "BP1.S1", 11, u"o\u027eu",
                u" \u200e\u200eIn a village there was a headman.")]
        useDialog = self._test4_make_useDialog_gramSettingsA()
        DlgGramSettings.useDialog = useDialog
        self.runDlgSettings(True)
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        oVC = self.unoObjs.viewcursor
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        for dataSet in dataSets:
            DlgGrabExamples.useDialog = useDialog_insertEx(dataSet.refNum)
            self.runDlgGrabEx(True)

            newFrameCount = self.unoObjs.document.getTextFrames().getCount()
            self.assertEqual(
                newFrameCount - self.prevFrameCount, dataSet.numFrames)
            self.verifyFrame(1, dataSet.firstWord)
            self.verifyFreeTrans(dataSet.ft, True)
            self.prevFrameCount = newFrameCount
        self._test4_verify_resize(dataSets)

    def _test4_make_useDialog_gramSettingsA(self):
        def useDialog(innerSelf):
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "Sena Int.flextext")
            testutil.modifyFilePicker(filepath)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
            innerSelf.dlgCtrls.txtPrefix.setText("A")
            innerSelf.dlgCtrls.chkUseSegnum.setState(False)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileUpdate"))
            filepath = os.path.join(
                util.TESTDATA_FOLDER, "FWtextPigFox.xml")
            testutil.modifyFilePicker(filepath)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
            innerSelf.dlgCtrls.txtPrefix.setText("B")
            innerSelf.dlgCtrls.chkUseSegnum.setState(True)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("FileUpdate"))
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test4_verify_resize(self, dataSets):
        oVC = self.unoObjs.viewcursor
        oVC.goUp(2, False)   # move into second table
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:DeleteTable", "", 0, ())
        for resize in False, True:
            if resize:

                def useDialog(innerSelf):
                    # This value may need to be adjusted depending on your
                    # default system settings.
                    # If the test fails, adjust the value until the table
                    # starts at 2 frames tall and resizes to 3 frames tall.
                    RESIZE_PERCENT = 50
                    innerSelf.dlgCtrls.txtNumColWidth.setText(RESIZE_PERCENT)
                    innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))

                DlgGramSettings.useDialog = useDialog
                self.runDlgSettings(True)
            oVC.goLeft(2, False)  # move into first table after ref num
            ft = dataSets[1].ft
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
        """
        Test updating examples.  Verify that:
        - the example is actually updated
        - the correct example number is updated
        - the old example isn't still there
        - surrounding spacing, formatting and text doesn't get messed up
        """
        testutil.blankWriterDoc(self.unoObjs)
        Test5Data = collections.namedtuple('Test5Data', [
            'refNum', 'numFrames', 'firstWord', 'attrName', 'attrVal'])
        dataSets = [
            Test5Data(
                "AJPDN60.01", 9, u"ce\u028bu\u027eu", 'Default', ''),
            Test5Data(
                "AJPDN61.08", 11, u"ce\u027e\u027eune", 'ParaStyleName',
                "Caption"),
            Test5Data(
                "B1.1", 11, u"o\u027eu", 'CharStyleName',
                "Caption characters"),
            Test5Data(
                "B1.2", 21, u"a\u028bant\u032au", 'CharFontName',
                "Arial Black")]
        self._test5_insert_original_examples(dataSets)
        self._test5_update_examples()
        self._test5_check_comparisondoc(dataSets)
        self._test5_check_examples(dataSets)

    def _test5_insert_original_examples(self, dataSets):
        useDialog = self._test5_make_useDialoga()
        DlgGramSettings.useDialog = useDialog
        self.surroundNum = 0
        self.prevFrameCount = self.unoObjs.document.getTextFrames().getCount()
        oVC = self.unoObjs.viewcursor
        for data in dataSets:
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
        self.assertEqual(tables.getCount(), len(dataSets))

    def _test5_make_useDialoga(self):
        def useDialog(innerSelf):
            if len(innerSelf.fileItems) == 0:
                filepath = os.path.join(
                    util.TESTDATA_FOLDER, "TbxIntJPDN60.xml")
                testutil.modifyFilePicker(filepath)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
                innerSelf.dlgCtrls.txtPrefix.setText("A")
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("FileUpdate"))
                filepath = os.path.join(
                    util.TESTDATA_FOLDER, "FWtextPigFox.xml")
                testutil.modifyFilePicker(filepath)
                innerSelf.evtHandler.actionPerformed(MyActionEvent("FileAdd"))
                innerSelf.dlgCtrls.txtPrefix.setText("B")
                innerSelf.evtHandler.actionPerformed(
                    MyActionEvent("FileUpdate"))
            innerSelf.dlgCtrls.optFrames.setState(1)
            # This size may need to be adjusted depending on system settings.
            RESIZE_PERCENT = 15
            innerSelf.dlgCtrls.txtNumColWidth.setText(RESIZE_PERCENT)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))
        return useDialog

    def _test5_update_examples(self):

        def useDialog_gramSettings(innerSelf):
            innerSelf.dlgCtrls.optTables.setState(1)
            innerSelf.evtHandler.actionPerformed(MyActionEvent("OK"))

        DlgGramSettings.useDialog = useDialog_gramSettings
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

    def _test5_check_comparisondoc(self, dataSets):
        compDoc = self.dlgGrabEx.app.operations.exUpdater.compDoc
        self.assertIsNotNone(compDoc)
        self.assertIsNotNone(compDoc.writerDoc)
        self.assertIsNotNone(compDoc.writerDoc.document)
        numTables = compDoc.writerDoc.document.getTextTables().getCount()
        multiLineExs = 1  # number of examples that have another line
        self.assertEqual(numTables, 3 * len(dataSets) + multiLineExs)
        compDoc.writerDoc.document.close(True)
        testutil.do_dispose(self.dlgGrabEx)
        self.dlgGrabEx = None

    def _test5_check_examples(self, dataSets):
        tables = self.unoObjs.document.getTextTables()
        multiLineExs = 1  # number of examples that have another line
        self.assertEqual(tables.getCount(), 2 * len(dataSets) + multiLineExs)

        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        self.surroundNum = 0
        tableNum = 1
        for data in dataSets:
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
        """After gram ex is created, verify text content of the text frame.
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
        """
        After gram ex is created, verify text content of table.
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
        """After gram ex is created, verify that a table does or does not have
        a specific column such as A1.
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
        """After gram ex is created, verify free translation."""
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
        grammarStyles = styles.GrammarStyles(self.unoObjs, userVars)
        grammarStyles.createStyles()
        logger.debug(util.funcName() + ": Created grammar styles.")
        styleFonts = styles.StyleFonts(
            self.unoObjs, grammarStyles.styleNames)
        styleFonts.setParaStyleWithFont(fontDef, styleKey="word2")
        styleFonts.setParaStyleWithFont(fontDef, styleKey="morph2")

    #@classmethod
    #def tearDownClass(cls):
    #    unoObjs = testutil.unoObjsForCurrentDoc()
    #    testutil.blankWriterDoc(unoObjs)


def useDialog_insertEx(refNum):
    def useDialog(innerSelf):
        innerSelf.dlgCtrls.txtRefnum.setText(refNum)
        innerSelf.evtHandler.actionPerformed(MyActionEvent("InsertEx"))
    return useDialog


if __name__ == '__main__':
    testutil.run_suite(getSuite())
