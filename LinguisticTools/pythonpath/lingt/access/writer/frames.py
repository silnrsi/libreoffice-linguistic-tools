"""
Create TextFrames in Writer.
"""
import logging
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.SizeType import FIX, VARIABLE

from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.access.Frames")

def set_noFrameBorders(textFrame):
    """Sets a TextFrame to have no borders."""
    BORDER_WIDTH = 0
    borderLine = textFrame.getPropertyValue("LeftBorder")
    borderLine.OuterLineWidth = BORDER_WIDTH
    textFrame.setPropertyValue("LeftBorder", borderLine)
    textFrame.setPropertyValue("RightBorder", borderLine)
    textFrame.setPropertyValue("TopBorder", borderLine)
    textFrame.setPropertyValue("BottomBorder", borderLine)

class InterlinFrames:
    def __init__(self, config, outerTable, unoObjs):
        """config should be of type lingex_structs.InterlinOutputSettings."""
        self.config = config
        self.outerTable = outerTable
        self.unoObjs = unoObjs
        self.styles = self.outerTable.styles
        self.msgbox = MessageBox(unoObjs)
        self.frameOuter = None
        self.framecursorOuter = None

    def createOuterFrame(self):
        """Create a new outer frame for the word."""
        logger.debug(util.funcName('begin'))
        frameOuter = self.unoObjs.document.createInstance(
            "com.sun.star.text.TextFrame")
        self.styles.requireFrameStyle('intF')
        frameOuter.setPropertyValue(
            "FrameStyleName", self.styles.styleNames['intF'])

        # Starting with variable size is exceedingly slow for CTL fonts.
        # After the first character is inserted,
        # we can change it back to variable size and it will work fine after
        # that.
        #
        # The width type doesn't seem to get taken from the style.

        frameOuter.WidthType = FIX
        frameOuter.Width = 0.5 * 2540   # 0.5 inches
        self.outerTable.text.insertTextContent(
            self.outerTable.cursor, frameOuter, False)
        logger.debug("Created outer frame %s", frameOuter.getName())

        # Get cursor in main column
        self.frameOuter = frameOuter
        self.framecursorOuter = frameOuter.createTextCursor()

    def insertInnerFrameData(self, word, isFirst, isLast):
        """Insert data into the outer frame.
        Optionally creates an inner frame for morpheme breaks.
        Expects word.morph to be set.
        Requires self.frameOuter, self.framecursorOuter
        """
        if word.morph is None:
            logger.error("Expected a single morph to be set.")
            return
        logger.debug(
            "%s: Adding frame '%s'", util.funcName(), word.morph.gloss)

        ## Word Text Lines 1 and 2

        if isFirst:
            if self.config.showWordText1:
                self._insertFrameData(
                    self.frameOuter, self.framecursorOuter, 'wordTx1',
                    word.text1)
            if self.config.showWordText2:
                self._insertFrameData(
                    self.frameOuter, self.framecursorOuter, 'wordTx2',
                    word.text2)

        frameForMorph = None    # either outer or inner frame
        if self.config.separateMorphColumns:
            ## Create an inner frame for morpheme breaks.

            frameInner = self.unoObjs.document.createInstance(
                "com.sun.star.text.TextFrame")
            self.styles.requireFrameStyle('morF')
            frameInner.setPropertyValue(
                "FrameStyleName", self.styles.styleNames['morF'])
            frameInner.WidthType = FIX
            frameInner.Width = 0.5 * 2540   # 0.5 inches
            self.frameOuter.insertTextContent(
                self.framecursorOuter, frameInner, False)
            logger.debug("Created text frame %s", frameInner.getName())

            frameForMorph = frameInner
            framecursor = frameInner.createTextCursor()
        else:
            frameForMorph = self.frameOuter
            framecursor = self.framecursorOuter

        ## Morpheme Text Lines 1 and 2

        if self.config.showMorphText1:
            self._insertFrameData(
                frameForMorph, framecursor, 'morphTx1', word.morph.text1)
        if self.config.showMorphText2:
            self._insertFrameData(
                frameForMorph, framecursor, 'morphTx2', word.morph.text2)

        ## Morpheme Part of Speech - first option

        if self.config.showMorphPos and not self.config.morphPosBelowGloss:
            self._insertFrameData(
                frameForMorph, framecursor, 'morphPos', word.morph.pos)

        ## Morpheme Gloss

        if self.config.showMorphGloss:
            self._insertFrameData(
                frameForMorph, framecursor, 'morphGloss', word.morph.gloss,
                parabreak='nobreak')

        ## Morpheme Part of Speech - second option

        if self.config.showMorphPos and self.config.morphPosBelowGloss:
            self._insertFrameData(
                frameForMorph, framecursor, 'morphPos', word.morph.pos,
                parabreak='before')

        ## Word Gloss

        if isLast:
            if self.config.showWordGloss:
                self._insertFrameData(
                    self.frameOuter, self.framecursorOuter, 'wordGloss',
                    word.gloss, parabreak='before')
        logger.debug(util.funcName('end'))

    def _insertFrameData(self, frame, frameCursor, paraStyleKey, strData,
                         parabreak='after'):
        """:param parabreak: either 'before', 'after', or 'nobreak'"""
        logger.debug("frame data style key %s", paraStyleKey)
        # FIXME: 13-Aug-2015 AOO crashed on 'orthm' while inserting Hunt06.
        if parabreak == 'before':
            frame.insertControlCharacter(frameCursor, PARAGRAPH_BREAK, 0)
        self.styles.requireParaStyle(paraStyleKey)
        frameCursor.setPropertyValue(
            "ParaStyleName", self.styles.styleNames[paraStyleKey])
        frame.insertString(frameCursor, strData, 0)
        if parabreak == 'after':
            frame.insertControlCharacter(frameCursor, PARAGRAPH_BREAK, 0)
        frame.WidthType = VARIABLE
        # in case it hasn't been done yet.
        self.frameOuter.WidthType = VARIABLE

    def insertInnerTempSpace(self, useOuterTable=False):
        """In LibreOffice 4.0 frames get resized improperly if there
        is only one inner frame.  A simple fix is to add and remove a space.
        """
        text = self.frameOuter
        cursor = self.framecursorOuter
        if useOuterTable:
            text, cursor = self.outerTable.getCursorObjs()
        text.insertString(cursor, " ", 0)
        cursor.collapseToEnd()
        cursor.goLeft(0, False)
        cursor.goLeft(1, True)
        cursor.setString("")
