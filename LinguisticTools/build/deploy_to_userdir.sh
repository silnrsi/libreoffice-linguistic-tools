#!/bin/sh
# Created 22-Jul-2011 by Jim K
# 03-May-16 JDK  Copy to pythonpath instead of assimilating.

APPNAME=libreoffice
#APPNAME=openoffice.org
DEPLOYDIR="$HOME/.config/$APPNAME/4/user/Scripts/python/"
DEPLOY_PYTHONPATH="$DEPLOYDIR/pythonpath"
SRCDIR=".."
TESTDIR="$SRCDIR/tests"

dirs_to_delete=("$DEPLOY_PYTHONPATH/lingt"
                "$DEPLOY_PYTHONPATH/lingttest"
                "$DEPLOY_PYTHONPATH/grantjenks")
for dir in "${dirs_to_delete[@]}"
do
    rm -r $dir
done
mkdir $DEPLOY_PYTHONPATH
cp -v "$SRCDIR/pythonpath/*" $DEPLOY_PYTHONPATH
cp -v "$TESTDIR/pythonpath/*" $DEPLOY_PYTHONPATH
cp -v "$TESTDIR/runTestSuite.py" $DEPLOYDIR
cp -v "$TESTDIR/componentsWrapper.py" $DEPLOYDIR

echo "Copied to $DEPLOYDIR"
