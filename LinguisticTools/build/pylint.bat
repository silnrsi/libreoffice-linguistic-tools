@rem @echo off
@rem created by Jim Kornelsen on 10-Sep-15
@rem
@rem Sets paths to lingt and lingttest and then runs pylint.
@rem Before running, install pylint if not yet done: pip3 install pylint

set ADD_ON=%~dp0\..
set FAKES=%ADD_ON%\build\pylint-fakes
@rem set PYTHONBASE=%ProgramFiles(x86)%\Python36-32
set PYTHONBASE=%ProgramFiles%\Python35
set PYTHONPATH=%ADD_ON%\pythonpath;%ADD_ON%\tests\pythonpath;%PYTHONBASE%;%FAKES%
set PYLINTRC=%USERPROFILE%\.pylintrc_lingttest

start pylint-gui.exe
