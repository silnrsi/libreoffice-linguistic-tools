"""
Main script practice logic.

This module exports:
    Script
    PracticeSettings
    Stats
"""
import logging
import re
import random
import time

from lingt.access.writer import styles
from lingt.utils import letters
from lingt.utils import unicode_data
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.app.scriptpractice")

class Script:
    """Script and character set properties."""

    def __init__(self, unoObjs):
        self.scriptName = ""
        self.charset = {}
        self.allFonts = styles.getListOfFonts(unoObjs)
        self.fontList = []
        self.onlyKnownFonts = True
        theLocale.loadUnoObjs(unoObjs)
        self.fallbackFontDisplay = theLocale.getText("(Fallback Font)")

    def setScriptName(self, newName):
        logger.debug(util.funcName('begin', args=newName))
        self.scriptName = newName
        self.fontList = []

    def scriptNameIsSet(self):
        if self.scriptName:
            return True
        return False

    def init_charset(self):
        self.charset = {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "WF_Consonants" : [],
            "AnyConsonants" : []}

    def setCharsetFromScript(self):
        """Sets self.charset"""
        if self.scriptName not in unicode_data.SCRIPT_LETTERS:
            self.init_charset()
            return
        # reference
        self.charset = unicode_data.SCRIPT_LETTERS[self.scriptName]

    def setCharsetFromInput(self, inputString):
        """Sets self.charset from input from user."""
        self.init_charset()
        for char in inputString:
            if not char.isspace():
                if char in letters.LetterIndex:
                    lettertype = letters.LetterIndex[char]
                else:
                    lettertype = "AnyConsonants"
                self.charset[lettertype].append(char)

    def getCharsetString(self):
        allchars = []
        for charlist in self.charset.values():
            allchars += charlist
        allchars.sort()
        return "  ".join(allchars)

    def getVirama(self):
        return letters.VIRAMA.get(self.scriptName, "")

    def setOnlyKnownFonts(self, newVal):
        if self.onlyKnownFonts == newVal:
            return
        self.onlyKnownFonts = newVal
        self._setFontList()

    def getFontList(self):
        if not self.fontList:
            self._setFontList()
        return self.fontList

    def _setFontList(self):
        """Sets self.fontList"""
        listOfFonts = [self.fallbackFontDisplay]
        if self.onlyKnownFonts:
            self._getKnownScriptFonts()
            listOfFonts.extend(self._getKnownScriptFonts())
        else:
            listOfFonts.extend(self.allFonts)
        self.fontList = listOfFonts

    def _getKnownScriptFonts(self):
        """
        Return a list of names of fonts that contain the characters in the
        script, and that are in the system font list.
        """
        scriptFonts = []
        if self.scriptName in letters.SCRIPT_FONTS:
            scriptFonts.extend(letters.SCRIPT_FONTS[self.scriptName])
        for fontName, scripts in letters.FONT_SCRIPTS.items():
            for scrpt in scripts:
                if scrpt == self.scriptName:
                    scriptFonts.append(fontName)
        # Only keep fonts that are in the system font list
        scriptFonts = [fontName for fontName in scriptFonts
                       if fontName in self.allFonts]
        #scriptFonts.append(" ")   # use the fallback system font
        return scriptFonts

    def getDefaultFont(self, selectedValue=""):
        self.getFontList()
        if (selectedValue and selectedValue != self.fallbackFontDisplay
                and selectedValue in self.fontList):
            return selectedValue
        if len(self.fontList) > 1:
            return self.fontList[1]
        return self.fallbackFontDisplay


class PracticeSettings:
    def __init__(self):
        self.whichSource = 'Generate'
        self.numWords = 1
        self.numSyllables = 1
        self.syllableSize = 2


class PracticeQuestions:
    """Generate practice questions."""

    def __init__(self, unoObjs, script):
        self.unoObjs = unoObjs
        self.script = script
        theLocale.loadUnoObjs(unoObjs)
        self.config = None
        self.datalist = None
        self.questionString = ""
        self.waitForSpace = False
        random.seed()

    def setConfig(self, config, newList):
        """Config should be of type PracticeSettings."""
        self.config = config
        self.datalist = newList

    def getNextQuestion(self):
        logger.debug(util.funcName('begin'))
        self.questionString = ""
        if self.config.whichSource == 'Generate':
            self.generateQuestionString()
        elif self.config.whichSource == 'Wordlist':
            self.questionFromList()
        logger.debug("Question %r", self.questionString)
        return self.questionString

    def generateQuestionString(self):
        for i in range(0, self.config.numWords):
            for j in range(0, self.config.numSyllables):
                wordInitial = False
                if j == 0:
                    wordInitial = True
                wordFinal = False
                if j == self.config.numSyllables - 1:
                    wordFinal = True
                newSyllable = self.chooseSyllable(wordInitial, wordFinal)
                logger.debug("syllable %d = '%s'", j, newSyllable)
                if newSyllable:
                    self.questionString += newSyllable
                else:
                    return
            if i < self.config.numWords - 1:
                self.questionString += " "

    def chooseSyllable(self, wordInitial, wordFinal):
        """Make a syllable of up to three characters in length."""
        charset = self.script.charset
        firstcharset = charset["AnyVowels"] + charset["AnyConsonants"]
        if wordInitial:
            firstcharset += charset["WI_Vowels"] + charset["WI_Consonants"]
        if not firstcharset:
            self.questionString = theLocale.getText("(cannot make word)")
            return ""
        firstchar = random.choice(firstcharset)
        if self.script.getVirama() and not wordInitial:
            prevChar = self.questionString[-1:]  # preceding this syllable
            logger.debug("prevChar %s", prevChar)
            if (firstchar in charset["AnyConsonants"] and
                    prevChar in charset["AnyConsonants"]):
                # Insert virama in between two consonants
                logger.debug("Inserting virama")
                firstchar = self.script.getVirama() + firstchar
        if self.config.syllableSize <= 1:
            return firstchar

        singlefirstchar = firstchar[-1:]  # make sure it's only one character
        logger.debug("firstchar %s", singlefirstchar)
        if (singlefirstchar in charset["WI_Consonants"] or
                singlefirstchar in charset["AnyConsonants"]):
            secondcharset = (charset["DepVowels"] +
                             charset["AnyVowels"])
        else:
            secondcharset = list(charset["AnyConsonants"])  # copy
            if wordFinal:
                secondcharset += charset["WF_Consonants"]
        if len(secondcharset) == 0:
            return firstchar
        secondchar = random.choice(secondcharset)
        if (self.config.syllableSize <= 2 or
                secondchar in charset["WI_Consonants"] or
                secondchar in charset["WF_Consonants"] or
                secondchar in charset["AnyConsonants"]):
            return firstchar + secondchar

        thirdcharset = list(charset["AnyConsonants"])  # copy
        if wordFinal:
            thirdcharset += charset["WF_Consonants"]
        if len(thirdcharset) == 0:
            return firstchar + secondchar
        thirdchar = random.choice(thirdcharset)
        return firstchar + secondchar + thirdchar

    def questionFromList(self):
        logger.debug("questionFromList()")
        if len(self.datalist) == 0:
            self.questionString = theLocale.getText("(no words found)")
        else:
            word = random.choice(self.datalist)
            self.questionString = word.text

    def answerIsReady(self, answerString):
        """Returns True if the answer is ready to check.
        There is no need to check until it gets long enough.
        """
        if len(answerString) < len(self.questionString):
            logger.debug(
                "%s %s; not long enough yet", util.funcName(), False)
            return False
        if self.waitForSpace:
            if not re.search(r"\s$", answerString):   # ends with whitespace
                logger.debug("%s %s; no space yet", util.funcName(), False)
            isReady = len(answerString) > len(self.questionString)
            logger.debug("%s %s", util.funcName(), isReady)
            return isReady
        logger.debug("%s %s", util.funcName(), True)
        return True

    def questionMatches(self, answerString):
        result = answerString == self.questionString
        logger.debug("%s returns %s", util.funcName(), result)
        return result


class Stats:
    """For keeping score."""

    def __init__(self):
        self.totalQuestions = 0
        self.numCorrect = 0
        self.numIncorrect = 0
        self.startTime = 0
        self.avgTime = 0
        self.alreadyAnswered = False
        self.alreadyAveraged = False

    def newQuestion(self):
        self.alreadyAnswered = False
        self.alreadyAveraged = False
        self.startTime = time.time()

    def answerCorrect(self):
        if not self.alreadyAnswered:
            self.alreadyAnswered = True
            self.totalQuestions += 1
            self.numCorrect += 1
        return self.numCorrect

    def answerIncorrect(self):
        if not self.alreadyAnswered:
            self.alreadyAnswered = True
            self.totalQuestions += 1
            self.numIncorrect += 1
        return self.numIncorrect

    def getTotalQuestions(self):
        return self.totalQuestions

    def getAvgTime(self):
        if self.alreadyAveraged:
            return "%1.1f" % self.avgTime
        self.alreadyAveraged = True
        curTime = time.time()
        timedelta = curTime - self.startTime
        if self.totalQuestions == 1:
            self.avgTime = timedelta
        else:
            self.avgTime = (
                float(self.avgTime * (self.totalQuestions - 1) + timedelta)
                / self.totalQuestions)
        return "%1.1f" % self.avgTime

    def resetStats(self):
        self.totalQuestions = 0
        self.numCorrect = 0
        self.numIncorrect = 0
        self.avgTime = 0
