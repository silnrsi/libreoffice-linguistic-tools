# -*- coding: Latin-1 -*-
#
# This file created Sept 14 2010 by Jim Kornelsen
#
# 21-Sep-10 JDK  Renamed logging vars to be different from other packages.
# 04-Oct-10 JDK  Check for existence of directory for debug file.
# 22-Oct-10 JDK  UserVars should handle None values.
# 25-Oct-10 JDK  Custom uniqueList() instead of set().
# 28-Jun-11 JDK  Optionally use Linux file paths.  Added function getFloat().
# 23-Oct-12 JDK  Move UserVars to its own file.
# 12-Nov-12 JDK  UnoObjs can optionally take an existing document object.
# 14-Nov-12 JDK  Added sameName().
# 16-Nov-12 JDK  Get frame window.
# 21-Nov-12 JDK  Added getControl().
# 17-Dec-12 JDK  Make UnoObjs.getFromSocket() work for Calc.
# 25-Mar-13 JDK  Added getOpenDocs().
# 27-Apr-13 JDK  Added testing path.
# 08-May-13 JDK  Added uniqueList() again after it was removed.
# 13-May-13 JDK  Default to getting current document in loadDocObjs().
# 29-Jun-15 JDK  Added funcName().
# 06-Jul-15 JDK  Moved UI-specific functions to ui.dutils.
# 15-Jul-15 JDK  Removed safeStr().  Use "%s" instead.
# 07-Aug-15 JDK  Added setupLogging().
# 14-Oct-15 JDK  Uno objects for Impress.
# 23-May-16 JDK  Added a generic UnoObjs doc type.

"""
This module is used by most OOLT modules:
- Logging and debugging
- Manage OpenOffice UNO objects

Logging and debugging values in this file should be configured as needed;
there is no external logging configuration file.
There is also a higher level logger set up in Components.py which should
be configured as needed.

This module exports:
    UnoObjs - Manage UNO context and document objects.
    createProp() - Creates an UNO property.
    uniqueList() - Return a list with duplicates removed and order preserved.

    funcName() - Returns name of calling function.
    xray() - Displays a dialog to analyze UNO object attributes.
    debug_tellNextChar() - Tells character to right of cursor.

    BASE_FOLDER - Convenient location for test results.
    TESTDATA_FOLDER - Input test data files.
"""
import inspect
import logging
import os
import platform
import uno

from com.sun.star.beans import PropertyValue
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import RuntimeException

LOGGING_ENABLED = True
#LOGGING_ENABLED = False    # Set to False for production.

# These paths are used for logging and testing.
# Change them depending on your system.
if platform.system() == "Windows":
    #ROOTDIR = "C:" + os.path.sep + "OurDocs"
    BASE_FOLDER = r"D:\dev\OOLT"
else:
    #ROOTDIR = "/media/winC/OurDocs"
    ROOTDIR = "/media/sf_OurDocs"
    BASE_FOLDER = os.path.join(ROOTDIR, "computing", "Office", "OOLT")
LOGGING_FILEPATH = os.path.join(BASE_FOLDER, "debug.txt")
TESTDATA_FOLDER = os.path.join(
    BASE_FOLDER, "LinguisticTools", "tests", "datafiles")


def setupLogging():
    """Set up logging output format, where the output gets sent,
    and which classes have logging turned on and at what levels.
    """
    topLogger = logging.getLogger("lingt")
    topLogger.setLevel(logging.ERROR)
    if LOGGING_ENABLED:
        if os.path.exists(os.path.dirname(LOGGING_FILEPATH)):
            loggingFh = logging.FileHandler(LOGGING_FILEPATH, encoding='utf8')
            loggingFh.setLevel(logging.DEBUG)
            topFormatter = logging.Formatter(
                "%(asctime)s - %(filename)s %(lineno)d - %(message)s")
            loggingFh.setFormatter(topFormatter)
            for previousHandler in topLogger.handlers:
                topLogger.removeHandler(previousHandler)
            topLogger.addHandler(loggingFh)

    # Configure the values here to debug various packages.
    # Set either the entire application or else a
    # specific package to logging.DEBUG as desired.

    #configLogger = logging.getLogger("lingt.ui")
    configLogger = logging.getLogger("lingt")
    configLogger.setLevel(logging.DEBUG)

    #for loggerName in ("lingt.access.writer.frames",
    #                   "lingt.access.writer.Tables"):
    #    configLogger = logging.getLogger(loggerName)
    #    configLogger.setLevel(logging.WARN)

setupLogging()


class UnoObjs:
    """Manage UNO context and document objects.
    UNO is the API we use to interact with OpenOffice.
    """
    DOCTYPE_WRITER = 'writer'
    DOCTYPE_CALC = 'calc'
    DOCTYPE_IMPRESS = 'impress'
    DOCTYPE_GENERIC = 'generic'

    def __init__(self, ctx, doctype=DOCTYPE_WRITER,
                 loadFromContext=True, loadDocObjs=True):
        """
        :param doctype: DOCTYPE_WRITER, DOCTYPE_CALC or DOCTYPE_IMPRESS
        :param ctx: UNO context object obtained when script was loaded
        """
        # Calling uno.getComponentContext() here causes a bad crash.
        # Apparently in components, it is necessary to use the provided
        # context.
        self.ctx = ctx
        if loadFromContext:
            self.smgr = ctx.ServiceManager
            self.desktop = self.smgr.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx)
            self.dispatcher = self.smgr.createInstanceWithContext(
                "com.sun.star.frame.DispatchHelper", ctx)
            self.document = None
            if loadDocObjs:
                self.loadDocObjs(None, doctype)

    def loadDocObjs(self, newDocument=None, doctype=DOCTYPE_WRITER):
        """Load UNO objects from self.document into the current object."""
        self.document = newDocument
        if newDocument is None:
            # Get whatever has the active focus.
            # This is not always reliable on Linux when opening and closing
            # documents because of focus rules, so hang on to a reference to
            # the document when possible.
            self.document = self.desktop.getCurrentComponent()
        try:
            # This will fail if either the document was not obtained (a simple
            # NoneType error) or if the document was disposed.
            self.controller = self.document.getCurrentController()
        except AttributeError:
            raise AttributeError("Could not get document.")
        self.frame = self.controller.getFrame()
        self.window = self.frame.getContainerWindow()
        self.text = None
        self.viewcursor = None
        self.sheets = None
        self.sheet = None
        if doctype == self.DOCTYPE_WRITER:
            try:
                self.text = self.document.getText()
            except AttributeError:
                raise AttributeError("Could not get Writer document.")
            self.viewcursor = self.controller.getViewCursor()
        elif doctype == self.DOCTYPE_CALC:
            try:
                self.sheets = self.document.getSheets()
                self.sheet = self.sheets.getByIndex(0)
            except AttributeError:
                raise AttributeError("Could not get Calc spreadsheet.")
        elif doctype == self.DOCTYPE_IMPRESS:
            try:
                self.pages = self.document.getDrawPages()
                self.presentation = self.document.getPresentation()
            except AttributeError:
                raise AttributeError("Could not get Impress presentation.")
        elif doctype == self.DOCTYPE_GENERIC:
            pass
        else:
            raise AttributeError("Unexpected doc type %s" % doctype)

    def getDocObjs(self, newDocument, doctype=DOCTYPE_WRITER):
        """Factory method to manufacture new UnoObjs based on current UnoObjs
        and the given document.
        Returns the new UnoObjs object, and does not modify the current object.
        """
        newObjs = UnoObjs(self.ctx, loadFromContext=False)
        newObjs.smgr = self.smgr
        newObjs.desktop = self.desktop
        newObjs.dispatcher = self.dispatcher
        newObjs.loadDocObjs(newDocument, doctype)
        return newObjs

    @classmethod
    def getCtxFromSocket(cls):
        """Use when connecting from outside OOo, such as when testing."""
        localContext = uno.getComponentContext()
        resolver = localContext.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", localContext)
        ctx = resolver.resolve(
            "uno:socket,host=localhost,port=2002;urp;"
            "StarOffice.ComponentContext")
        return ctx

    def getOpenDocs(self, doctype='any'):
        """Returns unoObjs of currently open documents of type doctype."""
        doclist = []
        oComponents = self.desktop.getComponents()
        oDocs = oComponents.createEnumeration()
        while oDocs.hasMoreElements():
            oDoc = oDocs.nextElement()
            if oDoc.supportsService("com.sun.star.text.TextDocument"):
                if doctype in ['any', self.DOCTYPE_WRITER]:
                    doclist.append(self.getDocObjs(oDoc, self.DOCTYPE_WRITER))
            elif oDoc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                if doctype in ['any', self.DOCTYPE_CALC]:
                    doclist.append(self.getDocObjs(oDoc, self.DOCTYPE_CALC))
        return doclist


def createProp(name, value):
    """Creates an UNO property."""
    prop = PropertyValue()
    prop.Name = name
    prop.Value = value
    return prop


def uniqueList(seq):
    """Return a list with duplicates removed and order preserved.
    Taken from http://www.peterbe.com/plog/uniqifiers-benchmark
    """
    checked = []
    for e in seq:
        if e not in checked:
            checked.append(e)
    return checked


def xray(myObject, unoObjs):
    """For debugging.
    Displays a dialog to analyze UNO object attributes.
    To use this function, the XRay OpenOffice extension is required.
    """
    if not LOGGING_ENABLED:
        return
    mspf = unoObjs.smgr.createInstanceWithContext(
        "com.sun.star.script.provider.MasterScriptProviderFactory",
        unoObjs.ctx)
    scriptPro = mspf.createScriptProvider("")
    try:
        xScript = scriptPro.getScript(
            "vnd.sun.star.script:XrayTool._Main.Xray?" +
            "language=Basic&location=application")
    except:
        raise RuntimeException(
            "\nBasic library Xray is not installed", unoObjs.ctx)
    xScript.invoke((myObject,), (), ())


def funcName(location=None, obj=None, args='args_unspecified'):
    """
    For debugging.  Return name of calling function.
    :param location: 'begin', 'end', 'return', or None to not display location
    :param obj: the calling object; leave as None to not display class
    :param args: arguments or return values for the function
    """
    if not LOGGING_ENABLED:
        return ""
    callingFrame = []
    functionName = ""
    try:
        callingFrame = inspect.stack()[1]
        functionName = callingFrame[3]
    except TypeError:
        # I think an exception can get thrown if caller is not in a package.
        functionName = "someFunc"
    finally:
        del callingFrame
    className = ""
    if obj:
        className = "%s." % type(obj).__name__
    displayString = "%s%s()" % (className, functionName)
    locationString = ""
    if location in ('begin', 'end', 'return'):
        locationString = " " + location.upper()
    argString = ""
    if args != 'args_unspecified':
        argString = " = " + repr(args)
    return displayString + locationString + argString


def debug_tellNextChar(oCurs):
    """Tells the character to the right of where the cursor is at."""
    if not LOGGING_ENABLED:
        return "debug_tellNextChar() OFF"
    try:
        oCursDbg = oCurs.getText().createTextCursorByRange(oCurs.getStart())
        oCursDbg.goRight(1, True)
        val = oCursDbg.getString()
        return "cursAtChar '" + val + "'"
    except (RuntimeException, IllegalArgumentException):
        return "cursAtChar cannot get"
