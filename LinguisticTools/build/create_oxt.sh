#!/bin/sh
#-------------------------------------------------------------------------------
#
# Created by Jim Kornelsen on July 01 2011
#
# 08-Nov-12 JDK  Add full path to unopkg.
# 28-Feb-13 JDK  Conditionally don't deploy.
# 11-May-13 JDK  Delete existing archive first, so that it doesn't just add.
# 11-Mar-17 JDK  Do not deploy by default.
#
# Build .oxt file.  Specify -deploy to deploy it to Office.
#
#-------------------------------------------------------------------------------
cd ..

rm "LinguisticTools.oxt"
7z a -tZip -xr!*.swp -xr!*.pyc -xr!*.stats -xr!pylint.txt \
-xr!"build/assimilated_code/*.*" \
LinguisticTools.oxt build help idl LingToolsBasic META-INF pkg-desc \
pythonpath tests *.xcu Components.py description.xml

if [ "$1" == "-deploy" ]; then
    echo Deploying...
    UNOPKG=/usr/lib/libreoffice/program/unopkg
    $UNOPKG remove name.JimK.LinguisticTools
    $UNOPKG add "LinguisticTools.oxt"
fi

