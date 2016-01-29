*******************************************************************************
* Linguistic Tools add-on for OpenOffice (OOLT)
* SIL South Asia
*******************************************************************************

OOLT provides a menu of tools for linguistic writeups and other documents
written in lesser-known languages.

For help, see Linguistics -> Help.

In this file:
    Requirements
    Installation instructions
    Version history


*******************************************************************************
* Requirements
*******************************************************************************

LibreOffice (LO) or Apache OpenOffice (AOO) is required.  The add-on supports
both brands equally, and in this document, the name OpenOffice refers
generically to both.  There is no python support in AOO 4.0 so please upgrade
to AOO 4.1 or higher.  OOLT is tested on Windows and Linux.  It should work on
a Mac as well.

For Data Conversion on Windows, download and install the SIL Converters
application.  On Linux, install FieldWorks which includes the required SIL
Converters libraries.

In addition to English, this add-on can be used in Spanish or French.  It
should change automatically when you use OpenOffice in one of those
languages (Tools -> Options -> Language Settings, Languages).

The latest release of the add-on can be downloaded from
http://projects.palaso.org/projects/ooolt.


*******************************************************************************
* Installation
*******************************************************************************

The add-on is installed from a file called LinguisticTools.oxt. When you
open this file, the OpenOffice Extensions Manager will install it. After it
finishes, open a Writer document. If the installation was
successful, you will see a new menu to the right of the Tools menu called
"Linguistics" as shown in Overview above.

If the extension is not able to install correctly, close all open windows of
OpenOffice including the quickstarter and then try again.

When installing OpenOffice in Windows, the Python-UNO bridge must be selected.
This is under Optional components and is selected by default.  In Fedora, the
Python bridge is not included by default.  You must add either the
libreoffice-pyuno or python-openoffice package.

If there is an older version of the add-on installed, the Extension Manager
will first remove the old version.  You may see an error when removing that
says "Addons.xcu does not exist." Just ignore this error and press ok.  To
prevent this error, you can delete the user profile
(check Tools -> Options -> Paths for the location), which will remove any
existing add-ons and settings.

Sometimes removing an older version may give other error messages such as
failing to close a bridge. If there are error messages like this, then close
all open windows of OpenOffice. Then try removing the older version again. You
may also need to reboot in order for this problem to go away.  Some people have
reported that re-downloading the extension was needed, especially in areas
where there is a poor internet connection.


*******************************************************************************
* Version History
*******************************************************************************

To see which version is installed, go to Tools -> Extension manager.

2.9.1 15-Dec-15  Option to read Flextext ref numbers.
2.9   30-Nov-15  Refactor to prepare for 3.0 release.
                 Revise help to focus on FieldWorks.
2.2.1 28-May-14  Updated for LibreOffice 4.1 and Apache OpenOffice 4.1
                 ECDriver is now included with FieldWorks on Linux.
2.1.2 05-Jul-13  Choose whether Flex lexeme is phonemic.
2.1.1 10-Jun-13  Search paths for Linux Data Conversion.
2.1   15-May-13  Fix Alt hotkeys in dialogs.
                 Improve case insensitive spell checking.
                 Programming: automated test suite.
2.0   25-Apr-13  Word List and Spelling using Calc spreadsheet.
                 Updated for LibreOffice 4 and Python 3.
                 Minimum Office 3.2 and Python 2.6.
                 Linux ECDriver patch for EncConverters from FieldWorks.
                 Data Conversion can search for complex fonts.
                 Fixed several Spanish and French localization problems.
                 Tested and fixed a number of bugs for grammar and phonology.
1.2.8 16-May-12  Fixed bug when reading flextext files.
1.2.7 30-Apr-12  Data Conversion in 1.2.6 on Windows was not recognizing the
                 converter name.
1.2.6 12-Jan-12  Fix bug when updating examples introduced in version 1.2.5.
1.2.5 22-Dec-11  Fix problems with Data Conversion introduced in version 1.1.
                 Data Conversion is pure python, no OpenOffice C++ component.
                 Requires Office 3.1 or higher.
1.2.1 28-Oct-11  Read Source field from Flex LIFT data.
1.2   17-Aug-11  Script Practice to help learn various scripts.
                 Handle experimental transcriptions from Phonology Assitant.
1.1   23-Apr-11  Spanish localization and corrected French localization.
                 Data Conversion handles footnotes, character styles and
                 line breaks, and is faster.
1.0.2 13-Nov-10  Updated French localization.
1.0.1 30-Oct-10  Fix installation problem on Office 3.3.
1.0   29-Oct-10  Ability to update examples.
                 Data Conversion can create styles and allows font-to-font.
                 Interlinear orthographic word and morpheme lines.
                 Can specify different tags to read Toolbox data.
                 Import Phonology data from Toolbox as XML, not SFM.
                 Menu uninstaller.
                 Programming: layered design by importing from pythonpath.
0.9.1 25-Aug-10  Bug fixes for FieldWorks interlinear data.
0.9   05-Aug-10  Improved Data Conversion: tables in selection, bug fixes.
0.8.3 08-Apr-10  Figure out optimal number of words for each table row.
                 French localization.
                 Grammar options: free translation in quotes, orthographic line,
                 part of speech above gloss.
                 Abbreviation Add New button improved.
0.8   24-Mar-10  Improved Data Conversion.
                 Option to not create an outer table for grammar.
                 Fixed significant problem of slow frames.
                 New feature: Abbreviations.
                 Import phonology data directly from Toolbox SFM.
0.7   26-Feb-10  Extensive testing and bug fixes.
                 Renamed to Linguistic Tools.
                 Experimental version of Data Conversion.
0.6   11-Feb-10  Handle LIFT data exported from Flex.
                 Removed font and size from Grammar Settings.
0.5   06-Feb-10  Change interlinear styles to be similar to those of Flex.
                 Tables improved.
0.4   02-Feb-10  Additional prefixes so that multiple Flex texts can be used.
                 Initial support for tables.
0.3   29-Jan-10  Help documentation.
0.2   27-Jan-10  Grammar examples using frames like Flex does.
                 Read XML files exported from Toolbox and Flex.
0.1   19-Jan-10  First extension for a workshop.
                 Phonology Assistant only.
(0.0) 2009       OOo python macro to import interlinear examples from Toolbox.
                 A single table for each example, wrapping not handled.
                 Used Martin Hosken's sh2xml, no exporting needed.
                 Text file for configuration.

