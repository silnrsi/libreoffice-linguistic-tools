# -*- coding: Latin-1 -*-
#
# This file created Aug 16, 2013 by Jim Kornelsen
#
# 09-Oct-15 JDK  Use python 3 string literals.
# 10-Nov-15 JDK  Now askEach catches all messages.
# 17-Nov-15 JDK  Reset direction user var at the end of test1.
# 20-May-16 JDK  Move useDialog definitions out of for loops.

# pylint: disable=no-self-use

"""
Test all features accessed by Data Conversion dialog controls.
Start from UI which calls App and Access layers (top-down).

As of November 2015, this test suite crashes on linux,
perhaps due to the ecdriver.
"""
from __future__ import unicode_literals
import collections
import logging
import os
import unittest

from lingttest.utils import testutil
from lingttest.utils.testutil import MyActionEvent, PARAGRAPH_BREAK

from lingt.access import sec_wrapper
from lingt.access.sec_wrapper import ConvType
from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.sec_wrapper import ProcessTypeFlags
from lingt.access.writer import styles
from lingt.ui.comp.dataconv import DlgDataConversion
from lingt.utils import util

logger = logging.getLogger("lingttest.dataconv_test")
addedConverters = set()  # which converters have we added


def getSuite():
    testutil.modifyClass_showDlg(DlgDataConversion)
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_toUpper',
            'test2_scopeFont',
            #'test3_parastyles',
            #'test4_charstyles',
            #'test5_targetFont',
            #'test6_encTypes',
        ):
        suite.addTest(DataConvTestCase(method_name))
    return suite


# If your system uses a font that is not here then manually add it
# as a key, and specify a different font as the value.
CHANGED_FONT = {
    "Liberation Serif": "Verdana",  # western LibreOffice
    "Liberation Sans": "Verdana",  # western LibreOffice
    "Times New Roman": "Verdana",  # western OpenOffice
    "Arial": "Verdana",  # western OpenOffice
    "Mangal": "Latha",  # complex Windows
    "FreeSans": "Lohit Tamil",  # complex Linux
    "Microsoft YaHei": "SimHei",  # asian Windows
    "SimSun": "SimHei",  # asian Windows
    "Droid Sans Fallback": "DejaVu Serif",  # asian Linux
    }

# Roman script paragraphs that allow simple upper/lowercase conversion.
# Also standard format markers.
ROMAN_PARAGRAPHS = [
    (r"\a Begin",),
    (r"\b selsFound1",),
    (r"\cc soMe r", "andOml", "Y capITaLIzed words"),
    (r"\d A nor", "mal paragraph.  Som", "ewhat long though."),
    (r"\eee sdgkl", "sdlkgjgldkj", "sdkljsdlkgjsd."),
    (r"\f dshkjle", "gsl.  Kekjgls", "slege."),
    (r"\g eoiksj feoi", "s3jsd.  Dgjsdh sdk", "slekj selkj."),
    (r"\hh End",),
    ]


class DataConvTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.unoObjs = None
        self.dlg = None

    @classmethod
    def setUpClass(cls):
        unoObjs = util.UnoObjs(
            testutil.stored.getContext(), loadDocObjs=False)
        testutil.blankWriterDoc(unoObjs)

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.dlg = DlgDataConversion(self.unoObjs)

    def runDlg(self, useDialog):
        DlgDataConversion.useDialog = useDialog
        try:
            self.dlg.showDlg()
        except testutil.MsgSentException:
            pass
        testutil.do_dispose(self.dlg)

    def test1_toUpper(self):
        """Keep it simple here -- a first test to see if basic conversion
        is working.
        Also tests the reverse checkbox.
        """
        convName = "capsTest.tec"
        self.addConverter(convName)
        textContent = "abCde\rFghI jkl"
        for reverse in False, True:
            self.setTextContent(textContent)
            func = self._test1_make_useDialog(reverse, convName)
            self.runDlg(func)
            expectedContent = textContent.replace("\r", "\r\n")
            if reverse:
                expectedContent = expectedContent.lower()
            else:
                expectedContent = expectedContent.upper()
            self.verifyTextContent(expectedContent)
        # Set converter settings to default.
        conv = ConverterSettings(self.dlg.userVars)
        conv.storeUserVars()

    def _test1_make_useDialog(self, reverse, convName):
        def useDialog(innerSelf):
            innerSelf.dlgCtrls.txtConverterName.setText(convName)
            innerSelf.dlgCtrls.chkDirectionReverse.setState(reverse)
            innerSelf.dlgCtrls.optScopeWholeDoc.setState(True)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("Close_and_Convert"))
        return useDialog

    def test2_scopeFont(self):
        """Test searching for direct formatting, which is perhaps the most
        common use for Data Conversion.
        """
        convName = "Any-Hex"
        self.addConverter(convName)
        Test2Data = collections.namedtuple('Test2Data', [
            'fontType', 'ctrlName', 'testChar'])
        dataSets = [
            Test2Data("Western", "optScopeFontWestern", "a"),
            # Tamil letter Ma
            Test2Data("Complex", "optScopeFontComplex", "\u0bae"),
            # a Chinese character
            Test2Data("Asian", "optScopeFontAsian", "\ua000")]
        for dataSet in dataSets:
            self._test2_do_dataSet(dataSet, convName)

    def _test2_do_dataSet(self, data, convName):
        CONTENT_LEN = 5  # arbitrary
        FORMAT_AT_INDEX = 3  # arbitrary
        textContent = data.testChar * CONTENT_LEN
        self.setTextContent(textContent)
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        oVC.goRight(FORMAT_AT_INDEX, False)
        oVC.goRight(1, True)  # select
        styleFonts = styles.StyleFonts(self.unoObjs)
        fontName, dummy = styleFonts.getFontOfStyle(
            styleName=testutil.getDefaultStyle(), fontType=data.fontType)
        fontDef = styles.FontDefStruct(
            CHANGED_FONT[fontName], data.fontType)
        # change font for one character
        styles.setFontAttrs(oVC, fontDef)
        oVC.goRight(0, False)  # deselect

        def useDialog(innerSelf):
            innerSelf.dlgCtrls.txtConverterName.setText(convName)
            innerSelf.dlgCtrls.optScopeFont.setState(1)
            getattr(innerSelf.dlgCtrls, data.ctrlName).setState(1)
            innerSelf.dlgCtrls.comboScopeFont.setText(fontDef.fontName)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("Close_and_Convert"))

        self.runDlg(useDialog)
        expectedChars = list(textContent)
        expectedChars[FORMAT_AT_INDEX] = anyToHex(data.testChar)
        self.verifyTextContent("".join(expectedChars))

    def test3_parastyles(self):
        """Test scope paragraph style and SF markers,
        target paragraph style.  Also test asking about each change.
        """
        CONVERT_PARAGRAPHS = ROMAN_PARAGRAPHS[1:-1]  #  all but start and end
        markers = []
        for para in CONVERT_PARAGRAPHS:
            paraString = "".join(para)
            marker = paraString.split()[0]
            markers.append(marker.lstrip("\\"))
        testutil.modifyMsgboxFour('yes')
        Test3Data = collections.namedtuple('Test3Data', [
            'askEach', 'ctrlName'])
        dataSets = [
            Test3Data(False, "optScopeParaStyle"),
            Test3Data(True, "optScopeParaStyle"),
            Test3Data(False, "optScopeSFMs"),
            Test3Data(True, "optScopeSFMs"),
            ]
        for dataSet in dataSets:
            self._test3_do_dataSet(dataSet, markers, CONVERT_PARAGRAPHS)

    def _test3_do_dataSet(self, data, markers, CONVERT_PARAGRAPHS):
        PARASTYLE_FROM = "Heading 5"  # source para style
        PARASTYLE_TO = "Heading 4"  # target para style
        self.setTextContent(ROMAN_PARAGRAPHS, True)

        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        for dummy in range(len(CONVERT_PARAGRAPHS)):
            oVC.goDown(1, False)
            oVC.setPropertyValue(
                "ParaStyleName", PARASTYLE_FROM)

        def useDialog(innerSelf):
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("NoConverter"))
            getattr(innerSelf.dlgCtrls, data.ctrlName).setState(1)
            innerSelf.dlgCtrls.comboScopeParaStyle.setText(
                PARASTYLE_FROM)
            innerSelf.dlgCtrls.txtSFM.setText(" ".join(markers))
            innerSelf.dlgCtrls.optTargetParaStyle.setState(1)
            innerSelf.dlgCtrls.comboTargetParaStyle.setText(
                PARASTYLE_TO)
            innerSelf.dlgCtrls.chkVerify.setState(data.askEach)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("Close_and_Convert"))

        testutil.clear_messages_sent()
        self.runDlg(useDialog)
        oVC.gotoStart(False)
        self.assertNotEqual(
            oVC.getPropertyValue("ParaStyleName"), PARASTYLE_TO,
            msg=repr(data))
        for dummy in CONVERT_PARAGRAPHS:
            oVC.goDown(1, False)
            self.assertEqual(
                oVC.getPropertyValue("ParaStyleName"), PARASTYLE_TO,
                msg=repr(data))
        oVC.goDown(1, False)
        self.assertNotEqual(
            oVC.getPropertyValue("ParaStyleName"), PARASTYLE_TO,
            msg=repr(data))
        if data.askEach:
            self.assertEqual(
                len(testutil.messages_sent), len(CONVERT_PARAGRAPHS) + 1,
                msg=repr(data))

    def test4_charstyles(self):
        """Test scope current selection and character style,
        target character style.
        """
        for ctrlName in ("optScopeSelection", "optScopeCharStyle"):
            self._test4_do_dataSet(ctrlName)

    def _test4_do_dataSet(self, ctrlName):
        CHARSTYLE_FROM = "Emphasis"  # source char style
        CHARSTYLE_TO = "Strong Emphasis"  # target char style
        LEFT, MID = 0, 1  # indices of paragraph splits
        self.setTextContent(ROMAN_PARAGRAPHS, True)
        self._select_multiple_strings(ctrlName, CHARSTYLE_FROM)

        def useDialog(innerSelf):
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("NoConverter"))
            getattr(innerSelf.dlgCtrls, ctrlName).setState(1)
            innerSelf.dlgCtrls.comboScopeCharStyle.setText(CHARSTYLE_FROM)
            innerSelf.dlgCtrls.optTargetCharStyle.setState(1)
            innerSelf.dlgCtrls.comboTargetCharStyle.setText(CHARSTYLE_TO)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("Close_and_Convert"))

        self.runDlg(useDialog)
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        for para in ROMAN_PARAGRAPHS:
            if len(para) <= MID:
                oVC.goDown(1, False)
                continue
            oVC.gotoStartOfLine(False)
            oVC.goRight(len(para[LEFT]) - 1, False)
            self.assertNotEqual(
                oVC.getPropertyValue("CharStyleName"), CHARSTYLE_TO)
            oVC.goRight(1, False)
            oVC.goRight(len(para[MID]), True)
            self.assertEqual(
                oVC.getPropertyValue("CharStyleName"), CHARSTYLE_TO)
            oVC.goRight(1, False)
            self.assertNotEqual(
                oVC.getPropertyValue("CharStyleName"), CHARSTYLE_TO)
            oVC.goDown(1, False)

    def _select_multiple_strings(self, ctrlName, CHARSTYLE_FROM):
        dummy_LEFT, MID = 0, 1  # indices of paragraph splits
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchRegularExpression = True
        # For some reason the first selected string gets collapsed,
        # so we include an extra one.
        stringsToFind = ["selsFound1"]
        stringsToFind.extend(
            [para[MID] for para in ROMAN_PARAGRAPHS if len(para) > MID])
        search.SearchString = "|".join(stringsToFind)
        #print("/%s/" % search.SearchString)
        selsFound = self.unoObjs.document.findAll(search)
        self.assertEqual(selsFound.getCount(), len(stringsToFind))
        oVC = self.unoObjs.viewcursor
        self.unoObjs.controller.select(selsFound)
        self.assertEqual(
            self.unoObjs.controller.getSelection().getCount(),
            len(stringsToFind))
        #oSels = self.unoObjs.controller.getSelection()
        #for oSls in (selsFound, oSels):
        #    print("selection: ")
        #    for oSel in iteruno.byIndex(oSls):
        #        print("%d," % len(oSel.getString()), end="")
        #    print()
        #return
        if ctrlName == "optScopeCharStyle":
            oVC.setPropertyValue("CharStyleName", CHARSTYLE_FROM)
            oVC.goRight(0, False)  # deselect

    def test5_targetFont(self):
        """Test target font and size, do not change font, changing without
        applying style, applying a paragraph style and changing its font.
        """
        Test5Data = collections.namedtuple('Test5Data', [
            'fontType', 'type_ctrl', 'testChar'])
        dataSets = [
            Test5Data("Western", "optTargetFontWestern", "a"),
            # Tamil letter Ma
            Test5Data("Complex", "optTargetFontComplex", "\u0bae"),
            # a Chinese character
            Test5Data("Asian", "optTargetFontAsian", "\ua000")]
        for dataSet in dataSets:
            if dataSet != dataSets[0]:
                # Get a fresh document.
                self.unoObjs = testutil.unoObjsForCurrentDoc()
                self.dlg = DlgDataConversion(self.unoObjs)
            for ctrlName in ("optTargetNoChange", "optTargetFontOnly",
                             "optTargetParaStyle"):
                self._test5_do_dataSet(dataSet, ctrlName)

    def _test5_do_dataSet(self, data, ctrlName):
        CHANGED_SIZE = 15.5
        PARASTYLE_FROM = "Heading 5"  # source para style
        PARASTYLE_TO = "Heading 4"  # target para style
        styleFonts = styles.StyleFonts(self.unoObjs)
        #print("%s %s" % (data.fontType, ctrlName))
        fontName, dummy = styleFonts.getFontOfStyle(
            styleName=PARASTYLE_TO, fontType=data.fontType)
        paragraphs = [("Begin",), (data.testChar,), ("End",), ]
        self.setTextContent(paragraphs, True)
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        oVC.goDown(1, False)
        oVC.setPropertyValue("ParaStyleName", PARASTYLE_FROM)

        def useDialog(innerSelf):
            innerSelf.evtHandler.actionPerformed(MyActionEvent("NoConverter"))
            innerSelf.dlgCtrls.optScopeParaStyle.setState(1)
            innerSelf.dlgCtrls.comboScopeParaStyle.setText(PARASTYLE_FROM)
            innerSelf.dlgCtrls.comboTargetParaStyle.setText(PARASTYLE_TO)
            getattr(innerSelf.dlgCtrls, data.type_ctrl).setState(1)
            innerSelf.dlgCtrls.listTargetStyleFont.selectItem(
                CHANGED_FONT[fontName], True)
            innerSelf.dlgCtrls.txtFontSize.setText(str(CHANGED_SIZE))
            getattr(innerSelf.dlgCtrls, ctrlName).setState(1)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("Close_and_Convert"))

        self.runDlg(useDialog)
        oVC.gotoStart(False)
        self._test5_check_dataSet(data, paragraphs, ctrlName, fontName)

    def _test5_check_dataSet(self, data, paragraphs, ctrlName, fontName):
        CHANGED_SIZE = 15.5
        CONVERT_PARA = 1  # we change only the second paragraph
        PARASTYLE_TO = "Heading 4"  # target para style
        oVC = self.unoObjs.viewcursor
        for para_index in range(0, len(paragraphs)):
            paraStyle2 = oVC.getPropertyValue("ParaStyleName")
            fontName2, fontSize2 = self._get_target_font(
                paraStyle2, data, ctrlName)
            if ctrlName == "optTargetNoChange" or para_index != CONVERT_PARA:
                self.assertNotEqual(paraStyle2, PARASTYLE_TO)
                self.assertNotEqual(fontName2, CHANGED_FONT[fontName])
                self.assertNotEqual(fontSize2, CHANGED_SIZE)
            elif ctrlName == "optTargetFontOnly":
                self.assertNotEqual(paraStyle2, PARASTYLE_TO)
                self.assertEqual(fontName2, CHANGED_FONT[fontName])
                self.assertEqual(fontSize2, CHANGED_SIZE)
            elif ctrlName == "optTargetParaStyle":
                self.assertEqual(paraStyle2, PARASTYLE_TO)
                self.assertEqual(fontName2, CHANGED_FONT[fontName])
                self.assertEqual(fontSize2, CHANGED_SIZE)
            oVC.goDown(1, False)

    def _get_target_font(self, paraStyle2, data, ctrlName):
        styleFonts = styles.StyleFonts(self.unoObjs)
        if ctrlName == "optTargetParaStyle":
            fontName2, fontSizeObj = styleFonts.getFontOfStyle(
                styleName=paraStyle2, fontType=data.fontType)
            fontSize2 = fontSizeObj.size
        else:
            propSuffix = data.fontType
            if propSuffix == 'Western':
                propSuffix = ""
            oVC = self.unoObjs.viewcursor
            fontName2 = oVC.getPropertyValue('CharFontName' + propSuffix)
            fontSize2 = oVC.getPropertyValue('CharHeight' + propSuffix)
        return fontName2, fontSize2

    def test6_encTypes(self):
        """Test different font encoding types."""
        # These fonts do not need to be present on your system.
        # Really we are only concerned with the encoding,
        # although the font is useful for viewing the data manually.
        Test6Data = collections.namedtuple('Test6Data', [
            'convName', 'fromFont', 'fromText', 'toFont', 'toText'])
        dataSets = [
            # Symbol type fonts - IPA (English language)
            Test6Data(
                "SAGIPA2Uni.tec",
                "SILDoulos IPA93", "mAi nejm Iz dZIm",
                "Doulos SIL", "m\u0251i nejm \u026az d\u0292\u026am"),
            # "Annapurna" type fonts - Devanagari (Hindi language)
            Test6Data(
                "Annapurna.tec",
                "Annapurna", "\xa7\xfa\xe0 \xe8k\xa7 \xcc\xf3\xdf|",
                "Mangal", "\u092e\u0948\u0902 \u091c\u093f\u092e \u0939"
                "\u0942\u0901\u0964"),
            # Unicode to Unicode - Tamil to Malayalam script (Tamil language)
            Test6Data(
                "MalUniToTam.tec",
                "Latha", "\u0b87\u0b9f\u0bc1 \u0ba8\u0bb2\u0bcd\u0bb2"
                "\u0b9f\u0bc1 \u0b87\u0bb2\u0bcd\u0bb2\u0bc6.",
                "Kartika", "\u0d07\u0d21\u0d4d \u0d28\u0d32\u0d4d\u0d32"
                "\u0d21\u0d4d \u0d07\u0d32\u0d4d\u0d32\u0d46."),
            ]
        for dataSet in dataSets:
            self._test6_do_dataSet(dataSet)

    def _test6_do_dataSet(self, data):
        self.addConverter(data.convName)
        self.setTextContent(data.fromText)

        def useDialog(innerSelf):
            innerSelf.dlgCtrls.txtConverterName.setText(data.convName)
            if data.fromFont == "Latha" and data.toFont == "Kartika":
                innerSelf.dlgCtrls.chkDirectionReverse.setState(True)
            innerSelf.dlgCtrls.optScopeWholeDoc.setState(True)
            innerSelf.evtHandler.actionPerformed(
                MyActionEvent("Close_and_Convert"))

        self.runDlg(useDialog)
        self.verifyTextContent(data.toText)

    def setTextContent(self, textContent, paragraphs=False):
        """Either set paragraphs to true and pass a list of paragraphs as
        the first parameter,
        or pass a string as the first parameter.
        """
        oVC = self.unoObjs.viewcursor
        if paragraphs:
            textParagraphs = textContent
            #oVC.gotoRange(self.unoObjs.text.getStart(), False)
            #oVC.gotoRange(self.unoObjs.text.getEnd(), True)  # select
            oVC.gotoStart(False)
            oVC.gotoEnd(True)  # select
            oVC.setString("")
            for textPara in textParagraphs:
                oText = self.unoObjs.text
                for textSplit in textPara:
                    oText.getText().insertString(oVC, textSplit, False)
                oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        else:
            oVC = self.unoObjs.viewcursor
            oVC.gotoStart(False)
            oVC.gotoEnd(True)
            oVC.setString(textContent)

    def addConverter(self, convName):
        addConverter(convName, self.dlg.msgbox, self.dlg.userVars)

    def verifyTextContent(self, textExpected):
        oVC = self.unoObjs.viewcursor
        oVC.gotoStart(False)
        oVC.gotoEnd(True)
        textContent = oVC.getString().strip()
        #print("[%s] cmp [%s]" % (dumpUnicodeString(textContent),
        #                         dumpUnicodeString(textExpected)))
        self.assertEqual(textContent, textExpected)

    #def tearDown(self):
        #unoObjs = testutil.unoObjsForCurrentDoc()
        #testutil.blankWriterDoc(unoObjs)


def addConverter(convName, msgbox, userVars):
    """Add an ICU translterator converter.
    :param convName: name of ICU transliterator or filename of TECkit map
    """
    if convName in addedConverters:
        # Converter has already been added.
        return
    convType = ConvType.Unicode_to_from_Unicode
    if convName == "Annapurna.tec" or convName == "SAGIPA2Uni.tec":
        convType = ConvType.Legacy_to_from_Unicode
    processFlags = ProcessTypeFlags.UnicodeEncodingConversion
    convSpec = convName
    if ".tec" in convSpec or ".map" in convSpec:
        convSpec = os.path.join(util.TESTDATA_FOLDER, convSpec)
    if convName in ("Any-Upper", "Any-Lower", "Any-Hex"):
        processFlags = ProcessTypeFlags.ICUTransliteration
    sec_call = sec_wrapper.SEC_wrapper(msgbox, userVars)
    sec_call.addConverter(
        convName, convSpec, convType,
        "", "", processFlags)
    addedConverters.add(convName)


FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.'
                  for x in range(256)])

def dumpUnicodeString(src, length=8):
    """Dump unicode string to formatted hex output.
    From Jack Trainor 2008, ActiveState recipe 572181.
    """
    result = []
    for i in range(0, len(src), length):
        unichars = src[i:i+length]
        hexval = ' '.join(["%04x" % ord(x) for x in unichars])
        result.append(str(hexval))
    return ''.join(result)

def anyToHex(inChar):
    """Return what ICU Any-Hex should give."""
    return "\\u%s" % dumpUnicodeString(inChar).upper()


if __name__ == '__main__':
    testutil.run_suite(getSuite())
