#------------------------------------------------------------------------------
# Building the code
#------------------------------------------------------------------------------
I use three different methods for building and running the LOLT extension. The
first is to manually select the folders, zip it up, rename as .oxt and then
double-click to deploy in LibreOffice. This is simple but somewhat tedious
and error-prone.

The second method is similar but more automated. Run create_oxt.ps1,
which zips up the folders and deploys them.
This is a good general purpose method.

For the third method, do not zip the code. Run from the user directory.
1. Go to Tools -> Extension Manager and remove Linguistic Tools if it exists.
2. If the LingToolsBasic library doesn't exist yet,
   go to Tools -> Macros -> Organize Dialogs.
   Under the Library tab, create a library named LingToolsBasic.
   Also, under the Dialogs tab, select LingToolsBasic and create a new
   dialog, because otherwise it doesn't recognize the new library.
   Then close LibreOffice to finish creating the new library.
3. Run deploy_to_userdir.ps1 which copies files to /basic and Scripts/python in
   the LibreOffice user directory.
4. From a LibreOffice document go to Tools -> Macros -> Run macro.
   Do not use the Linguistics menu with this approach.

The benefits of the third approach are:
- Shows helpful error messages instead of silently failing
- Can instantly make small changes for debugging by editing the files in the
  user directory
- Does not deploy as an uno package, so there is less chance of the uno
  package registry getting corrupt when making a large number of changes.
- No need to restart LibreOffice to deploy changes.
  However, to avoid restarting, it is necessary to run aaa_del_sys_modules().
  See tests/ComponentsWrapper.py for details about this function.
  It may still be easier to restart LO to load new code changes.

#------------------------------------------------------------------------------
# Debugging
#------------------------------------------------------------------------------
To enable debugging, set LOGGING_ENABLED and specify a path that exists on
your system. These settings are located in the following files:
1. lingt/utils/util.py
2. Components.py
3. tests/ComponentsWrapper.py

#------------------------------------------------------------------------------
# Testing
#------------------------------------------------------------------------------
See tests/README_testing.py.

#------------------------------------------------------------------------------
# Localization
#------------------------------------------------------------------------------
To search for changes needed, see read_error_messages.pl and
dialog_strings_read.py in the generating_code directory.

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
# Releasing
#------------------------------------------------------------------------------
To release a new .oxt file:
1. Make sure debugging is turned off (see above)
2. It may help to run clean.ps1
3. Increment the version in description.xml
4. Update README.txt with the version history and date.
5. Run create_oxt.ps1
6. Rename the generated .oxt file as LinguisticTools-#.#.oxt
