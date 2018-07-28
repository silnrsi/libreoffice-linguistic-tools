@rem created by Jim Kornelsen
@rem   25-Apr-13 JDK  AOO on Windows doesn't work with quoted string

c:
@rem chdir "%ProgramFiles(x86)%\OpenOffice 4\program\"
chdir "%ProgramFiles%\LibreOffice\program\"

@rem start ./soffice -accept=socket,host=0,port=2002;urp; %1
start soffice -accept=socket,host=localhost,port=2002;urp; %1

