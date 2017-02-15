# -*- coding: Latin-1 -*-
#
# This file created June 22 2015 by Jim Kornelsen
#
# 16-Dec-15 JDK  Fixed bug: specify absolute path to xml files.
# 17-Dec-15 JDK  Implemented readContentFile with limited functionality.
# 22-Dec-15 JDK  Read a list of text nodes.
# 23-Dec-15 JDK  Added changeContentFile().
# 24-Dec-15 JDK  Added class OdtChanger.
# 20-Feb-16 JDK  Read complex and Asian font types.
# 21-Jun-16 JDK  Choose font type based on Unicode block.
# 13-Jul-16 JDK  Read font size.
# 21-Jul-16 JDK  Use ProcessingStyleItem instead of FontItem.
# 28-Jul-16 JDK  Handle ScopeType.PARASTYLE.
# 29-Jul-16 JDK  Handle any ScopeType value.
# 30-Sep-16 JDK  Add conversion functions for internal names.

"""
Read and change an ODT file in XML format.
Call SEC_wrapper to do engine-based conversion.

This module exports:
    OdtReader
    OdtChanger
"""
import copy
import io
import logging
import os
import re
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.access.xml import xmlutil
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import ProcessingStyleItem
from lingt.app.data.bulkconv_structs import StyleType, ScopeType
from lingt.utils import letters
from lingt.utils import util
from lingt.utils.fontsize import FontSize

logger = logging.getLogger("lingt.access.odt_converter")


class BasicStyleType:
    """Not to be confused with bulkconv_structs.StyleType"""
    DEFAULT = 0  # document defaults, which perhaps are a kind of named style
    NAMED = 1  # for example "Heading 1"
    AUTOMATIC = 2  # also known as custom formatting


class OdtReader(FileReader):

    SUPPORTED_FORMATS = [("xml", "Unzipped Open Document Format (.odt)"),]

    def __init__(self, srcdir, scopeType, unoObjs):
        """
        :param srcdir: will read and write the same XML files
        :param scopeType: lingt.app.data.bulkconv_structs.ScopeType
        """
        FileReader.__init__(self, unoObjs)
        self.srcdir = srcdir
        self.defaultStyleItem = None
        self.stylesDom = None
        self.contentDom = None
        self.scopeType = scopeType
        self.stylesDict = {}  # keys style name, value ProcessingStyleItem
        self.styleReader = StyleReader(self.stylesDict, scopeType)

    def _initData(self):
        """Elements are of type bulkconv_structs.ProcessingStyleItem."""
        self.data = []

    def _verifyDataFound(self):
        if not self.data:
            scope_string = ScopeType.TO_STRING[self.scopeType]
            logger.debug(
                "Searched by %s in folder %s but did not find anything.",
                scope_string, self.srcdir)
            raise exceptions.DataNotFoundError(
                "Searched by %s but did not find anything.", scope_string)

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
        logger.debug(util.funcName('begin', args=filepath))
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
        logger.debug(util.funcName('end'))
        return dom

    def readStylesFile(self, dom):
        """Read in styles.xml which defines named styles."""
        logger.debug(util.funcName('begin'))
        for style in dom.getElementsByTagName("style:default-style"):
            if style.getAttribute("style:family") == "paragraph":
                self.defaultStyleItem = (
                    self.styleReader.read_default_item(style))
        for style in dom.getElementsByTagName("style:style"):
            self.styleReader.add_named_style(style)
        logger.debug(util.funcName('end'))

    def readContentFile(self, dom):
        """Read in content.xml."""
        logger.debug(util.funcName('begin'))
        # Unlike common styles, automatic styles are not visible to the user.
        auto_styles = dom.getElementsByTagName("office:automatic-styles")[0]
        if auto_styles:
            for style in auto_styles.childNodes:
                self.styleReader.read_text_props(
                    style, BasicStyleType.AUTOMATIC)
        for paragraph in xmlutil.getElementsByTagNames(
                dom, ["text:h", "text:p"]):
            xmlStyleName = paragraph.getAttribute("text:style-name")
            paraStyleItem = self.stylesDict.get(
                xmlStyleName, self.defaultStyleItem)
            para_texts = xmlutil.getElemTextList(paragraph)
            styleItemAppender = StyleItemAppender(
                self.data, paraStyleItem, self.scopeType)
            styleItemAppender.add_texts(para_texts)
            for span in paragraph.getElementsByTagName("text:span"):
                xmlStyleName = span.getAttribute("text:style-name")
                spanStyleItem = self.stylesDict.get(
                    xmlStyleName, paraStyleItem)
                span_texts = xmlutil.getElemTextList(span)
                styleItemAppender = StyleItemAppender(
                    self.data, spanStyleItem, self.scopeType)
                styleItemAppender.add_texts(span_texts)
        logger.debug(util.funcName('end'))


def stylename_to_internal(stylename):
    """
    Returns the internal name of named style,
    used in content.xml.

    From http://books.evc-cit.info/odbook/ch02.html:
    Non-alphanumeric characters in names are converted to hexadecimal;
    thus blanks are converted to _20_.
    """
    return "".join([
        c if c.isalnum()
        else "_" + format(ord(c), 'x') + "_"
        for c in stylename])

def internal_to_stylename(internal_name):
    """Returns the normal display name of the internal style name.
    For example, sequences like __20__ are converted to spaces.
    """
    def replace_hexcodes(match):
        hexcode = match.group(1)
        return chr(int(hexcode, 16))

    return re.sub(r'_([a-zA-Z0-9]{2})_', replace_hexcodes, internal_name)


class StyleReader:
    """Read style node attributes.  Modifies stylesDict."""

    def __init__(self, stylesDict, scopeType):
        self.stylesDict = stylesDict
        self.scopeType = scopeType

    def read_default_item(self, styleNode):
        """Read style:text-properties nodes and return the styleItem.
        This is different from read_text_props() because there is no
        "style:name" attribute.
        """
        styleItem = ProcessingStyleItem(self.scopeType, False)
        if (self.scopeType != ScopeType.FONT_WITH_STYLE
                and self.scopeType != ScopeType.FONT_WITHOUT_STYLE):
            return styleItem
        self._read_text_properties(styleItem, styleNode)
        return styleItem

    def add_named_style(self, styleNode):
        """Add paragraph and character styles with inherited attributes."""
        if (self.scopeType == ScopeType.FONT_WITHOUT_STYLE
                or self.scopeType == ScopeType.WHOLE_DOC):
            return
        xmlStyleName = styleNode.getAttribute("style:name")
        parentStyleName = styleNode.getAttribute("style:parent-style-name")
        styleFamily = styleNode.getAttribute("style:family")
        if styleFamily == "paragraph":
            if self.scopeType == ScopeType.CHARSTYLE:
                return
        elif styleFamily == "text":
            if self.scopeType == ScopeType.PARASTYLE:
                return
        else:
            # Ignore other styles such as "table" and "graphic".
            return
        styleItem = ProcessingStyleItem(self.scopeType, True)
        self.stylesDict[xmlStyleName] = styleItem
        styleItem.internalStyleName = xmlStyleName
        styleItem.styleName = internal_to_stylename(xmlStyleName)
        if styleFamily == "paragraph":
            styleItem.styleType = StyleType.PARA
        else:
            styleItem.styleType = StyleType.CHAR
        if parentStyleName in self.stylesDict:
            parentStyleItem = self.stylesDict[parentStyleName]
            for attrName in (
                    'fontStandard', 'fontComplex', 'fontAsian',
                    'sizeStandard', 'sizeComplex', 'sizeAsian'):
                setattr(
                    styleItem, attrName,
                    getattr(parentStyleItem, attrName))
        self.read_text_props(styleNode, BasicStyleType.NAMED)

    def read_text_props(self, styleNode, basicStyleType):
        """Read style:text-properties nodes and store in self.stylesDict."""
        newStyleItem = ProcessingStyleItem(
            self.scopeType, (basicStyleType == BasicStyleType.NAMED))
        if (self.scopeType != ScopeType.FONT_WITH_STYLE
                and self.scopeType != ScopeType.FONT_WITHOUT_STYLE):
            return newStyleItem
        if (self.scopeType == ScopeType.FONT_WITHOUT_STYLE
                and basicStyleType == BasicStyleType.NAMED):
            return newStyleItem
        xmlStyleName = styleNode.getAttribute("style:name")
        if xmlStyleName in self.stylesDict:
            styleItem = self.stylesDict[xmlStyleName]
        else:
            styleItem = newStyleItem
        if self._read_text_properties(styleItem, styleNode):
            self.stylesDict[xmlStyleName] = styleItem

    def _read_text_properties(self, styleItem, styleNode):
        has_props = False
        for textprop in styleNode.getElementsByTagName(
                "style:text-properties"):
            if self._read_font_name(styleItem, textprop):
                has_props = True
            if self._read_font_size(styleItem, textprop):
                has_props = True
        return has_props

    def _read_font_name(self, styleItem, textprop):
        """Modifies styleItem and self.stylesDict."""
        has_props = False
        # Western is last in the list because it is the default.
        # The others will only be used if there are Complex or Asian
        # characters in the text.
        for xmlAttr, styleItemAttr, fontType in [
                ("style:font-name-asian", 'fontAsian', 'Asian'),
                ("style:font-name-complex", 'fontComplex', 'Complex'),
                ("style:font-name", 'fontStandard', 'Western')]:
            fontName = textprop.getAttribute(xmlAttr)
            if fontName:
                styleItem.fontName = fontName
                styleItem.fontType = fontType
                setattr(styleItem, styleItemAttr, fontName)
                has_props = True
        return has_props

    def _read_font_size(self, styleItem, textprop):
        """Modifies styleItem and self.stylesDict."""
        has_props = False
        for xmlAttr, styleItemAttr, fontType in [
                ("style:font-size-asian", 'sizeAsian', 'Asian'),
                ("style:font-size-complex", 'sizeComplex', 'Complex'),
                ("fo:font-size", 'sizeStandard', 'Western')]:
            fontSize = textprop.getAttribute(xmlAttr)
            if fontSize and fontSize.endswith("pt"):
                fontSize = fontSize[:-len("pt")]
                propSuffix = fontType
                if propSuffix == 'Western':
                    propSuffix = ""
                fontSizeObj = FontSize(fontSize, propSuffix, True)
                styleItem.size = fontSizeObj
                styleItem.fontType = fontType
                setattr(styleItem, styleItemAttr, fontSizeObj)
                has_props = True
        return has_props


class StyleItemAppender:
    """Adds information to a list of ProcessingStyleItem objects.
    Modifies the list.
    """
    def __init__(self, styleItems, baseStyleItem, scopeType):
        """
        :param styleItems: list of ProcessingStyleItem objects to modify
        :param baseStyleItem: effective font of the node
        """
        self.styleItems = styleItems
        self.baseStyleItem = baseStyleItem
        self.scopeType = scopeType
        self.styleItemDict = {}  # keys like 'Western', values are StyleItem

    def add_texts_with_debug(self, textvals, xmlStyleName):
        logger.debug(
            util.funcName(args=(
                self.baseStyleItem.fontName, len(textvals), xmlStyleName)))
        self.add_texts(textvals)

    def add_texts(self, textvals):
        """Add content of a node for a particular effective font.
        :param textvals: text content of nodes
        """
        if (not self.baseStyleItem.fontName
                or self.baseStyleItem.fontName == "(None)"):
            return
        for newItem in self._get_items_for_each_type(textvals):
            self._add_item_data(newItem)

    def _get_items_for_each_type(self, textvals):
        """The font type is based on the unicode block of a character,
        not just based on formatting.
        Because the font name may just fall back to defaults.
        """
        self.styleItemDict = {}
        for textval in textvals:
            text_of_one_type = ""
            curFontType = letters.TYPE_INDETERMINATE
            for c in textval:
                nextFontType = letters.getFontType(c, curFontType)
                if (nextFontType == curFontType
                        or curFontType == letters.TYPE_INDETERMINATE
                        or nextFontType == letters.TYPE_INDETERMINATE):
                    text_of_one_type += c
                elif text_of_one_type:
                    self._append_text_of_one_type(
                        text_of_one_type, curFontType)
                    text_of_one_type = ""
                curFontType = nextFontType
            if text_of_one_type:
                self._append_text_of_one_type(text_of_one_type, curFontType)
        return list(self.styleItemDict.values())

    def _append_text_of_one_type(self, textval, curFontType):
        FONT_TYPE_NUM_TO_NAME = {
            letters.TYPE_INDETERMINATE : 'Western',
            letters.TYPE_STANDARD : 'Western',
            letters.TYPE_COMPLEX : 'Complex',
            letters.TYPE_CJK : 'Asian'}
        fontTypeName = FONT_TYPE_NUM_TO_NAME[curFontType]
        styleItem = self._get_item_for_type(fontTypeName)
        if styleItem:
            styleItem.inputData.append(textval)

    def _get_item_for_type(self, fontType):
        """Sets styleItem.fontType and styleItem.fontName."""
        if fontType in self.styleItemDict:
            return self.styleItemDict[fontType]
        ATTR_OF_FONT_TYPE = {
            'Asian' : 'fontAsian',
            'Complex' : 'fontComplex',
            'Western' : 'fontStandard'}
        newItem = copy.deepcopy(self.baseStyleItem)
        newItem.fontType = fontType
        if (self.scopeType == ScopeType.FONT_WITHOUT_STYLE
                and self.baseStyleItem.named):
            pass
        else:
            newItem.fontName = getattr(
                self.baseStyleItem, ATTR_OF_FONT_TYPE[fontType])
        if (self.scopeType == ScopeType.PARASTYLE or
                self.scopeType == ScopeType.CHARSTYLE):
            if not newItem.styleName:
                return
        self.styleItemDict[fontType] = newItem
        return newItem

    def _add_item_data(self, newItem):
        for item in self.styleItems:
            if item == newItem:
                item.inputData.extend(newItem.inputData)
                break
        else:
            # newItem was not in self.styleItems, so add it.
            logger.debug("appending ProcessingStyleItem %s", newItem)
            self.styleItems.append(newItem)


def setNodeAttribute(node, xmlattr, newval):
    """Returns number of changes made."""
    current_val = node.getAttribute(xmlattr)
    if current_val != newval:
        node.setAttribute(xmlattr, newval)
        return 1
    return 0

class OdtChanger:
    def __init__(self, reader, styleChanges):
        """
        :param reader: type OdtReader
        :param styleChanges: list of elements type StyleChange
        """
        self.reader = reader
        self.styleChanges = styleChanges
        self.scopeType = reader.scopeType

    def makeChanges(self):
        logger.debug(util.funcName('begin'))
        num_changes = self.change_text(self.reader.contentDom)
        num_changes += self.change_styles(
            self.reader.contentDom, self.reader.stylesDom)
        if num_changes == 0:
            return num_changes
        with io.open(os.path.join(self.reader.srcdir, 'styles.xml'),
                     mode="wt", encoding="utf-8") as f:
            self.reader.stylesDom.writexml(f, encoding="utf-8")
        with io.open(os.path.join(self.reader.srcdir, 'content.xml'),
                     mode="wt", encoding="utf-8") as f:
            self.reader.contentDom.writexml(f, encoding="utf-8")
        logger.debug(util.funcName('end'))
        return num_changes

    def change_text(self, dom):
        """Convert text in content.xml with EncConverters."""
        logger.debug(util.funcName('begin'))
        num_changes = 0
        for paragraph in xmlutil.getElementsByTagNames(
                dom, ["text:h", "text:p"]):
            xmlStyleName = paragraph.getAttribute("text:style-name")
            #logger.debug("para style name %s", xmlStyleName)
            paraStyleItem = self.reader.stylesDict.get(
                xmlStyleName, self.reader.defaultStyleItem)
            paraStyleChange = self.effective_styleChange(paraStyleItem)
            if paraStyleChange:
                logger.debug("Change for [%s]", xmlStyleName)
                for para_child in paragraph.childNodes:
                    if para_child.nodeType == para_child.TEXT_NODE:
                        if para_child.data in paraStyleChange.converted_data:
                            para_child.data = paraStyleChange.converted_data[
                                para_child.data]
                            num_changes += 1
            else:
                logger.debug("No change for [%s]", xmlStyleName)
            for span in paragraph.getElementsByTagName("text:span"):
                xmlStyleName = span.getAttribute("text:style-name")
                #logger.debug("span style name %s", xmlStyleName)
                spanStyleItem = self.reader.stylesDict.get(
                    xmlStyleName, paraStyleItem)
                spanStyleChange = self.effective_styleChange(spanStyleItem)
                if spanStyleChange:
                    for span_child in span.childNodes:
                        if span_child.nodeType == span_child.TEXT_NODE:
                            if (span_child.data in
                                    spanStyleChange.converted_data):
                                span_child.data = (
                                    spanStyleChange.converted_data[
                                        span_child.data])
                            num_changes += 1
        logger.debug(util.funcName('end'))
        return num_changes

    def change_styles(self, contentDom, stylesDom):
        """Change fonts and named styles."""
        num_changes = 0
        #TODO: Distinguish between automatic and named styles.
        for style in (
                contentDom.getElementsByTagName("style:font-face") +
                stylesDom.getElementsByTagName("style:font-face")):
            fontName = style.getAttribute("style:name")
            for styleChange in self.styleChanges:
                if fontName == styleChange.styleItem.fontName:
                    num_changes += setNodeAttribute(
                        style, "style:name", styleChange.fontName)
                    num_changes += setNodeAttribute(
                        style, "svg:font-family", styleChange.fontName)
        for style in (
                contentDom.getElementsByTagName("style:style") +
                stylesDom.getElementsByTagName("style:default-style")):
            for textprop in style.getElementsByTagName(
                    "style:text-properties"):
                fontName = textprop.getAttribute("style:font-name")
                for styleChange in self.styleChanges:
                    if fontName == styleChange.styleItem.fontName:
                        num_changes += setNodeAttribute(
                            textprop, "style:font-name", styleChange.fontName)
                        #num_changes += setNodeAttribute(
                        #   style, "style:parent-style-name",
                        #   styleChange.fontType)
                        #fontSize = textprop.getAttribute("fo:font-size")
                        #if fontSize and styleChange.size.isSpecified():
                        if styleChange.size.isSpecified():
                            num_changes += setNodeAttribute(
                                textprop, "fo:font-size",
                                str(styleChange.size) + "pt")
        return num_changes

    def effective_styleChange(self, processingStyleItem):
        """Returns the StyleChange object for the effective style,
        that is, the style specified by a paragraph node or
        overridden by a span node.
        """
        if processingStyleItem is None:
            logger.debug("processingStyleItem is None")
            return None
        logger.debug("Looking for %r", processingStyleItem)
        for styleChange in self.styleChanges:
            logger.debug("Checking %r", styleChange.styleItem)
            # This calls the overridden ProcessingStyleItem.__eq__().
            if processingStyleItem == styleChange.styleItem:
                logger.debug("Found %r", styleChange.styleItem)
                return styleChange
        logger.debug("Did not find processingStyleItem.")
        return None
