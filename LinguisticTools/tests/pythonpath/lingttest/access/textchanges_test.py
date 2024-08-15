import logging
import unittest

from lingt.access.writer import textchanges

from lingttest.utils import testutil
from lingttest.utils.testutil import PARAGRAPH_BREAK

logger = logging.getLogger("lingttest.textchanges_test")

def getSuite():
    suite = unittest.TestSuite()
    suite.addTest(TextChangesTestCase('testChangeString'))
    return suite

class TextChangesTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()

    def testChangeString(self):
        oText = self.unoObjs.text           # shorthand variable name
        oVC = self.unoObjs.viewcursor     # shorthand variable name

        oVC.gotoStartOfLine(False)
        oText.insertString(oVC, "Hello there, how are you?", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)

        oVC.goLeft(1, False)
        oVC.gotoStartOfLine(False)
        oVC.goRight(len("Hello "), False)
        oVC.goRight(len("there"), True)
        textchanges.changeString(oVC, "THERE")

        oVC.gotoStartOfLine(False)
        oVC.goRight(len("Hello there"), True)
        self.assertEqual(oVC.getString(), "Hello THERE")
        oVC.collapseToEnd()
        oVC.goDown(1, False)

if __name__ == '__main__':
    testutil.run_suite(getSuite())
