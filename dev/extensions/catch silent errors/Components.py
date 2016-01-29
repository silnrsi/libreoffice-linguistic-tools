#!/usr/bin/python
# -*- coding: Latin-1 -*-

# Components.py
#              
# Change History:
#   Created Sept 14 2010 by Jim Kornelsen
#
#   08-Jul-11 JDK  Added Script Practice.
#   25-Oct-12 JDK  Added Word List and Spelling Changes.
#
#
#
#
#
# Hacked 30-Nov-2012 for testing by Jim.
#
#
#
#
#
#
#

"""
Handles the events from the Linguistics menu,
defined in Addons.xcu.

Python OOo scripts in extensions must be implemented as PyUNO components,
and this file contains the component definitions.

Scripts are imported from the pythonpath subfolder,
which OOo automatically adds to the path.
The import from this file must be done at runtime or else it
leads to a failure during adding the extension to OOo.
Scripts in the pythonpath subfolder will not be reloaded until OOo is
completely closed and restarted.

There are no functions in this file to be run from Tools -> Macros -> Run.
Instead, run one of the ShowDlg() functions, for example in
pythonpath/lingt/UI/DlgAbbreviations.py
"""

import uno
import unohelper

# A job class that has a single worker method called trigger(), which will
# be called to execute the component.
from com.sun.star.task import XJobExecutor

class SimpleLingtJob(unohelper.Base, XJobExecutor):
    def __init__( self, ctx ):
        self.ctx = ctx
    def trigger(self, args):
        from lingt.UI.DlgSimple import ShowDlg
        ShowDlg(self.ctx)

#-------------------------------------------------------------------------------
# Define the components in this script.
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    SimpleLingtJob,
    "name.JimK.LinguisticTools.SimpleJob", \
    ("com.sun.star.task.Job",),)

