# -*- coding: Latin-1 -*-
#
# This file created Feb 24 2010 by Jim Kornelsen
#
# 01-Mar-10 JDK  Change frames.  Remember direction and normalize for SEC.
# 02-Mar-10 JDK  Display results found and changed.
# 15-Mar-10 JDK  No Char Style.  Add SFM.  Handle longer strings in parts.
# 16-Mar-10 JDK  Implemented option to preserve character formatting.
# 19-Mar-10 JDK  Fixed bug: do not use createCursor when excluding SFM mkr.
# 20-Mar-10 JDK  Use viewcursor to goRight() through tables.
# 31-Mar-10 JDK  Add localization.
# 30-Jul-10 JDK  Yes Char Style.  Remove isStartOfParagraph() check.
#                Enumerate paragraphs.  Always preserve formatting.
# 05-Aug-10 JDK  Added function for testing.
# 09-Sep-10 JDK  Always set a combo box default value.
# 15-Sep-10 JDK  Divided into packages.
# 16-Sep-10 JDK  Scope char styles are not possible, so don't put in list.
# 29-Sep-10 JDK  Add font of target style.
# 21-Oct-10 JDK  Option for changing font without applying a style.
# 20-Dec-11 JDK  Hidden option to limit number of matches.
# 15-Nov-12 JDK  Added font types option.
# 26-Nov-12 JDK  Option to ask before making each change.
# 11-Mar-13 JDK  Simplify remembering converter name between dialog calls.
# 13-Mar-13 JDK  Added type of target font.
# 15-Apr-13 JDK  Distinguish between underlying and display style names.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.

"""
Data conversion dialog for a Writer document.

This module exports:
    showDlg()
"""
import collections
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.writer import styles
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.dataconversion import DataConversion, ConversionSettings
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
from lingt.utils import util
from lingt.utils.fontsize import FontSize

logger = logging.getLogger("lingt.ui.dlgdataconv")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgDataConversion(unoObjs)
    dlg.showDlg()

class DlgDataConversion:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        USERVAR_PREFIX = 'LTc_'  # LinguisticTools Data Conversion vars
        self.userVars = uservars.UserVars(
            USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.styleFonts = styles.StyleFonts(unoObjs, self.userVars)
        self.app = DataConversion(unoObjs, self.userVars, self.styleFonts)
        self.dlgCtrls = None
        self.evtHandler = None
        self.charStyleNames = []
        self.paraStyleNames = []
        self.config = None
        self.converter = None
        self.convertOnClose = False
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgDataConversion")
        if not dlg:
            return
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = None
        try:
            self.dlgCtrls = DlgControls(
                self.unoObjs, dlg, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.evtHandler.setCtrls(self.dlgCtrls)

        logger.debug("Getting styles...")
        styleNames = styles.getListOfStyles('ParagraphStyles', self.unoObjs)
        self.paraStyleNames = dict(styleNames)
        paraStyleDispNames = tuple([dispName for dispName, name in styleNames])
        styleNames = styles.getListOfStyles('CharacterStyles', self.unoObjs)
        self.charStyleNames = dict(styleNames)
        charStyleDispNames = tuple([dispName for dispName, name in styleNames])
        self.dlgCtrls.loadValues(
            self.userVars, paraStyleDispNames, charStyleDispNames)
        self.dlgCtrls.enableDisable(self)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.convertOnClose:
            self.app.doConversions_writer()
        dlg.dispose()

    def selectTargetFont(self, control, styleType):
        """Selects the font based on the value specified in the control.
        If control is None (for initialization or testing), gets values from
        user variables instead.
        """
        logger.debug(util.funcName('begin'))
        listCtrl = self.dlgCtrls.listTargetStyleFont  # shorthand variable
        listValues = listCtrl.Items
        if control:
            fontType = 'Western'
            if self.dlgCtrls.optTargetFontComplex.getState() == 1:
                fontType = 'Complex'
            elif self.dlgCtrls.optTargetFontAsian.getState() == 1:
                fontType = 'Asian'
            displayName = control.getText()
            try:
                if styleType == 'Paragraph':
                    styleName = self.paraStyleNames[displayName]
                elif styleType == 'Character':
                    styleName = self.charStyleNames[displayName]
            except KeyError:
                # Perhaps a new style to be created
                logger.debug("%s is not a known style.", displayName)
                return
            fontName, fontSize = self.styleFonts.getFontOfStyle(
                styleType, fontType, styleName)
        else:
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
        elif self.config.whichScope == 'ParaStyle':
            displayName = self.dlgCtrls.comboScopeParaStyle.getText()
            # use display name when searching
            searchConfig.style = displayName
        elif self.config.whichScope == 'CharStyle':
            displayName = self.dlgCtrls.comboScopeCharStyle.getText()
            if displayName in self.charStyleNames:
                searchConfig.style = self.charStyleNames[displayName]
            else:
                searchConfig.style = displayName
        elif self.config.whichScope == 'SFMs':
            searchConfig.SFMs = self.dlgCtrls.txtSFM.getText()
        searchConfig.loadMatchLimit(self.userVars)

        self.config.whichTarget = dutil.whichSelected(
            self.dlgCtrls.radiosWhichTarget)
        self.userVars.store('WhichTarget', self.config.whichTarget)
        self.config.targetStyle = ''
        if self.config.whichTarget == 'ParaStyle':
            displayName = self.dlgCtrls.comboTargetParaStyle.getText()
            if displayName in self.paraStyleNames:
                self.config.targetStyle = self.paraStyleNames[displayName]
            else:
                # Perhaps a new style to be created
                self.config.targetStyle = displayName
        elif self.config.whichTarget == 'CharStyle':
            displayName = self.dlgCtrls.comboTargetCharStyle.getText()
            if displayName in self.charStyleNames:
                self.config.targetStyle = self.charStyleNames[displayName]
            else:
                # Perhaps a new style to be created
                self.config.targetStyle = displayName

        ## Target font

        targetFontName = self.dlgCtrls.listTargetStyleFont.getSelectedItem()
        if targetFontName == "(None)":
            targetFontName = None
        targetFontSize = FontSize()
        targetFontSize.loadCtrl(self.dlgCtrls.txtFontSize)
        if self.config.whichTarget == 'FontOnly':
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
        self.userVars.store('SFM_Markers', self.dlgCtrls.txtSFM.getText())
        self.userVars.store('AskEachChange',
                            str(self.dlgCtrls.chkVerify.getState()))
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.txtConverterName = dutil.getControl(dlg, 'txtCnvtrName')
        self.chkDirectionReverse = dutil.getControl(dlg, 'chkDirectionReverse')
        self.chkVerify = dutil.getControl(dlg, 'chkVerify')
        self.optScopeWholeDoc = dutil.getControl(dlg, 'optScopeWholeDoc')
        self.optScopeSelection = dutil.getControl(dlg, 'optScopeSelection')
        self.optScopeFont = dutil.getControl(dlg, 'optScopeFont')
        self.optScopeParaStyle = dutil.getControl(dlg, 'optScopeParaStyle')
        self.optScopeCharStyle = dutil.getControl(dlg, 'optScopeCharStyle')
        self.optScopeSFMs = dutil.getControl(dlg, 'optScopeSFMs')
        self.optScopeFontWestern = dutil.getControl(dlg, 'optScopeFontRegular')
        self.optScopeFontComplex = dutil.getControl(dlg, 'optScopeFontCTL')
        self.optScopeFontAsian = dutil.getControl(dlg, 'optScopeFontAsian')
        self.optTargetFontWestern = dutil.getControl(
            dlg, 'optTargetFontRegular')
        self.optTargetFontComplex = dutil.getControl(dlg, 'optTargetFontCTL')
        self.optTargetFontAsian = dutil.getControl(dlg, 'optTargetFontAsian')
        self.optTargetNoChange = dutil.getControl(dlg, 'optTargetNoChange')
        self.optTargetParaStyle = dutil.getControl(dlg, 'optTargetParaStyle')
        self.optTargetCharStyle = dutil.getControl(dlg, 'optTargetCharStyle')
        self.optTargetFontOnly = dutil.getControl(dlg, 'optTargetFontOnly')
        self.comboScopeParaStyle = dutil.getControl(dlg, 'cmbxScopeParaStyle')
        self.comboScopeCharStyle = dutil.getControl(dlg, 'cmbxScopeCharStyle')
        self.comboScopeFont = dutil.getControl(dlg, 'cmbxScopeFont')
        self.comboTargetParaStyle = dutil.getControl(
            dlg, 'cmbxTargetParaStyle')
        self.comboTargetCharStyle = dutil.getControl(
            dlg, 'cmbxTargetCharStyle')
        self.listTargetStyleFont = dutil.getControl(dlg, 'listStyleFont')
        self.txtSFM = dutil.getControl(dlg, 'txbxSFM')
        self.txtFontSize = dutil.getControl(dlg, 'txtFontSize')
        btnSelectConv = dutil.getControl(dlg, 'BtnSelectConv')
        btnNoConverter = dutil.getControl(dlg, 'BtnNoConverter')
        btnOK = dutil.getControl(dlg, 'BtnOK')
        btnCancel = dutil.getControl(dlg, "BtnCancel")

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
            dutil.RadioTuple(self.optScopeFont, 'Font'),
            dutil.RadioTuple(self.optScopeParaStyle, 'ParaStyle'),
            dutil.RadioTuple(self.optScopeCharStyle, 'CharStyle'),
            dutil.RadioTuple(self.optScopeSFMs, 'SFMs')]
        self.radiosWhichTarget = [
            dutil.RadioTuple(self.optTargetNoChange, 'NoChange'),
            dutil.RadioTuple(self.optTargetParaStyle, 'ParaStyle'),
            dutil.RadioTuple(self.optTargetCharStyle, 'CharStyle'),
            dutil.RadioTuple(self.optTargetFontOnly, 'FontOnly')]
        self.combos = None

    def loadValues(self, userVars, paraStyleDispNames, charStyleDispNames):
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
            ComboTuple(ctrl=self.comboScopeParaStyle,
                       varname='ScopeParaStyle',
                       data=paraStyleDispNames),
            ComboTuple(ctrl=self.comboScopeCharStyle,
                       varname='ScopeCharStyle',
                       data=charStyleDispNames),
            ComboTuple(ctrl=self.comboScopeFont,
                       varname='ScopeFont',
                       data=styles.getListOfFonts(self.unoObjs)),
            ComboTuple(ctrl=self.comboTargetParaStyle,
                       varname='TargetParaStyle',
                       data=paraStyleDispNames),
            ComboTuple(ctrl=self.comboTargetCharStyle,
                       varname='TargetCharStyle',
                       data=charStyleDispNames)]
        for combo in self.combos:
            dutil.fill_list_ctrl(
                combo.ctrl, combo.data, userVars.get(combo.varname))

        dutil.fill_list_ctrl(
            self.listTargetStyleFont,
            styles.getListOfFonts(self.unoObjs, addBlank=True))
        logger.debug("Finished populating font and styles lists.")

        ## Other fields

        varname = 'SFM_Markers'
        if userVars.isEmpty(varname):
            defaultCtrlText = "\\tx \\mb"
            userVars.store(varname, defaultCtrlText)
            userVarVal = defaultCtrlText
        else:
            userVarVal = userVars.get(varname)
        self.txtSFM.setText(userVarVal)
        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        for ctrl in (self.optTargetNoChange, self.optTargetParaStyle,
                     self.optTargetCharStyle, self.optTargetFontOnly):
            ctrl.addItemListener(self.evtHandler)

        for ctrl in (self.comboTargetParaStyle, self.comboTargetCharStyle):
            ctrl.addTextListener(self.evtHandler)

    def enableDisable(self, mainForm):
        """Enable or disable controls as appropriate."""
        listCtrl = self.listTargetStyleFont  # shorthand variable
        textCtrl = self.txtFontSize
        if self.optTargetNoChange.getState() == 1:
            listCtrl.selectItemPos(0, True)
            listCtrl.getModel().Enabled = False
            textCtrl.getModel().Enabled = False
        elif self.optTargetFontOnly.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            mainForm.selectTargetFont(None, None)
        elif self.optTargetParaStyle.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            mainForm.selectTargetFont(
                self.comboTargetParaStyle, 'Paragraph')
        elif self.optTargetCharStyle.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            mainForm.selectTargetFont(
                self.comboTargetParaStyle, 'Character')


class DlgEventHandler(XActionListener, XTextListener, XItemListener,
                      unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @dutil.log_event_handler_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))
        self.dlgCtrls.enableDisable(self.mainForm)

    @dutil.log_event_handler_exceptions
    def textChanged(self, textEvent):
        logger.debug(util.funcName('begin'))
        src = textEvent.Source
        if dutil.sameName(src, self.dlgCtrls.comboTargetParaStyle):
            if self.dlgCtrls.optTargetParaStyle.getState() == 1:
                self.mainForm.selectTargetFont(src, 'Paragraph')
        elif dutil.sameName(src, self.dlgCtrls.comboTargetCharStyle):
            if self.dlgCtrls.optTargetCharStyle.getState() == 1:
                self.mainForm.selectTargetFont(src, 'Character')
        else:
            logger.warning("unexpected source %s", src.Model.Name)

    @dutil.log_event_handler_exceptions
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
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
