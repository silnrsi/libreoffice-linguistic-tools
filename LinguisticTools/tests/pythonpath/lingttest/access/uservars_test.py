import logging
import unittest

from lingt.access.writer.uservars import Prefix, UserVars

from lingttest.utils import testutil

logger = logging.getLogger("lingttest.uservars_test")

def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'testWriter',
            'testCalc',
            'testDraw'):
        suite.addTest(UserVarsTestCase(method_name))
    return suite

class UserVarsTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.unoObjs = None

    def testWriter(self):
        testutil.blankWriterDoc()
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.testUserVars()

    def testCalc(self):
        testutil.blankSpreadsheet()
        self.unoObjs = testutil.unoObjsForCurrentSpreadsheet()
        self.testUserVars()

    def testDraw(self):
        testutil.blankDrawing()
        self.unoObjs = testutil.unoObjsForCurrentDrawing()
        self.testUserVars()

    def testUserVars(self):
        userVars = UserVars(
            Prefix.TESTING, self.unoObjs.document, logger)
        userVars.store("TestVar_1", "hamburger")
        result = userVars.get("TestVar_1")
        self.assertEqual(result, "hamburger")

        userVars.store("TestVar_2", "0")
        result = userVars.get("TestVar_2")
        self.assertEqual(result, "0")

        result = userVars.get("TestVar_3")
        self.assertEqual(result, "")

        userVars.store("TestVar_4", "something")
        userVars.store("TestVar_4", "")
        result = userVars.get("TestVar_4")
        self.assertEqual(result, "")

        userVars.delete("TestVar_1")
        result = userVars.get("TestVar_1")
        self.assertEqual(result, "")
        result = userVars.get("TestVar_2")
        self.assertEqual(result, "0")

        userVars.delete("TestVar_2")
        userVars.delete("TestVar_3")
        userVars.delete("TestVar_4")
        result = userVars.get("TestVar_2")
        self.assertEqual(result, "")
        result = userVars.get("TestVar_3")
        self.assertEqual(result, "")

    def tearDown(self):
        self.unoObjs.document.close(True)
        testutil.blankWriterDoc()

if __name__ == '__main__':
    testutil.run_suite(getSuite())
