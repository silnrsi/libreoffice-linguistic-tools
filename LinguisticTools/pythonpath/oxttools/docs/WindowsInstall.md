# Installing oxttools on Windows

The following instructions explain how to:
- install and use makeoxt.exe (in the makeoxt.zip package downloaded from the https://github.com/silnrsi/oxttools/releases page)
- install oxttools from source on Windows
- package the oxttools installation into a single .exe

## Installing from packaged version
### Installation
- Download makeoxt.zip from the https://github.com/silnrsi/oxttools/releases page and extract the makeoxt.exe file.
- Copy makeoxt.exe to working folder.

### Usage
- Copy WORDLIST to working folder
- Use from command prompt as:
```
makeoxt -d WORDLIST -l "Name of Language" -t SCRIPTTYPE LANGTAG OUTPUT.oxt
```
- Distribute OUTPUT.oxt

where
- WORDLIST (which processes differently based on the file extension) =
  - DICT.txt : plain text file containing a list of words (one per line)
  - PARATEXT_WORDLIST.xml : file containing the output of Paratext's Wordlist-File-Export to XML
  - DICT.aff : (experimental) hunspell .dic/.aff dictionary files
- "Name of Language" = the name of the language enclosed in quotes (for example "Ankave" or "Albanian")
- SCRIPTTYPE =
  - west (Latin, Greek, Cyrillic, etc.)
  - asian (Chinese, Japanese, Korean)
  - rtl (complex right-to-left scripts, Arabic, etc.)
  - ctl (complex left-to-right scripts, Devanagri, etc.)
- LANGTAG = the language tag (for example aak or aae-Latn)
- OUTPUT.oxt = name of the LibreOffice extension to be createdfrom

## Installing from source
### Install Python
Download installation file for Python 2.7 for Windows (64-bit) from:
https://www.python.org/ftp/python/2.7/python-2.7.amd64.msi

Launch the python-2.7.amd64.msi file you just downloaded
- Install for all users
- Use the default installation folder: C:\Python27\
- take defaults (to install everything) for Customize Python 2.7
- confirm installation, if asked
- Finish

### Install lxml
Download lxml for Python 2.7 (64-bit) by going to:
https://pypi.python.org/pypi/lxml/3.2.3
and clicking on the lxml-3.2.3.win-amd64-py2.7.exe link.

Launch the lxml-3.2.3.win-amd64-py2.7.exe file you just downloaded
- Click Next to start installation
- verify that it found the Python installation in C:\Python27, and click Next, Next,
- Finish

### Install Git (both GitHub and Git Shell)
On page https://desktop.github.com/ click "Download GitHub Desktop" to download the  GitHubSetup.exe file

Launch the GitHubSetup.exe file
- confirm installation, if asked
- the setup program downloads 127MB and installs GitHub Desktop as well as Git Shell.

### Obtain the oxttools repository from GitHub (using Git Shell)
Launch Git Shell. ~\Documents\GitHub> is displayed as command prompt.

Enter the following command after the prompt:

```
git clone https://github.com/silnrsi/oxttools.git
```

This places the `makeoxt` script in the `Documents\GitHub\oxttools\scripts` folder under the current user account.

## Packaging oxttools for Windows using pyinstaller

Once the above installation has been completed, the makeoxt.exe file can be created with pyinstaller (see http://www.pyinstaller.org/ for instructions on installing pyinstaller). This must be done on the same platform that the target .exe file will be used, in this case a Windows 64-bit machine (using Python 2.7).

The command:
```
C:\Python27\Scripts\pyinstaller.exe --hidden-import atexit --onefile makeoxt
```
uses the pyintaller.exe that was installed in the Python 2.7 `Scripts` folder. The `--hidden-import atexit` is needed to force inclusion of the implicitly loaded atexit module and the `--onefile` puts everything into the .exe file.

NB: The above pyinstaller command must be run in the folder where the makeoxt script resides (oxttools/scripts). The resulting makeoxt.exe file is placed in the `dist` subfolder (oxttools/scripts/dist)
