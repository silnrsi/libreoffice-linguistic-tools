Set oSM = CreateObject("com.sun.star.ServiceManager")
Set oDesk = oSM.createInstance("com.sun.star.frame.Desktop")
Set oReflection= oSM.createInstance("com.sun.star.reflection.CoreReflection")
Set propVal = oSM._GetValueObject()
propVal.set("object", Null)
Set classPropVal = oReflection.forName("com.sun.star.beans.PropertyValue")
classPropVal.createObject(propVal)
propVal.Name = "ReadOnly"
propVal.Value = True
Dim pPropValues(2)
a = 5
'pProp = oSM.Bridge_GetStruct("PropertyValue")
'pProp = oSM.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
'pPropValues(0) = oSM.Bridge_GetStruct("PropertyValue")
classPropVal.createObject(pPropValues(0))
pPropValues(0).Name = "ReadOnly"
pPropValues(0).Value = True
'pPropValues(1) = oSM.Bridge_GetStruct("PropertyValue")
classPropVal.createObject(pPropValues(1))
pPropValues(1).Name = "Hidden"
pPropValues(1).Value = True

Set oDoc = oDesk.loadComponentFromURL("private:factory/scalc", "_blank", 0, pPropValues())
