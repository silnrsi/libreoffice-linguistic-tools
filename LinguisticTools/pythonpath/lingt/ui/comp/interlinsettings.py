"""
Dialog for settings to import interlinear examples for grammar write-ups.
Stores persistent settings as explained in the uservars module.

Later, when the Grab Examples dialog is opened,
the lingexamples module loads these settings.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener

from lingt.access.writer import uservars
from lingt.access.writer.styles import InterlinStyles
from lingt.app import exceptions
from lingt.app.data import fileitemlist
from lingt.app.data import lingex_structs
from lingt.app.svc import lingexamples
from lingt.app.svc.lingexamples import EXTYPE_INTERLINEAR
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common import filepicker
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.dlgdefs import DlgInterlinSettings as _dlgdef
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlginterlinsettings")

def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgInterlinSettings(unoObjs)
    dlg.showDlg()

class DlgInterlinSettings:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.userVars = uservars.UserVars(
            uservars.Prefix.INTERLINEAR, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.fileItems = fileitemlist.FileItemList(
            fileitemlist.LingExFileItem, self.userVars)
        self.selectedIndex = -1  # position in listboxFiles
        self.app = lingexamples.ExServices(EXTYPE_INTERLINEAR, unoObjs)
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
        self.dlgCtrls.chkDontUseSegnum.setState(not fileItem.use_segnum)
        logger.debug(util.funcName('end'))

    def updateFile(self, selectNewItem):
        """:param selectNewItem: true to select item after refreshing list"""
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
        newItem.use_segnum = not bool(
            self.dlgCtrls.chkDontUseSegnum.getState())
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
            self.dlgCtrls.chkDontUseSegnum.setState(True)
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
        try:
            self.app.verifyRefnums()
        except (exceptions.DataNotFoundError,
                exceptions.DataInconsistentError) as exc:
            ok = self.msgbox.displayOkCancel(exc.msg, *exc.msg_args)
            if not ok:
                return

        ## Modify document settings

        try:
            interlinStyles = InterlinStyles(self.unoObjs, self.userVars)
            interlinStyles.createStyles()
            uservars.InterlinTags(self.userVars).loadUserVars()

            ctrlText = self.dlgCtrls.txtNumColWidth.getText()
            interlinStyles.resizeNumberingCol(
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

        self.chkWordText1 = ctrl_getter.get(_dlgdef.CHK_WORD_TEXT1)
        self.chkWordText2 = ctrl_getter.get(_dlgdef.CHK_WORD_TEXT2)
        self.chkWordGloss = ctrl_getter.get(_dlgdef.CHK_WORD_GLOSS)
        self.chkMorphText1 = ctrl_getter.get(_dlgdef.CHK_MORPH_TEXT1)
        self.chkMorphText2 = ctrl_getter.get(_dlgdef.CHK_MORPH_TEXT2)
        self.chkMorphGloss = ctrl_getter.get(_dlgdef.CHK_MORPH_GLOSS)
        self.chkMorphPos = ctrl_getter.get(_dlgdef.CHK_MORPH_POS)
        self.chkMorphPosBelowGloss = ctrl_getter.get(
            _dlgdef.CHK_MORPH_POS_BELOW_GLOSS)
        self.chkMorphsSeparate = ctrl_getter.get(
            _dlgdef.CHK_MORPHEMES_SEPARATE_COLS)
        self.chkFT_inQuotes = ctrl_getter.get(_dlgdef.CHK_FT_IN_QUOTES)
        self.chkNumbering = ctrl_getter.get(_dlgdef.CHK_INSERT_NUMBERING)
        self.chkOuterTable = ctrl_getter.get(_dlgdef.CHK_OUTER_TABLE)
        self.listboxFiles = ctrl_getter.get(_dlgdef.LISTBOX_FILES)
        self.txtPrefix = ctrl_getter.get(_dlgdef.TXT_REF_PREFIX)
        self.chkDontUseSegnum = ctrl_getter.get(_dlgdef.CHK_DONT_USE_SEGNUM)
        self.txtNumColWidth = ctrl_getter.get(_dlgdef.TXT_NUM_COL_WIDTH)
        self.lblNumColWidth = ctrl_getter.get(_dlgdef.LBL_NUM_COL_WIDTH)
        self.optTables = ctrl_getter.get(_dlgdef.OPTION_METHOD_TABLES)
        self.optFrames = ctrl_getter.get(_dlgdef.OPTION_METHOD_FRAMES)
        btnFileAdd = ctrl_getter.get(_dlgdef.BTN_FILE_ADD)
        btnFileRemove = ctrl_getter.get(_dlgdef.BTN_FILE_REMOVE)
        btnOk = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        ## Buttons

        btnFileAdd.setActionCommand("FileAdd")
        btnFileRemove.setActionCommand("FileRemove")
        btnOk.setActionCommand("OK")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnFileAdd, btnFileRemove, btnOk, btnCancel):
            ctrl.addActionListener(self.evtHandler)

        self.CHECKBOX_VAR_LIST = [
            (self.chkWordText1, "ShowWordText1"),
            (self.chkWordText2, "ShowWordText2"),
            (self.chkWordGloss, "ShowWordGloss"),
            (self.chkMorphText1, "ShowMorphText1"),
            (self.chkMorphText2, "ShowMorphText2"),
            (self.chkMorphGloss, "ShowMorphGloss"),
            (self.chkMorphPos, "ShowMorphPartOfSpeech"),
            (self.chkMorphPosBelowGloss, "MorphPartOfSpeechBelowGloss"),
            (self.chkMorphsSeparate, "SeparateMorphColumns"),
            (self.chkFT_inQuotes, "FreeTransInQuotes"),
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
                self.chkMorphText1, self.chkMorphText2, self.chkMorphGloss,
                self.chkMorphPos,
                self.optTables, self.optFrames, self.chkOuterTable,
                self.chkDontUseSegnum):
            ctrl.addItemListener(self.evtHandler)

        self.listboxFiles.addItemListener(self.evtHandler)
        self.txtPrefix.addTextListener(self.evtHandler)

    def verifyCheckboxVarList(self):
        """An assertion check to make sure the code is kept in sync."""
        checkboxSet = {
            varname for dummy_ctrl, varname in self.CHECKBOX_VAR_LIST}
        attrsSet = {
            varname for dummy_attr, varname in
            lingex_structs.InterlinOutputSettings.USERVAR_BOOLEAN_ATTRS}
        missingAttrs = checkboxSet - attrsSet
        extraAttrs = attrsSet - checkboxSet
        assert checkboxSet == attrsSet, (
            f"Assertion failed:\n"
            f"Items in checkboxSet but not in attrsSet: {missingAttrs}\n"
            f"Items in attrsSet but not in checkboxSet: {extraAttrs}")

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        if (self.chkMorphText1.getState() == 1
                or self.chkMorphText2.getState() == 1):
            self.chkMorphsSeparate.getModel().Enabled = True
        else:
            self.chkMorphsSeparate.getModel().Enabled = False
        if (self.chkOuterTable.getState() == 1
                or self.optTables.getState() == 1):
            self.txtNumColWidth.getModel().Enabled = True
            self.lblNumColWidth.getModel().Enabled = True
        else:
            self.txtNumColWidth.getModel().Enabled = False
            self.lblNumColWidth.getModel().Enabled = False
        if (self.chkMorphPos.getState() == 1
                and self.chkMorphGloss.getState() == 1):
            self.chkMorphPosBelowGloss.getModel().Enabled = True
        else:
            self.chkMorphPosBelowGloss.getModel().Enabled = False

class DlgEventHandler(XActionListener, XItemListener, XTextListener,
                      unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None
        self.handling_event = False

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    @evt_handler.do_not_enter_if_handling_event
    def itemStateChanged(self, itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        logger.debug(util.funcName('begin'))
        src = itemEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.listboxFiles):
            self.mainForm.viewFile(False)
            return
        if evt_handler.sameName(src, self.dlgCtrls.chkDontUseSegnum):
            #self.mainForm.updateFile(True)
            self.mainForm.viewFile(True)
            return
        for ctrl in (
                self.dlgCtrls.chkMorphText1, self.dlgCtrls.chkMorphText2,
                self.dlgCtrls.chkMorphGloss, self.dlgCtrls.chkMorphPos,
                self.dlgCtrls.optTables,
                self.dlgCtrls.optFrames, self.dlgCtrls.chkOuterTable):
            if evt_handler.sameName(src, ctrl):
                self.dlgCtrls.enableDisable()
                return
        logger.warning("unexpected source %s", src.Model.Name)

    @evt_handler.log_exceptions
    @evt_handler.do_not_enter_if_handling_event
    def textChanged(self, textEvent):
        """XTextListener event handler."""
        logger.debug(util.funcName('begin'))
        src = textEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.txtPrefix):
            self.mainForm.updateFile(True)
        else:
            logger.warning("unexpected source %s", src.Model.Name)

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
        elif event.ActionCommand == "OK":
            self.mainForm.storeAndClose()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (showDlg,)
