importClass(Packages.com.sun.star.uno.UnoRuntime);
importClass(Packages.com.sun.star.sheet.XSpreadsheetDocument);
importClass(Packages.com.sun.star.sheet.XSpreadsheetView);
importClass(Packages.com.sun.star.sheet.XSpreadsheet);
importClass(Packages.com.sun.star.frame.XModel);
importClass(Packages.com.sun.star.text.XText);

calcDoc = UnoRuntime.queryInterface(XModel, XSCRIPTCONTEXT.getInvocationContext());
if (!calcDoc)
    calcDoc = XSCRIPTCONTEXT.getDocument();
controller = calcDoc.getCurrentController();
view = UnoRuntime.queryInterface(XSpreadsheetView, controller);
sheet = view.getActiveSheet();
cell = sheet.getCellByPosition(0, 0);
text = UnoRuntime.queryInterface(XText, cell);
cursor = text.createTextCursor();
text.insertString(cursor, "Hello Calc", true);
