# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 23-Sep-10 JDK  Orthography is at word rather than sentence level.
# 01-Oct-10 JDK  First check if styles exist in order to avoid silent crash.
# 15-Apr-13 JDK  Added insertInnerTempSpace().
# 18-Apr-13 JDK  Make insertInnerTempSpace() handle outer cursor as well.
# 29-Jul-13 JDK  Import constants instead of using uno.getConstantByName.
# 30-Jul-15 JDK  Added _insertFrameData().
# 15-Aug-15 JDK  Fixed bug: No paragraph break after last inner frame line.

"""
Create TextFrames in Writer.
"""
import logging
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.SizeType import FIX, VARIABLE

from lingt.ui.messagebox import MessageBox
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
        """config should be of type outputmanager.InterlinSettings."""
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

    def insertInnerFrameData(self, word, firstMorph):
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

        ## Orthographic Word

        if firstMorph and self.config.showOrthoTextLine:
            self._insertFrameData(
                self.frameOuter, self.framecursorOuter, 'orth', word.orth)
            self.framecursorOuter.setPropertyValue("ParaStyleName", "Standard")

        ## Word

        if firstMorph and self.config.showText:
            self._insertFrameData(
                self.frameOuter, self.framecursorOuter, 'text', word.text)
            self.framecursorOuter.setPropertyValue("ParaStyleName", "Standard")

        frameForGloss = None    # either outer or inner frame
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

            frameForGloss = frameInner
            framecursor = frameInner.createTextCursor()
        else:
            frameForGloss = self.frameOuter
            framecursor = self.framecursorOuter

        ## Orthographic Morpheme

        if self.config.showOrthoMorphLine:
            self._insertFrameData(
                frameForGloss, framecursor, 'orthm', word.morph.orth)

        ## Morpheme

        if self.config.showMorphemeBreaks:
            self._insertFrameData(
                frameForGloss, framecursor, 'morph', word.morph.text)

        ## Part of Speech - first option

        if self.config.showPartOfSpeech and self.config.POS_aboveGloss:
            self._insertFrameData(
                frameForGloss, framecursor, 'pos', word.morph.pos)

        ## Gloss

        self._insertFrameData(
            frameForGloss, framecursor, 'gloss', word.morph.gloss,
            parabreak='nobreak')

        ## Part of Speech - second option

        if self.config.showPartOfSpeech and not self.config.POS_aboveGloss:
            self._insertFrameData(
                frameForGloss, framecursor, 'pos', word.morph.pos,
                parabreak='before')
        logger.debug(util.funcName('end'))

    def _insertFrameData(self, frame, frameCursor, paraStyleKey, strData,
                         parabreak='after'):
        """:param parabreak: either 'before', 'after', or 'nobreak'"""
        logger.debug("frame data style key %s", paraStyleKey)
        # FIXME: 13-Aug-15 AOO crashed on 'orthm' while inserting Hunt06.
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
