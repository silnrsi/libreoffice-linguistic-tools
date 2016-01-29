# -*- coding: Latin-1 -*-
#
# This file created June 22 2015 by Jim Kornelsen
#
# 16-Dec-15 JDK  Fixed bug: pass proper arguments to OdtConverter.

"""
Does the following so that ODT files can be read and modified as XML:
- Save files such as .rtf and .doc into .odt format.
- Unzip .odt XML files into a (temporary) folder inside destination folder.
- Zip back into .odt
Actual reading and modifying of the XML is done in the odt_converter module.
"""

import logging
import os
import shutil
import uno
import zipfile
from com.sun.star.task import ErrorCodeIOException
from com.sun.star.util import CloseVetoException

from lingt.access.writer import doc_reader
from lingt.access.xml.odt_converter import OdtReader, OdtChanger
from lingt.app import exceptions
from lingt.utils import util

logger = logging.getLogger("lingt.access.DocToXml")

class DocToXml:

    SUPPORTED_FORMATS = [
        ('writerdoc', "Document (.odt .doc .docx .rtf) for Writer")]

    def __init__(self, unoObjs, msgbox, fileconfig, outdir, progressRange):
        self.unoObjs = unoObjs
        self.msgbox = msgbox
        self.fileconfig = fileconfig   # type fileitemlist.BulkFileItem
        self.outdir = outdir
        self.progressRange = progressRange
        self.progressRange_partNum = 0
        self.tempDir = ""
        self.tempBaseDir = ""
        self.odt_reader = None

    def read(self):
        """Read in the data.
        Returns list with elements of type FontItem.
        """
        logger.debug(util.funcName('begin'))
        try:
            self.make_temp_dir()
        except exceptions.FileAccessError as exc:
            self.msgbox.displayExc(exc)
            return list()
        data = None
        self.progressRange_partNum = 0
        try:
            data = self.readFile()
        except zipfile.BadZipFile as exc:
            logger.warn(exc)
            self.convert_to_odt()
            data = self.readFile()
        except exceptions.FileAccessError as exc:
            if exc.msg.startswith("Error reading file"):
                logger.warn(exc)
                self.convert_to_odt()
                data = self.readFile()
            else:
                raise exc
        #self.cleanup()
        logger.debug(util.funcName('end'))
        return data

    def make_temp_dir(self):
        """Make temporary directory to extract .odt file contents."""
        self.tempBaseDir = os.path.join(self.outdir, 'OOLT Converted Files')
        if not os.path.exists(self.tempBaseDir):
            try:
                os.makedirs(self.tempBaseDir)
            except OSError:
                raise exceptions.FileAccessError(
                    "Could not create temporary folder %s", self.tempBaseDir)
        MAX_FOLDERS = 1000
        for folderNum in range(1, MAX_FOLDERS):
            tempDirCandidate = os.path.join(self.tempBaseDir, "%03d" % folderNum)
            if not os.path.exists(tempDirCandidate):
                self.tempDir = tempDirCandidate
                break
        if not self.tempDir:
            raise exceptions.FileAccessError(
                "Too many temporary folders in %s.", self.tempBaseDir)
        try:
            os.mkdir(self.tempDir)
        except OSError:
            raise exceptions.FileAccessError(
                "Could not create temporary folder %s", self.tempDir)

    def incrementProgressPart(self):
        self.progressRange_partNum += 1
        self.progressRange.updatePart(self.progressRange_partNum)

    def readFile(self):
        with zipfile.ZipFile(self.fileconfig.filepath, 'r') as zipper:
            zipper.extractall(self.tempDir)
        self.incrementProgressPart()
        self.odt_reader = OdtReader(
            self.tempDir, self.unoObjs)
        return self.odt_reader.read()

    def convert_to_odt(self):
        """Opens a file such as .doc, saves as .odt and then closes it."""
        logger.debug(util.funcName('begin'))
        self.incrementProgressPart()
        basename = os.path.basename(self.fileconfig.filepath)
        name, dummy_ext = os.path.splitext(basename)
        newpath = os.path.join(self.tempBaseDir, name + "_converted.odt")
        if os.path.exists(newpath):
            logger.warn("File already exists: %s", newpath)
            self.fileconfig.filepath = newpath
            logger.debug(util.funcName('return'))
            return
        doc_loader = doc_reader.DocReader(self.fileconfig, self.unoObjs, 0)
        doc_loader.loadDoc(self.fileconfig.filepath)
        loaded_doc = doc_loader.doc
        uno_args = (
            #util.createProp("FilterName", "StarOffice XML (Writer)"),
            #util.createProp("FilterName", "writer8"),
            util.createProp("Overwrite", False),
        )
        logger.debug("Saving as %s", newpath)
        fileUrl = uno.systemPathToFileUrl(os.path.realpath(newpath))
        try:
            loaded_doc.document.storeAsURL(fileUrl, uno_args)
        except ErrorCodeIOException:
            raise exceptions.FileAccessError("Error saving %s", newpath)
        try:
            loaded_doc.document.close(True)
        except CloseVetoException:
            logger.warn("Could not close %s", newpath)
        self.fileconfig.filepath = newpath
        self.incrementProgressPart()
        logger.debug(util.funcName('end'))

    def makeChanges(self, fontChanges):
        logger.debug(util.funcName('begin'))
        if not self.odt_reader:
            logger.warn("No odt_reader.")
        changer = OdtChanger(self.odt_reader, fontChanges)
        numChanges = changer.makeChanges()

        ## Zip the XML files back into a single ODT file

        resultFilepath = ""
        MAX_TRIES = 1000
        for fileNum in range(1, MAX_TRIES):
            basename, extension = os.path.splitext(
                os.path.basename(self.fileconfig.filepath))
            filename = "%s_%03d%s" % (basename, fileNum, extension)
            resultCandidate = os.path.join(self.outdir, filename)
            if not os.path.exists(resultCandidate):
                resultFilepath = resultCandidate
                break
        if not resultFilepath:
            self.msgbox.display(
                "Too many files named like %s.", resultCandidate)
            return 0
        logger.debug("Writing to file %s", resultFilepath)
        zipper = zipfile.ZipFile(resultFilepath, 'w')
        for root, dummy_dirs, filenames in os.walk(self.tempDir):
            for filename in filenames:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, self.tempDir)
                zipper.write(abs_path, rel_path)
        zipper.close()
        logger.debug(util.funcName('end'))
        return numChanges

    def cleanup(self):
        try:
            if self.tempDir:
                shutil.rmtree(self.tempDir)
                #os.rmdir(self.tempDir)
        except OSError:
            logger.warn("Failed to delete %s", self.tempDir)

