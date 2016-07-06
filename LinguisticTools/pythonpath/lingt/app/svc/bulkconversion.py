# -*- coding: Latin-1 -*-
#
# This file created April 4, 2015 by Jim Kornelsen
#
# 29-Dec-15 JDK  Set and verify sec_call if none exists yet.
# 29-Dec-15 JDK  Use converter name as key instead of ConverterSettings.
# 20-Feb-16 JDK  Added FontItemList.
# 24-Jun-16 JDK  FontItemList holds FontItemGroup instead of FontItem.
# 01-Jul-16 JDK  Samples reads from FontItemGroup instead of FontItem.

"""
Bulk Conversion will create multiple SEC call objects,
unlike Data Conversion which creates only one object.

This module exports:
    BulkConversion
    Samples
    ConvPool
"""
import collections
import copy
import logging
from operator import attrgetter

from lingt.access.sec_wrapper import ConverterSettings, SEC_wrapper
from lingt.access.writer import doc_to_xml
from lingt.access.writer import uservars
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import FontItemGroup
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.progressbar import ProgressBar, ProgressRange
from lingt.utils import util
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.app.dataconversion")


class BulkConversion:

    def __init__(self, docUnoObjs):
        """
        unoObjs needs to be for a writer doc
        """
        self.unoObjs = docUnoObjs
        uservars.SettingsDocPreparer(
            uservars.Prefix.BULK_CONVERSION, self.unoObjs).prepare()
        self.userVars = uservars.UserVars(
            uservars.Prefix.BULK_CONVERSION, self.unoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)
        self.convPool = ConvPool(
            self.userVars, self.msgbox, self.get_all_conv_names)
        self.fileItems = None  # FileItemList of BulkFileItem
        self.fontItemList = FontItemList(self.userVars)
        self.outdir = ""
        self.askEach = False

    def scanFiles(self, fileItems, outdir):
        """Sets self.fontItemList"""
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
        self.fontItemList.set_items(uniqueFontsFound.values())
        progressBar.updateFinishing()
        progressBar.close()
        logger.debug(util.funcName('end', args=len(self.fontItemList.groups)))

    def update_list(self, event_handler):
        """Update self.fontItemList based on the event that occurred."""
        group_to_update = self.fontItemList.selected_group()
        self.fontItemList.update_group(group_to_update, event_handler)

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
        Modifies self.fontItemList by setting FontChange.converted_data.
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
            if not sec_call:
                continue
            self.convPool.cleanup_unused()
            for fontItem in converter_fontItems[converter_settings]:
                fontChange = fontItem.change
                for inputText in fontItem.inputData:
                    if inputText not in fontChange.converted_data:
                        converted_val = sec_call.convert(inputText)
                        fontChange.converted_data[inputText] = converted_val

    def getFontChanges(self):
        """Returns a list of all non-empty FontChange objects for the list
        of found FontItem.
        """
        return [item.change for item in self.fontItemList.all_items()
                if item.change]

    def get_all_conv_names(self):
        """Returns all currently used converter names."""
        return set([
            fontChange.converter.convName
            for fontChange in self.getFontChanges()
            if fontChange.converter.convName])

    def selected_group(self):
        return self.fontItemList.selected_group()


class FontItemList:
    """Manage a list of FontItemGroup objects.  Optionally group similar
    items.
    """
    def __init__(self, userVars):
        self.userVars = userVars
        self.groups = []  # elements are type FontItemGroup
        self.groupSizes = True
        self.groupStyles = True
        self.groupFontTypes = True
        self.selected_index = -1  # selected FontItemGroup

    def set_items(self, allFontItems):
        """Groups items according to member flags.  Sets self.groups.
        Merge data, sorting data by fontItem.inputDataOrder.
        :param allFontItems: ungrouped list of FontItem objects
        """
        similar_items = {}  # key FontItem, value list of similar FontItem
        for item in allFontItems:
            for similar_item in similar_items:
                if self.is_item_similar(item, similar_item):
                    similar_items[similar_item].append(item)
                    break
            else:
                similar_items[item] = [item]
        for fontItems in similar_items.values():
            fontItems.sort(key=attrgetter('inputDataOrder'))
            group = FontItemGroup(fontItems)
            self.groups.append(group)
        self.groups.sort()

    def regroup_items(self):
        """This is useful if the grouping flags change."""
        self.set_items(self.all_items())

    def is_item_similar(self, item, item2):
        """Use member flags to test whether items are basically equal.
        Make a fuzzy item that conditionally has differences removed.
        See also FontItem.attrs() -- any attrs except 'name' can be ignored.
        """
        fuzzy_item = copy.deepcopy(item2)
        attrs_to_ignore = []
        if self.groupFontTypes:
            attrs_to_ignore.extend(
                ['fontType', 'nameStandard', 'nameComplex', 'nameAsian'])
        if self.groupStyles:
            attrs_to_ignore.extend(['styleName', 'styleType'])
        if self.groupSizes:
            attrs_to_ignore.append('size')
        for attr in attrs_to_ignore:
            setattr(fuzzy_item, attr, getattr(item, attr))
        return item == fuzzy_item

    def update_group(self, group_to_update, event_handler):
        """When controls get changed,
        update all FontItem objects in the selected group.

        :param group_to_update: type FontItemGroup
        :param changed_values: type FontChange
        :param attrs_changed: list of FontChange attribute names
        """
        logger.debug(util.funcName('begin', args=type(event_handler).__name__))
        for item in group_to_update.items:
            item.create_change(self.userVars)
            event_handler.update_change(item.change)

    def selected_group(self):
        if self.selected_index == -1:
            return None
        return self[self.selected_index]

    def all_items(self):
        """Generator function to return all items in the list."""
        for group in self.groups:
            for item in group.items:
                yield item

    def __getitem__(self, index):
        """For random access."""
        return self.groups[index]

    def __iter__(self):
        """We override __iter__ here for better performance than
        __getitem__.
        """
        return list.__iter__(self.groups)


class Samples:
    """Display samples of input data."""

    NO_DATA = theLocale.getText("(No data)")

    def __init__(self, convPool):
        self.convPool = convPool
        self.inputData = []  # from currently selected FontItem
        self.sampleIndex = -1  # index of self.inputData
        self.last_settings = {}  # keys conv name, values ConverterSettings
        self.conv_settings = ConverterSettings(None)
        self.converted_data = Samples.NO_DATA

    def set_fontItemGroup(self, fontItemGroup):
        """Use values from a FontItem."""
        self.sampleIndex = -1
        self.inputData = fontItemGroup.effective_item.inputData
        self.conv_settings = fontItemGroup.changeattr('converter')
        if fontItemGroup.changeattr_varies('converter'):
            # If two items have different converters, then don't perform
            # any conversion -- leave converted text blank.
            self.converted_data = FontItemGroup.VARIOUS

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

