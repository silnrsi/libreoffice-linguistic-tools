@rem @echo off
@rem created by Jim Kornelsen on 10-Sep-15
@rem
@rem Sets paths to lingt and lingttest and then runs pylint.

set ADD_ON=C:\OurDocs\computing\Office\OOLT\LinguisticTools
set PYTHONBASE=C:\python33
set PYTHONPATH=%ADD_ON%\pythonpath;%ADD_ON%\tests\pythonpath;%PYTHONBASE%
set PYLINTRC=%USERPROFILE%\.pylintrc_lingttest

start pylint-gui.exe
