# -*- coding: Latin-1 -*-
#
# This file created June 16 2016 by Jim Kornelsen

"""
Bulk Conversion classes that hold controls for FontItem data.

This module exports all of its classes, including the following aggregates:
    ConverterControls
    StyleControls
    FontControls
"""
import copy
import logging

from lingt.access.writer import styles
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import FontItem, FontChange
from lingt.app.svc.bulkconversion import Samples
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.ui.dep.bulkconv_step2 import AggregateControlHandler
from lingt.ui.dep.bulkconv_step2 import FontChangeControlHandler
from lingt.utils import util
from lingt.utils.fontsize import FontSize
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgbulkconv_step2items")


class ConverterControls(AggregateControlHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        AggregateControlHandler.__init__(self, ctrl_getter, app, step2Master)
        sampleControls = SampleControls(ctrl_getter, app)
        convName = ConvName(ctrl_getter, app, step2Master, sampleControls)
        chkReverse = CheckboxReverse(
            ctrl_getter, app, step2Master, sampleControls)
        self.controls_objects = (
            convName, chkReverse, sampleControls)


class ConvName(FontChangeControlHandler, evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, sample_controls):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ActionEventHandler.__init__(self)
        self.sample_controls = sample_controls
        self.btnSelectConv = ctrl_getter.get(_dlgdef.BTN_CHOOSE_CONV)
        self.txtConvName = ctrl_getter.get(_dlgdef.TXT_CONV_NAME)

    def add_listeners(self):
        self.btnSelectConv.setActionCommand('SelectConverter')
        self.btnSelectConv.addActionListener(self)

    def handle_action_event(self, action_command):
        self.selectConverter()
        FontChangeControlHandler.handle_action_event(self, action_command)
        self.sample_controls.fill_for_selected_item()

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        conv_settings = None
        if fontItem.change:
            conv_settings = fontItem.change.converter
        newChange = self.app.convPool.selectConverter(conv_settings)
        fontItem.set_change(newChange)
        self.app.convPool.cleanup_unused()
        checkboxReverse = CheckboxReverse(
            self.ctrl_getter, self.app, self.step2Master, self.sample_controls)
        self.fill_for_item(fontItem)
        checkboxReverse.fill_for_item(fontItem)
        logger.debug(util.funcName('end'))

    def update_change(self, fontChange):
        converter = fontChange.converter
        converter.txtConvName = self.txtConvName.getText()

    def _fill_for_item_change(self, fontChange):
        self.txtConvName.setText(
            fontChange.converter.convName)

    def _fill_for_item_no_change(self, dummy_fontItem):
        self.txtConvName.setText("<No converter>")

    def copy_change(self, change_from, change_to):
        change_to.converter.convName = change_from.converter.convName


class CheckboxReverse(FontChangeControlHandler,
                      evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, sample_controls):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.sample_controls = sample_controls
        self.chkReverse = ctrl_getter.get(_dlgdef.CHK_REVERSE)

    def add_listeners(self):
        self.chkReverse.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        self.sample_controls.fill_for_selected_item()

    def update_change(self, fontChange):
        converter = fontChange.converter
        converter.forward = (self.chkReverse.getState() == 0)

    def _fill_for_item_change(self, fontChange):
        self.chkReverse.setState(
            not fontChange.converter.forward)

    def _fill_for_item_no_change(self, dummy_fontItem):
        self.chkReverse.setState(False)

    def copy_change(self, change_from, change_to):
        change_to.converter.forward = change_from.converter.forward


class SampleControls(FontChangeControlHandler, evt_handler.EventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, None)
        evt_handler.EventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.samples = Samples(self.app.convPool)
        self.sampleLabels = SampleLabels(ctrl_getter, app)
        self.nextInputControls = ButtonNextInput(
            ctrl_getter, app, self.samples, self.sampleLabels)
        self.showConvControls = CheckboxShowConverter(
            ctrl_getter, app, self.nextInputControls)

    def start_working(self):
        self.sampleLabels.load_values()
        self.nextInputControls.start_working()
        self.showConvControls.start_working()

    def store_results(self):
        self.showConvControls.store_results()

    def fill_for_selected_item(self):
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        self.fill_for_item(fontItem)

    def fill_for_item(self, fontItem):
        if fontItem.change:
            converter = fontItem.change.converter
            self.samples.last_settings[converter.convName] = converter
        self.samples.set_fontItem(fontItem)
        self.change_font_name(fontItem)
        self.change_font_size(fontItem)
        self.nextInputControls.nextInputSample()

    def change_font_name(self, fontItem):
        self.sampleLabels.change_font_name(fontItem)

    def change_font_size(self, fontItem):
        self.sampleLabels.change_font_size(fontItem)


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

    def change_font_name(self, fontItem):
        fontItemName, dummy_size = self._effective_font(fontItem)
        self._change_font_name(fontItemName, self.lblInput)
        convertedFontName = fontItemName
        fontChangeName, dummy_size = self._effective_font(fontItem.change)
        if fontChangeName and fontChangeName != "(Default)":
            convertedFontName = fontChangeName
        self._change_font_name(convertedFontName, self.lblConverted)

    def change_font_size(self, fontItem):
        dummy_fontName, fontItemSize = self._effective_font(fontItem)
        self._change_font_size(fontItemSize, self.lblInput)
        convertedFontSize = fontItemSize
        dummy_fontName, fontChangeSize = self._effective_font(fontItem.change)
        if fontChangeSize and fontChangeSize.isSpecified():
            convertedFontSize = fontChangeSize
        self._change_font_size(convertedFontSize, self.lblConverted)

    def _effective_font(self, fontInfo):
        """Returns font name and size, from the style if possible."""
        if not fontInfo:
            return "", None
        if fontInfo.styleType == FontItem.STYLETYPE_CUSTOM:
            return fontInfo.name, fontInfo.size
        else:
            return getFontOfStyle(fontInfo, self.app.unoObjs)

    def _change_font_name(self, fontName, ctrl):
        """See also lingt.access.writer.textchanges.changeFont().
        :param fontInfo: either a FontItem or a FontChange
        """
        if not fontName:
            fontName = " "
        logger.debug("set %s.FontName %s", ctrl.getModel().Name, fontName)
        ctrl.getModel().setPropertyValue('FontName', fontName)

    def _change_font_size(self, fontSize, ctrl):
        """:param fontInfo: either a FontItem or a FontChange"""
        logger.debug("Font size '%s'", fontSize.getString())
        fontSize.changeCtrlProp(ctrl, always_change=True)


class ButtonNextInput(FontChangeControlHandler,
                      evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, samples, sampleLabels):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, None)
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
        controls = CheckboxShowConverter(self.ctrl_getter, self.app, None)
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


class CheckboxShowConverter(FontChangeControlHandler,
                            evt_handler.ItemEventHandler):
    """Controls to display sample input and converted text."""

    def __init__(self, ctrl_getter, app, next_input_controls=None):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, None)
        evt_handler.ItemEventHandler.__init__(self)
        self.next_input_controls = next_input_controls
        evt_handler.ItemEventHandler.__init__(self)
        self.chkShowConverted = ctrl_getter.get(_dlgdef.CHK_SHOW_CONVERTED)

    def load_values(self):
        #self.chkShowConverted.setState(
        #    userVars.getInt('DisplayConverted'))
        self.chkShowConverted.setState(False)

    def add_listeners(self):
        self.chkShowConverted.addItemListener(self)

    def handle_item_event(self, dummy_src):
        self.next_input_controls.show_sample_again()

    def store_results(self):
        displayConverted = (
            self.chkShowConverted.getState() == 1)
        self.app.userVars.store(
            'DisplayConverted', "%d" % displayConverted)


class FoundFontInfo:
    """Information about the font found.  These values are read-only."""

    def __init__(self, ctrl_getter, dummy_app):
        self.foundFonts = ctrl_getter.get(_dlgdef.FOUND_FONTS)
        self.foundFontSize = ctrl_getter.get(_dlgdef.FOUND_FONT_SIZE)

    def load_values(self):
        self.fill_for_item(FontItem())

    def fill_for_item(self, fontItem):
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


class FontNameHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, style_type_handler):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.style_type_handler = style_type_handler
        self.comboFontName = ctrl_getter.get(_dlgdef.COMBO_FONT_NAME)

    def load_values(self):
        fontNames = styles.getListOfFonts(self.app.unoObjs, addBlank=True)
        dutil.fill_list_ctrl(self.comboFontName, fontNames)

    def add_listeners(self):
        self.comboFontName.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        self.change_control_prop()
        self.set_style_radio()

    def update_change(self, fontChange):
        fontChange.name = self.comboFontName.getText()
        if fontChange.name == "(None)":
            fontChange.name = ""
        else:
            fontChange.styleType = FontItem.STYLETYPE_CUSTOM

    def _fill_for_item_no_change(self, dummy_fontItem):
        self.clear_combo_box()
        self.change_control_prop()

    def _fill_for_item_change(self, fontChange):
        if fontChange.name and fontChange.name != "(None)":
            self.comboFontName.setText(fontChange.name)
        else:
            self.clear_combo_box()
        self.change_control_prop()

    def copy_change(self, change_from, change_to):
        change_from.name = change_to.name

    def clear_combo_box(self):
        self.comboFontName.setText("")

    def change_control_prop(self):
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.change_font_name(self.app.selected_item())

    def set_style_radio(self):
        """Sets the style type radio buttons to Custom Formatting."""
        font_item = self.app.selected_item()
        self.style_type_handler.fill_for_item(font_item)
        # Calling update_change() gets the style name.
        self.style_type_handler.update_change(font_item.change)
        self.app.update_list(self.style_type_handler)


class FontTypeHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, font_name_handler):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
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

    def update_change(self, fontChange):
        fontChange.fontType = dutil.whichSelected(self.radios)
        self.font_name_handler.update_change(fontChange)

    def _fill_for_item_no_change(self, fontItem):
        self.fill(fontItem.fontType)

    def _fill_for_item_change(self, fontChange):
        self.fill(fontChange.fontType)

    def copy_change(self, change_from, change_to):
        change_from.fontType = change_to.fontType

    def fill(self, fontType, *dummy_args):
        dutil.selectRadio(self.radios, fontType)


class FontSizeHandler(FontChangeControlHandler, evt_handler.TextEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.TextEventHandler.__init__(self)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_FONT_SIZE)

    def add_listeners(self):
        self.txtFontSize.addTextListener(self)

    def handle_text_event(self, src):
        FontChangeControlHandler.handle_text_event(self, src)
        self.change_control_prop()

    def update_change(self, fontChange):
        fontChange.size = FontSize(propSuffix=fontChange.getPropSuffix())
        fontChange.size.loadCtrl(self.txtFontSize)

    def fill_for_item(self, fontItem):
        if fontItem.change:
            fontSize = fontItem.change.size
            fontSize.changeCtrlVal(self.txtFontSize)
        else:
            self.txtFontSize.setText("")
        self.change_control_prop()

    def copy_change(self, change_from, change_to):
        change_from.size = copy.copy(change_to.size)

    def change_control_prop(self):
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.change_font_size(self.app.selected_item())


class StyleControls(AggregateControlHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        AggregateControlHandler.__init__(self, ctrl_getter, app, step2Master)
        style_name_handler = StyleNameHandler(
            ctrl_getter, app, step2Master)
        self.style_type_handler = StyleTypeHandler(
            ctrl_getter, app, step2Master, style_name_handler)
        style_name_handler.set_style_type_handler(self.style_type_handler)
        self.controls_objects = (self.style_type_handler, style_name_handler)

    def get_style_type_handler(self):
        return self.style_type_handler


def getFontOfStyle(fontInfo, unoObjs):
    styleFonts = styles.StyleFonts(unoObjs)
    return styleFonts.getFontOfStyle(
        fontInfo.styleType, fontInfo.fontType, fontInfo.styleName)

def readFontOfStyle(fontChange, unoObjs):
    fontChange.fontName, fontChange.fontSize = getFontOfStyle(
        fontChange, unoObjs)

class StyleNameHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        para_list = StyleList(
            FontItem.STYLETYPE_PARA, ctrl_getter.get(_dlgdef.COMBO_PARA_STYLE),
            self.app.unoObjs)
        char_list = StyleList(
            FontItem.STYLETYPE_CHAR, ctrl_getter.get(_dlgdef.COMBO_CHAR_STYLE),
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
        FontChangeControlHandler.handle_item_event(self, src)
        self.style_type_handler.fill_for_item(self.app.selected_item())
        self.selectFontFromStyle()

    def update_change(self, fontChange):
        fontChange.styleName = ""
        fontChange.styleDisplayName = ""
        for stylelist in self.stylelists:
            if stylelist.same_ctrl(self.last_source):
                stylelist.update_change(fontChange)

    def update_change_for_type(self, fontChange, styleType):
        logger.debug(util.funcName())
        fontChange.styleName = ""
        fontChange.styleDisplayName = ""
        if fontChange.styleType == FontItem.STYLETYPE_CUSTOM:
            font_name_handler = FontNameHandler(
                self.ctrl_getter, self.app, self.step2Master,
                self.style_type_handler)
            font_name_handler.update_change(fontChange)
            font_size_handler = FontSizeHandler(
                self.ctrl_getter, self.app, self.step2Master)
            font_size_handler.update_change(fontChange)
            return
        for stylelist in self.stylelists:
            if stylelist.same_type(styleType):
                stylelist.update_change(fontChange)

    def selectFontFromStyle(self):
        """Selects the font based on the style."""
        logger.debug(util.funcName())
        fontItem = self.app.selected_item()
        fontChange = fontItem.change
        if fontChange.styleType == FontItem.STYLETYPE_CUSTOM:
            return
        readFontOfStyle(fontChange, self.app.unoObjs)
        font_name_handler = FontNameHandler(
            self.ctrl_getter, self.app, self.step2Master,
            self.style_type_handler)
        font_name_handler.fill_for_item(fontItem)
        font_size_handler = FontSizeHandler(
            self.ctrl_getter, self.app, self.step2Master)
        font_size_handler.fill_for_item(fontItem)

    def _fill_for_item_no_change(self, fontItem):
        self.clear_combo_boxes()

    def _fill_for_item_change(self, fontChange):
        for stylelist in self.stylelists:
            if stylelist.same_type(fontChange.styleType):
                stylelist.ctrl.setText(fontChange.styleDisplayName)

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
        if self.styleType == FontItem.STYLETYPE_CHAR:
            family = 'CharacterStyles'
        namesList = styles.getListOfStyles(family, self.unoObjs)
        self.styleNames.update(dict(namesList))
        displayNames = tuple([dispName for dispName, dummy_name in namesList])
        dutil.fill_list_ctrl(self.ctrl, displayNames)

    def update_change(self, fontChange):
        fontChange.styleType = self.styleType
        displayName = self.ctrl.getText()
        fontChange.styleDisplayName = displayName
        try:
            fontChange.styleName = self.styleNames[displayName]
        except KeyError:
            logger.warning(
                "%s is not a known %s.", displayName, self.styleType)

    def same_ctrl(self, ctrl):
        return evt_handler.sameName(ctrl, self.ctrl)

    def same_type(self, styleType):
        return styleType == self.styleType


class StyleTypeHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master, style_name_handler):
        FontChangeControlHandler.__init__(self, ctrl_getter, app, step2Master)
        evt_handler.ItemEventHandler.__init__(self)
        self.style_name_handler = style_name_handler
        self.optParaStyle = ctrl_getter.get(_dlgdef.OPT_PARA_STYLE)
        self.optCharStyle = ctrl_getter.get(_dlgdef.OPT_CHAR_STYLE)
        self.optNoStyle = ctrl_getter.get(_dlgdef.OPT_NO_STYLE)
        self.radios = [
            dutil.RadioTuple(self.optNoStyle, FontItem.STYLETYPE_CUSTOM),
            dutil.RadioTuple(self.optParaStyle, FontItem.STYLETYPE_PARA),
            dutil.RadioTuple(self.optCharStyle, FontItem.STYLETYPE_CHAR)]

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        self.style_name_handler.selectFontFromStyle()

    def update_change(self, fontChange):
        fontChange.styleType = dutil.whichSelected(self.radios)
        self.style_name_handler.update_change_for_type(
            fontChange, fontChange.styleType)

    def _fill_for_item_change(self, fontChange):
        self.fill(fontChange.styleType)

    def _fill_for_item_no_change(self, fontItem):
        self.fill(fontItem.styleType)

    def fill(self, styleType, *dummy_args):
        dutil.selectRadio(self.radios, styleType)

    def copy_change(self, change_from, change_to):
        change_from.styleType = change_to.styleType


