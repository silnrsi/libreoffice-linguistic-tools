/*************************************************************************

"C:\Program Files\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"


cl sec_call_impl.cxx -I"C:\Program Files\OpenOffice.org 3 SDK\sdk\include" -I"C:\openoffice.org3.3_sdk\WINlingtools.out\inc" /EHsc /link msvcrt.lib kernel32.lib uuid.lib user32.lib isal.lib icppu.lib ireg.lib /LIBPATH:"C:\Program Files\OpenOffice.org 3 SDK\sdk\lib" /NODEFAULTLIB:LIBCMT

set PATH=%PATH%;C:\Program Files\OpenOffice.org 3\URE\bin

 *************************************************************************/

#define PRINT_DEBUG_MESSAGES

#define WIN32
#define WNT

// For MessageBox
#include <ole2.h>

// First I tried <iostream> but had linking problems with the OOo SDK.
#include <stdio.h>

// To load functions from ECDriver.dll dynamically
#include <windows.h>

// These libraries are all needed for OOo components
#include <osl/interlck.h>
#include <osl/mutex.hxx>
#include <rtl/uuid.h>
#include <cppuhelper/implbase3.hxx> // "3" implementing three interfaces
#include <cppuhelper/factory.hxx>
#include <cppuhelper/implementationentry.hxx>
#include <com/sun/star/lang/XServiceInfo.hpp>
#include <com/sun/star/lang/XTypeProvider.hpp>

using namespace ::rtl; // for OUString
using namespace ::com::sun::star; // for odk interfaces
using namespace ::com::sun::star::uno; // for basic types

// Types for pointers to DLL procedures
typedef BOOL (_stdcall *P_IEI)(void);
    // IsEcInstalled
typedef HRESULT (_stdcall *P_ECSC)(LPWSTR, BOOL&, int&);
    // EncConverterSelectConverterW
typedef HRESULT (_stdcall *P_ECIC)(LPCWSTR, BOOL, int);
    // EncConverterInitializeConverterW
typedef HRESULT (_stdcall *P_ECCS)(LPCWSTR, LPCWSTR, LPWSTR, int);
    // EncConverterConvertStringW

class SEC_Call_Impl
{
private:
    wchar_t szConverterName[1000];
    bool converterNameSet;

    P_IEI  pIsInstalled;
    P_ECSC pSelectC;
    P_ECIC pInitC;
    P_ECCS pConvertS;

public:
    inline SEC_Call_Impl()
    {
        this->converterNameSet = false;
    }

    inline ~SEC_Call_Impl() throw ()
    {
    }
    
    bool Load_DLL_Procs();

    // XCallableSEC
    virtual sal_Bool SAL_CALL PickConverter( )
        throw (RuntimeException);
    virtual sal_Bool SAL_CALL SetConverter( OUString const & str )
        throw (RuntimeException);
    virtual OUString SAL_CALL GetName( )
        throw (RuntimeException);
    virtual OUString SAL_CALL Convert( OUString const & str )
        throw (RuntimeException);
};

bool SEC_Call_Impl::Load_DLL_Procs()
{
    bool allLoaded = true;
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Load_DLL_Procs BEGIN\n");
    ::MessageBox(NULL, TEXT("Load_Procs BEGIN."), TEXT("Dbg"), 0x10010);
    #endif

    // Get a handle to the DLL module.
    // Full path is C:\\Program Files\\Common Files\\SIL\\ECDriver.dll
    const char * dllFile = "ECDriver.dll";
    HINSTANCE hinstLib = LoadLibrary(TEXT(dllFile));
    if (hinstLib == NULL)
    {
        return false;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Got handle to DLL.\n");
    ::MessageBox(NULL, TEXT("Got DLL."), TEXT("Dbg"), 0x10010);
    #endif

    pIsInstalled = (P_IEI) GetProcAddress(hinstLib, "IsEcInstalled");
    if (pIsInstalled == NULL) {
        allLoaded = false;
    #ifdef PRINT_DEBUG_MESSAGES
        ::MessageBox(NULL, TEXT("Didn't get P_IEI."), TEXT("Dbg"), 0x10010);
    } else {
        ::MessageBox(NULL, TEXT("Got P_IEI."), TEXT("Dbg"), 0x10010);
        pIsInstalled();
        ::MessageBox(NULL, TEXT("returned again2."), TEXT("Dbg"), 0x10010);
    #endif
    }

    pSelectC = (P_ECSC) GetProcAddress(hinstLib,
                                       "EncConverterSelectConverterW");
    if (pSelectC == NULL) {
        allLoaded = false;
        ::MessageBox(NULL, TEXT("Didn't get P_ECSC."), TEXT("Dbg"), 0x10010);
    } else {
        ::MessageBox(NULL, TEXT("Got P_ECSC."), TEXT("Dbg"), 0x10010);
    }

    pInitC = (P_ECIC) GetProcAddress(hinstLib,
                                    "EncConverterInitializeConverterW");
    if (pInitC == NULL) {
        allLoaded = false;
    #ifdef PRINT_DEBUG_MESSAGES
        ::MessageBox(NULL, TEXT("Didn't get P_ECIC."), TEXT("Dbg"), 0x10010);
    } else {
        ::MessageBox(NULL, TEXT("Got P_ECIC."), TEXT("Dbg"), 0x10010);
    #endif
    }

    pConvertS = (P_ECCS) GetProcAddress(hinstLib,
                                        "EncConverterConvertStringW");
    if (pConvertS == NULL) {
        allLoaded = false;
    #ifdef PRINT_DEBUG_MESSAGES
        ::MessageBox(NULL, TEXT("Didn't get P_ECCS."), TEXT("Dbg"), 0x10010);
    } else {
        ::MessageBox(NULL, TEXT("Got P_ECCS."), TEXT("Dbg"), 0x10010);
    #endif
    }

    pIsInstalled();
    ::MessageBox(NULL, TEXT("returned again3."), TEXT("Dbg"), 0x10010);

    //FreeLibrary(hinstLib);  // crashes here

    pIsInstalled();
    ::MessageBox(NULL, TEXT("returned again4."), TEXT("Dbg"), 0x10010);

    #ifdef PRINT_DEBUG_MESSAGES
    //::MessageBox(NULL, TEXT("Load_DLLs finished."), TEXT("Dbg"), 0x10010);
    #endif

    return allLoaded;
}

//******************************************************************************
// XCallableSEC implementation
//******************************************************************************
sal_Bool SEC_Call_Impl::PickConverter( )
    throw (RuntimeException)
{
    if (!Load_DLL_Procs())
    {
        ::MessageBox(NULL,
            TEXT("Cannot find SIL Converters on this computer."),
            TEXT("Error"), 0x10010);
        return sal_False;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("DLLs loaded.\n");
    ::MessageBox(NULL, TEXT("DLLs loaded."), TEXT("Dbg"), 0x10010);
    #endif
    if (pIsInstalled != NULL)
    {
        ::MessageBox(NULL, TEXT("not null."), TEXT("Dbg"), 0x10010);
    }
    (pIsInstalled);
    ::MessageBox(NULL, TEXT("returned."), TEXT("Dbg"), 0x10010);
    pIsInstalled();
    ::MessageBox(NULL, TEXT("returned again2."), TEXT("Dbg"), 0x10010);
    (pIsInstalled)();
    ::MessageBox(NULL, TEXT("returned again3."), TEXT("Dbg"), 0x10010);
    pIsInstalled();
    ::MessageBox(NULL, TEXT("returned again4."), TEXT("Dbg"), 0x10010);
    if ((pIsInstalled)()) printf("true\n");
    ::MessageBox(NULL, TEXT("returned again4."), TEXT("Dbg"), 0x10010);
    BOOL result = (pIsInstalled)();
    ::MessageBox(NULL, TEXT("returned again with BOOL."), TEXT("Dbg"), 0x10010);
    if (!((pIsInstalled)()))
    //if (!(pIsInstalled()))
    {
        ::MessageBox(NULL,
            TEXT("SIL Converters is not installed properly."),
            TEXT("Error"), 0x10010);
        return sal_False;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("EC is installed.\n");
    ::MessageBox(NULL, TEXT("EC is installed."), TEXT("Dbg"), 0x10010);
    #endif

    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
    if ((pSelectC)(LPWSTR(this->szConverterName),
                   bDirectionForward, eNormFormOutput) == S_OK)
    {
        #ifdef PRINT_DEBUG_MESSAGES
        printf("Converter was successfully selected.\n");
        ::MessageBox(NULL, TEXT("Converter selected."), TEXT("Dbg"), 0x10010);
        #endif
        this->converterNameSet = true;
        return sal_True;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Converter was not selected.  User must have pressed cancel.\n");
    ::MessageBox(NULL, TEXT("Converter not selected."), TEXT("Dbg"), 0x10010);
    #endif
    return sal_False;
}

sal_Bool SEC_Call_Impl::SetConverter(OUString const & inStr)
    throw (RuntimeException)
{
    if (!Load_DLL_Procs())
    {
        ::MessageBox(NULL,
            TEXT("Cannot find SIL Converters on this computer."),
            TEXT("Error"), 0x10010);
        return sal_False;
    }
    if (!((pIsInstalled)()))
    {
        ::MessageBox(NULL,
            TEXT("SIL Converters is not installed properly."),
            TEXT("Error"), 0x10010);
        return sal_False;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("EC seems to be installed.\n");
    #endif

    if (!this->converterNameSet)
    {
        ::MessageBox(NULL,
            TEXT("The converter name has not been selected."),
            TEXT("Error"), 0x10010);
        return sal_False;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Converter name has been set.\n");
    #endif

	// initialize the converter based on these stored configuration
    // properties (but beware, it may no longer be installed!
    // So do something in the 'else' case to inform user)
    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
	if ((pInitC)(LPCWSTR(this->szConverterName),
                 bDirectionForward, eNormFormOutput) == S_OK)
	{
        #ifdef PRINT_DEBUG_MESSAGES
        printf("Converter was successfully selected.\n");
        #endif
        return sal_True;
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Converter was not initialized.\n");
    #endif
    ::MessageBox(NULL,
        TEXT("The converter could not be initialized. Please try again."),
        TEXT("Error"), 0x10010);
    this->converterNameSet = false;
    return sal_False;
}

OUString SEC_Call_Impl::GetName()
{
    if (this->converterNameSet)
        //return OUString(RTL_CONSTASCII_USTRINGPARAM(this->szConverterName));
        return OUString(this->szConverterName);
    else
        return OUString(L"");
}
OUString SEC_Call_Impl::Convert( OUString const & szInput )
    throw (RuntimeException)
{
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Convert BEGIN\n");
    #endif
    if(!this->converterNameSet)
    {
        ::MessageBox(NULL, TEXT("No converter was specified."),
            TEXT("Error"), 0x10010);
        return L"";
    }

    // Call Convert
    char szOutput[10000];
    if ((pConvertS)(
        LPCWSTR(szConverterName), LPCWSTR(szInput), LPWSTR(szOutput),
        10000) == S_OK)
        //OUStringToOString( szInput, RTL_TEXTENCODING_ASCII_US ),
    {
        #ifdef PRINT_DEBUG_MESSAGES
        printf("Convert was successful\n");
        #endif
        return OUString(RTL_CONSTASCII_USTRINGPARAM(szOutput));
    }
    #ifdef PRINT_DEBUG_MESSAGES
    printf("Convert failed\n");
    #endif
    return L"";
}

int main()
{
    try
    {
        printf("Starting Test_SEC_CallComponent. (press return)\n");
        getchar();

        // create a new instance of SEC_Call
        SEC_Call_Impl * secCall = new SEC_Call_Impl();
        printf("Created instance of SEC_CALL (press return)\n");
        getchar();

        // PickConverter()
        bool success = secCall->PickConverter();
        printf("XCallableSEC.PickConverter finished.\n");
        getchar();
        printf("XCallableSEC.PickConverter returned %s\n", success);
        getchar();

        // GetName()
        OUString convName = secCall->GetName();
        printf("XCallableSEC.GetName() returned %s\n",
            OUStringToOString( convName, RTL_TEXTENCODING_ASCII_US ).getStr());
        getchar();

        // Convert()
        OUString s = secCall->Convert(OUString(L"\u0BAA\u0B9F\u0BAE"));
        printf("XCallableSEC.Convert() = %s\n",
               OUStringToOString( s, RTL_TEXTENCODING_ASCII_US ).getStr());

        // create another new instance of SEC_Call
        SEC_Call_Impl * secCall2 = new SEC_Call_Impl();
        printf("Created another instance of SEC_CALL\n");
        getchar();

        // SetConverter()
        success = secCall2->SetConverter(convName);
        printf("XCallableSEC2.SetConverter returned %s\n",
               success);
        getchar();

        // GetName()
        convName = secCall2->GetName();
        printf("XCallableSEC2.GetName() returned %s\n",
            OUStringToOString( convName, RTL_TEXTENCODING_ASCII_US ).getStr());
        getchar();

        // Convert()
        s = secCall2->Convert(OUString(L"\u0BAE\u0B9F"));
        printf("XCallableSEC2.Convert() = %s\n",
               OUStringToOString( s, RTL_TEXTENCODING_ASCII_US ).getStr());

        printf("\n\nPlease press 'return' to finish the example!\n");
        getchar();
    }
    //catch ( ::cppu::BootstrapException & e )
    //{
    //    fprintf(stderr, "\ncaught BootstrapException: %s\n",
    //            OUStringToOString( e.getMessage(),
    //                RTL_TEXTENCODING_ASCII_US ).getStr());
    //    return 1;
    //}
    catch ( Exception & e )
    {
        fprintf(stderr, "\ncaught UNO exception: %s\n",
                OUStringToOString( e.Message,
                    RTL_TEXTENCODING_ASCII_US ).getStr());
        return 1;
    }
    return 0;
}
