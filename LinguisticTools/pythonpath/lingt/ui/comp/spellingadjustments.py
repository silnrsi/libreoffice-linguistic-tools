"""
Dialog to search a word list in Calc and suggest or make spelling adjustments.

This module exports:
    showAdjustmentsDlg()
"""
import collections
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener
from com.sun.star.lang import EventObject

from lingt.access.writer import uservars
from lingt.app.svc.scriptpractice import Script
from lingt.app.svc.spellingcomparisons import SpellingCharClasses
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.dlgdefs import DlgSpellingAdjustments as _dlgdef
from lingt.utils import unicode_data
from lingt.utils import util
from lingt.utils.fontsize import FontSize

logger = logging.getLogger("lingt.ui.dlgspellingadjustments")

DEFAULT_FONT_SIZE = 28.0


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showAdjustmentsDlg()------------------------------------")
    calcUnoObjs = util.UnoObjs(ctx, doctype=util.UnoObjs.DOCTYPE_CALC)
    logger.debug("got UNO context")

    dlg = DlgSpellingAdjustments(calcUnoObjs)
    dlg.showDlg()

class DlgSpellingAdjustments:
    """Main class for this dialog."""

    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        self.msgbox = MessageBox(self.unoObjs)
        self.userVars = uservars.UserVars(
            uservars.Prefix.SPELLING, calcUnoObjs.document, logger)
        # for fonts and scripts
        self.script = Script(calcUnoObjs)
        self.app = SpellingCharClasses(self.unoObjs, self.userVars)
        self.charCompOpts = []
        self.charsetAlreadySet = False
        self.compareOnClose = False
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
            self.unoObjs, ctrl_getter, self.evtHandler, self.script)
        self.evtHandler.setCtrls(self.dlgCtrls)
        self.dlgCtrls.loadValues(self.userVars)

        varname = 'CharComparison'
        if not self.userVars.isEmpty(varname):
            self.app.setCharCompFromInput(self.userVars.get(varname))
            self.charsetAlreadySet = True
        else:
            self.charsetAlreadySet = False

        evt = EventObject()
        for ctrl in (
                self.dlgCtrls.comboScript, self.dlgCtrls.comboFont,
                self.dlgCtrls.txtFontSize):
            evt.Source = ctrl
            self.evtHandler.textChanged(evt)   # Simulate a textChanged event

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.compareOnClose:
            self.app.doChecks()
        dlg.dispose()

    def revertChars(self):
        logger.debug("Reverting Characters...")
        varname = 'CharComparison'
        if not self.userVars.isEmpty(varname):
            self.app.setCharCompFromInput(self.userVars.get(varname))
        self.dlgCtrls.txtCharComp.setText(self.app.getCharCompString())

    def getCharCompOpts(self):
        """
        Reads checkboxes and gets list of comparison types for
        determining the char comparison list.
        Result is self.charCompOpts
        """
        logger.debug(util.funcName('begin'))
        self.charCompOpts = []
        for chk in self.dlgCtrls.checkboxVarList:
            if chk.ctrl.getState() == 1:
                self.charCompOpts.append(chk.key)
        logger.debug(util.funcName('end'))

    def updateCharCompOpts(self):
        self.getCharCompOpts()
        self.app.setCharCompFromScript(self.charCompOpts)
        self.dlgCtrls.txtCharComp.setText(
            self.app.getCharCompString())

    def changeScript(self):
        scriptName = self.dlgCtrls.comboScript.getText()
        self.app.setScript(scriptName)
        self.script.setScriptName(scriptName)
        if self.charsetAlreadySet:
            self.charsetAlreadySet = False
        else:
            self.getCharCompOpts()
            self.app.setCharCompFromScript(self.charCompOpts)
        self.dlgCtrls.txtCharComp.setText(self.app.getCharCompString())
        self.dlgCtrls.setFontList()
        self.dlgCtrls.enableDisable(self.app)

    def getFormResults(self):
        """Reads form fields and gets settings."""
        logger.debug(util.funcName('begin'))

        charcompString = self.dlgCtrls.txtCharComp.getText()
        self.app.setCharCompFromInput(charcompString)
        self.userVars.store("CharComparison", charcompString)

        ## Font name and size

        fontName = self.dlgCtrls.comboFont.getText()
        if fontName == "(None)":
            fontName = None
        fontSize = FontSize(default=DEFAULT_FONT_SIZE)
        fontSize.loadCtrl(self.dlgCtrls.txtFontSize)
        self.userVars.store('Font', fontName)
        self.userVars.store('FontSize', fontSize.getString())
        self.userVars.store(
            "OnlyKnownFonts", str(self.dlgCtrls.chkKnownFonts.getState()))

        self.userVars.store("Script", self.dlgCtrls.comboScript.getText())

        ## Checkbox var list

        for chk in self.dlgCtrls.checkboxVarList:
            self.userVars.store(chk.varname, str(chk.ctrl.getState()))

        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler, script):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler
        self.script = script

        self.lblCharComp = ctrl_getter.get(_dlgdef.LBL_COMP_LIST)
        self.txtCharComp = ctrl_getter.get(_dlgdef.TXT_COMPARISON_LIST)
        self.comboScript = ctrl_getter.get(_dlgdef.COMBO_SCRIPT)
        self.lblScript = ctrl_getter.get(_dlgdef.LBL_SCRIPT)
        self.comboFont = ctrl_getter.get(_dlgdef.COMBO_FONT)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_SIZE)
        self.chkVowelLength = ctrl_getter.get(_dlgdef.CHK_VOWEL_LENGTH)
        self.chkVowelGlides = ctrl_getter.get(_dlgdef.CHK_VOWEL_GLIDES)
        self.chkNasals = ctrl_getter.get(_dlgdef.CHK_NASALS)
        self.chkAspiration = ctrl_getter.get(_dlgdef.CHK_ASPIRATION)
        self.chkPOA = ctrl_getter.get(_dlgdef.CHK_POA)
        self.chkGeminates = ctrl_getter.get(_dlgdef.CHK_GEMINATES)
        self.chkLiquids = ctrl_getter.get(_dlgdef.CHK_LIQUIDS)
        self.chkKnownFonts = ctrl_getter.get(_dlgdef.CHK_KNOWN_FONTS)
        self.btnResetChars = ctrl_getter.get(_dlgdef.BTN_RESET)
        btnCompare = ctrl_getter.get(_dlgdef.BTN_COMPARE)
        btnClose = ctrl_getter.get(_dlgdef.BTN_CLOSE)

        self.btnResetChars.setActionCommand("RevertChars")
        btnCompare.setActionCommand("Close_and_Compare")
        btnClose.setActionCommand("Close")
        for ctrl in (self.btnResetChars, btnCompare, btnClose):
            ctrl.addActionListener(self.evtHandler)

        CheckboxTuple = collections.namedtuple(
            'CheckboxTuple', ['ctrl', 'key', 'varname'])
        self.checkboxVarList = [
            CheckboxTuple(ctrl=self.chkVowelLength, key='VOW_LEN',
                          varname="CompareVowelLength"),
            CheckboxTuple(ctrl=self.chkVowelGlides, key='VOW_GLIDE',
                          varname="CompareVowelGlides"),
            CheckboxTuple(ctrl=self.chkNasals, key='NASAL',
                          varname="CompareNasals"),
            CheckboxTuple(ctrl=self.chkLiquids, key='LIQUID',
                          varname="CompareLiquids"),
            CheckboxTuple(ctrl=self.chkAspiration, key='ASP',
                          varname="CompareAspiration"),
            CheckboxTuple(ctrl=self.chkPOA, key='POA',
                          varname="ComparePOA"),
            CheckboxTuple(ctrl=self.chkGeminates, key='GEMIN',
                          varname="CompareGeminates")]

    def loadValues(self, userVars):
        scriptNames = sorted(list(unicode_data.SCRIPT_LETTERS.keys()))
        selectedValue = userVars.get("Script")
        if not selectedValue:
            selectedValue = "DEVANAGARI"
        dutil.fill_list_ctrl(self.comboScript, scriptNames, selectedValue)

        selectedValue = userVars.get("Font")
        if selectedValue:
            self.comboFont.setText(selectedValue)
        else:
            self.comboFont.setText("")
        self.chkKnownFonts.setState(userVars.getInt("OnlyKnownFonts"))
        self.setFontList()

        fontSize = FontSize(default=DEFAULT_FONT_SIZE)
        fontSize.loadUserVar(userVars, 'FontSize')
        fontSize.changeCtrlVal(self.txtFontSize)

        for chk in self.checkboxVarList:
            if userVars.isEmpty(chk.varname):
                chk.ctrl.setState(True)
            else:
                chk.ctrl.setState(userVars.getInt(chk.varname))

        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        for ctrl in (self.comboScript, self.comboFont, self.txtFontSize):
            ctrl.addTextListener(self.evtHandler)
        self.chkKnownFonts.addItemListener(self.evtHandler)

        for chk in self.checkboxVarList:
            chk.ctrl.addItemListener(self.evtHandler)

    def setFontList(self):
        logger.debug(util.funcName())
        self.script.setOnlyKnownFonts(self.chkKnownFonts.getState())
        selectedValue = self.script.getDefaultFont(self.comboFont.getText())
        dutil.fill_list_ctrl(
            self.comboFont, self.script.getFontList(), selectedValue)

    def changeFont(self):
        fontName = self.comboFont.getText()
        if fontName == self.script.fallbackFontDisplay:
            fontName = " "
        self.txtCharComp.getModel().FontName = fontName

    def changeFontSize(self):
        fontSize = FontSize(default=DEFAULT_FONT_SIZE)
        fontSize.loadCtrl(self.txtFontSize)
        fontSize.changeCtrlProp(self.txtCharComp)

    def enableDisable(self, app):
        """Enable or disable controls as appropriate."""
        availableKeys = app.getAvailableScriptKeys()
        for chk in self.checkboxVarList:
            chk.ctrl.getModel().Enabled = chk.key in availableKeys


class DlgEventHandler(XActionListener, XItemListener, XTextListener,
                      unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    def itemStateChanged(self, itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))
        src = itemEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.chkKnownFonts):
            self.dlgCtrls.setFontList()
            return
        self.mainForm.updateCharCompOpts()

    @evt_handler.log_exceptions
    def textChanged(self, textEvent):
        """XTextListener event handler."""
        logger.debug(util.funcName('begin'))
        src = textEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.comboScript):
            self.mainForm.changeScript()
        elif evt_handler.sameName(src, self.dlgCtrls.comboFont):
            self.dlgCtrls.changeFont()
        elif evt_handler.sameName(src, self.dlgCtrls.txtFontSize):
            self.dlgCtrls.changeFontSize()
        else:
            logger.warning("unexpected source %s", src.Model.Name)

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "RevertChars":
            self.mainForm.revertChars()
        elif event.ActionCommand == "Close_and_Compare":
            self.mainForm.getFormResults()
            self.mainForm.compareOnClose = True
            self.mainForm.dlgClose()
        elif event.ActionCommand == "Close":
            self.mainForm.getFormResults()
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (showDlg,)
