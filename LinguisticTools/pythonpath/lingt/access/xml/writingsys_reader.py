"""
Read XML files describing writing systems.
"""
import logging
import os
import re
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.utils import util

logger = logging.getLogger("lingt.access.writingsys_reader")

class WritingSystem:
    """Information about a writing system."""
    def __init__(self):
        self.name = ""
        self.internalCode = ""


class WritingSysReader(FileReader):
    def __init__(self, filepath, unoObjs):
        FileReader.__init__(self, unoObjs)
        self.filepath = filepath

    def _initData(self):
        # list of WritingSystem objects
        self.data = []

    def read(self):
        self._initData()
        self._read()
        return self.data

    def _read(self):
        filefolder = os.path.dirname(self.filepath)
        filelist = os.listdir(filefolder)
        for filename in filelist:
            self._getWritingSystemFromFile(filefolder, filename)
        subdir = os.path.join(filefolder, "WritingSystems")
        if os.path.exists(subdir):
            filelist = os.listdir(subdir)
            for filename in filelist:
                self._getWritingSystemFromFile(subdir, filename)

    def _getWritingSystemFromFile(self, folder, filename):
        """Read an .ldml LIFT file.  Add its info to self.data."""
        logger.debug(util.funcName('begin'))
        ws = WritingSystem()

        ## Get the internal code from the filename

        m = re.match(r"(.+)\.ldml$", filename)
        if not m:
            # Ignore this file
            return
        #ws.internalCode = m.group(1)    # doesn't work for LIFT format???

        ## Parse the XML to get writing system information

        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", filepath)
            return
        try:
            self.dom = xml.dom.minidom.parse(filepath)
        except xml.parsers.expat.ExpatError as exc:
            self.msgbox.display(
                "Error reading file %s\n\n%s", filepath, str(exc).capitalize())
            return

        ## Get the code (seems to be different from FW Internal Code)

        elems = self.dom.getElementsByTagName("identity")
        if elems:
            elem = elems[0]
            languages = elem.getElementsByTagName("language")
            if languages:
                language = languages[0]
                if language.attributes:
                    ws.internalCode = language.getAttribute("type")
            variants = elem.getElementsByTagName("variant")
            if variants:
                variant = variants[0]
                if variant.attributes:
                    variantVal = variant.getAttribute("type")
                    ws.internalCode += "-x-" + variantVal

        ## Get the language name

        elems = self.dom.getElementsByTagName("palaso:languageName")
        if elems:
            elem = elems[0]
            if elem.attributes:
                ws.name = elem.getAttribute("value")

        ## Add results to the list

        if ws.internalCode:
            if not ws.name:
                ws.name = ws.internalCode
            self.data.append(ws)
            logger.debug("Got %s, %s", ws.name, ws.internalCode)
