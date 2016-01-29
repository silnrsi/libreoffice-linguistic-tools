# vim: set filetype=conf : 
# Created on May 14, 2013 by Jim Kornelsen

#-------------------------------------------------------------------------------
# Testing the code
#-------------------------------------------------------------------------------

I use two different methods for running tests.
The first is easier to run and easier to see errors, and is good for running
tests slowly, one at a time.
This approach is to run OpenOffice listening on a socket.
Use the batch or shell scripts to start OpenOffice and to run the tests,
or enter command line commands that do these things.

The second is to assimilate the code and run from My Macros,
like we can do when running the main OOLT code.
Testing results are written to a file, since stdout is not accessible.
This approach is MUCH faster.
1. Run "assim_deploy.sh tests". This puts all of the python code into a few
   large files, then copies the large files to Scripts/python in the
   OpenOffice or LibreOffice user directory.
2. (optional step) Start OpenOffice listening and run the test from the
   assimilated_code folder. This should give pretty much the same results as
   the first approach, but it allows us to more easily find any bugs caused by
   the assimilation process.
3. From OpenOffice go to Tools -> Macros -> Run macro.

