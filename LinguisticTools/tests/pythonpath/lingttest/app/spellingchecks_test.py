import logging
import unittest
# pylint: disable=import-error
import uno
# pylint: enable=import-error

from lingt.access.calc.spreadsheet_reader import SpreadsheetReader
from lingt.access.writer.uservars import Prefix, UserVars
from lingt.app.data import fileitemlist
from lingt.app.data.wordlist_structs import ColumnOrder
from lingt.app.svc import spellingchecks
from lingt.app.svc.wordlist import WordList
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.dep.spellreplace import DlgSpellingReplace
from lingt.utils import util

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent, PARAGRAPH_BREAK

logger = logging.getLogger("lingttest.spellingchecks_test")

def getSuite():
    testutil.modifyClass_showDlg(
        DlgSpellingReplace, methodName="makeDlg")
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    suite.addTest(SpellingChecksTestCase('testAffixesEN'))
    return suite

class SpellingChecksTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.userVars = UserVars(
            Prefix.SPELLING, self.unoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)

    def testAffixesEN(self):
        self.set_writer_contents()
        self.create_blank_wordlist()
        FILEPATH = testutil.output_path("wordListTemp.ods")
        wordListDoc = self.write_wordlist_file(FILEPATH)

        app = spellingchecks.SpellingChecker(self.unoObjs, self.userVars)
        config = spellingchecks.CheckerSettings()
        config.filepath = FILEPATH
        config.whichTask = 'SpellCheck'
        config.whichScope = 'WholeDoc'
        config.setAffixes("-ing\n-ed")
        config.punctuation = "."
        app.setConfig(config)

        def useDialog(innerSelf):
            innerSelf.evtHandler.actionPerformed(MyActionEvent("Add"))

        DlgSpellingReplace.useDialog = useDialog
        try:
            app.doSearch()
        except testutil.MsgSentException as exc:
            self.assertEqual(exc.msg, "Spell check finished.")
        else:
            self.fail("Expected error message.")

        reader = SpreadsheetReader(wordListDoc)
        stringList = reader.getColumnStringList("A", True)
        self.assertIn("jump", stringList)
        self.assertNotIn("jumping", stringList)
        self.assertNotIn("jumped", stringList)
        self.assertIn("runn", stringList)
        self.assertNotIn("running", stringList)
        wordListDoc.document.close(True)
        self.unoObjs.window.setFocus()  # so that getCurrentController() works

    def set_writer_contents(self):
        oText = self.unoObjs.text
        oVC = self.unoObjs.viewcursor
        oText.insertString(oVC, "My dog is running and jumping.", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        oText.insertString(oVC, "Now he can jump.", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        oText.insertString(oVC, "Yesterday he jumped.", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)

    def create_blank_wordlist(self):
        columnOrder = ColumnOrder(self.userVars)
        fileItemList = fileitemlist.FileItemList(
            fileitemlist.WordListFileItem, self.userVars)
        wordList = WordList(
            self.unoObjs, fileItemList, columnOrder, self.userVars)
        punct = ""
        try:
            wordList.generateList(punct, 'NFD')
        except testutil.MsgSentException as exc:
            self.assertTrue(exc.msg.startswith("Made list"))
        else:
            self.fail("Expected error message.")

    def write_wordlist_file(self, FILEPATH):
        props = (
            util.createProp('FilterName', 0),
            util.createProp('Overwrite', 1),
        )
        wordListDoc = self.unoObjs.getOpenDocs(util.UnoObjs.DOCTYPE_CALC)[0]
        wordListDoc.document.storeAsURL(
            uno.systemPathToFileUrl(FILEPATH), props)
        return wordListDoc

if __name__ == '__main__':
    testutil.run_suite(getSuite())
