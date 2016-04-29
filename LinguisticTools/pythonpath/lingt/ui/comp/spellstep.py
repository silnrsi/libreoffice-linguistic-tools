# -*- coding: Latin-1 -*-
#
# This file created Dec 17 2012 by Jim Kornelsen
#
# 22-Feb-13 JDK  Changed "Don't give suggestions" to a positive statement.
# 01-Mar-13 JDK  Slide to maxRow instead of dataLen.
# 29-Mar-13 JDK  Go directly to row 2 when creating dialog.
# 09-Apr-13 JDK  Remember row number where we left off.
# 15-Apr-13 JDK  Disable Set Correction button if word is unchanged.
# 18-Apr-13 JDK  Clearing correction should check Correct.
# 25-Apr-13 JDK  Fixed bug: displayOkCancel, not displayYesNo.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 05-Aug-15 JDK  Use constants for threeway checkbox.

"""
Step through a word list to make spelling corrections.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener
from com.sun.star.awt import XAdjustmentListener

from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.spellingchecks import SpellingStepper
from lingt.ui.common import dutil
from lingt.ui.common.dlgdefs import DlgSpellStep as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgspellstep")


def showDlg(ctx=uno.getComponentContext()):
    logger.debug("----showDlg-------------------------------------------------")
    calcUnoObjs = util.UnoObjs(ctx, util.UnoObjs.DOCTYPE_CALC)
    logger.debug("got UNO context")
    dlg = DlgSpellingStep(calcUnoObjs)
    dlg.showDlg()

class DlgSpellingStep:
    """Main class for this dialog."""

    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        finder = uservars.SettingsDocFinder(
            uservars.Prefix.SPELLING, calcUnoObjs)
        writerUnoObjs = finder.getWriterDoc()
        self.userVars = uservars.UserVars(
            uservars.Prefix.SPELLING, writerUnoObjs.document, logger)
        self.app = SpellingStepper(calcUnoObjs, self.userVars)
        self.msgbox = MessageBox(calcUnoObjs)
        self.maxRow = -1
        self.scrollbarAlreadyMoved = False
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
        try:
            self.dlgCtrls = DlgControls(
                self.unoObjs, ctrl_getter, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.evtHandler.setCtrls(self.dlgCtrls)

        # This fixes two problems, at least on Ubuntu:
        # - bar on scrollbar control doesn't show in viewable area
        # - cannot set background color of text box
        dlg.getPeer().setProperty("NativeWidgetLook", False)

        self.dlgCtrls.loadValues(self.userVars, self.app)

        ## Go to first row

        self.dlgCtrls.lblWordText.setText("")
        self.dlgCtrls.lblConvertedText.setText("")
        dataFound = self.loadData()
        if not dataFound:
            self.msgbox.display("No data found.")
            dlg.dispose()
            return
        startingRow = "2"
        varname = "CurrentRow"
        if not self.userVars.isEmpty(varname):
            startingRow = self.userVars.get(varname)
        self.dlgCtrls.txtRowNum.setText(startingRow)  # row 1 contains headings
        self.gotoRow()

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        dlg.dispose()

    def loadData(self):
        dataLen = self.app.loadData()
        logger.debug("Data len: %d", dataLen)
        self.maxRow = dataLen + 1   # skip first row
        self.dlgCtrls.scrollbarRow.setMaximum(self.maxRow)
        self.dlgCtrls.scrollbarRow.setBlockIncrement(dataLen // 20)
        return dataLen > 0

    def gotoRow(self):
        """Go to a particular row in the spreadsheet and display its
        information in the dialog.
        """
        logger.debug(util.funcName('begin'))
        txtVal = self.dlgCtrls.txtRowNum.getText()
        lightRedColor = int("FF8888", 16)
        if txtVal.strip() == '':
            self.dlgCtrls.txtRowNum.getModel().BackgroundColor = lightRedColor
            return
        try:
            rowNum = int(txtVal)
        except ValueError:
            logger.warning("Couldn't parse '%s' as integer.", txtVal)
            self.dlgCtrls.txtRowNum.getModel().BackgroundColor = lightRedColor
            return
        if rowNum < 2 or rowNum > self.maxRow:
            self.dlgCtrls.txtRowNum.getModel().BackgroundColor = lightRedColor
            return
        self.dlgCtrls.txtRowNum.getModel().setPropertyToDefault(
            "BackgroundColor")
        if self.scrollbarAlreadyMoved:
            self.scrollbarAlreadyMoved = False
        else:
            self.dlgCtrls.scrollbarRow.setValue(rowNum)

        wordInList = self.app.gotoRow(rowNum)
        self.userVars.store("CurrentRow", str(rowNum))
        self.dlgCtrls.lblWordText.setText(wordInList.text)
        self.dlgCtrls.lblConvertedText.setText(wordInList.converted1)
        if wordInList.correction:
            self.dlgCtrls.txtCorrection.setText(wordInList.correction)
        else:
            self.dlgCtrls.txtCorrection.setText(wordInList.text)
        dutil.set_tristate_checkbox(
            self.dlgCtrls.chkIsCorrect, wordInList.isCorrect)
        dutil.fill_list_ctrl(
            self.dlgCtrls.listSimilarWords, wordInList.similarWords)
        suggestions = []
        if self.app.wantSuggestions:
            suggestions = self.app.getSuggestions(wordInList.similarWords)
        dutil.fill_list_ctrl(
            self.dlgCtrls.listSuggestions, suggestions)
        logger.debug(util.funcName('end'))

    def enableDisable(self):
        newVal = self.dlgCtrls.txtCorrection.getText()
        wordInList = self.app.currentRowData()
        if newVal == wordInList.text or newVal == wordInList.correction:
            self.dlgCtrls.btnSetCorrection.getModel().Enabled = False
        else:
            self.dlgCtrls.btnSetCorrection.getModel().Enabled = True

    def setCorrection(self):
        logger.debug("Setting Correction...")
        if self.dlgCtrls.chkIsCorrect.getState() == dutil.CHECKED:
            ok = self.msgbox.displayOkCancel(
                "This word was already set to correct.  Change anyway?")
            if not ok:
                return
        correctionStr = self.dlgCtrls.txtCorrection.getText()
        self.app.setCorrection(correctionStr)
        if correctionStr.strip() == "":
            self.app.setIsCorrect(True)
            self.dlgCtrls.chkIsCorrect.setState(dutil.CHECKED)
        else:
            self.app.setIsCorrect(False)
            self.dlgCtrls.chkIsCorrect.setState(dutil.UNCHECKED)
        self.enableDisable()

    def checkSuggestions(self):
        self.userVars.store("GiveSuggestions",
                            str(self.dlgCtrls.chkSuggestions.getState()))
        if self.dlgCtrls.chkSuggestions.getState() == 1:
            self.app.wantSuggestions = True
        else:
            self.app.wantSuggestions = False
        self.gotoRow()


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.txtRowNum = ctrl_getter.get(_dlgdef.TXT_ROW_NUM)
        self.txtCorrection = ctrl_getter.get(_dlgdef.TXT_CORRECTION)
        self.scrollbarRow = ctrl_getter.get(_dlgdef.SCROLLBAR_ROW)
        self.lblWordText = ctrl_getter.get(_dlgdef.LBL_WORD_TEXT)
        self.lblConvertedText = ctrl_getter.get(_dlgdef.LBL_CONVERTED_TEXT)
        self.chkIsCorrect = ctrl_getter.get(_dlgdef.CHK_IS_CORRECT)
        self.chkSuggestions = ctrl_getter.get(_dlgdef.CHK_GIVE_SUGGESTIONS)
        self.listSimilarWords = ctrl_getter.get(_dlgdef.LISTBOX_SIMILAR_WORDS)
        self.listSuggestions = ctrl_getter.get(_dlgdef.LISTBOX_SUGGESTIONS)
        self.btnSetCorrection = ctrl_getter.get(_dlgdef.BTN_SET_CORRECTION)
        btnClose = ctrl_getter.get(_dlgdef.BTN_CLOSE)

        self.btnSetCorrection.setActionCommand("SetCorrection")
        self.btnSetCorrection.addActionListener(self.evtHandler)
        btnClose.setActionCommand("Close")
        btnClose.addActionListener(self.evtHandler)

    def loadValues(self, userVars, app):
        varname = "GiveSuggestions"
        if not userVars.isEmpty(varname):
            app.wantSuggestions = (userVars.getInt(varname) == 1)
        if app.wantSuggestions:
            self.chkSuggestions.setState(1)
        else:
            self.chkSuggestions.setState(0)
        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.txtRowNum.addTextListener(self.evtHandler)
        self.txtCorrection.addTextListener(self.evtHandler)
        self.scrollbarRow.addAdjustmentListener(self.evtHandler)

        for ctrl in (self.chkSuggestions, self.chkIsCorrect,
                     self.listSimilarWords, self.listSuggestions):
            ctrl.addItemListener(self.evtHandler)

        # Simulate an itemStateChanged event.
        evt = uno.createUnoStruct("com.sun.star.lang.EventObject")
        evt.Source = self.chkSuggestions
        self.evtHandler.itemStateChanged(evt)


class DlgEventHandler(XActionListener, XItemListener, XTextListener,
                      XAdjustmentListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @dutil.log_event_handler_exceptions
    def itemStateChanged(self, itemEvent):
        """XItemListener event handler.
        Could be for the list control or checkboxes.
        """
        logger.debug(util.funcName('begin'))
        src = itemEvent.Source
        logger.debug(str(src.getModel().Name))
        if dutil.sameName(src, self.dlgCtrls.chkSuggestions):
            self.mainForm.checkSuggestions()
        elif dutil.sameName(src, self.dlgCtrls.chkIsCorrect):
            logger.debug(
                "chkIsCorrect %d", self.dlgCtrls.chkIsCorrect.getState())
            self.mainForm.app.setIsCorrect(
                dutil.get_tristate_checkbox(self.dlgCtrls.chkIsCorrect))
        elif (dutil.sameName(src, self.dlgCtrls.listSuggestions) or
              dutil.sameName(src, self.dlgCtrls.listSimilarWords)
             ):
            self.dlgCtrls.txtCorrection.setText(src.getSelectedItem())

    @dutil.log_event_handler_exceptions
    def adjustmentValueChanged(self, dummy_event):
        """XAdjustmentListener event handler."""
        self.mainForm.scrollbarAlreadyMoved = True
        self.dlgCtrls.txtRowNum.setText(self.dlgCtrls.scrollbarRow.getValue())

    @dutil.log_event_handler_exceptions
    def textChanged(self, textEvent):
        """XTextListener event handler."""
        logger.debug(util.funcName('begin'))
        src = textEvent.Source
        if dutil.sameName(src, self.dlgCtrls.txtRowNum):
            self.mainForm.gotoRow()
        elif dutil.sameName(src, self.dlgCtrls.txtCorrection):
            self.mainForm.enableDisable()

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "Close":
            logger.debug("Action command was Close")
            self.mainForm.dlgClose()
        elif event.ActionCommand == "SetCorrection":
            self.mainForm.setCorrection()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
