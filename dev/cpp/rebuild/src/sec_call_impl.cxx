/*************************************************************************
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
#include <osl/interlck.h>
#include <osl/mutex.hxx>
#include <rtl/uuid.h>
#include <cppuhelper/implbase3.hxx> // "3" implementing three interfaces
#include <cppuhelper/factory.hxx>
#include <cppuhelper/implementationentry.hxx>
#include <com/sun/star/lang/XServiceInfo.hpp>
#include <com/sun/star/lang/XTypeProvider.hpp>
#include <lingtools_module/XCallableSEC.hpp>

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

namespace lingtools_sc_impl
{
class SEC_Call_Impl : public ::lingtools_module::XCallableSEC,
                      public lang::XServiceInfo,
                      public lang::XTypeProvider
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

    oslInterlockedCount m_refcount;
    OUString m_sData;
    // it's good practise to store the context for further use when you use
    // other UNO API's in your implementation
    Reference< XComponentContext > m_xContext;
public:
    inline SEC_Call_Impl(
        Reference< XComponentContext > const & xContext)
        throw ()
        : m_refcount( 0 ),
          m_xContext(xContext)
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
};

bool SEC_Call_Impl::Load_DLL_Procs()
{
    FILE * logfile = fopen("D:\\Jim\\computing\\Office\\OOo Linguistic Tools\\dev\\cpp\\rebuild\\src\\debug.txt", "w");
    if (DEBUG) {
        fprintf(logfile, "Load_DLL_Procs BEGIN\n");
        char * pPath;
        pPath = getenv ("PATH");
        if (pPath!=NULL)
            fprintf (logfile, "The current path is: %s\n",pPath);
        else
            fprintf (logfile, "Couldn't get path.\n");

        HKEY hKey; // Declare a key to store the result
        DWORD buffersize = 1024; // Declare the size of the data buffer
        char* lpData = new char[buffersize];// Declare the buffer
 
        /* Open the Registry Key at the location
        HKEY_CURRENT_USER\Software\Microsoft\Internet Explorer\Main
        with read only access
        */
 
        RegOpenKeyEx (HKEY_CURRENT_USER,
        L"Software\\Microsoft\\Internet Explorer\\Main",NULL,KEY_READ,&hKey);
 
        // Query the registry value
        RegQueryValueEx(hKey,L"Start Page",NULL,NULL,(LPBYTE) lpData,&buffersize);
 
        // Print out the registry value
        fprintf(logfile, "Registry Key Open: memory location=%s\n", hKey);
        fprintf(logfile, "Your Internet Start Page is %s\n", lpData);
 
        // Close the Registry Key
        RegCloseKey (hKey);
 
// Pause the system so there is time to read what is going on
system("Pause");
 
delete lpData;
    }
    if (this->allLoaded)
    {
        // Nothing needs to be done.
        fclose(logfile);
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
        fprintf(logfile, "Got handle to DLL.\n");
    }

    pIsInstalled = (P_IEI) GetProcAddress(hinstLib, "IsEcInstalled");
    if (pIsInstalled == NULL) {
        this->allLoaded = false;
        if (DEBUG) fprintf(logfile, "Didn't get P_IEI.\n");
    } else {
        if (DEBUG) fprintf(logfile, "Got P_IEI.\n");
    }

    pSelectC = (P_ECSC) GetProcAddress(hinstLib,
                                       "EncConverterSelectConverterW");
    if (pSelectC == NULL) {
        this->allLoaded = false;
        if (DEBUG) fprintf(logfile, "Didn't get P_ECSC.\n");
    } else {
        if (DEBUG) fprintf(logfile, "Got P_ECSC.\n");
    }

    pInitC = (P_ECIC) GetProcAddress(hinstLib,
                                    "EncConverterInitializeConverterW");
    if (pInitC == NULL) {
        this->allLoaded = false;
        if (DEBUG) fprintf(logfile, "Didn't get P_ECIC.\n");
    } else {
        if (DEBUG) fprintf(logfile, "Got P_ECIC.\n");
    }

    pConvertS = (P_ECCS) GetProcAddress(hinstLib,
                                        "EncConverterConvertStringW");
    if (pConvertS == NULL) {
        this->allLoaded = false;
        if (DEBUG) fprintf(logfile, "Didn't get P_ECCS.\n");
    } else {
        if (DEBUG) fprintf(logfile, "Got P_ECCS.\n");
    }

    if (DEBUG) fprintf(logfile, "Load_DLLs finished.\n");
    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
    fprintf(logfile, "Calling SelectConverter.\n");
    if (pSelectC(szConverterName, bDirectionForward,
                 eNormFormOutput) == S_OK)
    {
        if (DEBUG) {
            fprintf(logfile, "Converter was successfully selected.\n");
            fprintf(logfile, "%s\n", szConverterName);
        }
        directionForward = bDirectionForward;
        normFormOutput   = eNormFormOutput;
        converterNameSet = true;
        fclose(logfile);
        return true;
    }
    if (DEBUG) {
        fprintf(logfile, "Converter was not selected.  User must have pressed cancel.\n");
    }

    fclose(logfile);
    return this->allLoaded;
}

//******************************************************************************
// XCallableSEC implementation
//******************************************************************************

// Returns true if a converter has been gotten
sal_Bool SEC_Call_Impl::PickConverter( )
    throw (RuntimeException)
{
    if (!Load_DLL_Procs())
    {
        printf("Cannot find SIL Converters on this computer.\n");
        return sal_False;
    }
    if (DEBUG) {
        printf("DLLs loaded.\n");
        #ifdef UNICODE
        printf("Unicode defined.\n");
        #else
        printf("Unicode not defined.\n"),
        #endif
    }
    if (!pIsInstalled())
    {
        printf("SIL Converters is not installed properly.\n");
        return sal_False;
    }
    if (DEBUG) {
        printf("EC is installed.\n");
    }

/*
    // Setting the bDirectionForward (BOOL) to TRUE is not strictly necessary,
    // since that value is ignored by the function and whatever the user has
    // chosen will be returned in that variable.
    BOOL bDirectionForward = TRUE;
    int eNormFormOutput = 0;
    if (pSelectC(this->szConverterName, bDirectionForward,
                 eNormFormOutput) == S_OK)
    {
        if (DEBUG) {
            printf("Converter was successfully selected.\n");
            printf("%s\n", this->szConverterName);
        }
        this->directionForward = bDirectionForward;
        this->normFormOutput   = eNormFormOutput;
        this->converterNameSet = true;
        return sal_True;
    }
    if (DEBUG) {
        printf("Converter was not selected.  User must have pressed cancel.\n");
    }
    return sal_False;
*/
    return sal_True;
}

// Returns true if a converter has been successfuly set
sal_Bool SEC_Call_Impl::SetConverter(
    OUString const & inStr, sal_Bool directionFw, sal_Int32 normalize)
    throw (RuntimeException)
{
    if (!Load_DLL_Procs())
    {
        printf("Cannot find SIL Converters on this computer.");
        return sal_False;
    }
    if (!pIsInstalled())
    {
        printf("SIL Converters is not installed properly.\n");
        return sal_False;
    }
    if (DEBUG) printf("EC seems to be installed.\n");

    wcscpy(this->szConverterName, inStr.getStr());
    this->converterNameSet = true;
    if (DEBUG) printf("Converter name set.\n");

	// initialize the converter based on these stored configuration
    // properties (but beware, it may no longer be installed!
    // So do something in the 'else' case to inform user)
    BOOL bDirectionForward = directionFw;
    int eNormFormOutput    = normalize;
	if (pInitC(this->szConverterName,
               bDirectionForward, eNormFormOutput) == S_OK)
	{
        if (DEBUG) printf("Converter was successfully selected.\n");
        this->directionForward = bDirectionForward;
        this->normFormOutput   = eNormFormOutput;
        return sal_True;
    }
    if (DEBUG) printf("Converter was not initialized.\n");
    this->converterNameSet = false;
    return sal_False;
}

OUString SEC_Call_Impl::Convert( OUString const & szInput )
    throw (RuntimeException)
{
    if (DEBUG) printf("Convert BEGIN\n");
    if(!this->converterNameSet)
    {
        printf("No converter was specified.\n");
        return L"";
    }

    // Call Convert
    wchar_t szOutput[10000];
    if (pConvertS(this->szConverterName,
                  szInput.getStr(), szOutput, 10000) == S_OK)
    {
        if (DEBUG) printf("Convert was successful\n");
        return OUString(szOutput);
    }
    if (DEBUG) printf("Convert failed\n");
    return L"";
}

OUString SEC_Call_Impl::GetName()
{
    if (this->converterNameSet)
        return OUString(this->szConverterName);
    else
        return OUString(L"");
}

sal_Bool SEC_Call_Impl::GetDirectionFw()
{
    return this->directionForward;
}

sal_Int32 SEC_Call_Impl::GetNormalize()
{
    return this->normFormOutput;
}


//******************************************************************************
// XInterface implementation
// -This and other code below are needed for UNO components.
//******************************************************************************
Any SEC_Call_Impl::queryInterface( Type const & type )
    throw (RuntimeException)
{
    if (type.equals(::cppu::UnoType< Reference< XInterface > >::get()))
    {
        // return XInterface interface
        // (resolve ambiguity by casting to lang::XTypeProvider)
        Reference< XInterface > x(
            static_cast< lang::XTypeProvider * >( this ) );
        return makeAny( x );
    }
    if (type.equals(::cppu::UnoType< Reference< lang::XTypeProvider > >::get()))
    {
        // return XInterface interface
        Reference< XInterface > x(
            static_cast< lang::XTypeProvider * >( this ) );
        return makeAny( x );
    }
    if (type.equals(::cppu::UnoType< Reference< lang::XServiceInfo > >::get()))
    {
        // return XServiceInfo interface
        Reference< lang::XServiceInfo > x(
            static_cast< lang::XServiceInfo * >( this ) );
        return makeAny( x );
    }
    if (type.equals(::cppu::UnoType< Reference< ::lingtools_module::XCallableSEC > >::get()))
    {
        // return sample interface
        Reference< ::lingtools_module::XCallableSEC > x(
            static_cast< ::lingtools_module::XCallableSEC * >( this ) );
        return makeAny( x );
    }
    // querying for unsupported type
    return Any();
}

void SEC_Call_Impl::acquire()
    throw ()
{
    // thread-safe incrementation of reference count
    ::osl_incrementInterlockedCount( &m_refcount );
}

void SEC_Call_Impl::release()
    throw ()
{
    // thread-safe decrementation of reference count
    if (0 == ::osl_decrementInterlockedCount( &m_refcount ))
    {
        delete this; // shutdown this object
    }
}

// XTypeProvider implementation
Sequence< Type > SEC_Call_Impl::getTypes()
    throw (RuntimeException)
{
    Sequence< Type > seq( 3 );
    seq[ 0 ] = ::cppu::UnoType< Reference< lang::XTypeProvider > >::get();
    seq[ 1 ] = ::cppu::UnoType< Reference< lang::XServiceInfo > >::get();
    seq[ 2 ] = ::cppu::UnoType< Reference< ::lingtools_module::XCallableSEC > >::get();
    return seq;
}
Sequence< sal_Int8 > SEC_Call_Impl::getImplementationId()
    throw (RuntimeException)
{
    static Sequence< sal_Int8 > * s_pId = 0;
    if (! s_pId)
    {
        // create unique id
        Sequence< sal_Int8 > id( 16 );
        ::rtl_createUuid( (sal_uInt8 *)id.getArray(), 0, sal_True );
        // guard initialization with some mutex
        ::osl::MutexGuard guard( ::osl::Mutex::getGlobalMutex() );
        if (! s_pId)
        {
            static Sequence< sal_Int8 > s_id( id );
            s_pId = &s_id;
        }
    }
    return *s_pId;
}

// XServiceInfo implementation
OUString SEC_Call_Impl::getImplementationName()
    throw (RuntimeException)
{
    // unique implementation name
    return OUString(L"lingtools_module.lingtools_sc_implementation.SEC_Call");
}
sal_Bool SEC_Call_Impl::supportsService( OUString const & serviceName )
    throw (RuntimeException)
{
    // this object only supports one service, so the test is simple
    return serviceName.equalsAsciiL( RTL_CONSTASCII_STRINGPARAM(
                                         "lingtools_module.SEC_Call") );
}
Sequence< OUString > SEC_Call_Impl::getSupportedServiceNames()
    throw (RuntimeException)
{
    // this object only supports one service
    OUString serviceName(
        RTL_CONSTASCII_USTRINGPARAM("lingtools_module.SEC_Call") );
    return Sequence< OUString >( &serviceName, 1 );
}

Sequence< OUString > SAL_CALL getSupportedServiceNames_SEC_Call_Impl()
{
    Sequence< OUString > names(1);
    names[0] = OUString(
        RTL_CONSTASCII_USTRINGPARAM("lingtools_module.SEC_Call"));
    return names;
}

OUString SAL_CALL getImplementationName_SEC_Call_Impl()
{
    return OUString( RTL_CONSTASCII_USTRINGPARAM(
                    "lingtools_module.lingtools_sc_implementation.SEC_Call") );
}

Reference< XInterface > SAL_CALL create_SEC_Call_Impl(
    Reference< XComponentContext > const & xContext )
    SAL_THROW( () )
{
    return static_cast< lang::XTypeProvider * >( new SEC_Call_Impl( xContext) );
}

/* shared lib exports implemented without helpers in service_impl1.cxx */
static struct ::cppu::ImplementationEntry s_component_entries [] =
{
    {
        create_SEC_Call_Impl, getImplementationName_SEC_Call_Impl,
        getSupportedServiceNames_SEC_Call_Impl,
        ::cppu::createSingleComponentFactory,
        0, 0
    },
    { 0, 0, 0, 0, 0, 0 }
};


} // namespace


extern "C"
{
void SAL_CALL component_getImplementationEnvironment(
    sal_Char const ** ppEnvTypeName, uno_Environment ** )
{
    *ppEnvTypeName = CPPU_CURRENT_LANGUAGE_BINDING_NAME;
}

sal_Bool SAL_CALL component_writeInfo(
    lang::XMultiServiceFactory * xMgr, registry::XRegistryKey * xRegistry )
{
    return ::cppu::component_writeInfoHelper(
        xMgr, xRegistry, ::lingtools_sc_impl::s_component_entries );
}

void * SAL_CALL component_getFactory(
    sal_Char const * implName, lang::XMultiServiceFactory * xMgr,
    registry::XRegistryKey * xRegistry )
{
    return ::cppu::component_getFactoryHelper(
        implName, xMgr, xRegistry, ::lingtools_sc_impl::s_component_entries );
}

} // extern "C"

