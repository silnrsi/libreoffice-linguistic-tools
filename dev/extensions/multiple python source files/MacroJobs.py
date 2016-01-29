# cre 9/13/10 by Jim K
import uno
import unohelper
from com.sun.star.task import XJobExecutor

class Macro1Job(unohelper.Base, XJobExecutor):
    """A job class that has a single worker method called trigger().
    It is needed in order to use this file as a component,
    for use as part of an .oxt file.
    """
    def __init__( self, ctx ):
        self.ctx = ctx

    def trigger(self, args):
        # importing it at the top of this file
        # leads to a failure during adding the extension to OOo ???
        debug_msg("----Macro1Job trigger()-----------------------");
        import lingt.UserInterface.TestCenter
        debug_msg("----importing finished-----------------------");
        lingt.UserInterface.TestCenter.doMain(self.ctx)
        debug_msg("----call finished-----------------------");

class Macro2Job(unohelper.Base, XJobExecutor):
    """A job class that has a single worker method called trigger().
    It is needed in order to use this file as a component,
    for use as part of an .oxt file.
    """
    def __init__( self, ctx ):
        self.ctx = ctx

    def trigger(self, args):
        debug_msg("----Macro2Job trigger()-----------------------");
        disp(self.ctx)

def disp(ctx=uno.getComponentContext()):
    unoObjs = UnoObjs()
    unoObjs.ctx         = ctx
    unoObjs.smgr        = unoObjs.ctx.ServiceManager
    unoObjs.desktop     = unoObjs.smgr.createInstanceWithContext(
                          "com.sun.star.frame.Desktop", unoObjs.ctx)
    unoObjs.dispatcher  = unoObjs.smgr.createInstanceWithContext (
                          "com.sun.star.frame.DispatchHelper", unoObjs.ctx)
    unoObjs.frame       = unoObjs.desktop.getCurrentFrame()
    unoObjs.document    = unoObjs.desktop.getCurrentComponent()
    unoObjs.text        = unoObjs.document.Text
    unoObjs.controller  = unoObjs.document.getCurrentController()
    unoObjs.viewcursor  = unoObjs.controller.getViewCursor()

    unoObjs.viewcursor.getText().insertString(
        unoObjs.viewcursor, "Hello from Macro2 trigger().", 0)

DEBUG = True
#DEBUG = False
debug_filepath = "D:\\Jim\\study\\_computing\\Office\\OOo Linguistic Tools" + \
                 "\\debug.txt"
def debug_msg(message):
    """Debugging messages. This is important because UNO can
    be hard to debug, since it often does not show error messages.
    """
    if not DEBUG: return
    import datetime
    try:
        f = open(debug_filepath, 'a')
        datestamp = str(datetime.datetime.now())
        f.write(datestamp + "  " + message + "\n")
        f.close()
    except:
        pass

class UnoObjs:
    """A data structure to hold uno context objects."""
    def __init__(self):
        self.ctx         = None
        self.smgr        = None
        self.desktop     = None
        self.document    = None
        self.frame       = None
        self.dispatcher  = None
        self.text        = None
        self.controller  = None
        self.viewcursor  = None

#-------------------------------------------------------------------------------
# Define as a component so it can be used in an extension.
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    Macro1Job,
    "name.JimK.Dev.Macro1",
    ("com.sun.star.task.Job",),)
g_ImplementationHelper.addImplementation(
    Macro2Job,
    "name.JimK.Dev.Macro2",
    ("com.sun.star.task.Job",),)
# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = disp,

