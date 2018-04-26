# -*- coding: Latin-1 -*-
#
# This file created August 20 2015 by Jim Kornelsen
#
# 05-Oct-15 JDK  Log exceptions with logger.exception().
# 17-May-16 JDK  Added function to reload sys.modules.

"""
This is like Components.py but for code run from the user directory,
useful for catching exceptions while testing and debugging.

If the modules are in Scripts/python/pythonpath,
then it may be necessary to remove the lingt extension if installed,
or else the extension's pythonpath will override Scripts/python/pythonpath.
"""
import logging
import os
import platform
import sys
# pylint: disable=import-error
import uno
# pylint: enable=import-error

from lingt.ui.common import messagebox
from lingt.ui.comp import abbrevs
from lingt.ui.comp import applyconv
from lingt.ui.comp import bulkconv
from lingt.ui.comp import changermaker
from lingt.ui.comp import dataconv
from lingt.ui.comp import grabex
from lingt.ui.comp import gramsettings
from lingt.ui.comp import mkoxt_settings
from lingt.ui.comp import phonsettings
from lingt.ui.comp import scriptpractice
from lingt.ui.comp import spellingadjustments
from lingt.ui.comp import spellsearch
from lingt.ui.comp import spellstep
from lingt.ui.comp import wordlist
from lingt.utils import util

# These paths are used for logging and testing.
# Change them depending on your system.
# Also change lingt/utils/util.py and Components.py

LOGGING_ENABLED = False
#LOGGING_ENABLED = True  # Uncomment to turn on.
if platform.system() == "Windows":
    ROOTDIR = r"C:\OurDocs"
    #TOPLEVEL_LOGGER_FILEPATH = r"D:\dev\OOLT\debug.txt"
else:
    ROOTDIR = "/mnt/sf_OurDocs"
TOPLEVEL_LOGGER_FILEPATH = os.path.join(
    ROOTDIR, "computing", "Office", "OOLT_dev_extra", "debug.txt")


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
        if not LOGGING_ENABLED:
            return
        self._setup()
        self.logger.error('-' * 30)

    def log_exceptions(self, func):
        """Decorator method to log uncaught exceptions."""
        if not LOGGING_ENABLED:
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
        if not LOGGING_ENABLED:
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


def abbreviations(dummy_int=0):
    doShowDlg(abbrevs.showDlg)

def applyConverter(dummy_int=0):
    doShowDlg(applyconv.showDlg)

def bulkConversion(dummy_int=0):
    doShowDlg(bulkconv.showDlg)

def dataConversion(dummy_int=0):
    doShowDlg(dataconv.showDlg)

def goodSpellingsCheck(dummy_int=0):
    doShowDlg(spellsearch.showDlg)

def grammarGrabEx(dummy_int=0):
    doShowDlg(grabex.showGrammarDlg)

def grammarSettings(dummy_int=0):
    doShowDlg(gramsettings.showDlg)

def makeOxt(dummy_int=0):
    doShowDlg(mkoxt_settings.showDlg)

def makeSpellingChanger(dummy_int=0):
    doShowDlg(changermaker.showDlg)

def phonSettings(dummy_int=0):
    doShowDlg(phonsettings.showDlg)

def phonologyGrabEx(dummy_int=0):
    doShowDlg(grabex.showPhonologyDlg)

def scriptPractice(dummy_int=0):
    doShowDlg(scriptpractice.showDlg)

def spellingAdjustments(dummy_int=0):
    doShowDlg(spellingadjustments.showDlg)

def spellingStepper(dummy_int=0):
    doShowDlg(spellstep.showDlg)

def wordList(dummy_int=0):
    doShowDlg(wordlist.showDlg)


@logManager.log_exceptions
def aaa_del_sys_modules(dummy_int=0):
    """Normally it is necessary to restart Office in order to reload modules.
    To make a change to a lingt module without restarting, do the following:
    1. Run this function.
    2. Make the desired change to a module in lingt.
    [3. Make an arbitrary change to this file to cause it to reload.
        Running build/deploy_to_userdir.ps1 will update the modified timestamp,
        which makes it so that this step is not necessary.]
    (Steps 1-3 can be done in any order).
    4. Run build/deploy_to_userdir.ps1 to deploy the changes.
    5. Run the component again, which will now use the new changes.

    Note: "aaa_" prefix is just to move it up in the alphabetical list.
    """
    logManager.spacer()
    modules_count = 0
    for mod in list(sys.modules):
        if mod.startswith('lingt.') or mod.startswith('lingttest.'):
            del sys.modules[mod]
            modules_count += 1
    ctx = uno.getComponentContext()
    uno_objs = util.UnoObjs(ctx, util.UnoObjs.DOCTYPE_GENERIC)
    msgbox = messagebox.MessageBox(uno_objs)
    msgbox.display("Deleted " + str(modules_count) + " modules.")

@logManager.log_exceptions
def aab_disp_sys_modules(dummy_int=0):
    logManager.spacer()
    ctx = uno.getComponentContext()
    uno_objs = util.UnoObjs(ctx)
    msgbox = messagebox.MessageBox(uno_objs)
    msgbox.display(sorted(sys.modules.keys()))


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (
    abbreviations,
    applyConverter,
    bulkConversion,
    dataConversion,
    goodSpellingsCheck,
    grammarGrabEx,
    grammarSettings,
    makeOxt,
    makeSpellingChanger,
    phonSettings,
    phonologyGrabEx,
    scriptPractice,
    spellingAdjustments,
    spellingStepper,
    wordList,
    aaa_del_sys_modules,
    #aab_disp_sys_modules,
    )
