# -*- coding: Latin-1 -*-
#
# This file created Oct 23 2012 by Jim Kornelsen
#
# 07-Nov-12 JDK  Allow for the controller of a different document.
# 19-Nov-12 JDK  Added pause() method.
# 19-Dec-12 JDK  Just pass controller along with document as main arg.
# 24-Jul-15 JDK  Added ProgressRange class.  Removed percentMore().
# 25-Aug-15 JDK  Fixed bug: Keyword is always pbar rather than bar.

"""
Display a progress bar to the user.

This module exports:
    ProgressBar
    ProgressRange
    ProgressRanges
"""
import logging
import time

from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.progressbar")


def snooze():
    """Wait a short time so the user can see the bar."""
    time.sleep(0.1)


class ProgressBar:
    MAXVAL = 100
    def __init__(self, genericUnoObjs, title):
        self.unoObjs = genericUnoObjs
        theLocale.loadUnoObjs(genericUnoObjs)
        self.titleText = theLocale.getText(title)
        self.progress = None
        self.val = 0   # needed because self.progress.Value is write-only

    def show(self):
        logger.debug(util.funcName('begin'))
        self.progress = self.unoObjs.controller.StatusIndicator
        self.progress.start(self.titleText, self.MAXVAL)
        logger.debug("ProgressBar show() Finished")

    def updateBeginning(self):
        """Sets to 10% and waits a short time so the user can see it."""
        self.val = 10
        self.progress.setValue(self.val)
        snooze()

    def updateFinishing(self):
        """Sets to 100%."""
        self.val = self.MAXVAL
        self.progress.setValue(self.val)
        snooze()

    def updatePercent(self, percent):
        """Set the percentage finished.  Maximum value is 100."""
        logger.debug("ProgressBar updatePercent %d", percent)
        self.val = percent
        self.progress.setValue(self.val)

    def getPercent(self):
        return self.val

    def close(self):
        """
        This method will throw an exception if show() has not been called.
        """
        logger.debug("ProgressBar close")
        self.progress.end()


class ProgressRange:
    """
    Calculates a range of percentages for a progress bar.

    The basic calculation is the current operation number divided by the total
    number of operations.
    For example, an operation number may be the index of an enumerated for
    loop, and the total number is the length of the for loop iterator.
    """
    def __init__(self, start=20, stop=90, ops=4, pbar=None):
        self.startPercent = start
        self.stopPercent = stop
        self.totalOperations = ops
        self.progressBar = pbar
        self.prevPct = 0
        # Split up each operation into several smaller parts.
        self.partSize = 4

    def update(self, opNum):
        """
        The main method of this class.
        Param should be in range(0, self.totalOperations).
        """
        if opNum <= 0:
            opNum = 0
        elif opNum >= self.totalOperations:
            opNum = self.totalOperations - 1
        pct = self.startPercent + int(opNum * self.percentEach())
        self.updatePercent(pct)

    def updateStart(self):
        self.updatePercent(self.startPercent)

    def updateStop(self):
        self.updatePercent(self.stopPercent)

    def updatePart(self, partNum):
        """Increment a smaller amount than percentEach().
        Caller should set self.partSize before using this method.
        """
        percentEachPart = self.percentEach() // self.partSize
        self.updatePercent(self.prevPct + percentEachPart * partNum)

    def percentEach(self):
        rangePct = self.stopPercent - self.startPercent
        return float(rangePct) / self.totalOperations

    def updatePercent(self, pct):
        if pct == self.prevPct:
            # No reason to update.  Increment was probably too small to notice.
            return
        self.prevPct = pct
        self.progressBar.updatePercent(pct)


class ProgressRanges:
    """
    Multiple synchronized ProgressRange objects.
    This is useful for operations that span multiple Office windows,
    for example one Calc window and one Writer window.
    """
    def __init__(self, progressBars):
        self.bars = progressBars
        self.ranges = []

    def initRanges(self, *args, **kwargs):
        for progressBar in self.bars:
            kwargs['pbar'] = progressBar
            newRange = ProgressRange(*args, **kwargs)
            self.ranges.append(newRange)

    def update(self, *args, **kwargs):
        self._invokeRangeMethod('update', *args, **kwargs)

    def updatePart(self, *args, **kwargs):
        self._invokeRangeMethod('updatePart', *args, **kwargs)

    def updateStart(self):
        self._invokeRangeMethod('updateStart')

    def updateStop(self):
        self._invokeRangeMethod('updateStop')

    def updateFinishing(self):
        self._invokeBarMethod('updateFinishing')

    def closeBars(self):
        self._invokeBarMethod('close')

    def _invokeRangeMethod(self, methodName, *args, **kwargs):
        """Calls the specified ProgressRange method."""
        for progressRange in self.ranges:
            meth = getattr(progressRange, methodName)
            meth(*args, **kwargs)

    def _invokeBarMethod(self, methodName, *args, **kwargs):
        """Calls the specified ProgressBar method."""
        for progressBar in self.bars:
            meth = getattr(progressBar, methodName)
            meth(*args, **kwargs)
