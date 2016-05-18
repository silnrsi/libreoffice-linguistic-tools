# -*- coding: Latin-1 -*-
#
# This file created 30-Nov-12 by Jim Kornelsen
#
# 25-Mar-13 JDK  Fixed problem: don't call goToAfterEx() until cursor is at
#                ref number. Also enumerate content to check results.
# 23-Apr-13 JDK  Remove table from main doc when finished, so that next
#                test in suite can pass.

import copy
import logging
import unittest

from lingttest.utils import testutil

from lingt.access.writer import styles
from lingt.access.writer.ex_updater import ExUpdater
from lingt.access.writer.outputmanager import InterlinMgr
from lingt.access.writer.uservars import UserVars
from lingt.app.data import lingex_structs
from lingt.utils import util

logger = logging.getLogger("lingttest.ex_updater_test")

def getSuite():
    suite = unittest.TestSuite()
    suite.addTest(ExUpdaterTestCase('testUpdater'))
    return suite

class ExUpdaterTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.unoObjs = None
        self.frameCount = 0
        self.tableCount = 0

    @classmethod
    def setUpClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankWriterDoc(unoObjs)

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.exnumRanges = []
        USERVAR_PREFIX = "LTg_"    # for Grammar
        self.userVars = UserVars(
            USERVAR_PREFIX, self.unoObjs.document, logger)
        self.styles = styles.GrammarStyles(self.unoObjs, self.userVars)
        self.styles.createStyles()
        self.baseConfig = lingex_structs.InterlinOutputSettings(None)
        self.baseConfig.makeOuterTable = True
        self.baseConfig.methodFrames = True
        self.baseConfig.methodTables = False
        self.baseConfig.showOrthoTextLine = True
        self.baseConfig.showText = True
        self.baseConfig.showOrthoMorphLine = True
        self.baseConfig.showMorphemeBreaks = True
        self.baseConfig.showPartOfSpeech = True
        self.baseConfig.insertNumbering = True
        self.baseConfig.separateMorphColumns = True
        self.baseConfig.POS_aboveGloss = False
        self.baseConfig.freeTransInQuotes = True
        self.baseConfig.startingOuterRowHeight = 2
        self.baseConfig.tableBottomMargin = 0.5
        self.baseConfig.numberingColumnWidth = 5

    def testUpdater(self):
        config = copy.copy(self.baseConfig)
        exManager = InterlinMgr(self.unoObjs, self.styles)
        exManager.setConfig(config)
        ex = lingex_structs.LingGramExample()
        ex.refText = "WORD01"
        ex.freeTrans = "ft1"
        ex.appendMorph("m1orth", "m1text", "m1Gloss", "m1pos")
        ex.appendMorph("m2orth", "m2text", "m2Gloss", "m2pos")
        ex.appendWord("word1_m1, 2", "word1Orth")
        ex.appendMorph("m3orth", "m3text", "m3Gloss", "m3pos")
        ex.appendMorph("m4orth", "m4text", "m4Gloss", "m4pos")
        ex.appendMorph("m5orth", "m5text", "m5Gloss", "m5pos")
        ex.appendWord("word2_m3-5", "word2Orth")
        exManager.outputExample(ex, False, False)
        exManager.addExampleNumbers()
        self.enumerateTextContent(self.unoObjs.text)
        self.assertEqual(self.tableCount, 1)
        self.assertEqual(self.frameCount, 7)

        # move cursor to end of ref number
        self.unoObjs.viewcursor.goUp(1, False)
        self.unoObjs.viewcursor.goLeft(1, False)

        updater = ExUpdater(self.unoObjs, exManager, "LTg_")
        updater.gotoAfterEx()
        ex.appendMorph("m6orth", "m6text", "m6Gloss", "m6pos")
        ex.appendWord("word3_m6", "word3Orth")
        exManager.outputExample(ex, False, True)

        updater.moveExNumber()
        updater.moveExamplesToNewDoc()
        self.enumerateTextContent(self.unoObjs.text)
        self.assertEqual(self.tableCount, 1)
        self.assertEqual(self.frameCount, 9)

        compDoc = updater.compDoc
        self.assertIsNotNone(compDoc)
        self.assertIsNotNone(compDoc.writerDoc)
        self.assertIsNotNone(compDoc.writerDoc.document)
        updater.compDoc.writerDoc.document.close(True)

    def enumerateTextContent(self, oParEnumerator):
        """
        Hacked from Access/Search.py
        """
        self.frameCount = 0
        self.tableCount = 0
        oParEnumeration = oParEnumerator.createEnumeration()
        i = 0
        while oParEnumeration.hasMoreElements():
            oPar = oParEnumeration.nextElement()
            i += 1
            logger.debug("par " + str(i) + ": " + oPar.ImplementationName)
            self.enumeratePar(oPar)
        return self.frameCount

    def enumeratePar(self, oPar):
        """Recursively enumerate paragraphs, tables and frames.
        Tables may be nested.
        """
        if oPar.supportsService("com.sun.star.text.Paragraph"):
            oSectionEnum = oPar.createEnumeration()
            while oSectionEnum.hasMoreElements():
                oSection = oSectionEnum.nextElement()
                if oSection.TextPortionType == "Text":
                    logger.debug("simple text portion")
                elif oSection.TextPortionType == "Frame":
                    logger.debug("Frame text portion")
                    oFrameEnum = oSection.createContentEnumeration(
                        "com.sun.star.text.TextFrame")
                    while oFrameEnum.hasMoreElements():  # always only 1 item?
                        oFrame = oFrameEnum.nextElement()
                        self.enumeratePar(oFrame)
        elif oPar.supportsService("com.sun.star.text.TextTable"):
            oTable = oPar
            logger.debug("table " + oTable.getName())
            self.tableCount += 1
            self.unoObjs.controller.select(oTable)  # go to first cell
            sNames = oTable.getCellNames()
            for sName in sNames:
                logger.debug("cell " + oTable.getName() + ":" + sName)
                oCell = oTable.getCellByName(sName)
                oParEnum = oCell.createEnumeration()
                while oParEnum.hasMoreElements():
                    oPar2 = oParEnum.nextElement()
                    self.enumeratePar(oPar2)
        elif oPar.supportsService("com.sun.star.text.TextFrame"):
            oFrame = oPar
            logger.debug("frame " + oFrame.getName())
            self.frameCount += 1
            oParEnum = oFrame.createEnumeration()
            while oParEnum.hasMoreElements():
                oPar2 = oParEnum.nextElement()
                self.enumeratePar(oPar2)

    @classmethod
    def tearDownClass(cls):
        unoObjs = testutil.unoObjsForCurrentDoc()
        unoObjs.dispatcher.executeDispatch(
            unoObjs.frame, ".uno:SelectTable", "", 0, ())
        unoObjs.dispatcher.executeDispatch(
            unoObjs.frame, ".uno:DeleteTable", "", 0, ())

if __name__ == '__main__':
    testutil.run_suite(getSuite())
