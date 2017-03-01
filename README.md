# OpenOffice Linguistic Tools

This add-on reads files exported from [SIL FieldWorks](http://software.sil.org/fieldworks/) and [Toolbox](http://www-01.sil.org/computing/toolbox/). Other features include Data Conversion using [SIL Converters](http://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=EncCnvtrs).

The primary site to download releases is https://extensions.libreoffice.org/extensions/lingtools.  Complete source code can be downloaded from github, and recent releases are here as well.

To install, download the "LinguisticTools" oxt file and double-click to open it.  The Extension Manager should open and install the add-on.  For more detailed installation instructions and version history, see [README.txt](/releases/download/v2.9.1/README.txt)

![OOLT menu](/external%20docs/OOoLT_writer_menu.jpg)

*Download latest version*: [LinguisticTools-2.9.1.oxt](https://github.com/jkornelsen/OOLingTools/releases/download/v2.9.1/LinguisticTools-2.9.1.oxt) (642 KB) released December 2015

Help is available from the menu, or you can download it separately here: [Linguistic Tools Help.pdf](/external%20docs/Linguistic_Tools_Help.pdf) (503 KB)

If you need to remove the Linguistics menu and are having problems, use [RemoveLingMenu.oxt](https://github.com/jkornelsen/OOLingTools/releases/download/v2.9.1/RemoveLingMenu.oxt) (only 2 KB)

# Technical Notes

The .oxt file is a zipped file with source code included.  Most of the code is in the pythonpath folder as described [here](https://wiki.openoffice.org/wiki/Python/Transfer_from_Basic_to_Python#Importing_Modules).

More information for developers is in the following files:
- [README_build.txt](/LinguisticTools/build/README_build.txt)
- [README_pylint.txt](/LinguisticTools/build/README_pylint.txt)
- [Design.txt](/Design.txt)
