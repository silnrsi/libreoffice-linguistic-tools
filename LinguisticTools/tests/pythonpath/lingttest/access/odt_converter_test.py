"""
Reads and modifies content.xml and styles.xml.
"""
import os
import logging
import shutil
import unittest

from lingt.access.xml import odt_converter
from lingt.app.data.bulkconv_structs import ScopeType
from lingt.app.svc.bulkconversion import UniqueStyles
from lingt.utils import util

from lingttest.utils import testutil

logger = logging.getLogger("lingttest.odt_converter_test")

REPLACED_VAL = "__REPLACED_VAL__"

def getSuite():
    suite = unittest.TestSuite()
    suite.addTest(BulkReaderTestCase('testReader'))
    suite.addTest(BulkWriterTestCase('testWriter'))
    return suite

class BulkReaderTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.srcdir = os.path.join(util.TESTDATA_FOLDER, "all_scope_types")

    def read_files(self, scopeType):
        reader = odt_converter.OdtReader(self.srcdir, scopeType, self.unoObjs)
        return reader.read()

    def testReader(self):
        dataSets = [
            (ScopeType.PARASTYLE, 4),
            (ScopeType.CHARSTYLE, 3),
            (ScopeType.FONT_WITH_STYLE, 9),
            (ScopeType.FONT_WITHOUT_STYLE, 4),
            (ScopeType.WHOLE_DOC, 1),
            ]
        for scopeType, num_expected in dataSets:
            processingStylesFound = self.read_files(scopeType)
            self.assertEqual(
                len(processingStylesFound), num_expected,
                msg=ScopeType.TO_STRING[scopeType])

class BulkWriterTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.outdir = testutil.output_path("all_scope_types")

    def _setUp_dataset(self):
        if os.path.exists(self.outdir):
            for f in os.listdir(self.outdir):
                os.remove(os.path.join(self.outdir, f))
                #logger.debug("Removed " + repr(f))
        else:
            os.makedirs(self.outdir)
        srcdir = os.path.join(util.TESTDATA_FOLDER, "all_scope_types")
        for filename in ("content.xml", "styles.xml"):
            shutil.copy(os.path.join(srcdir, filename), self.outdir)

    def testWriter(self):
        dataSets = [
            (ScopeType.PARASTYLE, "Heading 3", 1),
            (ScopeType.PARASTYLE, "My Heading Style", 1),
            (ScopeType.PARASTYLE, "Preformatted Text", 1),
            (ScopeType.PARASTYLE, "My Preformatted Text", 1),
            (ScopeType.CHARSTYLE, "Emphasis", 1),
            (ScopeType.CHARSTYLE, "My Emphasis", 1),
            (ScopeType.CHARSTYLE, "Source Text", 1),
            (ScopeType.FONT_WITH_STYLE, "DejaVu Sans", 1),
            (ScopeType.FONT_WITHOUT_STYLE, "DejaVu Sans", 1),
            (ScopeType.FONT_WITH_STYLE, "Verdana", 0),
            (ScopeType.FONT_WITHOUT_STYLE, "Verdana", 1),
            (ScopeType.WHOLE_DOC, None, 9),
            ]
        for dataSet in dataSets:
            self._do_dataset(dataSet)

    def _do_dataset(self, dataSet):
        scopeType, style_to_find, num_expected = dataSet
        self._setUp_dataset()
        reader = odt_converter.OdtReader(self.outdir, scopeType, self.unoObjs)
        unique_styles = UniqueStyles(scopeType)
        unique_styles.add(reader.read())
        styleItems = unique_styles.get_values()
        styleChanges = getStyleChanges(styleItems, style_to_find)
        changer = odt_converter.OdtChanger(reader, styleChanges)
        changer.makeChanges()
        with open(os.path.join(self.outdir, "content.xml"), 'r',
                encoding="utf-8") as resultfile:
            count = resultfile.read().count(REPLACED_VAL)
        debug_msg = ScopeType.TO_STRING[scopeType] + "/" + str(style_to_find)
        self.assertEqual(count, num_expected, msg=debug_msg)

def getStyleChanges(styleItems, style_to_find):
    styleChanges = []
    for item in styleItems:
        if str(item) == style_to_find:
            getStyleChange(item, styleChanges)
    return styleChanges

def getStyleChange(item, styleChanges):
    item.create_change(None)
    for instr in item.inputData:
        item.change.converted_data[instr] = REPLACED_VAL
    styleChanges.append(item.change)

if __name__ == '__main__':
    testutil.run_suite(getSuite())
