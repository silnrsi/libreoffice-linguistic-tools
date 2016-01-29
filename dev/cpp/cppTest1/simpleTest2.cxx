
/*************************************************************************

"C:\Program Files\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"


cl simpleTest2.cxx /EHsc -Zi /link msvcrt.lib kernel32.lib uuid.lib user32.lib /NODEFAULTLIB:LIBCMT

 *************************************************************************/

#define _UNICODE
#define UNICODE

// For MessageBox
#include <ole2.h>

// First I tried <iostream> but had linking problems with the OOo SDK.
#include <stdio.h>

// To load functions from ECDriver.dll dynamically
#include <windows.h>

// Types for pointers to DLL procedures
typedef BOOL (_stdcall *P_IEI)(void);
    // IsEcInstalled
typedef HRESULT (_stdcall *P_ECSC)(LPWSTR, BOOL&, int&);
    // EncConverterSelectConverterA
typedef HRESULT (_stdcall *P_ECIC)(LPCWSTR, BOOL, int);
    // EncConverterInitializeConverterA
typedef HRESULT (_stdcall *P_ECCS)(LPCWSTR, LPCWSTR, LPWSTR, int);
    // EncConverterConvertStringA

void main()
{
    // Get a handle to the DLL module.
    // Full path is C:\\Program Files\\Common Files\\SIL\\ECDriver.dll
    HINSTANCE hinstLib = LoadLibrary(TEXT("ECDriver.dll"));
    //HINSTANCE hinstLib = LoadLibrary(TEXT("D:\\Jim\\computing\\SEC_on_linux\\ec-main\\src\\ECDriver\\windows\\output\\Debug\\ECDriver.dll"));
    if (hinstLib == NULL)
    {
        return;
    }
    printf("Got handle to DLL.\n");

    P_IEI pIsInstalled = (P_IEI) GetProcAddress(hinstLib, "IsEcInstalled");
    if (!pIsInstalled())
    {
        printf("Not installed.");
        return;
    }
    printf("Is installed.\n");

    P_ECSC pSelectC = (P_ECSC) GetProcAddress(hinstLib,
                                       "EncConverterSelectConverterW");
    if (pSelectC != NULL) printf("Got P_ECSC.\n");

    P_ECCS pConvertS = (P_ECCS) GetProcAddress(hinstLib,
                                        "EncConverterConvertStringW");
    if (pConvertS != NULL) printf("Got P_ECCS.\n");

    // Loading finished.  Now get a converter.

    wchar_t szConverterName[1000];
    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
    int status = pSelectC(szConverterName, bDirectionForward, eNormFormOutput);
    if (status == S_OK)
    {
        printf("Got Converter");
    }
    else
    {
        printf("Didn't get Converter: %d\n", status);
    }

    const wchar_t * InStr1 = L"\u0BAA\u0B9F\u0BAE";

    // Call Convert
    wchar_t szOutput[10000];
    if (pConvertS(szConverterName, InStr1, szOutput, 10000) == S_OK)
    {
        printf("Convert was successful\n");
        //return OUString(RTL_CONSTASCII_USTRINGPARAM(szOutput));
        ::MessageBox(NULL, L"Convert Successful", TEXT("Dbg"), 0x10010);
        ::MessageBox(NULL, szOutput, TEXT("Dbg"), 0x10010);
    }
    else
    {
        printf("Convert failed.");
    }

    FreeLibrary(hinstLib);
}
