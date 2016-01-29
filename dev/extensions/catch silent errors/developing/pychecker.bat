@echo off
rem Created by Jim Kornelsen on 02/11/10
rem
rem 14-Nov-12 JDK  Handle multiple files.
rem
rem Run pychecker with UNO-enabled (OpenOffice.org) python.
rem To use, drag one or more files from the pythonpath folder onto this icon.
rem
rem See also C:\python26\scripts\pychecker.bat

set PYTHONPATH=D:\Jim\computing\Office\OOo Linguistic Tools\LinguisticTools\pythonpath
set PYINST="C:\Program Files\OpenOffice.org 3\program\python.exe"
rem set PYINST="C:\python26\python.exe"
set PYCHECKER=C:\Python26\Lib\site-packages\pychecker\checker.py

%PYINST% %PYCHECKER% --limit 30 %*

pause
