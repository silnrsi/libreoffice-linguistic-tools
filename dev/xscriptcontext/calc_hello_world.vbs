Set oSM = CreateObject("com.sun.star.ServiceManager")
Set oDesk = oSM.createInstance("com.sun.star.frame.Desktop")
Dim arg()
Set wb = oDesk.loadComponentFromURL("private:factory/scalc", "_blank", 0, arg)
Set oSheet = wb.CurrentController.ActiveSheet
oSheet.getCellByPosition(1, 2).String = "Hello world!"
MsgBox "The End"

