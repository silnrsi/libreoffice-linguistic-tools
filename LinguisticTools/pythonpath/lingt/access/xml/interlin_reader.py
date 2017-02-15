# -*- coding: Latin-1 -*-
#
# This file created Oct 23 2012 by Jim Kornelsen
#
# 25-Oct-12 JDK  FileList in self.config contains FileItem elements.
# 11-Apr-13 JDK  Generate ref IDs when harvesting word list data.
# 25-Apr-13 JDK  Use // instead of / for integers, better for Python 3.
# 07-Jul-15 JDK  Specific arguments instead of generic config object.
# 16-Sep-15 JDK  Fixed bug in handleWord(): continue instead of return.
# 08-Dec-15 JDK  Optionally use segnum as ref number.
# 12-Dec-15 JDK  Fixed bug: Add Flextext suggestion only if ref number.

"""
Read interlinear examples, typically used for grammar writeups.
"""
import logging
import os
import re
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.access.writer.uservars import GrammarTags
from lingt.access.xml import xmlutil
from lingt.app import exceptions
from lingt.app.data import lingex_structs
from lingt.app.data import wordlist_structs
from lingt.ui.common.progressbar import ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.access.interlin_reader")


class InterlinReader(FileReader):
    SUPPORTED_FORMATS = [
        ('flextext', "FieldWorks Interlinear XML (flextext)"),
        ('tbxint', "Toolbox Interlinear XML"),
        ]
    autoRefID = 0   # used if we need to generate IDs for keys to self.data

    def __init__(self, unoObjs, userVars, config):
        """Config should be of type fileitemlist.InterlinInputSettings."""
        FileReader.__init__(self, unoObjs)
        self.userVars = userVars
        self.config = config
        self.suggestions = []  # list of example ref numbers
        self.generateRefIDs = False
        self.prefix = ""
        self.use_segnum = False

    def getSuggestions(self):
        return self.suggestions

    def _initData(self):
        # Dictionary of examples keyed by lowercase ref number.
        # Examples are of type lingex_structs.LingGramExample.
        self.data = {}

    def _verifyDataFound(self):
        """Override base class method."""
        pass

    def _read(self):
        progressRange = ProgressRange(
            ops=len(self.config.fileList), pbar=self.progressBar)
        progressRange.partSize = 3
        self.suggestions = []
        list_index = 1   # 1-based index of current element in list
        for fileItem in self.config.fileList:
            logger.debug("Parsing file %s", fileItem.filepath)
            self.prefix = fileItem.prefix
            self.use_segnum = fileItem.use_segnum
            self.dom = None
            if not os.path.exists(fileItem.filepath):
                raise exceptions.FileAccessError(
                    "Cannot find file %s", fileItem.filepath)
            try:
                self.dom = xml.dom.minidom.parse(fileItem.filepath)
            except (xml.parsers.expat.ExpatError, IOError) as exc:
                raise exceptions.FileAccessError(
                    "Error reading file %s\n\n%s",
                    fileItem.filepath, str(exc).capitalize())
            logger.debug("Parse finished.")
            progressRange.updatePart(1)
            filetype = self.get_filetype(fileItem.filepath, self.dom)
            progressRange.updatePart(2)

            prevLen = len(self.data)
            if filetype == "toolbox":
                ToolboxXML(self).read()
            elif filetype == "fieldworks":
                FieldworksXML(self).read()
            logger.debug("Read %d examples.", len(self.data))
            if len(self.data) == prevLen:
                raise exceptions.DataNotFoundError(
                    "Did not find any data in file %s", fileItem.filepath)
            progressRange.update(list_index)
            list_index += 1

    def grabWords(self, thingsToGrab):
        """Return values in a flat list of words."""
        self.generateRefIDs = True
        self.read()
        words = []
        logger.debug("Grabbing %s thing(s).", len(thingsToGrab))
        for gramEx in self.data.values():
            for whatToGrab in thingsToGrab:
                if whatToGrab.grabType == wordlist_structs.WhatToGrab.FIELD:
                    try:
                        newList = gramEx.grabList(whatToGrab.whichOne)
                    except exceptions.LogicError as exc:
                        self.msgbox.displayExc(exc)
                        return words
                    for text in newList:
                        newWord = wordlist_structs.WordInList()
                        newWord.text = text
                        newWord.source = self.config.fileList[0].filepath
                        words.append(newWord)
        logger.debug("got %d words", len(words))
        return words

    def get_filetype(self, filepath, dom):
        """Note to developer: Try to make it so that this function
        can never silently fail, even if for example a JPEG file is attempted.
        """
        logger.debug(util.funcName('begin'))
        filetype = ""
        if dom is None:
            raise exceptions.FileAccessError("Error with file: %s", filepath)
        docElem = dom.documentElement
        docElemChild = None
        if docElem.hasChildNodes():
            if len(docElem.childNodes) >= 2:
                docElemChild = docElem.childNodes[1]
            else:
                docElemChild = docElem.childNodes[0]
        if not docElemChild:
            raise exceptions.FileAccessError(
                "File does not seem to be from Toolbox or FieldWorks: %s",
                filepath)
        elif (docElem.nodeName == "database"
              and re.match(r"[a-zA-Z0-9]+Group", docElemChild.nodeName)):
            filetype = "toolbox"
        elif (docElem.nodeName == "document"
              and docElemChild.nodeName == "interlinear-text"):
            filetype = "fieldworks"
        else:
            raise exceptions.FileAccessError(
                "File does not seem to be from Toolbox or FieldWorks: %s",
                filepath)
        logger.debug("File type is %s", filetype)
        return filetype


class ToolboxXML:
    """Toolbox XML seems to follow this rule:
    If a marker has children, then it occurs within a group named after
    itself, and it is the first item.
    If there are other things associated with it,
    then they will also be in the group.
    """
    def __init__(self, mainReader):
        self.dom = mainReader.dom
        self.data = mainReader.data
        self.suggestions = mainReader.suggestions
        self.config = mainReader.config
        self.generateRefIDs = mainReader.generateRefIDs
        self.prefix = mainReader.prefix
        self.fieldTags = GrammarTags(mainReader.userVars).loadUserVars()
        self.ex = None  # the current example

    def read(self):
        logger.debug("reading toolbox XML file")
        addedSuggestion = False
        sentences = self.dom.getElementsByTagName(
            self.fieldTags['ref'] + "Group")
        for sentence in sentences:
            self.ex = lingex_structs.LingGramExample()
            self.handleSentence(sentence)
            if self.ex.refText:
                self.data[self.ex.refText.lower()] = self.ex
                if not addedSuggestion:
                    self.suggestions.append(self.ex.refText)
                    addedSuggestion = True

    def handleSentence(self, sentence):
        self.ex.refText = xmlutil.getTextByTagName(
            sentence, self.fieldTags['ref'])
        self.ex.freeTrans = xmlutil.getTextByTagName(
            sentence, self.fieldTags['ft'])
        orthoText = xmlutil.getTextByTagName(
            sentence, self.fieldTags['orth'])
        orthoWords = orthoText.split()
        words = sentence.getElementsByTagName(
            self.fieldTags['text'] + "Group")
        for word in words:
            self.handleWord(word, len(words), orthoText, orthoWords)
        if not self.ex.refText and self.generateRefIDs:
            InterlinReader.autoRefID += 1
            self.ex.refText = str(InterlinReader.autoRefID)
        if self.ex.refText and self.prefix:
            self.ex.refText = self.prefix + self.ex.refText

    def handleWord(self, word, num_words, orthoText, orthoWords):
        wordText = xmlutil.getTextByTagName(word, self.fieldTags['text'])
        orthoWord = ""
        if orthoWords:
            if num_words == 1:
                orthoWord = orthoText
            else:
                orthoWord = orthoWords.pop(0)
        morphemes = word.getElementsByTagName(
            self.fieldTags['morph'] + "Group")
        mergedMorphemes = MergedMorphemes()
        for morpheme in morphemes:
            morph = lingex_structs.LingGramMorph()
            morph.orth = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['orthm'])
            morph.text = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['morph'])
            morph.gloss = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['gloss'])
            morph.pos = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['pos'])
            if self.config.separateMorphColumns:
                ## store each morpheme separately
                self.ex.appendMorphObj(morph)
            else:
                ## merge the morphemes
                mergedMorphemes.add(morph)
        if not self.config.separateMorphColumns:
            self.ex.appendMorphObj(
                mergedMorphemes.getMorph(
                    self.config.showMorphemeBreaks))
        self.ex.appendWord(wordText, orthoWord)


def singleMorphemeWord(word):
    """For words consisting of a single morpheme, get word-level
    attributes instead of morpheme-level.
    """
    morph = lingex_structs.LingGramMorph()
    items = word.getElementsByTagName("item")
    for item in items:
        if item.attributes is None:
            continue
        itemType = item.getAttribute("type")
        if itemType == "gls":
            if morph.gloss and not morph.orth:
                morph.orth = morph.gloss
            morph.gloss = xmlutil.getElemText(item)
        elif itemType == "msa":
            morph.pos = xmlutil.getElemText(item)
    return morph

class FieldworksXML:
    """Parse Fieldworks XML file and store interlinear examples."""
    def __init__(self, mainReader):
        self.dom = mainReader.dom
        self.data = mainReader.data
        self.suggestions = mainReader.suggestions
        self.config = mainReader.config
        self.prefix = mainReader.prefix
        self.use_segnum = mainReader.use_segnum
        self.ex = None  # the current example

    def read(self):
        logger.debug("reading fieldworks XML file")
        paragraphs = self.dom.getElementsByTagName("paragraph")
        refTextPara = 1
        addedSuggestion = False
        for paragraph in paragraphs:
            sentences = paragraph.getElementsByTagName("phrase")
            refTextSent = 1
            for sentence in sentences:
                self.ex = lingex_structs.LingGramExample()
                if not self.use_segnum:
                    self.ex.refText = "%s.%s" % (refTextPara, refTextSent)
                self.handleSentence(sentence)
                if self.ex.refText:
                    self.data[self.ex.refText.lower()] = self.ex
                    if not addedSuggestion:
                        self.suggestions.append(self.ex.refText)
                        addedSuggestion = True
                refTextSent += 1
            refTextPara += 1

    def handleSentence(self, sentence):
        logger.debug(util.funcName('begin'))
        if self.use_segnum:
            for childNode in sentence.childNodes:
                if not childNode.attributes:
                    continue
                if childNode.getAttribute("type") == "segnum":
                    self.ex.refText = xmlutil.getElemText(childNode).strip()
                    break
        words = sentence.getElementsByTagName("word")
        for childNode in sentence.childNodes:
            if childNode.attributes is None:
                continue
            if childNode.getAttribute("type") == "gls":
                self.ex.freeTrans = xmlutil.getElemText(childNode)
        for word in words:
            self.handleWord(word)
        if self.prefix:
            self.ex.refText = self.prefix + self.ex.refText

    def handleWord(self, word):
        #logger.debug(util.funcName('begin'))
        wordOrth = ""
        wordText = ""
        punct = None
        for childNode in word.childNodes:
            if not childNode.attributes:
                continue
            elif childNode.getAttribute("type") == "txt":
                if wordText and not wordOrth:
                    wordOrth = wordText
                wordText = xmlutil.getElemText(childNode)
            elif childNode.getAttribute("type") == "punct":
                punct = xmlutil.getElemText(childNode)
                break
        if punct:
            if self.ex.wordList:
                self.ex.addPunctuation(punct)
            else:
                self.ex.appendWord(punct, punct)
            #logger.debug(util.funcName('return', args=punct))
            return
        morphemes = word.getElementsByTagName("morph")
        if len(morphemes):
            self.handleWordMorphemes(morphemes)
        else:
            self.ex.appendMorphObj(singleMorphemeWord(word))
        self.ex.appendWord(wordText, wordOrth)
        #logger.debug(util.funcName('end', args=wordText))

    def handleWordMorphemes(self, morphemes):
        #logger.debug(util.funcName('begin'))
        mergedMorphemes = MergedMorphemes()
        for morpheme in morphemes:
            items = morpheme.getElementsByTagName("item")
            morph = lingex_structs.LingGramMorph()
            for item in items:
                if item.attributes is None:
                    continue
                itemType = item.getAttribute("type")
                if itemType == "cf":
                    if morph.text and not morph.orth:
                        morph.orth = morph.text
                    morph.text = xmlutil.getElemText(item)
                elif itemType == "gls":
                    morph.gloss = xmlutil.getElemText(item)
                elif itemType == "msa":
                    morph.pos = xmlutil.getElemText(item)

            if self.config.separateMorphColumns:
                ## store each morpheme separately
                #logger.debug(morph.text)
                self.ex.appendMorphObj(morph)
            else:
                #logger.debug(morph.text)
                mergedMorphemes.add(morph)
        if not self.config.separateMorphColumns:
            self.ex.appendMorphObj(
                mergedMorphemes.getMorph(
                    self.config.showMorphemeBreaks))


class MergedMorphemes(lingex_structs.LingGramMorph):
    """Merge morphemes into a single dash-separated string."""
    def __init__(self):
        lingex_structs.LingGramMorph.__init__(self)

    def add(self, morph):
        """
        Saves the values for later.
        :param morph(type lingex_structs.LingGramMorph):
        """
        self._addTo('orth', morph.orth)
        self._addTo('text', morph.text)
        self._addTo('gloss', morph.gloss)

        PREFIXES = ['det']
        if (not self.pos
                or (self.pos.lower() in PREFIXES
                    and not morph.pos.startswith("-"))):
            # Just grab the first part of speech.
            # (This works best for head-final languages.)
            self.pos = morph.pos

    def _addTo(self, varName, valToAdd):
        varVal = getattr(self, varName)
        DELIM = "-"     # delimiter between morphemes
        if (varVal and not valToAdd.startswith(DELIM)
                and not varVal.endswith(DELIM)):
            varVal += DELIM
        varVal += valToAdd
        setattr(self, varName, varVal)

    def getMorph(self, showMorphemeBreaks):
        """Return type is subclass of lingex_structs.LingGramMorph."""
        if not showMorphemeBreaks:
            self.orth = ""
            self.text = ""
        return self
