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
# 16-May-16 JDK  Separate class for sample labels because ctrl props change.
# 28-May-16 JDK  Added Step2Master.
# 31-May-16 JDK  Standardize names of filling methods.
# 13-Jun-16 JDK  Aggregate related controls so that they can call each other.
# 16-Jun-16 JDK  Moved controls classes to their own module.
# 24-Jun-16 JDK  FontItemList holds FontItemGroup instead of FontItem.
# 13-Jul-16 JDK  Remember state of group check boxes.

"""
Bulk Conversion dialog step 2.

This module exports:
    FormStep2
"""
import logging

from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import FontChange
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.ui.dep import bulkconv_step2items as _itemctrls
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgbulkconv_step2")


class FormStep2:
    """Create control classes and load values."""

    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = Step2Master(ctrl_getter, app)
        self.event_handlers = []
        self.event_handlers.extend(self.step2Master.get_event_handlers())
        self.event_handlers.extend([
            ClipboardButtons(ctrl_getter, app, self.step2Master),
            JoinCheckboxes(ctrl_getter, app, self.step2Master),
            VerifyHandler(ctrl_getter, app)
            ])

    def start_working(self):
        for event_handler in self.event_handlers:
            event_handler.start_working()
        found_font_info = _itemctrls.FoundFontInfo(self.ctrl_getter, self.app)
        found_font_info.load_values()

    def store_results(self):
        """Store settings in user vars."""
        logger.debug(util.funcName('begin'))
        fontChanges = self.app.getFontChanges()
        self.app.userVars.store('FontChangesCount', str(len(fontChanges)))
        varNum = 0
        for fontChange in fontChanges:
            fontChange.setVarNum(varNum)
            varNum += 1
            fontChange.userVars = self.app.userVars
            fontChange.storeUserVars()

        MAX_CLEAN = 1000  # should be more than enough
        for varNum in range(len(fontChanges), MAX_CLEAN):
            fontChange = FontChange(None, self.app.userVars, varNum)
            foundSomething = fontChange.cleanupUserVars()
            if not foundSomething:
                break

        checkboxShowConverter = _itemctrls.CheckboxShowConverter(
            self.ctrl_getter, self.app)
        checkboxShowConverter.store_results()
        joinCheckboxes = JoinCheckboxes(
            self.ctrl_getter, self.app, self.step2Master)
        joinCheckboxes.store_results()
        verifyHandler = VerifyHandler(self.ctrl_getter, self.app)
        verifyHandler.store_results()
        logger.debug(util.funcName('end'))

    def refresh_list_and_fill(self):
        self.step2Master.refresh_list_and_fill()


class Step2Master:
    """Controls that need to be called by events.  The controls objects are
    maintained across events.
    """
    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.listFontsUsed = ListFontsUsed(ctrl_getter, app, self)
        converter_controls = _itemctrls.ConverterControls(
            ctrl_getter, app, self)
        style_controls = _itemctrls.StyleControls(ctrl_getter, app, self)
        font_controls = _itemctrls.FontControls(
            ctrl_getter, app, self, style_controls.get_style_type_handler())
        # controls that store FontItem data
        self.data_controls = [
            converter_controls, font_controls, style_controls]

    def get_event_handlers(self):
        return [self.listFontsUsed] + self.data_controls

    def read_change(self):
        """Reads the form and returns a FontChange object."""
        fontChange = FontChange(None, self.app.userVars)
        for fontitem_controls in self.data_controls:
            fontitem_controls.update_change(fontChange)
        return fontChange

    def copy_change_attrs(self, change_from, change_to):
        """Set attributes of change_to based on change_from."""
        for fontitem_controls in self.data_controls:
            fontitem_controls.copy_change(change_from, change_to)

    def refresh_list_and_fill(self):
        self.listFontsUsed.refresh_and_fill()

    def refresh_list(self):
        self.listFontsUsed.refresh_selected()

    def fill_for_group(self, fontItemGroup):
        """Fill form according to specified font settings."""
        logger.debug(util.funcName('begin'))
        foundFontInfo = _itemctrls.FoundFontInfo(self.ctrl_getter, self.app)
        for fontitem_controls in self.data_controls + [foundFontInfo]:
            fontitem_controls.fill_for_group(fontItemGroup)
        logger.debug(util.funcName('end'))


class ClipboardButtons(evt_handler.ActionEventHandler):
    """This does not actually use the system clipboard, but it implements
    copy/paste functionality.
    """
    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ActionEventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = step2Master
        self.btnReset = ctrl_getter.get(_dlgdef.BTN_RESET)
        self.btnCopy = ctrl_getter.get(_dlgdef.BTN_COPY)
        self.btnPaste = ctrl_getter.get(_dlgdef.BTN_PASTE)
        self.copiedSettings = None

    def add_listeners(self):
        self.btnReset.setActionCommand('ResetFont')
        self.btnCopy.setActionCommand('CopyFont')
        self.btnPaste.setActionCommand('PasteFont')
        for ctrl in (self.btnReset, self.btnCopy, self.btnPaste):
            ctrl.addActionListener(self)

    def handle_action_event(self, action_command):
        if action_command == 'ResetFont':
            self.resetFont()
        elif action_command == 'CopyFont':
            self.copyFont()
        elif action_command == 'PasteFont':
            self.pasteFont()
        else:
            evt_handler.raise_unknown_action(action_command)

    def resetFont(self):
        group = self.app.selected_group()
        if not group:
            return
        for item in group.items:
            item.change = None
        self.step2Master.refresh_list_and_fill()

    def copyFont(self):
        logger.debug(util.funcName())
        self.copiedSettings = self.step2Master.read_change()

    def pasteFont(self):
        logger.debug(util.funcName())
        if self.copiedSettings is None:
            self.app.msgbox.display("First copy font settings.")
            return
        group = self.app.selected_group()
        if not group:
            return
        for item in group.items:
            item.create_change(self.app.userVars)
            self.step2Master.copy_change_attrs(
                self.copiedSettings, item.change)
        self.step2Master.refresh_list_and_fill()


class ListFontsUsed(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ItemEventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = step2Master
        self.list_ctrl = ctrl_getter.get(_dlgdef.LIST_FONTS_USED)

    def add_listeners(self):
        self.list_ctrl.addItemListener(self)

    def handle_item_event(self, src):
        self._read_selected_group()
        self.fill_form_for_selected_group()
        self.refresh()

    def _read_selected_group(self):
        """Sets the app's selected_index."""
        try:
            self._set_app_index(
                dutil.get_selected_index(self.list_ctrl, "a file"))
        except exceptions.ChoiceProblem as exc:
            self.app.msgbox.displayExc(exc)
            self._set_app_index(-1)
            return None

    def refresh_and_fill(self):
        self.refresh()
        self.fill_form_for_selected_group()

    def refresh(self):
        """Redraw the list and select the same item."""
        dutil.fill_list_ctrl(
            self.list_ctrl,
            [str(group.effective_item) for group in self.app.fontItemList])
        if self.app.fontItemList.groups:
            if self._get_app_index() == -1:
                self._set_app_index(0)
            dutil.select_index(
                self.list_ctrl, self._get_app_index())

    def refresh_selected(self):
        index = self._get_app_index()
        if index == -1:
            self.refresh()
            return
        effective_item = self.app.selected_group().effective_item
        self.list_ctrl.addItem(str(effective_item), index)
        self.list_ctrl.removeItems(index + 1, 1)

    def fill_form_for_selected_group(self):
        """Fills data controls based on the item selected in the list."""
        logger.debug(util.funcName('begin'))
        group = self.app.selected_group()
        if not group:
            logger.debug("No fontItem selected.")
            return
        self.step2Master.fill_for_group(group)

    def _set_app_index(self, index):
        self.app.fontItemList.selected_index = index

    def _get_app_index(self):
        return self.app.fontItemList.selected_index


class JoinCheckboxes(evt_handler.ItemEventHandler):
    """Checkboxes that join or split the list."""

    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ItemEventHandler.__init__(self)
        self.app = app
        self.step2Master = step2Master
        self.chkJoinFontTypes = ctrl_getter.get(_dlgdef.CHK_JOIN_FONT_TYPES)
        self.chkJoinSizes = ctrl_getter.get(_dlgdef.CHK_JOIN_SIZE)
        self.chkJoinStyles = ctrl_getter.get(_dlgdef.CHK_JOIN_STYLES)

    def load_values(self):
        userVars = self.app.userVars
        fontItemList = self.app.fontItemList
        for attr, varname, ctrl in (
                ('groupFontTypes', 'JoinFontTypes', self.chkJoinFontTypes),
                ('groupSizes', 'JoinSizes', self.chkJoinSizes),
                ('groupStyles', 'JoinStyles', self.chkJoinStyles),
            ):
            if not userVars.isEmpty(varname):
                state = bool(userVars.getInt(varname))
                setattr(fontItemList, attr, state)
                ctrl.setState(state)

    def add_listeners(self):
        for ctrl in (
                self.chkJoinFontTypes, self.chkJoinSizes, self.chkJoinStyles):
            ctrl.addItemListener(self)

    def handle_item_event(self, src):
        self.read()
        self.step2Master.refresh_list_and_fill()

    def read(self):
        fontItemList = self.app.fontItemList
        fontItemList.groupFontTypes = bool(self.chkJoinFontTypes.getState())
        fontItemList.groupSizes = bool(self.chkJoinSizes.getState())
        fontItemList.groupStyles = bool(self.chkJoinStyles.getState())

    def store_results(self):
        fontItemList = self.app.fontItemList
        for varname, val in (
                ('JoinFontTypes', fontItemList.groupFontTypes),
                ('JoinSizes', fontItemList.groupSizes),
                ('JoinStyles', fontItemList.groupStyles),
            ):
            self.app.userVars.store(varname, "%d" % val)


class VerifyHandler(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        self.chkVerify = ctrl_getter.get(_dlgdef.CHK_VERIFY)
        self.app = app

    def load_values(self):
        self.chkVerify.setState(self.app.userVars.getInt('AskEachChange'))

    def store_results(self):
        self.app.askEach = (
            self.chkVerify.getState() == 1)
        self.app.userVars.store(
            'AskEachChange', "%d" % self.app.askEach)


