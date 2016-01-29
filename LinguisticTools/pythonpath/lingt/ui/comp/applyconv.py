# -*- coding: Latin-1 -*-
#
# This file created Nov 16 2012 by Jim Kornelsen
#
# 04-Mar-13 JDK  Added comboHidden and chkSkipFirstRow.
# 11-Mar-13 JDK  Simplify remembering converter name between dialog calls.
# 09-Apr-13 JDK  Default to ConvSourceColumn set by wordlist.py.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.

"""
Dialog to apply an SIL converter.
Could be expanded to perform other conversions in the future, although I'm not
sure what, because EncConverters does everything useful that I can think of.

This module exports:
    showDlg()
"""
import uno
import unohelper
import logging
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XTextListener

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.dataconversion import DataConversion
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgapplyconv")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    calcUnoObjs = util.UnoObjs(ctx, doctype=util.UnoObjs.DOCTYPE_CALC)
    logger.debug("got UNO context")

    dlg = DlgApplyConverter(calcUnoObjs)
    dlg.showDlg()

class DlgApplyConverter:
    """Main class for this dialog."""

    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        self.msgbox = MessageBox(self.unoObjs)
        USERVAR_PREFIX = "LTw_"  # LinguisticTools Word List variables
        finder = uservars.SettingsDocFinder(USERVAR_PREFIX, calcUnoObjs)
        writerUnoObjs = finder.getWriterDoc()
        self.userVars = uservars.UserVars(
            USERVAR_PREFIX, writerUnoObjs.document, logger)
        self.app = DataConversion(calcUnoObjs, self.userVars, styleFonts=None)
        self.sourceCol = ""
        self.targetCol = ""
        self.skipFirstRow = True
        self.convertOnClose = False
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgApplyConverter")
        if not dlg:
            return
        self.evtHandler = DlgEventHandler(self)
        try:
            self.dlgCtrls = DlgControls(self.unoObjs, dlg, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.dlgCtrls.loadValues(self.userVars)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.convertOnClose:
            self.app.doConversions_calc(
                self.sourceCol, self.targetCol, self.skipFirstRow)
        dlg.dispose()

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        converter = self.app.selectConverter()
        self.dlgCtrls.txtConverterName.setText(converter.convName)
        self.dlgCtrls.chkDirectionReverse.setState(not converter.forward)
        logger.debug(util.funcName('end'))

    def closeAndConvert(self):
        logger.debug(util.funcName('begin'))
        converter = self.getFormResults()
        try:
            self.app.setAndVerifyConverter(converter)
            self.convertOnClose = True
            self.dlgClose()
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
        logger.debug(util.funcName('end'))

    def getFormResults(self):
        """
        Reads form fields and stores user vars.
        returns: converter settings
        """
        logger.debug(util.funcName('begin'))
        converter = ConverterSettings(self.userVars)
        converter.loadUserVars()  # for normForm
        converter.convName = self.dlgCtrls.txtConverterName.getText()
        converter.forward = (
            self.dlgCtrls.chkDirectionReverse.getState() == 0)
        converter.storeUserVars()
        self.sourceCol = self.dlgCtrls.txtSourceCol.getText()
        self.targetCol = self.dlgCtrls.txtTargetCol.getText()
        self.skipFirstRow = bool(self.dlgCtrls.chkSkipRow.getState())
        self.userVars.store("ConvSourceColumn", self.sourceCol)
        self.userVars.store("ConvTargetColumn", self.targetCol)
        self.userVars.store("SkipFirstRow",
                            str(self.dlgCtrls.chkSkipRow.getState()))
        logger.debug(util.funcName('end'))
        return converter


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.txtConverterName = dutil.getControl(dlg, "txtConvName")
        self.chkDirectionReverse = dutil.getControl(dlg, "chkReverse")
        self.txtSourceCol = dutil.getControl(dlg, "txtSourceColumn")
        self.txtTargetCol = dutil.getControl(dlg, "txtTargetColumn")
        self.chkSkipRow = dutil.getControl(dlg, "chkSkipFirstRow")
        btnSelect = dutil.getControl(dlg, "btnSelect")
        btnConvert = dutil.getControl(dlg, "btnConvert")
        btnCancel = dutil.getControl(dlg, "btnCancel")
        comboHidden = dutil.getControl(dlg, "cmbxHidden")

        ## Listeners

        # The comboHidden control isn't used by the user,
        # nor do we override textChanged.
        # Its purpose is to prevent a crash that occurs in Ubuntu.
        # Hopefully in the future we will find another solution, but this
        # seems to work for now.
        comboHidden.addTextListener(self.evtHandler)  # calls textChanged

        btnSelect.setActionCommand("SelectConverter")
        btnConvert.setActionCommand("Close_and_Convert")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnSelect, btnConvert, btnCancel):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars):
        converter = ConverterSettings(userVars)
        converter.loadUserVars()
        self.txtConverterName.setText(converter.convName)
        self.chkDirectionReverse.setState(not converter.forward)

        ## Other fields

        self.txtSourceCol.setText(userVars.get("ConvSourceColumn"))
        self.txtTargetCol.setText(userVars.get("ConvTargetColumn"))

        varname = "SkipFirstRow"
        if not userVars.isEmpty(varname):
            self.chkSkipRow.setState(userVars.getInt(varname))


class DlgEventHandler(XActionListener, XTextListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "SelectConverter":
            self.mainForm.selectConverter()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        elif event.ActionCommand == "Close_and_Convert":
            self.mainForm.closeAndConvert()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
