# -*- coding: Latin-1 -*-
#
# This file created July 28 2018 by Jim Kornelsen
#
# 01-Aug-18 JDK  Draw search descriptors cannot search by font.
# 03-Aug-18 JDK  Draw does not have multiple selections.

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

    def load_userVars(self, userVars):
        """This hidden user variable must be set manually."""
        varname = 'MatchLimit'
        if userVars.isEmpty(varname):
            self.matchesLimit = 0
            userVars.store(varname, "0")  # make sure it exists
        else:
            self.matchesLimit = userVars.getInt(varname)
            logger.debug("Match limit %s", self.matchesLimit)


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

    def scopeSelection(self):
        """Search the currently selected text."""
        logger.debug(util.funcName('begin'))
        self.ranger.resetRanges()
        oSel = self.unoObjs.controller.getSelection()
        if oSel is None:
            raise exceptions.RangeError("No text is selected.")
        #util.xray(oSel, self.unoObjs)
        #XXX: This check fails even though, according to xray, the object
        #     *does* support it.
        #if not oSel.supportsService("com.sun.star.text.TextRange"):
        #    raise exceptions.RangeError("No text is selected.")
        cursor = oSel.getText().createTextCursorByRange(oSel)
        if cursor.isCollapsed():
            raise exceptions.RangeError("No text is selected.")
        self.ranger.addRange(oSel)
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
        #for oDrawPage in self.unoObjs.pages  # doesn't work in AOO
        for iDrawPage in range(self.unoObjs.pages.getCount()):
            oDrawPage = self.unoObjs.pages.getByIndex(iDrawPage)
            #for oShape in oDrawPage:
            for iShape in range(oDrawPage.getCount()):
                oShape = oDrawPage.getByIndex(iShape)
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
