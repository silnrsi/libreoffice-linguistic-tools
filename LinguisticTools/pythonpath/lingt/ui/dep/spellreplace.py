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
import logging

# uno is required for unohelper
# pylint: disable=unused-import
import uno
# pylint: enable=unused-import
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgSpellReplace as _dlgdef
from lingt.ui.common.messagebox import MessageBox
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
        dlg = dutil.createDialog(self.unoObjs, _dlgdef)
        if not dlg:
            return
        ctrl_getter = dutil.ControlGetter(dlg)
        self.evtHandler = DlgEventHandler(self)
        self.dlgCtrls = DlgControls(
            self.unoObjs, ctrl_getter, self.evtHandler)
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

    def __init__(self, unoObjs, ctrl_getter, evtHandler):
        self.unoObjs = unoObjs
        self.evtHandler = evtHandler

        self.listSuggestions = ctrl_getter.get(_dlgdef.LISTBOX_SUGGESTIONS)
        self.txtChangeTo = ctrl_getter.get(_dlgdef.TXT_CHANGE_TO)
        self.lblFoundText = ctrl_getter.get(_dlgdef.LBL_FOUND_TEXT)
        self.lblContext = ctrl_getter.get(_dlgdef.LBL_CONTEXT)
        btnAdd = ctrl_getter.get(_dlgdef.BTN_ADD)
        btnChange = ctrl_getter.get(_dlgdef.BTN_CHANGE)
        btnChangeAll = ctrl_getter.get(_dlgdef.BTN_CHANGE_ALL)
        btnIgnore = ctrl_getter.get(_dlgdef.BTN_IGNORE)
        btnIgnoreAll = ctrl_getter.get(_dlgdef.BTN_IGNORE_ALL)
        btnClose = ctrl_getter.get(_dlgdef.BTN_CLOSE)

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

    @evt_handler.log_exceptions
    def itemStateChanged(self, dummy_itemEvent):
        """XItemListener event handler."""
        logger.debug(util.funcName())
        self.dlgCtrls.txtChangeTo.setText(
            self.dlgCtrls.listSuggestions.getSelectedItem())

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        self.mainForm.finish(event.ActionCommand)
