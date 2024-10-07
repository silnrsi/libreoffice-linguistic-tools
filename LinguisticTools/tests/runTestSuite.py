"""
Run a suite of automated tests, either all together or individually.
See build/README_build.txt for instructions.
"""
import os
import unittest
import uno  # pylint: disable=import-error

from lingttest.utils import testutil

from lingttest.access import ex_updater_test
from lingttest.access import odt_converter_test
from lingttest.access import search_test
from lingttest.access import tables_test
from lingttest.access import textchanges_test
from lingttest.access import uservars_test
from lingttest.access import xml_readers_test
from lingttest.app import convpool_test
from lingttest.app import fileitemlist_test
from lingttest.app import spellingchecks_test
from lingttest.app import visual_test_interlin
from lingttest.app import visual_test_phonology
from lingttest.app import wordlist_test
from lingttest.topdown import abbrevs_test
from lingttest.topdown import apply_conv_test
from lingttest.topdown import dataconv_test
from lingttest.topdown import interlin_test
from lingttest.topdown import phonology_test
from lingttest.topdown import step_through_list
from lingttest.ui import dlg_bulkstep1_test
from lingttest.ui import dlg_bulkstep2_test
from lingttest.ui import dlg_dataconv_test
from lingttest.ui import dlg_interlinsettings_test
from lingttest.ui import messagebox_test
from lingttest.ui import wordlistfile_test

from lingt.utils import util

def get_master_suite():
    masterSuite = unittest.TestSuite()
    for module in (
            ex_updater_test,
            tables_test,
            search_test,
            textchanges_test,
            uservars_test,
            xml_readers_test,

            fileitemlist_test,
            spellingchecks_test,
            convpool_test,

            messagebox_test,
            dlg_bulkstep1_test,
            dlg_interlinsettings_test,
            dlg_dataconv_test,
            wordlistfile_test,

            abbrevs_test,
            phonology_test,
            interlin_test,
            dataconv_test,
            step_through_list,
        ):
        masterSuite.addTest(module.getSuite())
    return masterSuite

def run_to_outfile(suite):
    run_suite(suite, True)

def run_to_stdout(suite):
    run_suite(suite, False)

def run_suite(suite, outputToFile):

    ## Make sure a writer document is open

    ctx = testutil.stored.getContext()
    unoObjs = util.UnoObjs(ctx, loadDocObjs=False)
    if len(unoObjs.getOpenDocs()) == 0:
        unoObjs.desktop.loadComponentFromURL(
            "private:factory/swriter", "_blank", 0, ())

    ## Load and run the suite

    if outputToFile:
        run_suite_to_outfile(suite)
    else:
        unittest.TextTestRunner(verbosity=2).run(suite)

    testutil.blankWriterDoc()
    unoObjs = testutil.unoObjsForCurrentDoc()
    oVC = unoObjs.viewcursor
    oVC.gotoEnd(False)
    testutil.restoreMsgboxDisplay()
    oVC.getText().insertString(oVC, "\nTesting finished.\n", False)

def run_suite_to_outfile(suite):
    outfilepath = os.path.join(util.BASE_FOLDER, "testResults.txt")
    with open(outfilepath, mode='w', encoding='UTF8') as outfile:
        outfile.write("Calling TextTestRunner...\n")
        outfile.flush()
        unittest.TextTestRunner(stream=outfile, verbosity=2).run(suite)
        outfile.write("\nFinished!\n")

if __name__ == '__main__':
    testutil.stored.getContext()
    run_to_stdout(get_master_suite())

def aaa_run_all_tests():
    testutil.stored.ctx = uno.getComponentContext()
    run_to_outfile(get_master_suite())

def run_module_suite(module):
    """Run tests from a single module only."""
    testutil.stored.ctx = uno.getComponentContext()
    run_to_outfile(module.getSuite())

def run_ex_updater_test():
    run_module_suite(ex_updater_test)

def run_odt_converter_test():
    run_module_suite(odt_converter_test)

def run_search_test():
    run_module_suite(search_test)

def run_tables_test():
    run_module_suite(tables_test)

def run_textchanges_test():
    run_module_suite(textchanges_test)

def run_uservars_test():
    run_module_suite(uservars_test)

def run_xml_readers_test():
    run_module_suite(xml_readers_test)

def run_fileitemlist_test():
    run_module_suite(fileitemlist_test)

def run_spellingchecks_test():
    run_module_suite(spellingchecks_test)

def run_convpool_test():
    run_module_suite(convpool_test)

def run_visual_test_interlin():
    run_module_suite(visual_test_interlin)

def run_visual_test_phonology():
    run_module_suite(visual_test_phonology)

def run_wordlist_test():
    run_module_suite(wordlist_test)

def run_abbrevs_test():
    run_module_suite(abbrevs_test)

def run_apply_conv_test():
    run_module_suite(apply_conv_test)

def run_dataconv_test():
    run_module_suite(dataconv_test)

def run_interlin_test():
    run_module_suite(interlin_test)

def run_phonology_test():
    run_module_suite(phonology_test)

def run_step_through_list():
    run_module_suite(step_through_list)

def run_dlg_bulkstep1_test():
    run_module_suite(dlg_bulkstep1_test)

def run_dlg_bulkstep2_test():
    run_module_suite(dlg_bulkstep2_test)

def run_dlg_dataconv_test():
    run_module_suite(dlg_dataconv_test)

def run_dlg_interlinsettings_test():
    run_module_suite(dlg_interlinsettings_test)

def run_messagebox_test():
    run_module_suite(messagebox_test)

def run_wordlistfile_test():
    run_module_suite(wordlistfile_test)

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (
    aaa_run_all_tests,
    run_ex_updater_test,
    run_odt_converter_test,
    run_search_test,
    run_tables_test,
    run_textchanges_test,
    run_uservars_test,
    run_xml_readers_test,
    run_fileitemlist_test,
    run_spellingchecks_test,
    run_convpool_test,
    run_visual_test_interlin,
    run_visual_test_phonology,
    run_wordlist_test,
    run_abbrevs_test,
    run_apply_conv_test,
    run_dataconv_test,
    run_interlin_test,
    run_phonology_test,
    run_step_through_list,
    run_dlg_bulkstep1_test,
    run_dlg_bulkstep2_test,
    run_dlg_dataconv_test,
    run_dlg_interlinsettings_test,
    run_messagebox_test,
    run_wordlistfile_test,
    )
