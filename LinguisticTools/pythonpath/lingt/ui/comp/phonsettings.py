"""
Dialog for settings to import lexical examples for phonology.

This module exports:
    showDlg()
"""
import logging
import re

import uno
import unohelper
from com.sun.star.awt import XActionListener

from lingt.access.writer.styles import PhonologyStyles
from lingt.access.writer.uservars import Prefix, UserVars, PhonologyTags
from lingt.app import exceptions
from lingt.app.data import lingex_structs
from lingt.app.svc import lingexamples
from lingt.app.svc.lingexamples import EXTYPE_PHONOLOGY
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.dlgdefs import DlgPhnlgySettings as _dlgdef
from lingt.ui.dep.writingsystem import DlgWritingSystem
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
        self.userVars = UserVars(Prefix.PHONOLOGY, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.app = lingexamples.ExServices(EXTYPE_PHONOLOGY, unoObjs)
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
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
        try:
            self.app.verifyRefnums()
        except (exceptions.DataNotFoundError,
                exceptions.DataInconsistentError) as exc:
            ok = self.msgbox.displayOkCancel(exc.msg, *exc.msg_args)
            if not ok:
                return

        PhonologyStyles(self.unoObjs, self.userVars).createStyles()
        PhonologyTags(self.userVars).loadUserVars()
        self.dlgClose()
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.fileControl = ctrl_getter.get(_dlgdef.INPUT_FILE)
        self.checkboxBrackets = ctrl_getter.get(_dlgdef.CHECKBOX_BRACKETS)
        self.txtWritingSys = ctrl_getter.get(_dlgdef.TXT_WRITING_SYSTEM)
        self.optionLexemePht = ctrl_getter.get(_dlgdef.OPT_LEXEME_PHT)
        self.optionLexemePhm = ctrl_getter.get(_dlgdef.OPT_LEXEME_PHM)
        self.optionPhonemicFirst = ctrl_getter.get(_dlgdef.OPT_PHONEMIC_FIRST)
        self.optionPhoneticFirst = ctrl_getter.get(_dlgdef.OPT_PHONETIC_FIRST)
        btnSelectWS = ctrl_getter.get(_dlgdef.BTN_SELECT_WS)
        buttonOK = ctrl_getter.get(_dlgdef.BUTTON_OK)
        buttonCancel = ctrl_getter.get(_dlgdef.BUTTON_CANCEL)

        btnSelectWS.setActionCommand("SelectWritingSys")
        buttonOK.setActionCommand("OK")
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

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "SelectWritingSys":
            self.mainForm.selectWritingSys()
        elif event.ActionCommand == "OK":
            self.mainForm.storeAndClose()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (showDlg,)
