#!/bin/sh
#-------------------------------------------------------------------------------
# Run in terminal, for example:
# 1) ./start_soffice_listening.sh
# 2) select Text Document to open
# 3) ./run_test.sh Access/ExUpdater_test.py
#-------------------------------------------------------------------------------

# "." is the current directory and is needed to import uno for AOO.
export PYTHONPATH=.:../pythonpath:./pythonpath

#python $1
#/usr/bin/python3.3 $1
python3 $1
