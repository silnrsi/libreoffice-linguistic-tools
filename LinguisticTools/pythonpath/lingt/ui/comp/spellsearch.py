# -*- coding: Latin-1 -*-
#
# This file created Dec 7 2012 by Jim Kornelsen
#
# 30-Jan-13 JDK  Call from Writer and find Calc doc, instead of vice versa.
# 20-Mar-13 JDK  Incorporate "Quick Replace" into this dialog.
# 27-Mar-13 JDK  Add "Current Spreadsheet" button.
# 15-Apr-13 JDK  Fixed bug: Send locale obj to app layer, not locale name.
# 19-Apr-13 JDK  Get all locales, not just those available for spelling.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 15-Jul-15 JDK  Use CheckerSettings class from App layer.

"""
Settings for making spelling changes in Writer.

This module exports:
    showDlg()
"""
import uno
import unohelper
import logging
import operator
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.writer import styles
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc.spellingchecks import SpellingChecker, CheckerSettings
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
from lingt.utils import util
from lingt.utils.letters import Letters
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgspellsearch")


def showDlg(ctx=uno.getComponentContext()):
    logger.debug("----showSearchDlg-------------------------------------------")
    writerUnoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")
    dlg = DlgSpellingSearch(writerUnoObjs)
    dlg.showDlg()

class DlgSpellingSearch:
    """Main class for this dialog."""

    def __init__(self, writerUnoObjs):
        self.unoObjs = writerUnoObjs
        USERVAR_PREFIX = "LTsp_"  # LinguisticTools Spelling variables
        self.userVars = uservars.UserVars(
            USERVAR_PREFIX, writerUnoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)
        self.app = SpellingChecker(self.unoObjs, self.userVars)
        self.localeList = []
        self.paraStyleNames = []
        self.charStyleNames = []
        self.searchOnClose = False
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgSpellSearch")
        if not dlg:
            return
        self.evtHandler = DlgEventHandler(self)
        try:
            self.dlgCtrls = DlgControls(
                self.unoObjs, dlg, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        logger.debug("Getting styles...")
        styleNames = styles.getListOfStyles('ParagraphStyles', self.unoObjs)
        self.paraStyleNames = dict(styleNames)
        paraStyleDispNames = tuple([dispName for dispName, name in styleNames])
        styleNames = styles.getListOfStyles('CharacterStyles', self.unoObjs)
        self.charStyleNames = dict(styleNames)
        charStyleDispNames = tuple([dispName for dispName, name in styleNames])
        self.localeList = list(theLocale.LANG_CODES.items())
        self.localeList.sort(key=operator.itemgetter(1))  # sort by lang name
        localeNames = [tupl[1] for tupl in self.localeList]
        self.dlgCtrls.loadValues(
            self.userVars, paraStyleDispNames, charStyleDispNames, localeNames)
        self.enableDisable()

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        dlg.dispose()
        if self.searchOnClose:
            self.app.doSearch()

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        enabled = False
        if self.dlgCtrls.optSpellcheck.getState() == 1:
            enabled = True
        self.dlgCtrls.txtAffixes.getModel().Enabled = enabled
        self.dlgCtrls.lblAffixes.getModel().Enabled = enabled
        self.dlgCtrls.lblAffixes2.getModel().Enabled = enabled

    def useCurrent(self):
        """Use current Calc spreadsheet."""
        openDocs = self.unoObjs.getOpenDocs(util.UnoObjs.DOCTYPE_CALC)
        if len(openDocs) == 0:
            self.msgbox.display("No spreadsheet is open.")
            return
        url = openDocs[0].document.getURL()
        if not url:
            self.msgbox.display("Please save the spreadsheet first.")
            return
        syspath = uno.fileUrlToSystemPath(url)
        self.dlgCtrls.fileWordList.setText(syspath)

    def closeAndSearch(self):
        logger.debug("Closing and Searching...")
        try:
            self.getFormResults()
            self.searchOnClose = True
            self.dlgClose()
        except exceptions.ChoiceProblem as exc:
            self.msgbox.displayExc(exc)

    def getFormResults(self):
        """Reads form fields and sets user vars and app.config."""
        logger.debug(util.funcName('begin'))
        config = CheckerSettings()
        config.filepath = self.dlgCtrls.fileWordList.getText()
        self.userVars.store("WordListFile", config.filepath)

        if self.dlgCtrls.optApplyCorrections.getState() == 1:  # checked
            config.whichTask = 'ApplyCorrections'
        elif self.dlgCtrls.optSpellcheck.getState() == 1:  # checked
            config.whichTask = 'SpellCheck'
        self.userVars.store("WhichTask", config.whichTask)

        searchConfig = config.searchConfig  # shorthand name
        config.whichScope = dutil.whichSelected(
            self.dlgCtrls.radiosWhichScope)
        if config.whichScope == 'Language':
            for code, name in self.localeList:
                if name == self.dlgCtrls.listLocale.getSelectedItem():
                    searchConfig.lang = code
        elif config.whichScope == 'Font':
            searchConfig.fontName = self.dlgCtrls.comboFont.getText()
            self.userVars.store('Font', searchConfig.fontName)
            searchConfig.fontType = dutil.whichSelected(
                self.dlgCtrls.radiosFontType)
            self.userVars.store('FontType', searchConfig.fontType)
        elif config.whichScope == 'ParaStyle':
            displayName = self.dlgCtrls.comboParaStyle.getText()
            if displayName in self.paraStyleNames:
                searchConfig.style = self.paraStyleNames[displayName]
            else:
                searchConfig.style = displayName
        elif config.whichScope == 'CharStyle':
            displayName = self.dlgCtrls.comboCharStyle.getText()
            if displayName in self.charStyleNames:
                searchConfig.style = self.charStyleNames[displayName]
            else:
                searchConfig.style = displayName
        elif config.whichScope == 'SFMs':
            searchConfig.SFMs = self.dlgCtrls.txtSFM.getText()
        self.userVars.store("WhichScope", config.whichScope)
        searchConfig.loadMatchLimit(self.userVars)

        ctrls = [
            (self.dlgCtrls.comboParaStyle, "ParaStyle"),
            (self.dlgCtrls.comboCharStyle, "CharStyle"),
            (self.dlgCtrls.comboFont, "Font"),
            (self.dlgCtrls.txtSFM, "SFM_Markers"),
            (self.dlgCtrls.txtAffixes, "Affixes"),
            (self.dlgCtrls.txtPunct, "Punctuation")]
        for ctrl in ctrls:
            control, varname = ctrl
            self.userVars.store(varname, control.getText())

        self.userVars.store(
            "Language", self.dlgCtrls.listLocale.getSelectedItem())
        self.userVars.store(
            "MatchCase", str(self.dlgCtrls.chkMatchCase.getState()))
        config.matchCase = (self.dlgCtrls.chkMatchCase.getState() == 1)
        config.punctuation = self.dlgCtrls.txtPunct.getText()

        config.verify()
        config.setAffixes(self.dlgCtrls.txtAffixes.getText())
        self.app.setConfig(config)
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.fileWordList = dutil.getControl(dlg, "fileWordList")
        self.optApplyCorrections = dutil.getControl(dlg, "optApplyCorrections")
        self.optSpellcheck = dutil.getControl(dlg, "optSpellcheck")
        self.optWholeDoc = dutil.getControl(dlg, "optWholeDoc")
        self.optLocale = dutil.getControl(dlg, "optLanguage")
        self.optParaStyle = dutil.getControl(dlg, "optParaStyle")
        self.optCharStyle = dutil.getControl(dlg, "optCharStyle")
        self.optFont = dutil.getControl(dlg, "optFont")
        self.optSFMs = dutil.getControl(dlg, "optSFM")
        self.optFontTypeWestern = dutil.getControl(dlg, "optFontTypeWestern")
        self.optFontTypeComplex = dutil.getControl(dlg, "optFontTypeCTL")
        self.optFontTypeAsian = dutil.getControl(dlg, "optFontTypeAsian")
        self.comboParaStyle = dutil.getControl(dlg, "comboParaStyle")
        self.comboCharStyle = dutil.getControl(dlg, "comboCharStyle")
        self.comboFont = dutil.getControl(dlg, "comboFont")
        self.listLocale = dutil.getControl(dlg, "listboxLocale")
        self.txtSFM = dutil.getControl(dlg, "txtSFM")
        self.txtAffixes = dutil.getControl(dlg, "txtAffixes")
        self.lblAffixes = dutil.getControl(dlg, "lblAffixes")
        self.lblAffixes2 = dutil.getControl(dlg, "lblAffixes2")
        self.txtPunct = dutil.getControl(dlg, "txtPunctuation")
        self.chkMatchCase = dutil.getControl(dlg, "chkMatchCase")
        btnUseCurrent = dutil.getControl(dlg, "btnCurrentSpreadsheet")
        btnSearch = dutil.getControl(dlg, "btnSearch")
        btnCancel = dutil.getControl(dlg, "btnCancel")

        btnUseCurrent.setActionCommand("UseCurrent")
        btnSearch.setActionCommand("Close_and_Search")
        btnCancel.setActionCommand("Cancel")
        for ctrl in (btnUseCurrent, btnSearch, btnCancel):
            ctrl.addActionListener(self.evtHandler)

        self.radiosFontType = [
            dutil.RadioTuple(self.optFontTypeWestern, 'Western'),
            dutil.RadioTuple(self.optFontTypeComplex, 'Complex'),
            dutil.RadioTuple(self.optFontTypeAsian, 'Asian')]
        self.radiosWhichScope = [
            dutil.RadioTuple(self.optWholeDoc, 'WholeDoc'),
            dutil.RadioTuple(self.optLocale, 'Language'),
            dutil.RadioTuple(self.optFont, 'Font'),
            dutil.RadioTuple(self.optParaStyle, 'ParaStyle'),
            dutil.RadioTuple(self.optCharStyle, 'CharStyle'),
            dutil.RadioTuple(self.optSFMs, 'SFMs')]

    def loadValues(self, userVars, paraStyleDispNames, charStyleDispNames,
                   localeNames):
        logger.debug(util.funcName('begin'))

        ## Option buttons

        whichTask = userVars.get("WhichTask")
        if whichTask == "ApplyCorrections":
            self.optApplyCorrections.setState(True)
        elif whichTask == "SpellCheck":
            self.optSpellcheck.setState(True)

        dutil.selectRadio(self.radiosWhichScope, userVars.get('WhichScope'))
        dutil.selectRadio(self.radiosFontType, userVars.get('FontType'))

        if userVars.getInt("MatchCase") == 1:
            self.chkMatchCase.setState(True)

        ## Combo box lists

        logger.debug("Populating font and styles lists")
        dutil.fill_list_ctrl(
            self.comboParaStyle, paraStyleDispNames, userVars.get("ParaStyle"))
        dutil.fill_list_ctrl(
            self.comboCharStyle, charStyleDispNames, userVars.get("CharStyle"))
        dutil.fill_list_ctrl(
            self.comboFont, styles.getListOfFonts(self.unoObjs),
            userVars.get("Font"))
        selectedValue = ""
        varname = "Language"
        if not userVars.isEmpty(varname):
            selectedValue = userVars.get(varname)
        dutil.fill_list_ctrl(self.listLocale, localeNames, selectedValue)
        logger.debug("Finished populating font and styles lists.")

        ## Other fields

        self.fileWordList.setText(userVars.get("WordListFile"))

        varname = "SFM_Markers"
        if userVars.isEmpty(varname):
            defaultCtrlText = "\\tx \\mb"
            userVars.store(varname, defaultCtrlText)
            userVarVal = defaultCtrlText
        else:
            userVarVal = userVars.get(varname)
        self.txtSFM.setText(userVarVal)

        varname = 'Affixes'
        if not userVars.isEmpty(varname):
            self.txtAffixes.setText(userVars.get(varname))

        varname = 'Punctuation'
        if userVars.isEmpty(varname):
            punct = u" ".join(Letters.PUNCTUATION)
            userVars.store(varname, punct)
        else:
            punct = userVars.get(varname)
        self.txtPunct.setText(punct)

        self.addRemainingListeners()

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        self.optApplyCorrections.addItemListener(self.evtHandler)
        self.optSpellcheck.addItemListener(self.evtHandler)


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm

    @dutil.log_event_handler_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        logger.debug(util.funcName('begin'))
        self.mainForm.enableDisable()

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "UseCurrent":
            self.mainForm.useCurrent()
        elif event.ActionCommand == "Cancel":
            logger.debug("Action command was Cancel")
            self.mainForm.dlgClose()
            return
        elif event.ActionCommand == "Close_and_Search":
            self.mainForm.closeAndSearch()
        else:
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
