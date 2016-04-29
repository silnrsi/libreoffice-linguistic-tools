# -*- coding: Latin-1 -*-
#
# This file created Mar 6 2013 by Jim Kornelsen
#
# 15-Mar-13 JDK  Interrupt if there is a choice problem.
# 09-Apr-13 JDK  Use only item in list even if not selected.
# 19-Apr-13 JDK  Replace .cct if it should be .xsl.
# 25-Apr-13 JDK  Add a default for txtXpath to prevent result &55.Ctrl.Value.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 12-Dec-15 JDK  Use listbox_items() instead of getItems().

"""
Dialog to save a change file from the list of words, either a CC table or
an XSLT file.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.spellingchanges import ChangerMaker
from lingt.ui.common import dutil
from lingt.ui.common import filepicker
from lingt.ui.common.dlgdefs import DlgChangerMaker as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgchangermaker")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----ShowMakerDlg()------------------------------------")
    calcUnoObjs = util.UnoObjs(ctx, doctype=util.UnoObjs.DOCTYPE_CALC)
    logger.debug("got UNO context")

    dlg = DlgChangerMaker(calcUnoObjs)
    dlg.showDlg()

# file extensions
CCT_EXT = ".cct"
XSLT_EXT = ".xsl"

class DlgChangerMaker:
    """Main class for this dialog."""

    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        self.msgbox = MessageBox(self.unoObjs)
        finder = uservars.SettingsDocFinder(
            uservars.Prefix.SPELLING, calcUnoObjs)
        self.writerUnoObjs = finder.getWriterDoc()
        self.userVars = uservars.UserVars(
            uservars.Prefix.SPELLING, self.writerUnoObjs.document, logger)
        self.app = ChangerMaker(calcUnoObjs, self.userVars)
        self.exportOnClose = False
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
        try:
            self.dlgCtrls = DlgControls(
                self.unoObjs, ctrl_getter, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.evtHandler.setCtrls(self.dlgCtrls)
        self.dlgCtrls.loadValues(self.userVars)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.exportOnClose:
            self.app.make()
        dlg.dispose()

    def showFilePicker(self):
        logger.debug(util.funcName('begin'))
        filetype = "CCT"
        extension = CCT_EXT
        if self.dlgCtrls.optXSLT.getState() == 1:  # selected
            filetype = "XSLT"
            extension = XSLT_EXT
        logger.debug("Extension %s", extension)
        defaultFilename = "spelling_changes" + extension
        if filetype == "CCT":
            filters = [
                ["Consistent Change Table (%s)" % CCT_EXT, "*" + CCT_EXT]]
        elif filetype == "XSLT":
            filters = [
                ["XSL Transformations (%s)" % XSLT_EXT, "*" + XSLT_EXT]]
        filepath = filepicker.showFilePicker(
            self.unoObjs, True, filters, defaultFilename)
        logger.debug(repr(filepath))
        if filepath == "":
            logger.debug("No filepath specified.")
            return
        if not filepath.lower().endswith(extension):
            filepath = "%s%s" % (filepath, extension) # += fails in python3
        self.dlgCtrls.txtFilePath.setText(filepath)
        logger.debug("set filepath to '%s'", filepath)

    def addXpath(self):
        logger.debug(util.funcName('begin'))
        newValue = self.dlgCtrls.txtXpath.getText()
        newValue = newValue.strip()
        stringList = dutil.listbox_items(self.dlgCtrls.listXpaths)
        logger.debug(repr(stringList))
        if newValue in stringList:
            self.msgbox.display("This expression is already in the list.")
            return
        stringList.append(newValue)
        stringList.sort()
        dutil.fill_list_ctrl(self.dlgCtrls.listXpaths, stringList, newValue)

    def removeXpath(self):
        logger.debug(util.funcName('begin'))
        try:
            itemPos = dutil.get_selected_index(self.dlgCtrls.listXpaths)
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
            return
        self.dlgCtrls.listXpaths.removeItems(itemPos, 1)
        # Select the next item
        dutil.select_index(self.dlgCtrls.listXpaths, itemPos)

    def closeAndExport(self):
        logger.debug(util.funcName('begin'))
        try:
            self.getFormResults()
            self.exportOnClose = True
            self.dlgClose()
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
        except exceptions.UserInterrupt:
            pass

    def closeDlg(self):
        logger.debug(util.funcName('begin'))
        self.getFormResults(verify=False)
        self.dlgClose()

    def getFormResults(self, verify=True):
        """Reads form fields and gets settings.
        If verify is True, raises an exception if there is a problem.
        """
        logger.debug(util.funcName('begin'))
        exportType = ""
        if self.dlgCtrls.optReplacementCCT.getState() == 1:  # selected
            exportType = "ReplacementCCT"
        elif self.dlgCtrls.optSFM_CCT.getState() == 1:
            exportType = "SFM_CCT"
            sfMarkers = self.dlgCtrls.txtSFM.getText().strip()
            if verify and sfMarkers == "":
                ok = self.msgbox.displayOkCancel(
                    "No SF markers were specified.  Continue anyway?")
                if not ok:
                    raise exceptions.UserInterrupt()
            self.userVars.store("SFM_Markers", sfMarkers)
            self.app.setSFM(sfMarkers)
        elif self.dlgCtrls.optXSLT.getState() == 1:
            exportType = "XSLT"
            if verify and self.dlgCtrls.listXpaths.getItemCount() == 0:
                ok = self.msgbox.displayOkCancel(
                    "No Xpath expressions were specified.  Continue anyway?")
                if not ok:
                    raise exceptions.UserInterrupt()
            self.userVars.store("XSLT_MatchPartial",
                                str(self.dlgCtrls.chkMatchPartial.getState()))
            self.app.setMatchPartial(
                self.dlgCtrls.chkMatchPartial.getState() == 1)
            self.userVars.store("XpathCount",
                                str(self.dlgCtrls.listXpaths.getItemCount()))
            stringList = dutil.listbox_items(self.dlgCtrls.listXpaths)
            for exprNum, exprVal in enumerate(stringList):
                varname = "XpathExpr%02d" % exprNum
                self.userVars.store(varname, exprVal)
            self.app.setXpathExprs(stringList)
        self.userVars.store("ExportType", exportType)
        self.app.setExportType(exportType)

        filepath = self.dlgCtrls.txtFilePath.getText().strip()
        if verify and filepath == "":
            raise exceptions.ChoiceProblem("Please specify a file to export.")
        self.userVars.store("Filepath", filepath)
        self.app.setFilepath(filepath)
        logger.debug(util.funcName('end'))

class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.optReplacementCCT = ctrl_getter.get(_dlgdef.OPT_REPLACEMENT_CCT)
        self.optSFM_CCT = ctrl_getter.get(_dlgdef.OPT_SFM_CCT)
        self.optXSLT = ctrl_getter.get(_dlgdef.OPT_XSLT)
        self.chkMatchPartial = ctrl_getter.get(_dlgdef.CHK_MATCH_PARTIAL)
        self.txtSFM = ctrl_getter.get(_dlgdef.TXT_SFMARKERS)
        self.txtXpath = ctrl_getter.get(_dlgdef.TXT_XPATH)
        self.listXpaths = ctrl_getter.get(_dlgdef.LIST_XPATH_EXPRS)
        self.txtFilePath = ctrl_getter.get(_dlgdef.TXT_FILE_PATH)
        btnBrowse = ctrl_getter.get(_dlgdef.BTN_BROWSE)
        btnRemoveXpath = ctrl_getter.get(_dlgdef.BTN_REMOVE_XPATH)
        btnAddXpath = ctrl_getter.get(_dlgdef.BTN_ADD_XPATH)
        btnRemoveXpath = ctrl_getter.get(_dlgdef.BTN_REMOVE_XPATH)
        btnOK = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        btnBrowse.setActionCommand("ShowFilePicker")
        btnAddXpath.setActionCommand("AddXpath")
        btnRemoveXpath.setActionCommand("RemoveXpath")
        btnOK.setActionCommand("Close_and_Export")
        btnCancel.setActionCommand("Close")
        for ctrl in (btnBrowse, btnAddXpath, btnRemoveXpath, btnOK, btnCancel):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars):
        exportType = userVars.get("ExportType")
        if exportType == "ReplacementCCT":
            self.optReplacementCCT.setState(True)
        elif exportType == "SFM_CCT":
            self.optSFM_CCT.setState(True)
        elif exportType == "XSLT":
            self.optXSLT.setState(True)

        self.txtXpath.setText("//gloss")
        varname = "XSLT_MatchPartial"
        if not userVars.isEmpty(varname):
            self.chkMatchPartial.setState(userVars.getInt(varname))

        ## Initialize list of Xpath expressions

        logger.debug("Initializing list of Xpath exprs")
        stringList = []
        num_exprs = userVars.getInt("XpathCount")
        for exprNum in range(0, num_exprs):
            varname = "XpathExpr%02d" % exprNum
            if not userVars.isEmpty(varname):
                stringList.append(userVars.get(varname))
        dutil.fill_list_ctrl(self.listXpaths, stringList)

        ## Other fields

        self.txtFilePath.setText(userVars.get("Filepath"))
        varname = "SFM_Markers"
        if userVars.isEmpty(varname):
            defaultCtrlText = "\\lx \\cf \\xv"
            userVars.store(varname, defaultCtrlText)
            userVarVal = defaultCtrlText
        else:
            userVarVal = userVars.get(varname)
        self.txtSFM.setText(userVarVal)
        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.optReplacementCCT.addItemListener(self.evtHandler)
        self.optSFM_CCT.addItemListener(self.evtHandler)
        self.optXSLT.addItemListener(self.evtHandler)


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @dutil.log_event_handler_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))
        newExt = CCT_EXT
        if self.dlgCtrls.optXSLT.getState() == 1:
            newExt = XSLT_EXT
        filepath = self.dlgCtrls.txtFilePath.getText().strip()
        if newExt == XSLT_EXT and filepath.endswith(CCT_EXT):
            filepath = filepath[:-len(CCT_EXT)] + XSLT_EXT  # replace extension
            self.dlgCtrls.txtFilePath.setText(filepath)
        elif newExt == CCT_EXT and filepath.endswith(XSLT_EXT):
            filepath = filepath[:-len(XSLT_EXT)] + CCT_EXT  # replace extension
            self.dlgCtrls.txtFilePath.setText(filepath)

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "ShowFilePicker":
            self.mainForm.showFilePicker()
        elif event.ActionCommand == "AddXpath":
            self.mainForm.addXpath()
        elif event.ActionCommand == "RemoveXpath":
            self.mainForm.removeXpath()
        elif event.ActionCommand == "Close_and_Export":
            self.mainForm.closeAndExport()
        elif event.ActionCommand == "Close":
            self.mainForm.closeDlg()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
