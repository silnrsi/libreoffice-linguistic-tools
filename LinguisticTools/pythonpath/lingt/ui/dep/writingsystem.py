"""
A dialog to select a writing system, as in FieldWorks.

This module exports:
    DlgWritingSystem
"""
import logging

# uno is required for unohelper
# pylint: disable=unused-import
import uno
# pylint: enable=unused-import
import unohelper
from com.sun.star.awt import XActionListener

from lingt.access.xml import writingsys_reader
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgWritingSystem as _dlgdef
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgwritingsystem")


class DlgWritingSystem(XActionListener, unohelper.Base):
    """Main class for this dialog."""

    def __init__(self, defaultCode, unoObjs):
        self.def_ws_code = defaultCode
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.selectedWS = writingsys_reader.WritingSystem()
        self.writingSystems = []
        self.listbox = None
        self.dlgClose = None
        self.dlgDispose = None

    def readFile(self, filepath):
        fileReader = writingsys_reader.WritingSysReader(filepath, self.unoObjs)
        self.writingSystems = fileReader.read()

    def getResult(self):
        return self.selectedWS

    def showDlg(self):
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.listbox = ctrl_getter.get(_dlgdef.WSLIST_BOX)
        btnOK = ctrl_getter.get(_dlgdef.BTN_OK)
        logger.debug("Got controls.")

        def_ws_display = theLocale.getText("(none)")
        self.listbox.addItem(def_ws_display, 0)
        for ws in self.writingSystems:
            listCount = self.listbox.getItemCount()
            ws_display = "%s (%s)" % (ws.name, ws.internalCode)
            self.listbox.addItem(ws_display, listCount)  # add at end of list
            if ws.internalCode == self.def_ws_code:
                def_ws_display = ws_display
        self.listbox.selectItem(def_ws_display, True)
        logger.debug("Added %d to list.", len(self.writingSystems))

        btnOK.setActionCommand("OK")
        btnOK.addActionListener(self)

        self.dlgClose = dlg.endExecute
        self.dlgDispose = dlg.dispose
        dlg.execute()

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        if event.ActionCommand == "OK":
            itemPos = self.listbox.getSelectedItemPos()
            logger.debug("Item %d selected.", itemPos)
            if itemPos is not None and itemPos > 0:
                wsIndex = itemPos - 1   # excluding the first entry "(none)"
                self.selectedWS = self.writingSystems[wsIndex]
            self.dlgClose()
            logger.debug("OK finished")
        else:
            evt_handler.raise_unknown_action(event.ActionCommand)

    def call_dispose(self):
        logger.debug("disposing")
        self.dlgDispose()
