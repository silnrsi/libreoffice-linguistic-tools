#!/bin/sh
# Created May 11, 2013 by Jim K
#
# Open all testing code for editing using Vim, with each package in
# a separate window.
#

BASEPATH="/media/OurDocs/computing/Office/LOLT/LinguisticTools/developing/tests"
gvim "$BASEPATH/"*.py &
# Wait for window to open before opening another one,
# so that it appears in the correct order in the task bar.
sleep 2
gvim "$BASEPATH/lingttest/UI/"*.py &
sleep 2
gvim "$BASEPATH/lingttest/App/"*.py &
sleep 2
gvim "$BASEPATH/lingttest/Access/"*.py &
sleep 2
gvim "$BASEPATH/lingttest/TopDown/"*.py &
sleep 2
gvim "$BASEPATH/lingttest/Utils/"*.py &
sleep 1

