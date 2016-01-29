@echo off

chdir
"C:\Program Files\7-Zip\7z.exe" a -tZip -xr!*.swp -r RefNumbersForFlex.zip *.py Help.* History.txt
pause
