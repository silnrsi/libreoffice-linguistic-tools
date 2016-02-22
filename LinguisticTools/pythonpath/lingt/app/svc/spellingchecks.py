# -*- coding: Latin-1 -*-
#
# This file created March 7 2013 by Jim Kornelsen
#
# 17-Apr-13 JDK  Split words by whitespace, then remove punctuation.
# 08-May-13 JDK  Suggest only words of the same case as the word found.
# 15-Jul-15 JDK  Added CheckerSettings class.
# 23-Jul-15 JDK  Added GoodList and WorkAsker classes.

"""
Checks a document or list for spelling corrections.
Uses classes in spellingcomparisons.py for some logic.

This module exports:
    CheckerSettings
    SpellingChecker
    SpellingStepper
"""
import copy
import logging
import re
from grantjenks.tribool import Tribool

from lingt.access.calc import spreadsheet_reader
from lingt.access.calc.spreadsheet_output import SpreadsheetOutput
from lingt.access.calc.wordlist_io import WordlistIO
from lingt.access.writer.textchanges import FindAndReplace
from lingt.access.writer.textsearch import TextSearch, TextSearchSettings
from lingt.access.writer.traveler import RangeJumper
from lingt.app import exceptions
from lingt.app.svc import spellingchanges
from lingt.app.svc.spellingcomparisons import SpellingSuggestions
from lingt.app.wordlist_structs import ColumnOrder
from lingt.ui.dep.spellreplace import DlgSpellingReplace
from lingt.ui.messagebox import MessageBox, FourButtonDialog
from lingt.ui.progressbar import ProgressBar
from lingt.utils import letters
from lingt.utils import util

logger = logging.getLogger("lingt.app.spellingchecks")

class CheckerSettings:
    """Settings for SpellingChecker class."""

    def __init__(self):
        # These attributes should be set from an external class.
        self.filepath = ""
        self.whichTask = ""
        self.whichScope = ""
        self.punctuation = ""
        self.matchCase = False
        self.searchConfig = TextSearchSettings()
        # These attributes are set from within this class.
        self.prefixes = []
        self.suffixes = []

    def verify(self):
        """Verify that settings are acceptable."""
        logger.debug(util.funcName('begin'))
        if (not self.filepath or not self.filepath.lower().endswith(
                (".ods", ".sxc", ".xls", ".xlsx"))):
            raise exceptions.ChoiceProblem(
                "Please specify a word list file.  To make a new empty "
                "list, go to Word List and Spelling and then save the "
                "spreadsheet file.")
        if not self.whichTask:
            raise exceptions.LogicError("No task was specified.")
        if not self.whichScope:
            raise exceptions.LogicError("No scope was specified.")
        if self.whichScope == 'Language' and not self.searchConfig.lang:
            raise exceptions.ChoiceProblem("Please select a language name.")
        if self.whichScope == 'ParaStyle' and not self.searchConfig.style:
            raise exceptions.ChoiceProblem(
                "Please select a scope paragraph style.")
        if self.whichScope == 'CharStyle' and not self.searchConfig.style:
            raise exceptions.ChoiceProblem(
                "Please select a scope character style.")
        if self.whichScope == 'Font' and not self.searchConfig.fontName:
            raise exceptions.ChoiceProblem("Please select a scope font.")
        if self.whichScope == 'SFMs' and not self.searchConfig.SFMs:
            raise exceptions.ChoiceProblem("Please specify SFMs.")
        logger.debug(util.funcName('end'))

    def setAffixes(self, affixString):
        """Set list of prefixes and suffixes."""
        self.prefixes = []
        self.suffixes = []
        affixes = affixString.split()
        for affix in affixes:
            if affix.startswith("-"):
                self.suffixes.append(affix.lstrip("-"))
            elif affix.endswith("-"):
                self.prefixes.append(affix.rstrip("-"))
            else:
                self.prefixes.append(affix)
                self.suffixes.append(affix)


def getTokens(delimitedStr):
    """Split into tokens by white space.
    Will return an array with even elements as words (i.e. 0,2,4...),
    and odd elements as the white space delimiters.
    Element 0 will be empty if the string starts with delimiters.
    """
    tokens = re.split("(\\s+)", delimitedStr)  # split by whitespace
    if not tokens[-1]:
        tokens.pop()  # remove the empty final element
    return tokens

class SpellingChecker:
    """Traverse words in a Writer document to check and make spelling
    corrections.  This is similar in concept to a traditional spell checker.
    Calls DlgSpellingReplace from the UI layer.
    """
    def __init__(self, writerUnoObjs, userVars):
        self.unoObjs = writerUnoObjs
        self.msgbox = MessageBox(self.unoObjs)
        self.userVars = userVars
        self.goodList = GoodList(self.msgbox)
        self.wordAsker = WordAsker(self.unoObjs, self.goodList)
        self.config = None
        self.numChanges = 0

    def setConfig(self, newConfig):
        """Param should be of type CheckerSettings."""
        self.config = newConfig
        self.wordAsker.setConfig(newConfig)

    def doSearch(self):
        """Get text ranges and then check those ranges for words.
        Navigate to each word (perhaps using punctuation list) and
        verify each word against the word list.
        """
        logger.debug(util.funcName('begin'))
        try:
            self.readWordList()
        except (exceptions.FileAccessError, exceptions.DocAccessError) as exc:
            self.msgbox.display(
                "Error reading file %s", self.config.filepath)
            return
        rangesFound = self.getRanges()
        self.numChanges = 0
        try:
            for txtRange in rangesFound:
                self.changeTextRange(txtRange)
            if self.config.whichTask == 'ApplyCorrections':
                plural = "" if self.numChanges == 1 else "s"
                self.msgbox.display(
                    "Made %d correction%s.", self.numChanges, plural)
            else:
                self.msgbox.display("Spell check finished.")
        except exceptions.UserInterrupt:
            pass
        except exceptions.DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")
        except exceptions.RangeError as exc:
            self.msgbox.displayExc(exc)
        finally:
            self.wordAsker.cleanup()

    def changeTextRange(self, txtRange):
        rangeJumper = RangeJumper(self.unoObjs)
        rangeJumper.setTextRange(txtRange)
        rangeTokens = getTokens(rangeJumper.getString())
        tokenNum = -2   # because the loop starts by += 2
        while True:
            tokenNum += 2   # tokens are in pairs: word, delim
            logger.debug("Token '%d' of %d", tokenNum, len(rangeTokens))
            if tokenNum >= len(rangeTokens):
                break
            word = rangeTokens[tokenNum].strip(self.config.punctuation)
            wordLower = self.goodList.firstLower(word)
            wordNoAffix = self.wordAsker.removeAffixes(wordLower)
            suspect = True
            if not word:
                suspect = False
            elif word.isdigit() or word.isspace():
                suspect = False
            elif wordLower in self.goodList or wordNoAffix in self.goodList:
                suspect = False
            elif wordLower in self.wordAsker.wordsToIgnore:
                suspect = False
            if self.config.whichTask == 'ApplyCorrections':
                suspect = wordLower in self.goodList.changeDict
            if suspect:
                logger.debug("Word '%s' is suspect", word)
                try:
                    rangeJumper.selectWord(
                        "".join(rangeTokens[:tokenNum]),
                        rangeTokens[tokenNum])
                except exceptions.RangeError:
                    if self.msgbox.displayOkCancel(
                            "Missed word '%s'.  Keep going?", word):
                        continue
                    else:
                        raise exceptions.UserInterrupt()
                if self.wordAsker.handleWord(
                        word, rangeTokens, tokenNum, rangeJumper):
                    self.numChanges += 1
                    rangeTokens = getTokens(rangeJumper.getString())
                    tokensBefore = getTokens(rangeJumper.getStringBefore())
                    tokenNum = len(tokensBefore)
                    tokenNum -= tokenNum % 2  # make sure it's even

    def readWordList(self):
        """Read word list from Calc.
        Sets self.changeDict if applying corrections.
        """
        fileReader = spreadsheet_reader.CalcFileReader(self.unoObjs)
        fileReader.loadDoc(self.config.filepath)
        self.goodList.setCalcUnoObjs(fileReader.calcUnoObjs)
        columnOrder = ColumnOrder(self.userVars)
        columnOrder.loadUserVars()
        if self.config.whichTask == 'SpellCheck':
            logger.debug("Reading good list.")
            columnLetter = columnOrder.getColLetter('colWord')
            wordListReader = fileReader.getSpreadsheetReader()
            wordList = wordListReader.getColumnStringList(
                columnLetter, skipFirstRow=True)
            self.goodList.setGoodList(
                wordList, self.config.matchCase, columnLetter)
        else:
            logger.debug("Reading change list.")
            changeList = spellingchanges.getChangeList(
                fileReader.calcUnoObjs, columnOrder)
            for oldVal, newVal in changeList:
                self.goodList.changeDict[
                    self.goodList.firstLower(oldVal)] = newVal

    def getRanges(self):
        progressBar = ProgressBar(self.unoObjs, "Finding text...")
        progressBar.show()
        progressBar.updateBeginning()
        textSearch = TextSearch(self.unoObjs, progressBar)
        textSearch.setConfig(self.config.searchConfig)
        try:
            if self.config.whichScope == 'WholeDoc':
                textSearch.scopeWholeDocTraverse()
            elif self.config.whichScope == 'Selection':
                textSearch.scopeSelection()
            elif self.config.whichScope == 'Language':
                textSearch.scopeLocale()
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
            progressBar.updateFinishing()
        except exceptions.MessageError as exc:
            raise exc
        finally:
            progressBar.close()
        return textSearch.getRanges()


class GoodList:
    """List of words that are correctly spelled."""
    def __init__(self, msgbox):
        self.suggestions = SpellingSuggestions(msgbox)
        self.wordList = []
        self.insensitiveList = []  # case insensitive (unless matchCase)
        self.matchCase = False
        self.columnLetter = ""
        self.calcUnoObjs = None
        # used instead of a good list if applying corrections
        self.changeDict = {}

    def setCalcUnoObjs(self, calcUnoObjs):
        self.calcUnoObjs = calcUnoObjs

    def setGoodList(self, newList, matchCase, columnLetter):
        """Sets most of the attributes of this class."""
        self.wordList = newList
        self.matchCase = matchCase
        self.columnLetter = columnLetter
        self.suggestions.setList(newList)
        self.loadInsensitiveList()

    def add(self, wordSimplified):
        self.wordList.append(wordSimplified)
        self.suggestions.setList(self.wordList)
        self.loadInsensitiveList()
        spreadsheetOutput = SpreadsheetOutput(self.calcUnoObjs)
        spreadsheetOutput.outputToColumn(
            self.columnLetter, self.wordList)

    def loadInsensitiveList(self):
        if self.matchCase:
            self.insensitiveList = self.wordList
            return
        self.insensitiveList = self.wordList[:]
        for i, word in enumerate(self.wordList):
            wordLower = self.firstLower(word)
            if wordLower != word:
                self.insensitiveList[i] = wordLower

    def firstLower(self, wordText):
        """
        Sets the initial character to lower case.
        Returns True if a change was made.
        """
        if self.matchCase or not wordText:
            return wordText
        c = wordText[0]
        if c in letters.CASE_CAPITALS:
            # change first letter
            i = letters.CASE_CAPITALS.index(c)
            wordText = letters.CASE_LOWER[i] + wordText[1:]
            return wordText
        return wordText

    def __contains__(self, word):
        return word in self.insensitiveList


def getContext(tokens, wordTokenNum):
    CONTEXT_LEN = 10   # probably use an even number
    contextBegin = wordTokenNum - CONTEXT_LEN
    contextEnd = wordTokenNum + CONTEXT_LEN
    if contextBegin < 0:
        contextBegin = 0
    return "".join(tokens[contextBegin:contextEnd])

class WordAsker:
    """Handles a particular word according to user feedback."""
    def __init__(self, unoObjs, goodList):
        self.unoObjs = unoObjs
        self.goodList = goodList
        self.dlgReplace = None  # type spellreplace.DlgSpellingReplace
        self.msgboxFour = FourButtonDialog(self.unoObjs)
        self.rangeJumper = None
        self.config = None
        self.wordsToIgnore = set()
        self.askEach = True
        self.punctBefore = ""
        self.punctAfter = ""

    def setConfig(self, newConfig):
        """Param should be of type CheckerSettings."""
        self.config = newConfig

    def handleWord(self, wordText, tokens, wordTokenNum, rangeJumper):
        """Returns True if a change was made."""
        self.rangeJumper = rangeJumper
        self.separatePunct(tokens[wordTokenNum])
        if self.config.whichTask == 'ApplyCorrections':
            return self.applyCorrection(wordText)
        else:
            return self.checkSpelling(
                wordText, getContext(tokens, wordTokenNum))

    def checkSpelling(self, wordText, context):
        suggestList = self.goodList.suggestions.getSuggestions(wordText)
        if not self.config.matchCase:
            ## Suggest only words of the same case as the word found.
            #  Non-roman characters will not be changed.
            firstChar = wordText[:1]
            if firstChar.isupper():
                suggestList = util.uniqueList(
                    [s.capitalize() for s in suggestList])
            elif firstChar.islower():
                suggestList = util.uniqueList(
                    [s.lower() for s in suggestList])
        if not self.dlgReplace:
            self.dlgReplace = DlgSpellingReplace(self.unoObjs)
            self.dlgReplace.makeDlg()
        self.dlgReplace.setContents(wordText, suggestList, context)
        self.dlgReplace.doExecute()
        action, changeTo = self.dlgReplace.getResults()
        if action == 'Ignore':
            # just keep going
            return False
        elif action == 'IgnoreAll':
            self.wordsToIgnore.add(self.goodList.firstLower(wordText))
            return False
        elif action == 'Change':
            self.rangeJumper.changeString(self.addPunct(changeTo))
            return True
        elif action == 'ChangeAll':
            self.rangeJumper.changeString(self.addPunct(changeTo))
            replacer = FindAndReplace(self.unoObjs, False)
            replacer.replace(wordText, changeTo)
            return True
        elif action == 'Add':
            self.goodList.add(self.removeAffixes(wordText))
            return False
        # user probably pressed Close or x'd out of the dialog
        raise exceptions.UserInterrupt()

    def applyCorrection(self, wordText):
        """Returns True if a change was made."""
        newWord = self.goodList.changeDict[self.goodList.firstLower(wordText)]
        if self.askEach:
            result = self.msgboxFour.display(
                "Make this change?  (%s -> %s)", wordText, newWord)
            if result == 'yes':
                pass
            elif result == 'no':
                return False
            elif result == 'yesToAll':
                self.askEach = False
            else:
                raise exceptions.UserInterrupt()
        self.rangeJumper.changeString(self.addPunct(newWord))
        return True

    def separatePunct(self, wordWithPunct):
        """Separate punctuation from a word.
        Sets self.punctBefore and self.punctAfter.
        """
        withoutLPunct = wordWithPunct.lstrip(self.config.punctuation)
        withoutRPunct = wordWithPunct.rstrip(self.config.punctuation)
        # These will just be "" if the word does not have punctuation.
        self.punctBefore = wordWithPunct[:-len(withoutLPunct)]
        self.punctAfter = wordWithPunct[len(withoutRPunct):]

    def addPunct(self, word):
        """Add to a word whatever punctuation was found."""
        return self.punctBefore + word + self.punctAfter

    def removeAffixes(self, wordText):
        for prefix in self.config.prefixes:
            if wordText.startswith(prefix):
                wordText = wordText[len(prefix):]
        for suffix in self.config.suffixes:
            if wordText.endswith(suffix):
                wordText = wordText[:-len(suffix)]
        return wordText

    def cleanup(self):
        if self.dlgReplace:
            self.dlgReplace.doDispose()
        # reset in case we use this class again later
        self.askEach = True


class SpellingStepper:
    """Step through each row in a word list to check for spelling."""

    def __init__(self, calcUnoObjs, userVars):
        self.unoObjs = calcUnoObjs
        self.userVars = userVars
        self.msgbox = MessageBox(self.unoObjs)
        self.suggestions = SpellingSuggestions(self.msgbox)
        self.suggListSet = False
        self.wantSuggestions = True
        self.currentRow = -1
        self.datalist = []  # List of wordlist_structs.WordInList items.
        self.columnOrder = None

    def loadData(self):
        self.columnOrder = ColumnOrder(self.userVars)
        self.columnOrder.loadUserVars()

        wordlistIO = WordlistIO(self.unoObjs, self.columnOrder)
        self.datalist = wordlistIO.readList()
        self.setSuggestionList()
        return len(self.datalist)

    def gotoRow(self, rowNum):
        """Return copy of WordInList item of that row."""
        self.currentRow = rowNum
        return copy.deepcopy(self.currentRowData())

    def setSuggestionList(self):
        if not self.wantSuggestions:
            self.suggListSet = False
            return
        wordStrings = []
        for wordData in self.datalist:
            if (wordData.isCorrect is not Tribool('False')
                    and not wordData.correction):
                wordStrings.append(wordData.text)
        self.suggestions.setList(wordStrings)
        self.suggListSet = True

    def getSuggestions(self, listToIgnore):
        if not self.suggListSet:
            self.setSuggestionList()
        wordData = self.currentRowData()
        suggList = self.suggestions.getSuggestions(wordData.text)

        ## Remove duplicate words
        wordData = self.currentRowData()
        for wordText in listToIgnore + [wordData.text]:
            if wordText in suggList:
                suggList.remove(wordText)
        return suggList

    def setIsCorrect(self, newVal):
        """:param newVal: type Tribool"""
        logger.debug("%s %r %s", util.funcName('begin'), newVal, type(newVal))
        outputter = SpreadsheetOutput(self.unoObjs)
        wordData = self.currentRowData()
        wordData.isCorrect = newVal
        try:
            outputter.outputString(
                self.columnOrder.getColLetter('colOk'), self.currentRow,
                wordData.isCorrect_str())
        except exceptions.DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")
        self.setSuggestionList()
        logger.debug(util.funcName('end'))

    def setCorrection(self, newText):
        outputter = SpreadsheetOutput(self.unoObjs)
        wordData = self.currentRowData()
        wordData.correction = newText
        try:
            outputter.outputString(
                self.columnOrder.getColLetter('colChange'), self.currentRow,
                newText)
        except exceptions.DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")

    def currentRowData(self):
        """Data starts on the second row of the Calc spreadsheet."""
        return self.datalist[self.currentRow - 2]

