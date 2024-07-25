"""
Read SFM files and grab specified fields.
"""
import io
import logging
import os

from lingt.app import exceptions
from lingt.app.data import wordlist_structs
from lingt.access.common.file_reader import FileReader

logger = logging.getLogger("lingt.access.sfm_reader")

class SFM_Reader(FileReader):

    SUPPORTED_FORMATS = [
        ("sfm", "Generic SFM file (markers like \\tx)"),
        ]

    def __init__(self, fileconfig, unoObjs):
        """Will grab fields based on fileconfig.thingsToGrab."""
        FileReader.__init__(self, unoObjs)
        self.fileconfig = fileconfig  # type fileitemlist.WordListFileItem
        self.filepath = self.fileconfig.filepath
        self.rawData = []  # values are tuples of (marker, data)

    def _initData(self):
        """Elements are of type wordlist_structs.WordInList."""
        self.data = []

    def _read(self):
        """Read in the data.  Modifies self.data"""
        logger.debug("Parsing file %s", self.filepath)
        if not os.path.exists(self.filepath):
            raise exceptions.FileAccessError(
                "Cannot find file %s", self.filepath)
        self.progressBar.updatePercent(30)
        self.read_sfm_file()
        for dummy_marker, value in self.rawData:
            word = wordlist_structs.WordInList()
            word.text = value
            word.source = self.filepath
            self.data.append(word)

    def read_sfm_file(self):
        """
        Grabs a flat list of marker data, not organized by records of
        several markers.

        This should work whether self.fileconfig contains one field with
        several markers, or several fields with one marker each, or some
        combination of the two.

        Modifies self.rawData
        """
        logger.debug("reading SFM file")
        with io.open(self.filepath, mode='r', encoding='UTF8') as infile:
            sfMarkerList = []
            for whatToGrab in self.fileconfig.thingsToGrab:
                if whatToGrab.grabType == wordlist_structs.WhatToGrab.SFM:
                    sfMarkerList.extend(whatToGrab.whichOne.split())
            lineNum = 1
            try:
                for line in infile:
                    logger.debug("Line #%d.", lineNum)
                    lineNum += 1
                    for marker in sfMarkerList:
                        markerWithSpace = marker + " "
                        if line.startswith(markerWithSpace):
                            logger.debug("^%s", markerWithSpace)
                            data = line[len(markerWithSpace):]
                            data = data.strip() # is this needed?
                            self.rawData.append((marker, data))
            except UnicodeDecodeError as exc:
                raise exceptions.FileAccessError(
                    "Error reading file %s\n\n%s",
                    self.filepath, str(exc))
        logger.debug("Found %d words.", len(self.rawData))
