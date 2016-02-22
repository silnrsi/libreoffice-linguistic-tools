# -*- coding: Latin-1 -*-
#
# This file created Sept 21 2010 by Jim Kornelsen
#
# 25-Oct-10 JDK  Optionally don't create a comparison doc.
# 29-Oct-10 JDK  Only go up 2 when deleting phonology examples.
# 12-Aug-11 JDK  If number is just (), save range to add number.
# 09-Apr-13 JDK  Look for an already open comparsion doc.
# 19-Apr-13 JDK  Start at end of new example in deleteOldPhonEx.
# 29-Jul-13 JDK  Import constants instead of using uno.getConstantByName.
# 27-Jul-15 JDK  Added ComparisonDoc class.
# 10-Aug-15 JDK  Use generator to enumerate UNO collections.

"""
Given an old example and a new one, moves the ref number to the new example.
Then moves the old example to a new comparison document, and copies the
new example to the comparison document as well.
Inserts hyperlinks to the main document.

For phonology, there is no need to keep copy the old example, so it is
much simpler.
"""
import logging

import uno
from com.sun.star.style.BreakType import PAGE_BEFORE
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER

from lingt.access import iteruno
from lingt.access.writer.uservars import UserVars
from lingt.utils import util

logger = logging.getLogger("lingt.access.ExUpdater")


class ExUpdater:
    """
    Inserts a new example to replace an old one.
    """
    def __init__(self, unoObjs, exampleManager, VAR_PREFIX):
        self.unoObjs = unoObjs
        self.exampleManager = exampleManager
        self.compDoc = ComparisonDoc(self.unoObjs, VAR_PREFIX)
        logger.debug("ExUpdater init() finished")

    def doNotMakeCompDoc(self):
        self.compDoc.doNotMake()

    def gotoAfterEx(self):
        """
        Move viewcursor to the next line.
        Before this method is called, the cursor is expected to be at
        the reference number of an example.
        """
        logger.debug(util.funcName('begin'))
        self.unoObjs.viewcursor.goDown(1, False)
        self.unoObjs.viewcursor.gotoStartOfLine(False)

    def moveExNumber(self):
        """
        Move the example number from the old example to the new one.

        Before this method is called, the cursor is expected to be one
        line below two tables with examples, and there should be no
        empty line between the two tables -- they should be touching.
        """
        logger.debug(util.funcName('begin'))
        oVC = self.unoObjs.viewcursor   # shorthand variable name

        ## Delete paragraph break inserted by outputmanager.insertEx()

        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Delete", "", 0, ())

        ## Go to ex number of old example.

        oVC.goUp(2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        oTextCurs = oVC.getText().createTextCursorByRange(oVC)
        strval = oTextCurs.getString()

        # FIXME: This can cause a crash in some cases.
        # It happened when repeatedly updating the same example.
        logger.debug("Cut begin")
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Cut", "", 0, ())
        logger.debug("Cut finished")

        ## Cut ex number from old example.
        ## Paste unformatted text of ex number.

        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Cut", "", 0, ())
        uno_args = (
            util.createProp("SelectedFormat", 1),    # paste unformatted
        )
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:ClipboardFormatItems", "", 0, uno_args)

        ## Paste ex number into new example

        oVC.goDown(1, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Paste", "", 0, ())

        # If a new example was just added and then updated,
        # we need to save this range to add the example number.
        # The original range will be invalid now.
        if strval == "()":
            oVC.goLeft(1, False)
            self.exampleManager.exnumRanges.append(oVC.getStart())
        logger.debug(util.funcName('end'))

    def moveExamplesToNewDoc(self):
        """Cut the old example and create a comparison document."""
        logger.debug(util.funcName('begin'))
        oVC = self.unoObjs.viewcursor  # short variable name
        self.compDoc.createComparisonDoc()

        ## Cut old example

        logger.debug("cutting old example")
        self.unoObjs.viewcursor.goUp(1, False)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Copy", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:DeleteTable", "", 0, ())

        ## Cursor should now be in table of new example.
        ## Paste examples in comparison doc.

        newExTableName = ""
        if oVC.TextTable:
            newExTableName = oVC.TextTable.getName()
        self.compDoc.pasteExamples(newExTableName)

        ## Position cursor in main doc after example.
        ## This is important so that "Find Next" doesn't repeat this ex.

        self.unoObjs.window.toFront()
        if oVC.TextTable:
            logger.debug("in TextTable")
            self.unoObjs.controller.select(oVC.TextTable)
            firstCell = oVC.Cell
            # go to end of cell if cell is not empty
            oVC.gotoEnd(False)
            if oVC.Cell.CellName == firstCell.CellName:
                # go to end of last cell in table
                oVC.gotoEnd(False)
        self.unoObjs.viewcursor.goRight(1, False)
        logger.debug(util.funcName('end'))

    def deleteOldPhonEx(self):
        """
        Viewcursor should be at end of line of new example,
        with old example on line above.
        One line below new example, a new paragraph break has been inserted.
        """
        logger.debug(util.funcName('begin'))
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        oVC.goUp(1, False)

        ## delete line
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SwBackspace", "", 0, ())

        ## delete paragraph break inserted by outputmanager.insertEx()
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Delete", "", 0, ())

        ## finish
        oVC.gotoEndOfLine(False)
        logger.debug("deleteOldPhonEx() FINISH")

    def disposing(self, dummy_aEvent):
        ## XXX: Needs testing; Is this method needed for this class?
        logger.debug("Disposing")
        self.compDoc = None
        return None


def insertPageBreak(oText, oCursor):
    """Inserts a paragraph that has a page break."""
    oText.insertControlCharacter(oCursor, PARAGRAPH_BREAK, 0)
    oCursor.setPropertyValue('BreakType', PAGE_BEFORE)

class ComparisonDoc:
    """
    A temporary writer document that helps the user compare old and new
    examples.
    """
    def __init__(self, mainDocUnoObjs, VAR_PREFIX):
        self.mainDoc = mainDocUnoObjs
        self.VAR_PREFIX = VAR_PREFIX
        self.writerDoc = None
        self.makeDoc = True
        self.emptyDoc = False
        self.section = None
        self.calledSetMainDoc = False

    def doNotMake(self):
        self.makeDoc = False

    def createComparisonDoc(self):
        """
        Create an empty writer doc.
        If the main file has a saved path, then only one comparison doc
        should be created.
        Returns True if a new document was created.
        """
        if not self.makeDoc:
            return
        if self.writerDoc is not None:
            if self.writerDoc.document is not None:
                ## Document is already open
                return

        varname = "ComparisonDocForFile"
        currentFilepath = None  # file path of main document
        url = self.mainDoc.document.getURL()
        if url:
            currentFilepath = uno.fileUrlToSystemPath(url)
            doclist = self.mainDoc.getOpenDocs(util.UnoObjs.DOCTYPE_WRITER)
            for docUnoObjs in doclist:
                logger.debug("Checking writer document for settings.")
                userVars = UserVars(
                    self.VAR_PREFIX, docUnoObjs.document, logger)
                if not userVars.isEmpty(varname):
                    varFilepath = userVars.get(varname)
                    if varFilepath == currentFilepath:
                        logger.debug("found comparison doc")
                        self.writerDoc = docUnoObjs
                        return False
                    else:
                        logger.debug(
                            "%s != %s", varFilepath, currentFilepath)

        logger.debug("opening new document for comparison")
        newDoc = self.mainDoc.desktop.loadComponentFromURL(
            "private:factory/swriter", "_blank", 0, ())
        self.writerDoc = self.mainDoc.getDocObjs(newDoc)
        self.writerDoc.text.insertString(
            self.writerDoc.viewcursor,
            "Here are the changes that have been made.  " +
            "You may want to look through these changes, and make any " +
            "corrections in the main document.  " +
            "When finished checking, just close this window without saving.",
            0)
        self.writerDoc.text.insertControlCharacter(
            self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)
        self.writerDoc.text.insertControlCharacter(
            self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)
        if currentFilepath:
            userVars = UserVars(
                self.VAR_PREFIX, self.writerDoc.document, logger)
            userVars.store(varname, currentFilepath)
        self.emptyDoc = True
        logger.debug(util.funcName('end'))

    def pasteExamples(self, mainTableName):
        """
        Paste old example.
        Copy and paste new example.
        """
        if not self.makeDoc:
            return
        self._pasteExample(isOldEx=True)
        if mainTableName:
            logger.debug("copying new example")
            self.mainDoc.dispatcher.executeDispatch(
                self.mainDoc.frame, ".uno:SelectTable", "", 0, ())
            self.mainDoc.dispatcher.executeDispatch(
                self.mainDoc.frame, ".uno:Copy", "", 0, ())
            self._pasteExample(isOldEx=False, mainTableName=mainTableName)
        else:
            logger.debug("did not get main table")
            self.writerDoc.text.insertControlCharacter(
                self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)
            self.writerDoc.text.insertString(
                self.writerDoc.viewcursor,
                "There was a problem with this example.", 0)
            self.writerDoc.text.insertControlCharacter(
                self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)

    def _pasteExample(self, isOldEx, mainTableName=""):
        logger.debug("pasting example (isOldEx=%r)", isOldEx)
        self.writerDoc.viewcursor.gotoEnd(False)
        self.writerDoc.viewcursor.jumpToLastPage()
        self.writerDoc.viewcursor.jumpToEndOfPage()
        if self.emptyDoc:
            insertPageBreak(self.writerDoc.text, self.writerDoc.viewcursor)
            self.emptyDoc = False
        if isOldEx:
            self.writerDoc.text.insertControlCharacter(
                self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)
        self.writerDoc.viewcursor.goUp(1, False)

        bgcolor = int("FFFFCC", 16)  # yellow
        if isOldEx:
            bgcolor = int("F1F7FC", 16)  # light bluish grey
        self.insertSection(bgcolor)
        self.writerDoc.viewcursor.gotoRange(self.section.getAnchor(), False)

        title = "Old:" if isOldEx else "New:"
        self.writerDoc.text.insertString(
            self.writerDoc.viewcursor, title, 0)
        for dummy in range(3):
            self.writerDoc.text.insertControlCharacter(
                self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)
        if isOldEx:
            self.writerDoc.viewcursor.goUp(2, False)
            self.writerDoc.dispatcher.executeDispatch(
                self.writerDoc.frame, ".uno:Paste", "", 0, ())
        else:
            self.writerDoc.text.insertControlCharacter(
                self.writerDoc.viewcursor, PARAGRAPH_BREAK, 0)
            self.writerDoc.viewcursor.goUp(3, False)
            self.writerDoc.dispatcher.executeDispatch(
                self.writerDoc.frame, ".uno:Paste", "", 0, ())

            ## Insert button to go to example in main doc

            logger.debug("Inserting button")
            self.writerDoc.viewcursor.collapseToEnd()
            self.mainDoc.url = self.mainDoc.document.getURL()
            if self.mainDoc.url:
                oButtonModel = self.addNewButton()
                self.assignAction(oButtonModel, mainTableName)
                self.writerDoc.controller.setFormDesignMode(False)
            else:
                logger.debug("Main doc has no filename.")
        logger.debug("pasteExample() FINISHED")

    def addNewButton(self):
        logger.debug(util.funcName())
        oControlShape = self.writerDoc.document.createInstance(
            "com.sun.star.drawing.ControlShape")
        aPoint = uno.createUnoStruct("com.sun.star.awt.Point")
        aPoint.X = 1000
        aPoint.Y = 1000
        oControlShape.setPosition(aPoint)
        aSize = uno.createUnoStruct("com.sun.star.awt.Size")
        aSize.Width = 6000
        aSize.Height = 800
        oControlShape.setSize(aSize)
        oControlShape.AnchorType = AS_CHARACTER
        oButtonModel = self.mainDoc.smgr.createInstance(
            "com.sun.star.form.component.CommandButton")
        oButtonModel.Label = "Go to example in main document"
        oControlShape.setControl(oButtonModel)
        self.writerDoc.text.insertTextContent(
            self.writerDoc.viewcursor, oControlShape, False)
        return oButtonModel

    def assignAction(self, oButtonModel, sDestination):
        """assign sScriptURL event as css.awt.XActionListener::actionPerformed.
        event is assigned to the control described by the nIndex in the oForm
        container
        """
        logger.debug(util.funcName('begin'))
        logger.debug("specify which is the main document")
        if not self.calledSetMainDoc:
            sMacro = (
                'macro:///LingToolsBasic.ModuleMain.setMainDocURL("%s")' %
                self.mainDoc.url)
            logger.debug(sMacro)
            self.mainDoc.dispatcher.executeDispatch(
                self.writerDoc.frame, sMacro, "", 0, ())
            self.calledSetMainDoc = True

        logger.debug("getting index of button")
        oForm = self.writerDoc.document.getDrawPage().getForms().getByIndex(0)
        logger.debug("looking for button '%s'", oButtonModel.getName())
        logger.debug("Form has %d elements", oForm.getCount())
        nIndex = -1
        for formElemIndex, formElem in enumerate(iteruno.byIndex(oForm)):
            logger.debug(formElem.getName())
            if formElem.getName() == oButtonModel.getName():
                nIndex = formElemIndex
        logger.debug("nIndex=%d", nIndex)

        logger.debug("assigning action")
        oButtonModel.HelpText = sDestination   # a trick to pass the parameter
        sScriptURL = ("vnd.sun.star.script:"
                      "LingToolsBasic.ModuleMain.GoToTableInOtherDoc?"
                      "language=Basic&location=application")
        aEvent = uno.createUnoStruct(
            "com.sun.star.script.ScriptEventDescriptor")
        aEvent.AddListenerParam = ""
        aEvent.EventMethod = "actionPerformed"
        aEvent.ListenerType = "XActionListener"
        aEvent.ScriptCode = sScriptURL
        aEvent.ScriptType = "Script"
        oForm.registerScriptEvent(nIndex, aEvent)
        logger.debug(util.funcName('end'))

    def insertSection(self, bgcolor):
        logger.debug(util.funcName())
        self.section = self.writerDoc.document.createInstance(
            "com.sun.star.text.TextSection")
        self.section.BackColor = bgcolor
        self.writerDoc.text.insertTextContent(
            self.writerDoc.viewcursor, self.section, False)

    def disposing(self, dummy_aEvent):
        logger.debug("Disposing")
        self.writerDoc = None
        return None

