# -*- coding: Latin-1 -*-
#
# This file created December 24 2015 by Jim Kornelsen
#
# 28-Apr-16 JDK  Organize classes by controls.
# 15-Jul-16 JDK  Instead of fonts, use StyleItems that depend on scope type.

"""
Bulk Conversion dialog step 1.

This module exports:
    FormStep1
"""
import logging
import os

import uno

from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import FontItem, FontChange, ScopeType
from lingt.app.data.fileitemlist import FileItemList, BulkFileItem
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common import filepicker
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgbulkconv_step1")


class FormStep1:
    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app

        self.outputTo = OutputTo(ctrl_getter, app)
        self.filesList = FilesList(ctrl_getter, app, self.outputTo)
        self.filesListButtons = FilesListButtons(
            ctrl_getter, app, self.filesList)
        self.scopeTypeRadios = ScopeTypeRadios(ctrl_getter, app)

        self.event_handlers = [
            self.filesListButtons, self.outputTo, self.scopeTypeRadios]
        self.data_controls = [
            self.filesList, self.outputTo, self.scopeTypeRadios]

    def start_working(self):
        for event_handler in self.event_handlers:
            event_handler.start_working()
        self.filesList.load_values()

    def store_results(self):
        for data_controls_obj in self.data_controls:
            data_controls_obj.store_results()

    def scanFiles(self):
        logger.debug(util.funcName('begin'))
        self.store_results()
        try:
            self.verify_results()
            self.app.scanFiles(
                self.filesList.fileItems, self.outputTo.outdir,
                self.scopeTypeRadios.whichScope)
            self.load_changes()
        except exceptions.MessageError as exc:
            self.app.msgbox.displayExc(exc)
            raise exc
        logger.debug(util.funcName('end'))

    def verify_results(self):
        if not self.outputTo.outdir:
            raise exceptions.ChoiceProblem("Please select an output folder.")
        if len(self.filesList.fileItems) == 0:
            raise exceptions.ChoiceProblem("Please add files to scan.")

    def load_changes(self):
        """Load stored FontChange data from any previous scans."""
        logger.debug(util.funcName('begin'))
        for varNum in range(0, self.app.userVars.getInt('FontChangesCount')):
            loaded_item = FontItem()
            fontChange = FontChange(loaded_item, self.app.userVars, varNum)
            fontChange.loadUserVars()
            for fontItem in self.app.fontItemList.all_items():
                if (fontItem.name == loaded_item.name
                        and fontItem.styleName == loaded_item.styleName):
                    logger.debug("found match for %r", fontChange)
                    fontItem.change = fontChange
                    fontChange.fontItem = fontItem
                    break
            else:
                logger.debug("did not find match for %r", fontChange)
        logger.debug(util.funcName('end'))


class FilesListButtons(evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, filesList):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.filesList = filesList

    def add_listeners(self):
        btnAddCurrent = self.ctrl_getter.get(_dlgdef.BTN_ADD_CURRENT_DOC)
        btnAddCurrent.setActionCommand('AddCurrentDoc')
        btnFileAdd = self.ctrl_getter.get(_dlgdef.BTN_ADD)
        btnFileAdd.setActionCommand('FileAdd')
        btnFileRemove = self.ctrl_getter.get(_dlgdef.BTN_REMOVE)
        btnFileRemove.setActionCommand('FileRemove')
        for ctrl in (btnFileAdd, btnAddCurrent, btnFileRemove):
            ctrl.addActionListener(self)

    def handle_action_event(self, action_command):
        if action_command == "AddCurrentDoc":
            self.addCurrentDoc()
        elif action_command == "FileAdd":
            self.addFile()
        elif action_command == "FileRemove":
            self.removeFile()

    def addFile(self):
        logger.debug(util.funcName())
        filepath = filepicker.showFilePicker(self.app.unoObjs)
        if filepath:
            self.filesList.addFile(filepath)

    def addCurrentDoc(self):
        logger.debug(util.funcName())
        url = self.app.unoObjs.document.getURL()
        if not url:
            self.app.msgbox.display("Please save the current document first.")
            return
        syspath = uno.fileUrlToSystemPath(url)
        self.filesList.addFile(syspath)

    def removeFile(self):
        self.filesList.removeFile()


class FilesList(evt_handler.DataControls):
    def __init__(self, ctrl_getter, app, outputTo):
        evt_handler.DataControls.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.outputTo = outputTo
        self.listboxFiles = ctrl_getter.get(_dlgdef.LIST_FILES)
        self.fileItems = FileItemList(BulkFileItem, self.app.userVars)

    def load_values(self):
        logger.debug(util.funcName())
        self.fileItems.loadUserVars()
        fileItemStrings = self.fileItems.getItemTextList()
        self.listboxFiles.addItems(tuple(fileItemStrings), 0)

    def store_results(self):
        self.fileItems.storeUserVars()

    def addFile(self, filepath):
        newItem = BulkFileItem(self.app.userVars)
        newItem.filepath = filepath
        logger.debug("Adding item")
        try:
            self.fileItems.addItem(newItem)
        except exceptions.ChoiceProblem as exc:
            self.app.msgbox.displayExc(exc)
            return
        logger.debug("Successfully added.")
        dutil.fill_list_ctrl(
            listCtrl=self.listboxFiles,
            values=self.fileItems.getItemTextList(),
            selectedValue=str(newItem))
        if not self.outputTo.read():
            self.outputTo.fill(os.path.dirname(filepath))

    def removeFile(self):
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(
                self.listboxFiles, "a file")
            self.fileItems.deleteItem(itemPos)
        except exceptions.ChoiceProblem as exc:
            self.app.msgbox.displayExc(exc)
            return
        self.listboxFiles.removeItems(itemPos, 1)

        ## Select the next item

        if self.listboxFiles.getItemCount() > 0:
            dutil.select_index(self.listboxFiles, itemPos)
        logger.debug(util.funcName('end'))


class OutputTo(evt_handler.ActionEventHandler):
    """Manage the controls for the folder to output to."""

    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.txtOutputTo = ctrl_getter.get(_dlgdef.TX_FOLDER_OUTPUT_TO)
        self.outdir = ""

    def add_listeners(self):
        btnOutputTo = self.ctrl_getter.get(_dlgdef.BTN_OUTPUT_TO)
        btnOutputTo.setActionCommand('ChooseFolder')
        btnOutputTo.addActionListener(self)

    def handle_action_event(self, dummy_action_command):
        self.showFolderPicker()

    def showFolderPicker(self):
        logger.debug(util.funcName('begin'))
        folderpath = filepicker.showFolderPicker(self.app.unoObjs, self.read())
        logger.debug(repr(folderpath))
        if folderpath == "":
            logger.debug("No folderpath specified.")
            return
        self.fill(folderpath)

    def load_values(self):
        self.fill(self.app.userVars.get('OutputFolder'))

    def store_results(self):
        self.app.userVars.store('OutputFolder', self.read())

    def fill(self, new_val, *dummy_args):
        self.outdir = new_val
        self.txtOutputTo.setText(self.outdir)

    def read(self):
        self.outdir = self.txtOutputTo.getText().strip()
        return self.outdir


class ScopeTypeRadios(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        evt_handler.ItemEventHandler.__init__(self)
        self.radios = [
            dutil.RadioTuple(
                ctrl_getter.get(_dlgdef.OPT_SCOPE_WHOLE_DOC),
                ScopeType.FONT_WITH_STYLE),
            dutil.RadioTuple(
                ctrl_getter.get(_dlgdef.OPT_SCOPE_FONT_INCLUDING_STYLE),
                ScopeType.FONT_WITH_STYLE),
            dutil.RadioTuple(
                ctrl_getter.get(_dlgdef.OPT_SCOPE_FONT_EXCLUDING_STYLE),
                ScopeType.FONT_WITH_STYLE),
            dutil.RadioTuple(
                ctrl_getter.get(_dlgdef.OPT_SCOPE_PARA_STYLE),
                ScopeType.FONT_WITH_STYLE),
            dutil.RadioTuple(
                ctrl_getter.get(_dlgdef.OPT_SCOPE_CHAR_STYLE),
                ScopeType.FONT_WITH_STYLE)]
        self.whichScope = ScopeType.FONT_WITH_STYLE

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        self.whichScope = dutil.whichSelected(self.radios)

    def load_values(self):
        userVars = self.app.userVars
        varname = 'ScopeType'
        if not userVars.isEmpty(varname):
            self.whichScope = userVars.getInt(varname)
        dutil.selectRadio(self.radios, self.whichScope)

    def store_results(self):
        self.app.userVars.store('ScopeType', self.whichScope)

