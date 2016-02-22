This file created February 22 2016 by Jim Kornelsen.

This directory is used to satisfy PyLint when unable to import uno.
Often this happens on Windows when PyLint is using a different version of
python from that of LibreOffice.

Not needed for actually executing; only use when checking syntax using PyLint.

From @Chris Morgan on stackoverflow.com:

A solution that I have seen employed at my workplace, where there is a special module which Pylint can't possibly get at (Python is embedded and this special module is inside the main executable, while pylint is run in a regular Python installation) is to mock it by creating a .py file and putting it in the python path when running pylint (see PyLint "Unable to import" error - how to set PYTHONPATH?).

So, you might have a "pylint-fakes" directory containing an empty _winreg.py (or if you need to check imported names, not empty but with faked variables).

