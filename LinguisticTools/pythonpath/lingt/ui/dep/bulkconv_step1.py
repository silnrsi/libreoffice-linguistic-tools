# -*- coding: Latin-1 -*-
#
# This file created December 24 2015 by Jim Kornelsen

"""
Bulk Conversion dialog step 1.

This module exports:
    Step1Controls()
    Step1Form()
"""
import logging
import os

import uno

from lingt.app.fileitemlist import FileItemList, BulkFileItem
from lingt.app import exceptions
from lingt.app.bulkconv_structs import FontItem, FontChange
from lingt.ui import dutil
from lingt.ui import filepicker
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgbulkconv_step1")

class Step1Controls:
    """Store dialog controls for page step 1."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.listboxFiles = dutil.getControl(dlg, 'listFiles')
        self.txtOutputTo = dutil.getControl(dlg, 'txFolderOutputTo')
        btnAddCurrent = dutil.getControl(dlg, 'btnAddCurrentDoc')
        btnFileAdd = dutil.getControl(dlg, 'btnAdd')
        btnFileRemove = dutil.getControl(dlg, 'btnRemove')
        btnOutputTo = dutil.getControl(dlg, 'btnOutputTo')
        btnScan = dutil.getControl(dlg, 'btnScan')
        btnCancel = dutil.getControl(dlg, 'btnCancel')
        logger.debug("Got step 1 controls.")

        btnAddCurrent.setActionCommand('AddCurrentDoc')
        btnFileAdd.setActionCommand('FileAdd')
        btnFileRemove.setActionCommand('FileRemove')
        btnOutputTo.setActionCommand('ChooseFolder')
        btnScan.setActionCommand('ScanFiles')
        btnCancel.setActionCommand('Cancel')
        for ctrl in (
                btnFileAdd, btnAddCurrent, btnFileRemove, btnOutputTo,
                btnScan, btnCancel):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars, fileItemStrings):
        logger.debug(util.funcName('begin'))
        self.listboxFiles.addItems(tuple(fileItemStrings), 0)
        self.txtOutputTo.setText(userVars.get('OutputFolder'))


class Step1Form:
    """Handle items and data for page step 1."""

    def __init__(self, unoObjs, stepCtrls, userVars, msgbox, app, gotoStep2):
        self.unoObjs = unoObjs
        self.stepCtrls = stepCtrls
        self.userVars = userVars
        self.msgbox = msgbox
        self.app = app
        self.gotoStep2 = gotoStep2

        self.fileItems = FileItemList(BulkFileItem, self.userVars)
        self.outdir = ""

    def loadData(self):
        self.fileItems.loadUserVars()
        self.stepCtrls.loadValues(
            self.userVars, self.fileItems.getItemTextList())

    def addFile(self):
        logger.debug(util.funcName())
        filepath = filepicker.showFilePicker(self.unoObjs)
        if filepath:
            self._addFile(filepath)

    def addCurrentDoc(self):
        logger.debug(util.funcName())
        url = self.unoObjs.document.getURL()
        if not url:
            self.msgbox.display("Please save the current document first.")
            return
        syspath = uno.fileUrlToSystemPath(url)
        self._addFile(syspath)

    def _addFile(self, filepath):
        newItem = BulkFileItem(self.userVars)
        newItem.filepath = filepath
        logger.debug("Adding item")
        try:
            self.fileItems.addItem(newItem)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        logger.debug("Successfully added.")
        dutil.fill_list_ctrl(
            listCtrl=self.stepCtrls.listboxFiles,
            values=self.fileItems.getItemTextList(),
            selectedValue=str(newItem))
        if not self.stepCtrls.txtOutputTo.getText().strip():
            self.stepCtrls.txtOutputTo.setText(os.path.dirname(filepath))

    def removeFile(self):
        logger.debug(util.funcName())
        try:
            itemPos = dutil.get_selected_index(
                self.stepCtrls.listboxFiles, "a file")
            self.fileItems.deleteItem(itemPos)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        self.stepCtrls.listboxFiles.removeItems(itemPos, 1)

        ## Select the next item

        if self.stepCtrls.listboxFiles.getItemCount() > 0:
            dutil.select_index(self.stepCtrls.listboxFiles, itemPos)
        logger.debug("FileRemove end")

    def showFolderPicker(self):
        logger.debug(util.funcName('begin'))
        folderpath = filepicker.showFolderPicker(
            self.unoObjs, self.stepCtrls.txtOutputTo.getText().strip())
        logger.debug(repr(folderpath))
        if folderpath == "":
            logger.debug("No folderpath specified.")
            return
        self.stepCtrls.txtOutputTo.setText(folderpath)

    def scanFiles(self, step2Form):
        logger.debug(util.funcName('begin'))
        self.getResults()
        if not self.outdir:
            self.msgbox.display("Please select an output folder.")
            return
        if len(self.fileItems) == 0:
            self.msgbox.display("Please add files to scan.")
            return
        try:
            self.app.scanFiles(self.fileItems, self.outdir)
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)
            return
        for varNum in range(0, self.userVars.getInt('FontChangesCount')):
            loaded_item = FontItem()
            fontChange = FontChange(loaded_item, self.userVars, varNum)
            fontChange.loadUserVars()
            for fontItem in self.app.fontItemList:
                if (fontItem.name == loaded_item.name
                        and fontItem.styleName == loaded_item.styleName):
                    logger.debug("found match for %r", fontChange)
                    fontItem.change = fontChange
                    fontChange.fontItem = fontItem
                    break
            else:
                logger.debug("did not find match for %r", fontChange)
        self.gotoStep2()
        step2Form.updateFontsList()
        step2Form.fill_for_selected_font()
        logger.debug(util.funcName('end'))

    def getResults(self):
        logger.debug(util.funcName())
        self.fileItems.storeUserVars()
        self.outdir = self.stepCtrls.txtOutputTo.getText()
        self.userVars.store('OutputFolder', self.outdir)


