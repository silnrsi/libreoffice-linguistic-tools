#!/bin/sh
#-------------------------------------------------------------------------------
# Created by Jim Kornelsen on July 01 2011
#
# 08-Nov-12 JDK  Add full path to unopkg.
# 28-Feb-13 JDK  Conditionally don't deploy.
# 11-May-13 JDK  Delete existing archive first, so that it doesn't just add.
#-------------------------------------------------------------------------------
cd ..

rm "LinguisticTools.oxt"
7z a -tZip -xr!*.swp -xr!*.pyc -xr!*.stats -xr!pylint.txt \
-xr!"developing/assimilated_code/*.*" \
LinguisticTools.oxt developing help idl LingToolsBasic META-INF pkg-desc \
pythonpath tests *.xcu Components.py description.xml

if [ "$1" != "-nodeploy" ]; then
    echo Deploying...
    UNOPKG=/usr/lib/libreoffice/program/unopkg
    $UNOPKG remove name.JimK.LinguisticTools
    $UNOPKG add "LinguisticTools.oxt"
else
    echo Not Deploying
fi

