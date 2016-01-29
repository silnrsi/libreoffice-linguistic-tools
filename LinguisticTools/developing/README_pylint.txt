# vim: set filetype=conf :
# Created by Jim Kornelsen on June 22 2015
#
# This document describes using pylint to check for OOLT programming errors.

Pylint is useful for catching python errors such as print(self.x) when
self.x has never been used.
In a stricter language like Java most of these things would be compile
errors, and in Python it is really hard to catch these problems.

Pychecker seems to be obsolete, so use pylint from now on.
Pyflakes is another option, but it doesn't seem to catch most problems.


## Install and configure

pip install pylint       # not needed for python 3.4.1 and later
cd $env:USERPROFILE
pylint --generate-rcfile
msg-template={path}:{line}: {msg_id}({symbol}) {msg}
reports=no
Add codes to the disable line:
invalid-name,missing-docstring,too-many-instance-attributes,too-few-public-methods,duplicate-code,too-many-branches,too-many-statements,too-many-arguments,I0011,I0012

## Ordinary checking

cd LinguisticTools/pythonpath
pylint lingt.UI.FieldTags


## Windows OpenOffice using UNO libs in Windows system python

Note: With this setup, pylint complains about failing to import com.sun.star,
but it still checks syntax just fine.  This is true on Linux as well.

Pylint-gui works pretty well.  To use pylint from command line instead:
cd pythonpath
PYTHONPATH=.
& "C:\program files (x86)\libreoffice 4\program\python-core-3.3.3\scripts\pylint.exe" lingt.UI.DlgBulkConv
foreach ($f in gci lingt/UI/DlgBulkConv.py) {
    & "C:\Program Files (x86)\LibreOffice 4\program\python.exe" `
        C:\Python34\lib\site-packages\pylint\lint.py .\lingt\UI\$f
}

C:\Program Files (x86)\LibreOffice 4\program\python-core-3.3.3\Scripts\pylint


## Setting up Windows system python to use UNO libs

#Open Admin powershell.
#pip install --install-option="--prefix=C:\program files (x86)\libreoffice 4\program\python-core-3.3.3" --ignore-installed pylint
#& "C:\Program Files (x86)\LibreOffice 4\program\python-core-3.3.3\Scripts\pylint.exe" C:\Python34\lib\site-packages\pylint\lint.py lingt.UI.DlgBulkConv

import os
print(os.environ['URE_BOOTSTRAP'])
print(os.environ['UNO_PATH'])
print(os.environ['PATH'])

$env:URE_BOOTSTRAP = "vnd.sun.star.pathname:C:\program files (x86)\libreoffice 4\program\fundamental.ini"
$env:UNO_PATH = "C:\program files (x86)\libreoffice 4\program\"
$env:PATH = "C:\program files (x86)\libreoffice 4\URE\bin;C:\program files (x86)\libreoffice 4\program\;$env:PATH"

Create file C:\Python33\Lib\site-packages\uno.pth with the following contents:
c:\\program files (x86)\\libreoffice 4\\program
Or try it with URL escapes:
c:\\program%20files%20%28x86%29\\libreoffice%204\\program


## Linux - system python3 works for LibreOffice

sudo apt-get install python3-pip
sudo pip3 install pylint
sudo vi /usr/bin/pylint
    change shebang line to use python3 instead of python

perl assimilate.pl
cd "assimilated_code"
pylint DlgBulkConv.py > pylint.txt

pylint --init-hook="import sys; sys.path.append('')" DlgBulkConv.py
pylint --init-hook="import uno" DlgBulkConv.py

cd pythonpath
PYTHONPATH=.
python3 lingt/UI/DlgBulkConv.py
pychecker --limit 30 lingt.Access.Xml.InterlinReader.py
pychecker lingt/Access/*/*.py


## Other

To check if var is defined:
    "name" in locals()
    "name" in globals()
