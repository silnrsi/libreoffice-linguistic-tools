#!/usr/bin/python
# -*- coding: Latin-1 -*-

# MessageBox.py
#              
# Change History:
#   Created Sept 14 2010 by Jim Kornelsen
#
#   04-Oct-10 JDK  Use StatusIndicator instead of a ProgressBar control.
#   22-Oct-10 JDK  Added back getPercent method.
#   22-Apr-11 JDK  Using % to interpolate strings can throw exceptions.
#   23-Oct-12 JDK  Move ProgressBar class to its own file.
#   07-Nov-12 JDK  Allow for the controller of a different document.
#   28-Nov-12 JDK  Added FourButtonDialog.

"""
Dialogs to display a message to the user.
"""
import uno
import unohelper
from   com.sun.star.awt import XActionListener
import logging

from lingt.Utils        import Utils
from lingt.Utils.Locale import Locale

class MessageBox:
    """Message box for python, like OOo Basic MsgBox.
    Localizes messages before displaying.
    Modified from Villeroy 2007.
    """
    STYPE_ERROR = 'errorbox'
    STYPE_QUERY = 'querybox'
    STYPE_WARN  = 'warningbox' 
    STYPE_INFO  = 'infobox' # info always shows one OK button alone! 
    BUTTONS_OK            = 1
    BUTTONS_OK_CANCEL     = 2
    BUTTONS_YES_NO        = 3 
    BUTTONS_YES_NO_CANCEL = 4 
    RESULT_CANCEL = 0
    RESULT_OK     = 1
    RESULT_YES    = 2
    RESULT_NO     = 3 

    def __init__(self, unoObjs, logger, doc=None):
        """Requires the frame of the higher level window.
        Note: Don't call logging methods from this __init__ routine.
        """
        try:
            if doc:
                self.parent  = doc.frame.getContainerWindow() 
            else:
                self.parent  = unoObjs.frame.getContainerWindow() 
            self.toolkit = self.parent.getToolkit()
        except:
            raise AttributeError, 'Did not get a valid parent window' 
        self.logger = logger
        self.locale = Locale(unoObjs)

    def display(self, message='', vals=None, title=''):
        self.logger.debug("Displaying message box.")
        buttons = MessageBox.BUTTONS_OK
        self.__showDialog(message, vals, title, buttons, MessageBox.STYPE_INFO)

    def displayOkCancel(self, message='', vals=None, title=''):
        """Returns True if OK was pressed, False for Cancel."""
        buttons = MessageBox.BUTTONS_OK_CANCEL
        r = self.__showDialog(
                    message, vals, title, buttons, MessageBox.STYPE_WARN)
        if r == MessageBox.RESULT_OK:
            return True
        return False

    def displayYesNoCancel(self, message='', vals=None, title=''):
        """Returns a string: 'yes','no', or 'cancel'"""
        self.logger.debug("Displaying yes/no/cancel dialog.")
        buttons = MessageBox.BUTTONS_YES_NO_CANCEL
        r = self.__showDialog(
                    message, vals, title, buttons, MessageBox.STYPE_QUERY)
        if r == MessageBox.RESULT_YES:
            return "yes"
        elif r == MessageBox.RESULT_NO:
            return "no"
        return "cancel"

    def __showDialog(self, message, vals, title, buttons, stype):
        """Wrapper for com.sun.star.awt.XMessageBoxFactory.
        Private function.
        To include variables, specify them in vals (tuple,) and put %s %d etc
        in the message.
        """
        rect = uno.createUnoStruct('com.sun.star.awt.Rectangle')
        message = self.locale.getText(message)
        if vals is not None:
            try:
                message = message % vals    # for example "%d" % (50)
            except (TypeError, UnicodeDecodeError):
                self.logger.warn("message \"" + repr(message) +
                                 "\" failed to interpolate vals " + repr(vals))
        message = message + " "  # padding so that it displays better
        self.logger.warn(message)
        box = self.toolkit.createMessageBox(
              self.parent, rect, stype, buttons, title, message)
        return box.execute()

class FourButtonDialog(unohelper.Base, XActionListener):
    """
    toolkit.createMessageBox() only allows up to three buttons of certain
    types. Use this class for more flexibility with button number and names.
    """
    DefaultButtons = [['yes',      "Yes"],
                      ['no',       "No"],
                      ['yesToAll', "Yes to All"],
                      ['cancel',   "Cancel"]]

    def __init__(self, unoObjs, logger):
        self.unoObjs = unoObjs
        self.locale  = Locale(unoObjs)
        self.logger  = logger

    def display(self, message='', vals=None, title='', buttons=None):
        self.result = None

        # create the dialog model and set the properties 
        # create the dialog control and set the model 
        dlgModel = self.unoObjs.smgr.createInstanceWithContext( 
                   "com.sun.star.awt.UnoControlDialogModel", self.unoObjs.ctx)
        dlgModel.PositionX = 100
        dlgModel.PositionY = 100
        dlgModel.Width     = 250 
        dlgModel.Height    = 70
        dlgModel.Title     = self.locale.getText(title)
        ctrlContainer = self.unoObjs.smgr.createInstanceWithContext( 
                        "com.sun.star.awt.UnoControlDialog", self.unoObjs.ctx)

        # create the label model and set the properties 
        message = self.locale.getText(message)
        if vals is not None:
            try:
                message = message % vals    # for example "%d" % (50)
            except (TypeError, UnicodeDecodeError):
                self.logger.warn("message \"" + repr(message) +
                                 "\" failed to interpolate vals " + repr(vals))
        message = message + " "  # padding so that it displays better
        lblModel = dlgModel.createInstance( 
                   "com.sun.star.awt.UnoControlFixedTextModel")
        lblModel.PositionX = 10 
        lblModel.PositionY = 10 
        lblModel.Width     = 150 
        lblModel.Height    = 14 
        lblModel.Name      = "lblMessage" 
        lblModel.TabIndex  = 0
        lblModel.Label     = message
        dlgModel.insertByName("lblMessage", lblModel); 

        # create the button models and set the properties 
        if not buttons:
            buttons = FourButtonDialog.DefaultButtons
        for btn_i, btn in enumerate(buttons):
            btnVal, btnText = btn
            btnName  = "btn_" + btnVal
            btnModel = dlgModel.createInstance( 
                       "com.sun.star.awt.UnoControlButtonModel")
            btnModel.PositionX  = 10 + (btn_i * 60)
            btnModel.PositionY  = 45 
            btnModel.Width      = 50 
            btnModel.Height     = 14
            btnModel.Name       = btnName
            btnModel.TabIndex   = btn_i + 1        
            btnModel.Label      = self.locale.getText(btnText)
            dlgModel.insertByName(btnName, btnModel)

        ctrlContainer.setModel(dlgModel)
        for btn_i, btn in enumerate(buttons):
            btnVal, btnText = btn
            btnName  = "btn_" + btnVal
            ctrl = ctrlContainer.getControl(btnName)
            ctrl.setActionCommand(btnVal)
            ctrl.addActionListener(self)
            self.logger.debug("Added button " + btnName)

        # create a peer and execute the dialog
        toolkit = self.unoObjs.smgr.createInstanceWithContext( 
            "com.sun.star.awt.ExtToolkit", self.unoObjs.ctx);       

        ctrlContainer.setVisible(False);       
        ctrlContainer.createPeer(toolkit, None);
        self.dlgClose = ctrlContainer.endExecute
        ctrlContainer.execute()

        # dispose the dialog 
        ctrlContainer.dispose()
        return self.result

    def actionPerformed(self, event):
        """Handle which button was pressed."""
        self.logger.debug(
            "Button pressed: " + Utils.safeStr(event.ActionCommand))
        self.result = event.ActionCommand
        self.dlgClose()
        self.logger.debug("Action finished.")

#-------------------------------------------------------------------------------
# Everything below this point is for testing only
#-------------------------------------------------------------------------------
def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.MessageBox")
    logger.debug("----ShowDlg()----------------------------------------------")
    unoObjs = Utils.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = FourButtonDialog(unoObjs, logger)
    dlg.display("Testing")

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = ShowDlg,
