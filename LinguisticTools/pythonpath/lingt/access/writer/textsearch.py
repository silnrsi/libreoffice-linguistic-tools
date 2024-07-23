# -*- coding: Latin-1 -*-

"""
Writer document searches such as by font or full document.
"""
import logging
import re

from lingt.access.common import iteruno
from lingt.access.writer.traveler import Traveler
from lingt.app import exceptions
from lingt.ui.common.progressbar import ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.access.TextSearch")


class TextSearchSettings:
    """A structure to hold settings for TextSearch."""
    def __init__(self):
        self.fontName = ""
        self.fontType = ""
        self.style = ""
        self.lang = ""  # two-letter locale code
        self.SFMs = ""
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


class TextSearch:
    """Executes a search in Writer and gets resulting text ranges."""
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
        self.ranger.addRangeList(self.docEnum.footnotes())
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
        """
        This only searches direct formatting, that is, not including styles.
        """
        logger.debug(util.funcName('begin', args=self.config.fontName))
        if self.config.fontType in ['Complex', 'Asian']:
            self.scopeComplexFont()
            return
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchString = ""
        search.SearchAll = True
        attrName = "CharFontName"
        attrs = (
            # trailing comma is required to make a tuple
            util.createProp(attrName, self.config.fontName),
        )
        search.setSearchAttributes(attrs)
        self.doSearch(search)

    def scopeParaStyle(self):
        """self.config.style should be the DISPLAY NAME of a paragraph style.
        For example, LO 4.0 EN-US will find "Default Style" but not "Standard".
        """
        logger.debug(util.funcName('begin'))
        logger.debug("looking for %s", self.config.style)
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchStyles = True
        search.SearchString = self.config.style
        search.SearchAll = True

        self.doSearch(search)

    def scopeCharStyle(self):
        """OO does not currently have a built-in way to search for character
        styles, so we must go through the document to look for the style.

        self.config.style should be the UNDERLYING NAME of a character style.
        For example, "Standard", not "Default Style".
        """
        logger.debug(util.funcName('begin', args=self.config.style))
        for simpleTextSection in self.docEnum.documentSections():
            if simpleTextSection.CharStyleName == self.config.style:
                logger.debug("Found style %s", self.config.style)
                # TextPortions include the TextRange service.
                self.ranger.addRange(simpleTextSection)

    def scopeComplexFont(self):
        """Similar to character styles,
        searching for complex fonts using a search descriptor is currently
        buggy, so we enumerate instead.
        """
        logger.debug(util.funcName('begin'))
        for simpleTextSection in self.docEnum.documentSections():
            if self.config.fontType == "Complex":
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
            if lang in (
                    simpleTextSection.CharLocale.Language,
                    simpleTextSection.CharLocaleComplex.Language,
                    simpleTextSection.CharLocaleAsian.Language):
                # TextPortions include the TextRange service.
                self.ranger.addRange(simpleTextSection)

    def scopeSFMs(self):
        sfm_str = re.sub(r'\\', r'', self.config.SFMs)
        sfms = re.split(r'\s+', sfm_str)
        sfm_expr = r'|'.join(sfms)
        search_regex = r"^\\(" + sfm_expr + ") (.+)$"
        logger.debug("Searching %s", search_regex)

        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchRegularExpression = True
        search.SearchString = search_regex
        self.doSearch(search)

        ## Modify the range starts so that the SFM markers are not included.

        logger.debug("Moving the start to after the SFM marker.")
        for txtRange in self.ranger.getRanges():
            oSel = txtRange.sel
            oText = oSel.getText()
            cursor = oText.createTextCursorByRange(oSel)
            cursor.collapseToStart()
            while cursor.goRight(1, True):
                if cursor.getString().endswith(" "):
                    cursor.collapseToEnd()
                    cursor.gotoRange(oSel.getEnd(), True)
                    txtRange.sel = cursor
                    break
                if oText.compareRegionEnds(cursor, oSel.getEnd()) < 0:
                    logger.debug("passed end")
                    break

    def doSearch(self, search):
        logger.debug(util.funcName('begin'))
        self.ranger.resetRanges()
        selsFound = self.unoObjs.document.findAll(search)
        self.selsCount = selsFound.getCount()
        if self.selsCount == 0:
            logger.debug("Did not find anything.")
            return
        progressRange = ProgressRange(
            start=self.progressBar.val, stop=90, ops=self.selsCount,
            pbar=self.progressBar)
        progressRange.partSize = 2
        progressRange.updatePart(1)  # show some movement

        for selIndex, selectionFound in enumerate(
                iteruno.byIndex(selsFound)):
            logger.debug("Found selection %d", selIndex)
            self.ranger.addRangesForCursor(selectionFound)
            progressRange.update(selIndex)
            if (self.config.matchesLimit > 0
                    and selIndex >= self.config.matchesLimit):
                # Stop here.  This may help with large documents, doing a
                # little at a time.
                logger.debug("Stopping at this match")
                return


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
        return self.textSectionsForParEnum(self.unoObjs.text)

    def textSectionsForParEnum(self, oParEnumerator):
        """Get text sections for all paragraphs that are enumerated by the
        given object.
        Do not pass a cursor inside a table as the oParEnumerator, because it
        will work but the entire table
        or paragraph will be enumerated, not just the selection.
        Instead use addRangesForCursor().
        """
        textSections = []
        i = 0
        for oPar in iteruno.byEnum(oParEnumerator):
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
        if oPar.supportsService("com.sun.star.text.Paragraph"):
            for oTextPortion in iteruno.byEnum(oPar):
                if oTextPortion.TextPortionType == "Text":
                    # TextPortions include the TextRange service.
                    logger.debug("simple text portion")
                    textSectionList.append(oTextPortion)
                elif oTextPortion.TextPortionType == "Frame":
                    logger.debug("Frame text portion")
                    oFrameEnum = oTextPortion.createContentEnumeration(
                        "com.sun.star.text.TextFrame")
                    # always only 1 item?
                    for oFrame in iteruno.fromEnum(oFrameEnum):
                        self.textSectionsOfPar(oFrame, textSectionList)
        elif oPar.supportsService("com.sun.star.text.TextTable"):
            oTable = oPar
            logger.debug("table %s", oTable.getName())
            self.unoObjs.controller.select(oTable)  # go to first cell
            for cellName in oTable.getCellNames():
                logger.debug("cell %s:%s", oTable.getName(), cellName)
                oCell = oTable.getCellByName(cellName)
                for oPar2 in iteruno.byEnum(oCell):
                    self.textSectionsOfPar(oPar2, textSectionList)
        elif oPar.supportsService("com.sun.star.text.TextFrame"):
            oFrame = oPar
            logger.debug("frame %s", oFrame.getName())
            for oPar2 in iteruno.byEnum(oFrame):
                self.textSectionsOfPar(oPar2, textSectionList)
        return textSectionList

    def footnotes(self):
        textSections = []
        logger.debug("looking for footnotes")
        footnotes = self.unoObjs.document.getFootnotes()
        endnotes = self.unoObjs.document.getEndnotes()
        for notes in (footnotes, endnotes):
            for oNote in iteruno.byIndex(notes):
                for oPar in iteruno.byEnum(oNote):
                    if oPar.supportsService("com.sun.star.text.Paragraph"):
                        for oTextPortion in iteruno.byEnum(oPar):
                            if oTextPortion.TextPortionType == "Text":
                                # TextPortions include the TextRange service.
                                textSections.append(oTextPortion)
        return textSections


class TxRanger:
    """Walker for sections and ranges of text."""
    def __init__(self, unoObjs, checkForFormatting):
        self.unoObjs = unoObjs
        self.checkForFormatting = checkForFormatting
        self.ranges = []  # list of TxtRange objects
        self.traveler = None
        self.chunker = None
        self.selFormatting = None  # formatting of selected string

    def resetRanges(self):
        self.ranges = []

    def getRanges(self):
        return self.ranges

    def addRangesForCursor(self, oSel):
        """If there is different formatting, then we handle each string
        separately that is formatted differently.
        """
        logger.debug(util.funcName('begin'))
        if not self.checkForFormatting:
            self.addRange(oSel)
            logger.debug(util.funcName('return'))
            return
        simpleTextRanges = []  # ranges that have only one formatting
        self.traveler = Traveler(self.unoObjs)
        self.traveler.createCursors(oSel)
        self.chunker = Chunker()
        self.selFormatting = None
        while True:
            #logger.debug(
            #   "moreToGo %s", self.traveler.rangeRight.compareVC())
            if (self.traveler.rangeRight.compareVC() == 0
                    or self._formattingChanges()
                    or self.chunker.tooBig()):
                self.addCurrentRange(simpleTextRanges)
                self.selFormatting = None
            if self.traveler.rangeRight.compareVC() < 0:
                if self.moveRight():
                    self.chunker.stringLonger()
                    continue
            # We've reached the end of the string.
            break
        logger.debug(util.funcName('end'))
        self.addRangeList(simpleTextRanges)

    def _formattingChanges(self):
        """Check for formatting changes at the current location."""
        oVC = self.unoObjs.viewcursor
        splitAtFormattingChange = False
        if not self.selFormatting:
            self.selFormatting = Formatting(oVC)
        oVCTextCurs = oVC.getText().createTextCursorByRange(oVC)
        if oVCTextCurs.isEndOfParagraph():
            logger.debug("at end of paragraph")
            splitAtFormattingChange = True
        elif self.traveler.rangeRight.compareVC() < 0:
            # We need to look ahead because the different formatting is
            # only seen when the cursor is on the right side of the
            # character.
            oVC.goRight(1, False)
            #logger.debug(util.debug_tellNextChar(oVC))
            nextFormatting = Formatting(oVC)
            if not nextFormatting.sameCharForm(self.selFormatting):
                logger.debug("found different formatting")
                splitAtFormattingChange = True
            oVC.goLeft(1, False)
        return splitAtFormattingChange

    def addCurrentRange(self, simpleTextRanges):
        cursLeft = self.traveler.cursLeft
        # select the string
        cursLeft.gotoRange(self.unoObjs.viewcursor, True)
        logger.debug(
            "String %d = '%s'", self.chunker.stringNum, cursLeft.getString())
        oTextCursTmp = cursLeft.getText().createTextCursorByRange(cursLeft)
        simpleTextRanges.append(oTextCursTmp)
        cursLeft.goRight(0, False)  # deselect
        self.chunker.nextString()

    def moveRight(self):
        """Returns True on success, like cursor.goRight()."""
        oVC = self.unoObjs.viewcursor
        prevInText = InText(oVC)
        #logger.debug("oVC moveRight")
        if not oVC.goRight(1, False):
            logger.warning("cannot go any further")
            return False
        #logger.debug(util.debug_tellNextChar(oVC))
        nextInText = InText(oVC)
        if not nextInText.inSameText(prevInText):
            ## Going into a new text such as a TextTable.
            logger.debug("Going into new text.")
            self.traveler.cursLeft = oVC.getText().createTextCursorByRange(oVC)
        return True

    def addRangeList(self, rangeList):
        """Convenience function to handle a list."""
        for aRange in rangeList:
            self.addRange(aRange)

    def addRange(self, oSel):
        """Adds the selection to self.ranges
        oSels implements type com.sun.star.text.XTextRange.
        """
        logger.debug(util.funcName('begin'))
        #util.xray(oSel, self.unoObjs)
        txtRange = TxtRange()
        txtRange.sel = oSel     # contains the location range
        txtRange.inTable = False
        txtRange.inFrame = False
        txtRange.inSomething = False

        # These attributes are mentioned in TextRangeContentProperties
        try:
            if oSel.TextTable:
                txtRange.inTable = True
            if oSel.TextFrame:
                txtRange.inFrame = True
            if oSel.TextTable or oSel.TextFrame or oSel.TextField:
                txtRange.inSomething = True
        except AttributeError:
            # leave them all set to False
            pass

        self.ranges.append(txtRange)

        # -- For debugging only --
        # Note: oSel.getString() isn't as reliable as this method.
        #
        #cursor = oSel.getText().createTextCursorByRange(oSel)
        #logger.debug("range text = %s", cursor.getString())
        logger.debug(util.funcName('end'))


class Chunker:
    """Handle text in limited size chunks.
    The limit is pretty large, so most of the time there will probably just
    be a single chunk.
    """
    MAX_STRING_LENGTH = 4096
    def __init__(self):
        self.stringLen = 0
        self.stringNum = 1  # helpful for debugging

    def nextString(self):
        self.stringLen = 0
        self.stringNum += 1

    def stringLonger(self):
        self.stringLen += 1

    def tooBig(self):
        return self.stringLen >= self.MAX_STRING_LENGTH


class TxtRange:
    """A structure to store one range of text."""
    def __init__(self):
        self.sel = None
        self.start = None
        self.end = None
        self.inTable = False
        self.inFrame = False
        self.inSomething = False


class Formatting:
    """To hold cursor formatting attributes such as CharFontName"""
    #ATTR_NAMES = [
    #    'CharFontName', 'CharFontNameAsian', 'CharFontNameComplex',
    #    'CharFontStyleName', 'CharFontStyleNameAsian',
    #    'CharFontStyleNameComplex', 'CharStyleName', 'DropCapCharStyleName',
    #    'CharCombinePrefix', 'CharCombineSuffix',
    #    'HyperLinkName', 'HyperLinkTarget', 'HyperLinkURL',
    #    'ListId', 'ListLabelString',
    #    'NumberingStyleName', 'PageDescName', 'PageStyleName',
    #    'ParaAutoStyleName', 'ParaBackGraphicFilter', 'ParaBackGraphicURL',
    #    'ParaConditionalStyleName', 'ParaStyleName',
    #    'RubyCharStyleName', 'RubyText', 'UnvisitedCharStyleName',
    #    'VisitedCharStyleName', 'CharAutoEscapement', 'CharAutoKerning',
    #    'CharBackTransparent', 'CharCombineIsOn', 'CharContoured',
    #    'CharCrossedOut', 'CharFlash', 'CharHidden', 'CharNoHyphenation',
    #    'CharOverlineHasColor', 'CharRotationIsFitToLine', 'CharShadowed',
    #    'CharUnderlineHasColor', 'CharWordMode', 'ContinueingPreviousSubTree',
    #    'DropCapWholeWord', 'IsSkipHiddenText', 'IsSkipProtectedText',
    #    'NumberingIsNumber', 'ParaBackTransparent', 'ParaExpandSingleWord',
    #    'ParaIsAutoFirstLineIndent', 'ParaIsCharacterDistance',
    #    'ParaIsConnectBorder', 'ParaIsForbiddenRules',
    #    'ParaIsHangingPunctuation', 'ParaIsHyphenation',
    #    'ParaIsNumberingRestart', 'ParaKeepTogether', 'ParaLineNumberCount',
    #    'ParaRegisterModeActive', 'ParaSplit', 'RubyIsAbove', 'SnapToGrid',
    #    'CharCaseMap', 'CharEmphasis', 'CharEscapement',
    #    'CharEscapementHeight', 'CharFontCharSet', 'CharFontCharSetAsian',
    #    'CharFontCharSetComplex', 'CharFontFamily', 'CharFontFamilyAsian',
    #    'CharFontFamilyComplex', 'CharFontPitch', 'CharFontPitchAsian',
    #    'CharFontPitchComplex', 'CharKerning', 'CharOverline', 'CharRelief',
    #    'CharRotation', 'CharScaleWidth', 'CharStrikeout', 'CharUnderline',
    #    'NumberingLevel', 'NumberingStartValue', 'OutlineLevel',
    #    'PageNumberOffset', 'ParaAdjust',
    #    'ParaHyphenationMaxHyphens', 'ParaHyphenationMaxLeadingChars',
    #    'ParaHyphenationMaxTrailingChars', 'ParaLastLineAdjust',
    #    'ParaOrphans', 'ParaVertAlignment', 'ParaWidows', 'RubyAdjust',
    #    'WritingMode', 'BorderDistance', 'BottomBorderDistance',
    #    'BreakType', 'CharBackColor', 'CharColor', 'CharOverlineColor',
    #    'CharPosture', 'CharPostureAsian', 'CharPostureComplex',
    #    'CharUnderlineColor', 'LeftBorderDistance', 'ParaBackColor',
    #    'ParaBackGraphicLocation', 'ParaBottomMargin',
    #    'ParaFirstLineIndent', 'ParaLeftMargin', 'ParaLineNumberStartValue',
    #    'ParaRightMargin', 'ParaTopMargin', 'RightBorderDistance',
    #    'TopBorderDistance', 'CharHeight', 'CharHeightAsian',
    #    'CharHeightComplex']

    ## The value CharAutoStyleName is apparently a summary of formatting.
    ## It is MUCH faster than checking for each different type of formatting.
    ## In addition to formatting, check for character styles (CharStyleName).
    ATTR_NAMES = ['CharAutoStyleName', 'CharStyleName']

    def __init__(self, oSel):
        self.attrs = {}
        for attr in self.ATTR_NAMES:
            self.attrs[attr] = ""
            if oSel is not None:
                self.attrs[attr] = oSel.getPropertyValue(attr)
                #logger.debug(
                #    "%s attr %s = %s",
                #    oSel.getString(), attr, self.attrs[attr])

    def sameCharForm(self, otherFormatting):
        for attr in self.ATTR_NAMES:
            if self.attrs[attr] != otherFormatting.attrs[attr]:
                #logger.debug(
                #    "%s '%s' != '%s'",
                #    attr, self.attrs[attr], otherFormatting.attrs[attr])
                return False
        #logger.debug("same formatting")
        return True


def getContainerName(cursor, containerType):
    if containerType == 'CellName':
        if cursor.Cell:
            return cursor.Cell.CellName
    elif containerType == 'TextTable':
        if cursor.TextTable:
            return cursor.TextTable.getName()
    elif containerType == 'TextFrame':
        if cursor.TextFrame:
            return cursor.TextFrame.getName()
    return ""

class InText:
    """To hold cursor attributes about which text we are in."""
    #CONTAINER_TYPES = ['CharAutoStyleName', 'TextTable', 'TextFrame', 'Cell',
    #                   'TextSection', 'TextField', 'Footnote']
    CONTAINER_TYPES = ['TextTable', 'CellName', 'TextFrame']

    def __init__(self, cursor):
        self.containers = {}
        for container in self.CONTAINER_TYPES:
            self.containers[container] = ""
            if cursor is not None:
                self.containers[container] = getContainerName(
                    cursor, container)

    def inSameText(self, otherFormatting):
        for container in self.CONTAINER_TYPES:
            if (self.containers[container] !=
                    otherFormatting.containers[container]):
                return False
        return True

    def describeComparison(self, otherFormatting):
        for container in self.CONTAINER_TYPES:
            if (self.containers[container] !=
                    otherFormatting.containers[container]):
                return "%s != %s" % (
                    self.containers[container],
                    otherFormatting.containers[container])
        return "seem to be the same"
