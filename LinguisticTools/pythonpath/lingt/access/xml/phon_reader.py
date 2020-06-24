# -*- coding: Latin-1 -*-

# This file created Oct 23 2012 by Jim Kornelsen
#
# 11-Apr-13 JDK  Generate ref IDs when harvesting word list data.
# 05-Jul-13 JDK  Option to use Flex citation field for phonemic.
# 07-Jul-15 JDK  Specific arguments instead of generic config object.
# 17-Nov-15 JDK  Option to force LIFT ref number location.
# 13-Dec-17 JDK  Use collections.OrderedDict for display in a list.
# 24-Jun-20 JDK  Remember duplicate ref numbers.

"""
Read XML files that typically contain phonology corpus data.

It is possible to use it for other uses besides phonology, but phonology is
expected to be the basic structure of the data.
"""
import collections
import logging
import os
import re
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.access.writer.uservars import PhonologyTags
from lingt.access.xml import xmlutil
from lingt.app import exceptions
from lingt.app.data import lingex_structs
from lingt.app.data import wordlist_structs
from lingt.utils import util

logger = logging.getLogger("lingt.access.phon_reader")


class PhonReader(FileReader):
    """For Phonology examples."""
    SUPPORTED_FORMATS = [
        ('lift', "LIFT dictionary format from FieldWorks (.lift)"),
        ('tbxphn', "Toolbox Phonology XML"),
        ('paxml', "Phonology Assistant PAXML (.paxml)")]

    def __init__(self, unoObjs, userVars, config):
        """Config should be of type lingex_structs.PhonInputSettings."""
        FileReader.__init__(self, unoObjs)
        self.userVars = userVars
        self.config = config
        self.filepath = config.filepath
        self.fieldHelper = None
        self.generateRefIDs = False

    def getSuggestions(self):
        return self.fieldHelper.suggestions

    def getDuplicateRefNumbers(self):
        return self.fieldHelper.duplicate_refnums

    def _initData(self):
        """Dictionary of examples keyed by lowercase reference number.
        Values are of type lingex_structs.LingPhonExample.
        """
        self.data = collections.OrderedDict()
        self.fieldHelper = PhonFieldHelper(self.data, self.generateRefIDs)

    def _read(self):
        filetype = self.get_filetype()
        self.progressBar.updatePercent(30)
        logger.debug("Parsing file %s", self.filepath)
        if not os.path.exists(self.filepath):
            raise exceptions.FileAccessError(
                "Cannot find file %s", self.filepath)
        try:
            self.dom = xml.dom.minidom.parse(self.filepath)
        except xml.parsers.expat.ExpatError as exc:
            raise exceptions.FileAccessError(
                "Error reading file %s\n\n%s",
                self.filepath, str(exc).capitalize())
        logger.debug("Parse finished.")
        self.progressBar.updatePercent(60)
        if filetype == 'paxml':
            self.read_paxml_file()
        elif filetype == 'lift':
            self.read_lift_file()
        elif filetype == 'xml':
            self.read_toolbox_file()
        else:
            raise exceptions.LogicError(
                "Unexpected file type %s", filetype)

    def grabWords(self, thingsToGrab):
        """Return values in a flat list of words."""
        self.generateRefIDs = True
        self.read()
        words = []
        for phonEx in self.data.values():
            for whatToGrab in thingsToGrab:
                if whatToGrab.grabType == wordlist_structs.WhatToGrab.FIELD:
                    try:
                        newList = phonEx.grabList(whatToGrab.whichOne)
                    except exceptions.LogicError as exc:
                        self.msgbox.displayExc(exc)
                        return words
                    for text in newList:
                        newWord = wordlist_structs.WordInList()
                        newWord.text = text
                        newWord.source = self.filepath
                        words.append(newWord)
        logger.debug("got %d words", len(words))
        return words

    def get_filetype(self):
        """Determines file type based on extension.
        Does not read file contents.
        """
        logger.debug(util.funcName('begin'))
        filename = os.path.basename(self.filepath)
        filetype = ""
        if re.search(r"\.lift$", filename):
            filetype = 'lift'
        elif re.search(r"\.paxml$", filename):
            filetype = 'paxml'
        elif re.search(r"\.xml$", filename):
            filetype = 'xml'
        else:
            raise exceptions.FileAccessError(
                "Unknown file type for %s", filename)
        logger.debug("File type %s.", filetype)
        return filetype

    def read_lift_file(self):
        """Read in the LIFT data from FieldWorks.
        Modifies self.data
        """
        logger.debug("reading LIFT file")
        reader = LiftXML(self.dom, self.fieldHelper, self.config)
        reader.read()
        logger.debug("finished reading LIFT file")

    def read_paxml_file(self):
        """Read in the data from Phonology Assistant.
        Modifies self.data
        """
        logger.debug("reading Phonology Assistant file")
        PaXML(self.dom, self.fieldHelper, self.userVars).read()
        logger.debug("finished reading PA file")

    def read_toolbox_file(self):
        """Read in the data exported directly from Toolbox.
        Modifies self.data
        """
        logger.debug("reading Toolbox file")
        fieldTags = PhonologyTags(self.userVars).loadUserVars()
        groups = self.dom.getElementsByTagName("phtGroup")
        logger.debug("%d pht groups.", len(groups))
        for group in groups:
            self.fieldHelper.reset()
            for fieldName, tagName in fieldTags.items():
                txt = xmlutil.getTextByTagName(group, tagName)
                if txt != "":
                    self.fieldHelper.add(fieldName, txt)
            if self.fieldHelper.hasContents():
                self.fieldHelper.addEx()
        logger.debug("finished reading Toolbox file")


class LiftXML:
    def __init__(self, dom, fieldHelper, config):
        self.dom = dom
        self.fieldHelper = fieldHelper
        self.config = config

    def read(self):
        entries = self.dom.getElementsByTagName("entry")
        for entry in entries:
            self.fieldHelper.reset()
            self.handleEntry(entry)
            if self.fieldHelper.hasContents():
                self.fieldHelper.addEx()

    def handleEntry(self, entry):
        lexical_units = entry.getElementsByTagName("lexical-unit")
        if len(lexical_units):
            lexical_unit = lexical_units[0]
            if self.config.isLexemePhonetic:
                lexfield = 'phonetic'
            else:
                lexfield = 'phonemic'
            self.fieldHelper.add(
                lexfield, xmlutil.getTextByWS(
                    lexical_unit, self.config.phoneticWS))
        if self.config.isLexemePhonetic:
            citations = entry.getElementsByTagName("citation")
            if len(citations):
                citation = citations[0]
                self.fieldHelper.add(
                    'phonemic', xmlutil.getTextByWS(
                        citation, self.config.phoneticWS))
        else:
            pronunciations = entry.getElementsByTagName("pronunciation")
            if len(pronunciations):
                pronunciation = pronunciations[0]
                self.fieldHelper.add(
                    'phonetic', xmlutil.getTextByWS(
                        pronunciation, self.config.phoneticWS))
        senses = entry.getElementsByTagName("sense")
        fields = entry.getElementsByTagName("field")
        if len(senses):
            sense = senses[0]
            glossElems = sense.getElementsByTagName("gloss")
            if len(glossElems):
                glossElem = glossElems[0]
                self.fieldHelper.add(
                    'gloss', xmlutil.getTextByWS(glossElem, ""))
        self.grabRefNumber(senses, fields)

    def grabRefNumber(self, senses, fields):
        """
        Look in several places for the ref number and take the best choice.
        """
        if len(senses):
            sense = senses[0]
            notes = sense.getElementsByTagName("note")
            for note in notes:
                if not note.attributes:
                    continue
                # first choice - source note
                if note.getAttribute("type") == "source":
                    if self.config.refNumIn not in (
                            "ExampleRefNote", "CustomRefField"):
                        if not self.fieldHelper.vals['ref']:
                            self.fieldHelper.add(
                                'ref', xmlutil.getTextByWS(note, ""))
            for note in notes:
                if not note.attributes:
                    continue
                # second choice - example reference note
                if note.getAttribute("type") == "reference":
                    if self.config.refNumIn not in (
                            "SourceNote", "CustomRefField"):
                        if not self.fieldHelper.vals['ref']:
                            self.fieldHelper.add(
                                'ref', xmlutil.getTextByWS(note, ""))
        for field in fields:
            if not field.attributes:
                continue
            # third choice - custom reference field
            if field.getAttribute("type") == "Reference":
                if self.config.refNumIn not in (
                        "SourceNote", "ExampleRefNote"):
                    if not self.fieldHelper.vals['ref']:
                        self.fieldHelper.add(
                            'ref', xmlutil.getTextByWS(field, ""))


class PaXML:
    """The old Phonology Assistant XML file format (*.paxml)."""
    FIELD_TAGS = {
        'phonetic' : "Phonetic",
        'phonemic' : "Phonemic",
        'gloss' : "Gloss",
        'ref' : "Reference"}

    def __init__(self, dom, fieldHelper, userVars):
        self.dom = dom
        self.fieldHelper = fieldHelper
        self.userVars = userVars

    def read(self):
        paRecords = self.dom.getElementsByTagName("PaRecords")
        for paRecord in paRecords:
            self.fieldHelper.reset()
            self.handlePaRecord(paRecord)
            if self.fieldHelper.hasContents():
                self.fieldHelper.addEx()

    def handlePaRecord(self, paRecord):
        experimentalTrans = None
        for fieldsNode in paRecord.childNodes:
            if fieldsNode.localName == "Fields":
                fields = fieldsNode.getElementsByTagName("FieldValueInfo")
                for field in fields:
                    if field.attributes is None:
                        continue
                    name = field.getAttribute("FieldName")
                    value = field.getAttribute("Value")
                    for fieldName, tagName in self.FIELD_TAGS.items():
                        if name == tagName:
                            self.fieldHelper.add(fieldName, value)
            elif fieldsNode.localName == "ParsedFields":
                fields = fieldsNode.getElementsByTagName("FieldValueInfo")
                for field in fields:
                    if field.attributes is None:
                        continue
                    name = field.getAttribute("FieldName")
                    value = field.getAttribute("Value")
                    if name == "Phonetic":
                        experimentalTrans = value
        if experimentalTrans:
            if self.userVars.getInt("ExperTrans_Phonemic") == 1:
                self.fieldHelper.add('phonemic', experimentalTrans)
            else:
                self.fieldHelper.add('phonetic', experimentalTrans)


class PhonFieldHelper:
    """A data structure useful when reading phonology data.
    Values can be stored by string keys (using a dictionary).
    """
    autoRefID = 0   # used if we need to generate IDs for keys to examplesDict

    def __init__(self, examplesDict, generateRefIDs):
        self.examplesDict = examplesDict
        self.generateRefIDs = generateRefIDs
        self.suggestions = []  # list of example ref numbers
        self.duplicate_refnums = set()
        self.vals = {}
        self.hasSomeContents = False
        self.firstEx = True
        self.reset()

    def reset(self):
        self.vals['ref'] = ""
        self.vals['phonetic'] = ""
        self.vals['phonemic'] = ""
        self.vals['gloss'] = ""
        self.hasSomeContents = False

    def hasContents(self):
        return self.hasSomeContents

    def add(self, fieldname, val):
        self.vals[fieldname] = val
        self.hasSomeContents = True

    def addEx(self):
        ex = lingex_structs.LingPhonExample()
        ex.refText = self.vals['ref']
        ex.phonetic = self.vals['phonetic']
        ex.phonemic = self.vals['phonemic']
        ex.gloss = self.vals['gloss']
        if not ex.refText and self.generateRefIDs:
            PhonFieldHelper.autoRefID += 1
            ex.refText = str(PhonFieldHelper.autoRefID)
        if ex.refText:
            key = ex.refText.lower()
            if key in self.examplesDict:
                self.duplicate_refnums.add(key)
            else:
                self.examplesDict[key] = ex
            if self.firstEx:
                self.firstEx = False
                self.suggestions.append(ex.refText)
        self.reset()
