#!/usr/bin/python
# -*- coding: Latin-1 -*-

# FilePicker.py
#
# Change History:
#   Created Sept 15 2010 by Jim Kornelsen
#
#   26-Oct-10 JDK  Do not allow directories or symbolic links.
#   19-Nov-12 JDK  Option to Save instead of Open.
#   26-Nov-12 JDK  Option to specify filters or default filename.

"""
Display a dialog to select a file.
"""
import uno
import unohelper
import logging
import os.path

def showFilePicker(unoObjs, save=False, filters=None, defaultFilename=None):
    """Adapted from DannyB 2008"""
    logger = logging.getLogger("lingt.UI.FilePicker")
    logger.debug("showFilePicker begin")

    # Create a FilePicker dialog.
    dlg  = unoObjs.smgr.createInstanceWithContext(
           "com.sun.star.ui.dialogs.FilePicker", unoObjs.ctx)
    for name, ext in filters:
        dlg.appendFilter(name, ext)
    if defaultFilename:
        logger.debug("Default filename %s" % (defaultFilename)) 
        dlg.setDefaultName(defaultFilename)
    if save:
        dlgType = uno.getConstantByName(
            "com.sun.star.ui.dialogs.TemplateDescription.FILESAVE_SIMPLE")
    else:
        dlgType = uno.getConstantByName(
            "com.sun.star.ui.dialogs.TemplateDescription.FILEOPEN_SIMPLE")
    # Initialization is required for OOo3.0 on Vista
    dlg.initialize((dlgType,))

    # Execute it.
    dlg.execute()

    # Get an array of the files that the user picked.
    # There will only be one file in this array, because we did
    # not enable the multi-selection feature.
    filesList = dlg.getFiles()
    filepath = ""
    if filesList != None and len(filesList) > 0:
        filepath = filesList[0]
        # this line is like convertFromURL in OOo Basic
        filepath = unohelper.fileUrlToSystemPath(filepath)
        if os.path.exists(filepath):
            if os.path.isdir(filepath) or os.path.islink(filepath):
                # no file was selected
                filepath = ""
    logger.debug("filepath = " + filepath)
    return filepath

