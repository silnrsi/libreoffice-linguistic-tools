# -*- coding: Latin-1 -*-
#
# This file created October 25 2010 by Jim Kornelsen.

"""
Use this to quickly run some code.
In Basic this is easy using the editor, but in python it is not always easy,
so you can use this file instead.

To run in Windows:
  If not done yet, close OpenOffice and run start_soffice_listening.bat.
  Now drag this file to "run_test.bat"
"""
import uno
import logging
import time

from lingt.app import exceptions
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingttest.ad_hoc_testing")


def timeGetBigString():
    textCursor = unoObjs.text.createTextCursorByRange(
                 unoObjs.viewcursor.getStart())
    time1 = time.time()
    #textCursor.goRight(32768, True)   # throws CannotConvertException
    textCursor.goRight(32767, True)   # throws CannotConvertException
    textCursor.goRight(30000, True)    # works; apparently takes an int
    textCursor.goRight(30000, True)
    textCursor.goRight(30000, True)
    for rep in range(0, 500):
        strval = textCursor.getString()
        textCursor.goRight(1, True)
    time2 = time.time()
    msgbox.display("String length %d" % (len(strval)))
    msgbox.display("Elapsed time: %2.1f seconds" % (time2 - time1))

def timeGoRight():
    oVC = unoObjs.viewcursor
    textCursor = unoObjs.text.createTextCursorByRange(oVC.getStart())
    textCursor.goRight(5, True)
    #util.xray(textCursor, unoObjs)
    time1 = time.time()
    REPS = 1000     # number of repetitions
    DISTANCE = 10
    for rep in range(0, REPS):
        textCursor.goRight(DISTANCE, True)
        textCursor.goLeft(DISTANCE, False)
    time2 = time.time()
    msgbox.display("Elapsed time: %2.1f seconds" % (time2 - time1))

    time1 = time.time()
    for i in range(0, REPS):
        for j in range(0, DISTANCE): textCursor.goRight(1, False)
        for j in range(0, DISTANCE): textCursor.goLeft(1, False)
    time2 = time.time()
    msgbox.display("Elapsed time: %2.1f seconds" % (time2 - time1))
    
def testChangingRanges():
    oVC = unoObjs.viewcursor
    textCursor = unoObjs.text.createTextCursorByRange(oVC.getStart())
    textCursor.goRight(5, False)
    textCursor.goRight(10, True)
    msgbox.display(textCursor.getString())

    from lingt.Access.Writer.Search import TextSearch
    textSearch = TextSearch(unoObjs, None)
    textSearch.addRange(textCursor)
    textRanges = textSearch.getRanges()
    #textCursor.goRight(0, False)

    #oVC.goRight(9, False)
    oVC.goRight(3, False)
    oVC.goRight(5, True)
    oVC.setString("xx")

    for txtRange in textRanges:
        oSel = txtRange.sel
        oVC.gotoRange(oSel.getStart(), False)
        oVC.gotoRange(oSel.getEnd(), True) # select
        msgbox.display(oVC.getString())

def copyAll():
    #component = unoObjs.document
    #controller = component.getCurrentController()
    #frame = controller.getFrame()
    newDoc = unoObjs.desktop.loadComponentFromURL(
        "private:factory/swriter", "_blank", 0, ())
    newWriterDoc = unoObjs.getDocObjs(newDoc)
    #dispatcher.executeDispatch(
    #    frame, ".uno:SelectAll", "", 0, ())
    #dispatcher.executeDispatch(
    #    frame, ".uno:Copy", "", 0, ())
    #dispatcher.executeDispatch(
    #    frame, ".uno:Paste", "", 0, ())
    oVC = unoObjs.viewcursor
    oVC.gotoStart(False)
    oVC.gotoEnd(True)
    selectedContent = unoObjs.controller.getTransferable() 
    newWriterDoc.controller.insertTransferable(selectedContent)

def testCellEnumeration():
    from lingt.Access.Calc.SpreadsheetReader import SpreadsheetReader
    reader = SpreadsheetReader(unoObjs)
    stringList = reader.getColumnStringList('A', skipFirstRow=False)
    print(repr(stringList))
    stringList = reader.getColumnStringListByLen('A', False, 15)
    print(repr(stringList))

def testSelString():
    oVC = unoObjs.viewcursor
    #oVC.gotoRange(unoObjs.text.getStart(), False)
    #oVC.gotoRange(unoObjs.text.getEnd(), True)  # select
    #msgbox.display(oVC.getString())

    print("oVC.isCollapsed() == %s" % str(oVC.isCollapsed()))
    oSels = unoObjs.controller.getSelection()
    if oSels.getCount() == 1:
        oSel = oSels.getByIndex(0)
        if oSel.supportsService("com.sun.star.text.TextRange"):
            cursor = oSel.getText().createTextCursorByRange(oSel)
            print("cursor.isCollapsed() == %s" % str(cursor.isCollapsed()))
            if cursor.isCollapsed():
                print("is collapsed")
            else:
                print("is not collapsed")

    #oCurs = oVC.getText().createTextCursorByRange(oVC)
    #oCurs.goRight(1, False)
    #oCurs.goRight(4, True)
    #oCurs2 = oVC.getText().createTextCursorByRange(oCurs)
    #oCurs2.goRight(1, False)
    #oCurs2.goRight(4, True)
    #unoObjs.controller.select(oCurs)

    #unoObjs.controller.select(oCurs2)
    #unoObjs.controller.select((oCurs2, oCurs))
    #oVC.goRight(4, True)
    #oVC.goRight(4, False)
    #oVC.goRight(4, True)

def testReadInsertUnicode():
    """
    On Windows, LO / OOo only works correctly when given unicode strings.
    On Linux, LO accepts byte data in byte strings (e.g. b"\xe0") as well.

    To be safe, it's probably best just to assume Office always requires
    unicode strings.
    """
    oVC = unoObjs.viewcursor
    oVC.getText().insertString(oVC, b"1. \u0bae\n", False)
    oVC.getText().insertString(oVC, u"2. \u0bae\n", False)
    oVC.getText().insertString(oVC, b"3. \xe0\xae\xae\n", False)
    oVC.getText().insertString(oVC, b"4. " + u"\u0bae".encode("utf-8") + b"\n",
                               False)

def impress():
    print("isRunning() == %s" % unoObjs.presentation.isRunning())
    unoObjs.presentation.start()
    print("isRunning() == %s" % unoObjs.presentation.isRunning())
    while not unoObjs.presentation.isRunning():
        pass
    controller = unoObjs.presentation.getController()
    controller.gotoNextSlide()
    print("isRunning() == %s" % controller.isRunning())
    #unoObj = unoObjs.page
    #unoObj = unoObjs.controller
    #unoObj = unoObjs.document
    #unoObj = unoObjs.desktop

def doReplace():
    oDoc = unoObjs.document
    #r = oDoc.createReplaceDescriptor()
    #r.setSearchString("FOOBAR")
    #r.setReplaceString("OTHERSTUFF")
    #oDoc.replaceAll(r)
    #return

    #r = oDoc.createReplaceDescriptor()
    search = oDoc.createSearchDescriptor()
    search.SearchRegularExpression = True
    search.SearchString = "FOOBAR$"
    selsFound = oDoc.findAll(search)
    for sel_index in range(0, selsFound.getCount()):
        oSel = selsFound.getByIndex(sel_index)
        try:
            oCursor = oSel.getText().createTextCursorByRange(oSel)
        except (RuntimeException, IllegalArgumentException):
            return
        #oCursor.goRight(1, True)  # select
        #oCursor.goEnd(1, True)  # select
        oCursor.setString("")  # delete
        oCursor.goRight(1, True) # select newline character
        oCursor.setString("")  # delete

    #r.setSearchString("FOOBAR\n")
    #r.setSearchString("FOOBAR$")
    #r.setReplaceString("OTHERSTUFF")
    #oDoc.replaceAll(r)
    #r = oDoc.createReplaceDescriptor()
    #r.setSearchString("FOOBAR\r")
    #r.setReplaceString("OTHERSTUFF")
    #oDoc.replaceAll(r)

def displayAttrs():
    unoObj = unoObjs.text
    oVC = unoObjs.viewcursor
    #util.xray(oVC, unoObjs)
    #util.xray(unoObjs.controller, unoObjs)

    from lingt.access.writer import uservars
    from lingt.ui.dep.wordlistfile import DlgWordListFile
    from lingt.app.fileitemlist import WordListFileItem
    userVars = uservars.UserVars("LTw_", unoObjs.document, logger)
    newItem = WordListFileItem(userVars)
    dlgFile = DlgWordListFile(newItem, unoObjs, userVars)
    dlgFile.showDlg()
    lbox = dlgFile.dlgCtrls.listboxFileType
    lbox.removeItems(1, 8)
    #util.xray(lbox, unoObjs)
    items = lbox.getItems()
    print("repr %r, len %d" % (items, len(items)))
    dlgFile.dlgDispose()

    #tables = unoObjs.document.getTextTables()
    #table = tables.getByName("Table1");

    #oSels = unoObjs.controller.getSelection()
    #util.xray(unoObjs.document, unoObjs)
    #util.xray(table, unoObjs)

    #displayText = "Hello there\n\n\tHow are you?\nFine, thank you\t"
    #title = "An unimportant testing message"
    #msgbox.display(displayText, title=title)

    #xText = unoObjs.text
    #dlg = dutil.createDialog(
    #    unoObjs, msgbox, "DlgGrammarSettings")
    #ctrl = dutil.getControl(dlg, "chkMorphemesSeparateCols")

    #xforms = unoObjs.document.getXForms()
    #formName = xforms.getElementNames()[0]
    #xform = xforms.getByName(formName)
    #xTextRange = xText.getEnd()
    #xTextRange.setString(formName)
    #joinedString = "".join(elemNames)
    #msgbox.display(joinedString, title="title")
    #xform = xforms.getByIndex(0)
    #util.xray(xforms, unoObjs)
    #util.xray(xform, unoObjs)

    #xform = xforms.getByIndex(0)
    #util.xray(ctrl, unoObjs)
    #oVC.getText().insertString(oVC, oVC.getPropertyValue("ParaAdjust"), False)

    # Run one of these three in Basic:

    #GlobalScope.BasicLibraries.LoadLibrary( "Tools" )
    #Call Tools.WritedbgInfo(ThisComponent)

    #GlobalScope.BasicLibraries.LoadLibrary("XrayTool")
	#Xray ThisComponent

    # Globalscope.BasicLibraries.LoadLibrary( "MRILib" )
    # Mri ThisComponent

#------------------------------------------------------------------------------
# Main routine
#------------------------------------------------------------------------------
print("Starting...")
ctx = util.UnoObjs.getCtxFromSocket()
unoObjs = util.UnoObjs(ctx)
#unoObjs = util.UnoObjs(ctx, 'calc')
#unoObjs = util.UnoObjs(ctx, 'impress')
#msgbox = MessageBox(unoObjs)

#copyAll()
#testSelString()
#testReadInsertUnicode()
#impress()
displayAttrs()
#doReplace()
print("Finished!")

