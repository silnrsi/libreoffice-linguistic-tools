import uno
#import unohelper
import lingt.FileAccess.Utils

def doMain(ctx=uno.getComponentContext()):
    """Main method.  You can call it directly by Tools -> Macros -> Run Macro.
    """
    debug_msg("doMain BEGIN")
    ## Get references to document objects

    unoObjs = UnoObjs()
    # Calling uno.getComponentContext() here causes a bad crash.
    # Apparently in components, it is necessary to use the context provided.
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
        unoObjs.viewcursor, "Hello from TestCenter_mod.", 0)
    lingt.FileAccess.Utils.display(unoObjs)
    debug_msg("doMain END")

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

