# -*- coding: Latin-1 -*-
#
# This file created October 23 2010 by Jim Kornelsen.
#
# 23-Apr-13 JDK  Clean up for further unit tests by removing big table.

import logging
import unittest

from lingttest.utils import testutil
from lingttest.utils.testutil import PARAGRAPH_BREAK

from lingt.access.writer import styles
from lingt.access.writer import tables
from lingt.access.writer.uservars import UserVars
from lingt.app import lingex_structs

logger = logging.getLogger("lingttest.tables_test")

def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'test1_testOuterTable',
            'test2_testHasWrappingText'):
        suite.addTest(TablesTestCase(method_name))
    return suite

class TablesTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.exnumRanges = []
        USERVAR_PREFIX = "LTg_"    # for Grammar
        self.userVars = UserVars(
            USERVAR_PREFIX, self.unoObjs.document, logger)
        self.styles = styles.GrammarStyles(
            self.unoObjs, self.userVars)
        self.config = lingex_structs.InterlinOutputSettings(None)
        self.config.makeOuterTable = True
        self.config.insertNumbering = False
        self.config.methodFrames = True
        self.config.startingOuterRowHeight = 2
        self.config.numberingColumnWidth = 5
        self.config.showOrthoTextLine = False
        self.config.showText = True
        self.config.showOrthoMorphLine = False
        self.config.showMorphemeBreaks = True
        self.config.showPartOfSpeech = True
        self.config.insertNumbering = True
        self.config.separateMorphColumns = True
        self.config.POS_aboveGloss = False
        self.config.tableBottomMargin = 0
        self.styles.parastyles.createInDoc("numP")
        self.styles.styleNames = {}
        self.styles.styleNames['numP'] = 'User Index 1'

    def test1_testOuterTable(self):
        outerTable = tables.OuterTable(
            self.unoObjs, self.config, self.exnumRanges, False, self.styles)

        oTextcursor = self.unoObjs.text.createTextCursorByRange(
            self.unoObjs.viewcursor.getStart())
        textTables = self.unoObjs.document.getTextTables()
        prevCount = textTables.getCount()
        outerTable.create(oTextcursor)
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, PARAGRAPH_BREAK, False)
        self.assertEqual(textTables.getCount(), prevCount + 1)
        self.assertEqual(textTables.getByIndex(0).getName(), "Table1")
        self.unoObjs.viewcursor.goDown(1, False)

    def test2_testHasWrappingText(self):
        oTable = self.unoObjs.document.createInstance(
            "com.sun.star.text.TextTable")
        oTable.initialize(1, 1)
        self.unoObjs.text.insertTextContent(
            self.unoObjs.viewcursor, oTable, False)
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, PARAGRAPH_BREAK, False)
        oCell = oTable.getCellByPosition(0, 0)
        oCellCursor = oCell.createTextCursor()
        oCell.insertString(oCellCursor, "a" * 500, False)
        self.assert_(self.tableHasWrappingText(oTable))

        oCell.setString("")
        oCell.insertString(oCellCursor, "a" * 5, False)
        self.assert_(not self.tableHasWrappingText(oTable))

        oTable = self.unoObjs.document.createInstance(
            "com.sun.star.text.TextTable")
        oTable.initialize(7, 7)
        self.unoObjs.text.insertTextContent(
            self.unoObjs.viewcursor, oTable, False)
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, PARAGRAPH_BREAK, False)
        oTextTableCurs = oTable.createCursorByCellName("B2")
        oTextTableCurs.gotoCellByName("B4", True)
        oTextTableCurs.mergeRange()
        oCell = oTable.getCellByPosition(2, 1)
        oCellCursor = oCell.createTextCursor()
        oCell.insertString(oCellCursor, "a" * 500, False)
        self.assert_(self.tableHasWrappingText(oTable))

    def tableHasWrappingText(self, oTable):
        return tables.hasWrappingText(oTable, self.unoObjs, self.styles)

    @classmethod
    def tearDownClass(cls):
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)

if __name__ == '__main__':
    testutil.run_suite(getSuite())
