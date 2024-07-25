"""
Performs searches for data in the writer document.
"""
import logging
import re

from lingt.access.common import iteruno
from lingt.access.writer.traveler import VCLocation
from lingt.ui.common.messagebox import MessageBox
from lingt.ui.common.progressbar import ProgressBar, ProgressRange
from lingt.utils import util

logger = logging.getLogger("lingt.access.Search")

class ExampleSearch:
    """Search for example ref number."""
    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.foundSomething = False
        self.search = None
        self.foundString = None
        logger.debug("ExampleSearch init() finished")

    def getFoundString(self):
        return self.foundString

    def findRefNumber(self, startFromBeginning, findingAll=False):
        """Find a #abc123 tag in the document that should be replaced."""
        logger.debug(util.funcName('begin'))

        ## Set up the search

        if self.search is None:
            self.search = self.unoObjs.document.createSearchDescriptor()
            self.search.SearchRegularExpression = True
            self.search.SearchString = \
                r"#[a-zA-Z0-9][a-zA-Z0-9\._\-]*[a-zA-Z0-9][:space:]*"

        ## Do the search

        found = None
        if startFromBeginning:
            found = self.unoObjs.document.findFirst(self.search)
        else:
            found = self.unoObjs.document.findNext(
                self.unoObjs.viewcursor.getEnd(), self.search)

        ## Results

        if found:
            logger.debug("Found %s.", found.String)
            self.unoObjs.controller.select(found)
            self.foundSomething = True
            self.foundString = found.String
        else:
            if self.foundSomething:
                message = "No more reference numbers found."
                self.foundSomething = False
            else:
                message = "Did not find a reference number."
                if findingAll:
                    self.msgbox.display(message)
                if not startFromBeginning:
                    message += (
                        "\n Try checking the box to search from beginning.")
                else:
                    message += "\n Make sure to type # in front."
            if not findingAll:
                self.msgbox.display(message)
            self.foundString = None

    def findRefCharStyle(self, charStyleName, startFromBeginning,
                         findingAll=False):
        """Find text set to reference character style.  Probably it is there
        because an example was inserted.
        """
        logger.debug(util.funcName('begin'))
        charStyleSearch = CharStyleSearch(
            self.unoObjs, charStyleName, startFromBeginning)
        foundText = charStyleSearch.doSearch()
        if foundText:
            logger.debug("Found %s.", foundText)
            self.foundSomething = True
            self.foundString = foundText
        else:
            if self.foundSomething:
                message = "No more existing examples found."
                self.foundSomething = False
            else:
                message = "Did not find an existing example."
                if findingAll:
                    self.msgbox.display(message)
                if not startFromBeginning:
                    message += (
                        "\n Try checking the box to search from beginning.")
                else:
                    message += (
                        "\n Verify the example reference number's style.")
            if not findingAll:
                self.msgbox.display(message)
            self.foundString = None

    def refInTable(self):
        """Returns True if the selected ref is in a TextTable.
        Otherwise deselects the ref and returns False.
        """
        if not self.unoObjs.viewcursor.TextTable:
            self.unoObjs.viewcursor.collapseToEnd()
            self.unoObjs.viewcursor.goRight(0, False)
            return False
        return True


class CharStyleSearch:
    """Writer does not have good built-in character style searching, so this is
    an implementation which iterates over the document by paragraphs.
    """
    def __init__(self, unoObjs, charStyleName, startFromBeginning):
        self.unoObjs = unoObjs
        self.charStyleName = charStyleName
        self.startFromBeginning = startFromBeginning
        self.oVC = unoObjs.viewcursor  # shorthand variable name
        self.vcloc = None

    def doSearch(self):
        """
        Given a char style name, finds the next ref of that style.
        Returns the entire string that uses the style.
        If nothing is found, returns an empty string.
        """
        logger.debug("doSearch %s", self.charStyleName)
        if self.startFromBeginning:
            logger.debug("going to beginning")
            oLCurs = self.unoObjs.text.createTextCursor()
            oLCurs.gotoStart(False)
            self.oVC.gotoRange(oLCurs, False)
        self.oVC.collapseToEnd()  # make sure nothing is selected
        if self.oVC.TextFrame:
            # Need to get outside of the frame
            logger.debug("escaping from text frame")
            for dummy in range(2):
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:Escape", "", 0, ())

        ## Look through the document for the character style

        self.vcloc = VCLocation(self.unoObjs, self.startFromBeginning)
        for oPar in iteruno.byEnum(self.unoObjs.text):
            result = ""
            if oPar.supportsService("com.sun.star.text.Paragraph"):
                result = self._searchPara(oPar)
            elif oPar.supportsService("com.sun.star.text.TextTable"):
                result = self._searchTable(oPar)
            if result:
                return result
        logger.debug("returning empty string")
        return ""

    def _searchPara(self, oPar):
        """
        Searches a normal (i.e. non-table) paragraph.
        """
        logger.debug("looking at para")
        if not self.vcloc.parAfter(oPar):
            return ""
        for oSection in iteruno.byEnum(oPar):
            if oSection.TextPortionType == "Text":
                if oSection.CharStyleName == self.charStyleName:
                    logger.debug("Found style %s", self.charStyleName)
                    result = oSection.getString()
                    if result:
                        self.oVC.gotoRange(oSection.getStart(), False)
                        self.oVC.gotoRange(oSection.getEnd(), True)
                        #logger.debug("returning a string")
                        logger.debug("returning string '%s'", result)
                        return result
        return ""

    def _searchTable(self, oTable):
        """
        Searches through the text of a table.
        """
        logger.debug("looking at table %s.", oTable.getName())
        if not self.vcloc.tableAfter(oTable):
            return ""
        logger.debug("searching %s", oTable.getName())
        oTextCurs = self._gotoEndOfLastCell(oTable)
        while not oTextCurs.CharStyleName == self.charStyleName:
            if not oTextCurs.goLeft(1, False):
                break
        foundSomething = False
        while oTextCurs.CharStyleName == self.charStyleName:
            if not oTextCurs.goLeft(1, True):
                break
            foundSomething = True
        if foundSomething:
            oTextCurs.goRight(1, True)
        result = oTextCurs.getString()
        if foundSomething and result:
            self.oVC.gotoRange(oTextCurs.getStart(), False)
            self.oVC.gotoRange(oTextCurs.getEnd(), True)
            #logger.debug("returning a string")
            logger.debug("returning a string: '%s'", result)
            return result
        logger.debug("no ref found in this table")
        return ""

    def _gotoEndOfLastCell(self, oTable):
        """
        One way to traverse the text of a table is to start at the end of
        the last cell's text (and then cursor.goLeft()).
        """
        # go to first cell
        self.unoObjs.controller.select(oTable)
        firstCell = self.oVC.Cell
        # go to end of cell if cell is not empty
        self.oVC.gotoEnd(False)
        if self.oVC.Cell.CellName == firstCell.CellName:
            # go to end of last cell in table
            self.oVC.gotoEnd(False)
        return self.oVC.getText().createTextCursorByRange(
            self.oVC.getStart())


class AbbrevSearchSettings:
    """A structure to hold settings for Abbrevsearch."""
    def __init__(self):
        self.searchUpperCase = False
        self.maxSearchLength = -1
        self.searchAffix = ""
        self.searchDelimiters = ""
        self.startFromBeginning = False
        self.searchParaStyle = ""


class AbbrevSearch:
    """Search for unknown abbreviations and add them to the list."""
    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.msgbox = MessageBox(unoObjs)
        self.selectionFound = None
        self.alreadyAskedList = []
        self.searchConfig = None
        self.currentAbbrevList = None
        self.possibilities = []
        logger.debug("AbbrevSearch init() finished")

    def findOccurrences(self, abbrevList):
        """Modifies abbrevList."""
        progressBar = ProgressBar(self.unoObjs, "Searching for occurrences...")
        progressBar.show()
        progressBar.updateBeginning()
        progressRange = ProgressRange(ops=len(abbrevList), pbar=progressBar)
        for abbrevIndex, abbrev in enumerate(abbrevList):
            search = self.unoObjs.document.createSearchDescriptor()
            search.SearchString = abbrev.abbrevText
            search.SearchCaseSensitive = False
            search.SearchWords = True

            selectionsFound = self.unoObjs.document.findAll(search)
            occurrences = selectionsFound.getCount()
            abbrevList.setOccurrences(abbrevIndex, occurrences)
            progressRange.update(abbrevIndex)
        progressBar.updateFinishing()
        progressBar.close()

    def findNext(self, searchConfig, currentAbbrevList):
        """
        Look for possible abbreviations.
        Search by regular expression on a certain paragraph style.
        Param searchConfig should be of type AbbrevSearchSettings.
        """
        logger.debug(util.funcName('begin'))
        self.searchConfig = searchConfig
        self.currentAbbrevList = currentAbbrevList
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchStyles = True
        search.SearchString = searchConfig.searchParaStyle

        if searchConfig.startFromBeginning:
            logger.debug("Start from beginning")
            self.selectionFound = self.unoObjs.document.findFirst(search)
            searchConfig.startFromBeginning = False
        elif self.selectionFound:
            logger.debug("Start from previous match")
            self.selectionFound = self.unoObjs.document.findNext(
                self.selectionFound.getEnd(), search)
        else:
            logger.debug("Start from current loc")
            self.selectionFound = self.unoObjs.document.findNext(
                self.unoObjs.viewcursor.getEnd(), search)
        while self.selectionFound:
            self.possibilities = []
            self._checkString(self.selectionFound.String)
            if self.possibilities:
                return self.possibilities
            self.selectionFound = self.unoObjs.document.findNext(
                self.selectionFound.getEnd(), search)
        logger.debug(util.funcName('end'))
        return []

    def _checkString(self, searchString):
        logger.debug("Selection found: '%s'", searchString)
        delims = "- "
        if self.searchConfig.searchDelimiters != "":
            delims = self.searchConfig.searchDelimiters
        morphs = re.split('[' + delims + ']', searchString)
        if self.searchConfig.searchAffix == 'suffix':
            morphs = morphs[1:]
        elif self.searchConfig.searchAffix == 'prefix':
            morphs = morphs[:-1]
        for morph in morphs:
            self._checkMorph(morph)
        logger.debug("Possibilities: %d", len(self.possibilities))

    def _checkMorph(self, morph):
        logger.debug("Checking morph %s", morph)
        words = re.split(r'[.\',()_;]', morph)
        for word in words:
            logger.debug("Checking word %s", word)
            if len(word) > self.searchConfig.maxSearchLength:
                return
            if word.lower() in self.currentAbbrevList:
                # Already in the list, so no need to add it.
                return
            if word.lower() in self.alreadyAskedList:
                return
            if self.searchConfig.searchUpperCase and word.upper() != word:
                return

            ## Found a possibility.
            if len(self.possibilities) == 0:
                logger.debug("Selecting")
                start = self.selectionFound.getStart()
                end = self.selectionFound.getEnd()
                if self.selectionFound.getText().compareRegionStarts(
                        start, self.selectionFound) >= 0:
                    end, start = start, end  # swap
                self.unoObjs.viewcursor.gotoRange(start, False)
                self.unoObjs.viewcursor.gotoRange(end, True)
            logger.debug("Adding to alreadyAskedList")
            self.alreadyAskedList.append(word.lower())
            self.possibilities.append(word)
