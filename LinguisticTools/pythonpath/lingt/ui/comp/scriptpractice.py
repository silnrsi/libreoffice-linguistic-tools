# -*- coding: Latin-1 -*-
#
# This file created Jun 28 2011 by Jim Kornelsen
#
# 10-Aug-11 JDK  Don't go to practice if no script was selected.
# 16-Nov-12 JDK  Use DlgWordList to load words from files.
# 27-Feb-13 JDK  Use list(dict.keys()) as required by python 3.3
# 28-Feb-13 JDK  Default to Latin script.
# 19-Apr-13 JDK  Update text fields with any corrections.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.
# 15-Jul-15 JDK  Refactor App.ScriptPractice into three classes.
# 15-Aug-15 JDK  Checkbox instead of buttons for known fonts.
# 13-Feb-17 JDK  Normalize data.

"""
Script Practice dialog.

This module exports:
    showDlg()
"""
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener
from com.sun.star.uno import RuntimeException


from lingt.access.writer import uservars
from lingt.app.svc import scriptpractice
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgScriptPractice as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.comp.wordlist import DlgWordList
from lingt.utils import unicode_data
from lingt.utils import util
from lingt.utils.fontsize import FontSize
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgscriptpractice")


def showDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger.debug("----showDlg()----------------------------------------------")
    unoObjs = util.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgScriptPractice(unoObjs)
    dlg.showDlg()

class DlgScriptPractice:
    """Main class for this dialog."""

    # which dialog step (which view)
    STEP_SETTINGS = 1
    STEP_PRACTICE = 2

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        uservars.SettingsDocPreparer(
            uservars.Prefix.SCRIPT_PRACTICE, unoObjs).prepare()
        self.userVars = uservars.UserVars(
            uservars.Prefix.SCRIPT_PRACTICE, unoObjs.document, logger)
        self.msgbox = MessageBox(unoObjs)
        self.script = scriptpractice.Script(self.unoObjs)
        self.questions = scriptpractice.PracticeQuestions(
            self.unoObjs, self.script)
        self.stats = scriptpractice.Stats()
        self.wordList = []
        self.whichSource = ""
        self.step = self.STEP_SETTINGS
        self.dlg = None
        self.dlgCtrls = None
        self.evtHandler = None
        self.dlgClose = None

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        self.dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not self.dlg:
            return
        ctrl_getter = dutil.ControlGetter(self.dlg)
        self.evtHandler = DlgEventHandler(
            self.userVars, self, self.script, self.questions)
        self.dlgClose = self.dlg.endExecute
        self.dlgCtrls = DlgControls(
            ctrl_getter, self.evtHandler, self.script, self.dlgClose,
            self.msgbox)
        self.dlg.getModel().Step = self.step
        self.evtHandler.setCtrls(self.dlgCtrls)
        self.dlgCtrls.loadValues(self.userVars, self.questions)

        ## Display the dialog

        self.dlg.execute()
        if self.step == self.STEP_SETTINGS:
            self.getFormResults()
        self.dlg.dispose()

    def resetChars(self):
        logger.debug(util.funcName('begin'))
        self.script.setCharsetFromScript()
        self.dlgCtrls.txtCharset.setText(self.script.getCharsetString())

    def chooseFiles(self):
        logger.debug(util.funcName('begin'))
        dlgFileList = DlgWordList(
            self.unoObjs, self.userVars.VAR_PREFIX)
        dlgFileList.dontDisposeWhenFinished()
        dlgFileList.showDlg()
        if not dlgFileList.getResult():
            dlgFileList.dlgDispose()
            return
        fileItems = dlgFileList.fileItems
        listApp = dlgFileList.app
        punctToRemove = dlgFileList.punctToRemove
        dlgFileList.dlgDispose()
        if len(fileItems) > 0:
            listApp.generateList(
                punctToRemove, dlgFileList.normForm, outputToCalc=False)
            self.wordList = listApp.words[:]

    def switch(self):
        logger.debug(util.funcName('begin'))
        if self.step == self.STEP_SETTINGS:
            self.getFormResults()
            if self.whichSource == "Generate":
                if not self.script.scriptNameIsSet():
                    self.msgbox.display("Please select a script.")
                    return
            elif self.whichSource == "Wordlist":
                if len(self.wordList) == 0:
                    self.msgbox.display(
                        "Please load a word list by clicking on the "
                        "Files... button.  When file settings are "
                        "finished, click Get words.")
                    return
            self.step = self.STEP_PRACTICE
            self.dlg.getModel().Step = self.step   # change the dialog
            self.dlgCtrls.btnSwitch.Label = theLocale.getText(
                "Back to Settings")
            self.dlg.setTitle(theLocale.getText("Script Practice"))
            self.dlgCtrls.btnNextWord.setFocus()
            self.showNextQuestion()
        elif self.step == self.STEP_PRACTICE:
            self.step = self.STEP_SETTINGS
            self.dlg.getModel().Step = self.step   # change the dialog
            self.dlgCtrls.btnSwitch.Label = theLocale.getText(
                "Go to Practice")
            self.dlg.setTitle(
                theLocale.getText("Script Practice - Settings"))
            self.resetStats()

    def resetStats(self):
        self.stats.resetStats()
        self.dlgCtrls.dispCorrect.setText("0")
        self.dlgCtrls.dispIncorrect.setText("0")
        self.dlgCtrls.dispNumWords.setText("0")
        self.dlgCtrls.dispAvgTime.setText("0")

    def getFormResults(self):
        """Reads form fields and sets app configuration."""
        logger.debug(util.funcName('begin'))
        config = scriptpractice.PracticeSettings()
        charsetString = self.dlgCtrls.txtCharset.getText()
        self.script.setCharsetFromInput(charsetString)
        self.userVars.store("CharSet", charsetString)
        self.questions.setConfig(config, self.wordList)

        ## Radio buttons and the corresponding combo box selection

        self.whichSource = ""
        if self.dlgCtrls.optGenerate.getState():
            self.whichSource = "Generate"
        elif self.dlgCtrls.optWordlist.getState():
            self.whichSource = "Wordlist"
        self.userVars.store("WhichSource", config.whichSource)
        config.whichSource = self.whichSource

        ## Font name and size

        fontName = self.dlgCtrls.comboFont.getText()
        if fontName == "(None)":
            fontName = None
        fontSize = FontSize(default=30.0)
        fontSize.loadCtrl(self.dlgCtrls.txtFontSize)
        self.userVars.store('Font', fontName)
        self.userVars.store('FontSize', fontSize.getString())
        self.userVars.store("Script", self.dlgCtrls.comboScript.getText())
        self.userVars.store(
            "OnlyKnownFonts", str(self.dlgCtrls.chkKnownFonts.getState()))

        ## Syllable and Word size

        strval = self.dlgCtrls.listSyllableSize.getSelectedItem()
        try:
            val = int(strval)
        except ValueError:
            val = 2
        if val < 1 or val > 3:
            val = 2
        config.syllableSize = val
        self.userVars.store("SyllableSize", str(val))

        strval = self.dlgCtrls.txtNumSyllables.getText()
        try:
            val = int(strval)
        except ValueError:
            val = 1
            self.dlgCtrls.txtNumSyllables.setText(str(val))
        if val < 1 or val > 9:
            val = 1
            self.dlgCtrls.txtNumSyllables.setText(str(val))
        config.numSyllables = val
        self.userVars.store("NumSyllables", str(val))

        strval = self.dlgCtrls.txtNumWords.getText()
        try:
            val = int(strval)
        except ValueError:
            val = 1
            self.dlgCtrls.txtNumWords.setText(str(val))
        if val < 1 or val > 50:
            val = 1
            self.dlgCtrls.txtNumWords.setText(str(val))
        config.numWords = val
        self.userVars.store("NumWords", str(val))
        logger.debug(util.funcName('end'))

    def showNextQuestion(self):
        logger.debug(util.funcName('begin'))
        nextQuestion = self.questions.getNextQuestion()
        self.dlgCtrls.txtQuestion.setText(nextQuestion)
        self.stats.newQuestion()
        self.prepareAnswerBox()
        logger.debug(util.funcName('end'))

    def prepareAnswerBox(self):
        self.dlgCtrls.txtAnswer.setText("")
        self.dlgCtrls.txtAnswer.getModel().BackgroundColor = \
            int("FFFFFF", 16)  # White
        self.dlgCtrls.txtAnswer.setEditable(True)
        self.dlgCtrls.txtAnswer.setFocus()

    def answerChanged(self):
        if self.questions.answerIsReady(self.dlgCtrls.txtAnswer.getText()):
            self.checkAnswer()

    def checkAnswer(self):
        """Determine if the answer is correct."""
        if self.questions.waitForSpace:
            given = self.dlgCtrls.txtAnswer.getText().rstrip()
            if given != self.dlgCtrls.txtAnswer.getText():
                # Reset the text without the newline so it doesn't look funny.
                # Warning: This line can cause a crash, but hopefully we avoid
                # it by the "if" statement.
                self.dlgCtrls.txtAnswer.setText(given)
        else:
            given = self.dlgCtrls.txtAnswer.getText()
        if self.questions.questionMatches(given):
            self.dlgCtrls.dispCorrect.setText(self.stats.answerCorrect())
            self.dlgCtrls.txtAnswer.getModel().BackgroundColor = \
                int("00CC00", 16)  # Green
            self.dlgCtrls.btnNextWord.setFocus()
        else:
            self.dlgCtrls.dispIncorrect.setText(self.stats.answerIncorrect())
            self.dlgCtrls.txtAnswer.getModel().BackgroundColor = \
                int("FF0000", 16)  # Red
            self.dlgCtrls.btnRetry.setFocus()
        self.dlgCtrls.dispNumWords.setText(self.stats.getTotalQuestions())
        self.dlgCtrls.dispAvgTime.setText(self.stats.getAvgTime())
        self.dlgCtrls.txtAnswer.setEditable(False)


class DlgControls:
    """Store dialog controls."""

    def __init__(self, ctrl_getter, evtHandler, script, dlgClose, msgbox):
        self.dlgClose = dlgClose
        self.msgbox = msgbox
        self.evtHandler = evtHandler
        self.script = script
        self.charsetAlreadySet = False

        self.lblCharset = ctrl_getter.get(_dlgdef.LBL_CHARSET)
        self.txtCharset = ctrl_getter.get(_dlgdef.TXT_CHARSET)
        self.txtQuestion = ctrl_getter.get(_dlgdef.TXT_QUESTION)
        self.txtAnswer = ctrl_getter.get(_dlgdef.TXT_ANSWER)
        self.optGenerate = ctrl_getter.get(_dlgdef.OPT_GENERATE)
        self.optWordlist = ctrl_getter.get(_dlgdef.OPT_WORDLIST)
        self.optCheckAtLastChar = ctrl_getter.get(
            _dlgdef.OPT_CHECK_AT_LAST_CHAR)
        self.optCheckTypeSpace = ctrl_getter.get(_dlgdef.OPT_CHECK_TYPE_SPACE)
        self.comboScript = ctrl_getter.get(_dlgdef.CMBX_SCRIPT)
        self.lblScript = ctrl_getter.get(_dlgdef.LBL_SCRIPT)
        self.comboFont = ctrl_getter.get(_dlgdef.CMBX_FONT)
        self.listSyllableSize = ctrl_getter.get(_dlgdef.LIST_SYLLABLE_SIZE)
        self.lblSyllableSize = ctrl_getter.get(_dlgdef.LBL_SYLLABLE_SIZE)
        self.dispNumWords = ctrl_getter.get(_dlgdef.LBL_DISP_NUMBER_OF_WORDS)
        self.dispCorrect = ctrl_getter.get(_dlgdef.LBL_DISP_CORRECT)
        self.dispIncorrect = ctrl_getter.get(_dlgdef.LBL_DISP_INCORRECT)
        self.dispAvgTime = ctrl_getter.get(_dlgdef.LBL_DISP_AVG_TIME)
        self.txtNumSyllables = ctrl_getter.get(_dlgdef.TXT_NUM_SYLLABLES)
        self.lblNumSyllables = ctrl_getter.get(_dlgdef.LBL_NUM_SYLLABLES)
        self.txtNumWords = ctrl_getter.get(_dlgdef.TXT_NUM_WORDS)
        self.lblNumWords = ctrl_getter.get(_dlgdef.LBL_NUM_WORDS)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_FONT_SIZE)
        self.btnResetChars = ctrl_getter.get(_dlgdef.BTN_RESET_CHARACTERS)
        self.btnFiles = ctrl_getter.get(_dlgdef.BTN_FILES)
        self.chkKnownFonts = ctrl_getter.get(_dlgdef.CHK_KNOWN_FONTS)
        self.btnSwitch = ctrl_getter.get(_dlgdef.BTN_SWITCH)
        self.btnRetry = ctrl_getter.get(_dlgdef.BTN_RETRY)
        self.btnNextWord = ctrl_getter.get(_dlgdef.BTN_NEXT_WORD)
        btnResetStats = ctrl_getter.get(_dlgdef.BTN_RESET_STATS)
        btnExit = ctrl_getter.get(_dlgdef.BTN_EXIT)

        self.btnResetChars.setActionCommand("ResetChars")
        self.btnFiles.setActionCommand("ChooseFiles")
        self.btnSwitch.setActionCommand("Switch")
        self.btnNextWord.setActionCommand("NextWord")
        self.btnRetry.setActionCommand("Retry")
        btnResetStats.setActionCommand("ResetStats")
        btnExit.setActionCommand("Exit")
        for ctrl in (self.btnResetChars, self.btnFiles,
                     self.btnSwitch, self.btnNextWord,
                     self.btnRetry, btnResetStats, btnExit):
            ctrl.addActionListener(self.evtHandler)

    def loadValues(self, userVars, questions):
        logger.debug(util.funcName('begin'))
        if not userVars.isEmpty("CharSet"):
            self.script.setCharsetFromInput(userVars.get("CharSet"))
            self.charsetAlreadySet = True

        ## Option buttons

        whichSource = userVars.get("WhichSource")
        if whichSource == "Generate":
            self.optGenerate.setState(True)
        elif whichSource == "Wordlist":
            self.optWordlist.setState(True)

        whenToCheck = userVars.get("WhenToCheck")
        if whenToCheck == "Space":
            self.optCheckTypeSpace.setState(True)
            questions.waitForSpace = True
        elif whenToCheck == "LastChar":
            self.optCheckAtLastChar.setState(True)
            questions.waitForSpace = False

        ## Combo box lists

        logger.debug("Populating script and fonts lists")
        varname = "OnlyKnownFonts"
        if userVars.isEmpty(varname):
            self.chkKnownFonts.setState(True)
        else:
            self.chkKnownFonts.setState(userVars.getInt(varname))

        scriptNames = sorted(list(unicode_data.SCRIPT_LETTERS.keys()))
        selectedValue = userVars.get("Script")
        if not selectedValue:
            selectedValue = "LATIN"
        dutil.fill_list_ctrl(self.comboScript, scriptNames, selectedValue)
        self.changeScript()

        selectedValue = userVars.get("Font")
        if selectedValue:
            self.comboFont.setText(selectedValue)
        self.changeFont()

        ## Other fields

        logger.debug("Loading other field values from user vars")
        syllableSize = userVars.getInt("SyllableSize")
        if syllableSize < 1 or syllableSize > 3:
            syllableSize = 2
        self.listSyllableSize.selectItem(str(syllableSize), True)

        numSyllables = userVars.getInt("NumSyllables")
        if numSyllables < 1 or numSyllables > 9:
            numSyllables = 1
        self.txtNumSyllables.setText(str(numSyllables))

        numWords = userVars.getInt("NumWords")
        if numWords < 1 or numWords > 50:
            numWords = 1
        self.txtNumWords.setText(str(numWords))

        fontSize = FontSize(default=30.0)
        fontSize.loadUserVar(userVars, 'FontSize')
        fontSize.changeCtrlVal(self.txtFontSize)
        self.changeFontSize()

        self.enableDisable()

        self.addRemainingListeners()
        logger.debug(util.funcName('end'))

    def addRemainingListeners(self):
        """We have already added action listeners in __init__(),
        but we wait to add listeners for other types of controls because
        they could have side effects during loadValues().
        """
        for ctrl in (self.optGenerate, self.optWordlist,
                     self.optCheckAtLastChar, self.optCheckTypeSpace,
                     self.chkKnownFonts):
            ctrl.addItemListener(self.evtHandler)

        for ctrl in (self.comboScript, self.comboFont, self.txtFontSize,
                     self.txtAnswer):
            ctrl.addTextListener(self.evtHandler)

    def changeScript(self):
        self.script.setScriptName(self.comboScript.getText())
        if self.charsetAlreadySet:
            self.charsetAlreadySet = False
        else:
            self.script.setCharsetFromScript()
        logger.debug("txtCharset.setText BEFORE")
        try:
            charsetString = self.script.getCharsetString()
            # On some systems this causes a crash.
            # It may depend on which font is used.
            self.txtCharset.setText(charsetString)
        except RuntimeException as exc:
            # Sometimes a C++ exception will be caught here,
            # although often Office just crashes.
            logger.exception(exc)
            self.msgbox.displayExc(exc)
            self.dlgClose()
            return
        logger.debug("txtCharset.setText AFTER")
        self.setFontList()

    def setFontList(self):
        logger.debug(util.funcName())
        self.script.setOnlyKnownFonts(self.chkKnownFonts.getState())
        selectedValue = self.script.getDefaultFont(self.comboFont.getText())
        dutil.fill_list_ctrl(
            self.comboFont, self.script.getFontList(), selectedValue)

    def changeFont(self):
        fontName = self.comboFont.getText()
        if fontName == self.script.fallbackFontDisplay:
            fontName = " "
        for txctrl in (self.txtCharset, self.txtQuestion, self.txtAnswer):
            txctrl.getModel().FontName = fontName

    def changeFontSize(self):
        fontSize = FontSize(default=30.0)
        fontSize.loadCtrl(self.txtFontSize)
        for txctrl in (self.txtCharset, self.txtQuestion, self.txtAnswer):
            fontSize.changeCtrlProp(txctrl)

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        for control in (self.lblCharset,
                        self.txtCharset,
                        self.lblSyllableSize,
                        self.listSyllableSize,
                        self.lblNumSyllables,
                        self.txtNumSyllables,
                        self.lblNumWords,
                        self.txtNumWords,
                        self.btnResetChars):
            control.getModel().Enabled = self.optGenerate.getState()
        self.btnFiles.getModel().Enabled = self.optWordlist.getState()


class DlgEventHandler(XActionListener, XItemListener, XTextListener,
                      unohelper.Base):
    """Handles dialog events."""

    def __init__(self, userVars, mainForm, script, questions):
        self.mainForm = mainForm
        self.userVars = userVars
        self.script = script
        self.questions = questions
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @evt_handler.log_exceptions
    def itemStateChanged(self, itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName('begin'))
        src = itemEvent.Source
        if evt_handler.sameName(src, self.dlgCtrls.chkKnownFonts):
            self.dlgCtrls.setFontList()
            return
        if self.dlgCtrls.optCheckAtLastChar.getState():
            self.questions.waitForSpace = False
            self.userVars.store("WhenToCheck", "LastChar")
        elif self.dlgCtrls.optCheckTypeSpace.getState():
            self.questions.waitForSpace = True
            self.userVars.store("WhenToCheck", "Space")
        self.dlgCtrls.enableDisable()

    @evt_handler.log_exceptions
    def textChanged(self, textEvent):
        """XTextListener event handler."""
        src = textEvent.Source
        logger.debug("%s %s", util.funcName(), src.Model.Name)
        if evt_handler.sameName(src, self.dlgCtrls.txtAnswer):
            self.mainForm.answerChanged()
        elif evt_handler.sameName(src, self.dlgCtrls.comboScript):
            self.dlgCtrls.changeScript()
        elif evt_handler.sameName(src, self.dlgCtrls.comboFont):
            self.dlgCtrls.changeFont()
        elif evt_handler.sameName(src, self.dlgCtrls.txtFontSize):
            self.dlgCtrls.changeFontSize()
        else:
            logger.warning("unexpected source %s", src.Model.Name)

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "ResetChars":
            self.mainForm.resetChars()
        elif event.ActionCommand == "ChooseFiles":
            self.mainForm.chooseFiles()
        elif event.ActionCommand == "Switch":
            self.mainForm.switch()
        elif event.ActionCommand == "NextWord":
            self.mainForm.showNextQuestion()
        elif event.ActionCommand == "Retry":
            self.mainForm.prepareAnswerBox()
        elif event.ActionCommand == "ResetStats":
            self.mainForm.resetStats()
        elif event.ActionCommand == "Exit":
            logger.debug("Action command was Exit")
            self.mainForm.dlgClose()
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = showDlg,
