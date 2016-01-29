#!/usr/bin/python
# -*- coding: Latin-1 -*-

#
#
#
#
#
#  Hacked 17-Aug-2015 for development and testing
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# utils.py
#
# Change History:
#   Created Sept 14 2010 by Jim Kornelsen
#
#   21-Sep-10 JDK  Renamed logging vars to be different from other packages.
#   04-Oct-10 JDK  Check for existence of directory for debug file.
#   22-Oct-10 JDK  UserVars should handle None values.
#   25-Oct-10 JDK  Custom uniqueList() instead of set().
#   28-Jun-11 JDK  Optionally use Linux file paths.  Added function getFloat().
#   23-Oct-12 JDK  Move UserVars to its own file.
#   12-Nov-12 JDK  UnoObjs can optionally take an existing document object.
#   14-Nov-12 JDK  Added sameName().
#   16-Nov-12 JDK  Get frame window.
#   21-Nov-12 JDK  Added getControl().
#   17-Dec-12 JDK  Make UnoObjs.getFromSocket() work for Calc.
#   25-Mar-13 JDK  Added getOpenDocs().
#   27-Apr-13 JDK  Added testing path.
#   08-May-13 JDK  Added uniqueList() again after it was removed.
#   13-May-13 JDK  Default to getting current document in loadDocObjs().
#   29-Jun-15 JDK  Added funcName().
#   06-Jul-15 JDK  Moved UI-specific functions to UI.Dutils.
#   15-Jul-15 JDK  Removed safeStr().  Use "%s" instead.
#   07-Aug-15 JDK  Added setupLogging().

"""
This module is used by most OOLT modules:
- Logging and debugging
- Manage OpenOffice UNO objects

Logging and debugging values in this file should be configured as needed;
there is no external logging configuration file.

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

LOGGING_ENABLED = True
#LOGGING_ENABLED = False    # Set to False for production.

# These paths are used for logging and testing.
# Change them depending on your system.
if platform.system() == "Windows":
    ROOTDIR = r"C:" + os.path.sep
else:
    ROOTDIR = r"/media/winC"
BASE_FOLDER = os.path.join( 
    ROOTDIR, "Users", "JimStandard", "Desktop", "logging_test")
#BASE_FOLDER = os.path.join(ROOTDIR, "OurDocs", "computing", "Office", "OOLT")
LOGGING_FILEPATH = os.path.join(BASE_FOLDER, "debug.txt")
TESTDATA_FOLDER = os.path.join(
    BASE_FOLDER, "LinguisticTools", "developing", "tests", "data files")

def setupLogging():
    """Set up logging output format, where the output gets sent,
    and which classes have logging turned on and at what levels.
    """
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

def funcName(location=None):
    """For debugging.  Return name of calling function."""
    if not LOGGING_ENABLED:
        return ""
    #callingFrame = inspect.stack()[1]
    #functionName = callingFrame[3] + "()"
    #if location in ('begin', 'end'):
    #    return "%s %s" % (functionName, location.upper())
    #return functionName
    return "funcName"

# Executes when this module is loaded for the first time.
setupLogging()

