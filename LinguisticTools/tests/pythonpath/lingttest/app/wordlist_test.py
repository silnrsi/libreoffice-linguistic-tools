"""
Test generating various kinds of word lists using
lingt.app.svc.wordlist.WordList.

See also:
    lingttest.ui.dlg_wordlist  # TODO
    lingttest.ui.wordlistfile_test
    lingttest.app.spellingchecks_test  # tests empty list
"""
import logging
import os
import unittest

from lingt.access.calc.spreadsheet_reader import SpreadsheetReader
from lingt.access.writer.uservars import Prefix, UserVars
from lingt.app.data import fileitemlist
from lingt.app.data.wordlist_structs import ColumnOrder, WhatToGrab
from lingt.app.svc.wordlist import WordList
from lingt.utils import util

from lingttest.utils import testutil

logger = logging.getLogger("lingttest.app.wordlist_test")

FILEPATH = os.path.join(util.TESTDATA_FOLDER, "styles and fonts.odt")

def getSuite():
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    suite.addTest(WordListTestCase('test1_paragraphStyles'))
    return suite

class WordListTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.userVars = UserVars(
            Prefix.SPELLING, self.unoObjs.document, logger)

    def test1_paragraphStyles(self):
        dataSets = [
            [("Heading 1",),
             ("My", "big",),
             ("Now", "now", "will")],
            [("Heading 1", "Caption", "Preformatted Text"),
             ("My", "big", "Now", "now", "will"),
             ()],
            ]
        for dataSet in dataSets:
            styleNames, expectedStrings, notExpectedStrings = dataSet
            fileItem = fileitemlist.WordListFileItem(self.userVars)
            fileItem.filetype = 'writerdoc'
            fileItem.filepath = FILEPATH
            for styleName in styleNames:
                whatToGrab = WhatToGrab(None)
                whatToGrab.grabType = WhatToGrab.PARASTYLE
                whatToGrab.whichOne = styleName
                fileItem.thingsToGrab.append(whatToGrab)
            columnOrder = ColumnOrder(self.userVars)
            fileItemList = fileitemlist.FileItemList(
                fileitemlist.WordListFileItem, self.userVars)
            fileItemList.addItem(fileItem)
            wordList = WordList(
                self.unoObjs, fileItemList, columnOrder, self.userVars)
            try:
                wordList.generateList(". ?", 'NFD')
            except testutil.MsgSentException as exc:
                self.assertTrue(exc.msg.startswith("Made list"), msg=exc.msg)
            else:
                self.fail("Expected error message.")

            stringList = getColumnStringList(self.unoObjs)
            for testString in expectedStrings:
                self.assertIn(testString, stringList, msg=repr(styleNames))
            for testString in notExpectedStrings:
                self.assertNotIn(testString, stringList, msg=repr(styleNames))

    @classmethod
    def tearDownClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankWriterDoc(unoObjs)

def getColumnStringList(unoObjs, col="A"):
    doclist = unoObjs.getOpenDocs(util.UnoObjs.DOCTYPE_CALC)
    wordListDoc = doclist[0]
    reader = SpreadsheetReader(wordListDoc)
    stringList = reader.getColumnStringList(col, True)
    wordListDoc.document.close(True)
    # so that getCurrentController() works
    unoObjs.window.setFocus()
    return stringList

if __name__ == '__main__':
    testutil.run_suite(getSuite())
