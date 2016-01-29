# -*- coding: Latin-1 -*-
#
# This file created April 4, 2015 by Jim Kornelsen
#
# 29-Dec-15 JDK  Set and verify sec_call if none exists yet.
# 29-Dec-15 JDK  Use converter name as key instead of ConverterSettings.

"""
Bulk Conversion will create multiple SEC call objects,
unlike Data Conversion which creates only one object.

This module exports:
    BulkConversion
    Samples
    ConvPool
"""
import collections
import logging

from lingt.access.sec_wrapper import SEC_wrapper
from lingt.access.writer import doc_to_xml
from lingt.app import exceptions
from lingt.app.bulkconv_structs import FontChange
from lingt.ui.messagebox import MessageBox
from lingt.ui.progressbar import ProgressBar, ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.app.dataconversion")


class BulkConversion:

    def __init__(self, docUnoObjs, userVars):
        """
        unoObjs needs to be for a writer doc
        """
        self.unoObjs = docUnoObjs
        self.userVars = userVars
        self.msgbox = MessageBox(self.unoObjs)
        self.convPool = ConvPool(
            self.userVars, self.msgbox, self.get_all_conv_names)
        self.fileItems = []  # FileItemList of BulkFileItem
        self.fontsFound = []  # List of FontItem found in document.
        self.outdir = ""
        self.askEach = False

    def scanFiles(self, fileItems, outdir):
        """Sets self.fontsFound"""
        logger.debug(util.funcName('begin'))
        self.fileItems = fileItems
        self.outdir = outdir
        progressBar = ProgressBar(self.unoObjs, "Reading files...")
        progressBar.show()
        progressBar.updateBeginning()
        progressRange = ProgressRange(
            ops=len(self.fileItems), pbar=progressBar)
        #progressRange.partSize = 10
        progressRange.partSize = 4
        uniqueFontsFound = dict()
        for fileItemIndex, fileItem in enumerate(self.fileItems):
            fileItem.fileEditor = doc_to_xml.DocToXml(
                self.unoObjs, self.msgbox, fileItem, self.outdir,
                progressRange)
            fontsFound = fileItem.fileEditor.read()
            logger.debug("found %d fonts", len(fontsFound))
            for fontItem in fontsFound:
                if fontItem in uniqueFontsFound:
                    fontItem.inputData.extend(
                        uniqueFontsFound[fontItem].inputData)
                uniqueFontsFound[fontItem] = fontItem
            progressRange.update(fileItemIndex)
        self.fontsFound = sorted(uniqueFontsFound.values())
        progressBar.updateFinishing()
        progressBar.close()
        logger.debug(util.funcName('end', args=len(self.fontsFound)))

    def doConversions(self):
        logger.debug(util.funcName('begin'))
        progressBar = ProgressBar(self.unoObjs, "Converting...")
        progressBar.show()
        progressBar.updateBeginning()
        self.convert_vals()
        progressBar.updatePercent(25)

        totalChanges = 0
        totalFilesChanged = 0
        for fileItem in self.fileItems:
            numChanges = fileItem.fileEditor.makeChanges(
                self.getFontChanges())
            if numChanges > 0:
                totalChanges += numChanges
                totalFilesChanged += 1

        if progressBar.getPercent() < 40:
            progressBar.updatePercent(40)

        progressBar.updateFinishing()
        progressBar.close()

        ## Display results

        if totalChanges == 0:
            self.msgbox.display("No changes.")
        else:
            # add "s" if plural
            plural = "" if totalChanges == 1 else "s"
            pluralFiles = "" if totalFilesChanged == 1 else "s"
            self.msgbox.display(
                "Made %d change%s to %d file%s.",
                totalChanges, plural, totalFilesChanged, pluralFiles)

    def convert_vals(self):
        """Performs whatever encoding conversion needs to be done.
        Modifies self.fontsFound by setting FontChange.converted_data.
        """
        unique_converter_settings = set(
            [fontChange.converter for fontChange in self.getFontChanges()
             if fontChange.converter.convName])
        converter_fontItems = collections.defaultdict(list)
        for fontChange in self.getFontChanges():
            converter_fontItems[fontChange.converter].append(
                fontChange.fontItem)

        for converter_settings in unique_converter_settings:
            sec_call = self.convPool.loadConverter(
                converter_settings)
            self.convPool.cleanup_unused()
            for fontItem in converter_fontItems[converter_settings]:
                fontChange = fontItem.fontChange
                for inputText in fontItem.inputData:
                    if inputText not in fontChange.converted_data:
                        converted_val = sec_call.convert(inputText)
                        fontChange.converted_data[inputText] = converted_val

    def getFontChanges(self):
        """Returns a list of all non-empty FontChange objects for the list
        of found FontItem.
        """
        return [
            fontItem.fontChange for fontItem in self.fontsFound
            if fontItem.fontChange]

    def get_all_conv_names(self):
        """Returns all currently used converter names."""
        return set([
            fontChange.converter.convName
            for fontChange in self.getFontChanges()
            if fontChange.converter.convName])


class Samples:
    """Display samples of input data."""

    def __init__(self, convPool):
        self.convPool = convPool
        self.inputData = []  # from currently selected FontItem
        self.sampleIndex = -1  # index of self.inputData
        self.last_settings = {}  # keys conv name, values ConverterSettings
        self.conv_settings = None

    def set_fontItem(self, fontItem):
        """Use values from a FontItem."""
        self.sampleIndex = -1
        self.inputData = fontItem.inputData
        self.conv_settings = None
        if fontItem.fontChange:
            self.conv_settings = fontItem.fontChange.converter

    def has_more(self):
        """Returns True if there are more samples."""
        return len(self.inputData) - self.sampleIndex - 1 > 0

    def gotoNext(self):
        self.sampleIndex += 1
        return self.inputData[self.sampleIndex]

    def sampleNum(self):
        """1-based sample number."""
        return self.sampleIndex + 1

    def get_converted(self):
        """Convert input sample.  Return converted string."""
        if not self.conv_settings or not self.conv_settings.convName:
            return "(None)"
        convName = self.conv_settings.convName
        logger.debug("Using converter %r", self.conv_settings)
        sec_call = self.convPool.loadConverter(self.conv_settings)
        logger.debug("Got converter %r", sec_call.config)
        if convName in self.last_settings:
            if self.last_settings[convName] != sec_call.config:
                sec_call.setConverter()
                self.last_settings[convName] = sec_call.config
        convertedVal = sec_call.convert(
            self.inputData[self.sampleIndex])
        return convertedVal


class ConvPool:
    """Dictionary-like class to hold converters.

    Keys are converter name.
    Would be nice to have keys of type sec_wrapper.ConverterSettings,
    but the ECDriver only holds one settings value for each name.

    Values are of type sec_wrapper.SEC_Wrapper.
    """

    def __init__(self, userVars, msgbox, get_all_conv_names=None):
        self.userVars = userVars
        self.msgbox = msgbox
        self.get_all_conv_names = get_all_conv_names  # method
        self._secCallObjs = dict()  # the main dict for this class

    def selectConverter(self, key):
        """Returns a FontChange with EncConverter fields set, or None if
        cancelled.
        """
        logger.debug(util.funcName('begin'))
        if key in self:
            secCall = self[key]
        else:
            secCall = SEC_wrapper(self.msgbox, self.userVars)
        try:
            secCall.pickConverter()
        except exceptions.FileAccessError as exc:
            self.msgbox.displayExc(exc)
        if not secCall.config.convName:
            return None
        logger.debug("Picked converter.")
        self[secCall.config.convName] = secCall
        fontChange = FontChange(None, self.userVars)
        fontChange.converter = secCall.config
        logger.debug("Converter name '%s'", fontChange.converter.convName)
        return fontChange

    def loadConverter(self, conv_settings):
        """Call this method before calling one of the doConversion() methods.
        Returns the SEC_wrapper object.
        """
        logger.debug(util.funcName('begin'))

        ## Get the converter if not yet done

        key = conv_settings.convName
        if key == "":
            raise exceptions.ChoiceProblem("Please select a converter.")
        if key == "<No converter>":
            return
        if key in self:
            secCall = self[key]
        else:
            secCall = SEC_wrapper(self.msgbox, self.userVars)
        if secCall.config != conv_settings:
            try:
                secCall.setConverter(conv_settings)
                logger.debug("Did set converter.")
            except exceptions.FileAccessError as exc:
                self.msgbox.displayExc(exc)
                raise exceptions.ChoiceProblem(
                    "Please select the converter again.")
        self[key] = secCall
        logger.debug(util.funcName('end'))
        return secCall

    def cleanup_unused(self):
        """Remove unused calls from pool.
        :param all_conv_settings: iterable of all used ConverterSettings
        """
        if self.get_all_conv_names is None:
            # Do not perform any cleanup.
            return
        convNames = self.get_all_conv_names()
        for key in list(self._secCallObjs):
            if key not in convNames:
                del self._secCallObjs[key]

    def __contains__(self, key):
        return key in self._secCallObjs

    def __getitem__(self, key):
        return self._secCallObjs[key]

    def __setitem__(self, key, newObj):
        newKey = newObj.config.convName
        self._secCallObjs[newKey] = newObj

    def __delitem__(self, key):
        del self._secCallObjs[key]

    def __iter__(self):
        return iter(self._secCallObjs)

    def __len__(self):
        return len(self._secCallObjs)

