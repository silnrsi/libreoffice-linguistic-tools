# -*- coding: Latin-1 -*-
#
# This file created Sept 14 2010 by Jim Kornelsen
#
# 04-Oct-10 JDK  Use StatusIndicator instead of a ProgressBar control.
# 22-Oct-10 JDK  Added back getPercent method.
# 22-Apr-11 JDK  Using % to interpolate strings can throw exceptions.
# 23-Oct-12 JDK  Move ProgressBar class to its own file.
# 07-Nov-12 JDK  Allow for the controller of a different document.
# 28-Nov-12 JDK  Added FourButtonDialog.
# 19-Dec-12 JDK  Just pass controller along with document as main arg.
# 04-May-13 JDK  Do not mask exceptions during init.
# 24-Jul-13 JDK  Handle new AOO 4.0 parameters.
# 23-Jul-15 JDK  Added displayExc().
# 01-Aug-15 JDK  Use tuple unpacking for message arguments.
# 19-Oct-15 JDK  Move interpolating to app.exceptions module.

"""
Dialogs to display a message to the user.

This module exports:
    MessageBox
    FourButtonDialog
"""
import collections
import logging

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.lang import IllegalArgumentException

from lingt.app import exceptions
from lingt.ui.common import dutil
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.messagebox")


class MessageBox:
    """
    Message box for python, like OOo Basic MsgBox.
    Localizes messages before displaying.
    Modified from Villeroy 2007.
    """
    STYPE_MSG = 'messbox'
    STYPE_INFO = 'infobox' # info always shows one OK button alone!
    STYPE_ERROR = 'errorbox'
    STYPE_QUERY = 'querybox'
    STYPE_WARN = 'warningbox'
    BUTTONS_OK = 1
    BUTTONS_OK_CANCEL = 2
    BUTTONS_YES_NO = 3
    BUTTONS_YES_NO_CANCEL = 4
    RESULT_CANCEL = 0
    RESULT_OK = 1
    RESULT_YES = 2
    RESULT_NO = 3

    def __init__(self, genericUnoObjs):
        """
        Requires the frame of the higher level window.
        May throw com.sun.star.lang.DisposedException.
        Do not call logging methods from this __init__ routine.
        """
        self.parent = genericUnoObjs.frame.getContainerWindow()
        self.toolkit = self.parent.getToolkit()
        theLocale.loadUnoObjs(genericUnoObjs)

    def display(self, message, *msg_args, **kwargs):
        """
        :keyword arg title: Dialog title.
        """
        logger.debug("Displaying message box.")
        buttons = MessageBox.BUTTONS_OK
        self._showDialog(
            message, msg_args,
            title=kwargs.get('title', ""), buttons=buttons,
            stype=MessageBox.STYPE_INFO)

    def displayExc(self, exc):
        if isinstance(exc, exceptions.MessageError):
            self.display(exc.msg, *exc.msg_args)
        else:
            self.display(str(exc))

    def displayOkCancel(self, message, *msg_args, **kwargs):
        """
        :keyword arg title: Dialog title.
        :returns: True if OK was pressed, False for Cancel.
        """
        logger.debug("Displaying ok/cancel dialog.")
        buttons = MessageBox.BUTTONS_OK_CANCEL
        r = self._showDialog(
            message, msg_args,
            title=kwargs.get('title', ""), buttons=buttons,
            stype=MessageBox.STYPE_WARN)
        if r == MessageBox.RESULT_OK:
            return True
        return False

    def displayYesNoCancel(self, message, *msg_args, **kwargs):
        """
        :keyword arg title: Dialog title.
        :returns: 'yes','no', or 'cancel'
        """
        logger.debug("Displaying yes/no/cancel dialog.")
        buttons = MessageBox.BUTTONS_YES_NO_CANCEL
        r = self._showDialog(
            message, msg_args,
            title=kwargs.get('title', ""), buttons=buttons,
            stype=MessageBox.STYPE_QUERY)
        if r == MessageBox.RESULT_YES:
            return "yes"
        elif r == MessageBox.RESULT_NO:
            return "no"
        return "cancel"

    def _showDialog(self, message, msg_args, title, buttons, stype):
        """
        Wrapper for com.sun.star.awt.XMessageBoxFactory.

        :arg message: May contain "%" values to interpolate.
        :arg msg_args: Values to use for interpolation.
        """
        rect = uno.createUnoStruct('com.sun.star.awt.Rectangle')
        message = exceptions.interpolate_message(message, msg_args)
        message += " "  # padding so that it displays better
        logger.warning(message)
        try:
            box = self.toolkit.createMessageBox(
                self.parent, rect, stype, buttons, title, message)
        except IllegalArgumentException:
            # AOO 4.0 changes
            from com.sun.star.awt.MessageBoxType import (
                MESSAGEBOX, INFOBOX, QUERYBOX, WARNINGBOX, ERRORBOX)
            etype = MESSAGEBOX  # enumerated type
            if stype == MessageBox.STYPE_QUERY:
                etype = QUERYBOX
            elif stype == MessageBox.STYPE_WARN:
                etype = WARNINGBOX
            elif stype == MessageBox.STYPE_ERROR:
                etype = ERRORBOX
            elif stype == MessageBox.STYPE_INFO:
                etype = INFOBOX
            box = self.toolkit.createMessageBox(
                self.parent, etype, buttons, title, message)
        return box.execute()


def getNamedTuples(buttonList):
    ButtonTuple = collections.namedtuple(
        'ButtonTuple', ['index', 'action', 'text', 'name'])
    buttonIter = []
    for index, btn in enumerate(buttonList):
        action, text = btn
        name = "btn_" + action
        buttonIter.append(
            ButtonTuple(index, action, text, name))
    return buttonIter


class FourButtonDialog(unohelper.Base, XActionListener):
    """
    toolkit.createMessageBox() only allows up to three buttons of certain
    types.  Use this class for more flexibility with button number and names.
    """
    DefaultButtons = [['yes', "Yes"],
                      ['no', "No"],
                      ['yesToAll', "Yes to All"],
                      ['cancel', "Cancel"]]

    def __init__(self, genericUnoObjs):
        self.unoObjs = genericUnoObjs
        theLocale.loadUnoObjs(genericUnoObjs)
        self.result = ""
        self.dlgClose = None

    def display(self, message, *msg_args, **kwargs):
        """
        :keyword arg title: dialog title
        :keyword arg buttonList: buttons to show on the dialog
        :returns: which button pressed, for example 'yes'; see DefaultButtons
        """
        title = kwargs.get('title', "")
        buttonList = kwargs.get('buttonList', None)
        self.result = ""

        # create the dialog model and set the properties
        # create the dialog control and set the model
        dlgModel = self.unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", self.unoObjs.ctx)
        dlgModel.PositionX = 100
        dlgModel.PositionY = 100
        dlgModel.Width = 250
        dlgModel.Height = 70
        dlgModel.Title = theLocale.getText(title)
        ctrlContainer = self.unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", self.unoObjs.ctx)

        # create the label model and set the properties
        message = exceptions.interpolate_message(message, msg_args)
        message += " "  # padding so that it displays better
        lblModel = dlgModel.createInstance(
            "com.sun.star.awt.UnoControlFixedTextModel")
        lblModel.PositionX = 10
        lblModel.PositionY = 10
        lblModel.Width = 150
        lblModel.Height = 14
        lblModel.Name = "lblMessage"
        lblModel.TabIndex = 0
        lblModel.Label = message
        dlgModel.insertByName("lblMessage", lblModel)

        # create the button models and set the properties
        if not buttonList:
            buttonList = FourButtonDialog.DefaultButtons
        for btn in getNamedTuples(buttonList):
            btnModel = dlgModel.createInstance(
                "com.sun.star.awt.UnoControlButtonModel")
            btnModel.PositionX = 10 + (btn.index * 60)
            btnModel.PositionY = 45
            btnModel.Width = 50
            btnModel.Height = 14
            btnModel.Name = btn.name
            btnModel.TabIndex = btn.index + 1
            btnModel.Label = theLocale.getText(btn.text)
            dlgModel.insertByName(btn.name, btnModel)

        ctrlContainer.setModel(dlgModel)
        for btn in getNamedTuples(buttonList):
            ctrl = ctrlContainer.getControl(btn.name)
            ctrl.setActionCommand(btn.action)
            ctrl.addActionListener(self)
            logger.debug("Added button %s", btn.name)

        # create a peer and execute the dialog
        toolkit = self.unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.awt.ExtToolkit", self.unoObjs.ctx)

        ctrlContainer.setVisible(False)
        ctrlContainer.createPeer(toolkit, None)
        self.dlgClose = ctrlContainer.endExecute
        ctrlContainer.execute()

        # dispose the dialog
        ctrlContainer.dispose()
        return self.result

    @dutil.log_event_handler_exceptions
    def actionPerformed(self, event):
        """Handle which button was pressed."""
        logger.debug("Button pressed: %s", event.ActionCommand)
        self.result = event.ActionCommand
        self.dlgClose()
        logger.debug("Action finished.")


#------------------------------------------------------------------------------
# Everything below this point is for testing only
#------------------------------------------------------------------------------
#def showDlg(ctx=uno.getComponentContext()):
#    """Main method to show a dialog window.
#    You can call this method directly by Tools -> Macros -> Run Macro.
#    """
#    logger.debug("----showDlg()----------------------------------------------")
#    genericUnoObjs = util.UnoObjs(ctx)
#    logger.debug("got UNO context")
#
#    dlg = FourButtonDialog(genericUnoObjs)
#    dlg.display("Testing")

# Functions that can be called from Tools -> Macros -> Run Macro.
#g_exportedScripts = showDlg,
