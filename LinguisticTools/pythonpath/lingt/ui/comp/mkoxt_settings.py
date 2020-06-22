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
import os

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XTextListener

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

SCRIPT_TYPES = [
    'west',
    'asian',
    'ctl',
    'rtl',
    'none'
    ]

class MkoxtSettings(Syncable):
    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.langtag = ""
        self.outfile = ""
        self.word = ""  # word-forming punctuation list
        self.type = ''
        self.font = ""
        self.langname = ""
        self.dict = ""
        self.affix = ""
        self.normalize = ''
        self.version = ""
        self.dicttype = ""
        self.publisher = ""
        self.puburl = ""

    def loadUserVars(self):
        self.langtag = self.userVars.get("LangTag")
        self.outfile = self.userVars.get("Outfile")
        self.word = self.userVars.get("WordFormingPunct")
        self.type = self.userVars.getWithDefault("ScriptType", 'west')
        self.font = self.userVars.get("Font")
        self.langname = self.userVars.get("LangName")
        self.dict = self.userVars.get("WordList")
        self.affix = self.userVars.get("AffixFile")
        self.normalize = self.userVars.getWithDefault("Normalize", 'NFC')
        self.version = self.userVars.getWithDefault("Version", "0.1")
        self.dicttype = self.userVars.get("DictType")
        self.publisher = self.userVars.get("Publisher")
        self.puburl = self.userVars.get("PublisherURL")

    def storeUserVars(self):
        self.userVars.store("LangTag", self.langtag)
        self.userVars.store("Outfile", self.outfile)
        self.userVars.store("WordFormingPunct", self.word)
        self.userVars.store("ScriptType", self.type)
        self.userVars.store("Font", self.font)
        self.userVars.store("LangName", self.langname)
        self.userVars.store("WordList", self.dict)
        self.userVars.store("AffixFile", self.affix)
        self.userVars.store("Normalize", self.normalize)
        self.userVars.store("Version", self.version)
        self.userVars.store("DictType", self.dicttype)
        self.userVars.store("Publisher", self.publisher)
        self.userVars.store("PublisherURL", self.puburl)


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
        uservars.SettingsDocPreparer(
            uservars.Prefix.MAKE_OXT, unoObjs).prepare()
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
        self.evtHandler.setCtrls(self.dlgCtrls)
        self.dlgCtrls.loadValues()

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.runOnClose:
            _mkoxt(self.settings, self.msgbox)
            filename = os.path.basename(self.settings.outfile)
            self.msgbox.display("%s finished." % filename)

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

        self.txtLangName = ctrl_getter.get(_dlgdef.TXT_LANG_NAME)
        self.txtOutfile = ctrl_getter.get(_dlgdef.TXT_OUTFILE)
        self.fctlWordList = ctrl_getter.get(_dlgdef.FCTL_WORD_LIST)
        self.listboxScriptType = ctrl_getter.get(_dlgdef.LISTBOX_SCRIPT_TYPE)
        self.txtLangTag = ctrl_getter.get(_dlgdef.TXT_LANG_TAG)
        self.txtWordFormingPunct = ctrl_getter.get(_dlgdef.TXT_WORD_FORMING_PUNCT)
        self.txtFont = ctrl_getter.get(_dlgdef.TXT_FONT)
        self.fctlAffix = ctrl_getter.get(_dlgdef.FCTL_AFFIX)
        self.optNormNFC = ctrl_getter.get(_dlgdef.OPT_NORM_NFC)
        self.optNormNFD = ctrl_getter.get(_dlgdef.OPT_NORM_NFD)
        self.optNormNone = ctrl_getter.get(_dlgdef.OPT_NORM_NONE)
        self.txtVersion = ctrl_getter.get(_dlgdef.TXT_VERSION)
        self.listDictType = ctrl_getter.get(_dlgdef.LIST_DICT_TYPE)
        self.txtPublisher = ctrl_getter.get(_dlgdef.TXT_PUBLISHER)
        self.txtPublisherURL = ctrl_getter.get(_dlgdef.TXT_PUBLISHER_URL)
        btnBrowse = ctrl_getter.get(_dlgdef.BTN_BROWSE)
        btnOK = ctrl_getter.get(_dlgdef.BTN_OK)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

        ## Listeners

        btnBrowse.setActionCommand("ShowFilePicker")
        btnOK.setActionCommand("Close_and_Run")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnBrowse, btnOK, btnCancel):
            ctrl.addActionListener(self.evtHandler)

        self.radiosNormalize = [
            dutil.RadioTuple(self.optNormNFC, 'NFC'),
            dutil.RadioTuple(self.optNormNFD, 'NFD'),
            dutil.RadioTuple(self.optNormNone, 'None')]

    def loadValues(self):
        settings = MkoxtSettings(self.userVars)
        settings.loadUserVars()
        self.txtLangName.setText(settings.langname)
        self.txtOutfile.setText(settings.outfile)
        self.fctlWordList.setText(settings.dict)
        self.listboxScriptType.selectItemPos(0, True)
        self.txtLangTag.setText(settings.langtag)
        self.txtWordFormingPunct.setText(settings.word)
        self.txtFont.setText(settings.font)
        self.fctlAffix.setText(settings.affix)
        dutil.selectRadio(self.radiosNormalize, settings.normalize)
        self.txtVersion.setText(settings.version)
        self.listDictType.selectItem(settings.dicttype, True)
        self.txtPublisher.setText(settings.publisher)
        self.txtPublisherURL.setText(settings.puburl)

        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.fctlWordList.addTextListener(self.evtHandler)

    def getFormResults(self):
        """Reads form fields and returns settings.
        raises exceptions.ChoiceProblem
        """
        logger.debug(util.funcName('begin'))
        settings = MkoxtSettings(self.userVars)
        settings.langname = self.txtLangName.getText()
        settings.outfile = self.txtOutfile.getText()
        settings.dict = self.fctlWordList.getText()
        settings.type = SCRIPT_TYPES[
            self.listboxScriptType.getSelectedItemPos()]
        settings.langtag = self.txtLangTag.getText()
        settings.word = self.txtWordFormingPunct.getText()
        settings.font = self.txtFont.getText()
        settings.affix = self.fctlAffix.getText()
        settings.normalize = dutil.whichSelected(self.radiosNormalize)
        settings.version = self.txtVersion.getText()
        settings.dicttype = self.listDictType.getSelectedItem()
        settings.publisher = self.txtPublisher.getText()
        settings.puburl = self.txtPublisherURL.getText()
        settings.storeUserVars()
        return settings

    def changeDictType(self):
        filename = self.fctlWordList.getText()
        if filename.endswith('.aff') :
            dicttype = 'hunspell'
        elif filename.endswith('.xml') :
            dicttype = 'pt'
        elif filename.endswith('.txt') :
            dicttype = 'text'
        self.listDictType.selectItem(dicttype, True)


class DlgEventHandler(XActionListener, XTextListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    def textChanged(self, textEvent):
        """XTextListener event handler."""
        logger.debug(util.funcName('begin'))
        src = textEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.fctlWordList):
            self.dlgCtrls.changeDictType()
        else:
            logger.warning("unexpected source %s", src.Model.Name)

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "ShowFilePicker":
            self.mainForm.showFilePicker()
        elif event.ActionCommand == "Cancel":
            self.mainForm.dlgClose()
        elif event.ActionCommand == "Close_and_Run":
            self.mainForm.closeAndRun()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
