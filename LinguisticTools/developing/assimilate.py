# -*- coding: Latin-1 -*-
#
# This file created August 3 2015 by Jim Kornelsen.
#
# 19-Aug-15 JDK  Verify filename case on Windows.
# 21-Aug-15 JDK  Make componentsWrapper.py showDlg() calls unique.
# 15-Sep-15 JDK  Handle commented code specified as 'assimilate'.
# 28-Sep-15 JDK  Added uniqueGetSuite().
# 20-Oct-15 JDK  Move __future__ imports before uno.
# 04-Nov-15 JDK  Added quiet option.
# 02-Feb-16 JDK  Use file's directory instead of a manually edited constant.

"""
Reads in python files and assimilates them into independent
files (i.e. no importing) that can be run from OpenOffice My Macros.

To assimilate main: python assimilate.py
To assimilate tests: python assimilate.py tests
For less verbose: python assimilate.py quiet

To run tests in python 2.6 and earlier (such as Apache OpenOffice 3.4 on
Windows) the unittest2 library is needed:
    cd C:/OurDocs/Programming/unittest2-0.5.1
    "C:/Program Files/OpenOffice.org 3/program/python.exe" setup.py install
Then assimilate tests like this:
    python assimilate.py tests unittest2

To remove ^M newlines using Vim :%s Ctrl+V Ctrl+M $//c
"""
from __future__ import unicode_literals
from collections import defaultdict, namedtuple
import io
import os
import platform
import glob
import re
import sys

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
BASEDIR = os.path.join(CURRENT_DIR, "../")
UNITTEST2 = False
#print("args: %r" % sys.argv)
if len(sys.argv) > 1 and sys.argv[1] == "tests":
    print("Assimilating tests")
    INFOLDER_PATH = BASEDIR + "tests/"
    if len(sys.argv) > 2 and sys.argv[2] == "unittest2":
        UNITTEST2 = True
else:
    print("Assimilating code")
    INFOLDER_PATH = BASEDIR + "pythonpath/lingt/ui/comp/"
VERBOSE = True
if "quiet" in sys.argv:
    VERBOSE = False

OUTFOLDER = BASEDIR + 'developing/assimilated_code/'
BASE_PACKAGE_PATHS = {
    "lingt" : BASEDIR + "pythonpath/lingt/",
    "grantjenks" : BASEDIR + "pythonpath/grantjenks/",
    "lingttest" : BASEDIR + "tests/pythonpath/lingttest/"}

#ENCODING = 'UTF8'
ENCODING = 'LATIN1'

FileTuple = namedtuple('FileTuple', ['path', 'name'])

def readFolder():
    for filename in os.listdir(INFOLDER_PATH):
        filepath = os.path.join(INFOLDER_PATH, filename)
        if os.path.isfile(filepath) and filename.endswith(".py"):
            exportedScriptsDecl = getExportedScripts(
                filepath, filename)
            if exportedScriptsDecl:
                toplevelFile = ToplevelFile(
                    FileTuple(filepath, filename), exportedScriptsDecl)
                toplevelFile.handleFile()

def getExportedScripts(filepath, filename):
    exportedScriptsDecl = ""
    try:
        with io.open(filepath, 'r', encoding=ENCODING) as infile:
            for line in infile:
                line = line.rstrip()
                if line.startswith("g_exportedScripts"):
                    exportedScriptsDecl = uniqueShowDlg(line, filename) + "\n"
                elif exportedScriptsDecl and line:
                    exportedScriptsDecl += uniqueShowDlg(line, filename) + "\n"
    except (OSError, IOError) as exc:
        # print to console and exit
        raise exc
    return exportedScriptsDecl

def getNextfile(importedModule):
    """
    Takes an imported module description and looks for the corresponding file.

    param importedModule: type ImportedModule
    return arg1: file path including file name
    return arg2: file name
    """
    packagePath = os.path.join(
        importedModule.basepath,
        re.sub(r"\.", "/", importedModule.package))
    nextFilepath = os.path.join(packagePath, importedModule.filename) + ".py"
    nextFilepath = re.sub(r"\\", r"/", nextFilepath)
    if not os.path.exists(nextFilepath):
        # importedModule.filename may specify a class rather than a module
        Warnings.add("%s may be a class." % importedModule)
        nextFilepath = packagePath + ".py"
    dummy_head, tail = os.path.split(nextFilepath)
    #print("getNextfile = (%s, %s)" % (nextFilepath, tail))
    return FileTuple(nextFilepath, tail)

class ToplevelFile:
    """Import all packages and modules needed for an exported function."""
    def __init__(self, filetuple, exportedScriptsDecl):
        self.filetuple = filetuple
        self.exportedScriptsDecl = exportedScriptsDecl
        self.filesContent = {}  # values are file contents (large string)
        self.fileDependencies = defaultdict(list)
        self.filesList = []  # elements are of type FileTuple
        self.importedPackages = set()

    def handleFile(self):
        if VERBOSE:
            print("Building %s" % self.filetuple.name)
        self.getNeededFiles(self.filetuple)
        try:
            outfilepath = OUTFOLDER + self.filetuple.name
            with io.open(outfilepath, 'w', encoding=ENCODING) as outfile:
                self.writeFile(outfile)
                if VERBOSE:
                    print("Finished building %s\n" % self.filetuple.name)
        except (OSError, IOError) as exc:
            # print to console and exit
            raise exc

    def getNeededFiles(self, filetuple, indentLevel=1):
        reader = FileReader(filetuple, self)
        reader.readFile(indentLevel)
        self.filesContent[filetuple.path] = reader.fileContents
        self.filesList.append(filetuple)
        for importedModule in reader.importedModules:
            nextFile = getNextfile(importedModule)
            self.fileDependencies[filetuple].append(nextFile)
            if nextFile.path not in self.filesContent:
                self.getNeededFiles(nextFile, indentLevel + 1)

    def writeFile(self, outfile):
        #outfile.write("#!/usr/bin/python\n# -*- coding: UTF8 -*-\n\n")
        outfile.write("#!/usr/bin/python\n# -*- coding: LATIN1 -*-\n\n")
        outfile.write("## Import modules that have to come first.\n\n")
        for importedPackage in sorted(self.importedPackages):
            if "__future__" in importedPackage:
                outfile.write(importedPackage + "\n")
                self.importedPackages.remove(importedPackage)
        if "import uno" in self.importedPackages:
            outfile.write("import uno\n")
            self.importedPackages.remove("import uno")
        outfile.write("\n")
        outfile.write("## Import other standard and 3rd party modules.\n\n")
        for importedPackage in sorted(self.importedPackages):
            outfile.write(importedPackage + "\n")
        outfile.write("\n")
        self.sortFilesByDependency()
        for filetuple in self.filesList:
            LINEWIDTH = 79  # from PEP guidelines
            outfile.write("#%s\n" % ('-' * (LINEWIDTH - 1)))
            outfile.write("# Start of %s\n" % filetuple.name)
            outfile.write("#%s\n\n" % ('-' * (LINEWIDTH - 1)))
            outfile.write(self.filesContent[filetuple.path])
            outfile.write("#%s\n" % ('-' * (LINEWIDTH - 1)))
            outfile.write("# End of %s\n" % filetuple.name)
            outfile.write("#%s\n\n" % ('-' * (LINEWIDTH - 1)))
        outfile.write("\n")
        outfile.write("# Exported Scripts:\n")
        outfile.write(self.exportedScriptsDecl)

    def sortFilesByDependency(self):
        """Sort files according to dependencies.
        Modifies self.filesList.
        """
        listSorted = []
        for filetuple in self.filesList:
            if filetuple not in listSorted:
                # Add it at the end.
                listSorted.append(filetuple)
            for dep in self.fileDependencies[filetuple]:
                moveBefore(listSorted, dep, filetuple)
        self.filesList = listSorted


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


def uniqueShowDlg(line, filename):
    """Make showDlg() calls unique.
    This is needed for componentsWrapper.py since it uses multiple modules.
    """
    if re.search(r"^def showDlg", line) or re.search(r"showDlg,", line):
        # component dialogs in lingt.ui.comp
        line = uniqueMember("showDlg", line, filename)
    else:
        # componentsWrapper.py
        line = re.sub(r"\((\w+)\.showDlg\)", r"(showDlg_\1)", line)
    return line

def uniqueGetSuite(line, filename):
    """Make getSuite() calls unique.
    This is needed for runTestSuite.py since it uses multiple modules.
    """
    if re.search(r"^def getSuite", line):
        # test classes
        line = uniqueMember("getSuite", line, filename)
    else:
        # runTestSuite.py
        line = re.sub(r"(\w+)\.getSuite\(\)", r"getSuite_\1()", line)
    return line

def uniqueMember(memberName, line, filename):
    """Rename a module level class, function or variable to be unique
    across modules.
    """
    moduleName = re.sub(r"\.py$", r"", filename)
    newName = "%s_%s" % (memberName, moduleName)
    return re.sub(memberName, newName, line)

class FileReader(LineSearcher):

    def __init__(self, filetuple, toplevel):
        LineSearcher.__init__(self)
        self.filetuple = filetuple
        self.toplevel = toplevel
        self.importedModules = []  # elements are of type ImportedModule
        self.referencedModules = []  # list of filenames
        self.inHeader = True
        self.inModuleDocstring = False
        self.inMain = False
        self.fileContents = ""  # modified contents of the entire file
        self.fileContentsList = []  # hopefully faster than mere concatenation

    def readFile(self, indentLevel):
        if VERBOSE:
            print(
                "%sIncluding %s" %
                (" " * 4 * indentLevel, self.filetuple.name))
            #print(
            #    "%sIncluding %s" %
            #    (" " * 4 * indentLevel, self.filetuple.path))
        try:
            verifyFileCase(self.filetuple.path)
            with io.open(self.filetuple.path, 'r',
                         encoding=ENCODING) as infile:
                for self.line in infile:
                    self.parseLine()
        except (OSError, IOError) as exc:
            # Print to console and exit.
            raise exc
        except StopIteration:
            # Finish reading file.
            pass
        #self.fileContents = r"\n".join(self.fileContentsList) + r"\n"
        self.fileContents = "\n".join(self.fileContentsList) + "\n"
        if UNITTEST2:
            self.fileContents = re.sub(
                r"unittest", r"unittest2", self.fileContents)

    def parseLine(self):
        self.line = self.line.rstrip()
        if self.line.startswith("import") or self.line.startswith("from"):
            self.parseImportModule()
        elif self.inHeader:
            if self.line == '"""':
                if self.inModuleDocstring:
                    self.inModuleDocstring = False
                    self.inHeader = False
                else:
                    self.inModuleDocstring = True
            elif (self.line.startswith("class") or self.line.startswith("def")
                  or self.line.startswith("try")):
                self.inHeader = False
                self.addFileContents()
            else:
                # Skip this line.
                return
        elif self.inMain:
            if len(self.line) < 4:
                self.inMain = False
                self.addFileContents()
            else:
                # Skip this line.
                return
        elif (re.search(r"__name__.+__main__", self.line)
              and self.filetuple != self.toplevel.filetuple):
            self.inMain = True
            # Skip this line.
            return
        elif self.line.startswith("g_exportedScripts"):
            # Finish reading file.
            raise StopIteration()
        else:
            self.addFileContents()

    def addFileContents(self):
        if re.search(r"showDlg\W", self.line):
            self.line = uniqueShowDlg(self.line, self.filetuple.name)
        elif re.search(r"getSuite\W", self.line):
            self.line = uniqueGetSuite(self.line, self.filetuple.name)
        elif self.searchLine(
                r"\W(DlgEventHandler|DlgControls|doTests|doCall"
                r"|resetUserVars)"):
            self.line = uniqueMember(
                self.matchObj.group(1), self.line, self.filetuple.name)
        self.line = re.sub(r"#\s*assimilate:\s*", "", self.line)
        self.line = re.sub(
            r"lingt(?:test)?(?:\.\w+){2,3}\.(\w+)", r"\1", self.line)
        for moduleName in self.referencedModules:
            #self.line = re.sub(r"(\W)%s\." % moduleName, r"\1", self.line)
            self.line = re.sub(r"([^\w\.])%s\." % moduleName, r"\1", self.line)
        self.fileContentsList.append(self.line)

    def parseImportModule(self):
        self.inHeader = False
        basePackagePattern = r"(%s)" % '|'.join(BASE_PACKAGE_PATHS.keys())
        if self.searchLine(
                r"^from\s+" + basePackagePattern + r"((?:\.\w+){1,2})\s+" +
                r"import (\w+)"):
            self.grabModule(commaSeparated=True)
        elif self.searchLine(basePackagePattern + r"((?:\.\w+){1,2})\.(\w+)"):
            self.grabModule(commaSeparated=False)
        else:
            self.line = re.sub(r"  ", r" ", self.line)
            if UNITTEST2:
                self.line = re.sub(r"unittest", r"unittest2", self.line)
            self.toplevel.importedPackages.add(self.line)

    def grabModule(self, commaSeparated):
        """param commaSeparated: if True then will split string"""
        basePackage, package, filename = self.matchObj.groups()
        package = re.sub(r"^\.", r"", package)
        #if VERBOSE:
        #   print("grabModule %s - %s - %s" % (basePackage, package, filename))
        basepath = BASE_PACKAGE_PATHS[basePackage]
        package_path = re.sub(r"\.", r"/", package)
        if commaSeparated:
            filenames = re.split(r", ?", filename)
            for splitFilename in filenames:
                importedModule = ImportedModule(
                    basepath, package_path, splitFilename)
                importedModule.addTo(self)
        else:
            importedModule = ImportedModule(basepath, package_path, filename)
            importedModule.addTo(self)


def verifyFileCase(path):
    """Verify filename case because otherwise python
    won't be able to import it even though io.open ignores case.

    This is only needed for Windows because Linux will fail to find the
    file and raise an error, which is what we want.

    This method will also raise an error if the file doesn't exist.
    """
    path = path.replace('/', '\\')
    actualCase = get_actual_path(path)
    if not actualCase:
        Warnings.display()
        raise OSError("Did not find %s" % path)
    if actualCase != path:
        Warnings.display()
        raise OSError(
            "Case doesn't match: Needed %s but found %s"
            % (path, actualCase))

def get_actual_path(path):
    """Returns actual case of file.
    Adapted from stackoverflow.com user xvorsx.
    """
    if platform.system() != "Windows":
        return path
    dirs = path.split('\\')
    # disk letter
    test_path = [dirs[0].upper()]
    for d in dirs[1:]:
        #test_path += ["%s[%s]" % (d[:-1], d[-1])]
        test_path += [d]
    res = glob.glob('\\'.join(test_path))
    if not res:
        # File not found.
        return None
    return res[0]

class ImportedModule:
    def __init__(self, basepath, package, filename):
        self.basepath = basepath
        self.package = package
        self.filename = filename

    def __str__(self):
        return "%s/%s.py" % (self.package, self.filename)

    def addTo(self, fileReader):
        """
        Modifies:
            fileReader.importedModules
            fileReader.referencedModules
        """
        fileReader.importedModules.append(self)
        filepath = "%s%s/%s.py" % (
            self.basepath, self.package, self.filename)
        if os.path.exists(filepath):
            fileReader.referencedModules.append(self.filename)


def moveBefore(aList, elem1, elem2):
    """Move elem1 to just before elem2 in the list.
    Elem2 is required to be in the list already, but elem1 is optional.
    If elem1 is already earlier in the list than elem2, does nothing.
    """
    #if VERBOSE:
    #    print("moveBefore %s %s" % (elem1.name, elem2.name))
    i1 = -1  # index of elem1
    i2 = -1  # index of elem2
    for listIndex in range(len(aList)):
        if aList[listIndex] == elem1:
            i1 = listIndex
        elif aList[listIndex] == elem2:
            i2 = listIndex
    if i2 < 0:
        print("couldn't find in list: %r", elem2)
        return
    if i1 >= 0:
        if i1 < i2:
            # no need to do anything
            return
        # remove elem1 at original location
        aList.pop(i1)
    # insert elem1 just before elem2
    aList.insert(i2, elem1)


class Warnings:
    """Remember the most recent warning.
    Can report this if something goes wrong.
    """
    mostRecent = ""

    @staticmethod
    def add(message):
        Warnings.mostRecent = message

    @staticmethod
    def display():
        print("Most recent warning: %s" % Warnings.mostRecent)


if __name__ == "__main__":
    readFolder()
    print("Finished!")

