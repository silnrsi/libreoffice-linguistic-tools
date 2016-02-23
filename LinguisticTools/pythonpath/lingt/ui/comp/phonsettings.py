# -*- coding: Latin-1 -*-
#
# This file created Dec 22 2009 by Jim Kornelsen
#
# 24-Dec-09 JDK  Split into a separate file for dialogs.
# 07-Jan-10 JDK  Make the script filenames related to menu options.
# 11-Feb-10 JDK  Import LIFT data from Flex.
# 31-Mar-10 JDK  Add localization.
# 09-Sep-10 JDK  Always set a default combo box value.
# 14-Sep-10 JDK  Divide into packages.
# 08-Oct-10 JDK  Set SFM file defaults.
# 29-Oct-10 JDK  Writing system is a struct rather than a list.
# 01-Jul-11 JDK  User var to use experimental transcription for phonemic.
# 17-Apr-13 JDK  Don't show writing system chooser if none are found.
# 14-May-13 JDK  Rename DlgSettings to unique name for assimilation.
# 05-Jul-13 JDK  Radio buttons for which Flex field is phonemic.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.

"""
Dialog for settings to import Phonology examples.

This module exports:
    showDlg()
"""
import logging
import re

import uno
import unohelper
from com.sun.star.awt import XActionListener

from lingt.access.writer.styles import PhonologyStyles
from lingt.access.writer.uservars import UserVars, PhonologyTags
from lingt.app import exceptions
from lingt.app import lingex_structs
from lingt.ui import dutil
from lingt.ui.dep.writingsystem import DlgWritingSystem
from lingt.ui.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgphonsettings")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgPhonSettings(unoObjs)
    dlg.showDlg()

class DlgPhonSettings:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        USERVAR_PREFIX = "LTp_"  # LinguisticTools Phonology variables
        self.userVars = UserVars(USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgPhnlgySettings")
        if not dlg:
            return
        self.evtHandler = DlgEventHandler(self)
        try:
            self.dlgCtrls = DlgControls(
                self.unoObjs, dlg, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.dlgCtrls.loadValues(self.userVars)

        self.dlgClose = dlg.endExecute
        dlg.execute()
        dlg.dispose()

    def selectWritingSys(self):
        logger.debug(util.funcName('begin'))
        logger.debug("Selecting Writing System...")

        filepath = self.dlgCtrls.fileControl.getText()
        if not re.search(r"\.lift$", filepath):
            self.msgbox.display(
                "If you want to use LIFT data, then first specify a "
                "LIFT file exported from FieldWorks.")
            return
        defaultCode = self.dlgCtrls.txtWritingSys.getText()
        dlgWS = DlgWritingSystem(defaultCode, self.unoObjs)
        dlgWS.readFile(filepath)
        if len(dlgWS.writingSystems) == 0:
            self.msgbox.display("No writing systems found.")
            return
        dlgWS.showDlg()
        writingSystem = dlgWS.getResult()
        dlgWS.call_dispose()
        self.dlgCtrls.txtWritingSys.setText(writingSystem.internalCode)

    def storeAndClose(self):
        logger.debug(util.funcName('begin'))
        outSettings = lingex_structs.PhonOutputSettings(self.userVars)
        outSettings.showBrackets = bool(
            self.dlgCtrls.checkboxBrackets.getState())
        outSettings.phonemicLeftmost = bool(
            self.dlgCtrls.optionPhonemicFirst.getState())
        outSettings.storeUserVars()

        inSettings = lingex_structs.PhonInputSettings(self.userVars)
        inSettings.filepath = self.dlgCtrls.fileControl.getText()
        inSettings.phoneticWS = self.dlgCtrls.txtWritingSys.getText()
        inSettings.isLexemePhonetic = bool(
            self.dlgCtrls.optionLexemePht.getState())
        inSettings.storeUserVars()

        PhonologyStyles(self.unoObjs, self.userVars).createStyles()
        PhonologyTags(self.userVars).loadUserVars()
        self.dlgClose()
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.fileControl = dutil.getControl(dlg, "InputFile")
        self.checkboxBrackets = dutil.getControl(dlg, "CheckboxBrackets")
        self.txtWritingSys = dutil.getControl(dlg, "TxtWritingSystem")
        self.optionLexemePht = dutil.getControl(dlg, "optLexemePht")
        self.optionLexemePhm = dutil.getControl(dlg, "optLexemePhm")
        self.optionPhonemicFirst = dutil.getControl(dlg, "OptPhonemicFirst")
        self.optionPhoneticFirst = dutil.getControl(dlg, "OptPhoneticFirst")
        btnSelectWS = dutil.getControl(dlg, "BtnSelectWS")
        buttonOK = dutil.getControl(dlg, "ButtonOK")
        buttonCancel = dutil.getControl(dlg, "ButtonCancel")

        btnSelectWS.setActionCommand("SelectWritingSys")
        buttonOK.setActionCommand("Ok")
        buttonCancel.setActionCommand("Cancel")
        for ctrl in (btnSelectWS, buttonOK, buttonCancel):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars):
        """Set default values of controls."""
        self.fileControl.setText(userVars.get("XML_filePath"))
        varname = "ShowBrackets"
        if not userVars.isEmpty(varname):
            self.checkboxBrackets.setState(userVars.getInt(varname))

        self.txtWritingSys.setText(userVars.get("PhoneticWritingSystem"))
        if userVars.get("FlexLexeme") == "phonemic":
            self.optionLexemePhm.setState(True)
        elif userVars.get("FlexLexeme") == "phonetic":
            self.optionLexemePht.setState(True)
        if userVars.get("Leftmost") == "phonetic":
            self.optionPhoneticFirst.setState(True)

class DlgEventHandler(XActionListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "SelectWritingSys":
            self.mainForm.selectWritingSys()
        elif event.ActionCommand == "Ok":
            self.mainForm.storeAndClose()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
