# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 23-Sep-10 JDK  Orthography is at word rather than sentence level.
# 01-Oct-10 JDK  First check if styles exist in order to avoid silent crash.
# 04-Oct-10 JDK  Don't save numbering ranges when updating.
# 20-Oct-10 JDK  Optimizing a tall inner table requires adjustable outer row.
# 26-Oct-10 JDK  Set bottom margin on the table rather than POS or gloss.
# 12-Aug-11 JDK  Fix problem where inner tables can get out of order.
# 18-Apr-13 JDK  Don't delete final added newline of inner table.
# 29-Jul-15 JDK  Refactor into two classes.
# 18-Sep-15 JDK  Fixed bug: Should say not self.innerTable.doesWordFit().
# 21-Sep-15 JDK  Make wordRow_col() work without any word rows.
# 17-Feb-17 JDK  Word Line 1 and 2 instead of Orthographic and Text.

"""
Create TextTables for interlinear data.
"""
import logging

from com.sun.star.table import BorderLine

from lingt.app import exceptions
from lingt.app.data import lingex_structs
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.access.Tables")

INCH_TO_CM = 2540  # convert 1/1000 cm to inches

class OuterTable:
    """Table for numbering that contains frames or smaller tables where the
    data is.
    """
    def __init__(self, unoObjs, config, exnumRanges, updatingEx, styles):
        """config should be of type lingex_structs.InterlinOutputSettings."""
        self.unoObjs = unoObjs
        self.config = config
        self.exnumRanges = exnumRanges
        self.updatingEx = updatingEx
        self.styles = styles
        self.cursor = None
        self.text = None
        self.top_row = None

    def create(self, mainTextcursor):
        """Create outer table with example number in smaller left column and
        data in larger right column.
        Leaves viewcursor in smaller left column to the right of "()"
        """
        logger.debug(util.funcName('begin'))
        unoObjs = self.unoObjs  # shorthand variable name
        if self.config.makeOuterTable:
            outer_table = unoObjs.document.createInstance(
                "com.sun.star.text.TextTable")
            outer_table.initialize(1, 2)    # 1 row, 2 columns
            unoObjs.text.insertTextContent(mainTextcursor, outer_table, False)
            set_noTableSpacing(outer_table, self.unoObjs)
            outer_table.Split = False # Text Flow -> don't split pages
            outer_table.KeepTogether = True  # Text Flow -> keep w/next para
            rows = outer_table.getRows()
            self.top_row = rows.getByIndex(0)
            self.fixedSize()
            logger.debug("Created outer table %s.", outer_table.getName())
            self.insertNumberInTable(outer_table)

            # Get cursor in main column
            self.text = outer_table.getCellByPosition(1, 0) # second col
            self.cursor = self.text.createTextCursor()
        else:
            self.text = unoObjs.text
            self.cursor = unoObjs.text.createTextCursorByRange(
                mainTextcursor.getStart())
            if self.config.methodFrames:
                self.insertNumberInText(self.text, self.cursor)

        logger.debug(util.funcName('end'))
        return self.text, self.cursor

    def getCursorObjs(self):
        return self.text, self.cursor

    def fixedSize(self):
        """We set the table to a fixed size because inserting contents is
        faster this way.
        Requires self.top_row.
        """
        if self.config.makeOuterTable:
            self.top_row.IsAutoHeight = False
            self.top_row.Height = \
                self.config.startingOuterRowHeight * INCH_TO_CM

    def resize(self):
        """After the contents of the table are inserted, call this method
        to size the table correctly.
        """
        if self.config.makeOuterTable:
            self.top_row.IsAutoHeight = True

    def insertNumberInTable(self, table, isInnerTable=False):
        """Typically used to insert example numbering in the outer table."""
        cell = table.getCellByPosition(0, 0)  # first column
        self.insertNumberInText(
            cell, cell.createTextCursor(), isInnerTable)
        separators = table.getPropertyValue("TableColumnSeparators")
        if separators is not None and len(separators) > 0:
            logger.debug(
                "Resizing column to %d", self.config.numberingColumnWidth)
            PERCENT_TO_SEP = 100  # Separator width 10,000 is 100%.
            separators[0].Position = \
                self.config.numberingColumnWidth * PERCENT_TO_SEP
            table.TableColumnSeparators = separators
        else:
            logger.debug("No separators to resize.")

    def insertNumberInText(self, text, cursor, innerTableNumbering=False):
        """Insert the example autonumber field.
        Actually just insert xxxx for a placeholder.
        Later the number will be added when the dialog is closed.
        """
        logger.debug(util.funcName('begin'))
        if self.config.insertNumbering or self.config.makeOuterTable:
            # Set example number margin so it lines up with the table.
            self.styles.requireParaStyle('numP')
            cursor.setPropertyValue(
                "ParaStyleName", self.styles.styleNames['numP'])

            text.insertString(cursor, "(", 0)  # Add parenthesis around number.
            # Since inserting fields does not work from within a dialog,
            # we save the range until after the dialog is closed.
            if self.config.insertNumbering and not self.updatingEx:
                logger.debug("Adding range.")
                self.exnumRanges.append(cursor.getEnd())
            if innerTableNumbering:
                # Even though we can't insert the number yet, we need to keep
                # the proper width for when the table is optimized.
                cursor.goRight(0, False)  # deselect
                text.insertString(cursor, "xxxx", 0)
            cursor.goRight(0, False)  # deselect
            text.insertString(cursor, ")", 0)
            if self.config.methodFrames and not self.config.makeOuterTable:
                text.insertString(cursor, "  ", 0)


class InterlinTables:
    """Inner tables that contain word data.
    These are used in place of lingt.access.writer.frames.
    """
    def __init__(self, config, outerTable, unoObjs):
        """config should be of type outputmanager.InterlinSettings."""
        self.config = config
        self.outerTable = outerTable
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.wrappingManager = WrappingManager(config, outerTable, unoObjs)

    def addWordData(self, word):
        """Add columns for one word, many morphemes.
        Creates another line (a new inner table) if word does not fit on
        current line.
        """
        logger.debug(util.funcName('begin'))
        for dummy_which_line in ("current", "wrap to another"):
            morphRow_startCol = self.wrappingManager.prepareWordColumns(
                len(word.morphList))
            for morph_i, morph in enumerate(word.morphList):
                self._insertMorphColumnData(
                    word, morph, morphRow_startCol, morph_i)
            if self.wrappingManager.fit_word_on_line():
                logger.debug(util.funcName('return'))
                return
            logger.debug("Wrapping to next line.")
        raise exceptions.LogicError("Word failed to fit properly.")

    def _insertMorphColumnData(self, word, morph, morphRow_startCol, morph_i):
        """Add interlinear data for a single column."""
        wordOneMorph = lingex_structs.LingGramWord()
        wordOneMorph.text1 = word.text1
        wordOneMorph.text2 = word.text2
        wordOneMorph.morph = morph
        self._insertColumnData(
            wordOneMorph, morphRow_startCol + morph_i, (morph_i == 0))
        self.wrappingManager.innerTable.lastColFilled = True

    def _insertColumnData(self, word, morphRow_col, isFirstMorph):
        """Add interlinear data for a single column.
        Expects word.morph to be set.
        Requires self.wrappingManager.innerTable.
        """
        wordRow_col = self.wrappingManager.wordRow_col()
        if word.morph is None:
            logger.error("Expected a single morph to be set.")
            return
        logger.debug(
            "Adding data '%s' to word col %d, morph col %d",
            word.morph.gloss, wordRow_col, morphRow_col)
        row = -1

        # Word Line 1 and 2
        word1args = (
            self.config.showWordLine1, wordRow_col, row, 'word1', word.text1,
            isFirstMorph)
        word2args = (
            self.config.showWordLine2, wordRow_col, row, 'word2', word.text2,
            isFirstMorph)
        row = self._insertWordData(*word1args)
        row = self._insertWordData(*word2args)

        # Morphemes Line 1 and 2
        morph1args = (
            self.config.showMorphLine1, morphRow_col, row, 'morph1',
            word.morph.text1)
        morph2args = (
            self.config.showMorphLine2, morphRow_col, row, 'morph2',
            word.morph.text2)
        row = self._insertMorphData(*morph1args)
        row = self._insertMorphData(*morph2args)

        # Gloss
        if self.config.POS_aboveGloss:
            row += 2
        else:
            row += 1
        self._insertCellData(morphRow_col, row, 'gloss', word.morph.gloss)

        # Part of Speech
        if self.config.showPartOfSpeech:
            if self.config.POS_aboveGloss:
                row -= 1
            else:
                row += 1
            self._insertCellData(morphRow_col, row, 'pos', word.morph.pos)
        logger.debug(util.funcName('end'))

    def _insertWordData(self, show_line, col, row, paraStyleKey, strData,
                        isFirstMorph):
        if show_line:
            if isFirstMorph:
                self._insertCellData(col, row, paraStyleKey, strData)
            return row + 1
        return row

    def _insertMorphData(self, show_line, col, row, paraStyleKey, strData):
        if show_line:
            self._insertCellData(col, row, paraStyleKey, strData)
            return row + 1
        return row

    def _insertCellData(self, col, row, paraStyleKey, strData):
        cellInner = self.wrappingManager.innerTable.table.getCellByPosition(
            col, row)
        cellcursorInner = cellInner.createTextCursor()
        self.outerTable.styles.requireParaStyle(paraStyleKey)
        cellcursorInner.setPropertyValue(
            "ParaStyleName", self.outerTable.styles.styleNames[paraStyleKey])
        cellInner.insertString(cellcursorInner, strData, 0)

    def cleanupMarkers(self):
        self.wrappingManager.cleanupMarkers()


class WrappingManager:
    """Adds or removes columns and inner tables for best fit."""
    def __init__(self, config, outerTable, unoObjs):
        """config should be of type outputmanager.InterlinSettings."""
        self.config = config
        self.outerTable = outerTable
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.updatingEx = False

        self.innerTable = None  # the most recently created inner table
        self.markers = []  # marked locations in text
        self.numRows = 0

    def prepareWordColumns(self, num_morphs):
        """Create all new column(s) needed for all morphs of a word."""
        if self.innerTable is None:
            # This is needed for the first word of the example.
            self.createInnerTable()

        return self.innerTable.prepareWordColumns(num_morphs)

    def fit_word_on_line(self):
        """Check if the word fits on the current line, or whether
        we need to move the word to a new table instead.

        Returns True if the word fits.
        If not, then prepareColumn() should be called again.
        """
        if not self.innerTable.doesWordFit():
            # Delete the column for the word we just added
            self.innerTable.deleteWordColumns()
            self.createInnerTable()
            return False
        return True

    def wordRow_col(self):
        return self.innerTable.wordRow_col()

    def createInnerTable(self):
        """Create a new inner table."""
        logger.debug("Preparing to create inner table.")
        self.numRows = countRowsToShow((
            self.config.showWordLine1,
            self.config.showWordLine2,
            self.config.showMorphLine1,
            self.config.showMorphLine2,
            self.config.showPartOfSpeech))
        self.numRows += 1  # There's always a gloss row.
        firstInnerTable = False
        if self.innerTable is None:
            firstInnerTable = True
        self.innerTable = InnerTable(
            self.unoObjs, self.config, self.outerTable, self)
        self.innerTable.create(self.markers)

        ## Insert numbering if not already done outside of this table

        if (self.config.insertNumbering and not self.config.makeOuterTable
                and firstInnerTable):
            self.innerTable.hasNumbering = True
            # Add an empty column.  This is needed in order to resize the
            # numbering column correctly.
            logger.debug("Adding empty column column after numbering...")
            self.innerTable.insertNewColumn(40)
            self.outerTable.insertNumberInTable(
                self.innerTable.table, isInnerTable=True)

    def cleanupMarkers(self):
        """Delete the extra '+'s that we inserted to keep the inner tables
        from getting messed up.
        If we don't insert '+' marks, the inner tables can become out of order
        in certain situations, especially when the numbering column width is
        set extremely high (50%), causing a lot of wrapping.
        """
        logger.debug("cleaning up innerTable markers")
        for loopIndex, markerRange in enumerate(self.markers):
            self.unoObjs.viewcursor.gotoRange(markerRange, False)
            # delete '+'
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:Delete", "", 0, ())
            if loopIndex < len(self.markers) - 1:
                # Delete newline that was created by inserting '+' after table.
                # We don't need to do this for the last '+' because we will
                # add the free translation and ref number on that line.
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:Delete", "", 0, ())


class InnerTable:
    """Attributes for one inner table, which is the part of an interlinearized
    sentence that fits on one line.
    """
    def __init__(self, unoObjs, config, outerTable, wrappingManager):
        self.unoObjs = unoObjs
        self.config = config
        self.outerTable = outerTable
        self.wrappingManager = wrappingManager
        self.table = None
        self.wordRow_cols = 1  # counts merged word columns
        self.morphRow_cols = 1  # count of all inserted columns
        self.lastColFilled = False  # table starts with an empty column
        self.numColumnsAdded = 0
        # Typically numbering is in the outer table, but the inner table may
        # contain numbering if there is no outer table.
        self.hasNumbering = False

    def create(self, markers):
        """Create a new inner TextTable."""
        logger.debug("Preparing to create inner table.")

        ## Create the table

        table = self.unoObjs.document.createInstance(
            "com.sun.star.text.TextTable")
        table.initialize(self.wrappingManager.numRows, 1)  # one column
        self.outerTable.text.insertTextContent(
            self.outerTable.cursor, table, False)

        # Insert a '+' to keep the table locations from getting messed up.
        # We will delete it later, after all the tables are finished.
        self.outerTable.text.insertString(self.outerTable.cursor, '+', 0)
        self.outerTable.cursor.goLeft(1, False)
        # save the location for later
        markers.append(self.outerTable.cursor.getStart())
        self.outerTable.cursor.goRight(1, False)

        set_noTableBorders(table)
        table.Split = False # Text Flow -> don't split acr pages
        table.KeepTogether = True  # Text Flow -> keep with next para
        table.BottomMargin = self.config.tableBottomMargin * INCH_TO_CM
        logger.debug(
            "Created inner table %s with %d rows.",
            table.getName(), self.wrappingManager.numRows)
        self.table = table
        self.wordRow_cols = 1
        self.morphRow_cols = 1
        self.lastColFilled = False

    def prepareWordColumns(self, num_morphs):
        """Create all new column(s) needed for all morphs of a word."""
        if self.lastColFilled:
            self.insertNewColumn(100)
        morphRow_startCol = self.morphRow_cols - 1
        if num_morphs > 1:
            # Split up the column for all morphemes.
            self._splitColumn(num_morphs, morphRow_startCol)
        self.numColumnsAdded = num_morphs
        return morphRow_startCol

    def doesWordFit(self):
        """Check if the word fits on the current line, or whether
        we need to move the word to a new table instead.
        Returns True if the word fits.
        """
        self.optimize()

        firstDataCol = 0
        if self.hasNumbering:
            firstDataCol = 1
        if self.wordRow_col() > firstDataCol:
            if hasWrappingText(
                    self.table, self.unoObjs, self.outerTable.styles):
                return False
        return True

    def wordRow_col(self):
        """The most recent column for the word row.
        If there are no word rows, then returns the first morpheme column of
        the most recent word.
        """
        word_rows = countRowsToShow((
            self.config.showWordLine1,
            self.config.showWordLine2))
        if word_rows == 0:
            return self.wordRow_cols - self.numColumnsAdded
        return self.wordRow_cols - 1

    def insertNewColumn(self, percentWidth):
        """Param is percent of page width."""
        logger.debug("Inserting a column at index %d", self.wordRow_cols)
        oCols = self.table.getColumns()
        self.table.RelativeWidth = percentWidth
        oCols.insertByIndex(self.wordRow_cols, 1)   # add column
        self.wordRow_cols += 1
        self.morphRow_cols += 1

    def _splitColumn(self, numCols, startCol):
        """Split up the column."""
        numNewCols = numCols - 1
        word_rows = countRowsToShow((
            self.config.showWordLine1,
            self.config.showWordLine2))
        logger.debug(
            "Splitting for %d new morph cols at %d, %d",
            numNewCols, startCol, word_rows)
        cell1 = self.table.getCellByPosition(
            startCol, word_rows)
        cell2 = self.table.getCellByPosition(
            startCol, self.wrappingManager.numRows - 1)
        oTextTableCurs = self.table.createCursorByCellName(
            cell1.CellName)
        oTextTableCurs.gotoCellByName(cell2.CellName, True)
        bHorizontal = False
        oTextTableCurs.splitRange(numNewCols, bHorizontal)
        self.morphRow_cols += numNewCols
        if word_rows == 0:
            self.wordRow_cols += numNewCols

    def deleteWordColumns(self):
        """Deletes the columns that were recently added.
        Deleting 1 word column may delete several morph columns.
        """
        wordCol = self.wordRow_col()
        logger.debug("Deleting word col(s) at %d", wordCol)
        oWordCols = self.table.getColumns()
        if ((self.config.showWordLine1 or self.config.showWordLine2)
                and self.config.separateMorphColumns):
            oWordCols.removeByIndex(wordCol, 1)
            self.wordRow_cols -= 1
        else:
            logger.debug("deleting %d columns", self.numColumnsAdded)
            oWordCols.removeByIndex(wordCol, self.numColumnsAdded)
            self.wordRow_cols -= self.numColumnsAdded
        self.morphRow_cols -= self.numColumnsAdded

        ## Resize the current table to fix it
        self.optimize()

    def optimize(self):
        """Shrink the table to fit the text."""
        logger.debug(util.funcName('begin'))
        #oldSel = self.unoObjs.controller.getSelection()
        addedExtraCol = False
        # The outer table row needs to be adjustable or else optimizing
        # a tall inner table can mess it up.  This seems to be a bug in OOo.
        self.outerTable.resize()
        if self.morphRow_cols == 1:
            # Insert an extra column, because optimization doesn't work
            # for single-column tables.
            logger.debug("Inserting extra column")
            self.unoObjs.controller.select(self.table)
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:InsertColumns", "", 0, ())
            addedExtraCol = True
        endCol = self.morphRow_cols - 1
        if addedExtraCol:
            endCol += 1
        logger.debug(
            "Optimizing %d, %d to %d, %d",
            0, 0, endCol, self.wrappingManager.numRows - 1)
        cellsRange = self.table.getCellRangeByPosition(
            0, 0, endCol, self.wrappingManager.numRows - 1)
        self.unoObjs.controller.select(cellsRange)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SetOptimalColumnWidth", "", 0, ())
        if addedExtraCol:
            cellsRange = self.table.getCellRangeByPosition(1, 0, 1, 0)
            self.unoObjs.controller.select(cellsRange)
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:DeleteColumns", "", 0, ())
        #self.unoObjs.controller.select(oldSel)
        self.unoObjs.controller.select(None)
        self.outerTable.fixedSize()
        logger.debug(util.funcName('end'))


def set_noTableBorders(table):
    """Sets a table to have no borders."""
    borderLine = BorderLine()
    borderLine.OuterLineWidth = 0

    tableBorder = table.getPropertyValue("TableBorder")
    tableBorder.VerticalLine = borderLine
    tableBorder.HorizontalLine = borderLine
    tableBorder.LeftLine = borderLine
    tableBorder.RightLine = borderLine
    tableBorder.TopLine = borderLine
    tableBorder.BottomLine = borderLine
    table.setPropertyValue("TableBorder", tableBorder)


def set_noTableSpacing(table, unoObjs):
    """Sets a table to have no spacing.  As a side effect, this function
    also currently sets borders to none.
    """
    # move view cursor to first cell in table
    unoObjs.controller.select(table)

    unoObjs.dispatcher.executeDispatch(
        unoObjs.frame, ".uno:SelectTable", "", 0, ())
    ZERO_BORDER = (0, 0, 0, 0)
    uno_args = (
        util.createProp("BorderOuter.LeftBorder", ZERO_BORDER),
        util.createProp("BorderOuter.LeftDistance", 0),
        util.createProp("BorderOuter.RightBorder", ZERO_BORDER),
        util.createProp("BorderOuter.RightDistance", 0),
        util.createProp("BorderOuter.TopBorder", ZERO_BORDER),
        util.createProp("BorderOuter.TopDistance", 0),
        util.createProp("BorderOuter.BottomBorder", ZERO_BORDER),
        util.createProp("BorderOuter.BottomDistance", 0))
    unoObjs.dispatcher.executeDispatch(
        unoObjs.frame, ".uno:BorderOuter", "", 0, uno_args)
    # move view cursor to first cell in table
    unoObjs.controller.select(table)

def hasWrappingText(table, unoObjs, styles):
    """Returns true if text in a cell wraps to another line.
    To do this, we move the viewcursor down one line.
    If it is still in the same cell, then the cell has wrapping text,
    which means that there is too much text in this table.
    """
    logger.debug(util.funcName('begin'))
    viewcursor = unoObjs.viewcursor    # shorthand variable name
    for cellName in table.getCellNames():
        cell = table.getCellByName(cellName)
        oldRange = viewcursor.getStart()
        cellcursor = cell.createTextCursor()
        styles.requireParaStyle('numP')
        if (cellcursor.getPropertyValue("ParaStyleName") ==
                styles.styleNames['numP']):
            # Don't check whether the numbering wraps,
            # because moving the numbering to a new table won't help.
            continue
        viewcursor.gotoRange(cellcursor.getStart(), False)
        success = viewcursor.goDown(1, False)
        cell2 = viewcursor.Cell
        table2 = viewcursor.TextTable
        viewcursor.gotoRange(oldRange, False)
        if not success:
            ## Failure to go down means there is no wrapping text.
            continue
        if cell2 is not None:
            if (cell2.CellName == cellName and
                    table2.getName() == table.getName()):
                logger.debug(
                    "cell %s in table %s has wrapping text",
                    cellName, table.getName())
                return True
    logger.debug("No wrapping text found.")
    return False

def countRowsToShow(rowShowVars):
    """User variables specify whether to show or hide certain rows.
    Count how many rows to show.
    Value will be true if row should be shown.
    """
    return len([val for val in rowShowVars if val])
