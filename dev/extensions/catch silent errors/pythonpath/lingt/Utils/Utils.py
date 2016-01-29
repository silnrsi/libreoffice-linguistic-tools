#!/usr/bin/python
# -*- coding: Latin-1 -*-

# Utils.py
#
# Change History:
#   Created Sept 14 2010 by Jim Kornelsen
#
#   21-Sep-10 JDK  Renamed logging vars to be different from other packages.
#   04-Oct-10 JDK  Check for existence of directory for debug file.
#   22-Oct-10 JDK  UserVars should handle None values.
#   25-Oct-10 JDK  Custom uniqueList() instead of set().
#   28-Jun-11 JDK  Optionally use Linux file paths. Added function getFloat().
#   23-Oct-12 JDK  Move UserVars to its own file.
#   12-Nov-12 JDK  UnoObjs can optionally take an existing document object.
#   14-Nov-12 JDK  Added sameName().
#   16-Nov-12 JDK  Get frame window.
#   21-Nov-12 JDK  Added getControl().

"""
Contains functions that are helpful in many places:
- Set up logging
- Manage UNO objects provided by OOo
- String helpers
- Debugging routines
"""
import uno
import logging
from com.sun.star.uno import RuntimeException
import os
import platform

from lingt.App import Exceptions

#-------------------------------------------------------------------------------
# Initialize logging.
# - Executes when this module is loaded for the first time.
#-------------------------------------------------------------------------------
LOGGING_ENABLED  = True
#LOGGING_ENABLED  = False    # Set to False for production.

# Change this value depending on operating system and location
if platform.system() == "Windows" :
    BASE_FOLDER = r"D:\Jim\computing\Office\OOo Linguistic Tools" + "\\"
else:
    BASE_FOLDER = r"/media/winD/Jim/computing/Office/OOo Linguistic Tools/"

SOURCE_FOLDER    = BASE_FOLDER + "LinguisticTools" + os.sep # OOoLT zipped from
LOGGING_FILEPATH = BASE_FOLDER + "debug.txt"

topLogger = logging.getLogger("lingt")
topLogger.setLevel(logging.ERROR)
if LOGGING_ENABLED:
    if os.path.exists(os.path.dirname(LOGGING_FILEPATH)):
        loggingFh = logging.FileHandler(LOGGING_FILEPATH)
        loggingFh.setLevel(logging.DEBUG)
        topFormatter = logging.Formatter(
                    "%(asctime)s - %(filename)s %(lineno)d - %(message)s")
        loggingFh.setFormatter(topFormatter)
        for previousHandler in topLogger.handlers:
            topLogger.removeHandler(previousHandler)
        topLogger.addHandler(loggingFh)

## Configure the values here to debug various packages.
## Set either the entire application or else a
## specific package to logging.DEBUG as desired.

#configLogger = logging.getLogger("lingt.UI")
configLogger = logging.getLogger("lingt")
configLogger.setLevel(logging.DEBUG)

#for loggerName in ("lingt.Access.Writer.Frames",
#                   "lingt.Access.Writer.Tables"):
#    configLogger = logging.getLogger(loggerName)
#    configLogger.setLevel(logging.WARN)


def safeStr(s):
    """Make the string so it won't crash when concatenating."""
    if s is None: return ""
    return s

class UnoObjs:
    """A data structure to manage UNO context and document objects."""
    def __init__(self, ctx, doctype='writer', loadFromContext=True):
        self.ctx      = ctx
        self.document = None
        if loadFromContext:
            # Calling uno.getComponentContext() here causes a bad crash.
            # Apparently in components, it is necessary to use the provided
            # context.
            self.smgr       = ctx.ServiceManager
            self.desktop    = self.smgr.createInstanceWithContext(
                              "com.sun.star.frame.Desktop", ctx)
            self.dispatcher = self.smgr.createInstanceWithContext (
                              "com.sun.star.frame.DispatchHelper", ctx)
            self.getDocObjs(None, doctype)

    def serviceObjs(self):
        """
        Factory method to make an UnoObjs containing only context and service
        objects, not document-specific objects.
        """
        newObjs = UnoObjs(self.ctx, loadFromContext=False)
            # this is probably the only case where loadFromContext=False
        newObjs.smgr       = self.smgr
        newObjs.desktop    = self.desktop
        newObjs.dispatcher = self.dispatcher
        return newObjs

    def getDocObjs(self, document=None, doctype='writer'):
        if document:
            self.document = document
        else:
            self.document = self.desktop.getCurrentComponent()
        self.controller = self.document.getCurrentController()
        self.frame      = self.controller.getFrame()
        self.window     = self.frame.getContainerWindow()
        if doctype == 'writer':
            try:
                self.text = self.document.getText()
            except AttributeError:
                raise AttributeError, 'Could not get Writer document.'
            self.viewcursor = self.controller.getViewCursor()
        elif doctype == 'calc':
            try:
                self.sheets = self.document.getSheets()
                self.sheet  = self.sheets.getByIndex(0)
            except AttributeError:
                raise AttributeError, 'Could not get Calc spreadsheet.'
        else:
            raise AttributeError, 'Unexpected doc type ' + doctype

def getUnoObjsFromSocket():
    """Use when connecting from outside OOo. For testing."""
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext)
    ctx = resolver.resolve(
        "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    return UnoObjs(ctx)

def getControl(dlg, name):
    """Raises LogicError if control is not found."""
    ctrl = dlg.getControl(name)
    if not ctrl:
        raise Exceptions.LogicError("Error showing dialog: No %s control.",
                                    (name,))
    return ctrl

def createProp(name, value):
    """Creates an uno property."""
    prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    prop.Name  = name
    prop.Value = value
    return prop

def sameName(control1, control2):
    """
    Returns True if the UNO controls have the same name.
    This is the control name that is in the dialog designer,
    and also used with dlg.getControl().
    """
    return (control1.getModel().Name == control2.getModel().Name)

def xray(myObject, unoObjs):
    """For debugging.  To use this function, the XRay extension is required."""
    try:
        mspf = unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.script.provider.MasterScriptProviderFactory",
            unoObjs.ctx)
        scriptPro = mspf.createScriptProvider("")
        xScript = scriptPro.getScript(
            "vnd.sun.star.script:XrayTool._Main.Xray?" +
            "language=Basic&location=application")
        xScript.invoke((myObject,), (), ())
        return
    except:
        raise RuntimeException(
            "\nBasic library Xray is not installed", unoObjs.ctx)

class ConfigOptions:
    """
    A flexible structure to hold configuration options,
    typically settings that the user has selected or entered.
    Attributes can be created and used as needed.
    """
    pass

def debug_tellNextChar(oCurs):
    """Returns a message that tells the character to the right of where the
    cursor is at.  This is useful for debugging.
    """
    try:
        oCursDbg = oCurs.getText().createTextCursorByRange(oCurs.getStart())
        oCursDbg.goRight(1, True)
        val = oCursDbg.getString()
        return "cursAtChar '" + val + "'"
    except:
        return "cursAtChar cannot get"

