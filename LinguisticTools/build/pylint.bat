@rem @echo off
@rem
@rem Sets paths to lingt and lingttest and then runs pylint.
@rem Before running, install pylint if not yet done: pip3 install pylint

set ADD_ON=%~dp0\..
set FAKES=%ADD_ON%\build\pylint-fakes
set PYTHONBASE=%ProgramFiles%\Python312
set PYTHONPATH=%ADD_ON%\pythonpath;%ADD_ON%\tests\pythonpath;%PYTHONBASE%;%FAKES%
set PYLINTRC=%USERPROFILE%\.pylintrc_lingttest

start pylint-gui.exe
