"""
Settings for making spelling changes in Writer.

This module exports:
    showDlg()
"""
import logging
import operator

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.access.writer import styles
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.svc import spellingchecks
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgSpellSearch as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import letters
from lingt.utils import util
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
        self.userVars = uservars.UserVars(
            uservars.Prefix.SPELLING, writerUnoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)
        self.app = spellingchecks.SpellingChecker(self.unoObjs, self.userVars)
        self.localeList = []
        self.paraStyleNames = []
        self.charStyleNames = []
        self.searchOnClose = False
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
        logger.debug("Getting styles...")
        styleNames = styles.getListOfStyles('ParagraphStyles', self.unoObjs)
        self.paraStyleNames = dict(styleNames)
        paraStyleDispNames = tuple(dispName for dispName, name in styleNames)
        styleNames = styles.getListOfStyles('CharacterStyles', self.unoObjs)
        self.charStyleNames = dict(styleNames)
        charStyleDispNames = tuple(dispName for dispName, name in styleNames)
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
        config = spellingchecks.CheckerSettings()
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
        searchConfig.load_userVars(self.userVars)

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
        config.matchCase = self.dlgCtrls.chkMatchCase.getState() == 1
        config.punctuation = self.dlgCtrls.txtPunct.getText()

        varname = 'NormForm'
        if self.userVars.isEmpty(varname):
            config.normForm = spellingchecks.DEFAULT_NORM_FORM
            self.userVars.store(varname, config.normForm)
        else:
            config.normForm = self.userVars.get(varname)

        config.verify()
        config.setAffixes(self.dlgCtrls.txtAffixes.getText())
        self.app.setConfig(config)
        logger.debug(util.funcName('end'))


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.fileWordList = ctrl_getter.get(_dlgdef.FILE_WORD_LIST)
        self.optApplyCorrections = ctrl_getter.get(
            _dlgdef.OPT_APPLY_CORRECTIONS)
        self.optSpellcheck = ctrl_getter.get(_dlgdef.OPT_SPELLCHECK)
        self.optWholeDoc = ctrl_getter.get(_dlgdef.OPT_WHOLE_DOC)
        self.optLocale = ctrl_getter.get(_dlgdef.OPT_LANGUAGE)
        self.optParaStyle = ctrl_getter.get(_dlgdef.OPT_PARA_STYLE)
        self.optCharStyle = ctrl_getter.get(_dlgdef.OPT_CHAR_STYLE)
        self.optFont = ctrl_getter.get(_dlgdef.OPT_FONT)
        self.optSFMs = ctrl_getter.get(_dlgdef.OPT_SFM)
        self.optFontTypeWestern = ctrl_getter.get(
            _dlgdef.OPT_FONT_TYPE_WESTERN)
        self.optFontTypeComplex = ctrl_getter.get(_dlgdef.OPT_FONT_TYPE_CTL)
        self.optFontTypeAsian = ctrl_getter.get(_dlgdef.OPT_FONT_TYPE_ASIAN)
        self.comboParaStyle = ctrl_getter.get(_dlgdef.COMBO_PARA_STYLE)
        self.comboCharStyle = ctrl_getter.get(_dlgdef.COMBO_CHAR_STYLE)
        self.comboFont = ctrl_getter.get(_dlgdef.COMBO_FONT)
        self.listLocale = ctrl_getter.get(_dlgdef.LISTBOX_LOCALE)
        self.txtSFM = ctrl_getter.get(_dlgdef.TXT_SFM)
        self.txtAffixes = ctrl_getter.get(_dlgdef.TXT_AFFIXES)
        self.lblAffixes = ctrl_getter.get(_dlgdef.LBL_AFFIXES)
        self.lblAffixes2 = ctrl_getter.get(_dlgdef.LBL_AFFIXES2)
        self.txtPunct = ctrl_getter.get(_dlgdef.TXT_PUNCTUATION)
        self.chkMatchCase = ctrl_getter.get(_dlgdef.CHK_MATCH_CASE)
        btnUseCurrent = ctrl_getter.get(_dlgdef.BTN_CURRENT_SPREADSHEET)
        btnSearch = ctrl_getter.get(_dlgdef.BTN_SEARCH)
        btnCancel = ctrl_getter.get(_dlgdef.BTN_CANCEL)

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
            punct = " ".join(letters.PUNCTUATION)
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

    @evt_handler.log_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        logger.debug(util.funcName('begin'))
        self.mainForm.enableDisable()

    @evt_handler.log_exceptions
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
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (showDlg,)
