#
# dialog_strings_update.py
#
# Created by Jim Kornelsen on June 16 2020

"""
First run dialog_strings_read.py to create dialog_strings.csv.
This code reads the CSV file and makes a new LingToolsBasic with the changes.
"""
from collections import namedtuple
import os
import pathlib
import re

FILEPATH = os.path.realpath(__file__)
CURRENT_DIR = os.path.dirname(FILEPATH)
INFOLDER = os.path.join(CURRENT_DIR, "../../LingToolsBasic")
OUTFOLDER = os.path.join(CURRENT_DIR, "LingToolsBasic_new")
INFILE = os.path.join(CURRENT_DIR, "dialog_strings.csv")

Strings = dict()  # values of type DialogString
ItemLists = dict()  # for valtype StringItemList
AMP = "&amp;"

def amp_strip(string_id):
    if not string_id:
        return string_id
    if string_id.startswith(AMP):
        string_id = string_id[len(AMP):]
    return string_id

class DialogString:
    """Dialog string identifers and values."""
    def __init__(self, dialogID, stringID=""):
        self.dialogID = dialogID
        self.controlID = ""
        self.isTitle = False  # dialog titles do not have control IDs
        self.valueType = ''  # Value, HelpText, StringItemList
        self.string_id = amp_strip(stringID)
        self.string_num = None
        self.english = ""
        self.spanish = ""
        self.french = ""
        self.children = list()

    def getKey(self):
        """Uniquely identify this string.
        This key is also useful for finding and sorting."""
        if self.isTitle:
            return "{}.Title".format(self.dialogID)
        valueType = self.valueType
        if not valueType:
            return "{}.{}".format(self.dialogID, self.controlID)
        if valueType not in ('Value', 'HelpText', 'StringItemList'):
            valueType = 'Value'
        return "{}.{}.{}".format(self.dialogID, self.controlID, valueType)

    def getNewID(self):
        return "{}.{}".format(self.string_num, self.getKey())

    def addToDict(self, aDict=None):
        if not aDict:
            aDict = Strings
        aDict[self.getKey()] = self

    def set_langval(self, lang, val):
        if lang == 'en':
            self.english = val
        elif lang == 'es':
            self.spanish = val
        elif lang == 'fr':
            self.french = val

    def get_langval(self, lang):
        if lang == 'en':
            return self.english
        elif lang == 'es':
            return self.spanish
        elif lang == 'fr':
            return self.french

FileTuple = namedtuple('FileTuple', ['path', 'name'])

class FolderHandler:
    """Perform operations on all files in a folder."""
    def __init__(self):
        self.dialog_files = []

    def handle_folder(self):
        try:
            self.read_folder()
            self.handle_files()
        except (OSError, IOError):
            raise IOError("Couldn't open folder for reading: {}".format(
                INFOLDER))

    def read_folder(self):
        for filename in os.listdir(INFOLDER):
            filepath = os.path.join(INFOLDER, filename)
            if os.path.isfile(filepath):
                filetuple = FileTuple(filepath, filename)
                if filename.endswith(".xdl"):
                    self.dialog_files.append(filetuple)

    def handle_files(self):
        for filetuple in self.dialog_files:
            fileChanger = DialogFileChanger(filetuple)
            fileChanger.change()

class LineSearcher:
    """Quick Perl-style pattern match of a line,
    to make a series of elif statements easier when parsing a file.
    """
    def __init__(self):
        self.matchObj = None
        self.line = ""

    def searchLine(self, pattern):
        """Sets self.matchObj"""
        self.matchObj = re.search(pattern, self.line)
        if self.matchObj:
            return True
        return False

class FileReader(LineSearcher):
    def __init__(self, filetuple):
        LineSearcher.__init__(self)
        self.filetuple = filetuple

    def read(self):
        try:
            with open(self.filetuple.path, 'r') as infile:
                for self.line in infile:
                    self.parseLine()
        except (OSError, IOError):
            raise IOError("Couldn't open file for reading: {}".format(
                self.filetuple.path))

class CSV_FileReader(FileReader):
    def __init__(self, filetuple):
        FileReader.__init__(self, filetuple)
        self.dialogID = ""
        self.parentString = None

    def parseLine(self):
        if self.searchLine(r'^(.*)\t(.*)\t(.*)\t(.*)\t(.*)$'):
            string_id, _, strEN, strES, strFR = self.matchObj.groups()
            matchObj = re.match(r'(\d+)\.(\w+)\.(\w+)(?:\.(\w+))?', string_id)
            if not matchObj:
                return
            strNum, dialogID, controlID, valtype = matchObj.groups()
            dlgString = DialogString(dialogID, string_id)
            if controlID == 'Title':
                dlgString.isTitle = True
            else:
                dlgString.controlID = controlID
            dlgString.valueType = valtype
            dlgString.string_num = strNum
            dlgString.english = strEN
            dlgString.spanish = strES
            dlgString.french = strFR
            if valtype == 'StringItemList':
                ds_search = DialogString(dialogID)
                ds_search.controlID = controlID
                key = ds_search.getKey()
                if key in ItemLists:
                    parentString = ItemLists[key]
                else:
                    parentString = ds_search
                    parentString.addToDict(ItemLists)
                parentString.children.append(dlgString)
            else:
                dlgString.addToDict()

class DialogFileChanger(FileReader):
    def __init__(self, filetuple):
        FileReader.__init__(self, filetuple)
        self.dialogID = ""
        self.parentString = None

    def change(self):
        outfile_path = os.path.join(OUTFOLDER, self.filetuple.name)
        try:
            with open(outfile_path, 'w') as self.outfile:
                self.read()
        except (OSError, IOError):
            raise IOError("Couldn't open file for reading: {}".format(
                outfile_path))

    def parseLine(self):
        if self.searchLine(r'dlg:window.+dlg:id="(\w+)"'):
            self.dialogID = self.matchObj.group(1)
            print("Reading Dialog {}".format(self.dialogID))
            ds_search = DialogString(self.dialogID)
            ds_search.isTitle = True
            dialogString = Strings[ds_search.getKey()]
            string_id_amp = "{}{}".format(AMP, dialogString.string_id)
            self.line = re.sub(
                r'(dlg:title=)"([^"]+)"',
                r'\1"{}"'.format(string_id_amp), self.line)
        elif self.searchLine(r'dlg:titledbox dlg:id="(\w+)"'):
            controlID = self.matchObj.group(1)
            dialogString = DialogString(self.dialogID)
            dialogString.controlID = controlID
            self.parentString = dialogString
        elif self.searchLine(r'dlg:title dlg:value="([^"]*)"'):
            ds_search = DialogString(self.dialogID)
            ds_search.controlID = self.parentString.controlID
            ds_search.valueType = 'Value'
            key = ds_search.getKey()
            if key in Strings:
                dialogString = Strings[key]
                string_id_amp = "{}{}".format(AMP, dialogString.string_id)
                self.line = re.sub(
                    r'(dlg:value=)"([^"]+)"',
                    r'\1"{}"'.format(string_id_amp), self.line)
        elif self.searchLine(r'dlg:menulist dlg:id="(\w+)"'):
            controlID = self.matchObj.group(1)
            ds_search = DialogString(self.dialogID)
            ds_search.controlID = controlID
            key = ds_search.getKey()
            if key in ItemLists:
                self.parentString = ItemLists[key]
        elif self.searchLine(r'dlg:menuitem dlg:value="([^"]*)"'):
            string_id = self.matchObj.group(1)
            try:
                dialogString = self.parentString.children.pop(0)
            except IndexError:
                raise IndexError("Empty list for {}".format(string_id)) 
            string_id_amp = "{}{}".format(AMP, dialogString.string_id)
            self.line = re.sub(
                r'(dlg:value=)"([^"]+)"',
                r'\1"{}"'.format(string_id_amp), self.line)
        elif self.searchLine(r'dlg:id="(\w+)".+dlg:value="([^"]*)"'):
            controlID, string_id = self.matchObj.groups()
            ds_search = DialogString(self.dialogID, string_id)
            ds_search.controlID = controlID
            ds_search.valueType = 'Value'
            key = ds_search.getKey()
            if key in Strings:
                dialogString = Strings[key]
                string_id_amp = "{}{}".format(AMP, dialogString.string_id)
                self.line = re.sub(
                    r'(dlg:value=)"([^"]+)"',
                    r'\1"{}"'.format(string_id_amp), self.line)
        if self.searchLine(r'dlg:id="(\w+)".+dlg:help-text="([^"]*)"'):
            controlID, string_id = self.matchObj.groups()
            ds_search = DialogString(self.dialogID, string_id)
            ds_search.controlID = controlID
            ds_search.valueType = 'HelpText'
            key = ds_search.getKey()
            if key in Strings:
                dialogString = Strings[key]
                string_id_amp = "{}{}".format(AMP, dialogString.string_id)
                self.line = re.sub(
                    r'(dlg:help-text=)"([^"]+)"',
                    r'\1"{}"'.format(string_id_amp), self.line)
        self.outfile.write("{}".format(self.line))


class FileWriter:
    """Write results to file"""
    def __init__(self):
        self.outfile = None
        self.lang = ""

    def write(self):
        langs = [
            ('en', 'US'),
            ('es', 'ES'),
            ('fr', 'FR')]
        for self.lang, locale in langs:
            filename = "DialogStrings_{}_{}.properties".format(
                self.lang, locale)
            outfilepath = os.path.join(OUTFOLDER, filename)
            try:
                with open(outfilepath, 'w') as self.outfile:
                    print("Writing {}".format(filename))
                    self.write_data()
            except (OSError, IOError):
                raise IOError("Couldn't open file for writing: {}".format(
                    outfilepath))

    def write_data(self):
        self.outfile.write("# Strings for Dialog Library LingToolsBasic\n")
        sorted_strings = []
        for dialogString in Strings.values():
            sorted_strings.append(
                [dialogString.getKey(), dialogString])
        for dialogString in ItemLists.values():
            sorted_strings.append(
                [dialogString.getKey(), dialogString])
        sorted_strings.sort()
        for dummy_key, dialogString in sorted_strings:
            self.write_string(dialogString)
            for child in dialogString.children:
                self.write_string(child)

    def write_string(self, dialogString):
        if dialogString.string_num is None:
            return
        self.outfile.write("{}={}\n".format(
            dialogString.string_id, dialogString.get_langval(self.lang)))

if __name__ == "__main__":
    filename = pathlib.Path(INFILE).name
    filetuple = FileTuple(INFILE, filename)
    fileReader = CSV_FileReader(filetuple)
    fileReader.read()
    pathlib.Path(OUTFOLDER).mkdir(exist_ok=True)
    folderHandler = FolderHandler()
    folderHandler.handle_folder()
    FileWriter().write()
    print("Finished!")

