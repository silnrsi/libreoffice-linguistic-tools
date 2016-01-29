
@echo off

perl assimilate.pl

@rem set OFFICEAPP=OpenOffice.org
set OFFICEAPP=LibreOffice
set DEPLOYDIR="C:\Users\Jim Kornelsen\AppData\Roaming\%OFFICEAPP%\3\user\Scripts\python\"
if not exist %DEPLOYDIR% mkdir %DEPLOYDIR%
copy "assimilated code\*.py" %DEPLOYDIR%
pause
