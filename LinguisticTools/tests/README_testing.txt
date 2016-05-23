# vim: set filetype=conf : 
# Created on May 14, 2013 by Jim Kornelsen
#
# 23-May-16 JDK  Updated to no longer require assimilation.

#-------------------------------------------------------------------------------
# Testing the code
#-------------------------------------------------------------------------------

I use two different methods for running tests.
The first is easier to run and easier to see errors, and is good for running
tests slowly, one at a time.
This approach is to run OpenOffice listening on a socket.
Use the batch or shell scripts to start OpenOffice and to run the tests,
or enter command line commands that do these things.

The second is to run from the user directory,
like we can do when running the main OOLT code.
Testing results are written to a file, since stdout is not accessible.
This approach is MUCH faster.
1. Run build/deploy_to_userdir.ps1
2. From OpenOffice go to Tools -> Macros -> Run macro.
   Specify runTestSuite -> runTests_myMacros.

