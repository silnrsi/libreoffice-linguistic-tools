"""
Test grabbing phonology examples by setting user var values.

Examples must be visually checked for errors.
Normally I quickly skim through the resulting document,
looking for anything suspicious.

Alternatively just run it and if it doesn't crash or show exceptions in
the log then hopefully it is ok.
"""
import logging
import os
import unittest

from lingt.access.writer.styles import PhonologyStyles
from lingt.access.writer.uservars import UserVars, PhonologyTags
from lingt.app.svc.lingexamples import ExServices, EXTYPE_PHONOLOGY
from lingt.utils import util

from lingttest.utils import testutil

logger = logging.getLogger("lingttest.visual_test_phonology")
DASHES = "-" * 20

def getSuite():
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_paxml',
            'test2_lift',
            'test3_tbx',
        ):
        suite.addTest(VisPhonologyTestCase(method_name))
    return suite

class VisPhonologyTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)
        logger.debug("----Manual Test BEGIN----------------------------------")
        msgr.unoObjs = unoObjs
        msgr.write(DASHES + "Running tests" + DASHES)
        msgr.endl()

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()

    def test1_paxml(self):
        filepath = os.path.join(util.TESTDATA_FOLDER, "PAdata.paxml")
        allRefNums = ["JPDN58.02", "JPDN23.1", "JPDN37.4"]
        doTests(filepath, allRefNums, self.unoObjs)

    def test2_lift(self):
        filepath = os.path.join(util.TESTDATA_FOLDER, "FWlexicon.lift")
        allRefNums = ["EGAN02.30", "JPDN21.4"]
        doTests(filepath, allRefNums, self.unoObjs)

    def test3_tbx(self):
        filepath = os.path.join(
            util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
        allRefNums = ["JPDN49.09", "JPDN21.3", "JPDN21.5", "JPDN42.5"]
        doTests(filepath, allRefNums, self.unoObjs)

    @classmethod
    def tearDownClass(cls):
        msgr.endl()
        msgr.write(DASHES + "Finished" + DASHES)
        msgr.endl()
        msgr.unoObjs.viewcursor.gotoEnd(False)
        msgr.unoObjs = None
        logger.debug("----Manual Test END----------------------------------")

def doTests(filepath, allRefNums, unoObjs):
    msgr.endl()
    msgr.write(DASHES)
    msgr.endl()
    msgr.write(filepath)
    msgr.endl()
    msgr.endl()
    userVars = UserVars("LTp_", unoObjs.document, logger)
    PhonologyStyles(unoObjs, userVars).createStyles()
    PhonologyTags(userVars).loadUserVars()
    resetUserVars(userVars)
    for exrefnum in allRefNums:
        for leftmost in ["phonemic", "phonetic"]:
            for showBrackets in ["1", "0"]:
                userVars.store("XML_filePath", filepath)
                userVars.store("Leftmost", leftmost)
                userVars.store("ShowBrackets", showBrackets)
                app = ExServices(EXTYPE_PHONOLOGY, unoObjs)
                app.insertByRefnum(exrefnum)
                #return  # run only the first example

def resetUserVars(userVars):
    varValues = {
        'Leftmost' : 'phonemic',
        'ShowBrackets' : '1',

        'StyleName_ExamplePara' : 'Lex Example',
        'StyleName_Gloss' : 'Lex Gloss',
        'StyleName_Phonemic' : 'Lex Phonemic',
        'StyleName_Phonetic' : 'Lex Phonetic',
        'StyleName_RefNum' : 'Lex Reference Number',

        'PhoneticWritingSystem' : 'iru-x-X_ETIC'
    }
    for key, val in varValues.items():
        userVars.store(key, val)

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
