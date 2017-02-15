# -*- coding: Latin-1 -*-
#
# This file created Oct 23 2012 by Jim Kornelsen

"""
Read XML files that contain words we want to grab.
Some possible uses:
- word list
- spell checking
- script practice

Generally we want to capture words or phrases (optionally split up by
punctuation and whitespace).
At another layer we will also want to associate them with their file name.

For some formats, we will probably want to capture by writing system, style,
font, sfm marker, or field name.

Probably we don't care about:
- gloss
- ref no.
- context
- relation to other words or data
"""
import logging
import os
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.access.xml import xmlutil
from lingt.app import exceptions
from lingt.app.data import wordlist_structs

logger = logging.getLogger("lingt.access.words_reader")


class WordsReader(FileReader):
    SUPPORTED_FORMATS = [
        ("spellingStatus", "Paratext Spelling Status XML"),
        ]

    def __init__(self, fileconfig, unoObjs):
        FileReader.__init__(self, unoObjs)
        self.fileconfig = fileconfig   # type fileitemlist.WordListFileItem
        self.filepath = fileconfig.filepath

    def _initData(self):
        """Elements of type wordlist_structs.WordInList."""
        self.data = []

    def _read(self):
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
        if self.fileconfig.filetype == 'spellingStatus':
            self.read_spellingStatus_file()
        else:
            raise exceptions.FileAccessError(
                "Unexpected file type %s", self.fileconfig.filetype)

    def read_spellingStatus_file(self):
        """Modifies self.data"""
        logger.debug("reading Spelling Status file")
        statuses = self.dom.getElementsByTagName("Status")
        for status in statuses:
            if not status.attributes:
                continue
            text = status.getAttribute("Word")
            state = status.getAttribute("State")
            if not text:
                continue
            word = wordlist_structs.WordInList()
            word.text = text
            word.source = self.filepath
            if state == "R":
                word.isCorrect = True
            elif state == "W":
                word.isCorrect = False
                if not self.fileconfig.includeMisspellings:
                    continue
                correction = xmlutil.getTextByTagName(status, "Correction")
                if correction:
                    word.correction = correction
                    logger.debug("got correction")
            self.data.append(word)
        logger.debug("finished reading file")
