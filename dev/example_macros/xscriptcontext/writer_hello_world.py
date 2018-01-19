def hello():
    """From:
    wiki.openoffice.org/wiki/Python/Transfer_from_Basic_to_Python
    """
    XSCRIPTCONTEXT.getDocument().getText().setString("Hello!")

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = hello,
