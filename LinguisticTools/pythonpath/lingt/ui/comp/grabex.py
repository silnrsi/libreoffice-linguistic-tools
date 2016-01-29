# -*- coding: Latin-1 -*-
#
# This file created Dec 22 2009 by Jim Kornelsen
#
# 24-Dec-09 JDK  Split into a separate file for dialogs.
# 07-Jan-09 JDK  Make the script filenames related to menu options.
# 22-Jan-10 JDK  Added Grammar.
# 25-Jan-10 JDK  Use frames like FieldWorks interlinear, instead of tables.
# 02-Feb-10 JDK  Option to create tables.
# 03-Feb-10 JDK  Store morphemes as a list for each word.
# 09-Feb-10 JDK  Split WriterOutput into 3 classes.
# 11-Feb-10 JDK  Import LIFT data from Flex.
# 15-Feb-10 JDK  Add progress bar.
# 18-Mar-10 JDK  Optionally don't insert outer table or separate morph columns.
# 20-Mar-10 JDK  Frames and CTL fonts can be slow.  Solved by starting with
#                FIX width.
# 22-Mar-10 JDK  Added function for testing.
# 23-Mar-10 JDK  Import SFM data directly from Toolbox.  Add tests.
# 29-Mar-10 JDK  Make number of table columns optimal by trying new columns.
# 30-Mar-10 JDK  Option for orthographic line.
# 31-Mar-10 JDK  Add localization.
# 24-Apr-10 JDK  Fixed bug: Don't use gotoEnd.  Don't allow tables to break
#                across pages.
# 25-Aug-10 JDK  Use "cf" instead of "txt" from FieldWorks.
# 07-Sep-10 JDK  Large examples are too slow, so set row height to fixed,
#                and insert newlines between a lot of frames.
# 09-Sep-10 JDK  Import data from Toolbox in XML instead of SFM.
# 13-Sep-10 JDK  If ref no.  is not found, then don't delete it.
# 14-Sep-10 JDK  Merge Phonology and Grammar.  Divide into packages.
# 20-Sep-10 JDK  Ability to update examples.
# 02-Oct-10 JDK  Updating should not default to search from beginning.
# 01-Apr-11 JDK  Localize Update and Replace labels that change.
# 22-Jul-11 JDK  Separate function requireInputFile() - for Script Practice.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.

"""
Dialog to import Phonology and Grammar examples.

This module exports:
    showPhonologyDlg()
    showGrammarDlg()
"""
import uno
import unohelper
import logging
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.writer.uservars import UserVars
from lingt.app import exceptions
from lingt.app.svc import lingexamples
from lingt.app.svc.lingexamples import EXTYPE_PHONOLOGY, EXTYPE_GRAMMAR
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlggrabex")


def showPhonologyDlg(ctx=uno.getComponentContext()):
    showDlgForType(ctx, EXTYPE_PHONOLOGY)

def showGrammarDlg(ctx=uno.getComponentContext()):
    showDlgForType(ctx, EXTYPE_GRAMMAR)

def showDlgForType(ctx, exType):
    logger.debug("----showDlg(%s)--------------------------------", exType)
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgGrabExamples(exType, unoObjs)
    if not requireInputFile(exType, unoObjs, dlg.userVars):
        return
    dlg.showDlg()

def requireInputFile(exType, unoObjs, userVars):
    """Make sure the user has specified an input file.
    If no file is specified, displays an error message and returns false.
    """
    varname = "XML_filePath"
    if exType == EXTYPE_GRAMMAR:
        varname = "XML_filePath00"
    filepath = userVars.get(varname)
    if filepath == "":
        msgbox = MessageBox(unoObjs)
        if exType == EXTYPE_GRAMMAR:
            msgbox.display(
                "Please go to Grammar Settings and specify a file.")
        else:
            msgbox.display(
                "Please go to Phonology Settings and specify a file.")
        return False
    return True

class DlgGrabExamples:
    """Main class for this dialog."""

    def __init__(self, exType, unoObjs):
        self.exType = exType
        self.unoObjs = unoObjs
        logger.debug("DlgGrabExamples() %s", exType)
        self.msgbox = MessageBox(unoObjs)
        if exType == EXTYPE_PHONOLOGY:
            USERVAR_PREFIX = "LTp_"  # LinguisticTools Phonology variables
            self.titleText = theLocale.getText("Get Phonology Examples")
        else:
            USERVAR_PREFIX = "LTg_"  # LinguisticTools Grammar variables
            self.titleText = theLocale.getText(
                "Get Interlinear Grammar Examples")
        self.userVars = UserVars(USERVAR_PREFIX, unoObjs.document, logger)
        self.app = lingexamples.ExServices(exType, unoObjs)
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None
        logger.debug("DlgGrabExamples init() finished")

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgExGrab")
        if not dlg:
            return
        self.evtHandler = DlgEventHandler(self, self.app)
        try:
            self.dlgCtrls = DlgControls(self.unoObjs, dlg, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.evtHandler.setCtrls(self.dlgCtrls)
        dlg.setTitle(self.titleText)
        self.dlgCtrls.loadValues(self.userVars)
        self.dlgCtrls.enableDisable(self.app, self.userVars)

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.exType == EXTYPE_GRAMMAR:
            self.app.addExampleNumbers()
        dlg.dispose()

    def insertEx(self):
        logger.debug(util.funcName('begin'))
        refText = self.dlgCtrls.txtRefnum.getText()
        self.userVars.store("EXREFNUM", refText)
        self.app.insertByRefnum(refText)

    def findNext(self):
        logger.debug(util.funcName('begin'))
        startFromBeginning = (
            self.dlgCtrls.chkStartFromBeginning.getState() == 1)
        found = self.app.findNext(startFromBeginning)
        if found:
            self.dlgCtrls.chkStartFromBeginning.setState(False)

    def replace(self):
        logger.debug(util.funcName('begin'))
        startFromBeginning = (
            self.dlgCtrls.chkStartFromBeginning.getState() == 1)
        found = self.app.replace(startFromBeginning)
        if found:
            self.dlgCtrls.chkStartFromBeginning.setState(False)

    def replaceAll(self):
        logger.debug(util.funcName('begin'))
        if self.app.isUpdatingExamples():
            result = self.msgbox.displayOkCancel(
                "Update all examples now?  "
                "It is recommended to save a copy of your document first.")
            if not result:
                return
            ## Refresh the window
            oContainerWindow = self.unoObjs.frame.getContainerWindow()
            oContainerWindow.setVisible(False)
            oContainerWindow.setVisible(True)

        self.dlgCtrls.chkStartFromBeginning.setState(True)
        self.app.replaceAll()


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """Raises exceptions.LogicError if controls cannot be found."""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.txtRefnum = dutil.getControl(dlg, "TxtRefnum")
        self.chkStartFromBeginning = dutil.getControl(
            dlg, "ChkStartFromBeginning")
        self.optSearchRefNum = dutil.getControl(dlg, "optSearchRefNum")
        self.optSearchExisting = dutil.getControl(dlg, "optSearchExisting")
        self.btnReplace = dutil.getControl(dlg, "BtnReplace")
        self.btnReplaceAll = dutil.getControl(dlg, "BtnReplaceAll")
        btnFindNext = dutil.getControl(dlg, "BtnFindNext")
        btnReplace = dutil.getControl(dlg, "BtnReplace")
        btnReplaceAll = dutil.getControl(dlg, "BtnReplaceAll")
        btnInsertEx = dutil.getControl(dlg, "BtnInsertEx")
        btnClose = dutil.getControl(dlg, "BtnClose")

        btnFindNext.setActionCommand("FindNext")
        btnReplace.setActionCommand("Replace")
        btnReplaceAll.setActionCommand("ReplaceAll")
        btnInsertEx.setActionCommand("InsertEx")
        btnClose.setActionCommand("Close")
        for ctrl in (btnFindNext, btnReplace, btnReplaceAll, btnInsertEx,
                     btnClose):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars):
        self.txtRefnum.setText(userVars.get("EXREFNUM"))
        self.txtRefnum.setFocus()
        varname = "SearchFor"
        if not userVars.isEmpty(varname):
            if userVars.get(varname) == "RefNum":
                self.optSearchRefNum.setState(True)
            else:
                self.optSearchExisting.setState(True)
        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.optSearchRefNum.addItemListener(self.evtHandler)
        self.optSearchExisting.addItemListener(self.evtHandler)

    def enableDisable(self, app, userVars):
        """Enable or disable controls as appropriate."""
        logger.debug(util.funcName('begin'))
        if self.optSearchRefNum.getState() == 1:
            self.btnReplace.Label = theLocale.getText(
                "Replace with Example")
            self.btnReplaceAll.Label = theLocale.getText(
                "Replace All")
            app.setUpdateExamples(False)
            userVars.store("SearchFor", "RefNum")
            self.chkStartFromBeginning.setState(True)
        else:
            self.btnReplace.Label = theLocale.getText(
                "Update Example")
            self.btnReplaceAll.Label = theLocale.getText(
                "Update All")
            app.setUpdateExamples(True)
            userVars.store("SearchFor", "Existing")
            self.chkStartFromBeginning.setState(False)


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm, app):
        self.mainForm = mainForm
        self.app = app
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @dutil.log_event_handler_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        logger.debug(util.funcName('begin'))
        self.dlgCtrls.enableDisable(self.app, self.mainForm.userVars)

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "InsertEx":
            self.mainForm.insertEx()
        elif event.ActionCommand == "FindNext":
            self.mainForm.findNext()
        elif event.ActionCommand == "Replace":
            self.mainForm.replace()
        elif event.ActionCommand == "ReplaceAll":
            self.mainForm.replaceAll()
        elif event.ActionCommand == "Close":
            self.mainForm.dlgClose()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showPhonologyDlg, showGrammarDlg
