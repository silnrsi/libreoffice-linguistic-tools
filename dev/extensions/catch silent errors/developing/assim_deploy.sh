#!/bin/sh
# Created 22-Jul-2011 by Jim K

perl assimilate.pl

APPNAME=libreoffice
#APPNAME=openoffice.org
DEPLOYDIR="/home/jkornelsen/.config/$APPNAME/3/user/Scripts/python/"
cp -v assimilated*code/*.py $DEPLOYDIR

