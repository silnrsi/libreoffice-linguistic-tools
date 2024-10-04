"""
Use this to quickly run some code.
In Basic this is easy using the editor, but in python it is not always easy,
so you can use this file instead.

To run in Windows:
If not done yet, close LibreOffice and run start_soffice_listening.bat.
Now drag this file to "run_test.bat"
"""
import logging
import threading
import time

import uno  # pylint: disable=import-error
#from com.sun.star.awt import Rectangle
from com.sun.star.awt import VclWindowPeerAttribute
from com.sun.star.awt import WindowClass
from com.sun.star.awt import WindowDescriptor
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import RuntimeException

from lingt.access.calc.spreadsheet_reader import SpreadsheetReader
from lingt.access.writer.textsearch import TxRanger
from lingt.access.writer import styles
#from lingt.ui.common import dutil
#from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util
#from lingt.access.writer import uservars
#from lingt.app.fileitemlist import WordListFileItem
#from lingt.ui.dep.wordlistfile import DlgWordListFile

logger = logging.getLogger("lingttest.ad_hoc_testing")
msgbox = None
unoObjs = None

def timeGetBigString():
    textCursor = unoObjs.text.createTextCursorByRange(
                 unoObjs.viewcursor.getStart())
    time1 = time.time()
    #textCursor.goRight(32768, True)   # throws CannotConvertException
    textCursor.goRight(32767, True)   # throws CannotConvertException
    textCursor.goRight(30000, True)    # works; apparently takes an int
    textCursor.goRight(30000, True)
    textCursor.goRight(30000, True)
    for _ in range(500):
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
    REPS = 1000  # number of repetitions
    DISTANCE = 10
    for _ in range(REPS):
        textCursor.goRight(DISTANCE, True)
        textCursor.goLeft(DISTANCE, False)
    time2 = time.time()
    msgbox.display("Elapsed time: %2.1f seconds" % (time2 - time1))

    time1 = time.time()
    for _ in range(REPS):
        for _ in range(DISTANCE):
            textCursor.goRight(1, False)
        for _ in range(DISTANCE):
            textCursor.goLeft(1, False)
    time2 = time.time()
    msgbox.display("Elapsed time: %2.1f seconds" % (time2 - time1))

def testChangingRanges():
    oVC = unoObjs.viewcursor
    textCursor = unoObjs.text.createTextCursorByRange(oVC.getStart())
    textCursor.goRight(5, False)
    textCursor.goRight(10, True)
    msgbox.display(textCursor.getString())

    ranger = TxRanger(unoObjs, True)
    ranger.addRange(textCursor)
    textRanges = ranger.getRanges()
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
    """On Windows, LO only works correctly when given unicode strings.
    On Linux, LO accepts byte data in byte strings (e.g. b"\xe0") as well.

    To be safe, it's probably best just to assume Office always requires
    unicode strings.
    """
    oVC = unoObjs.viewcursor
    oVC.getText().insertString(oVC, "1. \u0bae\n", False)  # Unicode string
    oVC.getText().insertString(oVC, b"2. \xe0\xae\xae\n", False)  # Byte string
    oVC.getText().insertString(oVC, b"3. " + "\u0bae".encode("utf-8") + b"\n",
                               False)  # UTF-8 bytes converted from Unicode

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

def underlying_style_names():
    styleNames = styles.getListOfStyles('ParagraphStyles', unoObjs)
    for styleName in styleNames:
        print(
            "disp_name=" + styleName[0] +
            ", underlying_name=" + styleName[1] + ";")

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
    #unoObj = unoObjs.text
    #oVC = unoObjs.viewcursor
    #util.xray(oVC, unoObjs)
    #util.xray(unoObjs.controller, unoObjs)

    util.xray(unoObjs.document, unoObjs)

    #userVars = uservars.UserVars("LTw_", unoObjs.document, logger)
    #newItem = WordListFileItem(userVars)
    #dlgFile = DlgWordListFile(newItem, unoObjs, userVars)
    #dlgFile.showDlg()
    #lbox = dlgFile.dlgCtrls.listboxFileType
    #lbox.removeItems(1, 8)
    #util.xray(lbox, unoObjs)
    #items = lbox.getItems()
    #print("repr %r, len %d" % (items, len(items)))
    #dlgFile.dlgDispose()

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
    #    unoObjs, msgbox, "DlgInterlinSettings")
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

def fs2_GoToTimestamp(*args):
    """from https://stackoverflow.com/questions/44703487/"""
    # Get doc from scripting context which is made available to all scripts
    desktop = unoObjs.desktop
    model = desktop.getCurrentComponent()
    oSelected = model.getCurrentSelection()
    cursor = desktop.getCurrentComponent().getCurrentController().getViewCursor()
    util.xray(cursor, unoObjs)

    def get_selected_text(oSelected, cursor):
        oText = ""
        try:
            oSel = oSelected.getByIndex(0)
            oText = oSel.getString()
        except (RuntimeException, IllegalArgumentException):
            pass
        if oText == "":
            cursor.gotoStartOfLine(False)  # Move cursor to start without selecting (False)
            cursor.gotoEndOfLine(True)  # Now move cursor to end of line selecting all (True)
            try:
                oSelected = model.getCurrentSelection()
                oSel = oSelected.getByIndex(0)
                oText = oSel.getString()
                cursor.gotoStartOfLine(False)  # Deselect line
            except (RuntimeException, IllegalArgumentException):
                pass
        return oText

    def extract_time(oText):
        valid_chars = '0123456789:'
        timestamp = ''.join(char for char in oText if char in valid_chars)
        if timestamp.count(":") == 1:
            oM, oS = timestamp.split(":")
            oH = "00"
        elif timestamp.count(":") == 2:
            oH, oM, oS = timestamp.split(":")
        else:
            return None
        if len(oS) != 2:
            oS = oS[:2]
        try:
            secs = int(oS) + int(oM) * 60 + int(oH) * 3600
            return secs
        except ValueError:
            return None

    oText = get_selected_text(oSelected, cursor)
    timestamp = extract_time(oText)
    if timestamp is not None:
        seek_instruction = f'seek{timestamp}\n'
        print(seek_instruction)

def create_dlg(toolkit, parent):
    #describe window properties.
    aDescriptor = WindowDescriptor()
    aDescriptor.Type = WindowClass.MODALTOP
    aDescriptor.WindowServiceName = "messbox"
    aDescriptor.ParentIndex = -1
    aDescriptor.Parent = parent
    #aDescriptor.Bounds = Rectangle()
    aDescriptor.WindowAttributes = VclWindowPeerAttribute.OK
    #tk = parent.getToolkit()
    #msgbox_tk = tk.createWindow(aDescriptor)
    #msgbox_tk.setMessageText("Hi there!")
    #msgbox_tk.setCaptionText("a title")
    dlg = toolkit.createWindow(aDescriptor)
    return dlg

class DialogThread(threading.Thread):
    def __init__(self, doc):
        threading.Thread.__init__(self)
        self.dlg = None
        self.parent = doc.CurrentController.Frame.ContainerWindow
        self.toolkit = self.parent.getToolkit()
        print("__init__")
        self.val = 1

    def run(self):
        print("run() begin")
        self.dlg = create_dlg(self.toolkit, self.parent)
        util.xray(self.dlg, unoObjs)
        print("run() 2")
        self.val = 2
        #self.dlg.execute()
        print("run() end")
        self.val = 3

    def dispval(self):
        print("val = " + str(self.val))

def show_mdlg():
    doc = unoObjs.document
    util.xray(doc, unoObjs)
    #util.xray(doc, unoObjs)
    #parent = doc.CurrentController.Frame.ContainerWindow
    #toolkit = parent.getToolkit()
    #dlg = create_dlg(toolkit, parent)
    #util.xray(dlg, unoObjs)
    #doc = XSCRIPTCONTEXT.getDocument()
    #t = DialogThread(doc)
    #t.start()
    #t.dispval()
    #time.sleep(1)
    #t.dispval()
    #if t.dlg:
    #    print("t.dlg =...")
    #    dir(t.dlg)
    #    #util.xray(t.dlg, unoObjs)
    #else:
    #    print("t.dlg not")
    #t.dlg.endExecute()

#------------------------------------------------------------------------------
# Main routine
#------------------------------------------------------------------------------
if __name__ == '__main__':
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
    #fs2_GoToTimestamp()
    show_mdlg()
    #underlying_style_names()
    #displayAttrs()
    #doReplace()
    print("Finished!")
