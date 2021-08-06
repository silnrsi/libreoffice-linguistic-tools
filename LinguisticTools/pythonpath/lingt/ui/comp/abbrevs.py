# -*- coding: Latin-1 -*-

"""
Insert a list of abbreviations used in the document.
Reads from gloss and part of speech.

This breaks the layer design to some extent because it works directly
with the Writer package, bypassing the App layer.  This could be changed in the
future by moving code to lingt.app.abbreviations.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.writer import styles
from lingt.access.writer import search
from lingt.access.writer import outputmanager
from lingt.access.writer.uservars import Prefix, UserVars
from lingt.app import exceptions
from lingt.app.svc import abbreviations
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgAbbreviations as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgabbrevs")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgAbbreviations(unoObjs)
    dlg.showDlg()

class DlgAbbreviations:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.userVars = UserVars(
            Prefix.ABBREVIATIONS, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.abbrevList = abbreviations.AbbrevList(self.unoObjs, self.userVars)
        self.selectedIndex = -1  # position in abbrevList and listboxAbbrevs
        self.selectedAbbrev = None
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.dlgClose = dlg.endExecute
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
        logger.debug("Got controls.")

        self.dlgCtrls.loadValues(self.userVars, self.abbrevList)
        self.viewAbbrev(False)

        ## Display the dialog and then close it

        dlg.execute()
        self.storeResults()
        dlg.dispose()

    def viewAbbrev(self, checkForUpdates):
        """
        Fill the form with values of the selected abbreviation.
        :param checkForUpdates: set to true to update current item if needed
        """
        logger.debug(util.funcName('begin'))
        if checkForUpdates:
            newSelectedItem = self.dlgCtrls.listboxAbbrevs.getSelectedItem()
            logger.debug("newSelectedItem '%s'", newSelectedItem)
            self.updateAbbrev(False)
            if newSelectedItem:
                # Select the new item again,
                # since it may have been deselected while refreshing the list.
                self.dlgCtrls.listboxAbbrevs.selectItem(newSelectedItem, True)
        try:
            self.selectedIndex = dutil.get_selected_index(
                self.dlgCtrls.listboxAbbrevs)
            logger.debug("self.selectedIndex %d", self.selectedIndex)
        except exceptions.ChoiceProblem:
            return
        abbr = self.abbrevList[self.selectedIndex]
        logger.debug("Abbrev %s", abbr.abbrevText)

        self.dlgCtrls.txtAbbrev.setText(abbr.abbrevText)
        self.dlgCtrls.txtFullName.setText(abbr.fullName)
        if abbr.forceOutput:
            self.dlgCtrls.chkForceOutput.setState(True)
        else:
            self.dlgCtrls.chkForceOutput.setState(False)
        self.dlgCtrls.txtOccurrences.setText(abbr.occurrences)
        logger.debug(util.funcName('end'))

    def updateAbbrev(self, selectNewItem):
        """
        Update abbrev attributes from dialog fields if changed.
        :param selectNewItem: set to True to select item when refreshing list
        """
        logger.debug(util.funcName('begin'))
        if not 0 <= self.selectedIndex < len(self.abbrevList):
            if selectNewItem:
                self.msgbox.displayExc(self.abbrevList.noItemSelected())
            return
        newAbbrev = abbreviations.Abbrev()
        newAbbrev.abbrevText = self.dlgCtrls.txtAbbrev.getText()
        if not newAbbrev.abbrevText:
            return
        newAbbrev.fullName = self.dlgCtrls.txtFullName.getText()
        if self.dlgCtrls.chkForceOutput.getState() == 1:  # checked
            newAbbrev.forceOutput = True
        oldAbbrev = self.abbrevList[self.selectedIndex]
        if oldAbbrev:
            if newAbbrev.sameAs(oldAbbrev):
                return
            logger.debug("%r not sameAs %r", newAbbrev, oldAbbrev)
            if newAbbrev.abbrevText == oldAbbrev.abbrevText:
                newAbbrev.occurrences = oldAbbrev.occurrences
            try:
                self.abbrevList.updateItem(self.selectedIndex, newAbbrev)
            except exceptions.ChoiceProblem as exc:
                self.msgbox.displayExc(exc)
                return
        if selectNewItem:
            self.refreshListAndSelectItem(newAbbrev)
        else:
            self.refreshList()
        logger.debug(util.funcName('end'))

    def refreshList(self):
        dutil.fill_list_ctrl(
            self.dlgCtrls.listboxAbbrevs, self.abbrevList.getItemTextList())

    def refreshListAndSelectItem(self, selItem):
        logger.debug(util.funcName('begin'))
        dutil.fill_list_ctrl(
            self.dlgCtrls.listboxAbbrevs, self.abbrevList.getItemTextList(),
            str(selItem))
        try:
            self.selectedIndex = dutil.get_selected_index(
                self.dlgCtrls.listboxAbbrevs)
            logger.debug("self.selectedIndex %d", self.selectedIndex)
            self.viewAbbrev(False)
        except exceptions.ChoiceProblem:
            return
        logger.debug(util.funcName('end'))

    def addAbbrev(self):
        logger.debug(util.funcName('begin'))
        newAbbrev = abbreviations.Abbrev()
        newAbbrev.abbrevText = "---"
        newAbbrev.fullName = ""
        self.abbrevList.addItem(newAbbrev, allowDuplicates=True)
        self.refreshListAndSelectItem(newAbbrev)
        logger.debug(util.funcName('end'))

    def deleteAbbrev(self):
        logger.debug(util.funcName('begin'))
        try:
            self.abbrevList.deleteItem(self.selectedIndex)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        self.refreshList()

        ## Select the next item

        if self.dlgCtrls.listboxAbbrevs.getItemCount() > 0:
            dutil.select_index(
                self.dlgCtrls.listboxAbbrevs, self.selectedIndex)
            self.viewAbbrev(False)
        else:
            ## The list is empty.  Clear the fields.
            logger.debug("Clearing fields.")
            self.dlgCtrls.txtAbbrev.setText("")
            self.dlgCtrls.txtFullName.setText("")
            self.dlgCtrls.chkForceOutput.setState(False)
            self.dlgCtrls.txtOccurrences.setText(0)
            self.selectedIndex = -1
        logger.debug(util.funcName('end'))

    def changeAllCaps(self):
        logger.debug(util.funcName('begin'))
        self.abbrevList.changeAllCaps()
        self.refreshList()
        dutil.select_index(self.dlgCtrls.listboxAbbrevs, self.selectedIndex)
        self.viewAbbrev(False)
        logger.debug(util.funcName('end'))

    def rescan(self):
        logger.debug(util.funcName('begin'))
        abbrevSearch = search.AbbrevSearch(self.unoObjs)
        abbrevSearch.findOccurrences(self.abbrevList)
        self.refreshList()
        dutil.select_index(self.dlgCtrls.listboxAbbrevs, self.selectedIndex)
        self.viewAbbrev(False)
        logger.debug(util.funcName('end'))

    def insertList(self):
        logger.debug(util.funcName('begin'))

        ## Rescan and prepare for output

        abbrevSearch = search.AbbrevSearch(self.unoObjs)
        abbrevSearch.findOccurrences(self.abbrevList)
        self.refreshList()
        self.abbrevList.storeUserVars()
        abbrevStyles = styles.AbbrevStyles(self.unoObjs, self.userVars)
        abbrevStyles.createStyles()

        ## Output the list and close

        writerOutput = outputmanager.AbbrevManager(self.unoObjs, abbrevStyles)
        try:
            writerOutput.outputList(self.abbrevList)
        except exceptions.MessageError as exc:
            self.msgbox.displayExc(exc)
        self.dlgClose()
        logger.debug(util.funcName('end'))

    def findNext(self):
        logger.debug(util.funcName('begin'))

        ## Get search form results

        displayName = self.dlgCtrls.cmbxSearchParaStyle.getText()
        if not displayName:
            self.msgbox.display("Please select a paragraph style.")
            return
        searchConfig = search.AbbrevSearchSettings()
        searchConfig.searchParaStyle = displayName
        self.userVars.store("SearchParaStyle", displayName)

        searchConfig.searchAffix = "any"
        if self.dlgCtrls.optSearchSuffix.getState() == 1:  # checked
            searchConfig.searchAffix = "suffix"
        elif self.dlgCtrls.optSearchPrefix.getState() == 1:  # checked
            searchConfig.searchAffix = "prefix"
        self.userVars.store("SearchAffix", searchConfig.searchAffix)

        try:
            searchConfig.maxSearchLength = int(
                self.dlgCtrls.txtMaxSearchLength.getText())
        except ValueError:
            self.msgbox.display("Please enter a number for max length.")
            return
        self.userVars.store("MaxSearchLength", searchConfig.maxSearchLength)

        searchConfig.searchUpperCase = False
        chkValue = self.dlgCtrls.chkSearchUpperCase.getState()
        if chkValue == 1:
            searchConfig.searchUpperCase = True
        self.userVars.store("SearchUpperCase", str(chkValue))

        searchConfig.startFromBeginning = False
        if self.dlgCtrls.chkStartFromBeginning.getState() == 1:
            searchConfig.startFromBeginning = True
            self.dlgCtrls.chkStartFromBeginning.setState(False)

        searchConfig.searchDelimiters = self.userVars.get("SearchDelimiters")

        ## Search

        abbrevSearch = search.AbbrevSearch(self.unoObjs)
        while True:
            possibleAbbrevs = abbrevSearch.findNext(
                searchConfig, self.abbrevList.getUniqueList())
            if len(possibleAbbrevs) == 0:
                self.msgbox.display("No more possible abbreviations found.")
                return
            for possibleAbbrevText in possibleAbbrevs:
                if possibleAbbrevText.strip() == "":
                    continue
                result = self.msgbox.displayYesNoCancel(
                    "Add '%s' as a new abbreviation?", possibleAbbrevText)
                if result == "yes":
                    logger.debug("Adding abbreviation from search.")
                    newAbbrev = abbreviations.Abbrev()
                    newAbbrev.abbrevText = possibleAbbrevText
                    newAbbrev.occurrences = 1
                    try:
                        self.abbrevList.addItem(newAbbrev)
                        self.refreshListAndSelectItem(newAbbrev)
                    except exceptions.ChoiceProblem as exc:
                        self.msgbox.displayExc(exc)
                elif result == "cancel":
                    return
                elif result == "no":
                    ## continue
                    pass
        logger.debug(util.funcName('end'))

    def storeResults(self):
        logger.debug(util.funcName('begin'))
        self.updateAbbrev(False)
        self.abbrevList.storeUserVars()
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.listboxAbbrevs = ctrl_getter.get(_dlgdef.LISTBOX_ABBREVIATIONS)
        self.txtAbbrev = ctrl_getter.get(_dlgdef.TXT_ABBREV)
        self.txtFullName = ctrl_getter.get(_dlgdef.TXT_FULL_NAME)
        self.chkForceOutput = ctrl_getter.get(_dlgdef.CHK_FORCE_OUTPUT)
        self.txtOccurrences = ctrl_getter.get(_dlgdef.TXT_OCCURRENCES)
        btnUpdateAbbrev = ctrl_getter.get(_dlgdef.BTN_UPDATE_ABBREV)
        btnAddAbbrev = ctrl_getter.get(_dlgdef.BTN_ADD_ABBREV)
        btnDeleteAbbrev = ctrl_getter.get(_dlgdef.BTN_DELETE_ABBREV)
        btnChangeAllCaps = ctrl_getter.get(_dlgdef.BTN_CHANGE_ALL_CAPS)
        btnRescan = ctrl_getter.get(_dlgdef.BTN_RESCAN)
        self.cmbxSearchParaStyle = ctrl_getter.get(
            _dlgdef.CMBX_SEARCH_PARA_STYLE)
        self.optSearchSuffix = ctrl_getter.get(_dlgdef.OPT_SEARCH_SUFFIX)
        self.optSearchPrefix = ctrl_getter.get(_dlgdef.OPT_SEARCH_PREFIX)
        self.optSearchAny = ctrl_getter.get(_dlgdef.OPT_SEARCH_ANY)
        self.txtMaxSearchLength = ctrl_getter.get(
            _dlgdef.TXT_MAX_SEARCH_LENGTH)
        self.chkSearchUpperCase = ctrl_getter.get(
            _dlgdef.CHK_SEARCH_UPPER_CASE)
        self.chkStartFromBeginning = ctrl_getter.get(
            _dlgdef.CHK_START_FROM_BEGINNING)
        btnFindNext = ctrl_getter.get(_dlgdef.BTN_FIND_NEXT)
        btnInsertList = ctrl_getter.get(_dlgdef.BTN_INSERT_LIST)
        btnClose = ctrl_getter.get(_dlgdef.BTN_CLOSE)

        btnUpdateAbbrev.setActionCommand("UpdateAbbrev")
        btnAddAbbrev.setActionCommand("AddAbbrev")
        btnDeleteAbbrev.setActionCommand("DeleteAbbrev")
        btnChangeAllCaps.setActionCommand("ChangeAllCaps")
        btnRescan.setActionCommand("Rescan")
        btnFindNext.setActionCommand("FindNext")
        btnInsertList.setActionCommand("InsertList")
        btnClose.setActionCommand("Close")
        for ctrl in (
                btnUpdateAbbrev, btnAddAbbrev, btnDeleteAbbrev,
                btnChangeAllCaps, btnRescan, btnFindNext, btnInsertList,
                btnClose):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars, abbrevList):
        logger.debug(util.funcName('begin'))
        abbrevList.loadUserVars()
        dutil.fill_list_ctrl(
            self.listboxAbbrevs, abbrevList.getItemTextList())

        styleNames = styles.getListOfStyles("ParagraphStyles", self.unoObjs)
        displayNames = [dispName for dispName, name in styleNames]
        selectedValue = userVars.get("SearchParaStyle")
        if selectedValue == "":
            userVarsInterlin = UserVars(
                Prefix.INTERLINEAR, self.unoObjs.document, logger)
            selectedValue = userVarsInterlin.get("StyleName_Gloss")
        dutil.fill_list_ctrl(
            self.cmbxSearchParaStyle, displayNames, selectedValue)

        searchAffix = userVars.get("SearchAffix")
        if searchAffix == "suffix":
            self.optSearchSuffix.setState(True)
        elif searchAffix == "prefix":
            self.optSearchPrefix.setState(True)
        elif searchAffix == "any":
            self.optSearchAny.setState(True)

        varname = "MaxSearchLength"
        if userVars.isEmpty(varname):
            defaultCtrlText = "5"
            userVars.store(varname, defaultCtrlText)
            userVarVal = defaultCtrlText
        else:
            userVarVal = userVars.getInt(varname)
        self.txtMaxSearchLength.setText(userVarVal)

        if userVars.getInt("SearchUpperCase") == 1:
            self.chkSearchUpperCase.setState(True)

        self.addRemainingListeners()
        logger.debug(util.funcName('end'))

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        logger.debug(util.funcName())
        self.listboxAbbrevs.addItemListener(self.evtHandler)


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.handling_event = False

    @evt_handler.log_exceptions
    @evt_handler.do_not_enter_if_handling_event
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))
        self.mainForm.viewAbbrev(True)

    @evt_handler.log_exceptions
    @evt_handler.remember_handling_event
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "UpdateAbbrev":
            self.mainForm.updateAbbrev(True)
        elif event.ActionCommand == "AddAbbrev":
            self.mainForm.addAbbrev()
        elif event.ActionCommand == "DeleteAbbrev":
            self.mainForm.deleteAbbrev()
        elif event.ActionCommand == "ChangeAllCaps":
            self.mainForm.changeAllCaps()
        elif event.ActionCommand == "Rescan":
            self.mainForm.rescan()
        elif event.ActionCommand == "InsertList":
            self.mainForm.insertList()
        elif event.ActionCommand == "FindNext":
            self.mainForm.findNext()
        elif event.ActionCommand == "Close":
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
