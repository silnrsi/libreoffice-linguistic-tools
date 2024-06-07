# LibreOffice Linguistic Tools

This add-on inserts lexical and interlinear data from [SIL FieldWorks](http://software.sil.org/fieldworks/) into LibreOffice.  Other features include Data Conversion using [SIL Converters](https://software.sil.org/silconverters/).

![LOLT menu](/external%20docs/writer_menu.jpg)

To download the add-on, find the latest release on the sidebar. Builds can also be found at [extensions.libreoffice.org](https://extensions.libreoffice.org/en/extensions/show/99202).

Help (including installation instructions) is available from the menu, or you can download it here: [Linguistic Tools Help.pdf](/external%20docs/Linguistic%20Tools%20Help.pdf). For complete version history, see [README.txt](/LinguisticTools/help/README.txt).


# Notes for Developers

The `.oxt` is a zipped file with source code included. The file is built by zipping up relevant files, either with [this PowerShell script](https://github.com/silnrsi/libreoffice-linguistic-tools/blob/master/LinguisticTools/build/create_oxt.ps1) or by hand. More options to build the extension are described in [README_build.txt](/LinguisticTools/build/README_build.txt).

Most of the code is in the pythonpath folder as described [here](https://wiki.openoffice.org/wiki/Python/Transfer_from_Basic_to_Python#Importing_Modules).
