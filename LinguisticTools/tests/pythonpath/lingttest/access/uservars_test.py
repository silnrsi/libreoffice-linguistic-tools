# -*- coding: Latin-1 -*-
#
# This file created February 6 2010 by Jim Kornelsen
#
# 23-Oct-10 JDK  Use unittest.
# 23-Apr-13 JDK  UserVars is now in Access layer.
# 28-Sep-15 JDK  Added getSuite().
# 23-Jul-20 JDK  Test Calc and Draw as well.

import logging
import unittest

from lingttest.utils import testutil

from lingt.access.writer.uservars import UserVars

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
        USERVAR_PREFIX = "Test_"  # variables for testing
        userVars = UserVars(
            USERVAR_PREFIX, self.unoObjs.document, logger)
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
