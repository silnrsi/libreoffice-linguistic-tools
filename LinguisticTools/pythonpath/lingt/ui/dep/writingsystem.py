# -*- coding: Latin-1 -*-
#
# Created Sept 14 2010 by Jim Kornelsen
#
# 31-Mar-11 JDK  Localizations for "(none)"
# 09-Nov-12 JDK  Read file, rather than expecting to be given the data.
# 29-Mar-13 JDK  Localize "(none)" by code rather than by dialog setting.
# 15-Apr-13 JDK  Use list box instead of combo box.
# 18-Apr-13 JDK  Fixed bug: self.writingSystems index should be offset by 1.

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
from lingt.app import exceptions
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
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
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgWritingSystem")
        if not dlg:
            return
        try:
            self.listbox = dlg.getControl("WSListBox")
            btnOK = dlg.getControl("BtnOK")
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
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
        logger.debug(
            "Added " + str(len(self.writingSystems)) + " to list.")

        btnOK.setActionCommand("OK")
        btnOK.addActionListener(self)

        self.dlgClose = dlg.endExecute
        self.dlgDispose = dlg.dispose
        dlg.execute()

    @dutil.log_event_handler_exceptions
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
            raise exceptions.LogicError(
                "Unknown action command '%s'", event.ActionCommand)

    def call_dispose(self):
        logger.debug("disposing")
        self.dlgDispose()

