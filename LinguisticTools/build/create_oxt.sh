#!/bin/bash
#-------------------------------------------------------------------------------
#
# Created by Jim Kornelsen on July 01 2011
#
# 08-Nov-12 JDK  Add full path to unopkg.
# 28-Feb-13 JDK  Conditionally don't deploy.
# 11-May-13 JDK  Delete existing archive first, so that it doesn't just add.
# 11-Mar-17 JDK  Do not deploy by default.
# 18-Nov-19 JDK  Array arguments with bash shell.
#
# Build .oxt file.  Specify -deploy to deploy it to Office.
#
#-------------------------------------------------------------------------------
cd "$(dirname "$0")"  # path of script
cd ..

# The .oxt file gets built simply by zipping up the files.
# We use 7-zip to do this.
OxtFile=LinguisticTools.oxt
ZipOptions=(
    a
    -tZip
    -xr!*.swp
    -xr!*.pyc
    -xr!*.stats
    -xr!pylint.txt
    -xr!build/assimilated_code/*.*
)
ZipInput=(
    build
    help
    idl
    LingToolsBasic
    META-INF
    pkg-desc
    pythonpath
    tests
    *.xcu
    Components.py
    description.xml
)
rm $OxtFile
7z ${ZipOptions[@]} $OxtFile ${ZipInput[@]}

if [ "$1" == "-deploy" ]; then
    echo Deploying...
    UNOPKG=/usr/lib/libreoffice/program/unopkg
    $UNOPKG remove name.JimK.LinguisticTools
    $UNOPKG add $OxtFile
fi

