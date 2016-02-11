#!/bin/sh
# Created 22-Jul-2011 by Jim K

#python assimilate.py $*
python assimilate.py tests quiet

APPNAME=libreoffice
#APPNAME=openoffice.org
DEPLOYDIR="$HOME/.config/$APPNAME/4/user/Scripts/python/"
cp -v assimilated_code/*.py $DEPLOYDIR
