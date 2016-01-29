#!/bin/sh
#-------------------------------------------------------------------------------
# Created by Jim Kornelsen on July 01 2011
#
# 08-Nov-12 JDK  Add full path to unopkg.
#-------------------------------------------------------------------------------
cd ..

7z a -tZip -xr!*.swp -xr!*.pyc -xr!"developing/assimilated code/*.*" LinguisticTools.oxt developing help LingToolsBasic META-INF pkg-desc pythonpath Addons.xcu Components.py description.xml

UNOPKG=/usr/lib/libreoffice/program/unopkg
$UNOPKG remove name.JimK.LinguisticTools
$UNOPKG add "LinguisticTools.oxt"
