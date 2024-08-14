"""
Originally this was used with "nested tables.odt"
"""
import logging
import os
import unittest

from lingttest.utils import testutil

from lingt.access.writer.doc_reader import DocReader
from lingt.access.writer.textsearch import TextSearch
from lingt.app.data import fileitemlist
from lingt.ui.common.progressbar import ProgressBar
from lingt.utils import util

logger = logging.getLogger("lingttest.search_test")

def getSuite():
    suite = unittest.TestSuite()
    for method_name in (
            'test1_selection',
            'test2_wholeDoc',
        ):
        suite.addTest(SearchTestCase(method_name))
    return suite

class SearchTestCase(unittest.TestCase):

    INFILE = os.path.join(util.TESTDATA_FOLDER, "search nested items.odt")

    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.textSearch = None
        self.unoObjs = None
        self.progressBar = None

    def setUp(self):
        unoObjs = testutil.unoObjsForCurrentDoc()
        fileconfig = fileitemlist.WordListFileItem(None)
        docReader = DocReader(fileconfig, unoObjs, -1)
        docReader.loadDoc(self.INFILE)
        self.unoObjs = docReader.doc
        testutil.stored.doc = self.unoObjs.document
        self.progressBar = ProgressBar(self.unoObjs, "TestSearch")

    def test1_selection(self):
        self.unoObjs.viewcursor.gotoStart(False)  # needed for AOO 23-May-16
        self.unoObjs.viewcursor.goRight(1, True)  # select
        self.textSearch = TextSearch(self.unoObjs, self.progressBar)
        self.textSearch.scopeSelection()
        self.unoObjs.viewcursor.goRight(0, False)  # deselect
        self.assertEqual(len(self.textSearch.getRanges()), 1)
        #self.displayRanges()  # uncomment for debugging

    def test2_wholeDoc(self):
        self.textSearch = TextSearch(self.unoObjs, self.progressBar)
        self.textSearch.scopeWholeDoc()
        self.assertEqual(len(self.textSearch.getRanges()), 20)
        #self.displayRanges()  # uncomment for debugging

    def displayRanges(self):
        """Show where each range is located in the document.
        Do not use for automated testing because it will add more ranges,
        causing the assertions to fail.
        """
        ranges = self.textSearch.getRanges()
        print("found ", len(ranges), " ranges")
        i = 1
        for txtRange in ranges:
            oSel = txtRange.sel
            oCursor = oSel.getText().createTextCursorByRange(oSel)
            if not oCursor:
                print("could not get range ", i)
                continue
            oCursor.CharBackColor = 15138560    # yellow
            oCursor.collapseToEnd()
            oCursor.getText().insertString(oCursor, "(" + str(i) + ")", False)
            i += 1

    @classmethod
    def tearDownClass(cls):
        #unoObjs = util.UnoObjs(
        #    testutil.stored.getContext(), loadDocObjs=False)
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)

if __name__ == '__main__':
    testutil.run_suite(getSuite())
