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
cl.exe test_sec_call.cxx /link ECDriver.lib
cl.exe test_sec_call.cxx /MD
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

#include "windows.h"

#define DEBUG true
#define _UNICODE
#define UNICODE

#include "ecdriver.h"

// First I tried <iostream> but had linking problems with the OOo SDK.
#include <stdio.h>
#include <string.h>

wchar_t szConverterName[1000];
bool converterNameSet = false;
BOOL directionForward = TRUE;
int  normFormOutput = 0;

bool      allLoaded = false;
    
// Returns true if a converter has been gotten
bool PickConverter()
{
    printf("PickConverter BEGIN\n");
    if (DEBUG) {
        #ifdef UNICODE
        printf("Unicode defined.\n");
        #else
        printf("Unicode not defined.\n");
        #endif
    }
    if (!IsEcInstalled())
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
    if (EncConverterSelectConverterW(szConverterName, bDirectionForward,
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
    if (!IsEcInstalled())
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
	if (EncConverterInitializeConverterW(szConverterName,
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
    if (EncConverterConvertStringW(szConverterName,
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

    return 0;
}
