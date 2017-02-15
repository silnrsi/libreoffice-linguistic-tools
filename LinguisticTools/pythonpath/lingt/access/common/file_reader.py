# -*- coding: Latin-1 -*-
#
# This file created Sept 14 2010 by Jim Kornelsen
#
# 24-Sep-10 JDK  Split up \or from Toolbox into columns.
# 28-Sep-10 JDK  Use a wrapper class to make getReader() more elegant.
# 05-Oct-10 JDK  Fixed bug: Strings are immutable in pass-by-reference.
# 07-Oct-10 JDK  If \tx has only one column, then don't split up \tor.
# 23-Oct-10 JDK  Fixed bugs: Made ref key consistent, gloss not tuple.
# 25-Oct-10 JDK  Report better information on file reading problems.
# 26-Oct-10 JDK  Fixed bug: return without arg returns None.
# 01-Jul-11 JDK  Handle PA experimental transcription field.
# 28-Oct-11 JDK  For LIFT format, get ref no. from Source field.
# 15-May-12 JDK  Fixed bug: Not all node types have a getAttribute() method.
# 23-Oct-12 JDK  Refactor into several files.
# 29-Oct-12 JDK  Make XML_Reader a more definite abstract class.
# 09-Nov-12 JDK  Generalize for other file types besides XML.
# 22-Jul-15 JDK  read() can close progressBar in finally clause.
# 22-Jun-16 JDK  Move logger to a module variable.

"""
Interface to read XML or other files.
"""
import logging

from lingt.app import exceptions
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.progressbar import ProgressBar
from lingt.utils import util

logger = logging.getLogger("lingt.access.file_reader")


class FileReader:
    """Abstract base class for XML file readers.
    The methods beginning with a single underscore are intended to only be
    called from the base class.
    """
    SUPPORTED_FORMATS = []  # list of tuples of name, text description

    def __init__(self, unoObjs):
        if self.__class__ is FileReader:
            # The base class should not be instantiated.
            raise NotImplementedError()
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.progressBar = ProgressBar(unoObjs, "Loading data...")
        self.data = None
        self.dom = None
        self.filepath = ""

    @classmethod
    def supportedNames(cls):
        names = [name for name, desc in cls.SUPPORTED_FORMATS]
        return names

    def read(self):
        logger.debug(util.funcName('begin'))
        if self.progressBar:
            self.progressBar.show()
            self.progressBar.updateBeginning()
            self.progressBar.updatePercent(20)
        self._initData()
        try:
            self._read()
            self._verifyDataFound()
            if self.progressBar:
                self.progressBar.updateFinishing()
        finally:
            if self.progressBar:
                self.progressBar.close()
        logger.debug(util.funcName('end'))
        return self.data

    def _initData(self):
        # All derived classes should implement this method.
        raise NotImplementedError()

    def _read(self):
        # All derived classes should implement this method.
        raise NotImplementedError()

    def _verifyDataFound(self):
        """Derived classes should override if they don't want this check to
        be performed.
        """
        if not self.data:
            raise exceptions.DataNotFoundError(
                "Did not find any data in file %s", self.filepath)

    def getSuggestions(self):
        """Get suggested ref numbers.  Intended for linguistic examples only,
        so derived classes are not required to override this method.
        """
        return []
