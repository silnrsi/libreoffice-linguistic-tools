# -*- coding: Latin-1 -*-
#
# This file created March 22, 2010 by Jim Kornelsen
#
# 09-Oct-10 JDK  Updated to use with assimilated scripts.
# 23-Apr-13 JDK  Change paths for Linux.
# 25-Nov-15 JDK  Integrated into test suite.

"""
Test grabbing interlinear examples by setting user var values.

This test takes a VERY long time to run (a few hours depending on the system),
so it is important to run assimilated rather than with a listening instance.
However it may help to do a trial run with a listening instance first
in order to make sure it will start, and then interrupt it.
One more suggestion: Run in a virtual desktop or a virtual machine or a
separate machine so that it doesn't tie up your user interface.

Examples must be visually checked for errors.
Normally I quickly skim through the resulting document,
looking for anything suspicious.

Alternatively just run it and if it doesn't crash or show exceptions in
the log then hopefully it is ok.
"""
import logging
import os
import unittest

from lingttest.utils import testutil

from lingt.access.writer.styles import GrammarStyles
from lingt.access.writer.uservars import UserVars, GrammarTags
from lingt.app.svc.lingexamples import ExServices, EXTYPE_GRAMMAR
from lingt.utils import util

logger = logging.getLogger("lingttest.visual_test_grammar")
DASHES = "-" * 20

def getSuite():
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    suite.addTest(VisGrammarTestCase('test1'))
    return suite

class VisGrammarTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)
        logger.debug("----Manual Test BEGIN----------------------------------")
        msgr.unoObjs = unoObjs
        msgr.write(DASHES + "Running tests" + DASHES)
        msgr.endl()

    # pylint: disable=no-self-use
    def test1(self):
        doTests()
        # pylint: enable=no-self-use

    @classmethod
    def tearDownClass(cls):
        msgr.endl()
        msgr.write(DASHES + "Finished" + DASHES)
        msgr.endl()
        msgr.unoObjs.viewcursor.gotoEnd(False)
        msgr.unoObjs = None
        logger.debug("----Manual Test END----------------------------------")


def doTests():
    unoObjs = testutil.unoObjsForCurrentDoc()
    userVars = UserVars("LTg_", unoObjs.document, logger)
    GrammarStyles(unoObjs, userVars).createStyles()
    GrammarTags(userVars).loadUserVars()
    resetUserVars(userVars)
    allRefNums = ["JPDN60.01", "Hunt06", "Hunt39"]
    #allRefNums = ["JPDN60.01"]
    #allRefNums = ["FW-1.1", "FW-1.2", "FW-2.1"]

    ## Just do one test

    #userVars.store('MakeOuterTable', "0")
    #userVars.store('Method', "tables")
    #userVars.store('InsertNumbering', "1")
    #doCall("JPDN60.01", unoObjs)
    #return

    ## Basic tests

    #numTests = len(allRefNums)
    #msgr.write(DASHES + "Basic Tests (" + str(numTests) + " tests)" + DASHES)
    #msgr.endl()
    #for exrefnum in allRefNums:
    #    doCall(exrefnum, unoObjs)
    #return  # do only basic tests

    ## Showing / hiding lines

    resetUserVars(userVars)
    numTests = 2 * 2 * 2 * 2 * 2 * 2 * 2 * len(allRefNums)
    msgr.endl()
    msgr.write(
        DASHES + "Showing / hiding lines (" + str(numTests) + " tests)" +
        DASHES)
    msgr.endl()
    for method in ["frames", "tables"]:
        msgr.write("Method = " + method)
        for separateMorphCols in ["0", "1"]:
            msgr.write("SeparateMorphColumns = " + separateMorphCols)
            for showText in ["1", "0"]:
                msgr.write("ShowText = " + showText)
                for showMorphBreaks in ["1", "0"]:
                    msgr.write("ShowMorphBreaks = " + showMorphBreaks)
                    for showOrtho in ["0", "1"]:
                        msgr.write("ShowOrthoTextLine = " + showOrtho)
                        for showPOS in ["1", "0"]:
                            msgr.write("ShowPartOfSpeech = " + showPOS)
                            for aboveGloss in ["0", "1"]:
                                if showPOS == 0 and aboveGloss != 0:
                                    continue
                                msgr.write("POS_AboveGloss = " + aboveGloss)
                                msgr.endl()
                                for exrefnum in allRefNums:
                                    userVars.store('Method', method)
                                    userVars.store('ShowText', showText)
                                    userVars.store(
                                        'ShowMorphBreaks', showMorphBreaks)
                                    userVars.store('ShowPartOfSpeech', showPOS)
                                    userVars.store(
                                        'POS_AboveGloss', aboveGloss)
                                    userVars.store("SeparateMorphColumns",
                                                   separateMorphCols)
                                    userVars.store(
                                        'ShowOrthoTextLine', showOrtho)
                                    doCall(exrefnum, unoObjs)

    ## Numbering

    resetUserVars(userVars)
    numTests = 2 * 2 * 2 * len(allRefNums) + 4 * len(allRefNums)
    msgr.endl()
    msgr.write(
        DASHES + "Numbering (" + str(numTests) + " tests)" + DASHES)
    msgr.endl()
    for makeOuterTable in ["1", "0"]:
        msgr.write("MakeOuterTable = " + makeOuterTable)
        for method in ["frames", "tables"]:
            msgr.write("Method = " + method)
            for insertNumbering in ["1", "0"]:
                msgr.write("InsertNumbering = " + insertNumbering)
                for separateMorphCols in ["0", "1"]:
                    msgr.write("SeparateMorphColumns = " + separateMorphCols)
                    msgr.endl()
                    for exrefnum in allRefNums:
                        userVars.store('MakeOuterTable', makeOuterTable)
                        userVars.store('Method', method)
                        userVars.store(
                            "SeparateMorphColumns", separateMorphCols)
                        userVars.store('InsertNumbering', insertNumbering)
                        doCall(exrefnum, unoObjs)
    resetUserVars(userVars)
    for method in ["frames", "tables"]:
        msgr.write("Method = " + method)
        for numberingColWidth in ["7", "10", "50"]:
            msgr.write("NumberingColWidth = " + numberingColWidth)
            msgr.endl()
            for exrefnum in allRefNums:
                userVars.store('Method', method)
                userVars.store('NumberingColWidth', numberingColWidth)
                doCall(exrefnum, unoObjs)


def doCall(exrefnum, unoObjs):
    app = ExServices(EXTYPE_GRAMMAR, unoObjs)
    app.insertByRefnum(exrefnum)


def resetUserVars(userVars):
    varValues1 = {
        'ShowOrthoTextLine' : '0',
        'ShowText' : '1',
        'SeparateMorphColumns' : '1',
        'ShowMorphBreaks' : '1',
        'ShowPartOfSpeech' : '1',

        'InsertNumbering' : '1',
        'MakeOuterTable' : '1',
        'NumberingColWidth' : '7',
        'TableBottomMargin' : '0.13',
        'FreeTransInQuotes' : '1',
        'POS_AboveGloss' : '0',

        'Method' : 'frames',

        'SFMarker_Orthographic' : 'or',

        'StyleName_FreeTxln' : 'Interlin Freeform Gloss',
        'StyleName_Gloss' : 'Interlin Gloss',
        'StyleName_InterlinearFrame' : 'Interlin Frame',
        'StyleName_LastRowPara' : 'Interlin Last Row',
        'StyleName_Morpheme' : 'Interlin Morph',
        'StyleName_MorphemeFrame' : 'Interlin Morpheme Frame',
        'StyleName_NumPara' : 'Interlin Example Number',
        'StyleName_Orthographic' : 'Interlin Orthographic',
        'StyleName_POS' : 'Interlin POS',
        'StyleName_RefNum' : 'Interlin Reference Number',
        'StyleName_Text' : 'Interlin Base',

        'XML_fileCount' : '3',
        'XML_filePath00' : os.path.join(
            util.TESTDATA_FOLDER, 'TbxIntHunt06.xml'),
        'XML_filePrefix00' : '',
        'XML_filePath01' : os.path.join(
            util.TESTDATA_FOLDER, 'TbxIntJPDN60.xml'),
        'XML_filePrefix01' : '',
        'XML_filePath02' : os.path.join(
            util.TESTDATA_FOLDER, 'FWtextPigFox.xml'),
        'XML_filePrefix02' : 'FW-'
    }
    for key in varValues1:
        userVars.store(key, varValues1[key])


class MessageWriter:
    def __init__(self):
        # Caller must set unoObjs before using the methods of this class.
        self.unoObjs = None

    def write(self, msg):
        self.unoObjs.text.insertString(self.unoObjs.viewcursor, msg + "  ", 0)

    def endl(self):
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, testutil.PARAGRAPH_BREAK, 0)

msgr = MessageWriter()


if __name__ == '__main__':
    testutil.run_suite(getSuite())
