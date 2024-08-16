"""
Read interlinear examples, typically used for grammar writeups.
"""
import logging
import os
import re
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.access.writer.uservars import InterlinTags
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
        self.duplicate_refnums = set()
        self.generateRefIDs = False
        self.prefix = ""
        self.use_segnum = False

    def getSuggestions(self):
        return self.suggestions

    def getDuplicateRefNumbers(self):
        return self.duplicate_refnums

    def _initData(self):
        # Dictionary of examples keyed by lowercase ref number.
        # Examples are of type lingex_structs.LingInterlinExample.
        self.data = {}

    def _verifyDataFound(self):
        """Override base class method."""
        pass

    def _read(self):
        progressRange = ProgressRange(
            ops=len(self.config.fileList), pbar=self.progressBar)
        progressRange.partSize = 3
        self.suggestions = []
        self.duplicate_refnums = set()
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
        for interlinEx in self.data.values():
            for whatToGrab in thingsToGrab:
                if whatToGrab.grabType == wordlist_structs.WhatToGrab.FIELD:
                    try:
                        newList = interlinEx.grabList(whatToGrab.whichOne)
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
        if (docElem.nodeName == "database"
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
        self.duplicate_refnums = mainReader.duplicate_refnums
        self.baseline = ToolboxBaseline(mainReader)
        self.config = mainReader.config
        self.generateRefIDs = mainReader.generateRefIDs
        self.prefix = mainReader.prefix
        self.fieldTags = InterlinTags(mainReader.userVars).loadUserVars()
        self.ex = None  # the current example

    def read(self):
        logger.debug("reading toolbox XML file")
        addedSuggestion = False
        sentences = self.dom.getElementsByTagName(
            self.fieldTags['ref'] + "Group")
        for sentence in sentences:
            self.ex = lingex_structs.LingInterlinExample()
            self.handleSentence(sentence)
            if self.ex.refText:
                key = self.ex.refText.lower()
                if key in self.data:
                    self.duplicate_refnums.add(key)
                else:
                    self.data[key] = self.ex
                    if not addedSuggestion:
                        self.suggestions.append(self.ex.refText)
                        addedSuggestion = True
        self.baseline.verify_words_found()

    def handleSentence(self, sentence):
        self.ex.refText = xmlutil.getTextByTagName(
            sentence, self.fieldTags['ref'])
        self.ex.freeTrans = xmlutil.getTextByTagName(
            sentence, self.fieldTags['ft'])
        words = sentence.getElementsByTagName(self.baseline.word_group)
        orthoText = xmlutil.getTextByTagName(sentence, self.baseline.ortho_tag)
        orthoWords = orthoText.split()
        for word in words:
            self.handleWord(word, len(words), orthoText, orthoWords)
        if not self.ex.refText and self.generateRefIDs:
            InterlinReader.autoRefID += 1
            self.ex.refText = str(InterlinReader.autoRefID)
        if self.ex.refText and self.prefix:
            self.ex.refText = self.prefix + self.ex.refText

    def handleWord(self, word, num_words, orthoText, orthoWords):
        wordText = xmlutil.getTextByTagName(word, self.baseline.word_tag)
        orthoWord = ""
        if orthoWords:
            if num_words == 1:
                orthoWord = orthoText
            else:
                orthoWord = orthoWords.pop(0)
        morphemes = word.getElementsByTagName(self.baseline.morph_group)
        mergedMorphemes = MergedMorphemes()
        for morpheme in morphemes:
            morph = lingex_structs.LingInterlinMorph()
            morph.text1 = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['morphTx1'])
            morph.text2 = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['morphTx2'])
            morph.gloss = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['morphGloss'])
            morph.pos = xmlutil.getTextByTagName(
                morpheme, self.fieldTags['morphPos'])
            if self.config.separateMorphColumns:
                ## store each morpheme separately
                self.ex.appendMorphObj(morph)
            else:
                ## merge the morphemes
                mergedMorphemes.add(morph)
        if not self.config.separateMorphColumns:
            self.ex.appendMorphObj(
                mergedMorphemes.getMorph(
                    self.config.get_showMorphemeBreaks()))
        if self.config.SFM_baseline_word1:
            self.ex.appendWord(wordText, orthoWord)
        else:
            self.ex.appendWord(orthoWord, wordText)

class ToolboxBaseline:
    """Baseline means which words the morphemes are grouped by."""

    def __init__(self, mainReader):
        self.msgbox = mainReader.msgbox
        self.userVars = mainReader.userVars
        self.config = mainReader.config
        self.fieldTags = InterlinTags(mainReader.userVars).loadUserVars()
        self.data = mainReader.data
        self.word_group = ''
        self.morph_group = ''
        self.word_tag = ''
        self.ortho_tag = ''
        self._determine_tags()

    def _determine_tags(self):
        if self.config.SFM_baseline_word1:
            word_tag = 'wordTx1'
            morph_tag = 'morphTx1'
            ortho_tag = 'wordTx2'
        else:
            word_tag = 'wordTx2'
            morph_tag = 'morphTx2'
            ortho_tag = 'wordTx1'
        self.word_group = self.fieldTags[word_tag] + "Group"
        self.morph_group = self.fieldTags[morph_tag] + "Group"
        self.word_tag = self.fieldTags[word_tag]
        self.ortho_tag = self.fieldTags[ortho_tag]

    def verify_words_found(self):
        if not self.data:
            return
        for ex in self.data.values():
            if ex.wordList:
                return
        if self.config.SFM_baseline_word1:
            current_wordline = 1
            other_wordline = 2
        else:
            current_wordline = 2
            other_wordline = 1
        self.msgbox.display(
            "Could not find any words in '%s'.  "
            "Try changing %s%d to use a different marker, "
            "or change %s to 'WordLine%d'.",
            self.word_group,
            self.userVars.getVarName("SFMarker_Word"), current_wordline,
            self.userVars.getVarName("SFM_Baseline"), other_wordline)

def singleMorphemeWord(word):
    """For words consisting of a single morpheme, get word-level
    attributes instead of morpheme-level.
    """
    morph = lingex_structs.LingInterlinMorph()
    items = word.getElementsByTagName("item")
    for item in items:
        if item.attributes is None:
            continue
        itemType = item.getAttribute("type")
        if itemType == "gls":
            if morph.gloss and not morph.text1:
                morph.text1 = morph.gloss
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
        self.duplicate_refnums = mainReader.duplicate_refnums
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
                self.ex = lingex_structs.LingInterlinExample()
                if not self.use_segnum:
                    self.ex.refText = "%s" % refTextPara
                    if sentences.length > 1:
                        self.ex.refText += ".%s" % refTextSent
                self.handleSentence(sentence)
                if self.ex.refText:
                    key = self.ex.refText.lower()
                    if key in self.data:
                        self.duplicate_refnums.add(key)
                    else:
                        self.data[key] = self.ex
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
        for childNode in sentence.childNodes:
            if childNode.attributes is None:
                continue
            if childNode.getAttribute("type") == "gls":
                self.ex.freeTrans = xmlutil.getElemText(childNode)
        words = sentence.getElementsByTagName("word")
        for word in words:
            self.handleWord(word)
        if self.prefix:
            self.ex.refText = self.prefix + self.ex.refText

    def handleWord(self, word):
        #logger.debug(util.funcName('begin'))
        text1 = ""
        text2 = ""
        gloss = ""
        punct = None
        is_first_text = True
        for childNode in word.childNodes:
            if not childNode.attributes:
                continue
            itemType = childNode.getAttribute("type")
            elemText = xmlutil.getElemText(childNode)
            if itemType == "txt":
                if is_first_text:
                    text1 = elemText
                    is_first_text = False
                else:
                    text2 = elemText
            elif itemType == "gls":
                gloss = elemText
            elif itemType == "punct":
                punct = elemText
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
        self.ex.appendWord(text1, text2, gloss)
        #logger.debug(util.funcName('end', args=text1))

    def handleWordMorphemes(self, morphemes):
        #logger.debug(util.funcName('begin'))
        mergedMorphemes = MergedMorphemes()
        for morpheme in morphemes:
            items = morpheme.getElementsByTagName("item")
            morph = lingex_structs.LingInterlinMorph()
            is_first_text = True
            for item in items:
                if item.attributes is None:
                    continue
                itemType = item.getAttribute("type")
                if itemType == "txt":
                    elemText = xmlutil.getElemText(item)
                    if is_first_text:
                        morph.text1 = elemText
                        is_first_text = False
                    else:
                        morph.text2 = elemText
                elif itemType == "cf":
                    # lex entry, typically same as morph text
                    pass
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
                    self.config.get_showMorphemeBreaks()))

class MergedMorphemes(lingex_structs.LingInterlinMorph):
    """Merge morphemes into a single dash-separated string."""
    def __init__(self):
        lingex_structs.LingInterlinMorph.__init__(self)

    def add(self, morph):
        """
        Saves the values for later.
        :param morph(type lingex_structs.LingInterlinMorph):
        """
        for attr_name in ('text1', 'text2', 'gloss'):
            self._addTo(attr_name, getattr(morph, attr_name))
        PREFIXES = ['det']
        if (not self.pos
                or (self.pos.lower() in PREFIXES
                    and not morph.pos.startswith("-"))):
            # Just grab the first part of speech.
            # (This works best for head-final languages.)
            self.pos = morph.pos

    def _addTo(self, attrName, valToAdd):
        attrVal = getattr(self, attrName)
        DELIM = "-"     # delimiter between morphemes
        if (attrVal and not valToAdd.startswith(DELIM)
                and not attrVal.endswith(DELIM)):
            attrVal += DELIM
        attrVal += valToAdd
        setattr(self, attrName, attrVal)

    def getMorph(self, showMorphemeBreaks):
        """Return type is subclass of lingex_structs.LingInterlinMorph."""
        if not showMorphemeBreaks:
            self.text1 = ""
            self.text2 = ""
        return self
