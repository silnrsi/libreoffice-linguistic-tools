# -*- coding: Latin-1 -*-
#
# This file created July 28 2018 by Jim Kornelsen
#
# 01-Aug-18 JDK  Draw search descriptors cannot search by font.

"""
Search through shapes in a Draw document, by font or full document.
"""
import logging
import re

from lingt.access.common import iteruno
from lingt.access.writer.textsearch import TxRanger
from lingt.access.writer.traveler import Traveler
from lingt.app import exceptions
from lingt.ui.common.progressbar import ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.access.TextSearch")


class ShapeSearchSettings:
    """A structure to hold settings for ShapeSearch."""
    def __init__(self):
        self.fontName = ""
        self.fontType = ""
        self.lang = ""  # two-letter locale code
        self.matchesLimit = 0  # max number of times to match

    def loadMatchLimit(self, userVars):
        """MatchLimit is a hidden user variable -- it must be set manually."""
        varname = 'MatchLimit'
        if userVars.isEmpty(varname):
            self.matchesLimit = 0
            userVars.store(varname, "0")  # make sure it exists
        else:
            self.matchesLimit = userVars.getInt(varname)
            logger.debug("Match limit %s", self.matchesLimit)
        return self.matchesLimit


class ShapeSearch:
    """Executes a search in Draw and gets resulting text ranges."""
    def __init__(self, unoObjs, progressBar, checkForFormatting=True):
        self.unoObjs = unoObjs
        self.progressBar = progressBar
        self.ranger = TxRanger(self.unoObjs, checkForFormatting)
        self.docEnum = DocumentEnumerator(self.unoObjs)
        self.config = None
        self.selsCount = 0

    def setConfig(self, searchConfig):
        """Settings typically specified by the user.
        :param searchConfig: type TextSearchSettings
        """
        self.config = searchConfig

    def getRanges(self):
        return self.ranger.getRanges()

    def scopeWholeDoc(self):
        logger.debug(util.funcName('begin'))
        self.ranger.resetRanges()
        self.ranger.addRangeList(self.docEnum.documentSections())
        logger.debug(util.funcName('end'))

    def scopeWholeDocTraverse(self):
        """Enumerating often splits up words because new sections get created
        when a character is typed out of order.
        Here is a presumably slower, less accurate method that preserves whole
        words.
        Traverse the document with cursors to split into chunks,
        since just adding self.unoObjs.text whole gets slow after about 100
        pages.
        """
        logger.debug(util.funcName('begin'))
        oText = self.unoObjs.text
        cursor = oText.createTextCursorByRange(oText.getStart())
        cursor.collapseToStart()
        MANY_CHARACTERS = 16384     # perhaps 5 pages, but this varies greatly
        cursLeft = oText.createTextCursorByRange(cursor.getStart())
        cursLeft.collapseToStart()
        while cursor.goRight(MANY_CHARACTERS, True):
            while cursor.goRight(1, True):
                # Find a wordbreak
                if cursor.getString().endswith(" "):
                    break
            cursRight = oText.createTextCursorByRange(cursLeft.getStart())
            cursRight.collapseToStart()
            cursRight.gotoRange(cursor.getEnd(), True)
            self.ranger.addRange(cursRight)
            cursLeft.gotoRange(cursor.getEnd(), False)
            cursLeft.collapseToStart()
        cursRight = oText.createTextCursorByRange(cursLeft.getStart())
        cursRight.collapseToStart()
        cursRight.gotoRange(oText.getEnd(), True)
        self.ranger.addRange(cursRight)
        logger.debug(util.funcName('end'))

    def scopeSelection(self):
        """Search the currently selected text."""
        logger.debug(util.funcName('begin'))
        self.ranger.resetRanges()
        oSels = self.unoObjs.controller.getSelection()
        if oSels is None:
            raise exceptions.RangeError("No text is selected.")
        if not oSels.supportsService("com.sun.star.text.TextRanges"):
            # When cells are selected rather than text,
            # the selection is a TextTableCursor and has no text ranges.
            raise exceptions.RangeError(
                "Please do not select individual table cells.")
        logger.debug("getCount() = %s", oSels.getCount())
        if oSels.getCount() == 1:
            oSel = oSels.getByIndex(0)
            if oSel.supportsService("com.sun.star.text.TextRange"):
                cursor = oSel.getText().createTextCursorByRange(oSel)
                if cursor.isCollapsed():
                    raise exceptions.RangeError("No text is selected.")
        for oSel in iteruno.byIndex(oSels):
            if oSel.supportsService("com.sun.star.text.TextRange"):
                self.ranger.addRangesForCursor(oSel)
        logger.debug(util.funcName('end'))

    def scopeFont(self):
        """The API for Draw does not provide searching by font like Writer,
        so we enumerate instead.
        """
        logger.debug(util.funcName('begin'))
        for simpleTextSection in self.docEnum.documentSections():
            if self.config.fontType == "Western":
                sectionFont = simpleTextSection.CharFontName
            elif self.config.fontType == "Complex":
                sectionFont = simpleTextSection.CharFontNameComplex
            elif self.config.fontType == "Asian":
                sectionFont = simpleTextSection.CharFontNameAsian
            else:
                raise exceptions.LogicError(
                    "Unexpected font type %s.", self.config.fontType)
            if sectionFont == self.config.fontName:
                logger.debug("Found font %s", self.config.fontName)
                # TextPortions include the TextRange service.
                self.ranger.addRange(simpleTextSection)

    def scopeLocale(self):
        """This is similar to searching for a character style."""
        logger.debug(util.funcName('begin'))
        lang = self.config.lang
        if not lang:
            raise exceptions.ChoiceProblem("No locale was specified.")
        for simpleTextSection in self.docEnum.documentSections():
            if (simpleTextSection.CharLocale.Language == lang or
                    simpleTextSection.CharLocaleComplex.Language == lang or
                    simpleTextSection.CharLocaleAsian.Language == lang):
                # TextPortions include the TextRange service.
                self.ranger.addRange(simpleTextSection)


class DocumentEnumerator:
    """
    Document enumeration can be more effecient and reliable than cursors.
    """
    def __init__(self, unoObjs):
        self.unoObjs = unoObjs

    def documentSections(self):
        """Get all text sections for the document.
        Each text section has a single type of formatting.
        """
        textSections = []
        for oDrawPage in self.unoObjs.pages:
            for oShape in oDrawPage:
                if oShape.supportsService("com.sun.star.drawing.TextShape"):
                    textSections += self.textSectionsForShapeEnum(oShape)
        return textSections

    def textSectionsForShapeEnum(self, oShapeEnumerator):
        """Get text sections for all paragraphs that are enumerated by the
        given object.
        Do not pass a cursor inside a table as the oShapeEnumerator, because it
        will work but the entire table
        or paragraph will be enumerated, not just the selection.
        Instead use addRangesForCursor().
        """
        textSections = []
        i = 0
        for oPar in iteruno.byEnum(oShapeEnumerator):
            i += 1
            logger.debug("par %d: %s", i, oPar.ImplementationName)
            textSections += self.textSectionsOfPar(oPar)
        return textSections

    def textSectionsOfPar(self, oPar, textSectionList=None):
        """Recursively enumerate paragraphs, tables and frames.
        Tables may be nested.
        """
        if textSectionList is None:
            textSectionList = []
        for oTextPortion in iteruno.byEnum(oPar):
            if oTextPortion.TextPortionType == "Text":
                # TextPortions include the TextRange service.
                logger.debug("simple text portion")
                textSectionList.append(oTextPortion)
        return textSectionList
