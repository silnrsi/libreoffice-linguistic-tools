@echo off

chdir
"C:\Program Files\7-Zip\7z.exe" a -tZip -xr!*.swp ItemsA.oxt META-INF Addons.xcu description.xml
pause
