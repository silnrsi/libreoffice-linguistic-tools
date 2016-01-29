# -*- coding: Latin-1 -*-
#
# This file created October 23, 2010 by Jim Kornelsen
#
# 23-Apr-13 JDK  Fix complaint about no handler for logging.
# 27-Apr-13 JDK  Make sure a writer doc is open.
# 13-May-13 JDK  Allow component context from argument as well as socket.
# 15-Sep-15 JDK  Output file encoded for unicode.
# 28-Sep-15 JDK  Load tests from modules rather than classes.

"""
This file runs a suite of automated tests all together.
Otherwise you can run each test individually from its file.

See README_testing.txt for instructions to run this code.
"""
import os
import unittest
# pylint: disable=import-error
import uno
# pylint: enable=import-error

from lingttest.utils import testutil

from lingttest.access import ex_updater_test
from lingttest.access import search_test
from lingttest.access import tables_test
from lingttest.access import textchanges_test
from lingttest.access import uservars_test
from lingttest.access import xml_readers_test
from lingttest.app import spellingchecks_test
from lingttest.app import visual_test_grammar
from lingttest.app import visual_test_phonology
from lingttest.topdown import abbrevs_test
from lingttest.topdown import dataconv_test
from lingttest.topdown import grammar_test
from lingttest.topdown import phonology_test
from lingttest.topdown import step_through_list
from lingttest.ui import dlg_dataconv_test
from lingttest.ui import dlg_gramsettings_test
from lingttest.ui import messagebox_test
from lingttest.ui import wordlistfile_test

from lingt.utils import util

def runTests(outputToFile=False):

    ## Make sure a writer document is open

    ctx = testutil.stored.getContext()
    unoObjs = util.UnoObjs(ctx, loadDocObjs=False)
    if len(unoObjs.getOpenDocs()) == 0:
        unoObjs.desktop.loadComponentFromURL(
            "private:factory/swriter", "_blank", 0, ())

    ## Load and run the test suite

    masterSuite = unittest.TestSuite()
    for moduleSuite in (
            ex_updater_test.getSuite(),
            tables_test.getSuite(),
            search_test.getSuite(),
            textchanges_test.getSuite(),
            uservars_test.getSuite(),
            xml_readers_test.getSuite(),

            spellingchecks_test.getSuite(),
            #convpool_test.getSuite(),

            messagebox_test.getSuite(),
            dlg_gramsettings_test.getSuite(),
            dlg_dataconv_test.getSuite(),
            wordlistfile_test.getSuite(),

            abbrevs_test.getSuite(),
            phonology_test.getSuite(),
            grammar_test.getSuite(),
            dataconv_test.getSuite(),
            step_through_list.getSuite(),
        ):
        masterSuite.addTest(moduleSuite)
    # Uncomment to run only this test.
    #masterSuite = visual_test_phonology.getSuite()

    if outputToFile:
        outfilepath = os.path.join(util.BASE_FOLDER, "testResults.txt")
        #outfile = io.open(outfilepath, mode='w', encoding='UTF8')
        #outfile.write(u"Calling TextTestRunner...\n")
        outfile = open(outfilepath, mode='w')
        outfile.write("Calling TextTestRunner...\n")
        outfile.flush()
        unittest.TextTestRunner(stream=outfile, verbosity=2).run(masterSuite)
        outfile.close()
    else:
        unittest.TextTestRunner(verbosity=2).run(masterSuite)

    unoObjs = testutil.unoObjsForCurrentDoc()
    oVC = unoObjs.viewcursor
    oVC.gotoEnd(False)
    oVC.getText().insertString(oVC, "Testing finished.\n", False)

if __name__ == '__main__':
    testutil.stored.getContext()
    runTests()

def runTests_myMacros():
    testutil.stored.ctx = uno.getComponentContext()
    runTests(outputToFile=True)

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = runTests_myMacros,
