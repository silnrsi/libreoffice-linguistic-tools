#!/bin/sh
# Created 28-Jan-2013 by Jim K
#
# Open all code in pythonpath for editing using Vim, with each package in
# a separate window.
#

BASEPATH="/media/OurDocs/computing/Office/OOLT/LinguisticTools/pythonpath"
gvim "$BASEPATH/lingt/UI/"*.py &
# Wait for window to open before opening another one,
# so that it appears in the correct order in the task bar.
sleep 2
gvim "$BASEPATH/lingt/App/"*.py &
sleep 2
gvim "$BASEPATH/lingt/Access/Writer/"*.py &
sleep 2
gvim "$BASEPATH/lingt/Access/Calc/"*.py &
sleep 2
gvim "$BASEPATH/lingt/Access/PlainText/"*.py &
sleep 2
gvim "$BASEPATH/lingt/Access/Xml/"*.py &
sleep 2
gvim "$BASEPATH/lingt/Access/"*.py &
sleep 2
gvim "$BASEPATH/lingt/Utils/"*.py &
sleep 1

