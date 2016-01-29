# -*- coding: Latin-1 -*-
#
# This file created June 22 2015 by Jim Kornelsen
#
# 16-Dec-15 JDK  Fixed bug: specify absolute path to xml files.
# 17-Dec-15 JDK  Implemented readContentFile with limited functionality.
# 22-Dec-15 JDK  Read a list of text nodes.
# 23-Dec-15 JDK  Added changeContentFile().
# 24-Dec-15 JDK  Added class OdtChanger.

"""
Read and change an ODT file in XML format.
Call SEC_wrapper to do engine-based conversion.

This module exports:
    OdtReader
    OdtChanger
"""

import io
import os
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.file_reader import FileReader
from lingt.access.xml import xmlutil
from lingt.app import exceptions
from lingt.app.bulkconv_structs import FontItem
from lingt.utils import util


class OdtReader(FileReader):

    SUPPORTED_FORMATS = [("xml", "Unzipped Open Document Format (.odt)"),]

    def __init__(self, srcdir, unoObjs):
        FileReader.__init__(self, unoObjs)
        self.srcdir = srcdir
        self.defaultFont = ""
        self.stylesDom = None
        self.contentDom = None
        self.stylesDict = {}  # keys style name, value font name

    def _initData(self):
        """Elements are of type bulkconv_structs.FontItem."""
        self.data = []

    def _verifyDataFound(self):
        if not self.data:
            raise exceptions.DataNotFoundError(
                "Did not find any fonts in folder %s", self.srcdir)

    def _read(self):
        self.stylesDom = self.loadFile(
            os.path.join(self.srcdir, 'styles.xml'))
        self.progressBar.updatePercent(30)
        self.readStylesFile(self.stylesDom)
        self.progressBar.updatePercent(35)

        self.contentDom = self.loadFile(
            os.path.join(self.srcdir, 'content.xml'))
        self.progressBar.updatePercent(45)
        self.readContentFile(self.contentDom)
        self.progressBar.updatePercent(50)

    def loadFile(self, filepath):
        """Returns dom, raises exceptions.FileAccessError."""
        self.logger.debug(util.funcName('begin', args=filepath))
        if not os.path.exists(filepath):
            raise exceptions.FileAccessError(
                "Cannot find file %s", filepath)
        dom = None
        try:
            dom = xml.dom.minidom.parse(filepath)
        except xml.parsers.expat.ExpatError as exc:
            raise exceptions.FileAccessError(
                "Error reading file %s\n\n%s",
                filepath, str(exc).capitalize())
        if dom is None:
            raise exceptions.FileAccessError(
                "Error reading file %s", filepath)
        self.logger.debug(util.funcName('end'))
        return dom

    def readStylesFile(self, dom):
        """Read in styles.xml."""
        self.logger.debug(util.funcName('begin'))
        styles = dom.getElementsByTagName("style:default-style")
        for style in styles:
            styleFamily = style.getAttribute("style:family")
            if styleFamily == "paragraph":
                textprops = style.getElementsByTagName("style:text-properties")
                for textprop in textprops:
                    fontName = textprop.getAttribute("style:font-name")
                    if fontName:
                        #self.logger.debug("default font %s", fontName)
                        self.defaultFont = fontName
        styles = dom.getElementsByTagName("style:style")
        for style in styles:
            xmlStyleName = style.getAttribute("style:name")
            parentStyleName = style.getAttribute("style:parent-style-name")
            if parentStyleName in self.stylesDict:
                #self.logger.debug(
                #    "self.stylesDict[%s] = %r", xmlStyleName,
                #    self.stylesDict[parentStyleName])
                self.stylesDict[xmlStyleName] = self.stylesDict[
                    parentStyleName]
            #self.logger.debug("searching descendents of %s", xmlStyleName)
            textprops = style.getElementsByTagName("style:text-properties")
            for textprop in textprops:
                fontName = textprop.getAttribute("style:font-name")
                if fontName:
                    #self.logger.debug("%r font %r", xmlStyleName, fontName)
                    self.stylesDict[xmlStyleName] = fontName
        self.logger.debug(util.funcName('end'))

    def readContentFile(self, dom):
        """Read in content.xml."""
        self.logger.debug(util.funcName('begin'))
        styles = dom.getElementsByTagName("style:style")
        for style in styles:
            xmlStyleName = style.getAttribute("style:name")
            #self.logger.debug("searching descendents of %s", xmlStyleName)
            textprops = style.getElementsByTagName("style:text-properties")
            for textprop in textprops:
                fontName = textprop.getAttribute("style:font-name")
                if fontName:
                    #self.logger.debug("%r font %r", xmlStyleName, fontName)
                    self.stylesDict[xmlStyleName] = fontName
        paragraphs = dom.getElementsByTagName("text:p")
        for paragraph in paragraphs:
            xmlStyleName = paragraph.getAttribute("text:style-name")
            #self.logger.debug("para style name %s", xmlStyleName)
            paraFontName = self.stylesDict.get(xmlStyleName, self.defaultFont)
            para_texts = xmlutil.getElemTextList(paragraph)
            self.add_data_for_font(paraFontName, para_texts, xmlStyleName)
            spans = paragraph.getElementsByTagName("text:span")
            for span in spans:
                xmlStyleName = span.getAttribute("text:style-name")
                #self.logger.debug("span style name %s", xmlStyleName)
                spanFontName = self.stylesDict.get(xmlStyleName, paraFontName)
                span_texts = xmlutil.getElemTextList(span)
                self.add_data_for_font(spanFontName, span_texts, xmlStyleName)
        self.logger.debug(util.funcName('end'))

    def add_data_for_font(self, fontName, textvals, xmlStyleName):
        """
        Add content of a node for a particular effective font.

        :param fontName: effective font of the node
        :param textvals: text content of nodes
        :param xmlStyleName: only used for debugging
        """
        #self.logger.debug(
        #    util.funcName('begin', args=(fontName, len(textvals), xmlStyleName)))
        if fontName:
            newItem = FontItem()
            newItem.name = fontName
            newItem.inputData = textvals
            for item in self.data:
                if item == newItem:
                    item.inputData.extend(newItem.inputData)
                    break
            else:
                # newItem was not in self.data, so add it.
                self.logger.debug("appended font name %s", fontName)
                self.data.append(newItem)


class OdtChanger:
    def __init__(self, reader, fontChanges):
        """
        :param reader: type OdtReader
        :param fontChanges: list of elements type FontChange
        """
        self.reader = reader
        self.logger = reader.logger
        self.fontChanges = fontChanges

    def makeChanges(self):
        self.logger.debug(util.funcName('begin'))
        num_changes = self.changeContentFile(self.reader.contentDom)
        with io.open(os.path.join(self.reader.srcdir, 'styles.xml'),
                     mode="wt", encoding="utf-8") as f:
            self.reader.stylesDom.writexml(f, encoding="utf-8")
        with io.open(os.path.join(self.reader.srcdir, 'content.xml'),
                     mode="wt", encoding="utf-8") as f:
            self.reader.contentDom.writexml(f, encoding="utf-8")
        self.logger.debug(util.funcName('end'))
        return num_changes

    def changeContentFile(self, dom):
        """Make changes to content.xml dom."""
        self.logger.debug(util.funcName('begin'))
        num_changes = 0
        paragraphs = dom.getElementsByTagName("text:p")
        for paragraph in paragraphs:
            xmlStyleName = paragraph.getAttribute("text:style-name")
            #self.logger.debug("para style name %s", xmlStyleName)
            paraFontName = self.reader.stylesDict.get(
                xmlStyleName, self.reader.defaultFont)
            paraFontChange = self.effective_fontChange(paraFontName)
            if paraFontChange:
                para_text_nodelist = paragraph.childNodes
                for para_text_node in para_text_nodelist:
                    if para_text_node.nodeType == para_text_node.TEXT_NODE:
                        para_text_node.data = paraFontChange.converted_data[
                            para_text_node.data]
                        num_changes += 1
            spans = paragraph.getElementsByTagName("text:span")
            for span in spans:
                xmlStyleName = span.getAttribute("text:style-name")
                #self.logger.debug("span style name %s", xmlStyleName)
                spanFontName = self.reader.stylesDict.get(
                    xmlStyleName, paraFontName)
                spanFontChange = self.effective_fontChange(spanFontName)
                if spanFontChange:
                    span_text_nodelist = span.childNodes
                    for span_text_node in span_text_nodelist:
                        if span_text_node.nodeType == span_text_node.TEXT_NODE:
                            span_text_node.data = (
                                spanFontChange.converted_data[
                                    span_text_node.data])
                            num_changes += 1
        self.logger.debug(util.funcName('end'))
        return num_changes

    def effective_fontChange(self, fontName="", styleName=""):
        """Returns the FontChange object for the effective font,
        that is, the font specified by a paragraph node or
        overridden by a span node.
        """
        for fontChange in self.fontChanges:
            #TODO: Uncomment to use style name.
            #if (fontChange.fontItem.name == fontName
            #        and fontChange.fontItem.styleName == styleName):
            if fontChange.fontItem.name == fontName:
                return fontChange
        return None

