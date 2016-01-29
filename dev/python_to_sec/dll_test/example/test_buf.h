
#define DLL_EXPORT __declspec(dllexport)

DLL_EXPORT int __stdcall test_buf(char* buf,
                                  int num,
                                  char* outbuf);

