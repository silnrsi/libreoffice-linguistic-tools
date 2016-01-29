#!/usr/bin/python
# -*- coding: Latin-1 -*-

# SEC_wrapper.py
#
# Change History:
#   Created Nov 1 2011 by Jim Kornelsen

"""
Calls the ECDriver DLL using the ctypes library.
On Linux the library is libecdriver.so
"""

import logging
from ctypes import *
from ctypes.util import find_library
import platform, warnings

#from   lingt.UI   import MessageBox

def statusHandler(s,f,args):
    return args
    #if s < 0:
    #    raise RuntimeError('error from ecdriver')
    #s = c_int8(s).value
    #if s == 0:
    #    return args
    #raise RuntimeError('unknown status code %s returned' % s)

class SEC_wrapper:
    def __init__(self, unoObjs, msgbox=None):
        self.methIsEcInstalled   = None
        self.methSelectConverter = None
        self.methInitConverter   = None
        self.methConvertString   = None
        self.methDescription     = None
        self.methCleanup         = None

        self.logger = logging.getLogger("lingt.File.SEC_wrapper")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        self.logger.addHandler(ch)
        if unoObjs:
            self.msgbox = MessageBox.MessageBox(unoObjs, self.logger)
        else:
            self.msgbox = msgbox

        self.loaded        = False
        self.converterName = None
        self.directionFw   = None
        self.normForm      = None

    def __del__(self):
        if self.methCleanup:
            self.methCleanup()

    def loadLibrary(self):
        if self.loaded:
            return
        wide = ''
        if platform.system() == "Windows" :
            wide = 'W'  # use ECDriver.dll functions with wide characters
            self.logger.debug("Loading DLL")
            #loc = find_library('ECDriver')
            try:
                libecdriver = windll.LoadLibrary("ECDriver")
            except OSError, exc:
                self.msgbox.display ("Library error: %s." % (exc.message))
                return
            self.logger.debug("DLL loaded")
            #LOCALFUNCTYPE = WINFUNCTYPE
            LOCALFUNCTYPE = CFUNCTYPE
        else :
            #loc = find_library('ecdriver')
            try:
                self.logger.debug("Loading .so")
                libecdriver = cdll.LoadLibrary("libecdriver.so.1")
                self.logger.debug(".so loaded")
            except OSError, exc:
                self.msgbox.display ("Library error: %s." % (exc.message))
                return
            LOCALFUNCTYPE = CFUNCTYPE

        # Define some 'typedefs' to make the argtypes list slightly less opaque.
        status_t = c_long
        c_BOOL   = c_ubyte
        paramIn  = 1

        try:
            self.logger.debug("Getting IsEcInstalled")
            prototype  = LOCALFUNCTYPE(c_bool)
            paramflags = ()
            self.methIsEcInstalled = prototype (
                ('IsEcInstalled', libecdriver), paramflags)

            self.logger.debug("Getting EncConverterSelectConverter")
            prototype  = LOCALFUNCTYPE(status_t,
                         POINTER(c_char), POINTER(c_BOOL), POINTER(c_uint16))
                         #POINTER(c_char), POINTER(c_bool), POINTER(c_int))
            paramflags = (paramIn,'sConverterName'),    \
                         (paramIn,'bDirectionForward'), \
                         (paramIn,'eNormFormOutput')
            self.methSelectConverter = prototype (
                ('EncConverterSelectConverter' + wide, libecdriver), paramflags)
            self.methSelectConverter.errcheck = statusHandler

            self.logger.debug("Getting EncConverterInitializeConverter")
            prototype  = LOCALFUNCTYPE(status_t,
                         c_char_p, c_bool, c_int)
            paramflags = (paramIn,'sConverterName'),    \
                         (paramIn,'bDirectionForward'), \
                         (paramIn,'eNormFormOutput')
            self.methInitConverter = prototype (
                ('EncConverterInitializeConverter' + wide, libecdriver),
                paramflags)
            self.methInitConverter.errcheck = statusHandler

            self.logger.debug("Getting EncConverterConvertString")
            prototype  = LOCALFUNCTYPE(status_t,
                         c_char_p, c_char_p, POINTER(c_char), c_int)
            paramflags = (paramIn,'sConverterName'), \
                         (paramIn,'sInput'),         \
                         (paramIn,'sOutput'),        \
                         (paramIn,'nOutputLen')
            self.methConvertString = prototype (
                ('EncConverterConvertString' + wide, libecdriver), paramflags)
            self.methConvertString.errcheck = statusHandler

            self.logger.debug("Getting EncConverterConverterDescription")
            prototype  = LOCALFUNCTYPE(status_t,
                         c_char_p, POINTER(c_char), c_int)
            paramflags = (paramIn,'sConverterName'), \
                         (paramIn,'sDescription'),   \
                         (paramIn,'nOutputLen')
            self.methDescription = prototype (
                ('EncConverterConverterDescription' + wide, libecdriver),
                paramflags)
            self.methDescription.errcheck = statusHandler

            self.logger.debug("Getting CleanupMono")
            prototype  = LOCALFUNCTYPE(None)
            paramflags = ()
            #self.methCleanup = prototype (
            #                   ('CleanupMono', libecdriver), paramflags)
        except AttributeError, exc:
            self.msgbox.display ("Library error: %s." % (exc))
            return

        self.logger.debug("Library successfully loaded.")
        self.loaded = True

    def PickConverter(self):
        self.logger.debug("PickConverter BEGIN")
        self.loadLibrary()
        if not self.loaded: return
        if not self.methIsEcInstalled():
            self.msgbox.display (
                "EncConverters does not seem to be installed properly.")
            return False

        bufConverterName = create_string_buffer(512)
        #c_directionFw    = c_bool(False)
        c_directionFw    = c_ubyte(False)
        c_normForm       = c_ushort(0)
        #c_normForm       = c_long(0)
        try:
            status = 0
            print "status size = ", status.__sizeof__()
            print "bufConverter size = ", bufConverterName.__sizeof__()
            print "directionFw size = ", c_directionFw.__sizeof__()
            print "normForm size = ", c_normForm.__sizeof__()
            status = self.methSelectConverter (
                     bufConverterName, byref(c_directionFw), byref(c_normForm))
                     #bufConverterName, c_directionFw, c_normForm)
            print "status = ", status
            #if (status != 0): return False
        except (RuntimeError, ValueError, ArgumentError), exc:
            self.msgbox.display (
                "Error calling EncConverters: %s." % (exc))
            return False

        self.converterName = bufConverterName.value
        self.directionFw = c_directionFw.value
        self.normForm    = c_normForm.value
        self.logger.debug("PickConverter END")
        return True

    def SetConverter(self, convName, directionFw, normForm):
        self.logger.debug("SetConverter BEGIN")
        self.loadLibrary()
        if not self.loaded: return
        if not self.methIsEcInstalled():
            self.msgbox.display (
                "EncConverters does not seem to be installed properly.")
            return False

        try:
            status = self.methInitConverter (
                     convName, directionFw, normForm)
            if (status != 0): return False
        except RuntimeError, exc:
            self.msgbox.display (
                "EncConverters error: %s." % (exc.message))
            return False

        self.converterName = convName
        self.directionFw = directionFw
        self.normForm    = normForm
        self.logger.debug("SetConverter END")
        return True

    def Convert(self, sInput):
        self.logger.debug("convert BEGIN")
        if not self.converterName:
            self.msgbox.display ("No converter was specified.")
            return ""
        bufOutput = create_string_buffer(1000)
        status = self.methConvertString (
                 self.converterName, sInput, bufOutput, 1000);
        if status != 0:
            return ""
        self.logger.debug("convert END")
        return bufOutput.value

