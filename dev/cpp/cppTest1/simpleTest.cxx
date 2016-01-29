
/*************************************************************************

"C:\Program Files\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"


cl simpleTest.cxx /EHsc /link msvcrt.lib kernel32.lib uuid.lib user32.lib /NODEFAULTLIB:LIBCMT

set PATH=%PATH%;C:\Program Files\OpenOffice.org 3\URE\bin

 *************************************************************************/

#define PRINT_DEBUG_MESSAGES

// For MessageBox
#include <ole2.h>

// First I tried <iostream> but had linking problems with the OOo SDK.
#include <stdio.h>

// To load functions from ECDriver.dll dynamically
#include <windows.h>

// Types for pointers to DLL procedures
typedef BOOL (_stdcall *P_IEI)(void);
    // IsEcInstalled

void main()
{
    P_IEI  pIsInstalled;

    // Get a handle to the DLL module.
    // Full path is C:\\Program Files\\Common Files\\SIL\\ECDriver.dll
    const char * dllFile = "ECDriver.dll";
    HINSTANCE hinstLib = LoadLibrary(TEXT(dllFile));
    if (hinstLib == NULL)
    {
        return;
    }
    printf("Got handle to DLL.\n");

    pIsInstalled = (P_IEI) GetProcAddress(hinstLib, "IsEcInstalled");
    if (pIsInstalled == NULL) {
        printf("Didn't get P_IEI");
    } else {
        printf("Got P_IEI");
    }

    (pIsInstalled)();
    printf("Finished call to pIsInstalled.\n");

    BOOL result = pIsInstalled();
    if (result)
        printf("Is installed.");
    else
        printf("Not installed.");
}
