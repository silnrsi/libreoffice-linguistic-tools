import os
import logging
import unittest

from lingttest.utils import testutil

from lingt.access.xml import interlin_reader
from lingt.access.xml import phon_reader
from lingt.access.writer.uservars import Prefix, UserVars
from lingt.app.data import lingex_structs
from lingt.app.data.fileitemlist import InterlinInputSettings, LingExFileItem
from lingt.utils import util

logger = logging.getLogger("lingttest.xml_readers_test")

def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'testPA',
            'testTbx1',
            'testTbx2'):
        suite.addTest(PhonTestCase(method_name))
    for method_name in (
            'testTbx',
            'testTbxOrth',
            'testFw',
            'testFlexText'):
        suite.addTest(InterlinTestCase(method_name))
    for method_name in (
            'testPhonFieldHelper',
            'testMergedMorphemes'):
        suite.addTest(TestHelpersTestCase(method_name))
    return suite

class PhonTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.userVars = UserVars(
            Prefix.PHONOLOGY, self.unoObjs.document, logger)

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


class InterlinTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.userVars = UserVars(
            Prefix.INTERLINEAR, self.unoObjs.document, logger)

    def testTbx(self):
        filepath = os.path.join(util.TESTDATA_FOLDER, "TbxIntHunt06.xml")
        fileItem = LingExFileItem(self.userVars)
        fileItem.filepath = filepath
        config = InterlinInputSettings(None)
        config.fileList = [fileItem]
        config.separateMorphColumns = True
        config.showMorphemeBreaks = True

        xmlReader = interlin_reader.InterlinReader(
            self.unoObjs, self.userVars, config)
        exampleDict = xmlReader.read()
        self.assertEqual(
            xmlReader.get_filetype(filepath, xmlReader.dom), "toolbox")

        self.assertTrue("Hunt06".lower() in exampleDict)
        interlinEx = exampleDict["Hunt06".lower()]
        self.assertEqual(interlinEx.refText, "Hunt06")
        self.assertEqual(
            interlinEx.freeTrans,
            '"Not so.  Tell him, "We should take along the sister\'s ' +
            'husband and go to the hill for hunting.\'" Only when he hunts ' +
            'they will go.')
        self.assertEqual(len(interlinEx.wordList), 13)

        word1 = interlinEx.wordList[0]
        self.assertNotEqual(word1.text1, "")
        self.assertEqual(word1.text2, "")
        self.assertEqual(len(word1.morphList), 1)
        morph1 = word1.morphList[0]
        self.assertEqual(morph1.gloss, "like.that")
        self.assertEqual(morph1.pos, "adv")
        self.assertNotEqual(morph1.text1, "")
        self.assertEqual(morph1.text2, "")

        word4 = interlinEx.wordList[3]
        self.assertEqual(len(word4.morphList), 2)
        morph1 = word4.morphList[0]
        self.assertEqual(morph1.gloss, "sister")
        self.assertEqual(morph1.pos, "n")
        self.assertNotEqual(morph1.text1, "")
        self.assertEqual(morph1.text2, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "Hunt01")

    def testTbxOrth(self):
        filepath = os.path.join(util.TESTDATA_FOLDER, "TbxIntHunt06.xml")
        fileItem = LingExFileItem(self.userVars)
        fileItem.filepath = filepath
        config = InterlinInputSettings(None)
        config.fileList = [fileItem]
        config.separateMorphColumns = True
        config.showMorphemeBreaks = True
        self.userVars.store("SFMarker_Word2", "or")
        self.userVars.store("SFMarker_Morpheme2", "mbtam")

        xmlReader = interlin_reader.InterlinReader(
            self.unoObjs, self.userVars, config)
        exampleDict = xmlReader.read()
        interlinEx = exampleDict["Hunt06".lower()]
        word1 = interlinEx.wordList[0]
        self.assertNotEqual(word1.text2, "")
        morph1 = word1.morphList[0]
        self.assertNotEqual(morph1.text2, "")

        word4 = interlinEx.wordList[3]
        self.assertNotEqual(word4.text2, "")
        morph1 = word4.morphList[0]
        self.assertNotEqual(morph1.text2, "")

        self.userVars.store("SFMarker_Word2", "")          # reset
        self.userVars.store("SFMarker_Morpheme2", "")     # reset

    def testFw(self):
        filepath = os.path.join(util.TESTDATA_FOLDER, "FWtextPigFox.xml")
        fileItem = LingExFileItem(self.userVars)
        fileItem.filepath = filepath
        fileItem.prefix = "Prefix-"
        config = InterlinInputSettings(None)
        config.fileList = [fileItem]
        config.separateMorphColumns = True
        config.showMorphemeBreaks = True

        xmlReader = interlin_reader.InterlinReader(
            self.unoObjs, self.userVars, config)
        exampleDict = xmlReader.read()
        self.assertEqual(
            xmlReader.get_filetype(filepath, xmlReader.dom), "fieldworks")

        self.assertTrue("Prefix-1.1".lower() in exampleDict)
        self.assertTrue(not "Prefix-1".lower() in exampleDict)
        self.assertTrue("Prefix-1.2".lower() in exampleDict)
        self.assertTrue(not "Prefix-1.3".lower() in exampleDict)
        self.assertTrue("Prefix-2".lower() in exampleDict)
        self.assertTrue(not "Prefix-2.1".lower() in exampleDict)
        self.assertTrue(not "Prefix-2.2".lower() in exampleDict)

        interlinEx = exampleDict["Prefix-1.2".lower()]
        self.assertEqual(interlinEx.refText, "Prefix-1.2")
        self.assertEqual(
            interlinEx.freeTrans,
            u" \u200e\u200eIn his house he kept one pig and one fox ")
        self.assertEqual(len(interlinEx.wordList), 7)

        word2 = interlinEx.wordList[1]
        self.assertNotEqual(word2.text1, "")
        self.assertEqual(word2.text2, "")
        self.assertEqual(len(word2.morphList), 2)
        morph2 = word2.morphList[1]
        self.assertEqual(morph2.gloss, "LOC.in")
        self.assertEqual(morph2.pos, "case ")
        self.assertNotEqual(morph2.text1, "")
        self.assertEqual(morph2.text2, "")

    def testFlexText(self):
        filepath = os.path.join(util.TESTDATA_FOLDER, "Sena Int.flextext")
        fileItem = LingExFileItem(self.userVars)
        fileItem.filepath = filepath
        fileItem.prefix = "ABC "
        config = InterlinInputSettings(None)
        config.fileList = [fileItem]
        config.separateMorphColumns = True
        config.showMorphemeBreaks = True

        xmlReader = interlin_reader.InterlinReader(
            self.unoObjs, self.userVars, config)
        exampleDict = xmlReader.read()
        self.assertEqual(
            xmlReader.get_filetype(filepath, xmlReader.dom), "fieldworks")

        self.assertTrue("ABC 1.1".lower() in exampleDict)
        self.assertTrue("ABC 1.2".lower() in exampleDict)
        self.assertTrue(not "ABC 2.1".lower() in exampleDict)

        interlinEx = exampleDict["ABC 1.2".lower()]
        self.assertEqual(interlinEx.refText, "ABC 1.2")
        self.assertEqual(interlinEx.freeTrans, "[1.2 ft]")
        self.assertEqual(len(interlinEx.wordList), 4)

        word1 = interlinEx.wordList[0]
        self.assertEqual(word1.text1, "Tonsene")

        word2 = interlinEx.wordList[2]
        self.assertEqual(word2.text1, "yathu")
        self.assertEqual(word2.text2, "")
        morph2 = word2.morphList[1]
        self.assertEqual(morph2.text1, "a-")
        self.assertEqual(morph2.gloss, "assocpx")
        self.assertEqual(morph2.pos, "Poss:assocpx")
        self.assertEqual(morph2.text2, "")


class TestHelpersTestCase(unittest.TestCase):

    def testPhonFieldHelper(self):
        exDict = dict()
        helper = phon_reader.PhonFieldHelper(exDict, False)
        self.assertTrue(not helper.hasContents())
        helper.add("ref", "ABC")
        self.assertTrue(helper.hasContents())
        helper.reset()
        self.assertTrue(not helper.hasContents())
        helper.add("phonetic", "123")
        self.assertTrue(helper.hasContents())
        helper.addEx()
        self.assertEqual(len(exDict.keys()), 0)
        self.assertEqual(len(helper.suggestions), 0)
        self.assertTrue(not helper.hasContents())
        helper.add("ref", "ABC")
        helper.add("phonetic", "123")
        helper.addEx()
        self.assertEqual(len(exDict.keys()), 1)
        self.assertEqual(len(helper.suggestions), 1)
        phonEx = exDict["abc"]
        self.assertEqual(phonEx.refText, "ABC")
        self.assertEqual(phonEx.phonetic, "123")
        self.assertEqual(phonEx.phonemic, "")
        self.assertEqual(phonEx.gloss, "")
        helper.addEx()
        helper.addEx()
        helper.add("ref", "BCD")
        helper.add("phonemic", "234")
        helper.addEx()
        self.assertEqual(len(exDict.keys()), 2)
        phonEx = exDict["bcd"]
        self.assertEqual(phonEx.phonemic, "234")
        phonEx = exDict["abc"]
        self.assertEqual(phonEx.phonemic, "")
        self.assertEqual(len(helper.suggestions), 1)
        sugg = helper.suggestions[0]
        self.assertEqual(sugg, "ABC")

    def testMergedMorphemes(self):
        mm = interlin_reader.MergedMorphemes()
        morph = lingex_structs.LingInterlinMorph()
        morph.gloss = "ham"
        morph.pos = "n"
        mm.add(morph)
        mm.add(morph)
        morphMerged = mm.getMorph(True)
        self.assertEqual(morphMerged.gloss, "ham-ham")
        self.assertEqual(morphMerged.pos, "n")

        mm = interlin_reader.MergedMorphemes()
        morph = lingex_structs.LingInterlinMorph()
        morph.gloss = "ham"
        morph.pos = "n"
        mm.add(morph)
        morph = lingex_structs.LingInterlinMorph()
        morph.gloss = "PL"
        morph.pos = "n.suff"
        mm.add(morph)
        morphMerged = mm.getMorph(True)
        self.assertEqual(morphMerged.gloss, "ham-PL")
        self.assertEqual(morphMerged.pos, "n")

        mm = interlin_reader.MergedMorphemes()
        morph = lingex_structs.LingInterlinMorph()
        morph.gloss = "the"
        morph.pos = "DET"
        mm.add(morph)
        morph = lingex_structs.LingInterlinMorph()
        morph.gloss = "cow"
        morph.pos = "n"
        mm.add(morph)
        morphMerged = mm.getMorph(True)
        self.assertEqual(morphMerged.gloss, "the-cow")
        self.assertEqual(morphMerged.pos, "n")

if __name__ == '__main__':
    testutil.run_suite(getSuite())
