# -*- coding: Latin-1 -*-
#
# This file created Sept 15 2010 by Jim Kornelsen
#
# 26-Oct-10 JDK  Do not allow directories or symbolic links.
# 19-Nov-12 JDK  Option to Save instead of Open.
# 26-Nov-12 JDK  Option to specify filters or default filename.
# 21-Dec-12 JDK  Fixed bug: Default filters value [] works in this case.
# 29-Jul-13 JDK  Import constants instead of using uno.getConstantByName.
# 16-Dec-15 JDK  Added folder picker.
# 16-Jun-20 JDK  Initialize first or else it defaults to opening.

"""
Display a dialog to select a file.

This module exports:
    showFilePicker()
    showFolderPicker()
"""
import logging
import os.path

import uno
from com.sun.star.ui.dialogs.TemplateDescription import (
    FILEOPEN_SIMPLE, FILESAVE_SIMPLE)
from com.sun.star.ui.dialogs.ExecutableDialogResults import OK as _RESULT_OK

from lingt.utils import util

logger = logging.getLogger("lingt.ui.filepicker")


def showFilePicker(genericUnoObjs, save=False, filters=None,
                   defaultFilename=None):
    logger.debug(util.funcName('begin'))

    # Create a FilePicker dialog.
    dlg = genericUnoObjs.smgr.createInstanceWithContext(
        "com.sun.star.ui.dialogs.FilePicker", genericUnoObjs.ctx)
    if save:
        dlgType = FILESAVE_SIMPLE
    else:
        dlgType = FILEOPEN_SIMPLE
    dlg.initialize((dlgType,))
    if filters:
        for name, ext in filters:
            dlg.appendFilter(name, ext)
    if defaultFilename:
        logger.debug("Default filename %s", defaultFilename)
        dlg.setDefaultName(defaultFilename)

    # Execute it.
    dlg.execute()

    # Get an array of the files that the user picked.
    # There will only be one file in this array, because we did
    # not enable the multi-selection feature.
    filesList = dlg.getFiles()
    filepath = ""
    if filesList != None and len(filesList) > 0:
        filepath = filesList[0]
        filepath = uno.fileUrlToSystemPath(filepath)
        if os.path.exists(filepath):
            if os.path.isdir(filepath) or os.path.islink(filepath):
                logger.warning("'%s' is not an ordinary file", filepath)
                filepath = ""
    logger.debug(util.funcName('end', args=filepath))
    return filepath


def showFolderPicker(genericUnoObjs, defaultFoldername=None):
    logger.debug(util.funcName('begin'))
    dlg = genericUnoObjs.smgr.createInstanceWithContext(
        "com.sun.star.ui.dialogs.FolderPicker", genericUnoObjs.ctx)
    if defaultFoldername:
        logger.debug("Default foldername %s", defaultFoldername)
        dlg.setDisplayDirectory(defaultFoldername)
    result = dlg.execute()

    # Get results.
    folderpath = ""
    if result == _RESULT_OK:
        folderpath = dlg.getDirectory()
        folderpath = uno.fileUrlToSystemPath(folderpath)
        if os.path.exists(folderpath):
            if os.path.isfile(folderpath) or os.path.islink(folderpath):
                logger.warning("'%s' is not a folder", folderpath)
                folderpath = ""
    logger.debug(util.funcName('end', args=folderpath))
    return folderpath
