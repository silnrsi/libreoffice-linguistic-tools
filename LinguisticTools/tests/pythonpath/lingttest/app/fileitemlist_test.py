# -*- coding: Latin-1 -*-
#
# This file created May 25, 2016 by Jim Kornelsen

"""
Verify that lists can add and remove items and stay the correct size.
Check that user vars get stored using mock objects.
"""
from __future__ import unicode_literals
import logging
import unittest
from unittest import mock

from lingttest.utils import testutil

from lingt.access.writer.uservars import UserVars
from lingt.app.data import fileitemlist
from lingt.app import exceptions
from lingt.ui.common.messagebox import MessageBox

logger = logging.getLogger("lingttest.fileitemlist_test")


def getSuite():
    testutil.modifyMsgboxDisplay()
    suite = unittest.TestSuite()
    for method_name in (
            'test1_item_types',
            'test2_empty_list',
            'test3_add_items',
            'test4_uservars',
        ):
        suite.addTest(FileItemListTestCase(method_name))
    return suite


class FileItemListTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.unoObjs = None
        self.dlg = None

    def setUp(self):
        self.unoObjs = testutil.unoObjsForCurrentDoc()
        self.msgbox = MessageBox(self.unoObjs)

    def test1_item_types(self):
        userVars = mock.Mock()
        dummy_item = fileitemlist.BulkFileItem(userVars)
        dummy_item = fileitemlist.WordListFileItem(userVars)
        dummy_item = fileitemlist.LingExFileItem(userVars)

    def test2_empty_list(self):
        USERVAR_PREFIX = 'LTbc_'  # LinguisticTools Bulk Conversion vars
        userVars = UserVars(USERVAR_PREFIX, self.unoObjs.document, logger)
        itemlist = fileitemlist.FileItemList(
            fileitemlist.BulkFileItem, userVars)
        self.assertEqual(len(itemlist), 0)
        with self.assertRaises(IndexError):
            dummy = itemlist[0]
        self.assertEqual(itemlist.getItemTextList(), [])
        itemlist.sortItems()
        item = itemlist.makeNewItem()
        item.filepath = "a.txt"
        with self.assertRaises(exceptions.ChoiceProblem) as cm:
            itemlist.updateItem(0, item)
        self.assertEqual(cm.exception.msg, "Please select a file in the list.")

    def test3_add_items(self):
        USERVAR_PREFIX = 'LTbc_'  # LinguisticTools Bulk Conversion vars
        userVars = UserVars(USERVAR_PREFIX, self.unoObjs.document, logger)
        itemlist = fileitemlist.FileItemList(
            fileitemlist.BulkFileItem, userVars)
        item = add_new_item(itemlist, "a.txt")
        self.assertEqual(len(itemlist), 1)
        itemdup = itemlist.makeNewItem()
        itemdup.filepath = item.filepath
        with self.assertRaises(exceptions.ChoiceProblem) as cm:
            itemlist.addItem(itemdup)
        self.assertEqual(cm.exception.msg, "File is already in the list.")
        self.assertEqual(len(itemlist), 1)
        itemlist.addItem(itemdup, allowDuplicates=True)
        self.assertEqual(len(itemlist), 2)
        add_new_item(itemlist, "b.txt")
        self.assertEqual(len(itemlist), 3)
        item = itemlist.makeNewItem()
        item.filepath = "a.txt"
        self.assertTrue(itemlist.alreadyContains(item))
        item = itemlist.makeNewItem()
        item.filepath = "b.txt"
        self.assertTrue(itemlist.alreadyContains(item, excludeItemPos=1))
        self.assertFalse(itemlist.alreadyContains(item, excludeItemPos=2))
        add_new_item(itemlist, "d.txt")
        add_new_item(itemlist, "c.txt")
        self.assertEqual(len(itemlist), 5)
        self.assertEqual(itemlist[-2].filepath, "c.txt")
        self.assertEqual(itemlist[-1].filepath, "d.txt")
        item = itemlist.makeNewItem()
        item.filepath = "e.txt"
        itemlist.updateItem(-1, item)
        self.assertEqual(len(itemlist), 5)
        self.assertEqual(itemlist[-1].filepath, "e.txt")
        itemlist.deleteItem(-1)
        self.assertEqual(len(itemlist), 4)
        self.assertEqual(itemlist[-1].filepath, "c.txt")

    def test4_uservars(self):
        USERVAR_PREFIX = 'LTbc_'  # LinguisticTools Bulk Conversion vars
        userVars = UserVars(USERVAR_PREFIX, self.unoObjs.document, logger)
        itemlist = fileitemlist.FileItemList(
            fileitemlist.BulkFileItem, userVars)
        add_new_item(itemlist, "a.txt")
        add_new_item(itemlist, "b.txt")
        add_new_item(itemlist, "c.txt")
        mock_store = mock.Mock()
        #mock_store.return_value = None
        with mock.patch.object(userVars, 'store', mock_store):
            itemlist.storeUserVars()
        expected = [
            mock.call("infile_count", "3"),
            mock.call("infile00_path", "a.txt"),
            mock.call("infile01_path", "b.txt"),
            mock.call("infile02_path", "c.txt"),
            ]
        logger.debug(mock_store.call_args_list)
        self.assertEqual(mock_store.call_args_list, expected)

        def mock_get_side_effect(varname):
            values = {
                "infile_count" : "3",
                "infile00_path" : "a.txt",
                "infile01_path" : "b.txt",
                "infile02_path" : "c.txt",
                }
            return values[varname]

        itemlist = fileitemlist.FileItemList(
            fileitemlist.BulkFileItem, userVars)
        mock_get = mock.Mock()
        mock_get.side_effect = mock_get_side_effect
        with mock.patch.object(userVars, 'get', mock_get):
            itemlist.loadUserVars()
        self.assertEqual(len(itemlist), 3)
        self.assertEqual(
            itemlist.getItemTextList(), [
                "a.txt",
                "b.txt",
                "c.txt"])


def add_new_item(itemlist, filepath):
    item = itemlist.makeNewItem()
    item.filepath = filepath
    itemlist.addItem(item)
    return item


if __name__ == '__main__':
    testutil.run_suite(getSuite())

