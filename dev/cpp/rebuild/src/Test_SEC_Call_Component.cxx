/*************************************************************************
 *
 * History:
 *  Created by Jim Kornelsen on 2/24/2010.
 *
 *************************************************************************/

#define _UNICODE
#define UNICODE

#include <ole2.h>       // For MessageBox
#include <stdio.h>
#include <sal/main.h>
#include <cppuhelper/bootstrap.hxx>
#include <com/sun/star/bridge/XUnoUrlResolver.hpp>
#include <com/sun/star/frame/XComponentLoader.hpp>
#include <lingtools_module/SEC_Call.hpp>

using namespace rtl;
using namespace com::sun::star::uno;
using namespace com::sun::star::lang;
using namespace com::sun::star::frame;

SAL_IMPLEMENT_MAIN()
{
    try
    {
        printf("Starting the Test_SEC_CallComponent. (press return) >\n");
        getchar();

        // get the remote office component context
        Reference< XComponentContext > xContext( ::cppu::bootstrap() ); 
        printf("connected to a running office>\n");
        //getchar();

        // create a new instance of SEC_Call
        Reference<lingtools_module::XCallableSEC> xCallableSEC =
            lingtools_module::SEC_Call::create(xContext);
        printf("Created instance of SEC_CALL>\n");
        //getchar();

        // PickConverter()
        bool success = xCallableSEC->PickConverter();
        printf("XCallableSEC.PickConverter finished.>\n");
        getchar();
        printf("XCallableSEC.PickConverter returned %s>\n",
               success ? "true" : "false");
        getchar();

        // GetName()
        OUString convName = xCallableSEC->GetName();
        wprintf(L"XCallableSEC.GetName() returned %s\n", convName.getStr());

        //Get direction and normalize
        bool convDirFw = xCallableSEC->GetDirectionFw();
        int  convNorm  = xCallableSEC->GetNormalize();
        wprintf(L"Dir %s, Norm %d>\n",
                convDirFw ? L"true" : L"false", convNorm);
        //getchar();

        // Convert()
        OUString s = xCallableSEC->Convert(OUString(L"\u0BAA\u0B9F\u0BAE"));
        wprintf(L"XCallableSEC.Convert() = %s\n", s.getStr());
        ::MessageBox(NULL, s.getStr(), TEXT("Dbg"), 0x10010);

/*
        // create another new instance of SEC_Call
        Reference<lingtools_module::XCallableSEC> xCallableSEC2 =
            lingtools_module::SEC_Call::create(xContext);
        printf("Created another instance of SEC_CALL\n");
        getchar();

        // SetConverter()
        success = xCallableSEC2->SetConverter(
            convName, convDirFw, convNorm);
        printf("XCallableSEC2.SetConverter returned %s\n",
               success ? "true" : "false");
        getchar();

        // GetName()
        convName = xCallableSEC2->GetName();
        wprintf(L"XCallableSEC2.GetName() returned %s\n", convName.getStr());

        //Get direction and normalize
        convDirFw = xCallableSEC2->GetDirectionFw();
        convNorm  = xCallableSEC2->GetNormalize();
        wprintf(L"Dir %s, Norm %d\n", convDirFw ? L"true" : L"false", convNorm);
        getchar();

        // Convert()
        s = xCallableSEC2->Convert(OUString(L"\u0BAE\u0B9F"));
        wprintf(L"XCallableSEC2.Convert() = %s\n", s.getStr());
        ::MessageBox(NULL, s.getStr(), TEXT("Dbg"), 0x10010);
*/

        printf("\n\nPlease press 'return' to finish the example!\n");
        getchar();
    }
    catch ( ::cppu::BootstrapException & e )
    {
        fprintf(stderr, "\ncaught BootstrapException: %s\n",
                OUStringToOString( e.getMessage(),
                    RTL_TEXTENCODING_ASCII_US ).getStr());
        return 1;
    }
    catch ( Exception & e )
    {
        fprintf(stderr, "\ncaught UNO exception: %s\n",
                OUStringToOString( e.Message,
                    RTL_TEXTENCODING_ASCII_US ).getStr());
        return 1;
    }
    return 0;
}
