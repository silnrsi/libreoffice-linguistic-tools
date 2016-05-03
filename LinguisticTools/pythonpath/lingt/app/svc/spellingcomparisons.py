# -*- coding: Latin-1 -*-
#
# This file created Nov 20 2012 by Jim Kornelsen
#
# 23-Feb-13 JDK  Fixed several basic suggestions problems.
# 28-Feb-13 JDK  Handle exception if Calc spreadsheet gets closed.
# 16-Jul-15 JDK  Use constructors instead of static factory functions.

"""
Logic for spelling comparisons.

This module exports:
    SpellingCharClasses
    SpellingSuggestions
"""
import logging
import os
from operator import itemgetter

from lingt.access.calc.spreadsheet_reader import SpreadsheetReader
from lingt.access.calc.spreadsheet_output import SpreadsheetOutput
from lingt.app import exceptions
from lingt.app.data.wordlist_structs import WordInList, ColumnOrder
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import letters
from lingt.utils import unicode_data
from lingt.utils import util

logger = logging.getLogger("lingt.app.spellingcomparisons")

def wordsFromStrings(stringList):
    """Create a list of WordInList objects from strings."""
    words = []
    for text in stringList:
        newWord = WordInList()
        newWord.text = text
        words.append(newWord)
    return words

class SpellingCharClasses:
    """Suggest spelling changes based on character classes."""

    def __init__(self, calcUnoObjs, userVars):
        self.unoObjs = calcUnoObjs
        self.userVars = userVars
        self.msgbox = MessageBox(self.unoObjs)
        self.script = ""
        self.charsComp = []  # lines of chars to compare
        self.datalist = None
        self.displayResults = True

    def setScript(self, newName):
        self.script = newName

    def getAvailableScriptKeys(self):
        if self.script not in unicode_data.SIMILAR_CHARS:
            return []
        charsDict = unicode_data.SIMILAR_CHARS[self.script]
        keys = list(charsDict.keys())
        if 'AnyConsonants' in unicode_data.SCRIPT_LETTERS[self.script]:
            keys.append('GEMIN')
        return keys

    def setCharCompFromScript(self, charCompOpts):
        """Sets self.charsComp"""
        logger.debug(util.funcName('begin', args=(charCompOpts,)))
        self.charsComp = []
        if self.script not in unicode_data.SIMILAR_CHARS:
            logger.debug("Did not find script '%s'", self.script)
            return
        charsDict = unicode_data.SIMILAR_CHARS[self.script]
        for key in charCompOpts:
            if key in charsDict:
                setList = charsDict[key]
                if len(setList) > 0:
                    setList.sort(key=itemgetter(0))
                    self.charsComp.extend(setList)
            elif key == 'GEMIN':
                if self.script in unicode_data.SCRIPT_LETTERS:
                    consList = unicode_data.SCRIPT_LETTERS[
                        self.script]['AnyConsonants']
                    gemList = []
                    for cons in consList:
                        if self.script in letters.VIRAMA:
                            virama = letters.VIRAMA[self.script]
                            gemChars = "".join([cons, virama, cons])
                        else:
                            gemChars = cons * 2
                        gemList.append([cons, gemChars])
                    self.charsComp.extend(gemList)

    def setCharCompFromInput(self, inputString):
        """Sets self.charsComp from input from user."""
        self.charsComp = []
        for line in inputString.splitlines():
            charlist = []
            for char in line:
                if not char.isspace():
                    charlist.append(char)
            self.charsComp.append(charlist)

    def getCharCompString(self):
        lines = list()
        for charlist in self.charsComp:
            lines.append("  ".join(charlist))
        return os.linesep.join(lines) + os.linesep

    def doChecks(self):
        """Check all words to see if they match by taking character classes
        into account.
        """
        logger.debug(util.funcName('begin'))
        columnOrder = ColumnOrder(self.userVars)
        columnOrder.loadUserVars()
        colLetter = columnOrder.getColLetter('colWord')

        reader = SpreadsheetReader(self.unoObjs)
        try:
            wordStrings = reader.getColumnStringList(
                colLetter, skipFirstRow=True)
        except exceptions.DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
            return
        words = wordsFromStrings(wordStrings)

        charSetList = []
        for charlist in self.charsComp:
            if len(charlist) < 2:
                # only useful to have at least two characters to compare
                continue
            charset = CharSet(charlist)
            # treat each similarity set as if it were an individual character
            wordChar = WordChar(charset, isCharset=True)
            charSetList.append(wordChar)

        numSimilarWords = compareAllWords(words, charSetList)

        similarWordsStrings = [word.similarWords_str() for word in words]
        colLetter = columnOrder.getColLetter('colSimilar')
        outputter = SpreadsheetOutput(self.unoObjs)
        try:
            outputter.outputToColumn(colLetter, similarWordsStrings)
        except exceptions.DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")

        if self.displayResults:
            if numSimilarWords == 0:
                self.msgbox.display("Did not find any similar words.")
            else:
                self.msgbox.display(
                    "Found %d similar words.", numSimilarWords)
        logger.debug(util.funcName('end'))


def subSuperString(s1, s2):
    """Return true if word is either a substring or a superstring.
    Two-letter words don't count, because for example "am" is a substring
    of "hamster" and "madam" and lots of other words.
    """
    if len(s1) > len(s2):
        # swap
        s1, s2 = s2, s1
    if len(s1) <= 2:
        return False
    return s1.lower() in s2.lower()

def levenshteinDistance(s1, s2):
    """Returns the edit distance of two strings.
    From http://rosettacode.org/wiki/Levenshtein_distance.
    """
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for index2, char2 in enumerate(s2):
        newDistances = [index2+1]
        for index1, char1 in enumerate(s1):
            if char1.lower() == char2.lower():
                newDistances.append(distances[index1])
            else:
                newDistances.append(
                    1 + min((distances[index1],
                             distances[index1+1],
                             newDistances[-1])))
        distances = newDistances
    return distances[-1]

class SpellingSuggestions:
    """Logic to find similar words based on edit distance."""

    def __init__(self, msgbox, limit=20):
        self.limit = limit
        self.msgbox = msgbox
        self.listSorted = []  # sorted by word
        self.listByLength = []  # sorted by length
        self.wordToFind = ""

    def setList(self, datalist):
        self.listSorted = datalist[:]
        try:
            self.listSorted = [word for word in self.listSorted
                               if word.strip() != ""]
        except AttributeError:
            self.msgbox.display("Error reading the list.")
            self.listSorted = []
        self.listSorted.sort()
        self.listByLength = sorted(self.listSorted, key=len)

    def getSuggestions(self, wordToFind):
        """The main function to get similar words.
        Returns a list.
        """
        self.wordToFind = wordToFind

        ## Sort list by most likely first.

        rank = {}
        self._compareBySameBeginning(rank)
        self._compareBySimilarLength(rank)
        rankings = [rank[word]
                    for word in self.listSorted]
        rankedList = sorted(zip(self.listSorted, rankings), key=itemgetter(1))

        ## Check edit distance starting with most likely candidates.

        superStrings, similarStrings = self._checkEditDistance(rankedList)
        suggestions = superStrings[:]
        for word, dummy in similarStrings:
            if word not in suggestions:
                suggestions.append(word)
        return suggestions[:self.limit]

    def _compareBySameBeginning(self, rank):
        """Words with same beginning are likely to be misspellings.
        Set rank values accordingly.
        """
        bestMatchingCount = 0
        firstMatchingIndex = 0
        lastMatchingIndex = 0
        for list_i, wordSorted in enumerate(self.listSorted):
            matchingCount = 0
            for list_j, char in enumerate(self.wordToFind.lower()):
                if (len(wordSorted) > list_j and
                        wordSorted[list_j].lower() == char):
                    matchingCount += 1
                else:
                    break
            if matchingCount > bestMatchingCount:
                firstMatchingIndex = list_i
                lastMatchingIndex = list_i
                bestMatchingCount = matchingCount
            elif matchingCount == bestMatchingCount:
                lastMatchingIndex = list_i
            elif matchingCount < bestMatchingCount:
                break
        median_i = (firstMatchingIndex +
                    (lastMatchingIndex - firstMatchingIndex) // 2)
        for list_i, wordSorted in enumerate(self.listSorted):
            rank[wordSorted] = abs(list_i - median_i)

    def _compareBySimilarLength(self, rank):
        """Words with same length are likely to be misspellings.
        Adjust rank values accordingly.
        """
        bestDiff = 1000  # an arbitrary big number
        firstBestIndex = 0
        lastBestIndex = 0
        for list_i, wordByLength in enumerate(self.listByLength):
            diff = abs(len(self.wordToFind) - len(wordByLength))
            if diff < bestDiff:
                firstBestIndex = list_i
                lastBestIndex = list_i
                bestDiff = diff
            elif diff == bestDiff:
                lastBestIndex = list_i
            elif diff > bestDiff:
                break
        median_i = firstBestIndex + (lastBestIndex - firstBestIndex) // 2
        for list_i, wordByLength in enumerate(self.listByLength):
            rank[wordByLength] += abs(list_i - median_i)

    def _checkEditDistance(self, rankedList):
        """Check edit distance by the order of the given list.
        Don't go through the whole list unless needed.
        """
        superStrings = []
        for rec in rankedList:
            wordRanked = rec[0]
            if subSuperString(self.wordToFind, wordRanked):
                superStrings.append(wordRanked)
            if len(superStrings) > self.limit // 2:
                break
        logger.debug("Found %d sub/super strings.", len(superStrings))
        similarStrings = []
        FAR_ENOUGH = 1000  # There's no need to check the whole list,
                           # since the most likely are towards the front.
        for list_i, rec in enumerate(rankedList):
            wordRanked = rec[0]
            editDistance = levenshteinDistance(self.wordToFind, wordRanked)
            isBetterMatch = False
            similarStrings_i = 0
            for similarStrings_i, rec2 in enumerate(similarStrings):
                dummy, dist = rec2
                if editDistance < dist:
                    isBetterMatch = True
                    break
            if isBetterMatch:
                similarStrings.insert(similarStrings_i,
                                      (wordRanked, editDistance))
                if len(similarStrings) > self.limit:
                    similarStrings.pop()
            elif len(similarStrings) < self.limit:
                similarStrings.append((wordRanked, editDistance))
            if list_i > FAR_ENOUGH:
                break
        return superStrings, similarStrings


def compareAllWords(wordList, charSetList):
    """Compare all words in list against each other.
    Modifies param wordList to add similar words.

    Running time is O(n log n) rather than O(n squared) because it
    compares word patterns rather than comparing actual words.
    """
    wordPatternHash, wordPatterns = getPatterns(wordList, charSetList)
    numSimilarWords = 0
    for word in wordList:
        if word in wordPatterns:
            for pattern in wordPatterns[word]:
                hashKey = pattern.getHashKey()
                for similarWord in wordPatternHash[hashKey]:
                    if similarWord.text != word.text:
                        word.similarWords.append(similarWord.text)
                        numSimilarWords += 1
    return numSimilarWords

def getPatterns(wordList, charSetList):
    """Reduce each word to its basic pattern by merging similar characters."""
    wordPatternHash = dict()  # keys are patterns, values are list of
                              # WordInList.  This lets us quickly
                              # match up identical patterns.
    wordPatterns = dict()  # keys are words, values are patterns.
                           # This is to remember what
                           # the patterns for that word were.
    for word in wordList:
        for word_i in range(len(word.text)):
            for charsetWordChar in charSetList:
                for char2 in charsetWordChar.val.charList:
                    list_j = word_i + len(char2)
                    if word.text[word_i:list_j] == char2:
                        newPattern = WordPattern(word.text)
                        newPattern.replace(word_i, list_j, charsetWordChar)
                        if word not in wordPatterns:
                            wordPatterns[word] = list()
                        wordPatterns[word].append(newPattern)
                        hashKey = newPattern.getHashKey()
                        if hashKey not in wordPatternHash:
                            wordPatternHash[hashKey] = list()
                        wordPatternHash[hashKey].append(word)
    return wordPatternHash, wordPatterns

class WordPattern:
    """The pattern rather than the actual text of the word."""

    def __init__(self, text):
        self.charList = [WordChar(char) for char in text]

    def replace(self, list_i, list_j, newWordChar):
        if list_j == list_i + 1:
            self.charList[list_i] = newWordChar
        else:
            self.charList = (
                self.charList[:list_i] + newWordChar + self.charList[list_j:])

    def getHashKey(self):
        """
        Returns a value that can be used as a dictionary key, and will be
        unique if and only if the WordChar list it contains is unique.
        """
        return "".join(wordChar.getHashKey() for wordChar in self.charList)



class WordChar:
    """Either a character in a string, or a CharSet in place of the
    character.
    """
    LITERAL = 0
    CHARSET = 1

    def __init__(self, newVal, isCharset=False):
        if isCharset:
            self.charType = self.CHARSET
        else:
            self.charType = self.LITERAL
        self.val = newVal

    def getHashKey(self):
        """TESTME: What happens if there is a literal value "1" or "2"?  Does
        it overwrite the charset with that ID?
        """
        if self.charType == self.CHARSET:
            return str(self.val.charsetID)
        elif self.charType == self.LITERAL:
            return self.val
        return "0"


class CharSet:
    """Uniquely label a character list."""

    instanceCount = 0

    def __init__(self, newCharList):
        self.charList = newCharList
        CharSet.instanceCount += 1
        self.charsetID = CharSet.instanceCount  # unique ID

