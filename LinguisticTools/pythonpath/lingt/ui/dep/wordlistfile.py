"""
Dialog for settings to harvest words from data files.

This module exports:
    DlgWordListFile
"""
import copy
import logging
import string

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener

from lingt.access.calc.spreadsheet_reader import CalcFileReader
from lingt.access.text.sfm_reader import SFM_Reader
from lingt.access.writer import styles
from lingt.access.writer.doc_reader import DocReader
from lingt.access.xml.interlin_reader import InterlinReader
from lingt.access.xml.phon_reader import PhonReader
from lingt.access.xml.words_reader import WordsReader
from lingt.app import exceptions
from lingt.app.data import lingex_structs
from lingt.app.data.wordlist_structs import WhatToGrab
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgWordListFile as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.dep.writingsystem import DlgWritingSystem
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgwordlistFile")


class DlgWordListFile:
    """Main class for this dialog."""

    def __init__(self, fileItem, unoObjs, userVars):
        """fileItem is expected to be of type WordListFileItem.
        It will be modified by reference,
        so the new value can be used when this dialog is finished.
        """
        self.fileItem = fileItem
        self.filetype = fileItem.filetype
        self.thingsToGrab = [copy.copy(whatToGrab)
                             for whatToGrab in fileItem.thingsToGrab]
        logger.debug("len(self.thingsToGrab) = %d", len(self.thingsToGrab))
        self.unoObjs = unoObjs
        self.userVars = userVars
        self.msgbox = MessageBox(unoObjs)  # calls theLocale.loadUnoObjs()
        self.ok = False
        self.titles = None
        self.paraStyleNames = []
        self.charStyleNames = []
        self.fileTypeDict = {}
        self.fileTypeNames = []
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None
        self.dlgDispose = None

    def getResult(self):
        return self.ok

    def showDlg(self):
        logger.debug(util.funcName('begin', obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
        self.evtHandler.setCtrls(self.dlgCtrls)

        styleNames = styles.getListOfStyles('ParagraphStyles', self.unoObjs)
        self.paraStyleNames = dict(styleNames)
        paraStyleDispNames = tuple(dispName for dispName, name in styleNames)

        styleNames = styles.getListOfStyles('CharacterStyles', self.unoObjs)
        self.charStyleNames = dict(styleNames)
        charStyleDispNames = tuple(dispName for dispName, name in styleNames)
        self.dlgCtrls.loadValues(
            paraStyleDispNames, charStyleDispNames, self.fileItem,
            self.getTypesTuple(), self.fileTypeDict, self.fillFieldList)
        self.dlgCtrls.enableDisable(self.filetype)

        self.dlgClose = dlg.endExecute
        self.dlgDispose = dlg.dispose
        logger.debug(util.funcName('end', obj=self))
        dlg.execute()

    def fillFieldList(self):
        """Fills listWhatToGrab based on self.filetype."""
        count = self.dlgCtrls.listWhatToGrab.getItemCount()
        self.dlgCtrls.listWhatToGrab.removeItems(0, count)
        self.titles = [("", "")]
        if self.filetype in PhonReader.supportedNames():
            self.titles.extend(lingex_structs.LingPhonExample.GRAB_FIELDS)
        elif self.filetype in InterlinReader.supportedNames():
            self.titles.extend(lingex_structs.LingInterlinExample.GRAB_FIELDS)
        elif self.filetype in DocReader.supportedNames():
            self.titles.append((WhatToGrab.WHOLE_DOC, "Whole Document"))
        elif self.filetype in CalcFileReader.supportedNames():
            for char in string.ascii_uppercase:
                self.titles.append(
                    (char, "%s %s" % (theLocale.getText("Column"), char)))
        if len(self.titles) > 1:
            stringList = [theLocale.getText(display)
                          for dummy_key, display in self.titles]
            self.dlgCtrls.listWhatToGrab.addItems(tuple(stringList), 0)

    def useCurrent(self):
        logger.debug(util.funcName('begin'))
        url = self.unoObjs.document.getURL()
        if not url:
            self.msgbox.display("Please save the current document first.")
            return
        syspath = uno.fileUrlToSystemPath(url)
        self.dlgCtrls.fileControl.setText(syspath)
        dummy, title = DocReader.SUPPORTED_FORMATS[0]
        self.dlgCtrls.listboxFileType.selectItem(title, False)
        self.dlgCtrls.listboxFileType.selectItem(title, True)

    def selectWritingSys(self):
        logger.debug(util.funcName('begin'))
        filepath = self.dlgCtrls.fileControl.getText()
        defaultCode = self.dlgCtrls.txtWS.getText()
        dlgWS = DlgWritingSystem(defaultCode, self.unoObjs)
        dlgWS.readFile(filepath)
        dlgWS.showDlg()
        writingSystem = dlgWS.getResult()
        dlgWS.call_dispose()
        self.dlgCtrls.txtWS.setText(writingSystem.internalCode)

    def addItem(self):
        """Handle button press.  Add whatever form field was changed."""
        logger.debug(
            util.funcName(
                'begin', args="%d control(s) changed." %
                len(self.dlgCtrls.ctrlsChanged)))
        something_to_add = False
        for ctrlName, ctrl in self.dlgCtrls.ctrlsChanged.items():
            logger.debug(ctrlName)
            if ctrl == self.dlgCtrls.listWhatToGrab:
                newObj = self.fieldItemToAdd(ctrl.getSelectedItemPos())
            else:
                newObj = self.formItemToAdd(ctrlName, ctrl)
            if (newObj.grabType != WhatToGrab.UNSPECIFIED
                    and newObj.whichOne.strip() != ""):
                self.addWhatToGrab(newObj)
                something_to_add = True
        if not something_to_add:
            self.msgbox.display("Please select or enter something to find.")
        self.dlgCtrls.clearWhatToFind()
        logger.debug(util.funcName('end'))

    def fieldItemToAdd(self, itemPos):
        """Create a field item to be added."""
        newObj = WhatToGrab(self.userVars)
        if itemPos >= 0:
            key, dummy_display = self.titles[itemPos]
            newObj.whichOne = key
        if self.filetype in CalcFileReader.supportedNames():
            newObj.grabType = WhatToGrab.COLUMN
        elif self.filetype in DocReader.supportedNames():
            newObj.grabType = WhatToGrab.PART
        else:
            newObj.grabType = WhatToGrab.FIELD
        logger.debug(
            util.funcName('end', args=(newObj.whichOne, newObj.grabType)))
        return newObj

    def formItemToAdd(self, ctrlName, ctrl):
        """Create a form item to be added."""
        newObj = WhatToGrab(self.userVars)
        newObj.whichOne = ctrl.getText()
        if ctrlName == self.dlgCtrls.comboParaStyle.getModel().Name:
            # use display name to search
            newObj.grabType = WhatToGrab.PARASTYLE
            displayName = ctrl.getText()
            if displayName in self.paraStyleNames:
                newObj.whichOne = self.paraStyleNames[displayName]
        elif ctrlName == self.dlgCtrls.comboCharStyle.getModel().Name:
            newObj.grabType = WhatToGrab.CHARSTYLE
            displayName = ctrl.getText()
            if displayName in self.charStyleNames:
                newObj.whichOne = self.charStyleNames[displayName]
        elif ctrlName == self.dlgCtrls.comboFont.getModel().Name:
            newObj.grabType = WhatToGrab.FONT
            newObj.fontType = 'Western'
            if self.dlgCtrls.optFontTypeComplex.getState() == 1:
                newObj.fontType = 'Complex'
            elif self.dlgCtrls.optFontTypeAsian.getState() == 1:
                newObj.fontType = 'Asian'
        elif ctrlName == self.dlgCtrls.txtSFM.getModel().Name:
            newObj.grabType = WhatToGrab.SFM
        logger.debug(
            util.funcName('end', args=(newObj.whichOne, newObj.grabType)))
        return newObj

    def addWhatToGrab(self, newObj):
        """Add newObj to the list."""
        logger.debug(
            util.funcName(
                'begin',
                args="len(self.thingsToGrab) = %d" % len(self.thingsToGrab)))
        newObj.whichOne = newObj.whichOne.strip()
        for whatToGrab in self.thingsToGrab:
            if str(whatToGrab) == str(newObj):
                self.msgbox.display(
                    "%s is already in the list.", str(whatToGrab))
                return
        self.thingsToGrab.append(newObj)
        self.thingsToGrab.sort(key=str)

        stringList = [str(df) for df in self.thingsToGrab]
        dutil.fill_list_ctrl(
            self.dlgCtrls.listboxFields, stringList, str(newObj))
        logger.debug(
            util.funcName(
                'end', args="len(self.thingsToGrab) = %d" %
                len(self.thingsToGrab)))

    def removeItem(self):
        """Handle button press."""
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(self.dlgCtrls.listboxFields)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        del self.thingsToGrab[itemPos]
        self.dlgCtrls.listboxFields.removeItems(itemPos, 1)
        # Select the next item
        dutil.select_index(self.dlgCtrls.listboxFields, itemPos)
        logger.debug(
            util.funcName(
                'end', args="len(self.thingsToGrab) = %d" %
                len(self.thingsToGrab)))

    def doOk(self):
        """Handle button press."""
        logger.debug(
            util.funcName(
                'begin', args="len(self.thingsToGrab) = %d" %
                len(self.thingsToGrab)))
        if (len(self.thingsToGrab) == 0 and
                self.filetype not in ['spellingStatus']):
            ok = self.msgbox.displayOkCancel(
                "You did not specify anything to find.  Continue anyway?")
            if not ok:
                return
        for whatToGrab in self.thingsToGrab:
            if whatToGrab.whichOne == WhatToGrab.WHOLE_DOC:
                if len(self.thingsToGrab) > 1:
                    self.msgbox.display(
                        "'Whole Document' must be the only thing to find.")
                    return

        self.fileItem.filepath = self.dlgCtrls.fileControl.getText()
        self.fileItem.filetype = self.filetype
        self.fileItem.writingSystem = self.dlgCtrls.txtWS.getText()
        self.fileItem.thingsToGrab = self.thingsToGrab
        logger.debug("len(self.thingsToGrab) = %d", len(self.thingsToGrab))
        self.fileItem.includeMisspellings = (
            self.dlgCtrls.checkboxMiss.getState() == 1)
        self.fileItem.skipFirstRow = (
            self.dlgCtrls.checkboxSkipRow.getState() == 1)
        self.fileItem.splitByWhitespace = (
            self.dlgCtrls.checkboxSplit.getState() == 1)

        self.ok = True
        self.dlgClose()

    def getTypesTuple(self):
        """Get file types that can be read for a word list.
        Returns a tuple suitable for filling a list box.

        Note: This method cannot be named getTypes(), apparently because that
        name is used in an unohelper.Base interface, XTypeProvider.
        Update 02-Jul-2015: This is probably only the case if this class
        inherits from unohelper.Base, which it no longer does.
        """
        fileTypes = (
            DocReader.SUPPORTED_FORMATS +
            CalcFileReader.SUPPORTED_FORMATS +
            WordsReader.SUPPORTED_FORMATS +
            PhonReader.SUPPORTED_FORMATS +
            InterlinReader.SUPPORTED_FORMATS +
            SFM_Reader.SUPPORTED_FORMATS)
        self.fileTypeDict = dict(fileTypes)
        self.fileTypeNames, titles = zip(*fileTypes)
        return titles


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.fileControl = ctrl_getter.get(_dlgdef.FILE_PICKER)
        self.listboxFileType = ctrl_getter.get(_dlgdef.LIST_BOX_TYPE_OF_FILE)
        self.lblWS = ctrl_getter.get(_dlgdef.LBL_WS)
        self.txtWS = ctrl_getter.get(_dlgdef.TXT_WS)
        self.lblAddItem = ctrl_getter.get(_dlgdef.LBL_ADD_ITEM)
        self.lblWhatToGrab = ctrl_getter.get(_dlgdef.LBL_ADD_FIELD)
        self.listWhatToGrab = ctrl_getter.get(_dlgdef.LIST_ADD_FIELD)
        self.lblParaStyle = ctrl_getter.get(_dlgdef.LBL_PARA_STYLE)
        self.comboParaStyle = ctrl_getter.get(_dlgdef.COMBO_BOX_PARA_STYLE)
        self.lblCharStyle = ctrl_getter.get(_dlgdef.LBL_CHAR_STYLE)
        self.comboCharStyle = ctrl_getter.get(_dlgdef.COMBO_BOX_CHAR_STYLE)
        self.lblFont = ctrl_getter.get(_dlgdef.LBL_FONT)
        self.comboFont = ctrl_getter.get(_dlgdef.COMBO_BOX_FONT)
        self.lblSFM = ctrl_getter.get(_dlgdef.LBL_SFM)
        self.txtSFM = ctrl_getter.get(_dlgdef.TXT_SFM)
        self.checkboxMiss = ctrl_getter.get(_dlgdef.CHECK_BOX_INCLUDE_MISSPELLED_WORDS)
        self.checkboxSkipRow = ctrl_getter.get(_dlgdef.CHECKBOX_SKIP_FIRST_ROW)
        self.checkboxSplit = ctrl_getter.get(_dlgdef.CHK_SPLIT_BY_WHITESPACE)
        self.lblFields = ctrl_getter.get(_dlgdef.LBL_FIELDS)
        self.listboxFields = ctrl_getter.get(_dlgdef.LIST_BOX_FIELDS)
        self.optFontTypeWestern = ctrl_getter.get(_dlgdef.OPT_FONT_WESTERN)
        self.optFontTypeComplex = ctrl_getter.get(_dlgdef.OPT_FONT_CTL)
        self.optFontTypeAsian = ctrl_getter.get(_dlgdef.OPT_FONT_ASIAN)
        self.btnAdd = ctrl_getter.get(_dlgdef.BTN_ADD_ITEM)
        self.btnRemove = ctrl_getter.get(_dlgdef.BTN_REMOVE)
        self.btnSelectWS = ctrl_getter.get(_dlgdef.BTN_SELECT)
        btnUseCurrent = ctrl_getter.get(_dlgdef.BTN_CURRENT_DOC)
        btnOk = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        btnOk.setActionCommand("OK")
        btnUseCurrent.setActionCommand("UseCurrent")
        self.btnSelectWS.setActionCommand("SelectWritingSys")
        self.btnAdd.setActionCommand("AddItem")
        self.btnRemove.setActionCommand("RemoveItem")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnOk, btnUseCurrent, self.btnSelectWS, self.btnAdd,
                     self.btnRemove, btnCancel):
            ctrl.addActionListener(self.evtHandler)

        # values in these controls have been changed
        self.ctrlsChanged = {}

    def loadValues(self, paraStyleDispNames, charStyleDispNames, fileItem,
                   typesList, fileTypeDict, fillFieldList):
        """Set default values of controls."""
        self.fileControl.setText(fileItem.filepath)

        self.listboxFileType.addItems(typesList, 0)
        if fileItem.filetype in fileTypeDict:
            title = fileTypeDict[fileItem.filetype]
            self.listboxFileType.selectItem(title, True)
            fillFieldList()

        self.txtWS.setText(fileItem.writingSystem)

        self.comboParaStyle.addItems(paraStyleDispNames, 0)
        self.comboCharStyle.addItems(charStyleDispNames, 0)
        dutil.fill_list_ctrl(
            self.comboFont, styles.getListOfFonts(self.unoObjs))

        self.checkboxMiss.setState(fileItem.includeMisspellings)
        self.checkboxSkipRow.setState(fileItem.skipFirstRow)
        self.checkboxSplit.setState(fileItem.splitByWhitespace)

        stringList = [str(df) for df in fileItem.thingsToGrab]
        logger.debug("len(thingsToGrab) = %d", len(fileItem.thingsToGrab))
        logger.debug("Adding %d data field(s).", len(stringList))
        self.listboxFields.addItems(tuple(stringList), 0)
        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added button listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.listboxFileType.addItemListener(self.evtHandler)
        self.listWhatToGrab.addItemListener(self.evtHandler)

        for ctrl in (self.comboParaStyle, self.comboCharStyle, self.comboFont,
                     self.txtSFM):
            ctrl.addTextListener(self.evtHandler)

    def enableDisable(self, filetype):
        """Enable or disable controls as appropriate."""
        enabled = filetype in DocReader.supportedNames()
        self.lblParaStyle.getModel().Enabled = enabled
        self.lblCharStyle.getModel().Enabled = enabled
        self.lblFont.getModel().Enabled = enabled
        self.comboParaStyle.getModel().Enabled = enabled
        self.comboCharStyle.getModel().Enabled = enabled
        self.comboFont.getModel().Enabled = enabled
        self.optFontTypeWestern.getModel().Enabled = enabled
        self.optFontTypeComplex.getModel().Enabled = enabled
        self.optFontTypeAsian.getModel().Enabled = enabled

        enabled = (
            filetype in PhonReader.supportedNames() or
            filetype in InterlinReader.supportedNames() or
            filetype in CalcFileReader.supportedNames() or
            filetype in DocReader.supportedNames())
        self.lblWhatToGrab.getModel().Enabled = enabled
        self.listWhatToGrab.getModel().Enabled = enabled

        enabled = filetype in CalcFileReader.supportedNames()
        self.checkboxSkipRow.getModel().Enabled = enabled

        enabled = filetype == 'spellingStatus'
        self.lblAddItem.getModel().Enabled = not enabled
        self.lblFields.getModel().Enabled = not enabled
        self.listboxFields.getModel().Enabled = not enabled
        self.btnAdd.getModel().Enabled = not enabled
        self.btnRemove.getModel().Enabled = not enabled
        self.checkboxMiss.getModel().Enabled = enabled

        enabled = filetype in SFM_Reader.supportedNames()
        self.lblSFM.getModel().Enabled = enabled
        self.txtSFM.getModel().Enabled = enabled

        enabled = filetype == 'lift'
        self.txtWS.getModel().Enabled = enabled
        self.lblWS.getModel().Enabled = enabled
        self.btnSelectWS.getModel().Enabled = enabled

    def clearWhatToFind(self):
        logger.debug(util.funcName('begin'))
        #self.listWhatToGrab.selectItemPos(
        #    self.listWhatToGrab.getSelectedItemPos(), False)  # deselect
        self.listWhatToGrab.selectItemPos(0, True)
        self.comboParaStyle.setText("")
        self.comboCharStyle.setText("")
        self.comboFont.setText("")
        self.txtSFM.setText("")
        itemPos = self.listboxFields.getSelectedItemPos()
        if itemPos is not None and itemPos >= 0:
            # deselect
            self.listboxFields.selectItemPos(itemPos, False)
        self.ctrlsChanged.clear()
        logger.debug(util.funcName('end'))


class DlgEventHandler(XActionListener, XItemListener, XTextListener,
                      unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    def itemStateChanged(self, itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))

        src = itemEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.listWhatToGrab):
            self.dlgCtrls.ctrlsChanged[src.getModel().Name] = src
            logger.debug(
                "%d control(s) changed.", len(self.dlgCtrls.ctrlsChanged))

        elif evt_handler.sameName(src, self.dlgCtrls.listboxFileType):

            ## Change to selected file type
            try:
                itemPos = dutil.get_selected_index(
                    self.dlgCtrls.listboxFileType)
            except exceptions.ChoiceProblem:
                return
            self.mainForm.filetype = self.mainForm.fileTypeNames[itemPos]
            logger.debug("Filetype %s", self.mainForm.filetype)

            self.mainForm.fillFieldList()

            # empty listboxFields
            self.mainForm.thingsToGrab[:] = []  # clear the list
            logger.debug("len(thingsToGrab) = %d", len(self.mainForm.thingsToGrab))
            count = self.dlgCtrls.listboxFields.getItemCount()
            self.dlgCtrls.listboxFields.removeItems(0, count)

            self.dlgCtrls.clearWhatToFind()
            self.dlgCtrls.enableDisable(self.mainForm.filetype)

    @evt_handler.log_exceptions
    def textChanged(self, textEvent):
        src = textEvent.Source
        self.dlgCtrls.ctrlsChanged[src.getModel().Name] = src
        logger.debug("%d control(s) changed.", len(self.dlgCtrls.ctrlsChanged))

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "UseCurrent":
            self.mainForm.useCurrent()
        elif event.ActionCommand == "SelectWritingSys":
            self.mainForm.selectWritingSys()
        elif event.ActionCommand == "AddItem":
            self.mainForm.addItem()
        elif event.ActionCommand == "RemoveItem":
            self.mainForm.removeItem()
        elif event.ActionCommand == "OK":
            self.mainForm.doOk()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)
