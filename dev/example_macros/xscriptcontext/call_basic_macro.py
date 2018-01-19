def call_basic_macro():
    document = XSCRIPTCONTEXT.getDocument()
    frame = document.getCurrentController().getFrame()
    ctx = XSCRIPTCONTEXT.getComponentContext()
    dispatcher = ctx.ServiceManager.createInstanceWithContext(
        'com.sun.star.frame.DispatchHelper', ctx)
    url = document.getURL()
    macro_call = ('macro:///Standard.Module1.Macro1("%s")' % url)
    dispatcher.executeDispatch(frame, macro_call, "", 0, ())

g_exported_scripts=call_basic_macro,
