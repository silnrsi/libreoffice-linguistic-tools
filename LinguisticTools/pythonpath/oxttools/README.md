# oxttools
Tools for creating language support oxt extensions for LibreOffice

## Dependencies
oxttools depends on the lxml python library, which can be tricky to install on Windows.

## Installation

### Windows
See WindowsInstall.md (in the `docs` folder)

### Linux
```
python setup.py build
sudo python setup.py install
```

## Usage
makeoxt is the tool for creating a LibreOffice extension. You will need to choose a language
tag to associate with your writing system. Also, adding new languages only works with
LibreOffice 5.3 or later.

For example:

```
makeoxt -d mywords.txt -l "My Language" -t ctl qax-x-complex qax-x-complex.oxt
```

See USAGE.md for more complete usage instructions.
