/*************************************************************************
 *
 *
 *
 *
 *
Hacked 7-Nov-2011 by Jim for testing.
 *
 *
 *
 *
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
//#include <ole2.h>

// First I tried <iostream> but had linking problems with the OOo SDK.
#include <stdio.h>
#include <string.h>

// To load functions from ECDriver.dll dynamically
#include <windows.h>

// These libraries are all needed for OOo components
//#include <osl/interlck.h>
//#include <osl/mutex.hxx>
//#include <rtl/uuid.h>
//#include <cppuhelper/implbase3.hxx> // "3" implementing three interfaces
//#include <cppuhelper/factory.hxx>
//#include <cppuhelper/implementationentry.hxx>
//#include <com/sun/star/lang/XServiceInfo.hpp>
//#include <com/sun/star/lang/XTypeProvider.hpp>
//#include <lingtools_module/XCallableSEC.hpp>

//using namespace ::rtl; // for OUString
//using namespace ::com::sun::star; // for odk interfaces
//using namespace ::com::sun::star::uno; // for basic types

// Types for pointers to DLL procedures
typedef BOOL (_stdcall *P_IEI)(void);
    // IsEcInstalled
typedef HRESULT (_stdcall *P_ECSC)(LPWSTR, BOOL&, int&);
    // EncConverterSelectConverterW
typedef HRESULT (_stdcall *P_ECIC)(LPCWSTR, BOOL, int);
    // EncConverterInitializeConverterW
typedef HRESULT (_stdcall *P_ECCS)(LPCWSTR, LPCWSTR, LPWSTR, int);
    // EncConverterConvertStringW

//namespace lingtools_sc_impl
//{
//class SEC_Call_Impl : public ::lingtools_module::XCallableSEC,
//                      public lang::XServiceInfo,
//                      public lang::XTypeProvider
class SEC_Call_Impl
{
private:
    wchar_t szConverterName[1000];
    bool converterNameSet;
    BOOL directionForward;
    int  normFormOutput;

    HINSTANCE hinstLib;
    bool      allLoaded;
    
    P_IEI  pIsInstalled;
    P_ECSC pSelectC;
    P_ECIC pInitC;
    P_ECCS pConvertS;

    //oslInterlockedCount m_refcount;
    //OUString m_sData;
    // it's good practise to store the context for further use when you use
    // other UNO API's in your implementation
    //Reference< XComponentContext > m_xContext;
public:
    //inline SEC_Call_Impl(
    //    Reference< XComponentContext > const & xContext)
    //    throw ()
    //    : m_refcount( 0 ),
    //      m_xContext(xContext)
    SEC_Call_Impl()
    {
        this->converterNameSet = false;
        this->directionForward = TRUE;
        this->normFormOutput = 0;

        this->hinstLib = NULL;
        this->allLoaded = false;
    }

    inline ~SEC_Call_Impl() throw ()
    {
        if (this->hinstLib != NULL)
        {
            FreeLibrary(this->hinstLib);
        }
    }
    
    bool Load_DLL_Procs();

/*
    // XCallableSEC
    virtual sal_Bool SAL_CALL PickConverter( )
        throw (RuntimeException);
    virtual sal_Bool SAL_CALL SetConverter( OUString const & str,
                                            sal_Bool dirFw, sal_Int32 norm )
        throw (RuntimeException);
    virtual OUString SAL_CALL Convert( OUString const & str )
        throw (RuntimeException);
    virtual OUString SAL_CALL GetName( )
        throw (RuntimeException);
    virtual sal_Bool SAL_CALL GetDirectionFw( )
        throw (RuntimeException);
    virtual sal_Int32 SAL_CALL GetNormalize( )
        throw (RuntimeException);

    // XInterface
    virtual Any SAL_CALL queryInterface( Type const & type )
        throw (RuntimeException);
    virtual void SAL_CALL acquire()
        throw ();
    virtual void SAL_CALL release()
        throw ();
    // XTypeProvider
    virtual Sequence< Type > SAL_CALL getTypes()
        throw (RuntimeException);
    virtual Sequence< sal_Int8 > SAL_CALL getImplementationId()
        throw (RuntimeException);
    // XServiceInfo
    virtual OUString SAL_CALL getImplementationName()
        throw (RuntimeException);
    virtual sal_Bool SAL_CALL supportsService( OUString const & serviceName )
        throw (RuntimeException);
    virtual Sequence< OUString > SAL_CALL getSupportedServiceNames()
        throw (RuntimeException);
*/
};

bool SEC_Call_Impl::Load_DLL_Procs()
{
    if (DEBUG) {
        printf("Load_DLL_Procs BEGIN\n");
    }
    if (this->allLoaded)
    {
        // Nothing needs to be done.
        return true;
    }
    this->allLoaded = true;

    // Get a handle to the DLL module.
    // Full path is C:\\Program Files\\Common Files\\SIL\\ECDriver.dll
    HINSTANCE hinstLib = LoadLibrary(TEXT("ECDriver.dll"));
    if (hinstLib == NULL)
    {
        this->allLoaded = false;
        return false;
    }
    if (DEBUG) {
        printf("Got handle to DLL.\n");
    }

    pIsInstalled = (P_IEI) GetProcAddress(hinstLib, "IsEcInstalled");
    if (pIsInstalled == NULL) {
        this->allLoaded = false;
        if (DEBUG) printf("Didn't get P_IEI.\n");
    } else {
        if (DEBUG) printf("Got P_IEI.\n");
    }

    pSelectC = (P_ECSC) GetProcAddress(hinstLib,
                                       "EncConverterSelectConverterW");
    if (pSelectC == NULL) {
        this->allLoaded = false;
        if (DEBUG) printf("Didn't get P_ECSC.\n");
    } else {
        if (DEBUG) printf("Got P_ECSC.\n");
    }

    pInitC = (P_ECIC) GetProcAddress(hinstLib,
                                    "EncConverterInitializeConverterW");
    if (pInitC == NULL) {
        this->allLoaded = false;
        if (DEBUG) printf("Didn't get P_ECIC.\n");
    } else {
        if (DEBUG) printf("Got P_ECIC.\n");
    }

    pConvertS = (P_ECCS) GetProcAddress(hinstLib,
                                        "EncConverterConvertStringW");
    if (pConvertS == NULL) {
        this->allLoaded = false;
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

    return this->allLoaded;
}

int main() {
    printf("main() BEGIN\n");
    SEC_Call_Impl * secCall = new SEC_Call_Impl();
    bool success = secCall->Load_DLL_Procs();
    printf("Returned %ssuccessful\n", success ? "" : "not ");
    return 0;
}
