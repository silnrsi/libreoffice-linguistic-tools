# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 23-Sep-10 JDK  Orthography is at word rather than sentence level.
# 01-Oct-10 JDK  First check if styles exist in order to avoid silent crash.
# 29-Oct-10 JDK  When replacing #ref, don't insert an extra newline.
# 13-Nov-10 JDK  Modified error message.
# 12-Nov-12 JDK  Move grammar and phonology into subclasses.
# 11-Mar-13 JDK  Use setPropertyToDefault instead of setting to "Default".
# 11-Apr-13 JDK  Wait until after inserting example to delete newline.
# 17-Apr-13 JDK  setAllPropertiesToDefault() doesn't work for styles.
# 18-Apr-13 JDK  Remember what the styles of the next line were set to.
# 06-May-13 JDK  Remember fonts too.

"""
Sends output to Writer.
"""
import logging
import copy
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.uno import RuntimeException

from lingt.access.writer.frames import InterlinFrames
from lingt.access.writer.tables import OuterTable, InterlinTables
from lingt.app import exceptions
from lingt.app.data import lingex_structs
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.access.OutputManager")

class ExampleManager:
    """
    Abstract base class to manage output of linguistic examples to the Writer
    document.
    """
    def __init__(self, unoObjs, styles):
        if self.__class__ is ExampleManager:
            # The base class should not be instantiated.
            raise NotImplementedError
        self.unoObjs = unoObjs
        self.styles = styles
        self.styleNames = styles.styleNames
        self.msgbox = MessageBox(unoObjs)
        self.exnumRanges = []
        self.textcursor = None
        self.config = None

    def setConfig(self, config):
        """Set options."""
        # Derived classes should implement this method.
        raise NotImplementedError

    def outputExample(self, example, deleteRefNum, updatingEx):
        """Output the example to the Writer document."""
        logger.debug(util.funcName('begin'))
        oVC = self.unoObjs.viewcursor   # shorthand variable name

        ## Delete the selected reference number

        extraNewline = False # newline from ref number
        if deleteRefNum:
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:SwBackspace", "", 0, ())
            if oVC.isAtEndOfLine():
                extraNewline = True

        ## Start with default formatting at the beginning

        if oVC.TextTable or oVC.TextFrame:
            raise exceptions.RangeError("Cannot be inside a table or frame.")
        elif oVC.getText().getImplementationName() == "SwXHeadFootText":
            raise exceptions.RangeError("Cannot be in a header or footer.")
        try:
            self.textcursor = self.unoObjs.text.createTextCursorByRange(
                oVC.getStart())
        except (RuntimeException, IllegalArgumentException):
            raise exceptions.RangeError("Cannot insert text here.")
        logger.debug("Created a text cursor.")
        propNames = [
            'ParaStyleName', 'CharStyleName', 'CharFontName',
            'CharFontNameComplex', 'CharFontNameAsian', 'CharHeight',
            'CharHeightComplex', 'CharHeightAsian']
        nextProps = dict()
        if self.textcursor.goRight(1, False):
            # Look ahead for next style and font
            for propName in propNames:
                nextProps[propName] = self.textcursor.getPropertyValue(
                    propName)
            self.textcursor.goLeft(1, False)
        self.textcursor.setAllPropertiesToDefault() # works for fonts
        self.textcursor.setPropertyValue('ParaStyleName', 'Standard')
        self.textcursor.setPropertyToDefault('CharStyleName')

        ## Insert examples

        logger.debug("Writing example.")
        self.insertEx(example, updatingEx)
        self.unoObjs.text.insertControlCharacter(
            self.textcursor, PARAGRAPH_BREAK, 0)
        for propName in propNames:
            propVal = ""
            if propName in nextProps:
                propVal = nextProps[propName]
            if propVal:
                ## Set property to look-ahead value
                logger.debug("PropName '%s' = '%s'", propName, propVal)
                self.textcursor.setPropertyValue(propName, propVal)
            else:
                ## Set property to default value
                if propName == 'ParaStyleName':
                    # Setting ParaStyleName to its default does not work.
                    # So we use the underlying default style name "Standard".
                    self.textcursor.setPropertyValue(propName, 'Standard')
                else:
                    self.textcursor.setPropertyToDefault(propName)
        if extraNewline:
            # Delete the extra newline from the #ref number.
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:Delete", "", 0, ())
        if updatingEx:
            # Go back to end of line before paragraph break,
            # in order to be ready to find the next ref number.
            oVC.goLeft(1, False)
        logger.debug("outputExamples FINISH")

    def insertEx(self, ex, updatingEx):
        # Derived classes should implement this method.
        raise NotImplementedError


class PhonMgr(ExampleManager):
    """Manages output of phonology examples."""
    def __init__(self, unoObjs, styles):
        ExampleManager.__init__(self, unoObjs, styles)

    def setConfig(self, config):
        """config should be of type lingex_structs.PhonSettings."""
        self.config = config

    def insertEx(self, ex, dummy_updatingEx):
        """ex is of type LingPhonExample"""
        self.styles.requireParaStyle('exPara')
        self.textcursor.setPropertyValue(
            "ParaStyleName", self.styleNames['exPara'])
        ex = copy.copy(ex)  # so we don't modify the original data
        if self.config.showBrackets:
            ex.phonemic = "/%s/" % ex.phonemic
            ex.phonetic = "[%s]" % ex.phonetic
            ex.gloss = "'%s'" % ex.gloss

        if self.config.phonemicLeftmost:
            self.styles.requireCharStyle('phonemic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonemic'])
            self.unoObjs.text.insertString(
                self.textcursor, "\t" + ex.phonemic + "\t", 0)
            self.styles.requireCharStyle('phonetic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonetic'])
            self.unoObjs.text.insertString(
                self.textcursor, ex.phonetic + "\t", 0)
        else:
            self.styles.requireCharStyle('phonetic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonetic'])
            self.unoObjs.text.insertString(
                self.textcursor, "\t" + ex.phonetic + "\t", 0)
            self.styles.requireCharStyle('phonemic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonemic'])
            self.unoObjs.text.insertString(
                self.textcursor, ex.phonemic + "\t", 0)

        self.styles.requireCharStyle('gloss')
        self.textcursor.setPropertyValue(
            "CharStyleName", self.styleNames['gloss'])
        self.unoObjs.text.insertString(
            self.textcursor, ex.gloss + "\t", 0)
        self.styles.requireCharStyle('ref')
        self.textcursor.setPropertyValue(
            "CharStyleName", self.styleNames['ref'])
        self.unoObjs.text.insertString(
            self.textcursor, ex.refText, 0)


class InterlinMgr(ExampleManager):
    """Manages output of interlinear examples."""
    def __init__(self, unoObjs, styles):
        ExampleManager.__init__(self, unoObjs, styles)
        self.outerTable = None

    def setConfig(self, config):
        """config should be of type lingex_structs.InterlinOutputSettings."""
        self.config = config

    def insertEx(self, ex, updatingEx):
        """ex is of type LingGramExample"""
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        self.outerTable = OuterTable(
            self.unoObjs, self.config, self.exnumRanges, updatingEx,
            self.styles)
        self.outerTable.create(self.textcursor)

        ## Add word data

        logger.debug("Adding %d words.", len(ex.wordList))
        if self.config.methodTables:
            interlinTables = InterlinTables(
                self.config, self.outerTable, self.unoObjs)
            for word in ex.wordList:
                interlinTables.addWordData(word)
            interlinTables.cleanupMarkers()
            self.outerTable.resize()
        elif self.config.methodFrames:
            frame_count = 0
            interlinFrames = InterlinFrames(
                self.config, self.outerTable, self.unoObjs)
            insertedNewlineRanges = []
            for word in ex.wordList:
                frame_count = self._addFrameData(
                    word, interlinFrames, frame_count, insertedNewlineRanges)
            if len(ex.wordList) == 1:
                interlinFrames.insertInnerTempSpace(useOuterTable=True)

            ## Now remove the extra newlines we inserted

            logger.debug("Removing any extra newlines.")
            self.outerTable.resize()
            originalRange = oVC.getStart()
            for txtRange in insertedNewlineRanges:
                oVC.gotoRange(txtRange, False)
                # Note: IsAutoHeight of the outer table should be True
                # before calling uno:SwBackspace.
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:SwBackspace", "", 0, ())
            oVC.gotoRange(originalRange, False)

        self._addFT_and_ref(ex)

    def _addFrameData(self, word, interlinFrames, frame_count,
                      insertedNewlineRanges):
        INSERT_AFTER = 30  # insert a newline after so many frames
        interlinFrames.createOuterFrame()
        frame_count += 1
        logger.debug("Adding %d morphemes.", len(word.morphList))
        isFirstMorph = True
        for morph in word.morphList:
            wordOneMorph = lingex_structs.LingGramWord()
            wordOneMorph.orth = word.orth
            wordOneMorph.text = word.text
            wordOneMorph.morph = morph
            interlinFrames.insertInnerFrameData(wordOneMorph, isFirstMorph)
            frame_count += 1
            isFirstMorph = False
        if len(word.morphList) == 1:
            interlinFrames.insertInnerTempSpace(useOuterTable=False)
        if frame_count >= INSERT_AFTER:
            ## Insert a newline because if there are a lot of
            ## frames without newlines, then inserting frames
            ## becomes very slow.
            logger.debug("Temporarily adding a newline.")
            self.outerTable.text.insertControlCharacter(
                self.outerTable.cursor, PARAGRAPH_BREAK, 0)
            insertedNewlineRanges.append(self.outerTable.cursor.getEnd())
            frame_count = 0
        return frame_count

    def _addFT_and_ref(self, ex):
        """
        Add free translation and reference.
        Add extra space at the end with default formatting.
        """
        logger.debug("Adding free translation")
        oVC = self.unoObjs.viewcursor  # shorthand variable name
        if self.config.methodFrames:
            self.outerTable.text.insertControlCharacter(
                self.outerTable.cursor, PARAGRAPH_BREAK, 0)
        self.styles.requireParaStyle('ft')
        self.outerTable.cursor.setPropertyValue(
            "ParaStyleName", self.styleNames['ft'])
        ex = copy.copy(ex)  # so we don't modify the original data
        if self.config.freeTransInQuotes:
            ex.freeTrans = "'%s'" % ex.freeTrans
        self.outerTable.text.insertString(
            self.outerTable.cursor, ex.freeTrans, 0)
        spacer = " " * 4    # four spaces, probably in fixed-width font
        self.outerTable.text.insertString(
            self.outerTable.cursor, spacer + ex.refText, 1) # select
        self.styles.requireCharStyle('ref')
        self.outerTable.cursor.setPropertyValue(
            "CharStyleName", self.styleNames['ref'])
        self.outerTable.cursor.collapseToEnd()
        self.outerTable.cursor.goRight(0, False) # deselect

        ## Add extra space at the end with default formatting

        if self.config.makeOuterTable:
            # viewcursor should be in numbering column after (),
            # because it goes in the first column when a table gets created.
            #
            # Go to beginning of next line.
            logger.debug("going after outer table")
            oVC.goDown(1, False)
            oVC.gotoStartOfLine(False)
        else:
            # viewcursor should be at end of ref number,
            # because it keeps being moved each time we insert something.
            logger.debug("adding para break")
            self.outerTable.text.insertControlCharacter(
                self.outerTable.cursor, PARAGRAPH_BREAK, 0)
            self.outerTable.cursor.setPropertyValue(
                'ParaStyleName', 'Standard')
            self.outerTable.cursor.setPropertyToDefault('CharStyleName')
            oVC.gotoRange(self.outerTable.cursor.getEnd(), False)
        self.textcursor = self.unoObjs.text.createTextCursorByRange(
            oVC.getStart())

    def addExampleNumbers(self):
        """Inserts example numbers at the specified locations.
        self.exnumRanges is of type com.sun.star.text.XTextRange.

        This function is needed because the .uno:InsertField call seems
        to fail when called within a dialog event handler.
        API calls succeed, but there does not seem to be a way to create
        a "Number Range" master field or text field with the API,
        only SetExpression items which are not as flexible.
        """
        logger.debug(util.funcName('begin'))

        originalRange = self.unoObjs.viewcursor.getStart()
        for exnumRange in self.exnumRanges:
            logger.debug("Going to a range.")
            try:
                self.unoObjs.viewcursor.gotoRange(exnumRange, False)
            except (IllegalArgumentException, RuntimeException):
                # Give up on this range and go on to the next one.
                logger.warning("Failed to locate range.")
                continue
            if (self.config.methodTables and
                    self.config.insertNumbering and
                    not self.config.makeOuterTable):
                ## Delete "xxxx" that we inserted earlier.
                self.unoObjs.viewcursor.goRight(4, True)
                self.unoObjs.viewcursor.String = ""
            uno_args = (
                util.createProp("Type", 23),
                util.createProp("SubType", 127),
                util.createProp("Name", "AutoNr"),
                util.createProp("Content", ""),
                util.createProp("Format", 4),
                util.createProp("Separator", " ")
            )
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:InsertField", "", 0, uno_args)
            logger.debug("Inserted AutoNr field")
        self.unoObjs.viewcursor.gotoRange(originalRange, False)
        logger.debug(util.funcName('end'))


class AbbrevManager:
    """Sends output to the Writer doc."""

    def __init__(self, unoObjs, styles):
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.styleNames = styles.styleNames
        self.styles = styles
        logger.debug("AbbrevManager init() finished")

    def outputList(self, abbrevList):
        logger.debug(util.funcName('begin'))

        ## Start with default formatting at the beginning

        oVC = self.unoObjs.viewcursor
        if oVC.TextTable or oVC.TextFrame:
            self.msgbox.display(
                "The cursor cannot be inside a table or frame.")
            return
        elif oVC.getText().getImplementationName() == "SwXHeadFootText":
            self.msgbox.display("The cursor cannot be in a header or footer.")
            return
        textcursor = self.unoObjs.text.createTextCursorByRange(
            self.unoObjs.viewcursor.getStart())
        logger.debug("Created a text cursor.")
        textcursor.setPropertyValue('ParaStyleName', 'Standard')
        textcursor.setPropertyToDefault('CharStyleName')

        didOutput = False
        for abbr in abbrevList:
            if not abbr.shouldOutput():
                logger.debug("Skipping abbrev %s.", abbr.abbrevText)
                continue
            logger.debug("Outputting abbrev %s.", abbr.abbrevText)
            didOutput = True
            self.styles.requireParaStyle('abbr')
            textcursor.setPropertyValue(
                "ParaStyleName", self.styleNames['abbr'])
            abbr_str = abbr.abbrevText + "\t" + abbr.fullName
            self.unoObjs.text.insertString(textcursor, abbr_str, 0)
            self.unoObjs.text.insertControlCharacter(
                textcursor, PARAGRAPH_BREAK, 0)

        if didOutput:
            self.unoObjs.text.insertControlCharacter(
                textcursor, PARAGRAPH_BREAK, 0)
            textcursor.setPropertyValue("ParaStyleName", "Standard")
        else:
            self.unoObjs.text.insertString(
                textcursor, "No abbreviations found.", 0)
            self.unoObjs.text.insertControlCharacter(
                textcursor, PARAGRAPH_BREAK, 0)
        logger.debug(util.funcName('end'))

