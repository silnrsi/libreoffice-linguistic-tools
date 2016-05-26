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

from lingt.app import exceptions
from lingt.app.svc.bulkconversion import BulkConversion
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.dep.bulkconv_step1 import FormStep1
from lingt.ui.dep.bulkconv_step2 import FormStep2
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.ui.common.messagebox import MessageBox
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
    """Main class for this dialog.
    We use a class instead of a simple function to make testing code easier.
    """

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.step1Form = None
        self.step2Form = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        app = BulkConversion(self.unoObjs)
        self.step1Form = FormStep1(ctrl_getter, app)
        self.step1Form.start_working()
        self.step2Form = FormStep2(ctrl_getter, app)
        self.step2Form.start_working()
        stepper = DlgStepper(dlg)
        advancer = AdvanceHandler(
            ctrl_getter, stepper, self.step1Form, self.step2Form)
        advancer.start_working()
        closingButtons = ClosingButtons(ctrl_getter, dlg.endExecute)
        closingButtons.start_working()

        ## Display the dialog

        dlg.execute()
        if stepper.on_step1():
            self.step1Form.store_results()
        if stepper.on_step2():
            self.step2Form.store_results()
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


class AdvanceHandler(evt_handler.ActionEventHandler):
    """Handle button to advance to step 2."""

    def __init__(self, ctrl_getter, stepper, step1Form, step2Form):
        self.stepper = stepper
        self.step1Form = step1Form
        self.step2Form = step2Form
        self.btnScan = ctrl_getter.get(_dlgdef.BTN_SCAN)

    def add_listeners(self):
        self.btnScan.setActionCommand('ScanFiles')
        self.btnScan.addActionListener(self)

    def handle_action_event(self, dummy_action_command):
        try:
            self.step1Form.scanFiles()
        except exceptions.MessageError:
            return
        self.stepper.goto_step2()
        self.step2Form.refresh_and_fill_list()


class ClosingButtons(evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, dlgClose):
        self.dlgClose = dlgClose
        self.btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)
        self.btnProcess = ctrl_getter.get(_dlgdef.BTN_PROCESS)
        self.convertOnClose = False

    def add_listeners(self):
        self.btnProcess.setActionCommand('Close_and_Convert')
        self.btnCancel.setActionCommand('Cancel')
        for ctrl in (self.btnProcess, self.btnCancel):
            ctrl.addActionListener(self)

    def handle_action_event(self, action_command):
        if action_command == 'Close_and_Convert':
            self.convertOnClose = True
        elif action_command == 'Cancel':
            self.convertOnClose = False
        else:
            evt_handler.raise_unknown_action(action_command)
        self.dlgClose()


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
