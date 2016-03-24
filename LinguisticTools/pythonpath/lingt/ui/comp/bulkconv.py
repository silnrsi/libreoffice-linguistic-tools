# -*- coding: Latin-1 -*-
#
# This file created April 6 2015 by Jim Kornelsen
#
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 16-Dec-15 JDK  Use folder picker.
# 04-Feb-16 JDK  Catch error messages for doConversion().
# 07-Mar-16 JDK  Write code for remaining itemStateChanged events.

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

    # which dialog step (which view)
    STEP_FILES = 1
    STEP_FONTS = 2

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        uservars.SettingsDocPreparer(
            uservars.Prefix.BULK_CONVERSION, unoObjs).prepare()
        self.userVars = uservars.UserVars(
            uservars.Prefix.BULK_CONVERSION, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.app = BulkConversion(unoObjs, self.userVars)
        self.dlg = None
        self.step = self.STEP_FILES
        self.convertOnClose = False
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        #self.dlg = dutil.createDialog(
        #    self.unoObjs, self.msgbox, "DlgBulkConversion")
        self.dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not self.dlg:
            return
        self.dlg.getModel().Step = self.step  # STEP_FILES (the first step)

        ctrl_getter = dutil.ControlGetter(dlg)
        step1Form = FormStep1(ctrl_getter, self.app)
        step1Form.start_working()
        step2Form = FormStep2(ctrl_getter, self.app)
        step2Form.start_working()
        closingButtons = ClosingButtons(ctrl_getter, dlg)
        closingButtons.start_working()
        #step1Form.loadData()
        #step2Form.loadData()

        ## Display the dialog

        self.dlgClose = self.dlg.endExecute
        self.dlg.execute()
        if self.step == self.STEP_FILES:
            step1Form.getResults()
        elif self.step == self.STEP_FONTS:
            step2Form.storeUserVars()
        if self.convertOnClose:
            try:
                self.app.doConversions()
            except exceptions.MessageError as exc:
                self.msgbox.displayExc(exc)
                return
        self.dlg.dispose()

    def isFirstStep(self):
        return self.step == self.STEP_FILES

    def gotoStep2(self):
        """Used as a callback."""
        self.step = self.STEP_FONTS
        self.dlg.getModel().Step = self.step  # change the dialog


class DlgEventHandler(XActionListener, XItemListener, XTextListener,
                      unohelper.Base):
    """Handles dialog events."""

    @dutil.log_event_handler_exceptions
    @dutil.do_not_enter_if_handling_event
    def itemStateChanged(self, itemEvent):
        """XItemListener event handler.
        For list controls or enabling and disabling.
        """
        logger.debug(util.funcName())
        src = itemEvent.Source
        #if dutil.sameName(src, self.step2Ctrls.listFontsUsed):
        if dutil.sameName(src, _dlgdef.LIST_FONTS_USED):
            self.step2Form.fill_for_selected_font()
        elif dutil.sameName(src, self.step2Ctrls.comboFontName):
            self.step2Ctrls.optNoStyle.setState(True)
            self.step2Form.getFontFormResults(ctrl_changed=src)
        elif dutil.sameName(src, self.step2Ctrls.comboParaStyle):
            self.step2Ctrls.optParaStyle.setState(True)
            self.step2Form.getFontFormResults(ctrl_changed=src)
            if self.step2Ctrls.optParaStyle.getState() == 1:
                self.step2Form.selectFontFromStyle(src, 'Paragraph')
        elif dutil.sameName(src, self.step2Ctrls.comboCharStyle):
            self.step2Ctrls.optCharStyle.setState(True)
            self.step2Form.getFontFormResults(ctrl_changed=src)
            if self.step2Ctrls.optCharStyle.getState() == 1:
                self.step2Form.selectFontFromStyle(src, 'Character')
        elif dutil.sameName(src, self.step2Ctrls.optParaStyle):
            self.step2Form.getFontFormResults(ctrl_changed=src)
            if self.step2Ctrls.comboParaStyle.getText():
                self.step2Form.selectFontFromStyle(src, 'Paragraph')
        elif dutil.sameName(src, self.step2Ctrls.optCharStyle):
            self.step2Form.getFontFormResults(ctrl_changed=src)
            if self.step2Ctrls.comboCharStyle.getText():
                self.step2Form.selectFontFromStyle(src, 'Character')
        elif dutil.sameName(src, self.step2Ctrls.optNoStyle):
            self.step2Form.getFontFormResults(ctrl_changed=src)
        elif dutil.sameName(src, self.step2Ctrls.chkShowConverted):
            if self.step2Form.samples.sampleIndex > -1:
                # Show the same sample again.
                self.step2Form.samples.sampleIndex -= 1
            self.step2Form.nextInputSample()
        elif dutil.sameName(src, self.step2Ctrls.chkReverse):
            self.step2Form.getFontFormResults(ctrl_changed=src)
            self.step2Form.fill_samples_for_selected_font()
        elif (dutil.sameName(src, self.step2Ctrls.optFontStandard)
              or dutil.sameName(src, self.step2Ctrls.optFontComplex)
              or dutil.sameName(src, self.step2Ctrls.optFontAsian)):
            self.step2Form.getFontFormResults(ctrl_changed=src)
        elif (dutil.sameName(src, self.step2Ctrls.chkJoinFontTypes)
              or dutil.sameName(src, self.step2Ctrls.chkJoinSize)
              or dutil.sameName(src, self.step2Ctrls.chkJoinStyles)):
            self.step2Form.fill_for_chkJoin()
        else:
            logger.warning("unexpected source %s", src.Model.Name)

    @dutil.log_event_handler_exceptions
    @dutil.do_not_enter_if_handling_event
    def textChanged(self, textEvent):
        """XTextListener event handler."""
        logger.debug(util.funcName())
        src = textEvent.Source
        if dutil.sameName(src, self.step2Ctrls.txtFontSize):
            self.step2Form.getFontFormResults(ctrl_changed=src)
            self.step2Ctrls.enableDisable(self.step2Form)
        else:
            logger.warning("unexpected source %s", src.Model.Name)

    @dutil.log_event_handler_exceptions
    @dutil.remember_handling_event
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "AddCurrentDoc":
            self.step1Form.addCurrentDoc()
        elif event.ActionCommand == "FileAdd":
            self.step1Form.addFile()
        elif event.ActionCommand == "FileRemove":
            self.step1Form.removeFile()
        elif event.ActionCommand == "ChooseFolder":
            self.step1Form.showFolderPicker()
        elif event.ActionCommand == "NextInput":
            self.step2Form.nextInputSample()
        elif event.ActionCommand == 'ResetFont':
            self.step2Form.resetFont()
        elif event.ActionCommand == 'CopyFont':
            self.step2Form.copyFont()
        elif event.ActionCommand == 'PasteFont':
            self.step2Form.pasteFont()
        elif event.ActionCommand == 'SelectConverter':
            self.step2Form.selectConverter()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


class ClosingButtons(evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, dlg):
        btnScan = dutil.getControl(dlg, 'btnScan')
        btnProcess = dutil.getControl(dlg, 'btnProcess')
        btnCancel = dutil.getControl(dlg, 'btnCancel')

    def add_listeners(self):
        btnScan.setActionCommand('ScanFiles')
        btnProcess.setActionCommand('Close_and_Convert')
        btnCancel.setActionCommand('Cancel')

    def handle_action_event(self, action_command):
        if event.ActionCommand == "ScanFiles":
            self.step1Form.scanFiles(self.step2Form)
        elif event.ActionCommand == 'Close_and_Convert':
            logger.debug("Closing and Converting...")
            self.mainDlg.convertOnClose = True
            self.mainDlg.dlgClose()
        elif event.ActionCommand == 'Cancel':
            logger.debug("Action command was Cancel")
            self.mainDlg.dlgClose()
        else:
            self.raise_unknown_command(action_command)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
