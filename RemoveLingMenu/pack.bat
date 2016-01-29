@echo off

chdir
"C:\Program Files\7-Zip\7z.exe" a -tZip -xr!*.swp RemoveLingMenu.oxt META-INF pkg-desc Addons.xcu description.xml
pause
