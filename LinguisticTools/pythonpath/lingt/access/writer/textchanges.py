# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 21-Oct-10 JDK  Option for changing font without applying a style.
# 29-Mar-11 JDK  Preserve character styles.  Preserve line and para breaks.
# 19-Apr-11 JDK  TextSearch now splits up text portions, so now we can assume
#                the formatting is all the same here.
# 21-Dec-11 JDK  Clear the font when setting character or paragraph styles.
# 26-Nov-12 JDK  Optional message box to ask before making each change.
# 22-Feb-13 JDK  Fixed bug in changeString -- added collapseToEnd.
# 07-Jun-13 JDK  Raise exception if convert fails.
# 13-Jul-15 JDK  Take fontDef as parameter.
# 10-Aug-15 JDK  Use generator to enumerate UNO collections.
# 09-Oct-15 JDK  Fixed bug in clearFont(): self.newFont is a FontDefStruct obj.
# 10-Dec-15 JDK  Import constant instead of using uno.Enum.
# 01-Aug-18 JDK  Do not require a viewcursor (for Draw).

"""
Handles changes to text in the document.
For Data Conversion.
"""

import logging
import re
from com.sun.star.beans.PropertyState import DIRECT_VALUE
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import RuntimeException

from lingt.access.common import iteruno
from lingt.access.writer import styles
from lingt.app import exceptions
from lingt.ui.common.messagebox import FourButtonDialog
from lingt.ui.common.progressbar import ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.access.textchanges")

class TextChanger:
    def __init__(self, unoObjs, progressBar):
        self.unoObjs = unoObjs
        self.progressBar = progressBar
        self.msgboxFour = FourButtonDialog(unoObjs)
        self.secCall = None
        self.styleType = ""
        self.newStyleName = ""
        self.newFont = None
        self.numChanges = 0
        self.numStyleChanges = 0
        self.selsCount = 0
        self.askEach = False

    def setConverterCall(self, secCall):
        self.secCall = secCall

    def setStyleToChange(self, styleType, styleName):
        self.styleType = styleType
        self.newStyleName = styleName

    def setFontToChange(self, fontDef):
        """:arg fontDef: type styles.FontDefStruct"""
        self.styleType = "FontOnly"
        self.newFont = fontDef

    def doChanges(self, ranges, askEach):
        """
        :arg ranges: list of search.TxtRange objects
        :returns: number of changes made
        """
        logger.debug(util.funcName('begin'))
        self.numChanges = 0
        self.numStyleChanges = 0
        self.askEach = askEach
        if self.unoObjs.viewcursor:
            originalRange = self.unoObjs.viewcursor.getStart()
        rangeLastChanged = None
        progressRange = ProgressRange(
            start=40, stop=90, ops=len(ranges), pbar=self.progressBar)

        rangeNum = 1
        for txtRange in ranges:
            changed = False
            try:
                changed = self.changeTextRange(txtRange)
            except (exceptions.UserInterrupt,
                    exceptions.FileAccessError) as exc:
                #logger.exception(str(exc))
                logger.exception(exc)
                return self.numChanges, self.numStyleChanges
            if changed:
                logger.debug("Converted.")
                try:
                    rangeLastChanged = txtRange.sel.getStart()
                except (RuntimeException, IllegalArgumentException):
                    # Just give up.
                    logger.warning("Failed to get text range.")
                    continue
            progressRange.update(rangeNum)
            rangeNum += 1

        if self.unoObjs.viewcursor:
            try:
                if rangeLastChanged is None:
                    self.unoObjs.viewcursor.gotoRange(originalRange, False)
                else:
                    self.unoObjs.viewcursor.gotoRange(rangeLastChanged, False)
            except (RuntimeException, IllegalArgumentException):
                # Just give up; it's not essential.
                logger.warning("Failed to go to text range.")
        logger.debug(util.funcName('end'))
        return self.numChanges, self.numStyleChanges

    def changeTextRange(self, txtRange):
        logger.debug(util.funcName('begin'))
        oSel = txtRange.sel
        try:
            oCursor = oSel.getText().createTextCursorByRange(oSel)
        except (RuntimeException, IllegalArgumentException):
            logger.warning("Failed to go to text range.")
            return
        logger.debug(u"String = '%r'", oCursor.getString())
        if self.askEach:
            if self.unoObjs.viewcursor:
                self.unoObjs.viewcursor.gotoRange(oSel.getStart(), False)
                self.unoObjs.viewcursor.gotoRange(oSel.getEnd(), True) # select
            result = self.msgboxFour.display("Make this change?")
            if result == "yes":
                # keep going
                pass
            elif result == "no":
                return False
            elif result == "yesToAll":
                self.askEach = False
            else:
                raise exceptions.UserInterrupt()
        return self.convertString(oCursor)

    def convertString(self, oCurs):
        """Here is where the call to SEC Converters is actually done.
        It calls an OOo C++ component which calls the SEC dll file.
        Then it makes the change in Writer.
        Also sets the new style.
        Returns True if a change is made.
        Throws an exception if there is a problem with conversion.
        """
        inValue = oCurs.getString()

        ## Get the converted value

        changedText = False
        if self.secCall is not None:
            outValue = self.secCall.convert(inValue)
            changedText = True
            if outValue == inValue:
                changedText = False
            outValue = prepareNewlines(outValue)
            if outValue == inValue:
                changedText = False
            logger.debug("converted text '%s'", outValue)

        if self.styleType == "ParaStyleName":
            self.changeParaStyle(oCurs)
        elif self.styleType == "CharStyleName":
            self.changeCharStyle(oCurs)
        elif self.styleType == "FontOnly":
            self.changeFont(oCurs)

        if not changedText:
            return False
        changeString(oCurs, outValue)
        self.numChanges += 1
        return True

    def changeParaStyle(self, oCurs):
        """Goes to the paragraph and sets the style.
        Changes any directly formatted font name and size to the default.
        """
        logger.debug(util.funcName('begin'))
        oCursDbg = oCurs.getText().createTextCursorByRange(oCurs.getStart())
        oCursDbg.gotoRange(oCurs.getEnd(), True)
        logger.debug("oCursText = '%s'", oCursDbg.getString())
        firstCellName = ""
        # enumerate current paragraph
        for oTextElem in iteruno.byEnum(oCurs):
            logger.debug("oTextElem %s", oTextElem.getString())
            if oTextElem.TextTable:
                curCurs = oTextElem.getText().createTextCursorByRange(
                    oTextElem.getStart())
                if curCurs is None:
                    # This happens after the first cell; I don't know why.
                    curCellName = "none"
                else:
                    curCurs.goRight(0, False)
                    curCellName = curCurs.Cell.CellName
                logger.debug("cell %s", curCellName)
                if firstCellName == "":
                    firstCellName = curCellName
                elif curCellName != firstCellName:
                    # Somehow we've gotten out of the cell
                    logger.debug(
                        "moved out of %s to %s", firstCellName, curCellName)
                    break
            if oTextElem.supportsService("com.sun.star.text.Paragraph"):
                curStyleName = oTextElem.getPropertyValue(self.styleType)
                if curStyleName != self.newStyleName:
                    logger.debug("Setting style %s", self.newStyleName)
                    oTextElem.setPropertyValue(
                        self.styleType, self.newStyleName)
                    self.numStyleChanges += 1
                for oTextPortion in iteruno.byEnum(oTextElem):
                    for propName in ("CharFontName", "CharHeight"):
                        if (oTextPortion.getPropertyState(propName) ==
                                DIRECT_VALUE):
                            oTextPortion.setPropertyToDefault(propName)
                            logger.debug("setToDefault %s", propName)
        self.clearFont(oCurs)
        logger.debug(util.funcName('end'))

    def changeCharStyle(self, oCurs):
        """Change character style."""
        curStyleName = oCurs.getPropertyValue(self.styleType)
        if curStyleName != self.newStyleName:
            logger.debug(
                "Setting style %s from %s", self.newStyleName, curStyleName)
            oCurs.setPropertyValue(self.styleType, self.newStyleName)
            self.numStyleChanges += 1
        self.clearFont(oCurs)

    def clearFont(self, oCurs):
        """Setting a character or paragraph style doesn't clear font
        formatting.  It just overrides it.  This can be a problem when changing
        encoding using a font as the scope, because it will still find the
        font even after the conversion is done.
        To make sure this doesn't happen, reset the font when changing styles.
        """
        self.newFont = styles.FontDefStruct()
        self.changeFont(oCurs)

    def changeFont(self, oCurs):
        for propSuffix in ['', 'Complex', 'Asian']:
            oCurs.setPropertyToDefault('CharFontName' + propSuffix)
            oCurs.setPropertyToDefault('CharHeight' + propSuffix)
        propSuffix = self.newFont.fontType
        if propSuffix == 'Western':
            propSuffix = ''
        if self.newFont.fontName:
            self.setCursProp(
                oCurs, 'CharFontName' + propSuffix, self.newFont.fontName)
        if self.newFont.fontSize.isSpecified():
            self.newFont.fontSize.setPropSuffix(propSuffix)
            self.newFont.fontSize.changeElemProp(oCurs)

    def setCursProp(self, oCurs, propName, newVal):
        curVal = oCurs.getPropertyValue(propName)
        if curVal != newVal:
            logger.debug("Setting %s from %s to %s", propName, curVal, newVal)
            oCurs.setPropertyValue(propName, newVal)
            self.numStyleChanges += 1


def prepareNewlines(value):
    """CR+LF creates an unwanted line break when inserting
    back into Writer.  So we change it to just CR before inserting.
    Inserting LF creates a line break, and CR creates a paragraph break.

    Tips for figuring out newlines:
    + In OOo go to View -> Nonprinting characters.
      This shows paragraph breaks and line breaks distinctly.
      Type Shift+Enter to create a line break.
    + Open the debug file in Notepad++ and View -> Show symbol -> EOL.
    """
    newValue = value
    regex1 = re.compile(r"(\x0d\x0a)", re.S)  # CR+LF for para break
    newValue = re.sub(regex1, "\x0d", newValue)
    return newValue

class FindAndReplace:
    def __init__(self, writerUnoObjs, askEach=True):
        self.unoObjs = writerUnoObjs
        self.msgboxFour = FourButtonDialog(writerUnoObjs)
        self.askEach = askEach
        self.selsCount = 0

    def replace(self, oldString, newString):
        changesMade = 0
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchString = oldString
        search.SearchAll = True
        search.SearchWords = True
        search.SearchCaseSensitive = False
        selsFound = self.unoObjs.document.findAll(search)
        self.selsCount = selsFound.getCount()
        if selsFound.getCount() == 0:
            logger.debug("Did not find anything.")
            return changesMade
        for selIndex, oSel in enumerate(iteruno.byIndex(selsFound)):
            logger.debug("Found selection %s", selIndex)
            if self.askEach:
                self.unoObjs.viewcursor.gotoRange(oSel.getStart(), False)
                self.unoObjs.viewcursor.gotoRange(oSel.getEnd(), True)
                result = self.msgboxFour.display(
                    "Make this change?  (%s -> %s)", oldString, newString)
                if result == "yes":
                    # keep going
                    pass
                elif result == "no":
                    continue
                elif result == "yesToAll":
                    self.askEach = False
                else:
                    raise exceptions.UserInterrupt()
                self.unoObjs.viewcursor.goRight(0, False) # deselect
            oTextCursTmp = oSel.getText().createTextCursorByRange(oSel)
            changeString(oTextCursTmp, newString)
            changesMade += 1
        return changesMade

def changeString(oCurs, stringVal):
    """
    Make the change in Writer

    To preserve formatting, add extra characters to surround the text.
    We use the "+" character for this purpose.
    Since the "+" characters are inserted following the old string,
    they will take on the old string's attributes.
    Also the starting range will be preserved by this method.
    """
    ## Insert word in between ++.
    start = oCurs.getStart()
    oCurs.collapseToEnd()
    oCurs.getText().insertString(oCurs, "++", False)
    oCurs.goLeft(2, False)
    oCurs.gotoRange(start, True)
    oCurs.setString("")     # deletes all but the extra characters
    oCurs.goRight(1, False) # move in between the two "+" characters.
    oCurs.collapseToEnd()   # Not sure why this is needed, since going right
                            # with False should deselect -- but it didn't.
    oCurs.getText().insertString(oCurs, stringVal, True)

    ## Remove the surrounding '+' characters.
    start = oCurs.getStart()
    end = oCurs.getEnd()
    oCurs.gotoRange(start, False)
    oCurs.goLeft(1, True)
    oCurs.setString("")     # delete the first extra character
    oCurs.gotoRange(end, False)
    oCurs.goRight(1, True)
    oCurs.setString("")     # delete the second extra character
    oCurs.goRight(0, False)
