# -*- coding: Latin-1 -*-
#
# This file created April 4, 2015 by Jim Kornelsen
#
# 29-Dec-15 JDK  Set and verify sec_call if none exists yet.
# 29-Dec-15 JDK  Use converter name as key instead of ConverterSettings.
# 20-Feb-16 JDK  Added FontItemList.
# 24-Jun-16 JDK  FontItemList holds FontItemGroup instead of FontItem.
# 01-Jul-16 JDK  Samples reads from FontItemGroup instead of FontItem.
# 15-Jul-16 JDK  Instead of fonts, use StyleItems that depend on scope type.

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

from lingt.access.sec_wrapper import ConverterSettings, SEC_wrapper
from lingt.access.writer import doc_to_xml
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import ScopeType
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.progressbar import ProgressBar, ProgressRange
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.app.dataconversion")


class BulkConversion:

    def __init__(self, docUnoObjs):
        """docUnoObjs needs to be for a writer doc"""
        self.unoObjs = docUnoObjs
        uservars.SettingsDocPreparer(
            uservars.Prefix.BULK_CONVERSION, self.unoObjs).prepare()
        self.userVars = uservars.UserVars(
            uservars.Prefix.BULK_CONVERSION, self.unoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)
        self.convPool = ConvPool(
            self.userVars, self.msgbox, self.get_all_conv_names)
        self.fileItems = None  # FileItemList of BulkFileItem
        self.styleItemList = StyleItemList(self.userVars)
        self.outdir = ""
        self.askEach = False
        self.scopeType = ScopeType.FONT_WITH_STYLE

    def scanFiles(self, fileItems, outdir, scopeType):
        """Sets self.styleItemList"""
        logger.debug(util.funcName('begin'))
        self.fileItems = fileItems
        self.outdir = outdir
        self.scopeType = scopeType
        progressBar = ProgressBar(self.unoObjs, "Reading files...")
        progressBar.show()
        progressBar.updateBeginning()
        progressRange = ProgressRange(
            ops=len(self.fileItems), pbar=progressBar)
        #progressRange.partSize = 10
        progressRange.partSize = 4
        unique_styles = UniqueStyles(self.scopeType)
        for fileItemIndex, fileItem in enumerate(self.fileItems):
            fileItem.fileEditor = doc_to_xml.DocToXml(
                self.unoObjs, self.msgbox, fileItem, self.outdir,
                self.scopeType, progressRange)
            processingStylesFound = fileItem.fileEditor.read()
            logger.debug("found %d styles", len(processingStylesFound))
            unique_styles.add(processingStylesFound)
            progressRange.update(fileItemIndex)
        self.styleItemList.set_items(unique_styles)
        progressBar.updateFinishing()
        progressBar.close()
        logger.debug(util.funcName('end', args=len(self.styleItemList.items)))

    def update_list(self, event_handler):
        """Update self.styleItemList based on the event that occurred."""
        item_to_update = self.styleItemList.selected_item()
        self.styleItemList.update_item(item_to_update, event_handler)

    def doConversions(self):
        logger.debug(util.funcName('begin'))
        progressBar = ProgressBar(self.unoObjs, "Converting...")
        progressBar.show()
        progressBar.updateBeginning()
        self.convert_vals()
        progressBar.updatePercent(25)

        totalChanges = 0
        totalFilesChanged = 0
        #logger.debug(
        #   repr([repr(change) for change in self.getStyleChanges()]))
        logger.debug(
            repr([change.converter.convName
                  for change in self.getStyleChanges()]))
        for fileItem in self.fileItems:
            numChanges = fileItem.fileEditor.makeChanges(
                self.getStyleChanges())
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
        Modifies self.styleItemList by setting StyleChange.converted_data.
        """
        unique_converter_settings = set(
            [styleChange.converter for styleChange in self.getStyleChanges()
             if styleChange.converter.convName])
        converter_styleItems = collections.defaultdict(list)
        for styleChange in self.getStyleChanges():
            converter_styleItems[styleChange.converter].append(
                styleChange.styleItem)

        for converter_settings in unique_converter_settings:
            sec_call = self.convPool.loadConverter(
                converter_settings)
            if not sec_call:
                continue
            self.convPool.cleanup_unused()
            for styleItem in converter_styleItems[converter_settings]:
                styleChange = styleItem.change
                for inputText in styleItem.inputData:
                    if inputText not in styleChange.converted_data:
                        converted_val = sec_call.convert(inputText)
                        styleChange.converted_data[inputText] = converted_val

    def getStyleChanges(self):
        """Returns a list of all non-empty StyleChange objects for the list
        of found StyleItem.
        """
        return [item.change for item in self.styleItemList
                if item.change]

    def get_all_conv_names(self):
        """Returns all currently used converter names."""
        return set([
            styleChange.converter.convName
            for styleChange in self.getStyleChanges()
            if styleChange.converter.convName])

    def selected_item(self):
        return self.styleItemList.selected_item()


class UniqueStyles:
    """Gets StyleItems from ProcessingStyleItems.
    Merges inputData of style items.
    """
    def __init__(self, scopeType):
        self.uniqueStyles = dict()  # key and value are both type StyleItem
        self.scopeType = scopeType

    def add(self, processingStyleItems):
        for processingStyleItem in processingStyleItems:
            styleItem = processingStyleItem.getStyleItem(self.scopeType)
            if styleItem in self.uniqueStyles:
                styleItem.inputData.extend(
                    self.uniqueStyles[styleItem].inputData)
            self.uniqueStyles[styleItem] = styleItem

    def get_values(self):
        return [
            styleItem for styleItem in self.uniqueStyles.values()
            if styleItem.inputData]


class StyleItemList:
    """Manage a list of StyleItem objects."""
    def __init__(self, userVars):
        self.userVars = userVars
        self.items = []  # elements are type StyleItem
        self.selected_index = -1  # selected StyleItem

    def set_items(self, unique_styles):
        """:param unique_styles: type UniqueStyles"""
        self.items = sorted(unique_styles.get_values())

    def update_item(self, item, event_handler):
        """When controls get changed, update StyleItem object.
        :param item: type StyleItem
        :param event_handler: type StyleChangeControlHandler
        """
        logger.debug(util.funcName('begin', args=type(event_handler).__name__))
        item.create_change(self.userVars)
        event_handler.update_change(item.change)

    def selected_item(self):
        if self.selected_index == -1:
            return None
        return self[self.selected_index]

    def __getitem__(self, index):
        """For random access."""
        return self.items[index]

    def __iter__(self):
        """We override __iter__ here for better performance than
        __getitem__.
        """
        return list.__iter__(self.items)

    def __len__(self):
        return len(self.items)


class Samples:
    """Display samples of input data."""

    NO_DATA = theLocale.getText("(No data)")

    def __init__(self, convPool):
        self.convPool = convPool
        self.inputData = []  # from currently selected StyleItem
        self.sampleIndex = -1  # index of self.inputData
        self.last_settings = {}  # keys conv name, values ConverterSettings
        self.conv_settings = ConverterSettings(None)
        self.converted_data = Samples.NO_DATA

    def set_styleItem(self, styleItem):
        """Use values from a StyleItem."""
        self.sampleIndex = -1
        self.inputData = styleItem.inputData
        self.conv_settings = ConverterSettings(None)
        if styleItem.change:
            self.conv_settings = styleItem.change.converter
        self.converted_data = ""

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
        self.converted_data = Samples.NO_DATA
        if not self.conv_settings.convName:
            logger.debug("No converter.")
            return self.converted_data
        convName = self.conv_settings.convName
        logger.debug("Using converter %r", self.conv_settings)
        sec_call = self.convPool.loadConverter(self.conv_settings)
        logger.debug("Got converter %r", sec_call.config)
        if convName in self.last_settings:
            if self.last_settings[convName] != sec_call.config:
                sec_call.setConverter()
                self.last_settings[convName] = sec_call.config
        self.converted_data = sec_call.convert(
            self.inputData[self.sampleIndex])
        logger.debug("Got converted data.")
        return self.converted_data


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
        """Returns ConverterSettings, or None if cancelled."""
        logger.debug(util.funcName('begin'))
        if key in self:
            secCall = self[key]
        else:
            secCall = SEC_wrapper(self.msgbox, self.userVars)
        try:
            secCall.pickConverter()
        except exceptions.FileAccessError as exc:
            self.msgbox.displayExc(exc)
        conv_settings = secCall.config
        if not conv_settings.convName:
            return None
        logger.debug("Picked converter.")
        self[conv_settings.convName] = secCall
        logger.debug("Converter name '%s'", conv_settings.convName)
        return conv_settings

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
                msg = (
                    "%s:\n%s  "
                    "Please select the converter again." % (
                        conv_settings, exc.msg))
                raise exceptions.ChoiceProblem(msg, *exc.msg_args)
                #self.msgbox.displayExc(exc)
                #raise exceptions.ChoiceProblem(
                #    "Please select the converter again.")
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
