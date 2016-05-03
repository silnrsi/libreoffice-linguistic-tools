# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 29-Sep-10 JDK  Create style with font if not yet done.
# 21-Oct-10 JDK  Option for changing font without applying a style.
# 01-Nov-11 JDK  Use python SEC_wrapper instead of SEC C++ component.
# 29-Oct-12 JDK  To check results, throw exception rather than return false.
# 26-Nov-12 JDK  Option to ask before making each change.
# 04-Mar-13 JDK  Option to skip first row in Calc.
# 11-Mar-13 JDK  Don't save user vars here for options shown in dialog.
# 27-Apr-13 JDK  Remove testing functions.
# 15-Oct-15 JDK  Fixed bug: was checking whichScope when creating para style.

"""
Main data conversion logic.

This module exports:
    ConversionSettings
    DataConversion
"""
import logging
from com.sun.star.uno import RuntimeException

from lingt.access.sec_wrapper import SEC_wrapper
from lingt.access.calc.spreadsheet_output import SpreadsheetOutput
from lingt.access.calc.spreadsheet_reader import SpreadsheetReader
from lingt.access.writer.textchanges import TextChanger
from lingt.access.writer.textsearch import TextSearch, TextSearchSettings
from lingt.app import exceptions
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.progressbar import ProgressBar
from lingt.utils import util

logger = logging.getLogger("lingt.app.dataconversion")

class ConversionSettings:

    def __init__(self):
        self.whichScope = 'Font'
        self.searchConfig = TextSearchSettings()
        self.whichTarget = 'ParaStyle'
        self.targetStyle = ""
        self.targetFont = None  # type styles.FontDefStruct
        self.askEach = False


class DataConversion:
    """Main class for this module."""

    def __init__(self, docUnoObjs, userVars, styleFonts=None):
        """unoObjs needs to be for a writer doc if calling
        doConversions_writer(),
        and for a calc spreadsheet if calling doConversion_calc().
        Set styleFonts if calling setAndVerifyConfig(),
        which is probably only for the DlgBulkConv dialog.
        """
        self.unoObjs = docUnoObjs
        self.userVars = userVars
        self.styleFonts = styleFonts
        self.msgbox = MessageBox(self.unoObjs)
        self.secCall = SEC_wrapper(self.msgbox, userVars)
        self.config = None

    def selectConverter(self):
        """Returns SEC_wrapper.ConverterSettings object.
        Saves normalization value, since it is not configurable in the dialog.
        """
        logger.debug(util.funcName('begin'))
        try:
            self.secCall.pickConverter()
            logger.debug("Picked converter.")
        except exceptions.FileAccessError as exc:
            self.msgbox.displayExc(exc)
        logger.debug("Converter name '%s'", self.secCall.config.convName)
        self.secCall.config.storeUserVars()  # for normalize
        return self.secCall.config

    def setAndVerifyConverter(self, newConv):
        """Parameter should be of type SEC_wrapper.ConverterSettings.
        Call this method before calling one of the doConversion() methods.
        """
        ## Get the converter if not yet done

        if newConv.convName == "":
            raise exceptions.ChoiceProblem("Please select a converter.")
        if newConv.convName == "<No converter>":
            return
        if self.secCall.config != newConv:
            try:
                self.secCall.setConverter(newConv)
                logger.debug("Did set converter.")
            except exceptions.FileAccessError as exc:
                self.msgbox.displayExc(exc)
                self.secCall.config.convName = ""
                raise exceptions.ChoiceProblem(
                    "Please select the converter again.")

    def setAndVerifyConfig(self, newConfig):
        """Sets self.config from newConfig, which should be type
        ConversionSettings.
        Throws exceptions.ChoiceProblem if the choices are not acceptable.
        """
        logger.debug(util.funcName('begin'))
        if not self.styleFonts:
            raise exceptions.LogicError("Expected styleFonts to be set.")

        if not newConfig.whichScope:
            raise exceptions.ChoiceProblem("Please specify a scope.")
        if (newConfig.whichScope == 'ParaStyle'
                and not newConfig.searchConfig.style):
            raise exceptions.ChoiceProblem(
                "Please select a scope paragraph style.")
        if (newConfig.whichScope == 'CharStyle'
                and not newConfig.searchConfig.style):
            raise exceptions.ChoiceProblem(
                "Please select a scope character style.")
        if (newConfig.whichScope == 'Font'
                and not newConfig.searchConfig.fontName):
            raise exceptions.ChoiceProblem("Please select a scope font.")
        if (newConfig.whichScope == 'SFMs'
                and not newConfig.searchConfig.SFMs):
            raise exceptions.ChoiceProblem("Please specify SFMs.")

        if not newConfig.whichTarget:
            raise exceptions.ChoiceProblem("Please specify a target.")
        if (newConfig.whichTarget == 'ParaStyle'
                and not newConfig.targetStyle):
            raise exceptions.ChoiceProblem("Please select a target style.")
        if (newConfig.whichTarget == 'CharStyle'
                and not newConfig.targetStyle):
            raise exceptions.ChoiceProblem("Please select a target style.")
        if (newConfig.whichTarget == 'FontOnly'
                and not newConfig.targetFont.fontName):
            raise exceptions.ChoiceProblem("Please select a target font.")

        self.config = newConfig
        try:
            if newConfig.whichTarget == 'ParaStyle':
                self.styleFonts.setParaStyleWithFont(
                    newConfig.targetFont, newConfig.targetStyle)
            elif newConfig.whichTarget == 'CharStyle':
                self.styleFonts.setCharStyleWithFont(
                    newConfig.targetFont, newConfig.targetStyle)
        except RuntimeException as exc:
            logger.exception(exc)
            raise exceptions.StyleError(
                'Could not create style "%s".', newConfig.targetStyle)
        logger.debug(util.funcName('end'))

    def doConversions_writer(self):
        """For converting data in a Writer doc."""
        logger.debug(util.funcName('begin'))

        ## Start progress bar

        progressBar = ProgressBar(self.unoObjs, "Converting...")
        progressBar.show()
        progressBar.updateBeginning()

        ## Find the text ranges

        textSearch = TextSearch(self.unoObjs, progressBar)
        textSearch.setConfig(self.config.searchConfig)
        try:
            if self.config.whichScope == 'WholeDoc':
                textSearch.scopeWholeDoc()
            elif self.config.whichScope == 'Selection':
                textSearch.scopeSelection()
            elif self.config.whichScope == 'ParaStyle':
                textSearch.scopeParaStyle()
            elif self.config.whichScope == 'CharStyle':
                textSearch.scopeCharStyle()
            elif self.config.whichScope == 'Font':
                textSearch.scopeFont()
            elif self.config.whichScope == 'SFMs':
                textSearch.scopeSFMs()
            else:
                raise exceptions.LogicError(
                    "Unexpected value %s", self.config.whichScope)
        except (exceptions.RangeError, exceptions.LogicError) as exc:
            self.msgbox.displayExc(exc)
            progressBar.close()
            return
        rangesFound = textSearch.getRanges()

        if progressBar.getPercent() < 40:
            progressBar.updatePercent(40)

        ## Do the changes to those ranges

        textChanger = TextChanger(self.unoObjs, progressBar)
        if self.secCall.config.convName:
            textChanger.setConverterCall(self.secCall)
        if self.config.whichTarget == "ParaStyle":
            textChanger.setStyleToChange(
                "ParaStyleName", self.config.targetStyle)
        elif self.config.whichTarget == "CharStyle":
            textChanger.setStyleToChange(
                "CharStyleName", self.config.targetStyle)
        elif self.config.whichTarget == "FontOnly":
            textChanger.setFontToChange(self.config.targetFont)
        numChanges, numStyleChanges = textChanger.doChanges(
            rangesFound, self.config.askEach)

        progressBar.updateFinishing()
        progressBar.close()

        ## Display results

        paragraphsFound = len(rangesFound)
        if paragraphsFound == 0:
            self.msgbox.display("Did not find scope of change.")
        elif numChanges == 0:
            if numStyleChanges == 0:
                self.msgbox.display("No changes.")
            else:
                plural = "" if numStyleChanges == 1 else "s"
                    # add "s" if plural
                self.msgbox.display(
                    "No changes, but modified style of %d paragraph%s.",
                    numStyleChanges, plural)
        elif paragraphsFound == 1:
            plural = "" if numChanges == 1 else "s" # add "s" if plural
            self.msgbox.display("Made %d change%s.", numChanges, plural)
        else:
            plural = "" if numChanges == 1 else "s" # add "s" if plural
            self.msgbox.display(
                "Found %d paragraphs and made %d change%s.",
                paragraphsFound, numChanges, plural)

    def doConversions_calc(self, sourceCol, destCol, skipFirstRow):
        """For converting data in a Calc spreadsheet."""
        logger.debug(util.funcName('begin'))

        ## Start progress bar

        progressBar = ProgressBar(self.unoObjs, "Converting...")
        progressBar.show()
        progressBar.updateBeginning()

        ## Get list of words from source column
        #  (just strings are enough, no need for a special object)

        reader = SpreadsheetReader(self.unoObjs)
        try:
            inputList = reader.getColumnStringList(sourceCol, skipFirstRow)
        except exceptions.DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
            progressBar.close()
        if len(inputList) == 0:
            self.msgbox.display(
                "Did not find anything in column %s.", sourceCol)
            progressBar.close()
            return

        if progressBar.getPercent() < 40:
            progressBar.updatePercent(40)

        ## Convert

        outList = []
        problems = False
        numChanges = 0
        for inValue in inputList:
            try:
                outValue = self.secCall.convert(inValue)
                outList.append(outValue)
                if outValue != inValue:
                    numChanges += 1
            except exceptions.MessageError as exc:
                self.msgbox.displayExc(exc)
                problems = True
                outList.append("")
                break

        ## Output results

        outputter = SpreadsheetOutput(self.unoObjs)
        try:
            outputter.outputToColumn(destCol, outList, skipFirstRow)
        except exceptions.DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")

        progressBar.updateFinishing()
        progressBar.close()

        ## Display results

        if not problems:
            if numChanges == 0:
                self.msgbox.display("No changes.")
            else:
                self.msgbox.display("Successfully finished conversion.")

