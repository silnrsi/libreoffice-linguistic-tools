# vim: set filetype=conf : 
# Created on May 14, 2013 by Jim Kornelsen
#
# 23-May-16 JDK  Updated to no longer require assimilation.
# 09-Mar-17 JDK  Added system setup information.

#-------------------------------------------------------------------------------
# Running the tests
#-------------------------------------------------------------------------------

I use two different methods for running tests.
The first is easier to run and easier to see errors, and is good for running
tests slowly, one at a time.
This approach is to run OpenOffice listening on a socket.
Use the batch or shell scripts to start OpenOffice and to run the tests,
or enter command line commands that do these things.

The second is to run from the user directory,
like the third method described in build/README_build.py.
Testing results are written to a file, since stdout is not accessible.
The file runTestSuite.py can be used to run most tests.
This approach is MUCH faster.
1. Run build/deploy_to_userdir.ps1
2. From OpenOffice go to Tools -> Macros -> Run macro.
   Specify runTestSuite -> runTests_myMacros.


#-------------------------------------------------------------------------------
# Setup to get tests to pass
#-------------------------------------------------------------------------------

Typically the tests do not pass the first time because various system settings
are required.  These include:
- adding converters
    + The tests attempt to add converters automatically such as Any-Hex,
      but it often fails, so add them manually.
- version of LibreOffice
    + change getDefaultFont() and getDefaultStyle() in testutil.py if needed.
- different fonts
    + On Windows 10, go to Settings -> Font Settings -> Download Fonts for
      All Languages.
    + Either download the required fonts or modify the testing code to use
      fonts that are already on your system.
    + See CHANGED_FONT in dataconv_test.py.
- table width
    + Seems to vary somewhat.  If necessary, change values such as
      RESIZE_PERCENT in grammar_test.py.

