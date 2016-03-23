# -*- coding: Latin-1 -*-
#
# This file created Oct 26 2012 by Jim Kornelsen
#
# 09-Apr-13 JDK  Initialize some user variables for Calc dialogs.
# 15-Apr-13 JDK  Vars for DlgApplyConv use LTw_ prefix.
# 05-Jul-13 JDK  Option to use Flex citation field for phonemic.
# 23-Jul-15 JDK  Refactor generateList().
# 25-Aug-15 JDK  Catch DataNotFoundError.

"""
Make Word List in Calc.

This module exports:
    WordList
"""
import logging
import re

from lingt.access.calc.spreadsheet_reader import CalcFileReader
from lingt.access.calc.wordlist_io import WordlistIO
from lingt.access.text.sfm_reader import SFM_Reader
from lingt.access.writer.textsearch import TextSearchSettings
from lingt.access.writer.doc_reader import DocReader
from lingt.access.writer.uservars import Prefix, UserVars
from lingt.access.xml.interlin_reader import InterlinReader
from lingt.access.xml.phon_reader import PhonReader
from lingt.access.xml.words_reader import WordsReader
from lingt.app import exceptions
from lingt.app import fileitemlist
from lingt.app import lingex_structs
from lingt.app.wordlist_structs import WordInList, ColumnOrder
from lingt.ui.messagebox import MessageBox
from lingt.ui.progressbar import ProgressBar, ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.app.wordlist")

class WordList:

    def __init__(self, writerUnoObjs, fileItems, columnOrder, userVars):
        self.unoObjs = writerUnoObjs
        self.fileItems = fileItems    # FileItemList of WordListFileItem
        self.columnOrder = columnOrder
        self.userVars = userVars
        self.msgbox = MessageBox(self.unoObjs)
        self.words = []
        self.progressBar = None

    def generateList(self, punctToRemove, outputToCalc=True):
        """Harvest words from various files.
        If outputToCalc is True, then output a word list in Calc.
        """
        logger.debug(util.funcName('begin'))
        all_words_read = []
        self.progressBar = ProgressBar(self.unoObjs, "Reading...")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        progressRange = ProgressRange(
            ops=len(self.fileItems), pbar=self.progressBar)
        try:
            for fileItemIndex, fileItem in enumerate(self.fileItems):
                try:
                    new_words = self._harvestWords(fileItem)
                    all_words_read.extend(new_words)
                    logger.debug("Word count: %d", len(all_words_read))
                except (exceptions.DataNotFoundError,
                        exceptions.FileAccessError) as exc:
                    self.msgbox.displayExc(exc)
                progressRange.update(fileItemIndex)
            self.progressBar.updateFinishing()
        finally:
            self.progressBar.close()
        self.progressBar = ProgressBar(self.unoObjs, "Sorting...")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        try:
            splitByWhitespace = True
            if len(self.fileItems) > 0:
                splitByWhitespace = self.fileItems[0].splitByWhitespace
            self.words = organizeList(
                all_words_read, punctToRemove, splitByWhitespace,
                self.progressBar)
            self.progressBar.updateFinishing()
        finally:
            self.progressBar.close()
        if self.words or len(self.fileItems) == 0:
            if outputToCalc:
                self.progressBar = ProgressBar(
                    self.unoObjs, "Generating List...")
                self.progressBar.show()
                self.progressBar.updateBeginning()
                try:
                    self._generateCalcList()
                    self.progressBar.updateFinishing()
                finally:
                    self.progressBar.close()
            else:
                self.msgbox.display("Found %d words.", len(self.words))
        else:
            self.msgbox.display("Did not find any words for the list.")

    def _harvestWords(self, fileItem):
        """Harvest words from the specified file."""
        fileType = fileItem.filetype  # short variable name
        logger.debug(util.funcName(args=fileType))
        words = []
        if fileType in WordsReader.supportedNames():
            reader = WordsReader(fileItem, self.unoObjs)
            words = reader.read()
        elif fileType in SFM_Reader.supportedNames():
            reader = SFM_Reader(fileItem, self.unoObjs)
            words = reader.read()
        elif fileType in InterlinReader.supportedNames():
            config = fileitemlist.InterlinInputSettings(self.userVars)
            config.showMorphemeBreaks = True
            config.separateMorphColumns = True
            lingExFileItem = fileitemlist.LingExFileItem(self.userVars)
            lingExFileItem.filepath = fileItem.filepath
            config.fileList.addItem(lingExFileItem)
            reader = InterlinReader(self.unoObjs, self.userVars, config)
            words = reader.grabWords(fileItem.dataFields)
        elif fileType in PhonReader.supportedNames():
            config = lingex_structs.PhonInputSettings(self.userVars)
            config.filepath = fileItem.filepath
            config.phoneticWS = fileItem.writingSystem
            config.isLexemePhonetic = True
            phonUserVars = UserVars(
                Prefix.PHONOLOGY, self.unoObjs.document, logger)
            if phonUserVars.get("FlexLexeme") == 'phonemic':
                config.isLexemePhonetic = False
            reader = PhonReader(self.unoObjs, self.userVars, config)
            words = reader.grabWords(fileItem.dataFields)
        elif fileType in DocReader.supportedNames():
            matchesLimit = TextSearchSettings().loadMatchLimit(self.userVars)
            reader = DocReader(fileItem, self.unoObjs, matchesLimit)
            words = reader.read()
        elif fileType in CalcFileReader.supportedNames():
            reader = CalcFileReader(self.unoObjs)
            reader.setFileConfig(fileItem)
            words = reader.read()
        return words


    def _generateCalcList(self):
        """Generate list in calc."""
        listOutput = WordlistIO(self.unoObjs, self.columnOrder)
        listOutput.outputList(self.words, self.progressBar)
        msgbox = listOutput.getMsgbox()  # for Calc spreadsheet

        ## Copy some user vars for the Spelling component.

        userVarsSp = UserVars(
            Prefix.SPELLING, self.unoObjs.document, logger)
        varname = "HasSettings"
        userVarsSp.store(varname, self.userVars.get(varname))
        columnOrderSp = ColumnOrder(userVarsSp)
        columnOrderSp.sortOrder = self.columnOrder.sortOrder
        columnOrderSp.storeUserVars()

        # Initialize some user vars for Calc dialogs.  We do this here
        # to reset properly if a new word list is made.
        self.userVars.store("ConvSourceColumn",
                            self.columnOrder.getColLetter('colWord'))
        self.userVars.store("ConvTargetColumn",
                            self.columnOrder.getColLetter('colConv1'))
        userVarsSp.store("CurrentRow", "")
        msgbox.display("Made list of %d words.", len(self.words))


def organizeList(wordList, punctToRemove, splitByWhitespace, progressBar):
    """All types of words are likely to be harvested.
    Clean up and organize the list.
    """
    # split by whitespace
    for word_read in wordList[:]:   # iterate over a copy
        text = word_read.text
        text = text.strip()
        if re.search(r'\s', text):
            text_parts = re.split(r'\s+', text)
            if not splitByWhitespace:
                text_parts = [" ".join(text_parts)]
            for i, part in enumerate(text_parts):
                if i == 0:
                    word_read.text = part
                else:
                    newWord = WordInList()
                    newWord.text = part
                    newWord.source = word_read.source
                    newWord.isCorrect = word_read.isCorrect
                    newWord.correction = word_read.correction
                    wordList.append(newWord)
    logger.debug("Word count: %d", len(wordList))
    progressBar.updatePercent(40)

    # remove outer punctuation
    punctToRemove = re.sub(r"\s+", "", punctToRemove)
    logger.debug("punctToRemove %r", punctToRemove)
    for word_read in wordList:
        word_read.text = word_read.text.strip()  # remove whitespace
        word_read.text = word_read.text.strip(punctToRemove)
        #logger.debug("text is now '%s'", word_read.text)
    progressBar.updatePercent(60)

    # group equal words
    unique_words = dict()
    for word_read in wordList:
        text = word_read.text
        if not text:
            continue
        if text in unique_words:
            word = unique_words[text]
        else:
            word = WordInList()
            word.text = text
            word.isCorrect = word_read.isCorrect
            word.correction = word_read.correction
            unique_words[text] = word
        word.occurrences += 1
        if word_read.source in word.sources:
            word.sources[word_read.source] += 1
        else:
            word.sources[word_read.source] = 1
    logger.debug("Word count: %d", len(unique_words))

    # sort
    progressBar.updatePercent(80)
    sorted_words = []
    for text in sorted(unique_words.keys()):
        sorted_words.append(unique_words[text])
    logger.debug("Word count: %d", len(sorted_words))
    return sorted_words

