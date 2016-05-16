# -*- coding: Latin-1 -*-
#
# This file created July 6 2015 by Jim Kornelsen
#
# 15-Aug-15 JDK  Added constants for checkboxes.
# 25-Aug-15 JDK  Added log_event_handler_exceptions().
# 08-Sep-15 JDK  Set handling_event in finally clause.
# 29-Sep-15 JDK  Set combo box values to empty string by default.
# 12-Dec-15 JDK  Added listbox_items().
# 21-Mar-16 JDK  Changed getControl() to a class to reduce arguments.
# 23-Mar-16 JDK  Moved event handling functions to another module.
# 16-May-16 JDK  Fixed bug: all_ctrl_names() should return strings, not attrs.

"""
Utilities to manage UNO dialogs and controls.

This module exports:
    createDialog()
    ControlGetter()
    whichSelected()
    selectRadio()
    fill_list_ctrl()
    get_selected_index()
    select_index()
    RadioTuple
    set_tristate_checkbox()
    get_tristate_checkbox()
"""
import collections
import logging

from com.sun.star.lang import IllegalArgumentException
from grantjenks.tribool import Tribool

from lingt.app import exceptions
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

# checkbox and radio button values
UNCHECKED = 0
CHECKED = 1
UNSELECTED = UNCHECKED
SELECTED = CHECKED
# Threeway checkbox values are UNCHECKED, CHECKED, and UNSPECIFIED.
UNSPECIFIED = 2

logger = logging.getLogger("lingt.ui.dutil")


def createDialog(uno_objs, definition_class):
    """:param definition_class: class from lingt.utils.dlgdefs"""
    logger.debug("Creating dialog...")
    dlg_getter = DialogGetter(uno_objs, definition_class)
    dlg = None
    try:
        dlg = dlg_getter.create_and_verify()
    except exceptions.DialogError as exc:
        msgbox = MessageBox(uno_objs)
        msgbox.displayExc(exc)
    return dlg

class DialogGetter:
    def __init__(self, uno_objs, definition_class):
        """:param definition_class: class from lingt.utils.dlgdefs"""
        self.uno_objs = uno_objs
        self.definition = definition_class
        self.dlg = None

    def create_and_verify(self):
        """raises: DialogError if dialog could not be created"""
        logger.debug("Creating and verifying dialog...")
        self._createDialog()
        if not self.dlg:
            raise exceptions.DialogError("Error: Could not create dialog.")
        logger.debug("Created dialog.")
        try:
            logger.debug("Verifying names...")
            self.verify_ctrl_names()
            logger.debug("Verified names.")
        finally:
            self.dlg.dispose()
        return self.dlg

    def _createDialog(self):
        logger.debug(util.funName())
        dlgprov = self.uno_objs.smgr.createInstanceWithArgumentsAndContext(
            "com.sun.star.awt.DialogProvider",
            (self.uno_objs.document,), self.uno_objs.ctx)
        dlg_string = (
            "vnd.sun.star.script:LingToolsBasic." + self.dlg_name() +
            "?location=application")
        logger.debug(dlg_string)
        try:
            self.dlg = dlgprov.createDialog(dlg_string)
        except IllegalArgumentException:
            pass
        return self.dlg

    def dlg_name(self):
        return self.definition.__name__

    def verify_ctrl_names(self):
        ctrl_getter = ControlGetter(self.dlg)
        for ctrl_name in self.all_ctrl_names():
            ctrl_getter.verify(ctrl_name)

    def all_ctrl_names(self):
        class_dict = self.definition.__dict__
        return [
            class_dict[attr] for attr in class_dict
            if not attr.startswith('__')]


class ControlGetter:
    def __init__(self, dlg):
        self.dlg = dlg

    def get_and_verify(self, ctrl_name):
        self.verify(ctrl_name)
        return self.get(ctrl_name)

    def verify(self, ctrl_name):
        """raises: DialogError if control is not found"""
        ctrl = self.get(ctrl_name)
        if not ctrl:
            raise exceptions.DialogError(
                "Error showing dialog: No %s control.", ctrl_name)

    def get(self, ctrl_name):
        return self.dlg.getControl(ctrl_name)


RadioTuple = collections.namedtuple('RadioTuple', ['ctrl', 'key'])

def whichSelected(radioList):
    """Return the selected radio button."""
    for radio in radioList:
        if radio.ctrl.getState() == 1:  # checked
            return radio.key
    return radioList[0].key

def selectRadio(radioList, whichKey):
    """Select the specified radio button."""
    for radio in radioList:
        if radio.key == whichKey:
            radio.ctrl.setState(1)
            return
    return radioList[0].ctrl.setState(1)


def fill_list_ctrl(listCtrl, values, selectedValue=""):
    """
    Fill a control with the given values.

    :param listCtrl: the UNO control, either a listbox or combobox
    :param values: values to fill the listbox, either list or tuple
    :param selectedValue: select this value when filled

    The UNO methods selectItem(), selectItemPos() and setText() will call
    any listening event handlers before this function is finished,
    so calling this function from within an event handler for the same
    control can cause infinite recursion.
    (Actually it's not infinite, because UNO seems to limit the
    maximum recursion to a depth of about 20).
    """
    logger.debug("%s selectedValue=%s", util.funcName('begin'), selectedValue)
    listCtrl.removeItems(0, listCtrl.getItemCount())
    listCtrl.addItems(tuple(values), 0)
    if listCtrl.supportsService("com.sun.star.awt.UnoControlListBox"):
        if selectedValue and selectedValue in values:
            listCtrl.selectItem(selectedValue, True)
        else:
            listCtrl.selectItemPos(0, True)
    elif listCtrl.supportsService("com.sun.star.awt.UnoControlComboBox"):
        if selectedValue and selectedValue in values:
            listCtrl.setText(selectedValue)
        else:
            listCtrl.setText("")
    logger.debug(util.funcName('end'))


def get_selected_index(listCtrl, itemDescription="an item"):
    """
    :param listCtrl: the UNO listbox control
    :param itemDescription: description of the item for error messages
    """
    itemPos = listCtrl.getSelectedItemPos()
    if itemPos is None or itemPos < 0:
        if listCtrl.getItemCount() == 1:
            itemPos = 0
        else:
            logger.debug("No item selected.")
            raise exceptions.ChoiceProblem(
                "Please select %s in the list." % itemDescription)
    logger.debug("Item at index %d is selected.", itemPos)
    return itemPos

def select_index(listCtrl, itemPos):
    """
    :param listCtrl: the UNO listbox control
    """
    if itemPos is None or itemPos == "":
        logger.warning("Could not select index %r", itemPos)
        return
    maxItemPos = listCtrl.getItemCount() - 1
    if itemPos > maxItemPos:
        logger.warning("Using %d instead of %d", maxItemPos, itemPos)
        itemPos = maxItemPos
    if itemPos >= 0:
        logger.debug("Selecting index %d", itemPos)
        listCtrl.selectItemPos(itemPos, True)
    else:
        logger.warning("Could not select index %r", itemPos)


def listbox_items(listboxCtrl):
    """This remedies problems with XListBox.getItems() for 0-length lists.
    XListBox.getItems() returns an empty byte string if the list is empty,
    not a list.  The object returned is actually a
    ByteSequence type; the class is defined in uno.py.
    Iterating over it always calls the value's __iter__() member.
    Strings in python 2 do not have this, so this raises an exception.
    Strings in python 3 do have this, and it actually works fine for
    python 3 because the 0-length string will simply not loop,
    which is what should happen for a 0-length list.
    But for python 2, which includes the latest version of Apache OpenOffice
    to date, this is a problem.

    :returns: a list of strings
    """
    items = listboxCtrl.getItems()
    if len(items) == 0:
        return []
    return items


def set_tristate_checkbox(chkCtrl, triboolVal):
    """
    :param chkCtrl: the dialog control to set
    :param triboolVal: the value
    """
    logger.debug(str(triboolVal))
    if triboolVal is Tribool('Indeterminate'):
        chkCtrl.setState(UNSPECIFIED)
    elif triboolVal is Tribool('True'):
        chkCtrl.setState(CHECKED)
    else:
        chkCtrl.setState(UNCHECKED)

def get_tristate_checkbox(chkCtrl):
    """Returns the Tribool value of the chkCtrl state."""
    if chkCtrl.getState() == UNSPECIFIED:
        return Tribool(None)
    else:
        return Tribool(bool(chkCtrl.getState()))

