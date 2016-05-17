def replace():
    XSCRIPTCONTEXT.getDocument().getText().setString(
        "abc search for defghi search for kll mno")

    document = XSCRIPTCONTEXT.getDocument()
    search = document.createSearchDescriptor()
    search.SearchString = "search for"
    search.SearchAll = True
    search.SearchWords = True
    search.SearchCaseSensitive = False
    selsFound = document.findAll(search)
    if selsFound.getCount() == 0:
        return
    for selIndex in range(0, selsFound.getCount()):
        selFound = selsFound.getByIndex(selIndex)
        selFound.setString("change to")


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = replace,    

