#------------------------------------------------------------------------------
# Start LibreOffice listening on a socket,
# so scripts can connect to it and execute UNO commands.
#------------------------------------------------------------------------------

if [ "$1" == "-headless" ]; then
    echo "Opening headless (use 'pkill loffice' and 'pkill soffice.bin' to end"
    loffice "--accept=socket,host=localhost,port=2002;urp;" --writer --headless --nologo --nofirststartwizard --nolockcheck --norestore &
else
    loffice "--accept=socket,host=localhost,port=2002;urp;" --writer &
fi
