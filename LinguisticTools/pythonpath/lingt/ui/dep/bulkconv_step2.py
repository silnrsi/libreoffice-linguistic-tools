# -*- coding: Latin-1 -*-
#
# This file created December 24 2015 by Jim Kornelsen
#
# 05-Feb-16 JDK  Show a mark in the list to indicate font changes.
# 11-Feb-16 JDK  Show modified font settings when FontItem is selected.
# 19-Feb-16 JDK  Add checkboxes to separate font type, size and style.
# 24-Feb-16 JDK  Use a single foundFonts label instead of three labels.
# 07-Mar-16 JDK  Handle chkJoin changes.
# 25-Mar-16 JDK  Split up into separate classes for each control.
# 26-Apr-16 JDK  Implement separate style classes for combos and radios.
# 29-Apr-16 JDK  Add methods for filling to each control class.

"""
Bulk Conversion dialog step 2.

This module exports:
    FormStep2
"""
import collections
import copy
import logging

from lingt.access.writer import styles
from lingt.app import exceptions
from lingt.app.bulkconv_structs import FontChange
from lingt.app.svc.bulkconversion import Samples
from lingt.ui.common import dutil
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.utils import util
from lingt.utils.fontsize import FontSize
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgbulkconv_step2")


class FormStep2:
    """Create control classes and load values."""

    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.event_handlers = []  # controls that handle events
        self.data_controls = []  # controls that store FontItem data
        for ctrl_class in (
                ConverterControls,
                FontNameHandler,
                FontTypeHandler,
                FontSizeHandler,
                StyleTypeHandler,
                StyleNameHandler,
            ):
            controls_object = ctrl_class(ctrl_getter, app)  # create new
            self.data_controls.append(controls_object)
            self.event_handlers.append(controls_object)
        for ctrl_class in (
                ListFontsUsed,
                SampleControls,
                ClipboardButtons,
                JoinCheckboxes,
                VerifyHandler,
            ):
            controls_object = ctrl_class(ctrl_getter, app)  # create new
            self.event_handlers.append(controls_object)
        self.found_font_info = FoundFontInfo(ctrl_getter)

    def start_working(self):
        for event_handler in self.event_handlers:
            event_handler.start_working()
        self.found_font_info.fill(fontItem)

    def store_results(self):
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

        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.store_results()
        verifyHandler = VerifyHandler(self.ctrl_getter, self.app)
        verifyHandler.store_results()
        logger.debug(util.funcName('end'))

    def read_change(self):
        """Reads the form and returns a FontChange object.""" 
        fontChange = FontChange(None, self.app.userVars)
        for fontitem_controls in self.data_controls:
            fontitem_controls.update_change(fontChange)
        return fontChange

    def fill_for_item(self, fontItem):
        """Fill form according to specified font settings."""
        logger.debug(util.funcName('begin'))
        for fontitem_controls in self.data_controls:
            if fontItem.change:
                fontitem_controls.fill_for_change(fontItem.change)
            else:
                fontitem_controls.fill_for_no_change(fontItem)
        for fontitem_controls_class in (
                SampleControls,
                FoundFontInfo:,
            ):
                fontitem_controls = fontitem_controls_class(
                    self.ctrl_getter, self.app)
                fontitem_controls.fill_values(fontItem)
        logger.debug(util.funcName('end'))


class FontChangeControlHandler:
    """Abstract base class to handle reading and writing of FontItem change
    controls.
    Inherit it alongside one of the evt_handler.EventHandler subclasses.
    """

    def __init__(self, ctrl_getter, app):
        if self.__class__ is FontChangeControlHandler:
            # The base classes should not be instantiated.
            raise NotImplementedError
        self.ctrl_getter = ctrl_getter
        self.app = app

    def handle_action_event(self, src):
        self.app.update_list(self)

    def handle_item_event(self, src):
        self.app.update_list(self)

    def handle_text_event(self, src):
        self.app.update_list(self)

    #XXX: Do we need a function like this?
    #def update_change_if_ctrl_was_changed(self, fontChange):
    #    if not self.last_source:
    #        return
    #    self.read()
    #    self.last_source = None

    def update_change(self, fontChange):
        """Read form values and modify fontChange accordingly."""
        raise NotImplementedError()

    def fill_for_change(self, fontChange):
        """Set form values based on the fontChange values."""
        raise NotImplementedError()

    def fill_for_no_change(self, fontItem):
        """Set form values based on the fontItem values."""
        raise NotImplementedError()


class ListFontsUsed(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        evt_handler.ItemEventHandler.__init__(self)
        self.listFontsUsed = ctrl_getter.get(_dlgdef.LIST_FONTS_USED)
        self.msgbox = MessageBox(app.unoObjs)
        self.app = app

    def add_listeners(self):
        self.listFontsUsed.addItemListener(self)

    def handle_item_event(self, src):
        self.fill_for_selected_item()
        self.updateFontsList()

    def grab_selected_item(self):
        """Sets self.app.selected_index.
        :returns: selected found font item
        """
        try:
            self.app.selected_index = dutil.get_selected_index(
                self.listFontsUsed, "a file")
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            self.app.selected_index = -1
            return None
        return self.app.selected_item()

    def fill_for_selected_item(self):
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        form2 = FormStep2(self.ctrl_getter, self.app)
        form2.fill_for_item(fontItem)

    def updateFontsList(self):
        dutil.fill_list_ctrl(
            self.listFontsUsed,
            [str(fontItem) for fontItem in self.app.fontItemList])
        if self.app.selected_index >= 0:
            dutil.select_index(
                self.listFontsUsed, self.app.selected_index)


class ConverterControls(FontChangeControlHandler,
                        evt_handler.ActionEventHandler,
                        evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ActionEventHandler.__init__(self)
        evt_handler.ItemEventHandler.__init__(self)
        self.txtConvName = ctrl_getter.get(_dlgdef.TXT_CONV_NAME)
        self.chkReverse = ctrl_getter.get(_dlgdef.CHK_REVERSE)
        self.btnSelectConv = ctrl_getter.get(_dlgdef.BTN_CHOOSE_CONV)

    def add_listeners(self):
        self.chkReverse.addItemListener(self)
        btnSelectConv.setActionCommand('SelectConverter')
        self.btnSelectConv.addActionListener(self)

    def handle_action_event(self, action_command):
        self.selectConverter()
        FontChangeControlHandler.handle_action_event(self, action_command)
        sampleControls.fill_values_for_selected_font()

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.fill_values_for_selected_font()

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        conv_settings = None
        if fontItem.change:
            conv_settings = fontItem.change.converter
        newChange = self.app.convPool.selectConverter(conv_settings)
        self.app.convPool.cleanup_unused()
        if newChange:
            self.fill_for_change(newChange)
        else:
            self.fill_for_no_change(None)
        logger.debug(util.funcName('end'))

    def update_change(self, fontChange):
        converter = ConverterSettings()
        converter.convName = self.txtConvName.getText()
        converter.forward = (self.chkReverse.getState() == 0)
        fontChange.converter = converter

    def fill_for_change(self, fontChange):
        self.txtConvName.setText(
            fontChange.converter.convName)
        self.chkReverse.setState(
            not fontChange.converter.forward)

    def fill_for_no_change(self, dummy_fontItem):
        self.txtConvName.setText("<No converter>")
        self.chkReverse.setState(False)


class SampleControls(evt_handler.ActionEventHandler,
                     evt_handler.ItemEventHandler):
    """Controls to display sample input and converted text."""

    def __init__(self, ctrl_getter, app):
        evt_handler.ActionEventHandler.__init__(self)
        evt_handler.ItemEventHandler.__init__(self)
        self.lblInput = ctrl_getter.get(_dlgdef.INPUT_DISPLAY)
        self.lblConverted = ctrl_getter.get(_dlgdef.CONVERTED_DISPLAY)
        self.lblSampleNum = ctrl_getter.get(_dlgdef.SAMPLE_NUM)
        self.btnNextInput = ctrl_getter.get(_dlgdef.BTN_NEXT_INPUT)
        self.chkShowConverted = ctrl_getter.get(_dlgdef.CHK_SHOW_CONVERTED)
        self.samples = Samples(self.app.convPool)
        self.msgbox = MessageBox(app.unoObjs)

    def load_values(self):
        #self.chkShowConverted.setState(
        #    userVars.getInt('DisplayConverted'))
        self.chkShowConverted.setState(False)
        self.lblInput.setText("(None)")
        self.lblSampleNum.setText("0 / 0")
        self.lblConverted.setText("(None)")

    def add_listeners(self):
        self.btnNextInput.setActionCommand('NextInput')
        self.btnNextInput.addActionListener(self)
        self.chkShowConverted.addItemListener(self)

    def handle_action_event(self, action_command):
        self.nextInputSample()

    def handle_item_event(self, src):
        if self.step2Form.samples.sampleIndex > -1:
            # Show the same sample again.
            self.step2Form.samples.sampleIndex -= 1
        self.step2Form.nextInputSample()

    def nextInputSample(self):
        if self.samples.inputData:
            if not self.samples.has_more():
                self.btnNextInput.getModel().Enabled = False
                return
            inputSampleText = self.samples.gotoNext()
            self.btnNextInput.getModel().Enabled = (
                self.samples.has_more())
            self.lblInput.setText(inputSampleText)
            self.lblSampleNum.setText(
                "%d / %d" % (
                    self.samples.sampleNum(),
                    len(self.samples.inputData)))
            convertedVal = "(None)"
            if self.chkShowConverted.getState() == 1:
                try:
                    convertedVal = self.samples.get_converted()
                except exceptions.MessageError as exc:
                    self.msgbox.displayExc(exc)
            self.lblConverted.setText(convertedVal)
        else:
            self.btnNextInput.getModel().Enabled = False
            self.lblInput.setText("(None)")
            self.lblSampleNum.setText("0 / 0")

    def fill_values_for_selected_font(self):
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        self.fill_values(fontItem)

    def fill_values(self, fontItem):
        """Called when converter changes."""
        if fontItem.change:
            converter = fontItem.change.converter
            self.samples.last_settings[converter.convName] = converter
        self.samples.set_fontItem(fontItem)
        self.nextInputSample()

    def store_results(self):
        displayConverted = (
            self.chkShowConverted.getState() == 1)
        self.app.userVars.store(
            'DisplayConverted', "%d" % displayConverted)


class ClipboardButtons(evt_handler.ActionEventHandler):
    """This does not actually use the system clipboard, but it implements
    copy/paste functionality.
    """
    def __init__(self, ctrl_getter, app):
        evt_handler.ActionEventHandler.__init__(self)
        self.btnReset = dutil.getControl(dlg, 'btnReset')
        self.btnCopy = dutil.getControl(dlg, 'btnCopy')
        self.btnPaste = dutil.getControl(dlg, 'btnPaste')
        self.copiedSettings = None

    def add_listeners(self):
        self.btnReset.setActionCommand('ResetFont')
        self.btnCopy.setActionCommand('CopyFont')
        self.btnPaste.setActionCommand('PasteFont')
        for ctrl in (self.btnReset, self.btnCopy, self.btnPaste):
            ctrl.addActionListener(self)

    def handle_action_event(self, action_command):
        if event.ActionCommand == 'ResetFont':
            self.step2Form.resetFont()
        elif event.ActionCommand == 'CopyFont':
            self.step2Form.copyFont()
        elif event.ActionCommand == 'PasteFont':
            self.step2Form.pasteFont()
        else:
            self.raise_unknown_command(action_command)

    def resetFont(self):
        if not self.app.selected_item():
            return
        fontItemList = self.app.fontItemList
        item_to_update = fontItemList.selected_item()
        for item in fontItemList.items_to_change(item_to_update):
            item.change = None
        listFontsUsed = ListFontsUsed(self.ctrl_getter, self.app)
        listFontsUsed.updateFontsList()
        listFontsUsed.fill_for_selected_item()

    def copyFont(self):
        logger.debug(util.funcName())
        #self.copiedSettings = self.getFontFormResults(False)
        form2 = FormStep2(self.ctrl_getter, self.app)
        self.copiedSettings = form2.read_change(

    def pasteFont(self):
        logger.debug(util.funcName())
        if self.copiedSettings is None:
            self.msgbox.display("First copy font settings.")
            return
        fontItem = self.grabSelectedItem()
        if self.selected_index == -1:
            return
        attrs_to_change = [
            'converter.convName', 'converter.forward',
            'fontType', 'name', 'size',
            'styleType', 'styleName']
        self.app.fontItemList.update_group(
            fontItem, self.copiedSettings, attrs_to_change)
        listFontsUsed = ListFontsUsed(self.ctrl_getter, self.app)
        listFontsUsed.updateFontsList()
        listFontsUsed.fill_for_selected_item()


class JoinCheckboxes(evt_handler.ItemEventHandler):
    """Checkboxes that join or split the list."""

    def __init__(self, ctrl_getter, app):
        evt_handler.ItemEventHandler.__init__(self)
        self.chkJoinFontTypes = ctrl_getter.get(_dlgdef.CHK_JOIN_FONT_TYPES)
        self.chkJoinSize = ctrl_getter.get(_dlgdef.CHK_JOIN_SIZE)
        self.chkJoinStyles = ctrl_getter.get(_dlgdef.CHK_JOIN_STYLES)

    def load_values(self):
        self.chkJoinFontTypes.setState(userVars.getInt('JoinFontTypes'))
        self.chkJoinSize.setState(userVars.getInt('JoinSize'))
        self.chkJoinStyles.setState(userVars.getInt('JoinStyles'))

    def add_listeners(self):
        for ctrl in (
                self.chkJoinFontTypes, self.chkJoinSize, self.chkJoinStyles):
            self.addItemListener(self)

    def handle_item_event(self, src):
        self.fill_for_chkJoin()

    def fill_for_chkJoin(self):
        self.app.fontItemList.groupFontTypes = bool(
            self.chkJoinFontTypes.getState())
        self.app.fontItemList.groupSizes = bool(
            self.chkJoinSize.getState())
        self.app.fontItemList.groupStyles = bool(
            self.chkJoinStyles.getState())
        self.updateFontsList()


class FoundFontInfo:
    """Information about the font found.  These values are read-only."""

    def __init__(self, ctrl_getter, app):
        self.foundFonts = ctrl_getter.get(_dlgdef.FOUND_FONTS)
        self.foundFontSize = ctrl_getter.get(_dlgdef.FOUND_FONT_SIZE)

    def fill_values(self, fontItem):
        foundFontNames = ""
        for title, fontName in (
                ("Standard", fontItem.nameStandard),
                ("Complex", fontItem.nameComplex),
                ("Asian", fontItem.nameAsian)):
            foundFontNames += "%s:  %s\n" % (
                theLocale.getText(title), fontName)
        self.foundFonts.setText(foundFontNames)
        if fontItem.size.isSpecified():
            fontItem.size.changeCtrlVal(self.foundFontSize)
        else:
            self.foundFontSize.setText("(Default)")


class FontNameHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.comboFontName = ctrl_getter.get(_dlgdef.COMBO_FONT_NAME)

    def load_values(self):
        fontNames = styles.getListOfFonts(self.app.unoObjs, addBlank=True)
        dutil.fill_list_ctrl(self.comboFontName, fontNames)

    def add_listeners(self):
        self.comboFontName.addItemListener(self.evtHandler)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        self.change_control_prop(app.selected_item())
        style_type_handler = StyleTypeHandler(self.ctrl_getter, self.app)
        style_type_handler.set_values('CustomFormatting')
        self.app.update_list(style_type_handler)

    def update_change(self, fontChange):
        fontChange.name = self.comboFontName.getText()
        if fontChange.name == "(None)":
            fontChange.name = None

    def fill_for_no_change(self, fontItem):
        self.clear_combo_box()

    def fill_for_change(self, fontChange):
        if fontChange.name and fontChange.name != "(None)":
            self.comboFontName.setText(fontChange.name)
        else:
            self.clear_combo_box()

    def clear_combo_box(self):
        self.comboFontName.setText("")

    def change_control_prop(self, fontItem):
        """See also lingt.access.writer.textchanges.changeFont()."""
        lblConverted = ctrl_getter.get(_dlgdef.CONVERTED_DISPLAY)
        lblConverted.getModel().FontName = fontItem.name
        lblConverted.getModel().FontNameAsian = fontItem.name


class FontTypeHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.optStandard = ctrl_getter.get(_dlgdef.OPT_FONT_STANDARD)
        self.optComplex = ctrl_getter.get(_dlgdef.OPT_FONT_COMPLEX)
        self.optAsian = ctrl_getter.get(_dlgdef.OPT_FONT_ASIAN)
        self.radios = [
            dutil.RadioTuple(self.optStandard, 'Western'),
            dutil.RadioTuple(self.optComplex, 'Complex'),
            dutil.RadioTuple(self.optAsian, 'Asian')]

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def update_change(self, fontChange):
        fontChange.fontType = dutil.whichSelected(self.radios)
        #font_name_handler = FontNameHandler(self.ctrl_getter, self.app)
        #font_name_handler.read(fontChange)

    def fill_for_no_change(self, fontItem):
        self.set_values(fontItem.fontType)

    def fill_for_change(self, fontChange):
        self.set_values(fontChange.fontType)

    def set_values(self, fontType):
        dutil.selectRadio(self.radios, fontChange.fontType)


class FontSizeHandler(FontChangeControlHandler, evt_handler.TextEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.TextEventHandler.__init__(self)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_FONT_SIZE)

    def add_listeners(self):
        self.txtFontSize.addTextListener(self)

    def update_change(self, fontChange):
        fontChange.size = FontSize()
        fontChange.size.loadCtrl(self.txtFontSize)

    def fill_for_no_change(self, fontItem):
        fontItem.size.changeCtrlVal(self.txtFontSize)
        fontItem.size.changeCtrlProp(self.stepCtrls.lblConverted, True)

    def fill_for_change(self, fontChange):
        fontChange.size.changeCtrlVal(self.txtFontSize)
        fontChange.size.changeCtrlProp(self.stepCtrls.lblConverted)

    def change_control_prop(self, fontItem):
        lblConverted = ctrl_getter.get(_dlgdef.CONVERTED_DISPLAY)
        fontItem.size.changeCtrlProp(lblConverted)


class StyleTypeHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.optParaStyle = ctrl_getter.get(_dlgdef.OPT_PARA_STYLE)
        self.optCharStyle = ctrl_getter.get(_dlgdef.OPT_CHAR_STYLE)
        self.optNoStyle = ctrl_getter.get(_dlgdef.OPT_NO_STYLE)  # not any style
        self.radios = [
            dutil.RadioTuple(self.optNoStyle, 'CustomFormatting'),
            dutil.RadioTuple(self.optParaStyle, 'ParaStyle'),
            dutil.RadioTuple(self.optCharStyle, 'CharStyle')]

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        style_name_handler = StyleName(self.ctrl_getter, self.app)
        style_name_handler.selectFontFromStyle()

    def update_change(self, fontChange):
        fontChange.fontType = dutil.whichSelected(self.radios)
        style_name_handler = StyleNameHandler(self.ctrl_getter, self.app)
        style_name_handler.read(fontChange)

    def fill_for_change(self, fontChange):
        self.set_values(fontChange.fontType)

    def fill_for_no_change(self, fontItem):
        self.set_values(fontItem.fontType)

    def set_values(self, fontType):
        dutil.selectRadio(self.radios, fontType)


StyleNameTuple = collections.namedtuple(
    'StyleNameTuple', ['styleType', 'ctrl', 'styleNames'])

class StyleNameHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        comboParaStyle = dutil.getControl(dlg, 'comboParaStyle')
        comboCharStyle = dutil.getControl(dlg, 'comboCharStyle')
        self.styledata = [
            StyleNameTuple('Paragraph', comboParaStyle, []),
            StyleNameTuple('Character', comboCharStyle, [])]

    def load_values(self):
        logger.debug(util.funcName())
        for data in self.styledata:
            stylesList = styles.getListOfStyles(
                data.styleType + 'Styles', self.unoObjs)
            data.styleNames = dict(stylesList)
            dispNames = tuple([dispName for dispName, name in stylesList])
            dutil.fill_list_ctrl(data.ctrl, dispNames)

    def add_listeners(self):
        for data in self.styledata:
            data.ctrl.addItemListener(self.evtHandler)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        style_type_handler = StyleTypeHandler(self.ctrl_getter, self.app)
        fontItem = self.app.selected_item()
        if fontItem.change:
            style_type_handler.set_values(fontItem.change.styleType)
            self.selectFontFromStyle(src, fontItem.change.styleType)
        else:
            style_type_handler.set_values(fontItem.styleType)
            self.selectFontFromStyle(src, fontItem.styleType)

    def update_change(self, fontChange):
        fontChange.styleName = ""
        for data in self.styledata:
            if dutil.sameName(self.last_source, data.ctrl):
                fontChange.styleType = data.styleType
                displayName = data.ctrl.getText()
                try:
                    fontChange.styleName = data.styleNames[displayName]
                except KeyError:
                    logger.warning("%s is not a known style.", displayName)
                break

    def selectFontFromStyle(self):
        """Selects the font based on the style."""
        logger.debug(util.funcName())
        fontChange = self.app.selected_item().change
        if fontChange.styleType == 'CustomFormatting':
            return
        self.readFontOfStyle(fontChange)
        font_name_handler = FontNameHandler(self.ctrl_getter, self.app)
        font_name_handler.set_values(fontChange)
        font_size_handler = FontSizeHandler(self.ctrl_getter, self.app)
        font_size_handler.set_values(fontChange)

    def readFontOfStyle(self, fontChange):
        """Sets fontChange.fontName and fontChange.fontSize."""
        styleFonts = styles.StyleFonts(self.app.unoObjs)
        name, size = styleFonts.getFontOfStyle(
            fontChange.styleType,
            fontChange.fontType,
            fontChange.styleName)
        fontChange.fontName = name
        fontChange.fontSize = size

    def fill_for_no_change(self, fontItem):
        self.clear_combo_boxes()

    def fill_for_change(self, fontChange):
        for data in self.styledata:
            if data.styleType == fontChange.styleType:
                data.ctrl.setText(fontChange.styleName)

    def clear_combo_boxes(self):
        for data in self.styledata:
            data.ctrl.setText("")


class VerifyHandler(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        self.chkVerify = ctrl_getter.get(_dlgdef.CHK_VERIFY)
        self.app = app

    def load_values(self):
        self.chkVerify.setState(self.app.userVars.getInt('AskEachChange'))

    def store_results(self):
        self.app.askEach = (
            self.stepCtrls.chkVerify.getState() == 1)
        self.app.userVars.store(
            'AskEachChange', "%d" % self.app.askEach)

