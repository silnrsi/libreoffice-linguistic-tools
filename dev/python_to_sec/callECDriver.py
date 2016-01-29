
# Before running, do this:
# export LD_LIBRARY_PATH=.:~/p4repo/Calgary/FW_7.0/DistFiles/Linux

from __future__ import with_statement
from ctypes import *
from ctypes.util import find_library
from itertools import chain, count
import platform, warnings

def statusHandler(s,f,args):
    if s < 0:
        raise RuntimeError('error from ecdriver')
    s = c_int8(s).value
    if s == 0:
        return args
    raise RuntimeError('unknown status code %s returned' % s)

# In OOoLT these can be members of the ECDriverWrapper class.
methIsEcInstalled   = None;
methSelectConverter = None;
methConvertString   = None;
methDescription     = None;

def LoadLibrary():
    if platform.system() == "Windows" :
        libecdriver = windll.LoadLibrary(
                      find_library('ECDriver_' + platform.machine()))
        LOCALFUNCTYPE = WINFUNCTYPE
    else :
        #loc = find_library('ecdriver')
        #if loc:
        #    print "Found ecdriver library."
        #else:
        #    print "Could not find ecdriver library."
        #    return -1
        try:
            #libecdriver = cdll.LoadLibrary(loc)
            libecdriver = cdll.LoadLibrary("libecdriver.so.1")
        except OSError, exc:
            print exc.message
            return -1
        LOCALFUNCTYPE = CFUNCTYPE

    # Define some 'typedefs' these make the argtypes list slight less opaque.
    status_t = c_int
    paramIn  = 1

    prototype  = LOCALFUNCTYPE(c_bool)
    paramflags = ()
    global methIsEcInstalled
    methIsEcInstalled = prototype(('IsEcInstalled', libecdriver), paramflags)

    prototype  = LOCALFUNCTYPE(status_t,
                 POINTER(c_char), POINTER(c_bool), POINTER(c_uint16))
    paramflags = (paramIn,'sConverterName'),(paramIn,'bDirectionForward'), \
                 (paramIn,'eNormFormOutput')
    global methSelectConverter
    methSelectConverter = prototype(
        ('EncConverterSelectConverter', libecdriver), paramflags)
    methSelectConverter.errcheck = statusHandler

    prototype  = LOCALFUNCTYPE(status_t,
                 c_char_p, c_char_p, POINTER(c_char), c_int)
    paramflags = (paramIn,'sConverterName'),(paramIn,'sInput'), \
                 (paramIn,'sOutput'),(paramIn,'nOutputLen')
    global methConvertString
    methConvertString = prototype(
        ('EncConverterConvertString', libecdriver), paramflags)
    methConvertString.errcheck = statusHandler

    prototype  = LOCALFUNCTYPE(status_t,
                 c_char_p, POINTER(c_char), c_int)
    paramflags = (paramIn,'sConverterName'),(paramIn,'sDescription'), \
                 (paramIn,'nOutputLen')
    global methDescription
    methDescription = prototype(
        ('EncConverterConverterDescription', libecdriver), paramflags)
    methDescription.errcheck = statusHandler

    prototype  = LOCALFUNCTYPE(None)
    paramflags = ()
    global methCleanup
    methCleanup = prototype(('CleanupMono', libecdriver), paramflags)

    return 0

################################################################################
# Main routine
################################################################################

err = LoadLibrary()
if err:
    exit(-1)

bResult = methIsEcInstalled()
if bResult:
    print "yes, EC is installed"
else:
    print "no, EC is not installed"
    exit(1)

bufConverterName = create_string_buffer(256)
directionFw = c_bool(False)
normForm = c_ushort(0)
try:
    status = methSelectConverter (
             bufConverterName, byref(directionFw), byref(normForm));
    print "status ", status
except RuntimeError, exc:
    print exc.message
    exit(-1)

print "Converter is ", bufConverterName.value
print "direction ", directionFw.value
print "normForm ", normForm.value

sInput = "abCde";
bufOutput = create_string_buffer(1000)
methConvertString (
    bufConverterName, sInput, bufOutput, 1000);
print "Result is ", bufOutput.value

bufDescription = create_string_buffer(1000)
methDescription(bufConverterName, bufDescription, 1000);
print "Description is ", bufDescription.value;

methCleanup()

