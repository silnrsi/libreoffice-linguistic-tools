// cl /o dll_test.dll test_buf.c /link /DLL
/*
from ctypes import *
test_dll = windll.dll_test
test_buf = test_dll.test_buf

data_in = c_char_p('\x04\x21\x41\x1F')
data_out = create_string_buffer(4)
numbytes = c_long(4)
ret = test_buf(data_in, numbytes, data_out)

import binascii
print "Returned", ret
print "Out =", binascii.hexlify(data_out.raw).upper()
*/
#include "test_buf.h"
int __stdcall test_buf(char* buf,
                       int num,
                       char* outbuf)
{
    int i = 0;

    for (i = 0; i < num; ++i)
    {
        outbuf[i] = buf[i] * 3;
    }

    return num;
}
