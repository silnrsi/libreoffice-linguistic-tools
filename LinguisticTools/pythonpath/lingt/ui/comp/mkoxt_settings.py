# -*- coding: Latin-1 -*-
#
# This file created April 26 2018 by Jim Kornelsen

"""
Dialog to call oxttools.makeoxt
https://github.com/silnrsi/oxttools

This module exports:
    showDlg()

"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener

from lingt.access.writer import uservars
from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common import filepicker
from lingt.ui.common.dlgdefs import DlgMkoxtSettings as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util
from oxttools.makeoxt import make as _mkoxt

logger = logging.getLogger("lingt.ui.dlgmkoxtsettings")

class MkoxtSettings(Syncable):
    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.langtag = ""
        self.outfile = ""
        self.word = ""  # word-forming punctuation list
        self.type = "west"  # script type
        self.font = ""
        self.langname = ""
        self.dict = ""
        self.affix = ""
        self.normalize = "NFC"
        self.version = ""
        self.dicttype = ""
        self.publisher = ""
        self.puburl = ""

    def loadUserVars(self):
        self.dict = self.userVars.get("WordList")
        self.langname = self.userVars.get("LangName")
        self.type = self.userVars.get("ScriptType")
        self.langtag = self.userVars.get("LangTag")
        self.outfile = self.userVars.get("Outfile")

    def storeUserVars(self):
        self.userVars.store("WordList", self.dict)
        self.userVars.store("LangName", self.langname)
        self.userVars.store("ScriptType", self.type)
        self.userVars.store("LangTag", self.langtag)
        self.userVars.store("Outfile", self.outfile)


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgMkoxtSettings(unoObjs)
    dlg.showDlg()

class DlgMkoxtSettings:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(self.unoObjs)
        self.userVars = uservars.UserVars(
            uservars.Prefix.MAKE_OXT, unoObjs.document, logger)
        self.settings = None
        self.runOnClose = False
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
            self.unoObjs, ctrl_getter, self.evtHandler, self.userVars)
        self.dlgCtrls.loadValues()

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.runOnClose:
            _mkoxt(self.settings, self.msgbox)
        dlg.dispose()

    def showFilePicker(self):
        logger.debug(util.funcName('begin'))
        OXT_EXT = ".oxt"
        extension = OXT_EXT
        defaultFilename = "MyLanguage" + extension
        filters = [
            ["OpenOffice Extension (%s)" % OXT_EXT, "*" + OXT_EXT]]
        filepath = filepicker.showFilePicker(
            self.unoObjs, True, filters, defaultFilename)
        logger.debug(repr(filepath))
        if filepath == "":
            logger.debug("No filepath specified.")
            return
        if not filepath.lower().endswith(extension):
            filepath = "{}{}".format(filepath, extension)
        self.dlgCtrls.txtOutfile.setText(filepath)
        logger.debug("set filepath to '%s'", filepath)

    def closeAndRun(self):
        logger.debug(util.funcName('begin'))
        #try:
        #    import lxml.etree as et
        #except ImportError:
        #    self.msgbox.display(
        #        "To use oxttools, the lxml python library must be installed.")
        #    self.dlgClose()
        #    return
        try:
            self.settings = self.dlgCtrls.getFormResults()
            self.runOnClose = True
            self.dlgClose()
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler, userVars):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler
        self.userVars = userVars

        self.fctlWordList = ctrl_getter.get(_dlgdef.FCTL_WORD_LIST)
        self.txtLangName = ctrl_getter.get(_dlgdef.TXT_LANG_NAME)
        self.listboxScriptType = ctrl_getter.get(_dlgdef.LISTBOX_SCRIPT_TYPE)
        self.txtLangTag = ctrl_getter.get(_dlgdef.TXT_LANG_TAG)
        self.txtOutfile = ctrl_getter.get(_dlgdef.TXT_OUTFILE)
        btnBrowse = ctrl_getter.get(_dlgdef.BTN_BROWSE)
        btnAdvancedOptions = ctrl_getter.get(_dlgdef.BTN_ADVANCED_OPTIONS)
        btnOK = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        ## Listeners

        btnBrowse.setActionCommand("ShowFilePicker")
        btnAdvancedOptions.setActionCommand("AdvancedOptions")
        btnOK.setActionCommand("Close_and_Run")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnBrowse, btnAdvancedOptions, btnOK, btnCancel):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self):
        settings = MkoxtSettings(self.userVars)
        settings.loadUserVars()
        self.fctlWordList.setText(settings.dict)
        self.txtLangName.setText(settings.langname)
        self.listboxScriptType.selectItem(settings.type, True)
        self.txtLangTag.setText(settings.langtag)
        self.txtOutfile.setText(settings.outfile)

    def getFormResults(self):
        """Reads form fields and returns settings.
        raises exceptions.ChoiceProblem
        """
        logger.debug(util.funcName('begin'))
        settings = MkoxtSettings(self.userVars)
        settings.dict = self.fctlWordList.getText()
        settings.langname = self.txtLangName.getText()
        settings.type = self.listboxScriptType.getSelectedItem()
        settings.langtag = self.txtLangTag.getText()
        settings.outfile = self.txtOutfile.getText()
        settings.storeUserVars()
        return settings


class DlgEventHandler(XActionListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "ShowFilePicker":
            self.mainForm.showFilePicker()
        elif event.ActionCommand == "AdvancedOptions":
            pass
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        elif event.ActionCommand == "Close_and_Run":
            self.mainForm.closeAndRun()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
