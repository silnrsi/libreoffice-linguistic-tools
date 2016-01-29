@rem created by Jim Kornelsen
@rem   25-Apr-13 JDK  AOO on Windows doesn't work with quoted string

c:
chdir "%ProgramFiles(x86)%\OpenOffice 4\program\"
@rem chdir "%ProgramFiles(x86)%\LibreOffice 5\program\"

start soffice -accept=socket,host=0,port=2002;urp; %1

