# created by Jim K on 10-Dec-12
#
# 27-Apr-13 JDK  Added option to start headless.

if [ "$1" == "-headless" ]; then
    echo "Opening headless (use 'pkill loffice' and 'pkill soffice.bin' to end"
    loffice "--accept=socket,host=localhost,port=2002;urp;" --writer --headless --nologo --nofirststartwizard --nolockcheck --norestore &
else
    loffice "--accept=socket,host=localhost,port=2002;urp;" --writer &
fi
