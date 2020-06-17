#
# dialog_strings_read.py
#
# Created by Jim Kornelsen on June 16 2020

"""
This code deals with the files in LingToolsBasic.
Often the localized strings get messed up, and in any case they are sorted by
most recent changes first rather than just by dialog, so over time it becomes
hard to follow.

Grab all of the strings and put them in a tab-delimited file suitable for
managing in a spreadsheet. Also make new IDs sorted only by dialog id and
control id.
"""
from collections import namedtuple
import os
import re

FILEPATH = os.path.realpath(__file__)
CURRENT_DIR = os.path.dirname(FILEPATH)
INFOLDER_PATH = os.path.join(CURRENT_DIR, "../../LingToolsBasic")
OUTFILE = os.path.join(CURRENT_DIR, "dialog_strings.csv")

Strings = dict()  # values of type DialogString

def amp_strip(string_id):
    amp = "&amp;"
    if not string_id:
        return string_id
    if string_id.startswith(amp):
        string_id = string_id[len(amp):]
    return string_id

class DialogString:
    """Dialog string identifers and values."""
    def __init__(self, dialogID, stringID):
        self.dialogID = dialogID
        self.controlID = ""
        self.isTitle = False  # dialog titles do not have control IDs
        self.valueType = ''  # Value, HelpText, StringItemList
        self.string_id = amp_strip(stringID)
        self.new_string_id = ""
        self.string_num = 0
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

    def addToDict(self):
        #Strings[self.getKey()] = self
        Strings[self.string_id] = self
        #print("Added {} to Strings.".format(self.string_id))

    def set_langval(self, lang, val):
        if lang == 'en':
            self.english = val
        elif lang == 'es':
            self.spanish = val
        elif lang == 'fr':
            self.french = val

FileTuple = namedtuple('FileTuple', ['path', 'name'])

class FolderHandler:
    """Perform operations on all files in a folder."""
    def __init__(self):
        self.dialog_files = []
        self.strings_files = []

    def handle_folder(self):
        try:
            self.read_folder()
            self.handle_files()
        except (OSError, IOError):
            print("Couldn't open folder for reading: %s", INFOLDER_PATH)
            exit()

    def read_folder(self):
        for filename in os.listdir(INFOLDER_PATH):
            filepath = os.path.join(INFOLDER_PATH, filename)
            if os.path.isfile(filepath):
                filetuple = FileTuple(filepath, filename)
                if filename.endswith(".xdl"):
                    self.dialog_files.append(filetuple)
                elif filename.endswith(".properties"):
                    self.strings_files.append(filetuple)

    def handle_files(self):
        for filetuple in self.dialog_files:
            fileReader = DialogFileReader(filetuple)
            fileReader.read()
        for filetuple in self.strings_files:
            fileReader = StringsFileReader(filetuple)
            fileReader.read()

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
            print("Couldn't open file for reading: %s", self.filetuple.path)
            exit()

class DialogFileReader(FileReader):
    def __init__(self, filetuple):
        FileReader.__init__(self, filetuple)
        self.dialogID = ""
        self.parentString = None

    def parseLine(self):
        if self.searchLine(r'dlg:window.+dlg:id="(\w+)".+dlg:title="([^"]+)"'):
            self.dialogID, string_id = self.matchObj.groups()
            print("Dialog {}".format(self.dialogID))
            dlgString = DialogString(self.dialogID, string_id)
            dlgString.isTitle = True
            dlgString.addToDict()
        elif self.searchLine(r'dlg:id="(\w+)".+dlg:value="([^"]*)"'):
            controlID, string_id = self.matchObj.groups()
            dlgString = DialogString(self.dialogID, string_id)
            dlgString.controlID = controlID
            dlgString.valueType = 'Value'
            dlgString.addToDict()
        elif self.searchLine(r'dlg:(?:titledbox|menulist) dlg:id="(\w+)"'):
            controlID = self.matchObj.group(1)
            self.parentString = DialogString(self.dialogID, "")
            self.parentString.controlID = controlID
            self.parentString.string_id = self.parentString.getKey()
            self.parentString.addToDict()
        elif self.searchLine(r'dlg:title dlg:value="([^"]*)"'):
            string_id = self.matchObj.group(1)
            self.parentString.string_id = amp_strip(string_id)
            self.parentString.valueType = 'Value'
        elif self.searchLine(r'dlg:(?:title|menuitem) dlg:value="([^"]*)"'):
            string_id = self.matchObj.group(1)
            dlgString = DialogString(self.dialogID, string_id)
            dlgString.controlID = self.parentString.controlID
            dlgString.valueType = 'StringItemList'
            self.parentString.children.append(dlgString)
        if self.searchLine(r'dlg:id="(\w+)".+dlg:help-text="([^"]*)"'):
            controlID, string_id = self.matchObj.groups()
            if string_id:
                dlgString = DialogString(self.dialogID, string_id)
                dlgString.controlID = controlID
                dlgString.valueType = 'HelpText'
                dlgString.addToDict()

class StringsFileReader(FileReader):
    def __init__(self, filetuple):
        FileReader.__init__(self, filetuple)
        matchObj = re.search(
            r'DialogStrings_(\w\w)_\w\w.properties', filetuple.name)
        self.lang = matchObj.group(1)

    def parseLine(self):
        if self.searchLine(r'^(\d+\.[^=]+)=(.*)$'):
            string_id, text = self.matchObj.groups()
            if string_id in Strings:
                if text:
                    Strings[string_id].set_langval(self.lang, text)
            #else:
            #    print("{} not in Strings.".format(string_id))

def tabSpaces(numTabs):
    TABWIDTH = 4  # following PEP8 style guide
    numSpaces = TABWIDTH * numTabs
    return ' ' * numSpaces

class FileWriter:
    """Write results to file"""
    CTRL_NAMES_TO_SKIP = []

    def __init__(self):
        self.outfile = None
        self.strNum = 0

    def write(self):
        try:
            with open(OUTFILE, 'w') as self.outfile:
                self.write_data()
        except (OSError, IOError):
            print("Couldn't open file for writing: %s" % OUTFILE)
            exit()

    def write_data(self):
        sorted_strings = []
        for dialogString in Strings.values():
            #print(dialogString.getKey())
            sorted_strings.append(
                [dialogString.getKey(), dialogString])
        sorted_strings.sort()
        self.strNum = 0
        for dummy_key, dialogString in sorted_strings:
            self.write_string(dialogString)
            for child in dialogString.children:
                self.write_string(child)

    def write_string(self, dialogString):
        dialogString.string_num = self.strNum
        self.strNum += 1
        self.outfile.write("{}\t".format(dialogString.getNewID()))
        # may actually be EN string
        self.outfile.write("{}\t".format(dialogString.string_id))
        self.outfile.write("{}\t".format(dialogString.english))
        self.outfile.write("{}\t".format(dialogString.spanish))
        self.outfile.write("{}\n".format(dialogString.french))

if __name__ == "__main__":
    folderHandler = FolderHandler()
    folderHandler.handle_folder()
    FileWriter().write()
    print("Finished!")

