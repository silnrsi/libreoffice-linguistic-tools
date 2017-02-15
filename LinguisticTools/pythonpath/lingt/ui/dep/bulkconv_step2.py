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
# 16-Jul-16 JDK  Instead of fonts, use StyleItems that depend on scope type.
# 29-Jul-16 JDK  RemoveCustomFormatting is checked per item, not globally.

"""
Bulk Conversion dialog step 2.

This module exports:
    FormStep2
"""
import logging

from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import StyleChange
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
            VerifyHandler(ctrl_getter, app)
            ])

    def start_working(self):
        for event_handler in self.event_handlers:
            event_handler.start_working()

    def store_results(self):
        """Store settings in user vars."""
        logger.debug(util.funcName('begin'))
        styleChanges = self.app.getStyleChanges()
        self.app.userVars.store('StyleChangesCount', str(len(styleChanges)))
        varNum = 0
        for styleChange in styleChanges:
            styleChange.setVarNum(varNum)
            varNum += 1
            styleChange.userVars = self.app.userVars
            styleChange.storeUserVars()

        MAX_CLEAN = 1000  # should be more than enough
        for varNum in range(len(styleChanges), MAX_CLEAN):
            styleChange = StyleChange(None, self.app.userVars, varNum)
            foundSomething = styleChange.cleanupUserVars()
            if not foundSomething:
                break
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
        self.listStylesUsed = ListStylesUsed(ctrl_getter, app, self)
        converter_controls = _itemctrls.ConverterControls(
            ctrl_getter, app, self)
        style_controls = _itemctrls.StyleControls(ctrl_getter, app, self)
        font_controls = _itemctrls.FontControls(
            ctrl_getter, app, self, style_controls.get_style_type_handler())
        # controls that store StyleItem data
        self.data_controls = [
            converter_controls, font_controls, style_controls]

    def get_event_handlers(self):
        return [self.listStylesUsed] + self.data_controls

    def read_change(self):
        """Reads the form and returns a StyleChange object."""
        styleChange = StyleChange(None, self.app.userVars)
        for styleitem_controls in self.data_controls:
            styleitem_controls.update_change(styleChange)
        return styleChange

    def copy_change_attrs(self, change_from, change_to):
        """Set attributes of change_to based on change_from."""
        for styleitem_controls in self.data_controls:
            styleitem_controls.copy_change(change_from, change_to)

    def refresh_list_and_fill(self):
        self.listStylesUsed.refresh_and_fill()

    def refresh_list(self):
        self.listStylesUsed.refresh_selected()

    def fill_for_item(self, styleItem):
        """Fill form according to specified styleItem."""
        logger.debug(util.funcName('begin'))
        for styleitem_controls in self.data_controls:
            styleitem_controls.fill_for_item(styleItem)
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
        self.btnReset.setActionCommand('ResetItem')
        self.btnCopy.setActionCommand('CopyItem')
        self.btnPaste.setActionCommand('PasteItem')
        for ctrl in (self.btnReset, self.btnCopy, self.btnPaste):
            ctrl.addActionListener(self)

    def handle_action_event(self, action_command):
        if action_command == 'ResetItem':
            self.resetItem()
        elif action_command == 'CopyItem':
            self.copyItem()
        elif action_command == 'PasteItem':
            self.pasteItem()
        else:
            evt_handler.raise_unknown_action(action_command)

    def resetItem(self):
        item = self.app.selected_item()
        if not item:
            return
        item.change = None
        self.step2Master.refresh_list_and_fill()

    def copyItem(self):
        logger.debug(util.funcName())
        self.copiedSettings = self.step2Master.read_change()

    def pasteItem(self):
        logger.debug(util.funcName())
        if self.copiedSettings is None:
            self.app.msgbox.display("First press Copy.")
            return
        item = self.app.selected_item()
        if not item:
            return
        item.create_change(self.app.userVars)
        self.step2Master.copy_change_attrs(
            self.copiedSettings, item.change)
        self.step2Master.refresh_list_and_fill()


class ListStylesUsed(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ItemEventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = step2Master
        self.list_ctrl = ctrl_getter.get(_dlgdef.LIST_STYLES_USED)

    def add_listeners(self):
        self.list_ctrl.addItemListener(self)

    def handle_item_event(self, src):
        self._read_selected_item()
        self.fill_form_for_selected_item()
        self.refresh()

    def _read_selected_item(self):
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
        self.fill_form_for_selected_item()

    def refresh(self):
        """Redraw the list and select the same item."""
        dutil.fill_list_ctrl(
            self.list_ctrl,
            [str(item) for item in self.app.styleItemList])
        if len(self.app.styleItemList) > 0:
            if self._get_app_index() == -1:
                self._set_app_index(0)
            dutil.select_index(self.list_ctrl, self._get_app_index())

    def refresh_selected(self):
        index = self._get_app_index()
        if index == -1:
            self.refresh()
            return
        item = self.app.selected_item()
        self.list_ctrl.addItem(str(item), index)
        self.list_ctrl.removeItems(index + 1, 1)

    def fill_form_for_selected_item(self):
        """Fills data controls based on the item selected in the list."""
        logger.debug(util.funcName('begin'))
        item = self.app.selected_item()
        if not item:
            logger.debug("No styleItem selected.")
            return
        self.step2Master.fill_for_item(item)

    def _set_app_index(self, index):
        self.app.styleItemList.selected_index = index

    def _get_app_index(self):
        return self.app.styleItemList.selected_index


class VerifyHandler(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        evt_handler.ItemEventHandler.__init__(self)
        self.app = app
        self.chkVerify = ctrl_getter.get(_dlgdef.CHK_VERIFY)

    def load_values(self):
        self.chkVerify.setState(self.app.userVars.getInt('AskEachChange'))
        self.get_results()

    def handle_item_event(self, dummy_src):
        self.store_results()

    def get_results(self):
        self.app.askEach = bool(self.chkVerify.getState())

    def store_results(self):
        self.get_results()
        self.app.userVars.store(
            'AskEachChange', "%d" % self.app.askEach)
