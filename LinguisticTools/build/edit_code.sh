#!/bin/sh
# Created 28-Jan-2013 by Jim K
#
# 2019-11-18 JDK  Open files recursively.
#
# Open all code in pythonpath for editing using Vim, with each package in
# a separate window.
#

#BASEPATH="/media/OurDocs/computing/Office/LOLT/LinguisticTools/pythonpath"
BASEPATH="/home/jkornels/LOLT_dev_extra/LinguisticTools/pythonpath"
gvim `find $BASEPATH/lingt/ui/ -name *.py`
# Wait for window to open before opening another one,
# so that it appears in the correct order in the task bar.
sleep 2
gvim `find $BASEPATH/lingt/app/ -name *.py`
sleep 2
gvim `find $BASEPATH/lingt/access/ -name *.py`
sleep 2
gvim `find $BASEPATH/lingt/utils/ -name *.py`
sleep 1
