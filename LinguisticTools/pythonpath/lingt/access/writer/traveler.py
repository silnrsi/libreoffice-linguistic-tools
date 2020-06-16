# -*- coding: Latin-1 -*-
#
# This file created Dec 10 2012 by Jim Kornelsen
#
# 22-Apr-13 JDK  Use travelCursor instead of viewcursor to select string.
# 25-Apr-13 JDK  Use // for integer division, needed in Python 3.

"""
Travel through a text range with a cursor, checking each word.
"""
import logging
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import RuntimeException

from lingt.access.writer import textchanges
from lingt.app import exceptions
from lingt.utils import util

logger = logging.getLogger("lingt.access.traveler")

class Traveler:
    """Cursors useful for traversing text."""
    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.cursLeft = None  # starting from leftmost and going right
        self.rangeRight = None  # to tell if we're finished traversing

    def createCursors(self, selectionCursor):
        text = selectionCursor.getText()
        cursLeftmost = selectionCursor.getStart()
        cursRightmost = selectionCursor.getEnd()
        try:
            if text.compareRegionStarts(
                    selectionCursor.getEnd(), selectionCursor) >= 0:
                logger.debug("start of selection is on the right")
                # swap
                cursLeftmost, cursRightmost = cursRightmost, cursLeftmost
        except (RuntimeException, IllegalArgumentException):
            logger.warning("could not get range from selection")
        try:
            cursTmp = text.createTextCursorByRange(cursLeftmost)
        except (RuntimeException, IllegalArgumentException):
            raise exceptions.RangeError("Failed to go to text range.")
        cursTmp.gotoRange(cursRightmost, True)
        logger.debug("text = '%s'", cursTmp.getString())

        # We use the viewcursor because text cursors cannot goRight into tables
        oVC = self.unoObjs.viewcursor
        oVC.gotoRange(cursLeftmost, False)
        #logger.debug(util.debug_tellNextChar(oVC))
        self.cursLeft = oVC.getText().createTextCursorByRange(oVC)
        self.rangeRight = RangeCompare(
            text.createTextCursorByRange(cursRightmost),
            self.unoObjs.viewcursor)


class RangeJumper:
    """Jumps to a specific location in a range specified by a string.
    By bisecting the string, takes O(log n) to jump.
    """
    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.text = None
        self.rangeCursor = None    # a textcursor to hold the whole range
        self.travelCursor = None    # a textcursor to travel in the range
        self.placeCursor = None    # a textcursor to remember a position

    def setTextRange(self, txtRange):
        """:param txtRange: type search.TxtRange"""
        oSel = txtRange.sel
        try:
            self.text = oSel.getText()
            self.rangeCursor = self.text.createTextCursorByRange(oSel)
            self.travelCursor = self.text.createTextCursorByRange(
                oSel.getStart())
            self.placeCursor = self.text.createTextCursorByRange(
                oSel.getStart())
        except (RuntimeException, IllegalArgumentException):
            logger.warning("Failed to go to text range.")
            raise exceptions.RangeError("Failed to go to text range.")
        logger.debug("String = <<%s>>", self.rangeCursor.getString())

    def getString(self):
        """If a word in the range is changed, the range will be
        adjusted and getString will give the new value.
        """
        return self.rangeCursor.getString()

    def getStringBefore(self):
        self.travelCursor.gotoRange(self.rangeCursor.getStart(), False)
        self.travelCursor.gotoRange(self.placeCursor.getStart(), True)
        return self.travelCursor.getString()

    def changeString(self, changeTo):
        textchanges.changeString(self.travelCursor, changeTo)
        self.placeCursor.gotoRange(self.travelCursor.getEnd(), False)

    def selectWord(self, stringBeforeWord, wordString):
        """Go to the word and select it."""
        logger.debug(
            util.funcName('begin', args=(stringBeforeWord, wordString)))
        self.gotoLoc(stringBeforeWord)
        selectedString = ""
        while len(selectedString) < len(wordString):
            if not self.travelCursor.goRight(1, True):
                logger.warning("Could not go right.")
                raise exceptions.RangeError("Failed to go to text range.")
            try:
                selectedString = self.travelCursor.getString()
                logger.debug("'%s'", selectedString)
            except RuntimeException:
                logger.warning("Could not get string from selection.")
                raise exceptions.RangeError("Could not get selection string.")
        logger.debug("selectedString = '%s'", selectedString)
        try:
            # Select the word so the user can see it.
            self.unoObjs.viewcursor.gotoRange(self.travelCursor, False)
        except RuntimeException:
            logger.warning("Could not go to range.")
            raise exceptions.RangeError("Failed to go to text range.")
        return selectedString == wordString

    def gotoLoc(self, stringBeforeWord):
        """Within the range, go to a specific location specified by the string.
        Will move self.travelCursor to that position.

        Going through each character in a document with oCurs.goRight(1, True)
        can be pretty slow, so instead we narrow down the location
        by guessing and then comparing string lengths.
        """
        logger.debug(util.funcName('begin'))
        # Make a textcursor to find where the viewcursor should go.
        # The textcursor will guess by doubling each time until it gets
        # big enough, then it will start getting smaller as we
        # narrow down the right place.
        # When guessing, no need to compare ranges.  Instead compare
        # string lengths.  If string lengths are the same, then that's
        # the exact spot.  Otherwise, whether beyond the end of the range or
        # not, we need to keep guessing.
        guess = 2
        delta = 1
        guessedHigh = False   # have we guessed too high yet
        oneStepForward = False   # have we already tried just one step forward
        self.travelCursor.gotoRange(self.rangeCursor.getStart(), False)
        self.travelCursor.goRight(guess, True)
        while True:
            guessString = self.travelCursor.getString()
            if len(guessString) < len(stringBeforeWord):
                if not guessedHigh:
                    delta = delta * 2
                else:
                    # From here on out, guess changes will get smaller.
                    delta = delta // 2
                    if delta == 0:
                        delta = 1
                prevCurs = self.text.createTextCursorByRange(self.travelCursor)
                ok = cursorGo(self.travelCursor, 'right', delta, True)
                if delta == 1:
                    oneStepForward = True
                logger.debug("%d, %d up", len(guessString), delta)
                while not ok:
                    # Probably went beyond the text range
                    delta = delta // 2
                    if delta == 0:
                        break
                    self.travelCursor.gotoRange(prevCurs, False)
                    ok = cursorGo(self.travelCursor, 'right', delta, True)
                    guessedHigh = True
                    if delta == 1:
                        oneStepForward = True
                    logger.debug("%d, %d up2", len(guessString), delta)
            elif len(guessString) > len(stringBeforeWord):
                delta = delta // 2
                if delta == 0:
                    # this covers cases where len(stringBeforeWord) < 2
                    delta = 1
                if oneStepForward and delta == 1:
                    logger.warning("Couldn't move to exact spot.")
                    break
                cursorGo(self.travelCursor, 'left', delta, True)
                guessedHigh = True
                logger.debug("%d, %d down", len(guessString), delta)
            else:
                logger.debug("Found it")
                break
        self.travelCursor.collapseToEnd()
        logger.debug(util.funcName('end'))

def cursorGo(oCurs, direction, count, doSel):
    """There is a limit to how big the parameter to oCurs.goRight() can be.
    To get around this, we simply call it several times with smaller numbers.
    """
    MAX_SIZE = pow(2, 15) - 1  # this limit probably comes from C sizeof(int)
    parts = []
    div, mod = divmod(count, MAX_SIZE)
    div = int(div)  # first argument returned from divmod is a float
    parts.extend([MAX_SIZE] * div)
    if mod > 0 or div == 0:
        parts.append(mod)
    for part in parts:
        if direction == 'right':
            return oCurs.goRight(part, doSel)
        else:
            return oCurs.goLeft(part, doSel)


class VCLocation:
    """Used to determine where the viewcursor and its table are."""
    def __init__(self, unoObjs, startFromBeginning):
        self.unoObjs = unoObjs
        self.oVC = unoObjs.viewcursor  # shorthand variable name

        self.tableName = ""
        if self.oVC.TextTable:
            self.tableName = self.oVC.TextTable.getName()
        self.reachedTable = False

        # current location is after viewcursor
        self.after = True if startFromBeginning else False

    def parAfter(self, oPar):
        """
        Returns true if the paragraph is after the viewcursor.
        """
        if self.after:
            return True
        if RangeCompare(oPar.getEnd(), self.oVC).compareVC() != -1:
            # The paragraph is not after the viewcursor.
            #logger.debug("para before self.oVC")
            return False
        self.after = True
        return True

    def tableAfter(self, oTable):
        """Returns true if the table is after the viewcursor.

        As explained in the API, oTable.getAnchor() cannot
        be used to determine where the table is.
        Instead, comparing table names works well for our needs.
        """
        if self.after:
            return True
        if self.tableName:
            if oTable.getName() == self.tableName:
                self.reachedTable = True
            elif self.reachedTable:
                self.after = True
        else:
            # Move the viewcursor to a new location: this table.
            originalRange = self.oVC.getEnd()
            self.unoObjs.controller.select(oTable) # go to 1st cell
            self.oVC.gotoEnd(False) # goto end of cell if cell not empty
            if RangeCompare(originalRange, self.oVC).compareVC() < 0:
                self.oVC.gotoRange(originalRange, False)
            else:
                self.after = True
        return self.after


def differentPlaces(oCurs1, oCurs2):
    """Test using compareRegion to see if two cursors are in different places.
    If compareRegion fails, such as after a nested table, return False.
    """
    try:
        oText = oCurs1.getText()
        return oText.compareRegionEnds(oCurs1, oCurs2) != 0
    except IllegalArgumentException:
        logger.info("Could not compare region.")
        return False

class RangeCompare:
    """Compare the viewcursor to a text range (a location).
    Can be useful when traversing a cursor over a range.
    The range is expected not to be modified.
    """
    def __init__(self, rangeEnd, viewCursor):
        self.oVC = viewCursor
        self.rangeEnd = rangeEnd
        self.endX = -1
        self.endY = -1

    def getCoords(self):
        if self.endY > -1:
            return
        # remember where we were, because we'll need to use the viewcursor
        originalVC = self.oVC.getText().createTextCursorByRange(self.oVC)

        self.oVC.gotoRange(self.rangeEnd, False)
        self.endX = self.oVC.getPosition().X
        self.endY = self.oVC.getPosition().Y

        self.oVC.gotoRange(originalVC, False)

    def compareVC(self):
        """Compare the viewcursor to the range.
        This works better with nested tables than oText.compareRegionEnds().
        Assume we are travelling with the viewcursor.
        See if it is up to the end yet or not.
        The comparison is done by checking the physical position of the cursor.

        Returns -1 if the VC location is less than self.rangeEnd, 0 if it is
        the same, and 1 if it is greater.
        Returns -2 if they are on the same line but not in the same spot, and
        it's not certain which location is greater.
        """
        self.getCoords()
        curX = self.oVC.getPosition().X
        curY = self.oVC.getPosition().Y
        if curY < self.endY:
            logger.debug("%d < %d", curY, self.endY)
            return -1
        elif curY > self.endY:
            logger.debug("%d > %d", curY, self.endY)
            return 1
        elif curY == self.endY:
            if curX == self.endX:
                if differentPlaces(self.oVC, self.rangeEnd):
                    # There is probably a word-final diacritic that doesn't
                    # change the position, so we're not to the end yet.
                    logger.debug("Including word-final diacritic.")
                    return -2
                # We're at the end.
                logger.debug(
                    "VC same loc as text range (%d, %d).", curX, curY)
                return 0
            else:
                # Probably we haven't gone far enough.
                # If there is some problem we may have gone too far, in which
                # case the method will return -1 when we get to the next line.
                # There are several advantages of not comparing curX and
                # self.endX here.  First, this handles right-to-left scripts.
                # Second, some fonts render badly and so going right one
                # character may not always be moving physically to the right.
                logger.debug("Probably haven't gone far enough.")
                return -2
