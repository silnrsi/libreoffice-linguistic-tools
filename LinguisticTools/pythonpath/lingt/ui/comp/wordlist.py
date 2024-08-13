"""
Dialog to read from data files and create a word list in Calc.

This module exports:
    showDlg()     - called directly from the menu
    DlgWordList() - called from DlgScriptPractice
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener

from lingt.access.writer import uservars
from lingt.access.xml.interlin_reader import InterlinReader
from lingt.access.xml.phon_reader import PhonReader
from lingt.app import exceptions
from lingt.app.data.fileitemlist import FileItemList, WordListFileItem
from lingt.app.data.wordlist_structs import ColumnOrder
from lingt.app.svc.spellingchecks import DEFAULT_NORM_FORM
from lingt.app.svc.wordlist import WordList
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgWordList as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.dep.wordlistfile import DlgWordListFile
from lingt.utils import letters
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgWordList")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgWordList(unoObjs)
    dlg.showDlg()

class DlgWordList:
    """Main class for this dialog."""

    def __init__(self, unoObjs, newUserVarPrefix=None):
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)  # calls theLocale.loadUnoObjs()
        userVarPrefix = uservars.Prefix.WORD_LIST
        if newUserVarPrefix:
            userVarPrefix = newUserVarPrefix
        uservars.SettingsDocPreparer(userVarPrefix, unoObjs).prepare()
        self.userVars = uservars.UserVars(
            userVarPrefix, unoObjs.document, logger)
        self.fileItems = FileItemList(WordListFileItem, self.userVars)
        self.punctToRemove = ""
        self.normForm = DEFAULT_NORM_FORM
        self.columnOrder = ColumnOrder(self.userVars)
        self.app = WordList(
            unoObjs, self.fileItems, self.columnOrder, self.userVars)
        self.generateOnClose = False
        self.disposeWhenFinished = True
        self.ok = False
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None
        self.dlgDispose = None

    def dontDisposeWhenFinished(self):
        """If you do this, then call .dlgDispose() when finished."""
        self.disposeWhenFinished = False

    def getResult(self):
        """The dialog result for calling code."""
        return self.ok

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.evtHandler = DlgEventHandler(self, self.app)
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
        self.evtHandler.setCtrls(self.dlgCtrls)
        self.columnOrder.loadUserVars()
        self.dlgCtrls.loadValues(
            self.userVars, self.fileItems, self.disposeWhenFinished)
        self.set_listboxColOrder_values()

        self.dlgClose = dlg.endExecute
        self.dlgDispose = dlg.dispose
        dlg.execute()

        if self.generateOnClose:
            self.app.generateList(self.punctToRemove, self.normForm)
        if self.disposeWhenFinished:
            dlg.dispose()

    def fileAdd(self):
        logger.debug(util.funcName('begin'))
        newItem = WordListFileItem(self.userVars)
        dlgFile = DlgWordListFile(newItem, self.unoObjs, self.userVars)
        dlgFile.showDlg()
        ok = dlgFile.getResult()
        dlgFile.dlgDispose()
        if ok:
            logger.debug("Adding item text %s", newItem)
            try:
                self.fileItems.addItem(newItem)
            except exceptions.ChoiceProblem as exc:
                self.msgbox.displayExc(exc)
                return
            self.fileItems.storeUserVars()
            logger.debug("Successfully added.")
            dutil.fill_list_ctrl(
                self.dlgCtrls.listboxFiles, self.fileItems.getItemTextList(),
                str(newItem))
            if self.disposeWhenFinished:
                self.dlgCtrls.btnMakeList.Label = theLocale.getText(
                    "Make List")
        logger.debug("FileAdd end")

    def fileChange(self):
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(
                self.dlgCtrls.listboxFiles, "a file")
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        fileItem = self.fileItems[itemPos]
        logger.debug("Copying item.")
        newItem = fileItem.getDeepCopy()
        dlgFile = DlgWordListFile(newItem, self.unoObjs, self.userVars)
        dlgFile.showDlg()
        ok = dlgFile.getResult()
        dlgFile.dlgDispose()
        if ok:
            logger.debug("Updating item.")
            try:
                self.fileItems.updateItem(itemPos, newItem)
            except exceptions.ChoiceProblem as exc:
                self.msgbox.displayExc(exc)
            self.fileItems.storeUserVars()
            logger.debug("Successfully updated.")

            logger.debug("Removing item at %d", itemPos)
            self.dlgCtrls.listboxFiles.removeItems(itemPos, 1)
            add_at_index = itemPos
            logger.debug("Adding item at %d", add_at_index)
            self.dlgCtrls.listboxFiles.addItem(
                str(newItem), add_at_index)
            self.dlgCtrls.listboxFiles.selectItemPos(add_at_index, True)
        logger.debug("FileUpdate end")

    def fileRemove(self):
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(
                self.dlgCtrls.listboxFiles, "a file")
            self.fileItems.deleteItem(itemPos)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        self.fileItems.storeUserVars()
        self.dlgCtrls.listboxFiles.removeItems(itemPos, 1)
        if len(self.fileItems) == 0 and self.disposeWhenFinished:
            self.dlgCtrls.btnMakeList.Label = theLocale.getText(
                "Make Empty List")
        # Select the next item
        dutil.select_index(self.dlgCtrls.listboxFiles, itemPos)
        logger.debug(util.funcName('end'))

    def moveUp(self):
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(self.dlgCtrls.listboxColOrder)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        changed = self.columnOrder.moveUp(itemPos)
        if changed:
            self.set_listboxColOrder_values(itemPos - 1)

    def moveDown(self):
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(self.dlgCtrls.listboxColOrder)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        changed = self.columnOrder.moveDown(itemPos)
        if changed:
            self.set_listboxColOrder_values(itemPos + 1)

    def makeList(self):
        logger.debug(util.funcName('begin'))
        if len(self.fileItems) == 0 and not self.disposeWhenFinished:
            self.msgbox.display("Please add a file to get words.")
            return
        self.storeUserVars()
        if self.disposeWhenFinished:
            self.generateOnClose = True
        else:
            self.ok = True
        self.dlgClose()

    def set_listboxColOrder_values(self, selItemPos=-1):
        listbox = self.dlgCtrls.listboxColOrder
        selectedValue = ""
        if 0 <= selItemPos < listbox.getItemCount():
            selectedValue = self.columnOrder.getTitle(selItemPos)
        dutil.fill_list_ctrl(
            listbox, self.columnOrder.getTitles(), selectedValue)

    def storeUserVars(self):
        self.punctToRemove = self.dlgCtrls.txtRemovePunct.getText()
        self.userVars.store("Punctuation", self.punctToRemove)
        self.normForm = self.userVars.get('NormForm')
        self.columnOrder.storeUserVars()
        for fileItem in self.fileItems:
            if fileItem.filetype in PhonReader.supportedNames():
                uservars.InterlinTags(self.userVars).loadUserVars()
                break
        for fileItem in self.fileItems:
            if fileItem.filetype in InterlinReader.supportedNames():
                uservars.PhonologyTags(self.userVars).loadUserVars()
                break


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.listboxFiles = ctrl_getter.get(_dlgdef.LISTBOX_FILES)
        self.txtRemovePunct = ctrl_getter.get(_dlgdef.TXT_REMOVE_PUNCT)
        self.listboxColOrder = ctrl_getter.get(_dlgdef.LISTBOX_COL_ORDER)
        self.btnMoveUp = ctrl_getter.get(_dlgdef.BTN_MOVE_UP)
        self.btnMoveDown = ctrl_getter.get(_dlgdef.BTN_MOVE_DOWN)
        self.btnMakeList = ctrl_getter.get(_dlgdef.BTN_MAKE_LIST)
        btnAdd = ctrl_getter.get(_dlgdef.BTN_ADD)
        btnRemove = ctrl_getter.get(_dlgdef.BTN_REMOVE)
        btnFileSettings = ctrl_getter.get(_dlgdef.BTN_FILE_SETTINGS)
        btnClose = ctrl_getter.get(_dlgdef.BTN_CLOSE)

        self.btnMoveUp.setActionCommand("MoveUp")
        self.btnMoveDown.setActionCommand("MoveDown")
        self.btnMakeList.setActionCommand("MakeList")
        btnAdd.setActionCommand("FileAdd")
        btnRemove.setActionCommand("FileRemove")
        btnFileSettings.setActionCommand("FileChange")
        btnClose.setActionCommand("Close")
        for ctrl in (self.btnMoveUp, self.btnMoveDown, self.btnMakeList,
                     btnAdd, btnRemove, btnFileSettings, btnClose):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars, fileItems, disposeWhenFinished):
        logger.debug("Initializing list of files")
        fileItems.loadUserVars()
        dutil.fill_list_ctrl(self.listboxFiles, fileItems.getItemTextList())

        varname = 'Punctuation'
        if userVars.isEmpty(varname) and len(fileItems) == 0:
            punctToRemove = " ".join(letters.PUNCTUATION)
            userVars.store(varname, punctToRemove)
        else:
            punctToRemove = userVars.get(varname)
        self.txtRemovePunct.setText(punctToRemove)

        varname = 'NormForm'
        if userVars.isEmpty(varname):
            userVars.store(varname, DEFAULT_NORM_FORM)

        if len(fileItems) == 0:
            self.btnMakeList.Label = theLocale.getText("Make Empty List")
        if not disposeWhenFinished:
            self.btnMakeList.Label = theLocale.getText("Get words")


class DlgEventHandler(XActionListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm, app):
        self.mainForm = mainForm
        self.dlgCtrls = None
        self.app = app

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "FileAdd":
            self.mainForm.fileAdd()
        elif event.ActionCommand == "FileChange":
            self.mainForm.fileChange()
        elif event.ActionCommand == "FileRemove":
            self.mainForm.fileRemove()
        elif event.ActionCommand == "MoveUp":
            self.mainForm.moveUp()
        elif event.ActionCommand == "MoveDown":
            self.mainForm.moveDown()
        elif event.ActionCommand == "Close":
            self.mainForm.storeUserVars()
            self.mainForm.dlgClose()
        elif event.ActionCommand == "MakeList":
            self.mainForm.makeList()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (showDlg,)
