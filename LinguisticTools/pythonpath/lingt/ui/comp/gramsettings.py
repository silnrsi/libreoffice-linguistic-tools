# -*- coding: Latin-1 -*-
#
# This file created Jan 21 2010 by Jim Kornelsen
#
# 25-Jan-10 JDK  Use frames like FieldWorks interlinear, instead of tables.
# 01-Feb-10 JDK  List of files.  Option for frames or tables.
# 02-Mar-10 JDK  Set complex font name.
# 10-Mar-10 JDK  Use list of objects for file list.
# 18-Mar-10 JDK  Optionally don't insert outer table or separate morph columns.
# 28-Mar-10 JDK  Remove text row limit.
# 30-Mar-10 JDK  Option for orthographic line.
# 31-Mar-10 JDK  Add localization.
# 01-Apr-10 JDK  Free translation in quotes.  Option for POS above gloss.
# 15-Sep-10 JDK  Divide into packages.
# 30-Sep-10 JDK  Option for orthographic morpheme line.
# 08-Oct-10 JDK  Set SFM file defaults.
# 26-Oct-10 JDK  Set bottom margin on the table rather than POS or gloss.
# 28-Mar-11 JDK  Use multiline labels instead of a second label.
# 09-Apr-13 JDK  Use only item in list even if not selected.
# 14-May-13 JDK  Rename DlgSettings to unique name for assimilation.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 09-Sep-15 JDK  Set prefix when another item in list is selected.
# 22-Sep-15 JDK  Verify checkbox user variable list.
# 08-Dec-15 JDK  Checkbox to use segnum as ref number.
# 17-Feb-17 JDK  Word Line 1 and 2 instead of Orthographic and Text.

"""
Dialog for settings to import Grammar examples.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.writer import uservars
from lingt.access.writer.styles import GrammarStyles
from lingt.app import exceptions
from lingt.app.data import fileitemlist
from lingt.app.data import lingex_structs
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common import filepicker
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.dlgdefs import DlgGrammarSettings as _dlgdef
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlggramsettings")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgGramSettings(unoObjs)
    dlg.showDlg()

class DlgGramSettings:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        USERVAR_PREFIX = 'LTg_'  # for LinguisticTools Grammar variables
        self.userVars = uservars.UserVars(
            USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.fileItems = fileitemlist.FileItemList(
            fileitemlist.LingExFileItem, self.userVars)
        self.selectedIndex = -1  # position in listboxFiles
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
        self.evtHandler.setCtrls(self.dlgCtrls)
        self.dlgCtrls.loadValues(self.userVars, self.fileItems)
        self.dlgCtrls.enableDisable()
        self.viewFile(False)

        logger.debug("Finishing dialog creation")
        self.dlgClose = dlg.endExecute
        dlg.execute()
        dlg.dispose()

    def viewFile(self, checkForUpdates):
        """Handle selected list item."""
        logger.debug(util.funcName('begin'))
        if checkForUpdates:
            newSelectedItem = self.dlgCtrls.listboxFiles.getSelectedItem()
            logger.debug("newSelectedItem '%s'", newSelectedItem)
            self.updateFile(False)
            if newSelectedItem:
                self.dlgCtrls.listboxFiles.selectItem(newSelectedItem, True)
        try:
            self.selectedIndex = dutil.get_selected_index(
                self.dlgCtrls.listboxFiles, "a file")
            logger.debug("self.selectedIndex %d", self.selectedIndex)
        except exceptions.ChoiceProblem:
            return
        fileItem = self.fileItems[self.selectedIndex]
        logger.debug("Filepath %s", fileItem.filepath)
        self.dlgCtrls.txtPrefix.setText(fileItem.prefix)
        self.dlgCtrls.chkUseSegnum.setState(fileItem.use_segnum)
        logger.debug(util.funcName('end'))

    def updateFile(self, selectNewItem):
        logger.debug(util.funcName('begin'))
        if not 0 <= self.selectedIndex < len(self.fileItems):
            if selectNewItem:
                self.msgbox.displayExc(self.fileItems.noItemSelected())
            else:
                logger.debug(util.funcName('return'))
            return
        newItem = fileitemlist.LingExFileItem(self.userVars)
        newItem.filepath = self.fileItems[self.selectedIndex].filepath
        newItem.setPrefixNoSpaces(self.dlgCtrls.txtPrefix.getText())
        newItem.use_segnum = bool(self.dlgCtrls.chkUseSegnum.getState())
        oldItem = self.fileItems[self.selectedIndex]
        if oldItem:
            if (newItem.filepath == oldItem.filepath
                    and newItem.prefix == oldItem.prefix
                    and newItem.use_segnum == oldItem.use_segnum):
                logger.debug(
                    util.funcName(
                        'return', args="%s same as %s" % (newItem, oldItem)))
                return
            logger.debug("%s not same as %s", newItem, oldItem)
            try:
                self.fileItems.updateItem(self.selectedIndex, newItem)
            except exceptions.ChoiceProblem as exc:
                self.msgbox.displayExc(exc)
                return
        if selectNewItem:
            self.refreshListAndSelectItem(newItem)
        else:
            self.refreshList()
        logger.debug(util.funcName('end'))

    def refreshList(self):
        dutil.fill_list_ctrl(
            self.dlgCtrls.listboxFiles, self.fileItems.getItemTextList())

    def refreshListAndSelectItem(self, selItem):
        logger.debug(util.funcName('begin'))
        dutil.fill_list_ctrl(
            self.dlgCtrls.listboxFiles, self.fileItems.getItemTextList(),
            str(selItem))
        try:
            self.selectedIndex = dutil.get_selected_index(
                self.dlgCtrls.listboxFiles)
            logger.debug("self.selectedIndex %d", self.selectedIndex)
            self.viewFile(False)
        except exceptions.ChoiceProblem:
            return
        logger.debug(util.funcName('end'))

    def addFile(self):
        logger.debug(util.funcName('begin'))
        filepath = filepicker.showFilePicker(self.unoObjs)
        if filepath != "":
            newItem = fileitemlist.LingExFileItem(self.userVars)
            newItem.filepath = filepath
            try:
                logger.debug("Adding item '%s'", str(newItem))
                self.fileItems.addItem(newItem)
            except exceptions.ChoiceProblem as exc:
                self.msgbox.displayExc(exc)
                return
            self.refreshListAndSelectItem(newItem)
        logger.debug(util.funcName('end'))

    def removeFile(self):
        logger.debug(util.funcName('begin'))
        try:
            self.fileItems.deleteItem(self.selectedIndex)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        self.refreshList()

        ## Select the next item

        if self.dlgCtrls.listboxFiles.getItemCount() > 0:
            dutil.select_index(self.dlgCtrls.listboxFiles, self.selectedIndex)
            self.viewFile(False)
        else:
            ## The list is empty.  Clear the text field.
            self.dlgCtrls.txtPrefix.setText("")
            self.dlgCtrls.chkUseSegnum.setState(False)
            self.selectedIndex = -1
        logger.debug("FileRemove end")

    def storeAndClose(self):
        """Get settings from form and update user variables and
        document settings.
        """
        logger.debug(util.funcName('begin'))
        self.updateFile(False)
        self.fileItems.storeUserVars()
        for ctrl, varname in self.dlgCtrls.CHECKBOX_VAR_LIST:
            state = ctrl.getState()  # 0 not checked, 1 checked
            self.userVars.store(varname, str(state))
        state = self.dlgCtrls.optTables.getState()
        varname = "Method"
        if state == 1:  # selected
            self.userVars.store(varname, 'tables')
        else:
            self.userVars.store(varname, 'frames')
        varname = "SFM_Baseline"
        if self.userVars.isEmpty(varname):
            self.userVars.store(varname, "WordLine1")

        ## Modify document settings

        try:
            grammarStyles = GrammarStyles(self.unoObjs, self.userVars)
            grammarStyles.createStyles()
            uservars.GrammarTags(self.userVars).loadUserVars()

            ctrlText = self.dlgCtrls.txtNumColWidth.getText()
            grammarStyles.resizeNumberingCol(
                ctrlText, self.dlgCtrls.origNumColWidth)
        except (exceptions.ChoiceProblem, exceptions.StyleError) as exc:
            self.msgbox.displayExc(exc)
            return
        self.dlgClose()


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler
        self.origNumColWidth = 7    # we compare this to the changed value

        self.chkWordLine1 = ctrl_getter.get(_dlgdef.CHK_WORD_LINE1)
        self.chkWordLine2 = ctrl_getter.get(_dlgdef.CHK_WORD_LINE2)
        self.chkMorphLine1 = ctrl_getter.get(_dlgdef.CHK_MORPH_LINE1)
        self.chkMorphLine2 = ctrl_getter.get(_dlgdef.CHK_MORPH_LINE2)
        self.chkMorphsSeparate = ctrl_getter.get(
            _dlgdef.CHK_MORPHEMES_SEPARATE_COLS)
        self.chkPOS_Line = ctrl_getter.get(_dlgdef.CHK_POS_LINE)
        self.chkFT_inQuotes = ctrl_getter.get(_dlgdef.CHK_FT_IN_QUOTES)
        self.chkPOS_aboveGloss = ctrl_getter.get(_dlgdef.CHK_POS_ABOVE_GLOSS)
        self.chkNumbering = ctrl_getter.get(_dlgdef.CHK_INSERT_NUMBERING)
        self.chkOuterTable = ctrl_getter.get(_dlgdef.CHK_OUTER_TABLE)
        self.listboxFiles = ctrl_getter.get(_dlgdef.LISTBOX_FILES)
        self.txtPrefix = ctrl_getter.get(_dlgdef.TXT_REF_PREFIX)
        self.chkUseSegnum = ctrl_getter.get(_dlgdef.CHK_USE_SEGNUM)
        self.txtNumColWidth = ctrl_getter.get(_dlgdef.TXT_NUM_COL_WIDTH)
        self.lblNumColWidth = ctrl_getter.get(_dlgdef.LBL_NUM_COL_WIDTH)
        self.optTables = ctrl_getter.get(_dlgdef.OPTION_METHOD_TABLES)
        self.optFrames = ctrl_getter.get(_dlgdef.OPTION_METHOD_FRAMES)
        btnFileAdd = ctrl_getter.get(_dlgdef.BTN_FILE_ADD)
        btnFileRemove = ctrl_getter.get(_dlgdef.BTN_FILE_REMOVE)
        btnFileUpdate = ctrl_getter.get(_dlgdef.BTN_FILE_UPDATE)
        btnOk = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        ## Buttons

        btnFileAdd.setActionCommand("FileAdd")
        btnFileRemove.setActionCommand("FileRemove")
        btnFileUpdate.setActionCommand("FileUpdate")
        btnOk.setActionCommand("Ok")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnFileAdd, btnFileRemove, btnFileUpdate, btnOk,
                     btnCancel):
            ctrl.addActionListener(self.evtHandler)

        self.CHECKBOX_VAR_LIST = [
            (self.chkWordLine1, "ShowWordLine1"),
            (self.chkWordLine2, "ShowWordLine2"),
            (self.chkMorphLine1, "ShowMorphLine1"),
            (self.chkMorphLine2, "ShowMorphLine2"),
            (self.chkMorphsSeparate, "SeparateMorphColumns"),
            (self.chkPOS_Line, "ShowPartOfSpeech"),
            (self.chkFT_inQuotes, "FreeTransInQuotes"),
            (self.chkPOS_aboveGloss, "POS_AboveGloss"),
            (self.chkNumbering, "InsertNumbering"),
            (self.chkOuterTable, "MakeOuterTable")]

    def loadValues(self, userVars, fileItems):

        ## Initialize checkboxes

        logger.debug("Initializing checkboxes")
        self.verifyCheckboxVarList()
        for ctrl, varname in self.CHECKBOX_VAR_LIST:
            if not userVars.isEmpty(varname):
                ## TESTME: does setting value to e.g. 5 make it crash?
                ctrl.setState(userVars.getInt(varname))

        ## Initialize list of files

        logger.debug("Initializing list of files")
        fileItems.loadUserVars()
        dutil.fill_list_ctrl(self.listboxFiles, fileItems.getItemTextList())

        ## Numbering column width

        logger.debug("Numbering column width")
        varname = "NumberingColWidth"
        if userVars.isEmpty(varname):
            userVars.store(varname, str(self.origNumColWidth))
        else:
            self.origNumColWidth = userVars.getInt(varname)
        self.txtNumColWidth.setText(self.origNumColWidth)

        ## Hidden options

        varname = "ComparisonDoc"
        if userVars.isEmpty(varname):
            userVars.store(varname, "1") # default is True

        varname = "TableBottomMargin"
        if userVars.isEmpty(varname):
            userVars.store(varname, "0.13")

        ## Output method

        method = userVars.get("Method")
        if method == "tables":
            self.optTables.setState(True)

        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        for ctrl in (
                self.chkMorphLine1, self.chkMorphLine2, self.chkPOS_Line,
                self.optTables, self.optFrames, self.chkOuterTable):
            ctrl.addItemListener(self.evtHandler)

        self.listboxFiles.addItemListener(self.evtHandler)

    def verifyCheckboxVarList(self):
        """An assertion check to make sure the code is kept in sync."""
        checkboxList = sorted(
            [varname for dummy_ctrl, varname in self.CHECKBOX_VAR_LIST])
        attrsList = sorted(
            [varname for dummy_attr, varname
             in lingex_structs.InterlinOutputSettings.USERVAR_BOOLEAN_ATTRS])
        assert checkboxList == attrsList

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        if (self.chkMorphLine1.getState() == 1
                or self.chkMorphLine2.getState() == 1):
            self.chkMorphsSeparate.getModel().Enabled = True
        else:
            self.chkMorphsSeparate.getModel().Enabled = False
        if (self.chkOuterTable.getState() == 1 or
                self.optTables.getState() == 1):
            self.txtNumColWidth.getModel().Enabled = True
            self.lblNumColWidth.getModel().Enabled = True
        else:
            self.txtNumColWidth.getModel().Enabled = False
            self.lblNumColWidth.getModel().Enabled = False

        if self.chkPOS_Line.getState() == 1:
            self.chkPOS_aboveGloss.getModel().Enabled = True
        else:
            self.chkPOS_aboveGloss.getModel().Enabled = False


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None
        self.handling_event = False

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    @evt_handler.do_not_enter_if_handling_event
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        logger.debug(util.funcName('begin'))
        self.dlgCtrls.enableDisable()
        self.mainForm.viewFile(True)

    @evt_handler.log_exceptions
    @evt_handler.remember_handling_event
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "FileAdd":
            self.mainForm.updateFile(False)
            self.mainForm.addFile()
        elif event.ActionCommand == "FileRemove":
            self.mainForm.removeFile()
        elif event.ActionCommand == "FileUpdate":
            self.mainForm.updateFile(True)
        elif event.ActionCommand == "Ok":
            self.mainForm.storeAndClose()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
