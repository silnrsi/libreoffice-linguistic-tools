"""
Dialogs to display a message to the user.

This module exports:
    MessageBox
    FourButtonDialog
"""
import collections
import logging

import unohelper
from com.sun.star.awt import Rectangle
from com.sun.star.awt import XActionListener
from com.sun.star.awt import MessageBoxType
from com.sun.star.lang import IllegalArgumentException

from lingt.app import exceptions
from lingt.ui.common import evt_handler
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.messagebox")

class MessageBox:
    """Message box for python, like LO Basic MsgBox.
    Localizes messages before displaying.
    Based on Villeroy 2007.
    """
    BUTTONS_OK = 1
    BUTTONS_OK_CANCEL = 2
    BUTTONS_YES_NO = 3
    BUTTONS_YES_NO_CANCEL = 4
    RESULT_CANCEL = 0
    RESULT_OK = 1
    RESULT_YES = 2
    RESULT_NO = 3

    def __init__(self, genericUnoObjs):
        """Requires the frame of the higher level window.
        May throw com.sun.star.lang.DisposedException.
        Do not call logging methods from this __init__ routine.
        """
        self.parent = genericUnoObjs.frame.getContainerWindow()
        self.toolkit = self.parent.getToolkit()
        theLocale.loadUnoObjs(genericUnoObjs)

    def display(self, message, *msg_args, **kwargs):
        """:keyword arg title: Dialog title."""
        logger.debug("Displaying message box.")
        buttons = MessageBox.BUTTONS_OK
        self._showDialog(
            message, msg_args,
            title=kwargs.get('title', ""), buttons=buttons,
            etype=MessageBoxType.INFOBOX)

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
            etype=MessageBoxType.WARNINGBOX)
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
        result = self._showDialog(
            message, msg_args,
            title=kwargs.get('title', ""), buttons=buttons,
            etype=MessageBoxType.QUERYBOX)
        if result == MessageBox.RESULT_YES:
            return "yes"
        if result == MessageBox.RESULT_NO:
            return "no"
        return "cancel"

    def _showDialog(self, message, msg_args, title, buttons, etype):
        """Wrapper for com.sun.star.awt.XMessageBoxFactory.
        :arg message: May contain "%" values to interpolate.
        :arg msg_args: Values to use for interpolation.
        :arg etype: type of message box (enumerated, not just a string)
        """
        message = exceptions.interpolate_message(message, msg_args)
        message += " "  # padding so that it displays better
        logger.warning(message)
        try:
            box = self.toolkit.createMessageBox(
                self.parent, etype, buttons, title, message)
        except IllegalArgumentException:
            # old API before AOO 4.0
            stype = 'messbox'  # string type
            if etype == MessageBoxType.QUERYBOX:
                stype = 'querybox'
            elif etype == MessageBoxType.WARNINGBOX:
                stype = 'warningbox'
            elif etype == MessageBoxType.ERRORBOX:
                stype = 'errorbox'
            elif etype == MessageBoxType.INFOBOX:
                stype = 'infobox'  # info always shows one OK button alone!
            rect = Rectangle()
            box = self.toolkit.createMessageBox(
                self.parent, rect, stype, buttons, title, message)
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
    """toolkit.createMessageBox() only allows up to three buttons of certain
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

    @evt_handler.log_exceptions
    def actionPerformed(self, event):
        """Handle which button was pressed."""
        logger.debug("Button pressed: %s", event.ActionCommand)
        self.result = event.ActionCommand
        self.dlgClose()
        logger.debug("Action finished.")
