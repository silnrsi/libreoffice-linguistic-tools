# -*- coding: Latin-1 -*-
#
# This file created June 16 2016 by Jim Kornelsen
#
# 24-Jun-16 JDK  FontItemList holds FontItemGroup instead of FontItem.
# 16-Jul-16 JDK  Instead of fonts, use StyleItems that depend on scope type.

"""
Bulk Conversion classes that hold controls for StyleItem data.

This module exports:
    ConverterControls
    StyleControls
    FontControls
"""
import copy
import logging

from lingt.access.writer import styles
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import StyleItem, StyleType
from lingt.app.svc.bulkconversion import Samples
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.utils import util
from lingt.utils.fontsize import FontSize
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgbulkconv_step2items")


class StyleChangeControlHandler:
    """Abstract base class to handle controls that display and
    modify StyleChange objects.
    Inherit it alongside one of the evt_handler.EventHandler subclasses.
    """

    def __init__(self, ctrl_getter, app, step2Master):
        if self.__class__ is StyleChangeControlHandler:
            # The base classes should not be instantiated.
            raise NotImplementedError
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = step2Master

    def handle_action_event(self, dummy_action_command):
        self.app.update_list(self)
        self.step2Master.refresh_list()

    def handle_item_event(self, dummy_src):
        self.app.update_list(self)
        self.step2Master.refresh_list()

    def handle_text_event(self, dummy_src):
        self.app.update_list(self)
        self.step2Master.refresh_list()

    def update_change(self, styleChange):
        """Read form values and modify styleChange accordingly."""
        item.create_change(self.app.userVars)

    def copy_change(self, change_from, change_to):
        """Set attributes of change_to based on change_from."""
        pass

    def fill_for_item(self, styleItem):
        if styleItem.change:
            self._fill_for_item_change(styleItem.change)
        else:
            self._fill_for_item_no_change(styleItem)

    def _fill_for_item_change(self, styleChange):
        """Set form values based on the styleChange values."""
        pass

    def _fill_for_item_no_change(self, styleItem):
        """Set form values based on the styleItem values."""
        pass


class AggregateControlHandler(StyleChangeControlHandler):
    """Holds a group of handlers."""

    def __init__(self, ctrl_getter, app, step2Master):
        if self.__class__ is AggregateControlHandler:
            # The base classes should not be instantiated.
            raise NotImplementedError
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        self.controls_objects = []

    def start_working(self, *args, **kwargs):
        self._invoke_for_each('start_working', *args, **kwargs)

    def update_change(self, *args, **kwargs):
        self._invoke_for_each('update_change', *args, **kwargs)

    def copy_change(self, *args, **kwargs):
        self._invoke_for_each('copy_change', *args, **kwargs)

    def fill_for_item(self, *args, **kwargs):
        self._invoke_for_each('fill_for_item', *args, **kwargs)

    def _invoke_for_each(self, methodName, *args, **kwargs):
        """Invoke the method on each handler."""
        for controls_object in self.controls_objects:
            meth = getattr(controls_object, methodName)
            meth(*args, **kwargs)


class ConverterControls(AggregateControlHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        AggregateControlHandler.__init__(self, ctrl_getter, app, step2Master)
        sampleControls = SampleControls(ctrl_getter, app)
        convName = ConvName(ctrl_getter, app, step2Master, sampleControls)
        chkReverse = CheckboxReverse(
            ctrl_getter, app, step2Master, sampleControls)
        self.controls_objects = (
            convName, chkReverse, sampleControls)


class ConvName(StyleChangeControlHandler, evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, sample_controls):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ActionEventHandler.__init__(self)
        self.sample_controls = sample_controls
        self.btnSelectConv = ctrl_getter.get(_dlgdef.BTN_CHOOSE_CONV)
        self.txtConvName = ctrl_getter.get(_dlgdef.TXT_CONV_NAME)

    def add_listeners(self):
        self.btnSelectConv.setActionCommand('SelectConverter')
        self.btnSelectConv.addActionListener(self)

    def handle_action_event(self, action_command):
        self.selectConverter()
        StyleChangeControlHandler.handle_action_event(self, action_command)
        self.sample_controls.fill_for_selected_item()

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        item = self.app.selected_item()
        if not item:
            return
        conv_settings = None
        if item.change:
            conv_settings = item.change.converter
        new_conv_settings = self.app.convPool.selectConverter(conv_settings)
        item.create_change(self.app.userVars)
        item.change.converter = new_conv_settings
        self.fill_for_item(item)
        checkboxReverse = CheckboxReverse(
            self.ctrl_getter, self.app, self.step2Master, self.sample_controls)
        checkboxReverse.fill_for_item(item)
        self.app.convPool.cleanup_unused()
        logger.debug("len(styleChanges) = %d", len(self.app.getStyleChanges()))
        logger.debug(
            repr([repr(change) for change in self.app.getStyleChanges()]))
        logger.debug(util.funcName('end'))

    def update_change(self, styleChange):
        converter = styleChange.converter
        converter.txtConvName = self.txtConvName.getText()

    def _fill_for_item_change(self, styleChange):
        self.txtConvName.setText(
            styleChange.converter.convName)

    def _fill_for_item_no_change(self, dummy_styleItem):
        self.txtConvName.setText("<No converter>")

    def copy_change(self, change_from, change_to):
        change_to.converter.convName = change_from.converter.convName


class CheckboxReverse(StyleChangeControlHandler,
                      evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, sample_controls):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.sample_controls = sample_controls
        self.chkReverse = ctrl_getter.get(_dlgdef.CHK_REVERSE)

    def add_listeners(self):
        self.chkReverse.addItemListener(self)

    def handle_item_event(self, src):
        StyleChangeControlHandler.handle_item_event(self, src)
        self.sample_controls.fill_for_selected_item()

    def update_change(self, styleChange):
        converter = styleChange.converter
        converter.forward = (self.chkReverse.getState() == 0)

    def _fill_for_item_change(self, styleChange):
        self.chkReverse.setState(
            not styleChange.converter.forward)

    def _fill_for_item_no_change(self, dummy_styleItem):
        self.chkReverse.setState(False)

    def copy_change(self, change_from, change_to):
        change_to.converter.forward = change_from.converter.forward


class SampleControls(StyleChangeControlHandler, evt_handler.EventHandler):
    def __init__(self, ctrl_getter, app):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, None)
        evt_handler.EventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.samples = Samples(self.app.convPool)
        self.sampleLabels = SampleLabels(ctrl_getter, app)
        self.nextInputControls = ButtonNextInput(
            ctrl_getter, app, self.samples, self.sampleLabels)
        self.showConvControls = CheckboxShowConverted(
            ctrl_getter, app, self.nextInputControls)

    def start_working(self):
        self.sampleLabels.load_values()
        self.nextInputControls.start_working()
        self.showConvControls.start_working()

    def store_results(self):
        self.showConvControls.store_results()

    def fill_for_selected_item(self):
        self.fill_for_item(self.app.selected_item())

    def fill_for_item(self, styleItem):
        logger.debug(util.funcName('begin'))
        if not styleItem:
            logger.debug(util.funcName('return'))
            return
        if styleItem.change:
            converter = styleItem.change.converter
            self.samples.last_settings[converter.convName] = converter
        self.samples.set_styleItem(self.app.selected_item())
        self.change_font_name(styleItem)
        self.change_font_size(styleItem)
        self.nextInputControls.nextInputSample()
        logger.debug(util.funcName('end'))

    def change_font_name(self, styleItem):
        self.sampleLabels.change_font_name(styleItem)

    def change_font_size(self, styleItem):
        self.sampleLabels.change_font_size(styleItem)


class SampleLabels:
    """Label controls to display sample input and converted text."""

    def __init__(self, ctrl_getter, app):
        self.app = app
        self.lblInput = ctrl_getter.get(_dlgdef.INPUT_DISPLAY)
        self.lblConverted = ctrl_getter.get(_dlgdef.CONVERTED_DISPLAY)
        self.lblSampleNum = ctrl_getter.get(_dlgdef.SAMPLE_NUM)

    def load_values(self):
        self.lblInput.setText(Samples.NO_DATA)
        self.lblSampleNum.setText("0 / 0")
        self.lblConverted.setText(Samples.NO_DATA)

    def fill_for_data(self, samples):
        logger.debug(util.funcName())
        inputSampleText = samples.inputData[samples.sampleIndex]
        self.lblInput.setText(inputSampleText)
        self.lblSampleNum.setText(
            "%d / %d" % (
                samples.sampleNum(), len(samples.inputData)))
        self.lblConverted.setText(samples.converted_data)

    def fill_for_no_data(self):
        logger.debug(util.funcName())
        self.lblInput.setText(Samples.NO_DATA)
        self.lblSampleNum.setText("0 / 0")
        self.lblConverted.setText(Samples.NO_DATA)

    def change_font_name(self, styleItem):
        styleItem_font_name, dummy_size = self._effective_font(styleItem)
        self._change_font_name(styleItem_font_name, self.lblInput)
        convertedFontName = styleItem_font_name
        styleChange_font_name, dummy_size = self._effective_font(
            styleItem.change)
        if styleChange_font_name and styleChange_font_name != "(Default)":
            convertedFontName = styleChange_font_name
        self._change_font_name(convertedFontName, self.lblConverted)

    def change_font_size(self, styleItem):
        dummy_fontName, styleItemSize = self._effective_font(styleItem)
        self._change_font_size(styleItemSize, self.lblInput)
        convertedSize = styleItemSize
        dummy_fontName, styleChangeSize = self._effective_font(
            styleItem.change)
        if styleChangeSize and styleChangeSize.isSpecified():
            convertedSize = styleChangeSize
        self._change_font_size(convertedSize, self.lblConverted)

    def _effective_font(self, styleInfo):
        """Returns font name and size, from the style if possible."""
        if not styleInfo:
            return "", None
        if styleInfo.styleType == StyleType.CUSTOM:
            return styleInfo.fontName, styleInfo.size
        else:
            return getFontOfStyle(styleInfo, self.app.unoObjs)

    def _change_font_name(self, fontName, ctrl):
        """See also lingt.access.writer.textchanges.changeFont()."""
        if not fontName:
            fontName = " "
        logger.debug("set %s.FontName %s", ctrl.getModel().Name, fontName)
        ctrl.getModel().setPropertyValue('FontName', fontName)

    def _change_font_size(self, fontSize, ctrl):
        logger.debug("Font size '%s'", fontSize.getString())
        fontSize.changeCtrlProp(ctrl, always_change=True)


class ButtonNextInput(StyleChangeControlHandler,
                      evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, samples, sampleLabels):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, None)
        evt_handler.ActionEventHandler.__init__(self)
        self.samples = samples
        self.sampleLabels = sampleLabels
        self.btnNextInput = ctrl_getter.get(_dlgdef.BTN_NEXT_INPUT)

    def add_listeners(self):
        self.btnNextInput.setActionCommand('NextInput')
        self.btnNextInput.addActionListener(self)

    def handle_action_event(self, dummy_action_command):
        self.nextInputSample()

    def nextInputSample(self):
        logger.debug(util.funcName('begin'))
        if not self.samples.inputData:
            logger.debug("No samples.")
            self.btnNextInput.getModel().Enabled = False
            self.sampleLabels.fill_for_no_data()
            return
        if not self.samples.has_more():
            logger.debug("No more samples.")
            self.btnNextInput.getModel().Enabled = False
            return
        self.samples.gotoNext()
        self.btnNextInput.getModel().Enabled = (
            self.samples.has_more())
        controls = CheckboxShowConverted(self.ctrl_getter, self.app, self)
        if controls.chkShowConverted.getState() == 1:
            try:
                self.samples.get_converted()
            except exceptions.MessageError as exc:
                self.app.msgbox.displayExc(exc)
        self.sampleLabels.fill_for_data(self.samples)
        logger.debug(util.funcName('end'))

    def show_sample_again(self):
        if self.samples.sampleIndex > -1:
            self.samples.sampleIndex -= 1
        self.nextInputSample()


class CheckboxShowConverted(StyleChangeControlHandler,
                            evt_handler.ItemEventHandler):
    """Display converted text if checked."""

    def __init__(self, ctrl_getter, app, next_input_controls):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, None)
        evt_handler.ItemEventHandler.__init__(self)
        self.next_input_controls = next_input_controls
        self.chkShowConverted = ctrl_getter.get(_dlgdef.CHK_SHOW_CONVERTED)

    def load_values(self):
        self.chkShowConverted.setState(
            userVars.getInt('DisplayConverted'))
        #self.chkShowConverted.setState(False)

    def add_listeners(self):
        self.chkShowConverted.addItemListener(self)

    def handle_item_event(self, dummy_src):
        self.store_results()
        self.next_input_controls.show_sample_again()

    def store_results(self):
        self.app.userVars.store(
            'DisplayConverted', str(self.chkShowConverted.getState()))


class FontControls(AggregateControlHandler):
    def __init__(self, ctrl_getter, app, step2Master, style_type_handler):
        AggregateControlHandler.__init__(self, ctrl_getter, app, step2Master)
        font_name_handler = FontNameHandler(
            ctrl_getter, app, step2Master, style_type_handler)
        font_type_handler = FontTypeHandler(
            ctrl_getter, app, step2Master, font_name_handler)
        font_size_handler = FontSizeHandler(
            ctrl_getter, app, step2Master)
        self.controls_objects = (
            font_name_handler, font_type_handler, font_size_handler)


class FontNameHandler(StyleChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, style_type_handler):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.style_type_handler = style_type_handler
        self.comboFontName = ctrl_getter.get(_dlgdef.COMBO_FONT_NAME)

    def load_values(self):
        fontNames = styles.getListOfFonts(self.app.unoObjs, addBlank=True)
        dutil.fill_list_ctrl(self.comboFontName, fontNames)

    def add_listeners(self):
        self.comboFontName.addItemListener(self)

    def handle_item_event(self, src):
        StyleChangeControlHandler.handle_item_event(self, src)
        self.change_control_prop()
        self.set_style_radio()

    def update_change(self, styleChange):
        styleChange.fontName = self.comboFontName.getText()
        if styleChange.fontName == "(None)":
            styleChange.fontName = ""
        else:
            styleChange.styleType = StyleType.CUSTOM

    def _fill_for_item_no_change(self, dummy_styleItem):
        self.clear_combo_box()
        self.change_control_prop()

    def _fill_for_item_change(self, styleChange):
        if styleChange.fontName and styleChange.fontName != "(None)":
            self.comboFontName.setText(styleChange.fontName)
        else:
            self.clear_combo_box()
        self.change_control_prop()

    def copy_change(self, change_from, change_to):
        change_from.fontName = change_to.fontName

    def clear_combo_box(self):
        self.comboFontName.setText("")

    def change_control_prop(self):
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.change_font_name(self.app.selected_item())

    def set_style_radio(self):
        """Sets the style type radio buttons to Custom Formatting."""
        style_item = self.app.selected_item()
        self.style_type_handler.fill_for_item(style_item)
        # Calling update_change() gets the style name.
        self.style_type_handler.update_item_changes(style_item)
        self.app.update_list(self.style_type_handler)


class FontTypeHandler(StyleChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, font_name_handler):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.font_name_handler = font_name_handler
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

    def update_change(self, styleChange):
        styleChange.fontType = dutil.whichSelected(self.radios)
        self.font_name_handler.update_change(styleChange)

    def _fill_for_item_no_change(self, styleItem):
        self.fill(styleItem.fontType)

    def _fill_for_item_change(self, styleChange):
        self.fill(styleChange.fontType)

    def copy_change(self, change_from, change_to):
        change_from.fontType = change_to.fontType

    def fill(self, fontType, *dummy_args):
        dutil.selectRadio(self.radios, fontType)


class FontSizeHandler(StyleChangeControlHandler, evt_handler.TextEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.TextEventHandler.__init__(self)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_FONT_SIZE)

    def add_listeners(self):
        self.txtFontSize.addTextListener(self)

    def handle_text_event(self, src):
        StyleChangeControlHandler.handle_text_event(self, src)
        self.change_control_prop()

    def update_change(self, styleChange):
        styleChange.size = FontSize(propSuffix=styleChange.getPropSuffix())
        styleChange.size.loadCtrl(self.txtFontSize)

    def fill_for_item(self, styleItem):
        if styleItem.change:
            fontSize = styleItem.change.size
            fontSize.changeCtrlVal(self.txtFontSize)
        else:
            self.txtFontSize.setText("")
        self.change_control_prop()

    def copy_change(self, change_from, change_to):
        change_from.size = copy.copy(change_to.size)

    def change_control_prop(self):
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.change_font_size(
            self.app.selected_item())


class StyleControls(AggregateControlHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        AggregateControlHandler.__init__(self, ctrl_getter, app, step2Master)
        style_name_handler = StyleNameHandler(
            ctrl_getter, app, step2Master)
        self.style_type_handler = StyleTypeHandler(
            ctrl_getter, app, step2Master, style_name_handler)
        style_checkbox_handler = StyleCheckboxHandler(
            ctrl_getter, app, step2Master)
        style_name_handler.set_style_type_handler(self.style_type_handler)
        self.controls_objects = (
            self.style_type_handler, style_name_handler,
            style_checkbox_handler)

    def get_style_type_handler(self):
        return self.style_type_handler


def getFontOfStyle(styleInfo, unoObjs):
    styleFonts = styles.StyleFonts(unoObjs)
    return styleFonts.getFontOfStyle(
        styleInfo.styleType, styleInfo.fontType, styleInfo.styleName)

def readFontOfStyle(styleChange, unoObjs):
    styleChange.fontName, styleChange.fontSize = getFontOfStyle(
        styleChange, unoObjs)

class StyleNameHandler(StyleChangeControlHandler,
                       evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        para_list = StyleList(
            StyleType.PARA, ctrl_getter.get(_dlgdef.COMBO_PARA_STYLE),
            self.app.unoObjs)
        char_list = StyleList(
            StyleType.CHAR, ctrl_getter.get(_dlgdef.COMBO_CHAR_STYLE),
            self.app.unoObjs)
        self.stylelists = [para_list, char_list]
        self.style_type_handler = None

    def set_style_type_handler(self, handler):
        """Call this method before using this class."""
        self.style_type_handler = handler

    def load_values(self):
        logger.debug(util.funcName())
        for stylelist in self.stylelists:
            stylelist.load_values()

    def add_listeners(self):
        for stylelist in self.stylelists:
            stylelist.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        StyleChangeControlHandler.handle_item_event(self, src)
        self.style_type_handler.fill_for_item(self.app.selected_item())
        self.selectFontFromStyle()

    def update_change(self, styleChange):
        styleChange.styleName = ""
        styleChange.styleDisplayName = ""
        for stylelist in self.stylelists:
            if stylelist.same_ctrl(self.last_source):
                stylelist.update_change(styleChange)

    def update_change_for_type(self, styleChange, styleType):
        logger.debug(util.funcName())
        styleChange.styleName = ""
        styleChange.styleDisplayName = ""
        if styleChange.styleType == StyleType.CUSTOM:
            font_name_handler = FontNameHandler(
                self.ctrl_getter, self.app, self.step2Master,
                self.style_type_handler)
            font_name_handler.update_change(styleChange)
            font_size_handler = FontSizeHandler(
                self.ctrl_getter, self.app, self.step2Master)
            font_size_handler.update_change(styleChange)
            return
        for stylelist in self.stylelists:
            if stylelist.same_type(styleType):
                stylelist.update_change(styleChange)

    def selectFontFromStyle(self):
        """Selects the font based on the style."""
        logger.debug(util.funcName())
        styleItem = self.app.selected_item()
        styleChange = styleItem.change
        if styleChange.styleType == StyleType.CUSTOM:
            return
        readFontOfStyle(styleChange, self.app.unoObjs)
        font_name_handler = FontNameHandler(
            self.ctrl_getter, self.app, self.step2Master,
            self.style_type_handler)
        font_name_handler.fill_for_item(styleItem)
        font_size_handler = FontSizeHandler(
            self.ctrl_getter, self.app, self.step2Master)
        font_size_handler.fill_for_item(styleItem)

    def _fill_for_item_no_change(self, dummy_styleItem):
        self.clear_combo_boxes()

    def _fill_for_item_change(self, styleChange):
        for stylelist in self.stylelists:
            if stylelist.same_type(styleChange.styleType):
                stylelist.ctrl.setText(styleChange.styleDisplayName)

    def clear_combo_boxes(self):
        for stylelist in self.stylelists:
            stylelist.ctrl.setText("")

    def copy_change(self, change_from, change_to):
        change_from.styleName = change_to.styleName
        change_from.styleDisplayName = change_to.styleDisplayName


class StyleList:
    """Manage the control and dictionary for a list of styles."""
    def __init__(self, styleType, ctrl, unoObjs):
        self.styleType = styleType
        self.ctrl = ctrl
        self.unoObjs = unoObjs
        self.styleNames = {}  # keys display name, values underlying name

    def load_values(self):
        family = 'ParagraphStyles'
        if self.styleType == StyleType.CHAR:
            family = 'CharacterStyles'
        namesList = styles.getListOfStyles(family, self.unoObjs)
        self.styleNames.update(dict(namesList))
        displayNames = tuple([dispName for dispName, dummy_name in namesList])
        dutil.fill_list_ctrl(self.ctrl, displayNames)

    def update_change(self, styleChange):
        styleChange.styleType = self.styleType
        displayName = self.ctrl.getText()
        styleChange.styleDisplayName = displayName
        try:
            styleChange.styleName = self.styleNames[displayName]
        except KeyError:
            logger.warning(
                "%s is not a known %s.", displayName, self.styleType)

    def same_ctrl(self, ctrl):
        return evt_handler.sameName(ctrl, self.ctrl)

    def same_type(self, styleType):
        return styleType == self.styleType


class StyleTypeHandler(StyleChangeControlHandler,
                       evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, style_name_handler):
        StyleChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.style_name_handler = style_name_handler
        self.optParaStyle = ctrl_getter.get(_dlgdef.OPT_PARA_STYLE)
        self.optCharStyle = ctrl_getter.get(_dlgdef.OPT_CHAR_STYLE)
        self.optNoStyle = ctrl_getter.get(_dlgdef.OPT_NO_STYLE)
        self.radios = [
            dutil.RadioTuple(self.optNoStyle, StyleType.CUSTOM),
            dutil.RadioTuple(self.optParaStyle, StyleType.PARA),
            dutil.RadioTuple(self.optCharStyle, StyleType.CHAR)]

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        StyleChangeControlHandler.handle_item_event(self, src)
        self.style_name_handler.selectFontFromStyle()

    def update_change(self, styleChange):
        styleChange.styleType = dutil.whichSelected(self.radios)
        self.style_name_handler.update_change_for_type(
            styleChange, styleChange.styleType)

    def _fill_for_item_change(self, styleChange):
        self.fill(styleChange.styleType)

    def _fill_for_item_no_change(self, styleItem):
        self.fill(styleItem.styleType)

    def fill(self, styleType, *dummy_args):
        dutil.selectRadio(self.radios, styleType)

    def copy_change(self, change_from, change_to):
        change_from.styleType = change_to.styleType


