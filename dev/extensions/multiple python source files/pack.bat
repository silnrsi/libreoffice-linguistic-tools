@echo off

chdir
"C:\Program Files\7-Zip\7z.exe" a -tZip -xr!*.swp MultSrcFile.oxt META-INF Addons.xcu description.xml pythonpath MacroJobs.py
pause
