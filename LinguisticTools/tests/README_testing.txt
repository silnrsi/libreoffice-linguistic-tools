#-------------------------------------------------------------------------------
# Running the tests
#-------------------------------------------------------------------------------
I use two different methods for running tests.
The first is easier to run and easier to see errors, good for running
tests slowly, one at a time.
Start LibreOffice listening on a socket, then run a module from outside of LO.
VS Code can be configured to do these things and run a debugger.
    Use the .vs_code/json files in the dev_extra branch.
    Start LO listening by going to Terminal > Run Task.
    Then press F5 to run currently opened test file.
Or, run start_soffice_listening.bat and drag a module onto run_test.bat.

The second is to run from the user directory,
like the third method described in build/README_build.py.
Testing results are written to a file, since stdout is not accessible.
The file runTestSuite.py can be used to run most tests.
This approach is MUCH faster.
1. Run build/deploy_to_userdir.ps1
2. From Writer go to Tools > Macros > Run macro.
   Specify runTestSuite > aaa_run_all_tests.

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
    + On Windows 10, go to Settings > Font Settings > Download Fonts for
      All Languages.
    + Either download the required fonts or modify the testing code to use
      fonts that are already on your system.
    + See CHANGED_FONT in dataconv_test.py.
- table width
    + Seems to vary somewhat.  If necessary, change values such as
      RESIZE_PERCENT in grammar_test.py.
