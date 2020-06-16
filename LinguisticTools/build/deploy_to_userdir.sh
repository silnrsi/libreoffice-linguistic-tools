#!/bin/bash
#-------------------------------------------------------------------------------
#
# Created 22-Jul-2011 by Jim Kornelsen
#
# 03-May-16 JDK  Copy to pythonpath instead of assimilating.
# 09-Mar-17 JDK  Also copy dialogs.
#
# Copy code the LO/AOO user directory, so it can be run from Tools -> Macros.
#
# Before running on a new user directory,
# go into Tools -> Macros -> Organize Dialogs,
# and create a library called LingToolsBasic.
# Close LibreOffice, which will modify basic/dialog.xlc.
#
#-------------------------------------------------------------------------------

if [ "$1" == "-openoffice" ]; then
    APPNAME=openoffice.org
else
    APPNAME=libreoffice
fi
DEPLOYDIR="$HOME/.config/$APPNAME/4/user"
DEPLOY_PY="$DEPLOYDIR/Scripts/python"
DEPLOY_PYTHONPATH="$DEPLOY_PY/pythonpath"
SRCDIR=".."
TESTDIR="$SRCDIR/tests"

dirs_to_delete=("$DEPLOY_PYTHONPATH/lingt"
                "$DEPLOY_PYTHONPATH/lingttest"
                "$DEPLOY_PYTHONPATH/grantjenks")
for dir in "${dirs_to_delete[@]}"
do
    rm -rf $dir
done
mkdir -p $DEPLOY_PYTHONPATH
cp -r "$SRCDIR/pythonpath/"* $DEPLOY_PYTHONPATH
cp -r "$TESTDIR/pythonpath/"* $DEPLOY_PYTHONPATH
cp -v "$TESTDIR/runTestSuite.py" $DEPLOY_PY
cp -v "$TESTDIR/ComponentsWrapper.py" $DEPLOY_PY

DEPLOY_BASIC="$DEPLOYDIR/basic/LingToolsBasic"
cp "$SRCDIR/LingToolsBasic/"* $DEPLOY_BASIC

echo "Copied to $DEPLOYDIR"
