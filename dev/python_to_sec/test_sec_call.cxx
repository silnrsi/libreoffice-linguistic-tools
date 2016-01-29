/*************************************************************************
 *
 *
 *
 *
 *
 *
 *
 * Hacked 03-Nov-2011 for testing.
 *
"C:\Program Files\Microsoft Visual Studio 10.0\VC\vcvarsall.bat"
"C:\Program Files\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"
cl.exe test_sec_call.cxx
 *
 *
 *
 *
 *
 *
 * sec_call_impl.cxx
 *
 * An OOo UNO component that calls SIL EncConverters (SEC) with COM.
 * This is needed because there were problems when making COM calls directly
 * from OOo Basic or python.
 *
 * To build, see "How to build this code.txt"
 *
 * For an explanation of C++ UNO components, see the CppComponent example in
 * the OOo Developer's guide, and the corresponding code in the OOo SDK.
 * This code is based on that example.
 * For an explanation of COM in C++, search MSDN on the internet.
 *
 * History:
 *  Created by Jim Kornelsen on 2/23/2010.
 *
 *  03/01/2010 JDK  Retrieve direction and normalize attributes.
 *
 *************************************************************************/

#define DEBUG true
#define _UNICODE
#define UNICODE

// For MessageBox
#include <ole2.h>

// First I tried <iostream> but had linking problems with the OOo SDK.
#include <stdio.h>
#include <string.h>

// To load functions from ECDriver.dll dynamically
#include <windows.h>

// Types for pointers to DLL procedures
typedef BOOL (_stdcall *P_IEI)(void);
    // IsEcInstalled
typedef HRESULT (_stdcall *P_ECSC)(LPWSTR, BOOL&, int&);
    // EncConverterSelectConverterW
typedef HRESULT (_stdcall *P_ECIC)(LPCWSTR, BOOL, int);
    // EncConverterInitializeConverterW
typedef HRESULT (_stdcall *P_ECCS)(LPCWSTR, LPCWSTR, LPWSTR, int);
    // EncConverterConvertStringW

wchar_t szConverterName[1000];
bool converterNameSet = false;
BOOL directionForward = TRUE;
int  normFormOutput = 0;

HINSTANCE hinstLib = NULL;
bool      allLoaded = false;
    
P_IEI  pIsInstalled;
P_ECSC pSelectC;
P_ECIC pInitC;
P_ECCS pConvertS;

bool Load_DLL_Procs()
{
    if (DEBUG) {
        printf("Load_DLL_Procs BEGIN\n");
    }
    if (allLoaded)
    {
        // Nothing needs to be done.
        return true;
    }
    allLoaded = true;

    // Get a handle to the DLL module.
    // Full path is C:\\Program Files\\Common Files\\SIL\\ECDriver.dll
    HINSTANCE hinstLib = LoadLibrary(TEXT("ECDriver.dll"));
    if (hinstLib == NULL)
    {
        allLoaded = false;
        return false;
    }
    if (DEBUG) {
        printf("Got handle to DLL.\n");
    }

    pIsInstalled = (P_IEI) GetProcAddress(hinstLib, "IsEcInstalled");
    if (pIsInstalled == NULL) {
        allLoaded = false;
        if (DEBUG) printf("Didn't get P_IEI.\n");
    } else {
        if (DEBUG) printf("Got P_IEI.\n");
    }

    pSelectC = (P_ECSC) GetProcAddress(hinstLib,
                                       "EncConverterSelectConverterW");
    if (pSelectC == NULL) {
        allLoaded = false;
        if (DEBUG) printf("Didn't get P_ECSC.\n");
    } else {
        if (DEBUG) printf("Got P_ECSC.\n");
    }

    pInitC = (P_ECIC) GetProcAddress(hinstLib,
                                    "EncConverterInitializeConverterW");
    if (pInitC == NULL) {
        allLoaded = false;
        if (DEBUG) printf("Didn't get P_ECIC.\n");
    } else {
        if (DEBUG) printf("Got P_ECIC.\n");
    }

    pConvertS = (P_ECCS) GetProcAddress(hinstLib,
                                        "EncConverterConvertStringW");
    if (pConvertS == NULL) {
        allLoaded = false;
        if (DEBUG) printf("Didn't get P_ECCS.\n");
    } else {
        if (DEBUG) printf("Got P_ECCS.\n");
    }

    if (DEBUG) printf("Load_DLLs finished.\n");
    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
    printf("Calling SelectConverter.\n");
    if (pSelectC(szConverterName, bDirectionForward,
                 eNormFormOutput) == S_OK)
    {
        if (DEBUG) {
            printf("Converter was successfully selected.\n");
            printf("%s\n", szConverterName);
        }
        directionForward = bDirectionForward;
        normFormOutput   = eNormFormOutput;
        converterNameSet = true;
        return true;
    }
    if (DEBUG) {
        printf("Converter was not selected.  User must have pressed cancel.\n");
    }

    return allLoaded;
}

// Returns true if a converter has been gotten
bool PickConverter()
{
    printf("PickConverter BEGIN\n");
    if (!Load_DLL_Procs())
    {
        printf("Cannot find SIL Converters on this computer.");
        return false;
    }
    if (DEBUG) {
        printf("DLLs loaded.\n");
        #ifdef UNICODE
        printf("Unicode defined.\n");
        #else
        printf("Unicode not defined.\n");
        #endif
        #if defined(_STDCALL_SUPPORTED)
        printf("stdcall supported\n");
        #else
        printf("stdcall not supported\n");
        #endif
        #ifdef __cplusplus
        printf("cplusplus\n");
        #else
        printf("not cplusplus\n");
        #endif
    }
    if (!pIsInstalled())
    {
        printf("SIL Converters is not installed properly.\n");
        return false;
    }
    if (DEBUG) {
        printf("EC is installed.\n");
    }

    // Setting the bDirectionForward (BOOL) to TRUE is not strictly necessary,
    // since that value is ignored by the function and whatever the user has
    // chosen will be returned in that variable.
    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
    printf("Calling SelectConverter.\n");
    if (pSelectC(szConverterName, bDirectionForward,
                 eNormFormOutput) == S_OK)
    {
        if (DEBUG) {
            printf("Converter was successfully selected.\n");
            printf("%s\n", szConverterName);
        }
        directionForward = bDirectionForward;
        normFormOutput   = eNormFormOutput;
        converterNameSet = true;
        return true;
    }
    if (DEBUG) {
        printf("Converter was not selected.  User must have pressed cancel.\n");
    }
    return false;
}

// Returns true if a converter has been successfuly set
bool SetConverter(
    wchar_t * inStr, bool directionFw, int normalize)
{
    if (!Load_DLL_Procs())
    {
        printf("Cannot find SIL Converters on this computer.\n");
        return false;
    }
    if (!pIsInstalled())
    {
        printf("SIL Converters is not installed properly.\n");
        return false;
    }
    if (DEBUG) printf("EC seems to be installed.\n");

    wcscpy(szConverterName, inStr);
    converterNameSet = true;
    if (DEBUG) printf("Converter name set.\n");

	// initialize the converter based on these stored configuration
    // properties (but beware, it may no longer be installed!
    // So do something in the 'else' case to inform user)
    BOOL bDirectionForward = directionFw;
    int eNormFormOutput    = normalize;
	if (pInitC(szConverterName,
               bDirectionForward, eNormFormOutput) == S_OK)
	{
        if (DEBUG) printf("Converter was successfully selected.\n");
        directionForward = bDirectionForward;
        normFormOutput   = eNormFormOutput;
        return true;
    }
    if (DEBUG) printf("Converter was not initialized.\n");
    printf("The converter could not be initialized. Please try again.\n"),
    converterNameSet = false;
    return false;
}

wchar_t * Convert( wchar_t * szInput )
{
    if (DEBUG) printf("Convert BEGIN\n");
    if(!converterNameSet)
    {
        printf("No converter was specified.\n");
        return L"";
    }

    // Call Convert
    wchar_t szOutput[10000];
    if (pConvertS(szConverterName,
                  szInput, szOutput, 10000) == S_OK)
    {
        if (DEBUG) printf("Convert was successful\n");
        return szOutput;
    }
    if (DEBUG) printf("Convert failed\n");
    return L"";
}

int main() {
    // PickConverter()
    bool success = PickConverter();
    printf("PickConverter finished.\n");
    printf("PickConverter returned %s\n",
           success ? "true" : "false");

    // Convert()
    wchar_t sInput[] = L"aBcDe";
    //wchar_t * s = Convert(L"\u0BAA\u0B9F\u0BAE");
    wchar_t * sOut = Convert(sInput);
    wprintf(L"Convert() = %s\n", sOut);

    if (hinstLib != NULL)
    {
        FreeLibrary(hinstLib);
    }
    return 0;
}
