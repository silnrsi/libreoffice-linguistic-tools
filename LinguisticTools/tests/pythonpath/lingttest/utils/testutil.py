# -*- coding: Latin-1 -*-
#
# This file created by Jim Kornelsen on April 29, 2013
#
# 13-May-13 JDK  Store context globally.
# 10-Jul-13 JDK  Write displayed messages to file.
# 11-Jul-13 JDK  Added verifyRegexMethods().
# 20-Aug-15 JDK  Added class CommonUnoObjs instead of global statements.
# 07-Sep-15 JDK  Exec with the class's module dict rather than globals().
# 11-Sep-15 JDK  Added do_dispose().
# 15-Sep-15 JDK  Fixed modifyFilePicker() assimilation problem.
# 28-Sep-15 JDK  Added run_suite().
# 29-Sep-15 JDK  Added getDefaultStyle().
# 30-Sep-15 JDK  Match dlg.execute$ for DlgSpellingReplace.
# 09-Dec-15 JDK  Added clear_messages_sent()

# Disable warnings related to modifying code dynamically, useful for testing.
# pylint: disable=exec-used,unused-argument

"""
Utilities for the test suite.

Also consider using unittest.mock.
"""

import inspect
import logging
import os
import platform
import re
import sys
import unittest
# pylint: disable=import-error,unused-import
#import uno  # This may no longer be needed.  Remove if tests pass.
# pylint: enable=import-error,unused-import

# Used in modules that import testutil.
# pylint: disable=unused-import
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
# pylint: enable=unused-import

from lingt.app import exceptions
from lingt.ui.common import filepicker
from lingt.ui.common.messagebox import MessageBox, FourButtonDialog
from lingt.utils import util

logger = logging.getLogger("lingttest.testutil")


class CommonUnoObjs:
    """Store some UNO objects for all tests.
    We could use property decorators but it would make it harder to follow how
    this class gets used.
    """
    def __init__(self):
        self.ctx = None
        self.doc = None  # writer doc
        self.calc_doc = None
        self.product_name = None

    def getContext(self):
        if self.ctx is None:
            self.ctx = util.UnoObjs.getCtxFromSocket()
        return self.ctx

    def getProductName(self):
        """Reads value in an XML file stored at a location like
        C:/Program Files/LibreOffice 5/share/registry/main.xcd

        Returns either "LibreOffice" or "OpenOffice".
        """
        if self.product_name is None:
            ctx = self.getContext()
            smgr = ctx.ServiceManager
            aConfigProvider = smgr.createInstanceWithContext(
                "com.sun.star.configuration.ConfigurationProvider", ctx)
            prop = util.createProp("nodepath", "/org.openoffice.Setup/Product")
            oNode = aConfigProvider.createInstanceWithArguments(
                "com.sun.star.configuration.ConfigurationAccess", (prop,))
            self.product_name = oNode.getByName("ooName")
        return self.product_name

stored = CommonUnoObjs()


def blankWriterDoc(unoObjs):
    """Closes all current documents and opens a new writer doc.
    Sets unoObjs to the new blank document.
    Be sure to update any objects that reference the old unoObjs.
    """
    doclist = unoObjs.getOpenDocs()
    for docUnoObjs in doclist:
        docUnoObjs.document.close(True)
    newDoc = unoObjs.desktop.loadComponentFromURL(
        "private:factory/swriter", "_blank", 0, ())
    unoObjs.loadDocObjs(newDoc)
    stored.doc = unoObjs.document

def blankCalcSpreadsheet(unoObjs):
    """Closes all current documents and opens a new calc spreadsheet.
    Also opens a new writer doc.
    Sets unoObjs to the new blank writer document,
    and returns the new calc uno objects.
    Be sure to update any objects that reference the old unoObjs.
    """
    blankWriterDoc(unoObjs)
    newDoc = unoObjs.desktop.loadComponentFromURL(
        "private:factory/scalc", "_blank", 0, ())
    calcUnoObjs = unoObjs.getDocObjs(newDoc, util.UnoObjs.DOCTYPE_CALC)
    stored.calc_doc = calcUnoObjs.document
    return calcUnoObjs


def unoObjsForCurrentDoc():
    return _unoObjsForDoc(stored.doc, util.UnoObjs.DOCTYPE_WRITER)

def unoObjsForCurrentSpreadsheet():
    return _unoObjsForDoc(stored.calc_doc, util.UnoObjs.DOCTYPE_CALC)

def _unoObjsForDoc(document, doctype):
    unoObjs = util.UnoObjs(stored.getContext(), loadDocObjs=False)
    unoObjs.loadDocObjs(document, doctype)
    return unoObjs


def setupTestLogging():
    """Further setup in addition to what's in lingt.utils.util"""
    ## Set up a logger that will ignore most messages
    #topLogger = logging.getLogger("lingt")
    #topLogger.setLevel(logging.ERROR)
    #loggingSh = logging.StreamHandler()
    #topLogger.addHandler(loggingSh)

    topLogger = logging.getLogger("lingt")
    topLogger.debug("got topLogger")
    try:
        loggingSh = topLogger.handlers[0]
    except IndexError:
        exc = IndexError(
            "The main logger in lingt.utils.util does not seem to have "
            "been initialized correctly.  "
            "Make sure LOGGING_ENABLED is set to True, and "
            "verify that %s exists." % util.LOGGING_FILEPATH)
        exc.__cause__ = None
        raise exc
    topTestLogger = logging.getLogger("lingttest")
    topTestLogger.addHandler(loggingSh)
    topTestLogger.setLevel(logging.DEBUG)
    logger.warning("-----%s-----", util.funcName())

# Executes when this module is loaded for the first time.
setupTestLogging()


class MyActionEvent:
    """Objects to pass to actionPerformed()."""
    def __init__(self, actionCommand):
        self.ActionCommand = actionCommand


# Don't inspect the same function twice, because the second time the
# source code is just a string rather than stored in a file.
# Inspect.findsource() requires a file, so it will fail the second time.
modifiedFunctions = set()

def modifyClass_showDlg(klass, methodName="showDlg"):
    """Modify showDlg() to call useDialog() instead of execute().
    As a result, the dialog does not wait for user interaction.
    """
    fnStr = "%s.%s" % (klass, methodName)
    #print(fnStr)
    if fnStr in modifiedFunctions:
        return
    modifiedFunctions.add(fnStr)

    # Get the code as a string and modify the string.
    code = inspect.getsource(getattr(klass, methodName))
    modifiedMethodName = methodName + "Modified"
    code = re.sub(methodName, modifiedMethodName, code)
    code = re.sub(r"dlg.execute\(\)", "self.useDialog()", code)
    code = re.sub(r"dlg.execute$", "self.useDialog", code, flags=re.M)
    code = re.sub(r"dlg.dispose\(\)", "pass", code)
    code = re.sub(
        r"\s{8}if not ((?:self\.)?)dlg:\s+return",
        r"""
        if \1dlg:
            self.dlgDispose = \1dlg.dispose
        else:
            return
        """,
        code, flags=re.M)
    pat = re.compile("^    ", re.M)
    code = re.sub(pat, "", code)  # decrease indent
    #print(code)  # for debugging

    # Compile the string and then attach the new function to the class.
    if klass.__module__ in sys.modules:
        klass_globals = sys.modules[klass.__module__].__dict__
    else:
        logger.warning("'%s' not in sys.modules", klass.__module__)
        klass_globals = globals()
    exec(code, klass_globals)
    setattr(klass, methodName, klass_globals[modifiedMethodName])


# List of tuples (msg, msg_args).
messages_sent = []

messageLogger = logging.getLogger('messages')

def clear_messages_sent():
    # Would like to do messages_sent.clear() but not in python 2.
    del messages_sent[:]

class MsgSentException(exceptions.MessageError):
    """Capture the message instead of displaying it to the user."""
    pass

def setupMessageLogger():
    outfilepath = os.path.join(util.BASE_FOLDER, "testMessages.txt")
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    fileHandler = logging.FileHandler(outfilepath)
    fileHandler.setFormatter(formatter)
    fileHandler.setLevel(logging.DEBUG)
    messageLogger.setLevel(logging.DEBUG)
    messageLogger.addHandler(fileHandler)

setupMessageLogger()

def record_message(message, msg_args):
    """Remember messages so they can be verified later."""
    messages_sent.append((message, msg_args))
    try:
        interpolated_message = message % msg_args
        messageLogger.info(interpolated_message)
    except (TypeError, UnicodeDecodeError):
        messageLogger.info(message)

def modifyMsgboxDisplay():
    """Modify lingt.ui.messagebox.MessageBox.display() to throw an exception
    instead of actually displaying a message.
    Also log messages so we can check them manually if needed.
    """
    if not hasattr(MessageBox, 'display_original'):
        MessageBox.display_original = MessageBox.display

        def newFunc(self, message, *msg_args, **kwargs):
            record_message(message, msg_args)
            raise MsgSentException(message, msg_args)

        MessageBox.display = newFunc

def restoreMsgboxDisplay():
    """Reverses what modifyMsgboxDisplay() did."""
    if hasattr(MessageBox, 'display_original'):
        MessageBox.display = MessageBox.display_original
        del MessageBox.display_original

def modifyMsgboxFour(retval):
    """Modify lingt.ui.messagebox.FourButtonDialog.display() to return the
    specified value instead of actually displaying a message.
    Keep the message in messages_sent so it can be checked.
    Also log messages so we can check them manually if needed.
    """
    def newFunc(self, message, *msg_args, **kwargs):
        record_message(message, msg_args)
        return retval
    FourButtonDialog.display = newFunc

def modifyMsgboxOkCancel(retval):
    """Modify lingt.ui.messagebox.MessageBox.displayOkCancel() to return the
    specified value instead of actually displaying a message.
    """
    def newFunc(*args):
        return retval
    MessageBox.displayOkCancel = newFunc

def modifyMsgboxYesNoCancel(retval):
    """Modify lingt.ui.messagebox.MessageBox.displayYesNoCancel() to return the
    specified value instead of actually displaying a message.
    """
    def newFunc(*args):
        return retval
    MessageBox.displayYesNoCancel = newFunc


def modifyFilePicker(retval):
    """Modify lingt.ui.filepicker.showFilePicker() to return the specified
    value instead of actually displaying a message.
    """
    logger.debug(util.funcName('begin'))
    def newFunc(*args):
        logger.debug(util.funcName('end', args=retval))
        return retval
    # showFilePicker() will be in the main module when assimilated.
    # assimilate: global showFilePicker
    filepicker.showFilePicker = newFunc
    logger.debug(util.funcName('end'))


def verifyRegexMethods(selfParam):
    """unittest prior to 2.7 was very incomplete.
    In newer versions names of some methods have changed as well.
    This function renames some methods to support different python versions.
    """
    try:
        # python 3.2 names
        # pylint: disable=pointless-statement
        selfParam.assertRegex
        selfParam.assertNotRegex
        # pylint: enable=pointless-statement
    except AttributeError:
        try:
            # python 2.7 names
            selfParam.assertRegex = selfParam.assertRegexpMatches
            selfParam.assertNotRegex = selfParam.assertNotRegexpMatches
        except AttributeError:
            selfParam.fail("Please use unittest2 for Python 2.6.")


def normalize_newlines(strval):
    """Returns string with normalized newlines.  The result uses Unix style
    newlines, although the main goal of this function is simply to ensure
    that the string will be identical no matter what platform the input was
    sent from.  This allows string comparisons.
    """
    # Windows => Unix (CR+LF = decimal 13 and 10)
    strval = strval.replace("\r\n", "\n")
    # Mac => Unix
    strval = strval.replace("\r", "\n")
    return strval


def do_dispose(modified_dlg):
    """
    :param modified_dlg: a dialog whose class has been modified by
                         modifyClass_showDlg()
    """
    # pylint: disable=no-member
    if modified_dlg.dlgDispose:
        modified_dlg.dlgDispose()
    # pylint: enable=no-member


def run_suite(test_suite):
    """Run a test suite."""
    unittest.TextTestRunner(verbosity=2).run(test_suite)


def getDefaultFont():
    if (stored.getProductName() == "OpenOffice"
            and platform.system() == "Windows"):
        return "Times New Roman"
    else:
        return "Liberation Serif"

def getDefaultStyle():
    if stored.getProductName() == "LibreOffice":
        return "Default Style"
    else:
        return "Default"

