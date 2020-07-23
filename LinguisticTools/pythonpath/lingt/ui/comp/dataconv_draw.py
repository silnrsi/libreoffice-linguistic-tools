# -*- coding: Latin-1 -*-
#
# This file created July 28 2018 by Jim Kornelsen
#
# 30-Jul-18 JDK  Get UserVars from a Writer document.

"""
Data conversion dialog for a Draw document.

This module exports:
    showDlg()
"""
import collections
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.writer import styles
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.dataconversion import DataConversion, ConversionSettings
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgDataConv_Draw as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util
from lingt.utils.fontsize import FontSize

logger = logging.getLogger("lingt.ui.dlgdataconv")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    drawingUnoObjs = util.UnoObjs(ctx, doctype=util.UnoObjs.DOCTYPE_DRAW)
    logger.debug("got UNO context")

    dlg = DlgDataConversion(drawingUnoObjs)
    dlg.showDlg()

class DlgDataConversion:
    """Main class for this dialog."""

    def __init__(self, drawingUnoObjs):
        self.unoObjs = drawingUnoObjs
        self.userVars = uservars.UserVars(
            uservars.Prefix.DATA_CONV_DRAW, drawingUnoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)
        self.styleFonts = styles.StyleFonts(self.unoObjs)
        self.app = DataConversion(self.unoObjs, self.userVars, self.styleFonts)
        self.dlgCtrls = None
        self.evtHandler = None
        self.config = None
        self.converter = None
        self.convertOnClose = False
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = None
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
        self.evtHandler.setCtrls(self.dlgCtrls)

        logger.debug("Getting styles...")
        self.dlgCtrls.loadValues(self.userVars)
        self.dlgCtrls.enableDisable(self)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.convertOnClose:
            self.app.doConversions_draw()
        dlg.dispose()

    def selectTargetFont(self):
        """Selects the font from user variables."""
        logger.debug(util.funcName('begin'))
        listCtrl = self.dlgCtrls.listTargetFont  # shorthand variable
        listValues = listCtrl.Items
        fontName = self.userVars.get('TargetFontName')
        fontSize = FontSize()
        fontSize.loadUserVar(self.userVars, 'TargetFontSize')
        if fontName and fontName in listValues:
            listCtrl.selectItem(fontName, True)
        else:
            listCtrl.selectItemPos(0, True)
        fontSize.changeCtrlVal(self.dlgCtrls.txtFontSize)

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        logger.debug("Selecting a converter...")
        converter = self.app.selectConverter()
        self.dlgCtrls.txtConverterName.setText(converter.convName)
        self.dlgCtrls.chkDirectionReverse.setState(not converter.forward)

    def noConverter(self):
        logger.debug(util.funcName('begin'))
        logger.debug("Clearing converter...")
        self.dlgCtrls.txtConverterName.setText("<No converter>")

    def closeAndConvert(self):
        logger.debug(util.funcName('begin'))
        logger.debug("Closing and Converting...")
        self.getFormResults()
        try:
            self.app.setAndVerifyConverter(self.converter)
            self.app.setAndVerifyConfig(self.config)
            self.convertOnClose = True
            self.dlgClose()
        except (exceptions.ChoiceProblem, exceptions.StyleError) as exc:
            self.msgbox.displayExc(exc)

    def getFormResults(self):
        """Reads form fields and sets self.config and self.converter.
        In setAndVerifyConfig() in app layer, the settings will be checked for
        inconsistencies.
        """
        logger.debug(util.funcName('begin'))

        ## Converter

        self.converter = ConverterSettings(self.userVars)
        self.converter.loadUserVars()  # for normForm
        self.converter.convName = self.dlgCtrls.txtConverterName.getText()
        self.converter.forward = (
            self.dlgCtrls.chkDirectionReverse.getState() == 0)
        self.converter.storeUserVars()

        ## Radio buttons and the corresponding combo box selection

        self.config = ConversionSettings()
        searchConfig = self.config.searchConfig  # shorthand name
        self.config.whichScope = dutil.whichSelected(
            self.dlgCtrls.radiosWhichScope)
        self.userVars.store('WhichScope', self.config.whichScope)
        if self.config.whichScope == 'Font':
            searchConfig.fontName = self.dlgCtrls.comboScopeFont.getText()
            searchConfig.fontType = dutil.whichSelected(
                self.dlgCtrls.radiosScopeFont)
            self.userVars.store('ScopeFontType', searchConfig.fontType)
        searchConfig.load_userVars(self.userVars)

        self.config.whichTarget = dutil.whichSelected(
            self.dlgCtrls.radiosWhichTarget)
        self.userVars.store('WhichTarget', self.config.whichTarget)

        ## Target font

        targetFontName = self.dlgCtrls.listTargetFont.getSelectedItem()
        if targetFontName == "(None)":
            targetFontName = None
        targetFontSize = FontSize()
        targetFontSize.loadCtrl(self.dlgCtrls.txtFontSize)
        if self.config.whichTarget == 'Font':
            self.userVars.store('TargetFontName', targetFontName)
            self.userVars.store('TargetFontSize', targetFontSize.getString())
        targetFontType = dutil.whichSelected(
            self.dlgCtrls.radiosTargetFont)
        self.userVars.store('TargetFontType', targetFontType)
        self.config.targetFont = styles.FontDefStruct(
            targetFontName, targetFontType, targetFontSize)

        self.config.askEach = (self.dlgCtrls.chkVerify.getState() == 1)

        ## Save selections for next time

        for combo in self.dlgCtrls.combos:
            self.userVars.store(combo.varname, combo.ctrl.getText())
        self.userVars.store('AskEachChange',
                            str(self.dlgCtrls.chkVerify.getState()))
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.txtConverterName = ctrl_getter.get(_dlgdef.TXT_CNVTR_NAME)
        self.chkDirectionReverse = ctrl_getter.get(_dlgdef.CHK_DIRECTION_REVERSE)
        self.chkVerify = ctrl_getter.get(_dlgdef.CHK_VERIFY)
        self.optScopeWholeDoc = ctrl_getter.get(_dlgdef.OPT_SCOPE_WHOLE_DOC)
        self.optScopeSelection = ctrl_getter.get(_dlgdef.OPT_SCOPE_SELECTION)
        self.optScopeFont = ctrl_getter.get(_dlgdef.OPT_SCOPE_FONT)
        self.optScopeFontWestern = ctrl_getter.get(_dlgdef.OPT_SCOPE_FONT_REGULAR)
        self.optScopeFontComplex = ctrl_getter.get(_dlgdef.OPT_SCOPE_FONT_CTL)
        self.optScopeFontAsian = ctrl_getter.get(_dlgdef.OPT_SCOPE_FONT_ASIAN)
        self.optTargetFontWestern = ctrl_getter.get(_dlgdef.OPT_TARGET_FONT_REGULAR)
        self.optTargetFontComplex = ctrl_getter.get(_dlgdef.OPT_TARGET_FONT_CTL)
        self.optTargetFontAsian = ctrl_getter.get(_dlgdef.OPT_TARGET_FONT_ASIAN)
        self.optTargetNoChange = ctrl_getter.get(_dlgdef.OPT_TARGET_NO_CHANGE)
        self.optTargetFont = ctrl_getter.get(_dlgdef.OPT_TARGET_FONT)
        self.comboScopeFont = ctrl_getter.get(_dlgdef.CMBX_SCOPE_FONT)
        self.listTargetFont = ctrl_getter.get(_dlgdef.LIST_TARGET_FONT)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_FONT_SIZE)
        btnSelectConv = ctrl_getter.get(_dlgdef.BTN_SELECT_CONV)
        btnNoConverter = ctrl_getter.get(_dlgdef.BTN_NO_CONVERTER)
        btnOK = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        btnSelectConv.setActionCommand('SelectConverter')
        btnNoConverter.setActionCommand('NoConverter')
        btnOK.setActionCommand('Close_and_Convert')
        btnCancel.setActionCommand('Cancel')
        for ctrl in (btnSelectConv, btnNoConverter, btnOK, btnCancel):
            ctrl.addActionListener(self.evtHandler)

        self.radiosScopeFont = [
            dutil.RadioTuple(self.optScopeFontWestern, 'Western'),
            dutil.RadioTuple(self.optScopeFontComplex, 'Complex'),
            dutil.RadioTuple(self.optScopeFontAsian, 'Asian')]
        self.radiosTargetFont = [
            dutil.RadioTuple(self.optTargetFontWestern, 'Western'),
            dutil.RadioTuple(self.optTargetFontComplex, 'Complex'),
            dutil.RadioTuple(self.optTargetFontAsian, 'Asian')]
        self.radiosWhichScope = [
            dutil.RadioTuple(self.optScopeWholeDoc, 'WholeDoc'),
            dutil.RadioTuple(self.optScopeSelection, 'Selection'),
            dutil.RadioTuple(self.optScopeFont, 'Font')]
        self.radiosWhichTarget = [
            dutil.RadioTuple(self.optTargetNoChange, 'NoChange'),
            dutil.RadioTuple(self.optTargetFont, 'Font')]
        self.combos = None

    def loadValues(self, userVars):
        converter = ConverterSettings(userVars)
        converter.loadUserVars()
        self.txtConverterName.setText(converter.convName)
        self.chkDirectionReverse.setState(not converter.forward)
        self.chkVerify.setState(
            userVars.getInt('AskEachChange'))

        ## Option buttons

        dutil.selectRadio(self.radiosWhichScope, userVars.get('WhichScope'))
        dutil.selectRadio(self.radiosWhichTarget, userVars.get('WhichTarget'))
        dutil.selectRadio(self.radiosScopeFont, userVars.get('ScopeFontType'))
        dutil.selectRadio(
            self.radiosTargetFont, userVars.get('TargetFontType'))

        ## Combo box lists

        ComboTuple = collections.namedtuple(
            'ComboTuple', ['ctrl', 'varname', 'data'])
        self.combos = [
            ComboTuple(ctrl=self.comboScopeFont,
                       varname='ScopeFont',
                       data=styles.getListOfFonts(self.unoObjs))]
        for combo in self.combos:
            logger.debug("Filling Scope Font list.")
            #XXX: Sometimes hangs here.
            dutil.fill_list_ctrl(
                combo.ctrl, combo.data, userVars.get(combo.varname))

        logger.debug("Filling Target Font list.")
        dutil.fill_list_ctrl(
            self.listTargetFont,
            styles.getListOfFonts(self.unoObjs, addBlank=True))
        logger.debug("Finished populating font and styles lists.")

        ## Other fields

        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        for ctrl in (self.optTargetNoChange, self.optTargetFont):
            ctrl.addItemListener(self.evtHandler)

    def enableDisable(self, mainForm):
        """Enable or disable controls as appropriate."""
        listCtrl = self.listTargetFont  # shorthand variable
        textCtrl = self.txtFontSize
        if self.optTargetNoChange.getState() == 1:
            listCtrl.selectItemPos(0, True)
            listCtrl.getModel().Enabled = False
            textCtrl.getModel().Enabled = False
        elif self.optTargetFont.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            mainForm.selectTargetFont()


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))
        self.dlgCtrls.enableDisable(self.mainForm)

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == 'SelectConverter':
            self.mainForm.selectConverter()
        elif event.ActionCommand == 'NoConverter':
            self.mainForm.noConverter()
        elif event.ActionCommand == 'Cancel':
            logger.debug("Action command was Cancel")
            self.mainForm.dlgClose()
        elif event.ActionCommand == 'Close_and_Convert':
            self.mainForm.closeAndConvert()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
