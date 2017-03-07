# -*- coding: Latin-1 -*-
#
# This file created December 29, 2015 by Jim Kornelsen

# pylint: disable=protected-access

"""
Test using multiple SEC calls.
In most of OOLT there is a one to one correspondence between calls and
components, but bulk conversion requires more than one call.
Make sure converters get removed from the pool if no longer used.

Tests ConvPool and Samples.  Also tests BulkConversion.convert_vals().
"""
from __future__ import unicode_literals
import logging
import platform
import unittest

from lingttest.utils import testutil
from lingttest.topdown import dataconv_test

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.sec_wrapper import SEC_wrapper
from lingt.access.writer.uservars import UserVars
from lingt.app.svc.bulkconversion import ConvPool
from lingt.ui.common.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingttest.convpool_test")
CONV_NAME = "capsTest.tec"


def getSuite():
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_single',
            'test2_double',
        ):
        suite.addTest(ConvPoolTestCase(method_name))
    return suite


class SelectSettingsCache:
    """A cache to hold settings for selecting a converter.
    Change this before using funcSelectConverter via selectConverter().
    """
    converter = None

def funcSelectConverter(convName, forward, normForm):
    """Set test values instead of asking the user to select a converter."""
    converter = SelectSettingsCache.converter
    if platform.system() == "Windows":
        convName.value = converter.convName
    else:
        convName.value = converter.convName.encode("utf-8")
    forward._obj.value = converter.forward
    normForm._obj.value = converter.normForm
    STATUS_OK = 0
    return STATUS_OK

def loadLibrary(self):
    self.loadLibrary0()
    self.funcSelectConverter = funcSelectConverter

# Modify SEC_wrapper class to use an alternative funcSelectConverter.
SEC_wrapper.loadLibrary0 = SEC_wrapper.loadLibrary
SEC_wrapper.loadLibrary = loadLibrary


class ConvPoolTestCase(unittest.TestCase):
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
        USERVAR_PREFIX = 'LTbc_'  # LinguisticTools Bulk Conversion vars
        self.userVars = UserVars(USERVAR_PREFIX, self.unoObjs.document, logger)
        self.msgbox = MessageBox(self.unoObjs)

    def test1_single(self):
        """Test a single converter in the pool."""
        self.addConverter(CONV_NAME)
        inputStr = "abCde"
        convPool = ConvPool(self.userVars, self.msgbox)
        conv_settings = ConverterSettings(self.userVars)
        conv_settings.convName = CONV_NAME
        conv_settings.forward = True
        SelectSettingsCache.converter = conv_settings
        dummy_fontChange = convPool.selectConverter(conv_settings)
        sec_call = convPool[CONV_NAME]
        convertedVal = sec_call.convert(inputStr)
        self.assertEqual(convertedVal, "ABCDE")
        self.assertEqual(len(convPool._secCallObjs), 1)

        conv_settings = ConverterSettings(self.userVars)
        conv_settings.convName = CONV_NAME
        conv_settings.forward = False
        sec_call = convPool.loadConverter(conv_settings)
        convertedVal = sec_call.convert(inputStr)
        self.assertEqual(convertedVal, "abcde")
        self.assertEqual(len(convPool._secCallObjs), 1)

        with self.assertRaises(KeyError):
            sec_call = convPool["doesn't exist"]


    def test2_double(self):
        """Test two converters in the pool."""
        self.addConverter(CONV_NAME)
        inputStr = "abCde"
        convPool = ConvPool(self.userVars, self.msgbox)
        conv_settings1 = ConverterSettings(self.userVars)
        conv_settings1.convName = CONV_NAME
        conv_settings1.forward = False
        SelectSettingsCache.converter = conv_settings1
        # This calls our modified funcSelectConverter() above,
        # which tells the ConvPool what EncConverters actually
        # contains after test1_single().
        dummy_fontChange = convPool.selectConverter(conv_settings1)

        conv_settings1 = ConverterSettings(self.userVars)
        conv_settings1.convName = CONV_NAME
        conv_settings1.forward = True
        sec_call1 = convPool.loadConverter(conv_settings1)
        convertedVal = sec_call1.convert(inputStr)
        self.assertEqual(convertedVal, "ABCDE")

        CONV_NAME2 = "Any-Lower"
        self.addConverter(CONV_NAME2)
        conv_settings2 = ConverterSettings(self.userVars)
        conv_settings2.convName = CONV_NAME2
        with self.assertRaises(KeyError):
            sec_call2 = convPool[CONV_NAME2]
        convPool.loadConverter(conv_settings2)
        sec_call2 = convPool[CONV_NAME2]
        convertedVal = sec_call2.convert(inputStr)
        self.assertEqual(convertedVal, "abcde")
        self.assertEqual(len(convPool._secCallObjs), 2)
        self.assertEqual(sec_call1.convert("f"), "F")
        self.assertEqual(sec_call2.convert("G"), "g")

    def addConverter(self, convName):
        dataconv_test.addConverter(
            convName, self.msgbox, self.userVars)

    def tearDown(self):
        unoObjs = testutil.unoObjsForCurrentDoc()
        testutil.blankWriterDoc(unoObjs)


if __name__ == '__main__':
    testutil.run_suite(getSuite())
