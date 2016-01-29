# -*- coding: Latin-1 -*-
#
# This file created 23-Oct-2010 by Jim Kornelsen
#
# 29-Sep-15 Expect exception to allow automated testing.

"""
Verify that the message box seems to be working.

It might be helpful to visually check if a message box is displayed correctly.
To do this, use ad_hoc_testing.py, adding code similar to below.
"""
import logging
import unittest

from lingt.ui import messagebox
from lingttest.utils import testutil

logger = logging.getLogger("lingttest.messagebox_test")


def getSuite():
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    suite.addTest(MessageBoxTestCase('testMessageBox'))
    return suite


class MessageBoxTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()

    def testMessageBox(self):
        msgbox = messagebox.MessageBox(self.unoObjs)
        displayText = "Hello there\n\n\tHow are you?\nFine, thank you\t"
        displayTitle = "An unimportant testing message"
        with self.assertRaises(testutil.MsgSentException) as contextMgr:
            msgbox.display(displayText, title=displayTitle)
        self.assertEqual(contextMgr.exception.msg, displayText)

        # The constructor should fail if we don't pass any unoObjs.
        self.assertRaises(AttributeError, messagebox.MessageBox, None)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
