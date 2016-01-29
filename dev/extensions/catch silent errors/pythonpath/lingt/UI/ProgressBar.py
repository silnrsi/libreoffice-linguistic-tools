#!/usr/bin/python
# -*- coding: Latin-1 -*-

# ProgressBar.py
#              
# Change History:
#   Created Oct 23 2012 by Jim Kornelsen
#
#   07-Nov-12 JDK  Allow for the controller of a different document.
#   19-Nov-12 JDK  Added pause() method.

"""
Display a progress bar to the user.
"""
import time
from lingt.Utils        import Utils
from lingt.Utils.Locale import Locale

class ProgressBar:
    MAXVAL = 100
    def __init__(self, unoObjs, logger, title, doc=None):
        self.unoObjs    = unoObjs
        self.doc        = doc
        self.logger     = logger
        locale          = Locale(unoObjs)
        self.titleText  = locale.getText(title)
        self.progress   = None
        self.val        = 0   # needed because self.progress.Value is write-only

    def show(self):
        self.logger.debug("ProgressBar.show() BEGIN")
        if self.doc:
            self.progress = self.doc.controller.StatusIndicator
        else:
            self.progress = self.unoObjs.controller.StatusIndicator
        self.progress.start(self.titleText, self.MAXVAL)
        self.logger.debug("ProgressBar show() Finished")

    def updateBeginning(self):
        """Sets to 10% and waits a short time so the user can see it."""
        self.val = 10
        self.progress.setValue(self.val)
        self.pause()

    def updateFinishing(self):
        """Sets to 100%."""
        self.val = self.MAXVAL
        self.progress.setValue(self.val)
        self.pause()

    def pause(self):
        """Wait a short time so the user can see the bar."""
        time.sleep(0.1)

    def updatePercent(self, percent):
        """Set the percentage finished. Maximum value is 100."""
        self.logger.debug("ProgressBar updatePercent " + str(percent))
        self.val = percent
        self.progress.setValue(self.val)

    def percentMore(self, percent):
        """Increases progress bar by the amount specified."""
        self.logger.debug("ProgressBar percentMore")
        self.val += percent
        self.progress.setValue(self.val)

    def getPercent(self):
        return self.val

    def close(self):
        self.logger.debug("ProgressBar close")
        self.progress.end()

