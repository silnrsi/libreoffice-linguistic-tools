@rem @echo off
@rem created by Jim Kornelsen on 23-Oct-10
@rem
@rem 17-Dec-12 JDK  Running OpenOffice python on listening LibreOffice gives
@rem                unpredictable results.  Use the same app for each side.
@rem 12-Aug-15 JDK  PYTHONPATH should include "."
@rem 18-Aug-15 JDK  Add pythonpath in the tests directory.

c:
@rem chdir "%ProgramFiles(x86)%\OpenOffice 4\program\"
@rem chdir "%ProgramFiles(x86)%\LibreOffice 5\program\"
chdir "%ProgramFiles%\LibreOffice 5\program\"

@rem set ADD_ON=C:\OurDocs\computing\Office\OOLT\LinguisticTools
set ADD_ON=D:\dev\OOLT\LinguisticTools
@rem "." is the current directory and is needed to import uno for AOO.
set PYTHONPATH=%ADD_ON%\pythonpath;%ADD_ON%\tests\pythonpath;.

python.exe -V
python.exe %1
@rem python.exe

@pause
