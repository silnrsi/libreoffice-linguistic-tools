# vim: set filetype=conf :
#
# Created on 18-Jul-2011 by Jim Kornelsen.
# 12-Dec-15 JDK  Added info about dialogs and releasing a new version.
# 03-May-16 JDK  No need to assimilate code.
# 07-Mar-17 JDK  Add testing information.
# 09-Mar-17 JDK  Moved testing information to README_testing.txt.

#------------------------------------------------------------------------------
# Building the code
#------------------------------------------------------------------------------

I use three different methods for building and running the OOLT extension.  The
first is to manually select the folders, zip it up, rename as .oxt and then
double-click to deploy in LibreOffice.  This is simple but somewhat tedious.

The second method is similar but more automated.  Run create_oxt.ps1,
which zips up the folders and deploys them.
This is a good general purpose method.

For the third method, do not zip it.  Run it from the user directory:
1. Go to Tools -> Extension Manager and remove Linguistic Tools if it exists.
2. Go to Tools -> Macros -> Organize Dialogs.
   Under the Library tab, create a library named LingToolsBasic.
   Also under the Dialogs tab, I selected LingToolsBasic and created a new
   dialog, because otherwise it didn't seem to notice the new library.
   Also, copy the LinguisticTools/LingToolsBasic folder to <user dir>/basic.
3. Run deploy_to_userdir.ps1 which copies files to Scripts/python in
   the OpenOffice or LibreOffice user directory.
4. From OpenOffice go to Tools -> Macros -> Run macro.
   Do not use the Linguistics menu with this approach.

The benefits of the third approach are:
- Shows helpful error messages instead of silently failing
- Can instantly make small changes for debugging by editing the files in the
  user directory
- Does not deploy as an uno package, so there is less chance of the uno
  package registry getting corrupt when making a large number of changes.
- No need to restart OpenOffice to deploy changes.
  However, to avoid restarting, it is necessary to run aaa_del_sys_modules().
  See tests/ComponentsWrapper.py for details about this function.


#------------------------------------------------------------------------------
# Releasing
#------------------------------------------------------------------------------
When releasing a new .oxt file:
1. Make sure debugging is turned off (see below).
2. It may help to run clean.ps1
3. Increment the version in description.xml
4. Update README.txt with the version history and date.
5. Rename the generated .oxt file as LinguistcTools-#.#.oxt


#------------------------------------------------------------------------------
# Dialog notes
#------------------------------------------------------------------------------
To make a new dialog window:
1. deploy current extension if not yet done
2. create new dialog in LibreOffice under LingToolsBasic module
3. go to the uno_packages subfolder of the LibreOffice user directory,
   and copy the new dialog file, modified .xlb file, and modified language
   translation files to LingToolsBasic.

To modify the dialog:
1. Tools -> Dialogs, make changes and save them.
2. Find the changed file under uno_packages and copy the .xdl file.
   Also grab the new translated strings from the .properties files.
3. Compare or replace files in LingToolsBasic.


#------------------------------------------------------------------------------
# Localization
#------------------------------------------------------------------------------
To search for changes needed, see read_error_messages.pl and
dialog_strings_read.pl in the generating_code directory.


#------------------------------------------------------------------------------
# Testing and Debugging
#------------------------------------------------------------------------------
See tests/README_testing.py.

To enable debugging, set LOGGING_ENABLED and specify a path that exists on
your system.  These settings are located in the following files:
1. lingt/utils/util.py
2. Components.py
3. tests/ComponentsWrapper.py
