# -*- coding: Latin-1 -*-
#
# This file created Sept 14 2010 by Jim Kornelsen
#
# 20-Sep-10 JDK  Fixed bug: bottom and right frame margins were switched.
# 29-Sep-10 JDK  Class for managing the font of a style, for Data Conversion.
# 01-Oct-10 JDK  Added hasCharStyle().  Create Orthographic Morph style.
# 22-Oct-10 JDK  Ability to set font size specified by user.
# 25-Oct-10 JDK  Use uniqueList() instead of set().
# 23-Oct-12 JDK  Now that we require a newer python version, use set().
# 11-Mar-13 JDK  Don't add "Default" paragraph style.  Use "Standard".
#                Also show display names in list.
# 13-Mar-13 JDK  Set attributes according to font type.
# 15-Apr-13 JDK  getListOfStyles() returns both underlying and display names.
# 18-Apr-13 JDK  Return status from resizeNumberingCol.
# 29-Jul-13 JDK  Import constants instead of using uno.getConstantByName.
# 08-Aug-15 JDK  Added StyleFamily class.
# 10-Aug-15 JDK  Use generator to loop through UNO collections.
# 25-Sep-15 JDK  Modify existing styles.
# 28-Sep-15 JDK  Resizing was not working after refactoring.
# 05-Oct-15 JDK  Default args for getFontOfStyle().
# 24-Mar-16 JDK  StyleFonts does not need user vars to specify style name.

"""
Create and manage styles.
Note on terminology:
    "Style" in this module means a named style.
    Automatic styles (also known as custom formatting) are just called fonts.
    This terminology is in contrast with modules such as
    writer/odt_converter.py that deal with the XML file format.
"""
import logging
from operator import itemgetter

from com.sun.star.style import TabStop
from com.sun.star.style.TabAlign import LEFT
from com.sun.star.text.SizeType import VARIABLE
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER
from com.sun.star.text.VertOrientation import LINE_TOP

from lingt.access.common import iteruno
from lingt.app import exceptions
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util
from lingt.utils.fontsize import FontSize

logger = logging.getLogger("lingt.access.Styles")

INCH_TO_CM = 2540  # convert 1/1000 cm to inches

# font colors
COLOR_BLACK = int("000000", 16)
COLOR_BLUE = int("0000FF", 16)
COLOR_MAGENTA = int("800080", 16)
COLOR_LIGHT_RED = int("FF0000", 16)
COLOR_LIGHT_MAGENTA = int("FF00FF", 16)
COLOR_GREEN = int("008000", 16)
COLOR_RED = int("800000", 16)


class FontDefStruct:
    def __init__(self, fontName="", fontType='Western', fontSize=None):
        """
        :param fontName: for example "Times New Roman"
        :param fontType: Western, Complex or Asian
        :param fontSize: type utils.fontsize.FontSize
        """
        self.fontName = fontName
        self.fontType = fontType
        if not fontSize:
            fontSize = FontSize()
        self.fontSize = fontSize


FONT_ORTH = FontDefStruct(
    "Mangal", "Complex", FontSize(14.0, spec=True))
FONT_VERN = FontDefStruct(
    "Doulos SIL", "Western", FontSize(14.0, spec=True))
FONT_GLOSS = FontDefStruct(
    "Times New Roman", "Western", FontSize(12.0, spec=True))
FONT_FIXED = FontDefStruct(
    "Courier New", "Western", FontSize(12.0, spec=True))


class DocumentStyles:
    """Abstract base class for managing the styles in a document."""
    styleVars = []
    defaultNames = {}

    def __init__(self, unoObjs, userVars):
        if self.__class__ is DocumentStyles:
            # The base class should not be instantiated.
            raise NotImplementedError()
        self.unoObjs = unoObjs
        self.userVars = userVars
        logger.debug("DocumentStyles() middle")
        self.msgbox = MessageBox(unoObjs)
        self.styleNames = {}
        self.families = unoObjs.document.getStyleFamilies()
        self.parastyles = StyleFamily('Paragraph', self)
        self.charstyles = StyleFamily('Character', self)
        self.framestyles = StyleFamily('Frame', self)

        # The user may set a different style with user vars.
        for key, var in self.styleVars:
            name = self.userVars.get(var)
            if name == "":
                name = self.defaultNames[key]
                self.userVars.store(var, name)
            self.styleNames[key] = name
            logger.debug("self.styleNames[%s] = %s", key, name)
        logger.debug("DocumentStyles() finished")

    def getNames(self):
        return self.styleNames

    def requireParaStyle(self, styleKey):
        self.parastyles.require(styleKey)

    def requireCharStyle(self, styleKey):
        self.charstyles.require(styleKey)

    def requireFrameStyle(self, styleKey):
        self.framestyles.require(styleKey)


def setFontAttrs(styleObj, fontDef, color=None):
    logger.debug(util.funcName('begin'))
    if fontDef:
        propSuffix = fontDef.fontType
        if propSuffix == 'Western':
            propSuffix = ""
        if fontDef.fontName:
            logger.debug("font name %r", fontDef.fontName)
            styleObj.setPropertyValue(
                'CharFontName' + propSuffix, fontDef.fontName)
            if fontDef.fontSize.isSpecified():
                fontDef.fontSize.setPropSuffix(propSuffix)
                fontDef.fontSize.changeElemProp(styleObj)
    else:
        logger.warning("no fontDef specified")
    if color is not None:
        styleObj.CharColor = color

def setFrameAttrs(styleObj, margins):
    if not margins:
        raise exceptions.LogicError("Expected frame margin parameter.")
    rightMargin, bottomMargin = margins
    styleObj.AnchorType = AS_CHARACTER
    styleObj.VertOrient = LINE_TOP
    styleObj.WidthType = VARIABLE
    styleObj.LeftMargin = 0
    styleObj.TopMargin = 0
    styleObj.RightMargin = rightMargin * INCH_TO_CM
    styleObj.BottomMargin = bottomMargin * INCH_TO_CM
    styleObj.BorderDistance = 0
    BORDER_WIDTH = 0
    borderLine = styleObj.getPropertyValue("LeftBorder")
    borderLine.OuterLineWidth = BORDER_WIDTH
    styleObj.setPropertyValue("LeftBorder", borderLine)
    styleObj.setPropertyValue("RightBorder", borderLine)
    styleObj.setPropertyValue("TopBorder", borderLine)
    styleObj.setPropertyValue("BottomBorder", borderLine)

class StyleFamily:
    """Manage a family of styles in a document."""

    def __init__(self, familyName, documentStylesObj):
        """
        :param familyName: Paragraph, Character or Frame
        :param documentStylesObj: type DocumentStyles
        """
        self.familyName = familyName
        main = documentStylesObj
        self.unoObjs = main.unoObjs
        self.families = main.families
        self.styleNames = main.styleNames
        self.styleObjs = None  # UNO collection of styles

    def __contains__(self, styleKey):
        if not self.styleObjs:
            listName = self.familyName + "Styles"
            self.styleObjs = self.families.getByName(listName)
        styleName = self.styleNames[styleKey]
        logger.debug(repr(styleName))
        return self.styleObjs.hasByName(str(styleName))

    def require(self, styleKey):
        """Raises an exception if style does not exist."""
        if styleKey not in self:
            raise exceptions.StyleError(
                str(self.familyName) + " style '%s' is missing",
                self.styleNames[styleKey])

    def createInDoc(self, styleKey, fontDef=None, color=None, margins=None,
                    modify=False):
        """
        Create a style with the attributes specified.

        :param modify: true to modify attributes of an existing style
        :returns: newly created style, or None if style already exists
        """
        createdObj = None
        styleName = self.styleNames[styleKey]
        if styleKey in self:
            if modify:
                logger.debug(
                    "Modifying %s style '%s'", self.familyName, styleName)
                styleObj = self.styleObjs.getByName(styleName)
            else:
                logger.debug(util.funcName('return'))
                return None
        else:
            logger.debug(
                "Creating %s style '%s'", self.familyName, styleName)
            styleObj = self.unoObjs.document.createInstance(
                "com.sun.star.style.%sStyle" % self.familyName)
            self.styleObjs.insertByName(styleName, styleObj)
            createdObj = styleObj
        if self.familyName == 'Frame':
            setFrameAttrs(styleObj, margins)
        else:
            setFontAttrs(styleObj, fontDef, color)
        logger.debug(util.funcName('end'))
        return createdObj


class PhonologyStyles(DocumentStyles):
    styleVars = [['phonemic', "StyleName_Phonemic"],
                 ['phonetic', "StyleName_Phonetic"],
                 ['gloss', "StyleName_Gloss"],
                 ['ref', "StyleName_RefNum"],
                 ['exPara', "StyleName_ExamplePara"]]

    defaultNames = {'phonemic' : "Lex Phonemic",
                    'phonetic' : "Lex Phonetic",
                    'gloss' : "Lex Gloss",
                    'ref' : "Lex Reference Number",
                    'exPara' : "Lex Example"}

    def createStyles(self):
        """Create styles if they don't already exist."""

        ## Create character styles

        logger.debug("Creating character styles")
        styleDefs = [
            ('phonemic', FONT_VERN, COLOR_GREEN),
            ('phonetic', FONT_VERN, COLOR_BLUE),
            ('gloss', FONT_GLOSS, COLOR_BLACK),
            ('ref', FONT_FIXED, COLOR_LIGHT_RED)]
        for styleKey, fontDef, color in styleDefs:
            self.charstyles.createInDoc(styleKey, fontDef, color)

        ## The paragraph style

        newStyle = self.parastyles.createInDoc("exPara")
        if newStyle:
            newStyle.setParentStyle("Standard")

            ## set tabs on paragraph style
            stops = []
            position = 0
            for width in [INCH_TO_CM * 1/2,
                          INCH_TO_CM * 1.5,
                          INCH_TO_CM * 1.5,
                          INCH_TO_CM * 1.5,
                          INCH_TO_CM * 1.5]:
                position += width
                tabStop = TabStop()
                tabStop.Position = position    # 1/1000cm: 2540 = 1 inch
                tabStop.Alignment = LEFT
                tabStop.DecimalChar = "."
                tabStop.FillChar = " "
                stops.append(tabStop)
            newStyle.ParaTabStops = tuple(stops)


class GrammarStyles(DocumentStyles):
    """Make changes to styles and the document itself."""
    styleVars = [['orth', "StyleName_Orthographic"],
                 ['text', "StyleName_Text"],
                 ['morph', "StyleName_Morpheme"],
                 ['orthm', "StyleName_OrthographicMorph"],
                 ['pos', "StyleName_POS"],
                 ['gloss', "StyleName_Gloss"],
                 ['ft', "StyleName_FreeTxln"],
                 ['ref', "StyleName_RefNum"],
                 ['numP', "StyleName_NumPara"],
                 ['intF', "StyleName_InterlinearFrame"],
                 ['morF', "StyleName_MorphemeFrame"]]

    defaultNames = {'orth' : "Interlin Orthographic",
                    'text' : "Interlin Base",
                    'morph' : "Interlin Morph",
                    'orthm' : "Interlin Orthographic Morph",
                    'pos' : "Interlin POS",
                    'gloss' : "Interlin Gloss",
                    'ft' : "Interlin Freeform Gloss",
                    'ref' : "Interlin Reference Number",
                    'numP' : "Interlin Example Number",
                    'intF' : "Interlin Frame",
                    'morF' : "Interlin Morpheme Frame"}

    def createStyles(self):
        """Create styles if they don't already exist."""
        logger.debug(util.funcName('begin'))

        ## Paragraph styles

        logger.debug("Modifying styles of interlinear lines")
        styleDefs = [
            ('orth', FONT_ORTH, COLOR_BLACK),
            ('text', FONT_VERN, COLOR_BLUE),
            ('orthm', FONT_ORTH, COLOR_BLACK),
            ('morph', FONT_VERN, COLOR_MAGENTA),
            ('pos', FONT_GLOSS, COLOR_LIGHT_RED),
            ('gloss', FONT_GLOSS, COLOR_LIGHT_MAGENTA),
            ('ft', FONT_GLOSS, COLOR_GREEN)]
        for styleKey, fontDef, color in styleDefs:
            self.parastyles.createInDoc(styleKey, fontDef, color)

        ## Character styles

        styleDefs = [('ref', FONT_FIXED, COLOR_RED)]
        for styleKey, fontDef, color in styleDefs:
            self.charstyles.createInDoc(styleKey, fontDef, color)

        ## Styles for spacing

        styleDefs = [('numP', 0.07, 0.0)]
        for styleDef in styleDefs:
            styleKey, topMargin, bottomMargin = styleDef
            newStyle = self.parastyles.createInDoc(styleKey)
            if newStyle:
                newStyle.ParaTopMargin = topMargin * INCH_TO_CM
                newStyle.ParaBottomMargin = bottomMargin * INCH_TO_CM

        ## Styles for frames

        logger.debug("Modifying styles of frames")
        styleDefs = [('intF', 0.1, 0.1),
                     ('morF', 0.1, 0.0)]
        for styleDef in styleDefs:
            styleKey, rightMargin, bottomMargin = styleDef
            self.framestyles.createInDoc(
                styleKey, margins=(rightMargin, bottomMargin))
        logger.debug(util.funcName('end'))

    def resizeNumberingCol(self, colWidthText, prevColWidth):
        """
        Resize the width of the column that contains example numbering.
        Size is an integer percentage of the page width.
        @param string colWidthText
        @param int    prevColWidth
        throws exceptions.ChoiceProblem

        It would be nice if there were such a thing as table styles.
        Then this function would presumably not be needed.
        """
        logger.debug(util.funcName('begin'))
        if colWidthText == "":
            raise exceptions.ChoiceProblem(
                "Please enter a value for column width.")
        try:
            newVal = int(colWidthText)
        except:
            raise exceptions.ChoiceProblem("Column width is not a number.")
        if newVal == prevColWidth:
            logger.debug("No need to change.")
            return
        if newVal > 50:     # more than 50% is unreasonable
            raise exceptions.ChoiceProblem(
                "Value %d for column width is too high.", newVal)
        elif newVal <= 0:
            raise exceptions.ChoiceProblem(
                "Value for column width must be more than zero.")

        PERCENT_TO_SEP = 100  # Separator width 10,000 is 100%.
                               # The user enters a number like 5 meaning 5%.
                               # So 5 * 100 would be 500 which is 5% of 10,000
        MARGIN_OF_ERROR = 2
        prevVal = prevColWidth * PERCENT_TO_SEP
        newVal = newVal * PERCENT_TO_SEP
        tables = self.unoObjs.document.getTextTables()
        logger.debug(
            "looping through %d tables.  prevVal = %d",
            tables.getCount(), prevVal)
        for table in iteruno.byIndex(tables):
            separators = table.getPropertyValue("TableColumnSeparators")
            if separators is None:
                logger.debug(
                    "No separators set for table %s", table.getName())
                continue
            sep0Pos = separators[0].Position
            logger.debug(
                "table %s separator is %d", table.getName(), sep0Pos)
            if (sep0Pos > prevVal - MARGIN_OF_ERROR and
                    sep0Pos < prevVal + MARGIN_OF_ERROR):
                separators[0].Position = newVal
                table.TableColumnSeparators = separators
                logger.debug("changed to %d", newVal)

        self.userVars.store("NumberingColWidth", str(newVal // PERCENT_TO_SEP))
        logger.debug(util.funcName('end'))


class AbbrevStyles(DocumentStyles):
    styleVars = [['abbr', "StyleName_Abbrev"]]
    defaultNames = {'abbr' : "Abbreviation Item"}

    def createStyles(self):
        logger.debug(util.funcName('begin'))
        self.parastyles.createInDoc('abbr', FONT_GLOSS)
        logger.debug(util.funcName('end'))


class StyleFonts(DocumentStyles):
    """Manages the font of a style."""
    def __init__(self, unoObjs, styleNames=None):
        """
        :param styleNames: specify this when passing styleKey params
        """
        DocumentStyles.__init__(self, unoObjs, None)
        if styleNames:
            self.styleNames.update(styleNames)

    def getFontOfStyle(self, styleFamilyName='', fontType='',
                       styleName=None, styleKey=None):
        """
        :param styleFamilyName: 'Paragraph' or 'Character'
        :param fontType: 'Western', 'Asian', or 'Complex'
        :param styleName: for example "Default" or "Heading 1"
        :param styleKey: for example 'orth' but see _setStyleKey()
        :returns: font name and size of the specified type
        """
        logger.debug(util.funcName(
            'begin', args=(styleFamilyName, fontType, styleName, styleKey)))
        styleKey = self._setStyleKey(styleName, styleKey)
        styleFamily = self.parastyles
        if styleFamilyName == 'Character':
            styleFamily = self.charstyles
        propSuffix = fontType
        if propSuffix == 'Western':
            propSuffix = ''
        fontSize = FontSize(propSuffix=propSuffix)
        if styleKey in styleFamily:
            styleObj = styleFamily.styleObjs.getByName(styleName)
            fontName = styleObj.getPropertyValue('CharFontName%s' % propSuffix)
            fontSize.loadElemProp(styleObj)
            return fontName, fontSize
        return "", fontSize

    def setParaStyleWithFont(self, fontDef, styleName=None, styleKey=None):
        """Set the font of the paragraph style."""
        styleKey = self._setStyleKey(styleName, styleKey)
        self.parastyles.createInDoc(styleKey, fontDef, modify=True)

    def setCharStyleWithFont(self, fontDef, styleName=None, styleKey=None):
        """Set the font of the character style."""
        styleKey = self._setStyleKey(styleName, styleKey)
        self.charstyles.createInDoc(styleKey, fontDef, modify=True)

    def _setStyleKey(self, styleName, styleKey):
        """If no key is specified, we use the name as the key.
        In Data Conversion the user specifies the style name in the
        dialog, so no key is needed.
        """
        if not styleKey:
            styleKey = styleName
            self.styleNames[styleName] = styleName
        return styleKey


def getListOfStyles(familyName, unoObjs):
    """Returns a list of tuples (display name, underlying name)
    The display name may be localized or changed for readability.
    In the rest of this module, the underlying name is used.
    """
    logger.debug(util.funcName())
    families = unoObjs.document.getStyleFamilies()
    styleObjs = families.getByName(familyName)
    styleNames = []
    for style in iteruno.byIndex(styleObjs):
        styleNames.append(
            (style.getPropertyValue("DisplayName"), style.getName()))
    # sort by display name
    styleNames.sort(key=itemgetter(0))
    logger.debug("styleNames has %d elements", len(styleNames))
    return styleNames

def getListOfFonts(unoObjs, addBlank=False):
    logger.debug("getListOfFonts")
    toolkit = unoObjs.smgr.createInstanceWithContext(
        "com.sun.star.awt.Toolkit", unoObjs.ctx)
    device = toolkit.createScreenCompatibleDevice(0, 0)
    fontDescriptors = device.getFontDescriptors()
    fontList = []
    for fontDescriptor in fontDescriptors:
        fontList.append(fontDescriptor.Name)
    # make the list unique and sorted
    fontList = sorted(list(set(fontList)))
    if addBlank:
        fontList.insert(0, "(None)")
    logger.debug("fontList has %d elements", len(fontList))
    return tuple(fontList)

