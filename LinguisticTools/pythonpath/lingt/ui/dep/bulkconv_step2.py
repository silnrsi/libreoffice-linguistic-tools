# -*- coding: Latin-1 -*-
#
# This file created December 24 2015 by Jim Kornelsen
#
# 05-Feb-16 JDK  Show a mark in the list to indicate font changes.
# 11-Feb-16 JDK  Show modified font settings when FontItem is selected.
# 19-Feb-16 JDK  Add checkboxes to separate font type, size and style.
# 24-Feb-16 JDK  Use a single foundFonts label instead of three labels.
# 07-Mar-16 JDK  Handle chkJoin changes.

"""
Bulk Conversion dialog step 2.

This module exports:
    Step2Controls()
    Step2Form()
"""
import copy
import logging

from lingt.access.writer import styles
from lingt.app import exceptions
from lingt.app.bulkconv_structs import FontChange
from lingt.app.svc.bulkconversion import Samples
from lingt.ui import dutil
from lingt.utils import util
from lingt.utils.fontsize import FontSize
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgbulkconv_step2")


class Step2Controls:
    """Store dialog controls for page step 2."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.listFontsUsed = dutil.getControl(dlg, 'listFontsUsed')
        self.btnNextInput = dutil.getControl(dlg, 'btnNextInput')
        self.lblInput = dutil.getControl(dlg, 'inputDisplay')
        self.lblSampleNum = dutil.getControl(dlg, 'sampleNum')
        self.lblConverted = dutil.getControl(dlg, 'convertedDisplay')
        self.chkShowConverted = dutil.getControl(dlg, 'chkShowConverted')
        btnReset = dutil.getControl(dlg, 'btnReset')
        btnCopy = dutil.getControl(dlg, 'btnCopy')
        btnPaste = dutil.getControl(dlg, 'btnPaste')
        self.txtConvName = dutil.getControl(dlg, 'txtConvName')
        btnSelectConv = dutil.getControl(dlg, 'btnChooseConv')
        self.chkReverse = dutil.getControl(dlg, 'chkReverse')

        self.chkJoinFontTypes = dutil.getControl(dlg, 'chkJoinFontTypes')
        self.foundFonts = dutil.getControl(dlg, 'foundFonts')
        self.comboFontName = dutil.getControl(dlg, 'comboFontName')
        self.optFontStandard = dutil.getControl(dlg, 'optFontStandard')
        self.optFontComplex = dutil.getControl(dlg, 'optFontComplex')
        self.optFontAsian = dutil.getControl(dlg, 'optFontAsian')

        self.chkJoinSize = dutil.getControl(dlg, 'chkJoinSize')
        self.foundFontSize = dutil.getControl(dlg, 'foundFontSize')
        self.txtFontSize = dutil.getControl(dlg, 'txtFontSize')

        self.chkJoinStyles = dutil.getControl(dlg, 'chkJoinStyles')
        self.optParaStyle = dutil.getControl(dlg, 'optParaStyle')
        self.comboParaStyle = dutil.getControl(dlg, 'comboParaStyle')
        self.optCharStyle = dutil.getControl(dlg, 'optCharStyle')
        self.comboCharStyle = dutil.getControl(dlg, 'comboCharStyle')
        self.optNoStyle = dutil.getControl(dlg, 'optNoStyle')
        self.chkVerify = dutil.getControl(dlg, 'chkVerify')
        btnProcess = dutil.getControl(dlg, 'btnProcess')
        logger.debug("Got step 2 controls.")

        ## Command buttons

        self.btnNextInput.setActionCommand('NextInput')
        btnReset.setActionCommand('ResetFont')
        btnCopy.setActionCommand('CopyFont')
        btnPaste.setActionCommand('PasteFont')
        btnSelectConv.setActionCommand('SelectConverter')
        btnProcess.setActionCommand('Close_and_Convert')
        for ctrl in (
                btnReset, btnCopy, btnPaste, self.btnNextInput, btnSelectConv,
                btnProcess):
            ctrl.addActionListener(self.evtHandler)

        self.radiosFontType = [
            dutil.RadioTuple(self.optFontStandard, 'Western'),
            dutil.RadioTuple(self.optFontComplex, 'Complex'),
            dutil.RadioTuple(self.optFontAsian, 'Asian')]
        self.radiosStyleType = [
            dutil.RadioTuple(self.optNoStyle, 'CustomFormatting'),
            dutil.RadioTuple(self.optParaStyle, 'ParaStyle'),
            dutil.RadioTuple(self.optCharStyle, 'CharStyle')]

    def loadValues(self, userVars, paraStyleDispNames, charStyleDispNames):
        """
        param paraStyleDispNames: list of paragraph style display names
        """
        logger.debug(util.funcName('begin'))
        #self.chkShowConverted.setState(
        #    userVars.getInt('DisplayConverted'))
        self.chkShowConverted.setState(False)
        self.chkJoinFontTypes.setState(userVars.getInt('JoinFontTypes'))
        self.chkJoinSize.setState(userVars.getInt('JoinSize'))
        self.chkJoinStyles.setState(userVars.getInt('JoinStyles'))
        self.chkVerify.setState(userVars.getInt('AskEachChange'))

        logger.debug("Populating font and styles lists")
        fontNames = styles.getListOfFonts(self.unoObjs, addBlank=True)
        dutil.fill_list_ctrl(self.comboFontName, fontNames)
        dutil.fill_list_ctrl(self.comboParaStyle, paraStyleDispNames)
        dutil.fill_list_ctrl(self.comboCharStyle, charStyleDispNames)
        logger.debug("Finished populating font and styles lists.")

        self.addRemainingListeners()
        logger.debug(util.funcName('end'))

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.listFontsUsed.addItemListener(self.evtHandler)
        for ctrl in (
                self.optFontStandard, self.optFontComplex, self.optFontAsian,
                self.optParaStyle, self.optCharStyle, self.optNoStyle,
                self.chkJoinFontTypes, self.chkJoinSize, self.chkJoinStyles,
                self.chkShowConverted, self.chkReverse):
            ctrl.addItemListener(self.evtHandler)

        self.txtFontSize.addTextListener(self.evtHandler)

        self.comboFontName.addItemListener(self.evtHandler)
        self.comboParaStyle.addItemListener(self.evtHandler)
        self.comboCharStyle.addItemListener(self.evtHandler)

    def enableDisable(self, stepForm):
        """Enable or disable controls as appropriate."""
        logger.debug(util.funcName())
        if self.optParaStyle.getState() == 1:
            stepForm.selectFontFromStyle(self.comboParaStyle, 'Paragraph')
        elif self.optCharStyle.getState() == 1:
            stepForm.selectFontFromStyle(self.comboCharStyle, 'Character')


class Step2Form:
    """Handle items and data for page step 2."""

    def __init__(self, unoObjs, stepCtrls, userVars, msgbox, app):
        self.unoObjs = unoObjs
        self.stepCtrls = stepCtrls
        self.userVars = userVars
        self.msgbox = msgbox
        self.app = app

        self.styleFonts = styles.StyleFonts(self.unoObjs, self.userVars)
        self.paraStyleNames = []
        self.charStyleNames = []
        self.copiedSettings = None
        self.selectedIndex = -1  # selected FontItem
        self.samples = Samples(self.app.convPool)

    def loadData(self):
        stylesList = styles.getListOfStyles('ParagraphStyles', self.unoObjs)
        self.paraStyleNames = dict(stylesList)
        paraStyleDispNames = tuple([dispName for dispName, name in stylesList])
        stylesList = styles.getListOfStyles('CharacterStyles', self.unoObjs)
        self.charStyleNames = dict(stylesList)
        charStyleDispNames = tuple([dispName for dispName, name in stylesList])
        self.stepCtrls.loadValues(
            self.userVars, paraStyleDispNames, charStyleDispNames)
        self.stepCtrls.lblInput.setText("(None)")
        self.stepCtrls.lblSampleNum.setText("0 / 0")
        self.stepCtrls.lblConverted.setText("(None)")

    def resetFont(self):
        self.grabSelectedItem()
        if self.selectedIndex == -1:
            return
        self.app.fontItemList[self.selectedIndex].change = None
        self.updateFontsList()
        self.fill_for_selected_font()

    def copyFont(self):
        logger.debug(util.funcName())
        self.copiedSettings = self.getFontFormResults(False)

    def pasteFont(self):
        logger.debug(util.funcName())
        if self.copiedSettings is None:
            self.msgbox.display("First copy font settings.")
            return
        fontItem = self.grabSelectedItem()
        if self.selectedIndex == -1:
            return
        attrs_to_change = [
            'converter.convName', 'converter.forward',
            'fontType', 'name', 'size',
            'styleType', 'styleName']
        self.app.fontItemList.update_item(
            fontItem, self.copiedSettings, attrs_to_change)
        self.updateFontsList()
        self.fill_for_selected_font()

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        fontItem = self.grabSelectedItem()
        if self.selectedIndex == -1:
            return
        conv_settings = None
        if fontItem.change:
            conv_settings = fontItem.change.converter
        newChange = self.app.convPool.selectConverter(conv_settings)
        self.app.convPool.cleanup_unused()
        if newChange:
            self.app.fontItemList.update_item(
                fontItem, newChange, ['converter.convName'])
            self.updateFontsList()
            self.fill_for_selected_font()
        logger.debug(util.funcName('end'))

    def selectFontFromStyle(self, style_ctrl, styleType):
        """Selects the font based on the style specified in style_ctrl.
        If style_ctrl is None (for initialization or testing), gets values from
        user variables instead.
        """
        logger.debug(util.funcName())
        fontItem = self.grabSelectedItem()
        if style_ctrl:
            fontType = dutil.whichSelected(self.stepCtrls.radiosFontType)
            displayName = style_ctrl.getText()
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
            fontName = fontItem.name
            fontSize = copy.copy(fontItem.size)
        comboFontName = self.stepCtrls.comboFontName
        if fontName and fontName in comboFontName.Items:
            comboFontName.setText(fontName)
        else:
            comboFontName.setText("")
        fontSize.changeCtrlVal(self.stepCtrls.txtFontSize)

    def getFontFormResults(self, updateFontItem=True, ctrl_changed=None):
        """Get form results for the currently selected font.
        Sets currently selected FontItem to the resulting FontChange.
        Returns the FontChange object.

        :param updateFontItem: true to modify item in self.app.fontItemList
        """
        logger.debug(util.funcName('begin'))
        attrs_changed = []
        fontItem = self.grabSelectedItem()
        fontChange = FontChange(fontItem, self.userVars)

        fontChange.converter.convName = self.stepCtrls.txtConvName.getText()
        fontChange.converter.forward = (
            self.stepCtrls.chkReverse.getState() == 0)
        if dutil.sameName(ctrl_changed, self.stepCtrls.chkReverse):
            attrs_changed = ['converter.forward']

        ## Font

        fontChange.name = self.stepCtrls.comboFontName.getText()
        if fontChange.name == "(None)":
            fontChange.name = None
        if dutil.sameName(ctrl_changed, self.stepCtrls.comboFontName):
            attrs_changed = ['name']
        fontChange.size = FontSize()
        fontChange.size.loadCtrl(self.stepCtrls.txtFontSize)
        fontChange.size.changeCtrlProp(self.stepCtrls.lblConverted)
        if dutil.sameName(ctrl_changed, self.stepCtrls.txtFontSize):
            attrs_changed = ['size']
        fontChange.fontType = dutil.whichSelected(
            self.stepCtrls.radiosFontType)
        if (dutil.sameName(ctrl_changed, self.stepCtrls.optFontStandard)
                or dutil.sameName(ctrl_changed, self.stepCtrls.optFontComplex)
                or dutil.sameName(ctrl_changed, self.stepCtrls.optFontAsian)):
            attrs_changed = ['fontType', 'name']

        ## Radio buttons and the corresponding listbox selection

        fontChange.styleType = dutil.whichSelected(
            self.stepCtrls.radiosStyleType)
        fontChange.styleName = None
        if (dutil.sameName(ctrl_changed, self.stepCtrls.optParaStyle)
                or dutil.sameName(ctrl_changed, self.stepCtrls.optCharStyle)
                or dutil.sameName(ctrl_changed, self.stepCtrls.optNoStyle)):
            attrs_changed = ['styleType', 'styleName']
        if fontChange.styleType == 'ParaStyle':
            displayName = self.stepCtrls.comboParaStyle.getText()
            if displayName in self.paraStyleNames:
                fontChange.styleName = self.paraStyleNames[displayName]
            else:
                logger.warning("unexpected style %s", displayName)
            if dutil.sameName(ctrl_changed, self.stepCtrls.comboParaStyle):
                attrs_changed = ['styleName']
        elif fontChange.styleType == 'CharStyle':
            displayName = self.stepCtrls.comboCharStyle.getText()
            if displayName in self.charStyleNames:
                fontChange.styleName = self.charStyleNames[displayName]
            else:
                logger.warning("unexpected style %s", displayName)
            if dutil.sameName(ctrl_changed, self.stepCtrls.comboCharStyle):
                attrs_changed = ['styleName']
        else:
            fontChange.styleName = ""
        if updateFontItem and attrs_changed:
            self.app.fontItemList.update_item(
                fontItem, fontChange, attrs_changed)
            self.updateFontsList()
        elif updateFontItem:
            logger.warning("No attributes changed.")
        logger.debug(util.funcName('end'))
        return fontChange

    def fill_for_selected_font(self):
        fontItem = self.grabSelectedItem()
        if not fontItem:
            return
        self.fill_for_font(fontItem)

    def fill_samples_for_selected_font(self):
        fontItem = self.grabSelectedItem()
        if not fontItem:
            return
        self.fill_samples(fontItem)

    def fill_for_chkJoin(self):
        self.app.fontItemList.groupFontTypes = bool(
            self.stepCtrls.chkJoinFontTypes.getState())
        self.app.fontItemList.groupSizes = bool(
            self.stepCtrls.chkJoinSize.getState())
        self.app.fontItemList.groupStyles = bool(
            self.stepCtrls.chkJoinStyles.getState())
        self.updateFontsList()

    def fill_for_font(self, fontItem):
        """Fill form according to specified font settings."""
        logger.debug(util.funcName('begin'))
        self.clear_combo_boxes()
        self.fill_found_font_info(fontItem)
        if fontItem.change:
            self.fill_for_change(fontItem.change)
        else:
            self.fill_for_no_change(fontItem)
        self.stepCtrls.enableDisable(self)
        self.fill_samples(fontItem)
        logger.debug(util.funcName('end'))

    def fill_samples(self, fontItem):
        """Called when converter changes."""
        if fontItem.change:
            converter = fontItem.change.converter
            self.samples.last_settings[converter.convName] = converter
        self.samples.set_fontItem(fontItem)
        self.nextInputSample()

    def grabSelectedItem(self):
        """Sets self.selectedIndex.
        :returns: selected found font item
        """
        try:
            self.selectedIndex = dutil.get_selected_index(
                self.stepCtrls.listFontsUsed, "a file")
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            self.selectedIndex = -1
            return None
        fontItem = self.app.fontItemList[self.selectedIndex]
        return fontItem

    def updateFontsList(self):
        dutil.fill_list_ctrl(
            self.stepCtrls.listFontsUsed,
            [str(fontItem) for fontItem in self.app.fontItemList])
        if self.selectedIndex >= 0:
            dutil.select_index(
                self.stepCtrls.listFontsUsed, self.selectedIndex)

    def clear_combo_boxes(self):
        self.stepCtrls.comboFontName.setText("")
        self.stepCtrls.comboParaStyle.setText("")
        self.stepCtrls.comboCharStyle.setText("")

    def fill_found_font_info(self, fontItem):
        """Fill form with information about the font found.
        These values are read-only, for information.
        """
        foundFontNames = ""
        for title, fontName in (
                ("Standard", fontItem.nameStandard),
                ("Complex", fontItem.nameComplex),
                ("Asian", fontItem.nameAsian)):
            foundFontNames += "%s:  %s\n" % (
                theLocale.getText(title), fontName)
        self.stepCtrls.foundFonts.setText(foundFontNames)
        if fontItem.size.isSpecified():
            fontItem.size.changeCtrlVal(self.stepCtrls.foundFontSize)
        else:
            self.stepCtrls.foundFontSize.setText("(Default)")

    def fill_for_change(self, fontChange):
        """Fill the form using the values specified in fontChange."""
        self.stepCtrls.txtConvName.setText(
            fontChange.converter.convName)
        self.stepCtrls.chkReverse.setState(
            not fontChange.converter.forward)
        if fontChange.name and fontChange.name != "(None)":
            self.stepCtrls.comboFontName.setText(fontChange.name)
        fontChange.size.changeCtrlVal(self.stepCtrls.txtFontSize)
        fontChange.size.changeCtrlProp(self.stepCtrls.lblConverted)
        dutil.selectRadio(
            self.stepCtrls.radiosFontType, fontChange.fontType)
        if fontChange.styleName:
            if fontChange.styleType == 'ParaStyle':
                self.stepCtrls.comboParaStyle.setText(fontChange.styleName)
            elif fontChange.styleType == 'CharStyle':
                self.stepCtrls.comboCharStyle.setText(fontChange.styleName)
        dutil.selectRadio(
            self.stepCtrls.radiosStyleType, fontChange.styleType)

    def fill_for_no_change(self, fontItem):
        """The fontItem has no changes, so fill the form accordingly."""
        self.stepCtrls.txtConvName.setText("<No converter>")
        self.stepCtrls.chkReverse.setState(False)
        fontItem.size.changeCtrlVal(self.stepCtrls.txtFontSize)
        fontItem.size.changeCtrlProp(
            self.stepCtrls.lblConverted, True)
        dutil.selectRadio(
            self.stepCtrls.radiosFontType, fontItem.fontType)
        dutil.selectRadio(
            self.stepCtrls.radiosStyleType, fontItem.styleType)

    def nextInputSample(self):
        if self.samples.inputData:
            if not self.samples.has_more():
                self.stepCtrls.btnNextInput.getModel().Enabled = False
                return
            inputSampleText = self.samples.gotoNext()
            self.stepCtrls.btnNextInput.getModel().Enabled = (
                self.samples.has_more())
            self.stepCtrls.lblInput.setText(inputSampleText)
            self.stepCtrls.lblSampleNum.setText(
                "%d / %d" % (
                    self.samples.sampleNum(),
                    len(self.samples.inputData)))
            convertedVal = "(None)"
            if self.stepCtrls.chkShowConverted.getState() == 1:
                try:
                    convertedVal = self.samples.get_converted()
                except exceptions.MessageError as exc:
                    self.msgbox.displayExc(exc)
            self.stepCtrls.lblConverted.setText(convertedVal)
        else:
            self.stepCtrls.btnNextInput.getModel().Enabled = False
            self.stepCtrls.lblInput.setText("(None)")
            self.stepCtrls.lblSampleNum.setText("0 / 0")

    def storeUserVars(self):
        """Store settings in user vars."""
        logger.debug(util.funcName('begin'))
        fontChanges = self.app.getFontChanges()
        self.userVars.store('FontChangesCount', str(len(fontChanges)))
        varNum = 0
        for fontChange in fontChanges:
            fontChange.setVarNum(varNum)
            varNum += 1
            fontChange.userVars = self.userVars
            fontChange.storeUserVars()

        MAX_CLEAN = 1000  # should be more than enough
        for varNum in range(len(fontChanges), MAX_CLEAN):
            fontChange = FontChange(None, self.userVars, varNum)
            foundSomething = fontChange.cleanupUserVars()
            if not foundSomething:
                break

        displayConverted = (
            self.stepCtrls.chkShowConverted.getState() == 1)
        self.userVars.store(
            'DisplayConverted', "%d" % displayConverted)
        self.app.askEach = (
            self.stepCtrls.chkVerify.getState() == 1)
        self.userVars.store(
            'AskEachChange', "%d" % self.app.askEach)
        logger.debug(util.funcName('end'))

