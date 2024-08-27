@rem ---------------------------------------------------------------------------
@rem Run a python-uno script.
@rem
@rem Before running this batch file, start LibreOffice listening on a socket.
@rem ---------------------------------------------------------------------------

c:
chdir "%ProgramFiles%\LibreOffice\program\"

set ADD_ON=C:\OurDocs\computing\Office\LOLT_dev_extra\LinguisticTools
@rem "." is the current directory and is needed to import uno for AOO.
set PYTHONPATH=%ADD_ON%\pythonpath;%ADD_ON%\tests\pythonpath;.

python.exe %1

@pause
