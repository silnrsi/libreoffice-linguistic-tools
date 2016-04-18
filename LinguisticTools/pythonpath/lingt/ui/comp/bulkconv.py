# -*- coding: Latin-1 -*-
#
# This file created April 6 2015 by Jim Kornelsen
#
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 16-Dec-15 JDK  Use folder picker.
# 04-Feb-16 JDK  Catch error messages for doConversion().
# 07-Mar-16 JDK  Write code for remaining itemStateChanged events.
# 18-Apr-16 JDK  Handle which step in a separate class.

"""
Bulk OpenOffice document conversion dialog,
with a blank Writer document used to store settings.
The conversion work is done outside of OpenOffice at the XML level,
except that non-ODT files are first saved into ODT format using OpenOffice.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener

from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.bulkconversion import BulkConversion
from lingt.ui import dutil
from lingt.ui.dep import bulkconv_step1
from lingt.ui.dep import bulkconv_step2
from lingt.ui.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.ui.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgbulkconv")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgBulkConversion(unoObjs)
    dlg.showDlg()

class DlgBulkConversion:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        stepper = DlgStepper(dlg)
        ctrl_getter = dutil.ControlGetter(dlg)
        app = BulkConversion(unoObjs)
        step1Form = FormStep1(ctrl_getter, app, stepper)
        step1Form.start_working()
        step2Form = FormStep2(ctrl_getter, app)
        step2Form.start_working()
        closingButtons = ClosingButtons(
            ctrl_getter, app, step1Form, step2Form, dlg.endExecute)
        closingButtons.start_working()

        ## Display the dialog

        dlg.execute()
        if stepper.on_step1():
            step1Form.storeResults()
        if stepper.on_step2():
            step2Form.storeResults()
        if closingButtons.convertOnClose:
            try:
                app.doConversions()
            except exceptions.MessageError as exc:
                msgbox = MessageBox(self.unoObjs)
                msgbox.displayExc(exc)
                return
        dlg.dispose()


class DlgStepper:
    """Manage which step the dialog is on."""

    # which dialog step (which view)
    STEP_FILES = 1
    STEP_FONTS = 2

    def __init__(self, dlg):
        self.dlg = dlg
        self._step = self.STEP_FILES
        self._change_dialog_view()

    def on_step1(self):
        return self._step == self.STEP_FILES

    def on_step2(self):
        return self._step == self.STEP_FONTS

    def goto_step2(self):
        self._step = self.STEP_FONTS
        self._change_dialog_view()

    def _change_dialog_view(self):
        """Change which controls the dialog shows."""
        self.dlg.getModel().Step = self._step


class ClosingButtons(evt_handler.ActionEventHandler,
                     evt_hander.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step1Form, step2Form, dlgClose):
        self.app = app
        self.step1Form = step1Form
        self.step2Form = step2Form
        self.dlgClose = dlgClose
        btnScan = dutil.getControl(dlg, 'btnScan')
        btnProcess = dutil.getControl(dlg, 'btnProcess')
        btnCancel = dutil.getControl(dlg, 'btnCancel')
        self.chkVerify = dutil.getControl(dlg, 'chkVerify')
        self.convertOnClose = False

    def load_values(self):
        self.chkVerify.setState(self.app.userVars.getInt('AskEachChange'))

    def add_listeners(self):
        btnScan.setActionCommand('ScanFiles')
        btnProcess.setActionCommand('Close_and_Convert')
        btnCancel.setActionCommand('Cancel')

    def handle_action_event(self, action_command):
        if event.ActionCommand == "ScanFiles":
            self.step1Form.scanFiles(self.step2Form)
        elif event.ActionCommand == 'Close_and_Convert':
            logger.debug("Closing and Converting...")
            self.convertOnClose = True
            self.dlgClose()
        elif event.ActionCommand == 'Cancel':
            logger.debug("Action command was Cancel")
            self.convertOnClose = False
            self.dlgClose()
        else:
            self.raise_unknown_command(action_command)

    def handle_item_event(self, dummy_src):
        pass


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
