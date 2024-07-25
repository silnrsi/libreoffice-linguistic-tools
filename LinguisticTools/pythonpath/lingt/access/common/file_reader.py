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
        self.data = None  # typically a list or dict
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
