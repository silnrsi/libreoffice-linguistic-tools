@rem @echo off
@rem created by Jim Kornelsen on 25-March-2019

c:
chdir "%ProgramFiles(x86)%\LibreOffice\program\"

set ADD_ON=C:\OurDocs\computing\Office\OOLT_dev_extra\LinguisticTools
@rem "." is the current directory and is needed to import uno for AOO.
set PYTHONPATH=%ADD_ON%\pythonpath;%ADD_ON%\tests\pythonpath;.

python.exe -V
python.exe %1
@rem python.exe

@pause
