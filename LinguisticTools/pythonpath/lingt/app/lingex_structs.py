# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 24-Sep-10 JDK  Add function to LingExample to append a word record.
# 30-Sep-10 JDK  Change LingGramExample to use structs instead of tuples.
# 19-Nov-12 JDK  Moved WordInList to the WordList module.
# 19-Nov-12 JDK  Moved many structures out, leaving just LingEx structures.
# 13-Jul-15 JDK  Moved to Access layer and added InterlinSettings.
# 22-Aug-15 JDK  Make GRAB_FIELDS type list rather than OrderedDict.
# 22-Sep-15 JDK  Fixed bug: Load ShowOrthoTextLine user variable.
# 04-Nov-15 JDK  Moved InterlinInputSettings to fileitemlist module.
# 17-Nov-15 JDK  Hidden user variable to specify ref number location for LIFT.

"""
Data structures for Linguistic Examples used by other parts of the application.
In order to avoid cyclic imports, classes used by lower layer packages should
be defined here rather than in the LingExamples module.

This module exports all of the classes defined below.
"""
from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions

class LingPhonExample:
    """A structure to hold one phonology example."""
    GRAB_FIELDS = [
        ('ref', "Ref. Number"),
        ('pht', "Phonetic"),
        ('phm', "Phonemic"),
        ('gl', "Gloss")]

    def __init__(self):
        self.refText = ""
        self.phonetic = ""
        self.phonemic = ""
        self.gloss = ""

    def grabList(self, grabKey):
        """Return list of strings of the specified GRAB_FIELDS key."""
        textList = []
        if grabKey == 'ref':
            textList = [self.refText]
        elif grabKey == 'pht':
            textList = [self.phonetic]
        elif grabKey == 'phm':
            textList = [self.phonemic]
        elif grabKey == 'gl':
            textList = [self.gloss]
        else:
            raise exceptions.LogicError("Unknown grabKey '%s'", grabKey)
        return textList


class LingGramExample:
    """A structure to hold one grammar example.
    It contains zero or more words, which each contain zero or more morphs.
    """
    GRAB_FIELDS = [
        ('ref', "Ref. Number"),
        ('ft', "Free Translation"),
        ('tx', "Text"),
        ('orth', "Orthographic"),
        ('mb', "Morphemes"),
        ('mbor', "Orth. Morphemes"),
        ('gl', "Gloss"),
        ('ps', "Part of Speech")]

    def __init__(self):
        self.refText = ""
        self.wordList = []   # list of LingGramWord
        self._morphList = []   # list of LingGramMorph
        self.freeTrans = ""

    def appendMorphObj(self, morph):
        """@arg1 type is LingGramMorph."""
        self._morphList.append(morph)

    def appendMorph(self, morphOrth, morphText, morphEng, morphPS):
        """Temporarily store morph before assigning to a particular word."""
        m = LingGramMorph()
        m.orth = morphOrth
        m.text = morphText
        m.gloss = morphEng
        m.pos = morphPS
        self._morphList.append(m)

    def appendWord(self, wordText, wordOrth):
        if len(self._morphList) == 0:
            ## add an entry so that the word shows up
            self.appendMorphObj(LingGramMorph())
        w = LingGramWord()
        w.orth = wordOrth
        w.text = wordText
        w.morphList = self._morphList
        self.wordList.append(w)
        self._morphList = []

    def addPunctuation(self, punct):
        if len(self.wordList) == 0:
            return
        prevWord = self.wordList[-1]
        prevWord.text += punct

    def grabList(self, grabKey):
        """Return list of strings of the specified GRAB_FIELDS key."""
        textList = []
        if grabKey == 'ref':
            textList = [self.refText]
        elif grabKey == 'ft':
            textList = [self.freeTrans]
        elif grabKey == 'tx':
            textList = [word.text for word in self.wordList]
        elif grabKey == 'orth':
            textList = [word.orth for word in self.wordList]
        elif grabKey == 'mb':
            textList = [morph.text for morph in self.getMorphsList()]
        elif grabKey == 'mbor':
            textList = [morph.orth for morph in self.getMorphsList()]
        elif grabKey == 'gl':
            textList = [morph.gloss for morph in self.getMorphsList()]
        elif grabKey == 'ps':
            textList = [morph.pos for morph in self.getMorphsList()]
        else:
            raise exceptions.LogicError("Unknown grabKey '%s'", grabKey)
        return textList

    def getMorphsList(self):
        """Get a list of the morphemes of all words."""
        morphsList = []
        for word in self.wordList:
            morphsList.extend(word.morphList)
        return morphsList


class LingGramMorph:
    """Used in LingGramExample"""
    def __init__(self):
        self.orth = ""  # orthographic representation of morpheme
        self.text = ""  # normal (typically IPA) representation of morpheme
        self.gloss = ""  # gloss (typically English)
        self.pos = ""  # part of speech


class LingGramWord:
    """Used in LingGramExample"""
    def __init__(self):
        self.orth = ""
        self.text = ""
        self.morphList = []  # to handle one or more morphs
        self.morph = None  # to handle only one morph


class PhonInputSettings(Syncable):
    """Phonology settings for reading data from files."""
    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.filepath = ""
        self.phoneticWS = ""  # writing system
        self.isLexemePhonetic = False
        self.refNumIn = "Any"  # look in any of the possible locations

    def loadUserVars(self):
        self.filepath = self.userVars.get("XML_filePath")
        self.phoneticWS = self.userVars.get("PhoneticWritingSystem")
        self.isLexemePhonetic = (
            self.userVars.get("FlexLexeme") != "phonemic")
        if not self.userVars.isEmpty("RefNumIn"):
            self.refNumIn = self.userVars.get("RefNumIn")

    def storeUserVars(self):
        self.userVars.store("XML_filePath", self.filepath)
        self.userVars.store("PhoneticWritingSystem", self.phoneticWS)
        if self.isLexemePhonetic:
            self.userVars.store("FlexLexeme", "phonetic")
        else:
            self.userVars.store("FlexLexeme", "phonemic")

        varname = "ExperTrans_Phonemic"
        if self.userVars.isEmpty(varname):
            self.userVars.store(varname, "0") # default is False
        if self.userVars.isEmpty("RefNumIn"):
            self.userVars.store("RefNumIn", self.refNumIn)


class PhonOutputSettings(Syncable):
    """Phonology settings for outputmanager."""
    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.showBrackets = True
        self.phonemicLeftmost = True

    def loadUserVars(self):
        self.showBrackets = bool(self.userVars.getInt("ShowBrackets"))
        self.phonemicLeftmost = (self.userVars.get("Leftmost") != 'phonetic')

    def storeUserVars(self):
        self.userVars.store("ShowBrackets", str(int(self.showBrackets)))
        if self.phonemicLeftmost:
            self.userVars.store("Leftmost", "phonemic")
        else:
            self.userVars.store("Leftmost", "phonetic")


class InterlinOutputSettings(Syncable):
    """
    Interlinear settings for outputmanager.
    Show rows and other options.
    """
    USERVAR_BOOLEAN_ATTRS = [
        ('makeOuterTable', "MakeOuterTable"),
        ('insertNumbering', "InsertNumbering"),
        ('showOrthoTextLine', "ShowOrthoTextLine"),
        ('showText', "ShowText"),
        ('showOrthoMorphLine', "ShowOrthoMorphLine"),
        ('showMorphemeBreaks', "ShowMorphBreaks"),
        ('separateMorphColumns', "SeparateMorphColumns"),
        ('showPartOfSpeech', "ShowPartOfSpeech"),
        ('POS_aboveGloss', "POS_AboveGloss"),
        ('freeTransInQuotes', "FreeTransInQuotes"),
        ]

    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.methodFrames = True
        self.methodTables = True
        self.makeOuterTable = True
        self.insertNumbering = True
        self.showOrthoTextLine = False
        self.showText = True
        self.showOrthoMorphLine = False
        self.showMorphemeBreaks = True
        self.separateMorphColumns = True
        self.showPartOfSpeech = True
        self.POS_aboveGloss = False
        self.freeTransInQuotes = False
        self.startingOuterRowHeight = 2
        self.tableBottomMargin = 0.13
        self.numberingColumnWidth = 7

    def loadUserVars(self):
        self.methodTables = False
        self.methodFrames = False
        method = self.userVars.get("Method")
        if method == 'tables':
            self.methodTables = True
        else:
            self.methodFrames = True

        for attrName, varName in self.USERVAR_BOOLEAN_ATTRS:
            setattr(self, attrName, False)
            if self.userVars.getInt(varName) == 1:
                setattr(self, attrName, True)

        if not self.showMorphemeBreaks:
            self.separateMorphColumns = False
        if not self.showPartOfSpeech:
            self.POS_aboveGloss = False

        val = 0.13
        varname = "TableBottomMargin"
        try:
            strVal = self.userVars.get(varname)
            val = float(strVal)
        except ValueError:
            self.userVars.store(varname, "")
        self.tableBottomMargin = val

        self.numberingColumnWidth = self.userVars.getInt("NumberingColWidth")

        varname = "StartingOuterRowHeight"
        if self.userVars.isEmpty(varname):
            defaultVal = "2"
            self.userVars.store(varname, defaultVal)
            self.startingOuterRowHeight = int(defaultVal)
        else:
            self.startingOuterRowHeight = self.userVars.getInt(varname)

    def storeUserVars(self):
        """Currently not used."""
        for attrName, varName in self.USERVAR_BOOLEAN_ATTRS:
            self.userVars.store(varName, str(getattr(self, attrName)))
