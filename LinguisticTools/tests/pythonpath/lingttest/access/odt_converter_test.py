# -*- coding: Latin-1 -*-
#
# This file created August 3 2016 by Jim Kornelsen
#
"""
Reads and modifies content.xml and styles.xml.
"""

import os
import logging
import unittest

from lingttest.utils import testutil

from lingt.access.xml import odt_converter
from lingt.access.writer.uservars import UserVars
from lingt.app.data import lingex_structs
from lingt.utils import util

logger = logging.getLogger("lingttest.odt_converter_test")

def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'testScopeWholeDoc',
            'testScopeFontWithStyle',
            'testScopeFontWithoutStyle',
            'testScopeParaStyle',
            'testScopeCharStyle'):
        suite.addTest(BulkReaderTestCase(method_name))
    return suite

class BulkReaderTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        USERVAR_PREFIX = "LTp_"  # LinguisticTools Phonology variables
        self.userVars = UserVars(
            USERVAR_PREFIX, self.unoObjs.document, logger)

    def testPA(self):
        config = lingex_structs.PhonInputSettings(None)
        config.filepath = os.path.join(
            util.TESTDATA_FOLDER, "PAdata.paxml")
        config.phoneticWS = ""
        config.isLexemePhonetic = False
        xmlReader = phon_reader.PhonReader(
            self.unoObjs, self.userVars, config)
        self.assertEqual(xmlReader.get_filetype(), "paxml")

        exampleDict = xmlReader.read()
        self.assertTrue("JPDN23.1".lower() in exampleDict)
        phonEx = exampleDict["JPDN23.1".lower()]
        self.assertEqual(phonEx.refText, "JPDN23.1")
        self.assertEqual(phonEx.gloss, "unmarried cousin")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        self.assertTrue("JPDN37.4".lower() in exampleDict)
        phonEx = exampleDict["JPDN37.4".lower()]
        self.assertEqual(phonEx.refText, "JPDN37.4")
        self.assertEqual(phonEx.gloss, "")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "JPDN58.02")

    def testTbx1(self):
        config = lingex_structs.PhonInputSettings(None)
        config.filepath = os.path.join(
            util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
        config.phoneticWS = ""
        config.isLexemePhonetic = False
        xmlReader = phon_reader.PhonReader(
            self.unoObjs, self.userVars, config)
        self.assertEqual(xmlReader.get_filetype(), "xml")

        exampleDict = xmlReader.read()
        self.assertTrue("JPDN21.5".lower() in exampleDict)
        phonEx = exampleDict["JPDN21.5".lower()]
        self.assertEqual(phonEx.refText, "JPDN21.5")
        self.assertEqual(phonEx.gloss, "elder sister")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        self.assertTrue("EGAN03.37".lower() in exampleDict)
        phonEx = exampleDict["EGAN03.37".lower()]
        self.assertEqual(phonEx.refText, "EGAN03.37")
        self.assertEqual(phonEx.gloss, "five")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertEqual(phonEx.phonemic, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "JPDN37.6")

    def testTbx2(self):
        self.userVars.store("SFMarker_Gloss", "gl123")    # doesn't exist
        config = lingex_structs.PhonInputSettings(None)
        config.filepath = os.path.join(
            util.TESTDATA_FOLDER, "TbxPhonCorpus.xml")
        config.phoneticWS = ""
        config.isLexemePhonetic = False
        xmlReader = phon_reader.PhonReader(
            self.unoObjs, self.userVars, config)

        exampleDict = xmlReader.read()
        self.assertTrue("JPDN21.5".lower() in exampleDict)
        phonEx = exampleDict["JPDN21.5".lower()]
        self.assertEqual(phonEx.refText, "JPDN21.5")
        self.assertEqual(phonEx.gloss, "")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "JPDN37.6")

        self.userVars.store("SFMarker_Gloss", "") # reset


if __name__ == '__main__':
    testutil.run_suite(getSuite())
