# Created on 18-Jul-2011 by Jim K

#-------------------------------------------------------------------------------
# Building the code
#-------------------------------------------------------------------------------

I use three different methods for building and testing this extension.  The
first is to manually select the folders, zip it up, rename as .oxt and then
double-click to deploy.  This is simple but somewhat tedious.

The second method is similar but more automated.  Run pack_redeploy.bat, which
automatically zips up the folders and deploys them.

The third is a different approach, more complex but with several benefits for
the developer.
1. Run assimilate.bat to put all of the python code into a few large files.
2. Run assim_deploy.bat to copy the large files to Scripts/python in the
   OpenOffice or LibreOffice user directory.
3. From OpenOffice go to Tools -> Macros -> Run macro.

The benefits of the third approach are:
- Shows errors without silently failing
- No need to restart OpenOffice to deploy changes
- Fast to deploy
- Can instantly make small changes for debugging

