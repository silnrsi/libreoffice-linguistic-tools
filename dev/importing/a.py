"""
To run:
chdir "C:\Program Files\LibreOffice\program"
./python C:\OurDocs\computing\Office\LOLT_dev_extra\dev\importing\a.py
Do not prepend ./ in cmd.exe, as it defaults to the current dir.
"""
# commenting out causes error trying to import in b:
# ModuleNotFoundError: No module named 'com'
#import uno

import b
print("Hello from a")
