// The myPuts function writes a null-terminated string to
// the standard output device.
 
// The export mechanism used here is the __declspec(export)
// method supported by Microsoft Visual Studio, but any
// other export method supported by your development
// environment may be substituted.
//
// "C:\Program Files\Microsoft Visual Studio 10.0\VC\vcvarsall.bat"
// cl /o myputs.dll myputs.cpp /link /DLL
/*
If declared _cdecl:
>>> from ctypes import *
>>> mylib = windll.LoadLibrary("myputs.dll")
>>> status = mylib.myPuts("hi there")
h hr  Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ValueError: Procedure probably called with too many arguments (4 bytes in excess)
>>> mylib = cdll.LoadLibrary("myputs.dll")
>>> status = mylib.myPuts("hi there")
Message received by DLL: 'hi there'

However if declared _stdcall:
>>> from ctypes import *
>>> mylib = cdll.myputs
>>> status = mylib.myPuts("hi there")
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "C:\python26\lib\ctypes\__init__.py", line 366, in __getattr__
    func = self.__getitem__(name)
  File "C:\python26\lib\ctypes\__init__.py", line 371, in __getitem__
    func = self._FuncPtr((name_or_ordinal, self))
AttributeError: function 'myPuts' not found
>>> mylib = windll.mylib = windll.myputs
>>> status = mylib.myPuts("hi there")
Message received by DLL: 'hi there'

Now let's try ECDriver:
>>> from ctypes import *
>>> mylib = windll.ECDriver
>>> myfunc = mylib.EncConverterSelectConverterW
>>> a = create_string_buffer(200)
>>> b = c_bool(True)
>>> c = c_long(0)
>>> myfunc(a,b,c)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ValueError: Procedure probably called with too many arguments (12 bytes in exces
s)
-------- Looks so far like ECDriver is declared _cdecl

>>> mylib = cdll.ECDriver
>>> myfunc = mylib.EncConverterSelectConverterW
>>> myfunc(a,b,c)
-18
------- It still acts like it is declared _cdecl
------- However it doesn't seem to really be working -- no dialog window etc.
Looking at ecdriver.h, I think maybe it was declared as:
extern "C" {
__declspec(dllexport) HRESULT __stdcall EncConverterSelectConverterW(
    LPWSTR lpszConverterName, BOOL& bDirectionForward, int& eNormOutputForm);
}
Or maybe _STDCALL_SUPPORTED wasn't defined?
*/
 
#include <stdio.h>
 
extern "C" {          // we need to export the C interface
 
__declspec(dllexport) int __stdcall myPuts(char * sMsg)
{
    printf("Message received by DLL: '%s'\n", sMsg);
    return 1;
}
 
}
