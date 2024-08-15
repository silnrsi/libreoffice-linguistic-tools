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


class LingInterlinExample:
    """A structure to hold one interlinear example.
    It contains zero or more words, which each contain zero or more morphemes.
    """
    GRAB_FIELDS = [
        ('ref', "Ref. Number"),
        ('ft', "Free Translation"),
        ('wordTx1', "Word Text 1"),
        ('wordTx2', "Word Text 2"),  # for a second writing system line
        ('wordGl', "Word Gloss"),
        ('morphTx1', "Morpheme Text 1"),
        ('morphTx2', "Morpheme Text 2"),
        ('morphGl', "Morpheme Gloss"),
        ('morphPos', "Morpheme Part Of Speech")]

    def __init__(self):
        self.refText = ""
        self.wordList = []   # list of LingInterlinWord
        self._morphList = []   # list of LingInterlinMorph
        self.freeTrans = ""

    def appendMorphObj(self, morph):
        """@arg1 type is LingInterlinMorph."""
        self._morphList.append(morph)

    def appendMorph(self, morph1, morph2, morphGl, morphPS):
        """Temporarily store morph before assigning to a particular word."""
        m = LingInterlinMorph()
        m.text1 = morph1
        m.text2 = morph2
        m.gloss = morphGl
        m.pos = morphPS
        self._morphList.append(m)

    def appendWord(self, wordText1, wordText2, wordGl=""):
        if len(self._morphList) == 0:
            ## add an entry so that the word shows up
            self.appendMorphObj(LingInterlinMorph())
        w = LingInterlinWord()
        w.text1 = wordText1
        w.text2 = wordText2
        w.gloss = wordGl
        w.morphList = self._morphList
        self.wordList.append(w)
        self._morphList = []

    def addPunctuation(self, punct):
        if len(self.wordList) == 0:
            return
        prevWord = self.wordList[-1]
        prevWord.text1 += punct
        prevWord.text2 += punct

    def grabList(self, grabKey):
        """Return list of strings of the specified GRAB_FIELDS key."""
        textList = []
        if grabKey == 'ref':
            textList = [self.refText]
        elif grabKey == 'ft':
            textList = [self.freeTrans]
        elif grabKey == 'wordTx1':
            textList = [word.text1 for word in self.wordList]
        elif grabKey == 'wordTx2':
            textList = [word.text2 for word in self.wordList]
        elif grabKey == 'wordGl':
            textList = [word.gloss for word in self.wordList]
        elif grabKey == 'morphTx1':
            textList = [morph.text1 for morph in self.getMorphsList()]
        elif grabKey == 'morphTx2':
            textList = [morph.text2 for morph in self.getMorphsList()]
        elif grabKey == 'morphGl':
            textList = [morph.gloss for morph in self.getMorphsList()]
        elif grabKey == 'morphPos':
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


class LingInterlinMorph:
    """Used in LingInterlinExample"""
    def __init__(self):
        self.text1 = ""  # first writing system, orthographic for Toolbox
        self.text2 = ""  # second writing system, typically IPA for Toolbox
        self.gloss = ""  # for example "LOC.in" (typically English)
        self.pos = ""  # part of speech


class LingInterlinWord:
    """Used in LingInterlinExample"""
    def __init__(self):
        self.text1 = ""  # first writing system, orthographic for Toolbox
        self.text2 = ""  # second writing system, typically IPA for Toolbox
        self.gloss = ""  # word level, for example "in.house"
        self.morphList = []  # to handle one or more morphs
        self.morph = None  # to handle only one morph


class PhonInputSettings(Syncable):
    """Settings for reading phonology data from files.
    Used in lingt.access.phon_reader.py"""
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
        self.phonemicLeftmost = bool(
            self.userVars.get("Leftmost") != 'phonetic')

    def storeUserVars(self):
        self.userVars.store("ShowBrackets", str(int(self.showBrackets)))
        if self.phonemicLeftmost:
            self.userVars.store("Leftmost", "phonemic")
        else:
            self.userVars.store("Leftmost", "phonetic")


class InterlinOutputSettings(Syncable):
    """Interlinear settings for outputmanager.
    Show rows and other options.
    """
    USERVAR_BOOLEAN_ATTRS = [
        ('makeOuterTable', "MakeOuterTable"),
        ('insertNumbering', "InsertNumbering"),
        ('showWordText1', "ShowWordText1"),
        ('showWordText2', "ShowWordText2"),
        ('showWordGloss', "ShowWordGloss"),
        ('showMorphText1', "ShowMorphText1"),
        ('showMorphText2', "ShowMorphText2"),
        ('showMorphGloss', "ShowMorphGloss"),
        ('separateMorphColumns', "SeparateMorphColumns"),
        ('showMorphPos', "ShowMorphPartOfSpeech"),
        ('morphPosBelowGloss', "MorphPartOfSpeechBelowGloss"),
        ('freeTransInQuotes', "FreeTransInQuotes"),
        ]

    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.methodFrames = True
        self.methodTables = True
        self.makeOuterTable = True
        self.insertNumbering = True
        self.showWordText1 = True
        self.showWordText2 = False
        self.showWordGloss = False
        self.showMorphText1 = True
        self.showMorphText2 = False
        self.showMorphGloss = True
        self.separateMorphColumns = True
        self.showMorphPos = True
        self.morphPosBelowGloss = False
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

        if (not self.showMorphText1 and not self.showMorphText2
                and not self.showMorphGloss):
            self.separateMorphColumns = False
        if not self.showMorphPos:
            self.morphPosBelowGloss = False

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
