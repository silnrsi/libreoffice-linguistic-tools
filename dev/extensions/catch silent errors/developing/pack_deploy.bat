@echo off
rem Created by Jim Kornelsen in 2009
rem 01-Jul-11  No need for separate pack.bat and redeploy.bat files.
rem 18-Jul-11  Skip files in assimilated code directory.

chdir ..
"C:\Program Files\7-Zip\7z.exe" a -tZip -xr!*.swp -xr!*.pyc ^
-xr!"developing/assimilated code/*.*" ^
LinguisticTools.oxt developing help LingToolsBasic META-INF pkg-desc ^
pythonpath Addons.xcu Components.py description.xml

@rem set OFFICEDIR=C:\Program Files\OpenOffice.org 3
set OFFICEDIR=C:\Program Files\LibreOffice 3.6
@echo on
"%OFFICEDIR%\program\unopkg" remove name.JimK.LinguisticTools
"%OFFICEDIR%\program\unopkg" add "LinguisticTools.oxt"
@pause
