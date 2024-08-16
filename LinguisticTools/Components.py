"""
Handles the events from the Linguistics menu, defined in Addons.xcu.

Python scripts in LibreOffice extensions must be implemented as PyUNO
components, and this file contains the component definitions.

Scripts are imported from the pythonpath subfolder,
which LibreOffice automatically adds to the path.
The import from this file must be done at runtime or else it
leads to a failure while adding the extension to LibreOffice.
Scripts in the pythonpath subfolder will not be reloaded until LibreOffice is
completely closed and restarted.

There are no functions in this file to be run from Tools > Macros > Run Macro.
Instead, run one of the component showDlg() functions, for example in
pythonpath/lingt/ui/comp/abbrevs.py.
"""
# pylint: disable=import-outside-toplevel

import logging
import os
import platform

# uno is required for unohelper
# pylint: disable=unused-import
import uno
# pylint: enable=unused-import
import unohelper
from com.sun.star.task import XJobExecutor

# This is defined in idl/XCalcFunctions.idl
# pylint: disable=import-error
from name.JimK.LinguisticTools.CalcFunctions import XCalcFunctions
# pylint: enable=import-error

# These paths are used for logging and testing.
# Change them depending on your system.
# Also change lingt/utils/util.py and tests/ComponentsWrapper.py

LOGGING_ENABLED = False
#LOGGING_ENABLED = True  # Uncomment to turn on.
if platform.system() == "Windows":
    BASE_FOLDER = r"C:\OurDocs\computing\Office\LOLT_dev_extra"
else:
    BASE_FOLDER = "/home/jkornels/LOLT_dev_extra"
TOPLEVEL_LOGGER_FILEPATH = os.path.join(BASE_FOLDER, "debug.txt")

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
            except:
                self._setup()
                self.logger.exception("Caught exception at top level.")
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
        self.logger = logging.getLogger('lolt.Components')
        loggingFh = logging.FileHandler(TOPLEVEL_LOGGER_FILEPATH)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        loggingFh.setFormatter(formatter)
        for previousHandler in self.logger.handlers:
            self.logger.removeHandler(previousHandler)
        self.logger.addHandler(loggingFh)

logManager = SimpleLogManager()

class JobWrapper(unohelper.Base, XJobExecutor):
    """A base class that can be used as the job for an UNO component.
    Catches exceptions that happen while running showDialog().
    """
    def __init__(self, ctx):
        if self.__class__ is JobWrapper:
            # The base class should not be instantiated.
            raise NotImplementedError()
        self.ctx = ctx

    @logManager.log_exceptions
    def trigger(self, dummy_sEvent):
        """XJobExecutor requires this worker method, which will be called to
        execute the component.
        """
        logManager.spacer()
        self.showDialog()

    def showDialog(self):
        # Pylint will be upset if this method is not implemented.
        raise NotImplementedError()

class PhonologySettingsJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.phonsettings import showDlg
        showDlg(self.ctx)

class PhonologyGrabExJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.grabex import showPhonologyDlg
        showPhonologyDlg(self.ctx)

class InterlinSettingsJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.interlinsettings import showDlg
        showDlg(self.ctx)

class InterlinGrabExJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.grabex import showInterlinDlg
        showInterlinDlg(self.ctx)

class AbbreviationsJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.abbrevs import showDlg
        showDlg(self.ctx)

class DataConversionJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.dataconv import showDlg
        showDlg(self.ctx)

class BulkConversionJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.bulkconv import showDlg
        showDlg(self.ctx)

class MakeOxtJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.mkoxt_settings import showDlg
        showDlg(self.ctx)

class ScriptPracticeJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.scriptpractice import showDlg
        showDlg(self.ctx)

class WordListJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.wordlist import showDlg
        showDlg(self.ctx)

class SpellingAdjustmentsJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.spellingadjustments import showDlg
        showDlg(self.ctx)

class SpellingStepperJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.spellstep import showDlg
        showDlg(self.ctx)

class ApplyConverterJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.applyconv import showDlg
        showDlg(self.ctx)

class GoodSpellingsCheckJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.spellsearch import showDlg
        showDlg(self.ctx)

class MakeSpellingChangerJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.changermaker import showDlg
        showDlg(self.ctx)

class DrawConverterJob(JobWrapper):
    def __init__(self, ctx):
        JobWrapper.__init__(self, ctx)

    def showDialog(self):
        from lingt.ui.comp.dataconv_draw import showDlg
        showDlg(self.ctx)

class StringReverserAddIn(unohelper.Base, XCalcFunctions):
    def __init__(self, ctx):
        self.ctx = ctx

    @staticmethod
    def factory(ctx):
        return StringReverserAddIn(ctx)

    def reverse(self, inString):
        """Note: For some reason decorating with @logManager.log_exceptions
        makes it not work in Calc.
        """
        from lingt.app.calcfunctions import reverseString
        return reverseString(inString)

## Define the components in this module.

g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    PhonologySettingsJob,
    "name.JimK.LinguisticTools.PhonologySettings",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    PhonologyGrabExJob,
    "name.JimK.LinguisticTools.PhonologyGrabExamples",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    InterlinSettingsJob,
    "name.JimK.LinguisticTools.InterlinSettings",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    InterlinGrabExJob,
    "name.JimK.LinguisticTools.InterlinGrabExamples",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    AbbreviationsJob,
    "name.JimK.LinguisticTools.Abbreviations",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    DataConversionJob,
    "name.JimK.LinguisticTools.DataConversion",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    BulkConversionJob,
    "name.JimK.LinguisticTools.BulkConversion",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    MakeOxtJob,
    "name.JimK.LinguisticTools.MakeOxt",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    ScriptPracticeJob,
    "name.JimK.LinguisticTools.ScriptPractice",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    WordListJob,
    "name.JimK.LinguisticTools.WordList",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    SpellingAdjustmentsJob,
    "name.JimK.LinguisticTools.SpellingCharComp",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    SpellingStepperJob,
    "name.JimK.LinguisticTools.SpellingStepper",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    ApplyConverterJob,
    "name.JimK.LinguisticTools.ApplyConverter",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    GoodSpellingsCheckJob,
    "name.JimK.LinguisticTools.GoodSpellingsCheck",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    MakeSpellingChangerJob,
    "name.JimK.LinguisticTools.MakeSpellingChanger",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    DrawConverterJob,
    "name.JimK.LinguisticTools.DrawConverter",
    ("com.sun.star.task.Job",),)

g_ImplementationHelper.addImplementation(
    StringReverserAddIn.factory,
    "name.JimK.LinguisticTools.ReverseStringImpl",
    ("com.sun.star.sheet.AddIn",),)
