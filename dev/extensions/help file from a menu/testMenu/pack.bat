@echo off

chdir
"C:\Program Files\7-Zip\7z.exe" a -tZip -xr!*.swp TestHelp.oxt META-INF help Addons.xcu description.xml
pause
