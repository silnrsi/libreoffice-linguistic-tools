#include <ansi_c.h>
//Include windows.h to call the DLL dynamically. windows.h contains LoadLibrary and GetProcAddress .
#include <windows.h>

//Typedef the pointer to the exported function so you can call it easily later
//The function returns an int and has two inputs, an int and a string
typedef int (*MYPROC)(int, char*);

int main ()
{

int number = 5;
char* string = "Hello";
int returnValue;

HINSTANCE hinstLib; //Handle to the DLL
MYPROC ProcAddress; //Pointer to the function

hinstLib = LoadLibrary("SimpleDLL.dll");
//The the pointer to the exported function and typecast it so that we can easily call it
//MYPROC is typedef'ed above
//GetProcAddress is part of the Windows SDK and is declared in windows.h
ProcAddress = (MYPROC) GetProcAddress(hinstLib, "ShowMyNumberAndString");

//Call the function using the function pointer
returnValue = (ProcAddress)(number, string);

return 0;

}



// A simple program that uses LoadLibrary and 
// GetProcAddress to access myPuts from Myputs.dll. 
 
#include <windows.h> 
#include <stdio.h> 
 
typedef int (__cdecl *MYPROC)(LPWSTR); 
 
VOID main(VOID) 
{ 
    HINSTANCE hinstLib; 
    MYPROC ProcAdd; 
    BOOL fFreeResult, fRunTimeLinkSuccess = FALSE; 
 
    // Get a handle to the DLL module.
 
    hinstLib = LoadLibrary(TEXT("MyPuts.dll")); 
 
    // If the handle is valid, try to get the function address.
 
    if (hinstLib != NULL) 
    { 
        ProcAdd = (MYPROC) GetProcAddress(hinstLib, "myPuts"); 
 
        // If the function address is valid, call the function.
 
        if (NULL != ProcAdd) 
        {
            fRunTimeLinkSuccess = TRUE;
            (ProcAdd) (L"Message sent to the DLL function\n"); 
        }
        // Free the DLL module.
 
        fFreeResult = FreeLibrary(hinstLib); 
    } 

    // If unable to call the DLL function, use an alternative.
    if (! fRunTimeLinkSuccess) 
        printf("Message printed from executable\n"); 
}




typedef void (WINAPI *PGNSI)(LPSYSTEM_INFO);
typedef BOOL (WINAPI *PGPI)(DWORD, DWORD, DWORD, DWORD, PDWORD);


// Call GetNativeSystemInfo if supported or GetSystemInfo otherwise.

   PGNSI pGNSI;
   SYSTEM_INFO si;

   ZeroMemory(&si, sizeof(SYSTEM_INFO));
   
   pGNSI = (PGNSI) GetProcAddress(
      GetModuleHandle(TEXT("kernel32.dll")), 
      "GetNativeSystemInfo");
   if(NULL != pGNSI)
      pGNSI(&si);
   else GetSystemInfo(&si);


      pGPI = (PGPI) GetProcAddress(
            GetModuleHandle(TEXT("kernel32.dll")), 
            "GetProductInfo");

         pGPI( osvi.dwMajorVersion, osvi.dwMinorVersion, 0, 0, &dwType);

    switch( dwType )
         {
            case PRODUCT_ULTIMATE:
            ...

