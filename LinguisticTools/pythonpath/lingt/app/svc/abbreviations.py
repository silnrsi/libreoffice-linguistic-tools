# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 20-Sep-10 JDK  Keep occurrences count unless abbrev is changed.
# 29-Oct-10 JDK  Use unique lists rather than sets.
# 23-Oct-12 JDK  Now that we require a newer python version, use set().
# 27-Feb-13 JDK  Use key instead of cmp for sorting (required in python 3.3).
# 01-Jul-15 JDK  Added Abbrev.__repr__().
# 09-Sep-15 JDK  Derive from ItemList.
# 18-Dec-15 JDK  Use rich comparisons instead of getID().

"""
Insert a list of abbreviations used in the document.
Reads from gloss and part of speech.

This module exports:
    AbbrevList
    Abbrev
"""
import functools
import logging
import re

from lingt.access.writer.uservars import Syncable
from lingt.app.fileitemlist import ItemList
from lingt.ui.messagebox import MessageBox
from lingt.utils import util

logger = logging.getLogger("lingt.app.abbreviations")

class AbbrevList(ItemList, Syncable):
    """Maintains a list of abbreviations."""

    ITEM_DESC_GENERIC = "an abbreviation"
    ITEM_DESC_SPECIFIC = "Abbreviation"

    def __init__(self, unoObjs, userVars):
        ItemList.__init__(self)
        Syncable.__init__(self, userVars)
        self.msgbox = MessageBox(unoObjs)

    def getUniqueList(self):
        """Return a lowercased set of the abbreviations."""
        newList = [item.abbrevText.lower() for item in self.itemList]
        # make the list unique
        newList = list(set(newList))
        return newList

    def loadUserVars(self):
        logger.debug(util.funcName())
        self.itemList = []
        varname = "Abbreviations"
        abbrevs_repr = self.userVars.get(varname)
        if abbrevs_repr == "":
            self.loadDefaultList()
            return

        ## Verify the string is correctly formed, like "(a,b,c,d)(e,f,g,h)"
        if not re.search(r'^(?:\(.*,.*,.*,.*\))*$', abbrevs_repr):
            self.msgbox.display(
                self.noUserVarData(self.userVars.VAR_PREFIX + varname))
            return

        ## Split by parenthesis into tuples.
        for abbrev_repr in re.split(r'(?<!\\)[()]', abbrevs_repr):
            if abbrev_repr == "":
                # Splitting "(a)(b)" by () results in three empty strings:
                # initially before "(", medially between ")(",
                # and finally after ")".  Just ignore these.
                continue
            newAbbrev = Abbrev()
            newAbbrev.loadFromRepr(abbrev_repr)
            self.itemList.append(newAbbrev)
        self.sortItems()

    def storeUserVars(self):
        """The string will look like:
        (abbrev1,fullName1,True,0)(abbrev2,fullName2,True,0)
        """
        if not self.changed:
            return
        logger.debug(util.funcName())

        abbrevs_repr = "".join(
            [repr(abbrev) for abbrev in self.itemList])
        self.userVars.store("Abbreviations", abbrevs_repr)
        self.changed = False
        logger.debug(util.funcName('end'))

    def loadDefaultList(self):
        """Loads the default list, taken from Leipzig Glossing Rules."""
        logger.debug(util.funcName())
        self.itemList = []
        defaultAbbrevs = [
            ("1", "first person"),
            ("2", "second person"),
            ("3", "third person"),
            ("A", "agent-like argument of canonical transitive verb"),
            ("ABL", "ablative"),
            ("ABS", "absolutive"),
            ("ACC", "accusative"),
            ("ADJ", "adjective"),
            ("ADV", "adverb(ial)"),
            ("AGR", "agreement"),
            ("ALL", "allative"),
            ("ANTIP", "antipassive"),
            ("APPL", "applicative"),
            ("ART", "article"),
            ("AUX", "auxiliary"),
            ("BEN", "benefactive"),
            ("CAUS", "causative"),
            ("CLF", "classifier"),
            ("COM", "comitative"),
            ("COMP", "complementizer"),
            ("COMPL", "completive"),
            ("COND", "conditional"),
            ("COP", "copula"),
            ("CVB", "converb"),
            ("DAT", "dative"),
            ("DECL", "declarative"),
            ("DEF", "definite"),
            ("DEM", "demonstrative"),
            ("DET", "determiner"),
            ("DIST", "distal"),
            ("DISTR", "distributive"),
            ("DU", "dual"),
            ("DUR", "durative"),
            ("ERG", "ergative"),
            ("EXCL", "exclusive"),
            ("F", "feminine"),
            ("FOC", "focus"),
            ("FUT", "future"),
            ("GEN", "genitive"),
            ("IMP", "imperative"),
            ("INCL", "inclusive"),
            ("IND", "indicative"),
            ("INDF", "indefinite"),
            ("INF", "infinitive"),
            ("INS", "instrumental"),
            ("INTR", "intransitive"),
            ("IPFV", "imperfective"),
            ("IRR", "irrealis"),
            ("LOC", "locative"),
            ("M", "masculine"),
            ("N", "neuter"),
            ("N", "non- (e.g. NSG nonsingular, NPST nonpast)"),
            ("NEG", "negation, negative"),
            ("NMLZ", "nominalizer/nominalization"),
            ("NOM", "nominative"),
            ("OBJ", "object"),
            ("OBL", "oblique"),
            ("P", "patient-like argument of canonical transitive verb"),
            ("PASS", "passive"),
            ("PFV", "perfective"),
            ("PL", "plural"),
            ("POSS", "possessive"),
            ("PRED", "predicative"),
            ("PRF", "perfect"),
            ("PRS", "present"),
            ("PROG", "progressive"),
            ("PROH", "prohibitive"),
            ("PROX", "proximal/proximate"),
            ("PST", "past"),
            ("PTCP", "participle"),
            ("PURP", "purposive"),
            ("Q", "question particle/marker"),
            ("QUOT", "quotative"),
            ("RECP", "reciprocal"),
            ("REFL", "reflexive"),
            ("REL", "relative"),
            ("RES", "resultative"),
            ("S", "single argument of canonical intransitive verb"),
            ("SBJ", "subject"),
            ("SBJV", "subjunctive"),
            ("SG", "singular"),
            ("TOP", "topic"),
            ("TR", "transitive"),
            ("VOC", "vocative")]
        for defaultTuple in defaultAbbrevs:
            newAbbrev = Abbrev()
            newAbbrev.abbrevText, newAbbrev.fullName = defaultTuple
            self.itemList.append(newAbbrev)
        self.sortItems()
        self.changed = True
        self.storeUserVars()

    def sortItems(self):
        """Sort by abbreviation."""
        logger.debug(util.funcName())
        self.itemList.sort()

    def setOccurrences(self, itemPos, newValue):
        self.itemList[itemPos].occurrences = newValue
        self.changed = True

    def changeAllCaps(self):
        """Rotate between three options:
        All caps, all lower, and first char upper.
        Returns True if change is made.
        """
        allCapsNew = "UPPER"
        allCapsPrev = self.userVars.get("AllCaps")
        if allCapsPrev == "":
            allCapsPrev = "UPPER"
        if allCapsPrev == "UPPER":
            allCapsNew = "lower"
        elif allCapsPrev == "lower":
            allCapsNew = "Capitalized"
        elif allCapsPrev == "Capitalized":
            allCapsNew = "UPPER"

        result = self.msgbox.displayOkCancel(
            "This will change the case of the entire list from '%s' "
            "to '%s.' Continue?", allCapsPrev, allCapsNew)
        if not result:
            logger.debug("Not changing caps.")
            return False
        logger.debug("Changing caps.")

        for abbr in self.itemList:
            if allCapsNew == "UPPER":
                abbr.abbrevText = abbr.abbrevText.upper()
            elif allCapsNew == "lower":
                abbr.abbrevText = abbr.abbrevText.lower()
            elif allCapsNew == "Capitalized":
                abbr.abbrevText = abbr.abbrevText.capitalize()
            else:
                self.msgbox.display("Unexpected new value %s.", allCapsNew)
                return False

        self.changed = True
        self.userVars.store("AllCaps", allCapsNew)
        return True


@functools.total_ordering
class Abbrev:
    """Stores information about an abbreviation."""

    def __init__(self):
        self.abbrevText = ""  # the abbreviation, example "ABL"
        self.fullName = ""  # what it stands for, example "Ablative"
        self.forceOutput = False
        self.occurrences = 0

    def __str__(self):
        if self.forceOutput:
            occurs = ">"
        elif self.occurrences > 0:
            occurs = "+"
        else:
            occurs = ""
        fullNameShortened = self.fullName[:25]
        return "%-2s %-5s %-25s" % (occurs, self.abbrevText, fullNameShortened)

    def __repr__(self):
        """String representation useful for storage in user variables.
        Put values in a single comma-separated string.  Escape any
        delimiters with a backslash.
        """
        abbrev_val = re.sub(r'([(),])', r'\\\1', self.abbrevText)
        fullNameVal = re.sub(r'([(),])', r'\\\1', self.fullName)
        s = "(%s,%s,%s,%d)" % (
            abbrev_val, fullNameVal, self.forceOutput, self.occurrences)
        return s

    def __lt__(self, other):
        return self.abbrevText.lower() < other.abbrevText.lower()

    def __eq__(self, other):
        return self.abbrevText.lower() == other.abbrevText.lower()

    def loadFromRepr(self, abbrev_repr):
        """Loads from a string representation.  The opposite of __repr__()."""
        ## Split by commas a string like "abbrev,fullName,True,0"
        vals = re.split(r'(?<!\\)[,]', abbrev_repr)

        ## Remove escape character "\"
        for i in range(0, len(vals)):
            vals[i] = re.sub(r'\\', '', vals[i])

        ## Now store the values
        self.abbrevText = vals[0]
        self.fullName = vals[1]
        forceOutput = vals[2]
        if forceOutput == "True":
            self.forceOutput = True
        try:
            self.occurrences = int(vals[3])
        except ValueError:
            self.occurrences = 0

    def shouldOutput(self):
        if self.forceOutput:
            return True
        if self.occurrences > 0:
            return True
        return False

    def sameAs(self, other):
        """Returns True if other and self have the same attribute values.
        Number of occurrences is not treated as distinctive.
        """
        return (
            self.abbrevText == other.abbrevText
            and self.fullName == other.fullName
            and self.forceOutput == other.forceOutput)

