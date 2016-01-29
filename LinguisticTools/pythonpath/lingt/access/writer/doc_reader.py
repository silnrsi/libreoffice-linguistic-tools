# -*- coding: Latin-1 -*-
#
# This file created Nov 5 2012 by Jim Kornelsen
#
# 01-Apr-13 JDK  Handle exceptions if document cannot be opened.
# 08-Apr-13 JDK  Separate loading document into a new method.

"""
Read text docs in Writer that contain words we want to grab.
Most of the grunt work is done by search.py
"""

import uno
import os
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import RuntimeException

from lingt.access.file_reader import FileReader
from lingt.access.writer.textsearch import TextSearchSettings, TextSearch
from lingt.app import exceptions
from lingt.app.wordlist_structs import WhatToGrab, WordInList
from lingt.utils import util
from lingt.utils.locale import theLocale

class DocReader(FileReader):

    SUPPORTED_FORMATS = [
        ('writerdoc', "Document (.odt .doc .docx .rtf) for Writer")]

    def __init__(self, fileconfig, unoObjs, matchesLimit):
        FileReader.__init__(self, unoObjs)
        theLocale.loadUnoObjs(unoObjs)
        self.fileconfig = fileconfig   # type fileitemlist.WordListFileItem
        self.filepath = self.fileconfig.filepath
        self.matchesLimit = matchesLimit
        self.doc = None

    def _initData(self):
        """Elements are of type WordInList."""
        self.data = []

    def _read(self):
        try:
            self.loadDoc(self.filepath)
        except (exceptions.FileAccessError, exceptions.DocAccessError):
            raise exceptions.FileAccessError(
                "Error reading file %s", self.filepath)
        self.progressBar.updatePercent(60)
        self.read_document()
        self.logger.debug("Setting visible.")
        self.doc.window.setVisible(True)

    def loadDoc(self, filepath):
        self.logger.debug(util.funcName('begin', args=filepath))
        if not os.path.exists(filepath):
            raise exceptions.FileAccessError(
                "Cannot find file %s", filepath)
        fileUrl = uno.systemPathToFileUrl(os.path.realpath(filepath))
        uno_args = (
            util.createProp("Minimized", True),
            # Setting a filter makes some files work but then .odt fails.
            # Instead just have the user open the file first.
            #util.createProp("FilterName", "Text"),
        )
        # Loading the document hidden was reported to frequently crash
        #       before OOo 2.0.  It seems to work fine now though.
        newDoc = self.unoObjs.desktop.loadComponentFromURL(
            fileUrl, "_default", 0, uno_args)
        try:
            self.doc = self.unoObjs.getDocObjs(newDoc)
        except AttributeError:
            raise exceptions.DocAccessError()
        self.logger.debug(util.funcName('end'))

    def read_document(self):
        """Sets self.data to list of WordInList objects."""
        self.logger.debug(util.funcName('begin'))
        textRanges = []
        textSearch = TextSearch(
            self.doc, self.progressBar, checkForFormatting=False)
        for whatToGrab in self.fileconfig.thingsToGrab:
            searchConfig = TextSearchSettings()
            searchConfig.matchesLimit = self.matchesLimit
            if whatToGrab.grabType == WhatToGrab.PARASTYLE:
                searchConfig.style = whatToGrab.whichOne
                textSearch.setConfig(searchConfig)
                textSearch.scopeParaStyle()
            elif whatToGrab.grabType == WhatToGrab.CHARSTYLE:
                searchConfig.style = whatToGrab.whichOne
                textSearch.setConfig(searchConfig)
                textSearch.scopeCharStyle()
            elif whatToGrab.grabType == WhatToGrab.FONT:
                searchConfig.fontName = whatToGrab.whichOne
                searchConfig.fontType = whatToGrab.fontType
                textSearch.setConfig(searchConfig)
                textSearch.scopeFont()
            elif (whatToGrab.grabType == WhatToGrab.PART and
                  whatToGrab.whichOne == WhatToGrab.WHOLE_DOC):
                textSearch.scopeWholeDocTraverse()
            else:
                continue
            textRanges.extend(textSearch.getRanges())

        self.logger.debug("Got %d ranges.", len(textRanges))
        for txtRange in textRanges:    # txtRange is of type search.TxtRange
            oSel = txtRange.sel
            try:
                oCursor = oSel.getText().createTextCursorByRange(oSel)
            except (RuntimeException, IllegalArgumentException):
                self.logger.warn("Failed to go to text range.")
                continue
            text = oCursor.getString()
            self.logger.debug(len(text))
            if text != "":
                ## Add word
                word = WordInList()
                word.text = text
                word.source = self.fileconfig.filepath
                self.data.append(word)
        self.logger.debug(util.funcName('end'))

