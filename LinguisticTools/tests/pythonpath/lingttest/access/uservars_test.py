# -*- coding: Latin-1 -*-
#
# This file created February 6 2010 by Jim Kornelsen
#
# 23-Oct-10 JDK  Use unittest.
# 23-Apr-13 JDK  UserVars is now in Access layer.
# 28-Sep-15 JDK  Added getSuite().

import logging
import unittest

from lingttest.utils import testutil

from lingt.access.writer.uservars import UserVars

logger = logging.getLogger("lingttest.uservars_test")

def getSuite():
    suite = unittest.TestSuite()
    suite.addTest(UserVarsTestCase('testUserVars'))
    return suite

class UserVarsTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()

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

if __name__ == '__main__':
    testutil.run_suite(getSuite())
