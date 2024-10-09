"""
Utilities for the test suite.
Also consider using unittest.mock.
"""
# Disable warnings related to modifying code dynamically, useful for testing.
# pylint: disable=exec-used,unused-argument

import inspect
import logging
import os
import platform
import re
import sys
import unittest
import uno  # pylint: disable=import-error,unused-import

# Used in modules that import testutil.
from com.sun.star.text.ControlCharacter import (
    PARAGRAPH_BREAK)  # pylint: disable=unused-import

from lingt.app import exceptions
from lingt.ui.common import filepicker
from lingt.ui.common.messagebox import MessageBox, FourButtonDialog
from lingt.utils import util

logger = logging.getLogger("lingttest.testutil")

def getDefaultFont(fontType='Western'):
    """Uncomment or otherwise change the values below to match your system's
    default font.
    
    When possible, instead of calling this method, read from unstyled text
    so that the test passes on any system without adjustments.

    Be sure that Asian and CTL support (says "defaults") are checked under
    Tools > Options > Languages and Locales > General.
    """
    if fontType == 'Complex':
        if platform.system() == "Windows":
            return "Arial"
            #return "Mangal"
            #return "Ezra SIL"
        else:
            return "FreeSans"
            #return "Lohit Hindi"
    elif fontType == 'Asian':
        return "NSimSun"
        #return "SimSun"
    else:
        return "Liberation Serif"
        #return "Times New Roman"

def getDefaultStyles():
    """Make sure the name of your default style is included in this list.
    The name varies by system and version, although 'Standard' should always
    be the underlying name.
    """
    return [
        "Default Paragraph Style",
        "No Character Style",
        "Default Style",
        "Default",
        "Standard"]

class TestCaseWithFixture(unittest.TestCase):
    """Keep track of which fixture we're using and include it in
    failure reports.
    """
    def __init__(self, testCaseName):
        super().__init__(testCaseName)

    def setUp(self):
        self.fixture_report = ""

    def _do_assertion(self, assertion_method, *args, **kwargs):
        try:
            assertion_method(*args, **kwargs)
        except AssertionError as ex:
            if self.fixture_report:
                ex.args = (f"{ex.args[0]}\nFixture: {self.fixture_report}",)
                raise
            raise

    def assertEqual(self, *args, **kwargs):
        self._do_assertion(super().assertEqual, *args, **kwargs)

    def assertNotEqual(self, *args, **kwargs):
        self._do_assertion(super().assertNotEqual, *args, **kwargs)

    def assertIn(self, *args, **kwargs):
        self._do_assertion(super().assertIn, *args, **kwargs)

    def assertNotIn(self, *args, **kwargs):
        self._do_assertion(super().assertNotIn, *args, **kwargs)

class CommonUnoObjs:
    """Store some UNO objects for all tests.
    We could use property decorators but it would make it harder to follow how
    this class gets used.
    """
    def __init__(self):
        self.ctx = None
        self.doc = None  # writer doc
        self.calc_doc = None
        self.draw_doc = None
        self.product_name = None

    def getContext(self):
        if self.ctx is None:
            self.ctx = util.UnoObjs.getCtxFromSocket()
        return self.ctx

    def getPlainUnoObjs(self):
        """Get basic UNO objects not including document objects."""
        return util.UnoObjs(self.getContext(), loadDocObjs=False)

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

def _closeAllOpenDocs(unoObjs):
    doclist = unoObjs.getOpenDocs()
    for docUnoObjs in doclist:
        docUnoObjs.document.close(True)

def blankWriterDoc(unoObjs=None):
    """Closes all current documents and opens a new document.
    Sets unoObjs to the new blank document.
    Be sure to update any objects that reference the old unoObjs.
    """
    if not unoObjs:
        unoObjs = stored.getPlainUnoObjs()
    _closeAllOpenDocs(unoObjs)
    newDoc = unoObjs.desktop.loadComponentFromURL(
        "private:factory/swriter", "_blank", 0, ())
    unoObjs.loadDocObjs(newDoc)
    stored.doc = unoObjs.document

def blankSpreadsheet(unoObjs=None):
    """Closes all current documents and opens a new spreadsheet.
    Sets unoObjs to the new blank writer document,
    and returns the new calc uno objects.
    Be sure to update any objects that reference the old unoObjs.
    """
    if not unoObjs:
        unoObjs = stored.getPlainUnoObjs()
    _closeAllOpenDocs(unoObjs)
    newDoc = unoObjs.desktop.loadComponentFromURL(
        "private:factory/scalc", "_blank", 0, ())
    calcUnoObjs = unoObjs.getDocObjs(newDoc, util.UnoObjs.DOCTYPE_CALC)
    stored.calc_doc = calcUnoObjs.document
    return calcUnoObjs

def blankDrawing(unoObjs=None):
    """Closes all current documents and opens a new drawing.
    Sets unoObjs to the new blank writer document,
    and returns the new calc uno objects.
    Be sure to update any objects that reference the old unoObjs.
    """
    if not unoObjs:
        unoObjs = stored.getPlainUnoObjs()
    _closeAllOpenDocs(unoObjs)
    newDoc = unoObjs.desktop.loadComponentFromURL(
        "private:factory/sdraw", "_blank", 0, ())
    drawUnoObjs = unoObjs.getDocObjs(newDoc, util.UnoObjs.DOCTYPE_DRAW)
    stored.draw_doc = drawUnoObjs.document
    return drawUnoObjs

def unoObjsForCurrentDoc():
    return _unoObjsForDoc(stored.doc, util.UnoObjs.DOCTYPE_WRITER)

def unoObjsForCurrentSpreadsheet():
    return _unoObjsForDoc(stored.calc_doc, util.UnoObjs.DOCTYPE_CALC)

def unoObjsForCurrentDrawing():
    return _unoObjsForDoc(stored.draw_doc, util.UnoObjs.DOCTYPE_DRAW)

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
    """Objects to pass to DlgEventHandler.actionPerformed()."""
    def __init__(self, actionCommand):
        self.ActionCommand = actionCommand

class MyTextEvent:
    """Objects to pass to DlgEventHandler.textChanged()."""
    def __init__(self, source):
        self.Source = source

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
        logger.warning(
            "Message '%s' failed to interpolate arguments %r",
            message, msg_args)

def modifyMsgboxDisplay():
    """Modify lingt.ui.messagebox.MessageBox.display() to throw an exception
    instead of actually displaying a message.
    Also log messages so we can check them manually if needed.
    """
    if not hasattr(MessageBox, 'display_original'):
        MessageBox.display_original = MessageBox.display

        def newFunc(self, message, *msg_args, **kwargs):
            record_message(message, msg_args)
            raise MsgSentException(message, *msg_args)

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

def output_path(filename):
    """Write files here for testing.  These can be deleted when finished,
    or just ignored.
    """
    return os.path.join(
        os.path.expanduser("~"), "Documents", "LOLT_testing", filename)
