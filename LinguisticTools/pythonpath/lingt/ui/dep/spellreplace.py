# -*- coding: Latin-1 -*-
#
# This file created Dec 7 2012 by Jim Kornelsen
#
# 10-May-13 JDK  Show message if changed was pressed but no changes.
# 01-Jul-15 JDK  Refactor controls and events into separate classes.

"""
Asks whether to add or change a particular misspelled word.
Called by WordAsker.checkSpelling() in app.svc.spellingchecks.

This module exports:
    DlgSpellingReplace
"""
# uno is required for unohelper
import logging
# pylint: disable=unused-import
import uno
# pylint: enable=unused-import
import unohelper

from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.app import exceptions
from lingt.ui import dutil
from lingt.ui.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.ui.dlgspellreplace")


class DlgSpellingReplace:
    """Main class for this dialog."""

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.dlgCtrls = None
        self.evtHandler = None
        self.buttonPressed = ""
        self.changeTo = None
        self.doExecute = None
        self.doEndExecute = None
        self.doDispose = None

    def makeDlg(self):
        """This method will neither show nor destroy the dialog.
        That is left up to the calling code, via
        doExecute() and doDispose().
        """
        logger.debug(util.funcName(obj=self))
        dlg = dutil.createDialog(
            self.unoObjs, self.msgbox, "DlgSpellReplace")
        if not dlg:
            return
        self.evtHandler = DlgEventHandler(self)
        try:
            self.dlgCtrls = DlgControls(
                self.unoObjs, dlg, self.evtHandler)
        except exceptions.LogicError as exc:
            self.msgbox.displayExc(exc)
            dlg.dispose()
            return
        self.evtHandler.setCtrls(self.dlgCtrls)

        ## Methods to display and close the dialog

        self.doExecute = dlg.execute
        # hides the dialog and cause the execute() method to return
        self.doEndExecute = dlg.endExecute
        # destroys the dialog
        self.doDispose = dlg.dispose

    def setContents(self, textFound, suggestions, context):
        self.buttonPressed = ""
        self.changeTo = textFound
        self.dlgCtrls.lblFoundText.setText(textFound)
        self.dlgCtrls.lblContext.setText(context)
        self.dlgCtrls.txtChangeTo.setText(textFound)
        logger.debug(repr(suggestions))
        dutil.fill_list_ctrl(self.dlgCtrls.listSuggestions, suggestions)
        logger.debug(util.funcName('end'))

    def finish(self, buttonPressed):
        if buttonPressed in ['Change', 'ChangeAll']:
            if (self.dlgCtrls.txtChangeTo.getText() ==
                    self.dlgCtrls.lblFoundText.getText()):
                self.msgbox.display(
                    "You did not made any changes to the word.")
                return
        self.buttonPressed = buttonPressed
        self.changeTo = self.dlgCtrls.txtChangeTo.getText()
        self.doEndExecute()   # return from the execute() loop

    def getResults(self):
        return self.buttonPressed, self.changeTo


class DlgControls:
    """Store dialog controls."""

    def __init__(self, unoObjs, dlg, evtHandler):
        """raises: exceptions.LogicError if controls cannot be found"""
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.listSuggestions = dutil.getControl(dlg, "listboxSuggestions")
        self.txtChangeTo = dutil.getControl(dlg, "txtChangeTo")
        self.lblFoundText = dutil.getControl(dlg, "lblFoundText")
        self.lblContext = dutil.getControl(dlg, "lblContext")
        btnAdd = dutil.getControl(dlg, "btnAdd")
        btnChange = dutil.getControl(dlg, "btnChange")
        btnChangeAll = dutil.getControl(dlg, "btnChangeAll")
        btnIgnore = dutil.getControl(dlg, "btnIgnore")
        btnIgnoreAll = dutil.getControl(dlg, "btnIgnoreAll")
        btnClose = dutil.getControl(dlg, "btnClose")

        self.listSuggestions.addItemListener(self.evtHandler)

        btnAdd.setActionCommand('Add')
        btnChange.setActionCommand('Change')
        btnChangeAll.setActionCommand('ChangeAll')
        btnIgnore.setActionCommand('Ignore')
        btnIgnoreAll.setActionCommand('IgnoreAll')
        btnClose.setActionCommand('Close')
        for ctrl in (btnAdd, btnChange, btnChangeAll, btnIgnore, btnIgnoreAll,
                     btnClose):
            ctrl.addActionListener(self.evtHandler)


class DlgEventHandler(XActionListener, XItemListener, unohelper.Base):
    """Handles dialog events."""

    def __init__(self, mainForm):
        self.mainForm = mainForm
        self.dlgCtrls = None

    def setCtrls(self, dlgCtrls):
        self.dlgCtrls = dlgCtrls

    @dutil.log_event_handler_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName())
        self.dlgCtrls.txtChangeTo.setText(
            self.dlgCtrls.listSuggestions.getSelectedItem())

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        self.mainForm.finish(event.ActionCommand)

