#!/usr/bin/python
# -*- coding: Latin-1 -*-
#
# Created on July 8 2015 by Jim Kornelsen.
#
# 03-Aug-15 JDK  Moved LineSearcher to a separate class.
# 06-Aug-15 JDK  Fixed bug: get correct group to check CHARS_TO_SKIP.
# 13-Aug-15 JDK  Fixed bug: vowel signs should be dependent.
# 13-Nov-15 JDK  Fixed bug: extend() modifies list in place.
# 22-Feb-16 JDK  Download file automatically.

"""
Parse data from the Unicode Character Database at http://unicode.org/ucd/.
Organize by script and linguistic properties.
Used to generate lingt/utils/unicode_data.py.
"""
from collections import defaultdict
import os
import re
import shutil
import sys
import urllib.request

INFILE = "UnicodeData.txt"
OUTFILE = "letters_out.py"


def download_file():
    """Downloads the latest character database file if it doesn't exist yet."""
    if os.path.exists(INFILE):
        print("Using previously downloaded file.")
        return
    print("Downloading file...", end="")
    sys.stdout.flush()
    url = "http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt"
    # Download the file and save it locally.
    with urllib.request.urlopen(url) as response, open(
            INFILE, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print("done.")


class Script:
    """Consonants and vowels of a particular script."""
    def __init__(self):
        self.initialVowels = []
        self.dependentVowels = []
        self.anywhereVowels = []
        self.initialConsonants = []
        self.finalConsonants = []
        self.anywhereConsonants = []

        self.similaritySets = SimilaritySets()

        # all nasals are phonetically similar, likewise with liquids
        self.nasals = []
        self.liquids = []

    def addLetter(self, code, letterName, flags):
        if flags.vowel:
            if flags.initial:
                self.initialVowels.append(code)
            elif flags.dependent:
                self.dependentVowels.append(code)
            else:
                self.anywhereVowels.append(code)
            if flags.candidate and letterName:
                self.similaritySets.candidateVowels.append(
                    (letterName, code, repr(flags)))
        elif flags.consonant:
            if flags.initial:
                self.initialConsonants.append(code)
            elif flags.final:
                self.finalConsonants.append(code)
            else:
                self.anywhereConsonants.append(code)
            if flags.nasal:
                self.nasals.append(code)
            elif flags.liquid:
                self.liquids.append(code)
            elif letterName:
                self.similaritySets.candidateConsonants.append(
                    (letterName, code, repr(flags)))


class LetterFlags:
    def __init__(self):
        self.consonant = False
        self.vowel = False
        self.nasal = False
        self.liquid = False
        self.initial = False  # occurs only word initially
        self.final = False    # occurs only word finally
        self.dependent = False  # vowel only occurs preceded by a consonant
        self.candidate = False  # vowel candidate for phonetic similarity

    def __repr__(self):
        """Return a string to uniquely identify the object."""
        return repr(self.__dict__)


class LineSearcher:
    """Quick Perl-style pattern match of a line,
    to make a series of elif statements easier when parsing a file.
    """
    def __init__(self):
        self.matchObj = None
        self.line = ""

    def searchLine(self, pattern):
        """Sets self.matchObj"""
        self.matchObj = re.search(pattern, self.line)
        if self.matchObj:
            return True
        return False


class FileReader(LineSearcher):

    INDIC_SCRIPTS = [
        "DEVANAGARI", "TAMIL", "TELEGU", "GUJARATI", "BENGALI", "GURMUKHI",
        "KANNADA", "MALAYALAM", "ORIYA"]

    def __init__(self):
        LineSearcher.__init__(self)
        self.scripts = defaultdict(Script)
        self.otherKnownChars = Script()  # characters not included in scripts

    def readFile(self):
        try:
            with open(INFILE, 'r') as infile:
                for self.line in infile:
                    self.parseLine()
        except (OSError, IOError):
            print("Couldn't open file for reading: %s", INFILE)
            exit()
        for script in self.scripts.values():
            script.similaritySets.buildSets()
        return self.scripts, self.otherKnownChars

    def parseLine(self):
        if self.searchLine(r"^([0-9A-F]{4});"):
            code = self.matchObj.group(1)
            if code in CHARS_TO_SKIP:
                self.addOtherKnownChar()
                return
        else:
            return
        self.line = re.sub(
            r"(SINHALA LETTER [A-Z]+) [A-Z]+", r"\1", self.line)
        self.line = re.sub(
            r"(SINHALA VOWEL SIGN [A-Z]+) [A-Z\-]+", r"\1", self.line)
        if self.searchLine(
                r"^([0-9A-F]{4});" +
                r"([A-Z]+)( CAPITAL| SMALL)? LETTER( FINAL)? ([A-Z]+);"):
            self.addNormalLetter()
            return
        code = ""
        scriptName = ""
        letterName = ""
        flags = LetterFlags()
        if self.searchLine(
                r"([0-9A-F]{4});([A-Z]+) VOWEL SIGN ([A-Z]+);"):
            code, scriptName, letterName = self.matchObj.groups()
            flags.vowel = True
            flags.dependent = True
            flags.candidate = True
        elif self.searchLine(r"([0-9A-F]{4});(HEBREW) POINT"):
            code, scriptName = self.matchObj.groups()
            flags.vowel = True
            flags.dependent = True
        elif self.searchLine(r"([0-9A-F]{4});(THAI) CHARACTER SARA"):
            code, scriptName = self.matchObj.groups()
            flags.vowel = True
            flags.dependent = True
        elif self.searchLine(r"([0-9A-F]{4});(THAI) CHARACTER"):
            code, scriptName = self.matchObj.groups()
            flags.consonant = True
        elif self.searchLine(r"([0-9A-F]{4});(ARABIC) LETTER FARSI YEH;"):
            code, scriptName = self.matchObj.groups()
            flags.vowel = True
            flags.dependent = True
        elif self.searchLine(r"([0-9A-F]{4});(HANGUL) CHOSEONG ([A-Z]+);"):
            # Note: We don't allow "-" because we ignore conjuncts
            code, scriptName, dummy_letterName = self.matchObj.groups()
            flags.consonant = True
            flags.initial = True
            self.scripts[scriptName].initialConsonants.append(code)
        elif self.searchLine(r"([0-9A-F]{4});(HANGUL) JUNGSEONG ([A-Z]+);"):
            code, scriptName, dummy_letterName = self.matchObj.groups()
            flags.vowel = True
            flags.dependent = True
        elif self.searchLine(r"([0-9A-F]{4});(HANGUL) JONGSEONG ([A-Z]+);"):
            code, scriptName, dummy_letterName = self.matchObj.groups()
            flags.consonant = True
            flags.final = True
        else:
            self.addOtherKnownChar()
            return
        if code and scriptName:
            script = self.scripts[scriptName]
            script.addLetter(code, letterName, flags)

    def addNormalLetter(self):
        code, scriptName, case, final, letterName = self.matchObj.groups()
        flags = LetterFlags()
        if case == " CAPITAL":
            flags.initial = True
        if letterName in ("Y", "YA", "YYA"):
            flags.consonant = True
        elif re.match(r"[A|E|I|O|U|Y]+", letterName):
            flags.vowel = True
            flags.candidate = True
        elif (scriptName == "GREEK" and re.match(
                r"ALPHA|EPSILON|ETA|IOTA|OMICRON|UPSILON|OMEGA", letterName)):
            flags.vowel = True
        elif re.search(r"B|C|D|F|G|H|J|K|L|M|N|P|Q|R|S|T|V|W|X|Z", letterName):
            flags.consonant = True
            if re.search(r"M|N", letterName):
                flags.nasal = True
            elif re.search(r"R|L", letterName):
                flags.liquid = True
        if flags.vowel and scriptName in self.INDIC_SCRIPTS:
            flags.initial = True
        if scriptName == "HANGUL":
            self.addOtherKnownChar()
            return
        if code == "0648" or code == "0627":
            # Arabic letter Waw and Alef
            flags.dependent = True
        if final == " FINAL":
            flags.final = True
        script = self.scripts[scriptName]
        script.addLetter(code, letterName, flags)

    def addOtherKnownChar(self):
        """Don't include in script letters.
        Modifies self.otherKnownChars
        """
        if self.searchLine(r"^([0-9A-F]{4});([^;]+);([^;]*);"):
            code, dummy_letterDescription, category = self.matchObj.groups()
            flags = LetterFlags()
            if category in ("Lu", "Lt"):
                flags.consonant = True
                flags.initial = True
            elif "<final>" in self.line or "<medial>" in self.line:
                flags.consonant = True
                flags.final = True
            elif "<initial>" in self.line or "<isolated>" in self.line:
                flags.consonant = True
                flags.initial = True
            elif category in ("Ll", "Lm", "Lo"):
                flags.consonant = True
            else:
                flags.vowel = True
                flags.dependent = True
            self.otherKnownChars.addLetter(code, "", flags)


class SimilaritySets:
    """Phonetically similar segments for a script."""
    POA_GROUPS = {'bilabial': ("P", "B"),
                  'labiodental': ("F", "V"),
                  'alveolar': ("T", "D", "S", "Z"),
                  'palatal': ("J", "C"),
                  'velar': ("K", "G", "X"),
                  'uvular': ("Q")}
    # maintain sorted order
    POA_GROUPS_KEYLIST = [
        'bilabial', 'labiodental', 'alveolar', 'palatal', 'velar', 'uvular']
    # index of self.candidateVowels and self.candidateConsonants
    LETTER_NAME = 0

    def __init__(self):
        # candidates to check for phonetic similarity
        # list of letter name without modifiers, code point, flags repr
        self.candidateVowels = list()  # compare for length, glide
        self.candidateConsonants = list()  # compare for aspiration, POA

        # phonetically similar segments
        # keys are code point
        # values are list of similar code points
        self.vowelLength = defaultdict(list)
        self.vowelGlide = defaultdict(list)
        self.aspiration = defaultdict(list)

        # phonetically similar point of articulation
        # keys are point of articulation group name
        # values are list of similar code points
        self.articulation = defaultdict(list)

    def buildSets(self):
        if self.candidateVowels:
            self.searchVowelCandidates()
        if self.candidateConsonants:
            self.searchConsonantCandidates()

    def searchVowelCandidates(self):
        singleLetters = [
            candidate for candidate in self.candidateVowels
            if len(candidate[self.LETTER_NAME]) == 1]
        dualLetters = [
            candidate for candidate in self.candidateVowels
            if len(candidate[self.LETTER_NAME]) == 2]  # digraphs
        for letterName1, code1, flags_repr1 in singleLetters:
            for letterName2, code2, flags_repr2 in dualLetters:
                if (letterName2 == letterName1 * 2
                        and flags_repr1 == flags_repr2):
                    # for example AA
                    self.vowelLength[code1].append(code2)
                elif (letterName2.startswith(letterName1)
                        and flags_repr1 == flags_repr2):
                    # for example AI
                    self.vowelGlide[code1].append(code2)

    def searchConsonantCandidates(self):
        for letterName, code, flags_repr in self.candidateConsonants:
            for groupName, poaChars in self.POA_GROUPS.items():
                if letterName[0] in poaChars:
                    self.articulation[groupName].append(code)
        aspiratedLetters = []
        unaspiratedLetters = []
        for candidate in self.candidateConsonants:
            if re.search(r"H", candidate[self.LETTER_NAME]):
                aspiratedLetters.append(candidate)
            else:
                unaspiratedLetters.append(candidate)
        for letterName1, code1, flags_repr1 in unaspiratedLetters:
            for letterName2, code2, flags_repr2 in aspiratedLetters:
                if (letterName1 == re.sub("H", "", letterName2)
                        and flags_repr1 == flags_repr2):
                    self.aspiration[code1].append(code2)

    def getLists(self, listName):
        lists = []
        if listName == 'POA':
            listDict = self.articulation
            for groupName in self.POA_GROUPS_KEYLIST:
                lists.append(listDict[groupName])
            return lists
        elif listName == 'VOW_LEN':
            listDict = self.vowelLength
        elif listName == 'VOW_GLIDE':
            listDict = self.vowelGlide
        elif listName == 'ASP':
            listDict = self.aspiration
        for code, codeSimilarList in listDict.items():
            # include the code along with its list
            codeIncludedList = [code]
            codeIncludedList.extend(codeSimilarList)
            lists.append(codeIncludedList)
        if not lists:
            lists.append([])
        return lists


def tabSpaces(numTabs):
    TABWIDTH = 4  # following PEP8 style guide
    numSpaces = TABWIDTH * numTabs
    return ' ' * numSpaces

def codeStr(code):
    return 'u"\\u%s"' % code

class FileWriter:
    """Write results to file"""
    LINEWIDTH = 79  # following PEP8 style guide
    SCRIPTS_TO_SKIP = ["MODIFIER"]
    START_INDENT = 0

    def __init__(self):
        self.outfile = None
        self.numTabs = 3  # how far to indent

    def writeFile(self, scripts, otherKnownChars):
        for scriptName in self.SCRIPTS_TO_SKIP:
            del scripts[scriptName]
        try:
            with open(OUTFILE, 'w') as self.outfile:
                self.writeScriptLetters(scripts)
                self.writeOtherKnownLetters(otherKnownChars)
                self.writeSimilarChars(scripts)
        except (OSError, IOError):
            print("Couldn't open file for writing: %s" % OUTFILE)
            exit()

    def writeScriptLetters(self, scripts):
        self.indent(self.START_INDENT + 0)
        self.outfile.write("SCRIPT_LETTERS = {\n")
        for scriptName, script in sorted(scripts.items()):
            self.indent(self.START_INDENT + 1)
            self.numTabs = self.START_INDENT + 2
            self.outfile.write('"%s": {\n' % scriptName)
            self.writeCodeList(script.initialVowels, 'WI_Vowels')
            self.writeCodeList(script.dependentVowels, 'DepVowels')
            self.writeCodeList(script.anywhereVowels, 'AnyVowels')
            self.writeCodeList(script.initialConsonants, 'WI_Consonants')
            self.writeCodeList(script.finalConsonants, 'WF_Consonants')
            self.writeCodeList(script.anywhereConsonants, 'AnyConsonants')
            self.outfile.write("        },\n")
        self.outfile.write("    }\n\n")

    def writeOtherKnownLetters(self, otherKnownChars):
        self.indent(self.START_INDENT + 0)
        self.outfile.write("OTHER_KNOWN_LETTERS = {\n")
        self.numTabs = self.START_INDENT + 1
        self.writeCodeList(otherKnownChars.initialVowels, 'WI_Vowels')
        self.writeCodeList(otherKnownChars.dependentVowels, 'DepVowels')
        self.writeCodeList(otherKnownChars.anywhereVowels, 'AnyVowels')
        self.writeCodeList(otherKnownChars.initialConsonants, 'WI_Consonants')
        self.writeCodeList(otherKnownChars.finalConsonants, 'WF_Consonants')
        self.writeCodeList(otherKnownChars.anywhereConsonants, 'AnyConsonants')
        self.indent(self.START_INDENT + 0)
        self.outfile.write("}\n\n")

    def writeSimilarChars(self, scripts):
        self.indent(self.START_INDENT + 0)
        self.outfile.write("SIMILAR_CHARS = {\n")
        for scriptName, script in sorted(scripts.items()):
            self.indent(self.START_INDENT + 1)
            self.outfile.write('"%s": {\n' % scriptName)
            self.numTabs = self.START_INDENT + 2
            for listName in [
                    'NASAL', 'LIQUID', 'VOW_LEN', 'VOW_GLIDE', 'ASP', 'POA']:
                self.indent(self.START_INDENT + 2)
                self.outfile.write('"%s" : [' % listName)
                if listName == 'NASAL':
                    similarityLists = [script.nasals]
                elif listName == 'LIQUID':
                    similarityLists = [script.liquids]
                else:
                    similarityLists = script.similaritySets.getLists(listName)
                if not similarityLists[0]:
                    self.outfile.write("],\n")
                    continue
                self.outfile.write("\n")
                for sublist in similarityLists:
                    self.writeCodeList(sublist, "")
                self.indent(self.START_INDENT + 2)
                self.outfile.write("],\n")
            self.indent(self.START_INDENT + 1)
            self.outfile.write("},\n")
        self.indent(self.START_INDENT + 0)
        self.outfile.write("}\n\n")


    def writeCodeList(self, codeList, listName):
        """
        Print a list of letter codes.
        Before calling this method, set self.outfile and self.indentSize.
        """
        lineBuffer = tabSpaces(self.numTabs + 1)
        if listName:
            self.indent(self.numTabs)
            self.outfile.write('"%s" : [' % listName)
            if not codeList:
                self.outfile.write("],\n")
                return
            self.outfile.write("\n")
        else:
            if not codeList:
                return
            lineBuffer += "["
        codeList.sort()
        lineBuffer += codeStr(codeList[0])
        BASEWIDTH = self.LINEWIDTH - len("],")
        for code in codeList[1:]:
            # Add another code on this line if it will fit.
            candidateLineBuffer = lineBuffer + ", " + codeStr(code)
            if len(candidateLineBuffer) <= BASEWIDTH:
                lineBuffer = candidateLineBuffer
                continue
            # Can't fit any more, so start a new line.
            self.outfile.write(lineBuffer + ",\n")
            extraSpace = ""
            if not listName:
                # align with opening delimiter "[" (see PEP8)
                extraSpace = " "
            lineBuffer = "%s%s%s" % (
                tabSpaces(self.numTabs + 1), extraSpace, codeStr(code))
        self.outfile.write("%s],\n" % lineBuffer)

    def indent(self, numTabs):
        self.outfile.write(tabSpaces(numTabs))


CHARS_TO_SKIP = set([
    # Arabic
    "06C6", "06C7", "06C8", "06D0", "06D5",
    "0679", "067A", "067B",
    "067E", "067F", "0680", "0683", "0684", "0686",
    "0687", "0688", "068C", "068D", "068E", "0691",
    "0698", "06A4", "06A6", "06A9", "06AD", "06AF",
    "06B1", "06B3", "06BB", "06CB",
    # Bengali
    "09CE", "09DC", "09DD", "09DF",
    # Cyrillic
    "0451", "0452", "0453", "0455", "0457", "0458", "0459", "045A", "045B",
    "045C", "045E", "045F", "0460", "0461", "0462", "0463", "046E", "046F",
    "0470", "0471", "0472", "0473", "0474", "0475", "0478", "0479", "047E",
    "047F", "0480", "0481", "04BA", "04BB", "04C0", "04CF", "04D8", "04D9",
    "0514", "0515", "0516", "0517", "0518", "0519", "051A", "051B", "051C",
    "051D",
    "A680", "A681", "A682", "A683", "A684", "A685", "A686", "A687", "A688",
    "A689", "A68A", "A68B", "A68C", "A68D", "A68E", "A68F", "A690", "A691",
    "A692", "A693", "A694", "A695", "A696", "A697",
    # Devanagari
    "090C", "0929", "0931", "0933", "0934", "093A", "093B", "094E", "094F",
    "0956", "0957",
    "0958", "0959", "095A", "095B", "095C", "095D", "095E", "095F",
    "0962", "0963",
    "0973", "0974", "0975", "0976", "0977", "0979",
    "097B", "097C", "097E", "097F",
    # Georgian
    "10A0", "10A1", "10A2", "10A3", "10A4", "10A5", "10A6", "10A7", "10A8",
    "10A9", "10AA", "10AB", "10AC", "10AD", "10AE", "10AF", "10B0", "10B1",
    "10B2", "10B3", "10B4", "10B5", "10B6", "10B7", "10B8", "10B9", "10BA",
    "10BB", "10BC", "10BD", "10BE", "10BF", "10C0", "10C1", "10C2", "10C3",
    "10C4", "10C5",
    "2D00", "2D01", "2D02", "2D03", "2D04", "2D05", "2D06", "2D07", "2D08",
    "2D09", "2D0A", "2D0B", "2D0C", "2D0D", "2D0E", "2D0F", "2D10", "2D11",
    "2D12", "2D13", "2D14", "2D15", "2D16", "2D17", "2D18", "2D19", "2D1A",
    "2D1B", "2D1C", "2D1D", "2D1E", "2D1F", "2D20", "2D21", "2D22", "2D23",
    "2D24", "2D25",
    # Greek
    "0370", "0371",
    "03DA", "03DB", "03DC", "03DD", "03DE", "03DF", "03E0", "03E1",
    "03F3", "03F7", "03F8", "03F9", "03FA", "03FB",
    # Gujarati
    "0AF9",
    # Gurmukhi
    "0A59", "0A5A", "0A5B", "0A5C", "0A5E",
    # Hangul
    "115F", "1160",
    "3165", "3166", "3167", "3168", "3169", "316A", "316B", "316C", "316D",
    "316E", "316F", "3170", "3171", "3172", "3173", "3174", "3175", "3176",
    "3177", "3178", "3179", "317A", "317B", "317C", "317D", "317E", "317F",
    "3180", "3181", "3182", "3183", "3184", "3185", "3186", "3187", "3188",
    "3189", "318A", "318B", "318C", "318D", "318E",
    # Hebrew
    "05C1", "05C2", "05C7", "05BA", "FB1E",
    # Kannada
    "0CDE",
    # Khmer
    "17A3", "17A4",
    # Latin
    "00C6", "00D0", "00DE", "00E6", "00F0", "00FE", "0138", "014A", "014B",
    "018F", "0194", "0195", "0196", "01A2", "01A3", "01A6", "01A9", "01B1",
    "01B7", "01BF", "01C7", "01C9", "01CA", "01CC", "01F1", "01F3", "01F6",
    "01F7", "021C", "021D", "0222", "0223",
    "0251", "0259", "0263", "0269", "026E",
    "0278", "0283", "028A", "0292", "1D25", "1D6B", "1E9F", "2C6D", "A726",
    "A727", "A728", "A729", "A72A", "A72B", "A72C", "A72D", "A732", "A733",
    "A734", "A735", "A736", "A737", "A738", "A739", "A73C", "A73D",
    "A74E", "A74F",
    "A760", "A761", "A768", "A769", "A76A", "A76B", "A76C", "A76D", "A76E",
    "A76F", "A771", "A772", "A773", "A774", "A775", "A777", "A778", "A78B",
    "A78C",
    "A7B3", "A7B4", "A7B5", "A7B6", "A7B7", "AB50", "AB53", "AB63",
    # Malayalam
    "0D29", "0D3A", "0D4C",
    # Oriya
    "0B5C", "0B5D",
    # Telugu
    "0C58", "0C59",
    # Thaana
    "07B1",
    # Thai
    "0E24", "0E26", "0E2F", "0E37", "0E3A", "0E45", "0E46", "0E48", "0E49",
    "0E4A", "0E4B", "0E4C", "0E4D", "0E4E", "0E4F", "0E5A", "0E5B",
    ])


if __name__ == "__main__":
    download_file()
    FileWriter().writeFile(
        *FileReader().readFile())
    print("Finished!")

