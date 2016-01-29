@echo off
rem Created by Jim Kornelsen in 2009
rem 01-Jul-11  No need for separate pack.bat and redeploy.bat files.
rem 18-Jul-11  Skip files in assimilated code directory.

set PACKAGE_NAME=DoobieDoo

move idl\XDoobieDoo.rdb %PACKAGE_NAME%\

del %PACKAGE_NAME%.oxt
cd %PACKAGE_NAME%\
"C:\program files\7-zip\7z.exe" a -r -tzip -xr!*.swp -xr!*.pyc ..\%PACKAGE_NAME%.oxt *.*
cd ..

@rem set OFFICEDIR=C:\Program Files\OpenOffice.org 3
set OFFICEDIR=C:\Program Files\LibreOffice 3.6
@echo on
rem "%OFFICEDIR%\program\unopkg" remove com.doobiecompany.examples.DoobieDoo
rem "%OFFICEDIR%\program\unopkg" add "%PACKAGE_NAME%.oxt"
@pause
