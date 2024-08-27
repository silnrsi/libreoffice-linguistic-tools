@rem --------------------------------------------------------------------------
@rem Start LibreOffice listening on a socket,
@rem so scripts can connect to it and execute UNO commands.
@rem --------------------------------------------------------------------------

c:
chdir "%ProgramFiles%\LibreOffice\program\"
start soffice -accept=socket,host=localhost,port=2002;urp; %1
