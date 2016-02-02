# -*- coding: Latin-1 -*-
#
# This file created August 20 2015 by Jim Kornelsen
#
# 05-Oct-15 JDK  Log exceptions with logger.exception().

"""
This is like Components.py but for assimilated code,
useful for catching exceptions while testing and debugging.
Alternatively, run each assimilated component script individually.
"""
import logging
import os
import platform
# pylint: disable=import-error
import uno
# pylint: enable=import-error

from lingt.ui.comp import abbrevs
from lingt.ui.comp import applyconv
from lingt.ui.comp import bulkconv
from lingt.ui.comp import changermaker
from lingt.ui.comp import dataconv
from lingt.ui.comp import grabex
from lingt.ui.comp import gramsettings
from lingt.ui.comp import phonsettings
from lingt.ui.comp import scriptpractice
from lingt.ui.comp import spellingadjustments
from lingt.ui.comp import spellsearch
from lingt.ui.comp import spellstep
from lingt.ui.comp import wordlist

# Since this module is intended only for debugging and testing,
# logging should normally be enabled here.
TOPLEVEL_LOGGING_ENABLED = True
if platform.system() == "Windows":
    #ROOTDIR = r"C:\OurDocs"
    TOPLEVEL_LOGGER_FILEPATH = r"D:\dev\OOLT\debug.txt"
else:
    #ROOTDIR = "/media/winC/OurDocs"
    ROOTDIR = "/media/sf_OurDocs"
    TOPLEVEL_LOGGER_FILEPATH = os.path.join(
        ROOTDIR, "computing", "Office", "OOLT", "debug.txt")


class SimpleLogManager:
    """The main logging is set up in pythonpath/lingt/utils/util.py.
    However a simpler logger at this level is useful to detect
    problems that occur before the lingt classes are initialized as well as
    uncaught exceptions.

    This class wraps a standard logger.
    Always use logger.error().
    Logging will be set up as needed, so only call methods when output is
    needed.
    """
    def __init__(self):
        self.logger = None

    def spacer(self):
        if not TOPLEVEL_LOGGING_ENABLED:
            return
        self._setup()
        self.logger.error('-' * 30)

    def log_exceptions(self, func):
        """Decorator method to log uncaught exceptions."""
        if not TOPLEVEL_LOGGING_ENABLED:
            return func

        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as exc:
                self._setup()
                self.logger.exception(exc)
                # Re-raising is proper coding practice when catching all
                # exceptions, and we do so even though it will probably
                # have no effect, at least during runtime.
                raise

        return wrapper

    def _setup(self):
        """Set up a minimalist file logger."""
        if not TOPLEVEL_LOGGING_ENABLED:
            return
        if self.logger:
            return
        self.logger = logging.getLogger('oolt.componentsWrapper')
        loggingFh = logging.FileHandler(
            TOPLEVEL_LOGGER_FILEPATH, encoding='utf8')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        loggingFh.setFormatter(formatter)
        for previousHandler in self.logger.handlers:
            self.logger.removeHandler(previousHandler)
        self.logger.addHandler(loggingFh)

logManager = SimpleLogManager()


@logManager.log_exceptions
def doShowDlg(showDlgFunc):
    """
    Call the showDlg() function of a component module.
    :param showDlgFunc: a function that takes an UNO context argument
    """
    logManager.spacer()
    ctx = uno.getComponentContext()
    showDlgFunc(ctx)


def abbreviations():
    doShowDlg(abbrevs.showDlg)

def applyConverter():
    doShowDlg(applyconv.showDlg)

def bulkConversion():
    doShowDlg(bulkconv.showDlg)

def dataConversion():
    doShowDlg(dataconv.showDlg)

def goodSpellingsCheck():
    doShowDlg(spellsearch.showDlg)

def grammarGrabEx():
    doShowDlg(grabex.showGrammarDlg)

def grammarSettings():
    doShowDlg(gramsettings.showDlg)

def makeSpellingChanger():
    doShowDlg(changermaker.showDlg)

def phonSettings():
    doShowDlg(phonsettings.showDlg)

def phonologyGrabEx():
    doShowDlg(grabex.showPhonologyDlg)

def scriptPractice():
    doShowDlg(scriptpractice.showDlg)

def spellingAdjustments():
    doShowDlg(spellingadjustments.showDlg)

def spellingStepper():
    doShowDlg(spellstep.showDlg)

def wordList():
    doShowDlg(wordlist.showDlg)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (
    abbreviations,
    applyConverter,
    bulkConversion,
    dataConversion,
    goodSpellingsCheck,
    grammarGrabEx,
    grammarSettings,
    makeSpellingChanger,
    phonSettings,
    phonologyGrabEx,
    scriptPractice,
    spellingAdjustments,
    spellingStepper,
    wordList,
    )
