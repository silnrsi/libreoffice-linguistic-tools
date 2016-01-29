#!/usr/bin/python
# -*- coding: Latin-1 -*-

# DlgDataConv.py
#
# Change History:
#   Created Nov 16 2012 by Jim Kornelsen
#
#
#
#
#
#
# Hacked 30-Nov-12 for testing by Jim.
#
#

"""
Dialog to apply an SIL converter.
Could be expanded to perform other conversions in the future, although I'm not
sure what, because EncConverters does everything useful that I can think of.
"""
import uno
import unohelper
from   com.sun.star.awt import XActionListener
import logging

from lingt.Utils                    import Utils
from lingt.Utils.Locale             import Locale
from lingt.UI.MessageBox            import MessageBox
from lingt.App                      import Exceptions

def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.DlgApplyConv")
    logger.debug("----ShowDlg()----------------------------------------------")
    unoObjs = Utils.UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgSimple(unoObjs, logger)
    dlg.showDlg()

class DlgSimple(XActionListener, unohelper.Base):
    """The dialog implementation."""

    def __init__(self, unoObjs, logger):
        self.unoObjs        = unoObjs
        self.logger         = logger
        self.msgbox         = MessageBox(unoObjs, self.logger)

    def showDlg(self):
        self.logger.debug("DlgSimple.showDlg BEGIN")
        dlgprov = self.unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.awt.DialogProvider", self.unoObjs.ctx )
        dlg = None
        try:
            dlg = dlgprov.createDialog(
                "vnd.sun.star.script:LingToolsBasic.DlgApplyConverter" + \
                "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not show dialog window.")
            return
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.txtConverterName    = Utils.getControl(dlg, "txtConvName")
            self.chkDirectionReverse = Utils.getControl(dlg, "chkReverse")
            self.txtSourceCol        = Utils.getControl(dlg, "txtSourceColumn")
            self.txtTargetCol        = Utils.getControl(dlg, "txtTargetColumn")
            btnSelect                = Utils.getControl(dlg, "btnSelect")
            btnConvert               = Utils.getControl(dlg, "btnConvert")
            btnCancel                = Utils.getControl(dlg, "btnCancel")
        except Exceptions.LogicError, exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        hamster = Exceptions.Hammy()
        print hamster
        self.logger.debug("Won't get here I bet.")

        ## Command buttons

        btnSelect.setActionCommand("SelectConverter")
        btnSelect.addActionListener(self)
        btnConvert.setActionCommand("Close_and_Convert")
        btnConvert.addActionListener(self)
        btnCancel.setActionCommand("Cancel")
        btnCancel.addActionListener(self)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()
        dlg.dispose()

    def actionPerformed(self, event):
        """Handle which button was pressed."""
        self.logger.debug("An action happened: " + event.ActionCommand)
        if event.ActionCommand == "SelectConverter":
            self.logger.debug("Pretending to select a converter...")
        elif event.ActionCommand == "Cancel":
            self.logger.debug("Action command was Cancel")
            self.dlgClose()
            return
        elif event.ActionCommand == "Close_and_Convert":
            self.logger.debug("Closing and Converting...")
            self.dlgClose()

#-------------------------------------------------------------------------------
# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = ShowDlg,
