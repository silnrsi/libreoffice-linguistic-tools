# -*- coding: Latin-1 -*-

"""
Access SIL Encoding Converters.
Calls the ECDriver DLL using the ctypes library.
On Linux the library is libecdriver.so

This module exports:
    ConverterSettings
    SEC_wrapper
    ProcessTypeFlags
    ConvType
"""
import ctypes
import logging
import os
import platform

from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions
from lingt.utils import util

logger = logging.getLogger("lingt.access.sec_wrapper")


class ConverterSettings(Syncable):
    def __init__(self, userVars):
        Syncable.__init__(self, userVars)
        self.convName = ""
        self.forward = True  # left to right
        self.normForm = 0  # for normalization

    def attrs(self):
        """Attributes that uniquely identify this object.
        Used for several magic methods below.
        """
        return self.convName, self.forward, self.normForm

    def __eq__(self, other):
        logger.debug("%r cmp %r", self, other)
        return (isinstance(other, ConverterSettings) and
                self.attrs() == other.attrs())

    def __hash__(self):
        """Make instances with identical attributes use the same hash."""
        return hash(self.attrs())

    def __repr__(self):
        return repr(self.attrs())

    def __str__(self):
        return "Converter '%s' (forward=%s, normalize=%d)" % (
            self.convName, self.forward, self.normForm)

    def storeUserVars(self):
        self.userVars.store('ConverterName', self.convName)
        self.userVars.store('ConvDirectionFw', str(int(self.forward)))
        self.userVars.store('ConvNormForm', str(self.normForm))

    def loadUserVars(self):
        self.convName = self.userVars.get('ConverterName')
        varname = 'ConvDirectionFw'
        if (not self.userVars.isEmpty(varname) and
                self.userVars.getInt(varname) == 0):
            self.forward = False
        self.normForm = self.userVars.getInt('ConvNormForm')


class SEC_wrapper:

    def __init__(self, msgbox, userVars):
        self.msgbox = msgbox

        self.funcIsEcInstalled = None
        self.funcSelectConverter = None
        self.funcInitConverter = None
        self.funcAddConverter = None
        self.funcConvertString = None
        self.funcDescription = None
        self.funcCleanup = None
        self.loaded = False
        self.config = ConverterSettings(userVars)

    def __del__(self):
        if self.loaded and self.funcCleanup is not None:
            self.funcCleanup()

    def loadLibrary(self):
        """Load ECDriver library."""
        if self.loaded:
            return
        if platform.system() == "Windows":
            libfile = "ECDriver"
            wide = 'W'  # use functions named with 'W' for wide characters
            logger.debug("Loading %s", libfile)
            try:
                try:
                    # Python 3.8 and newer
                    # It is recommended to use os.add_dll_directory("..."),
                    # but that would not search with environment variables. See
                    # docs.python.org/3/whatsnew/3.8.html#bpo-36085-whatsnew
                    libecdriver = ctypes.CDLL(libfile, winmode=0)
                except TypeError:
                    # Python 3.7 or older
                    libecdriver = ctypes.cdll.LoadLibrary(libfile)
            except OSError as exc:
                raise exceptions.FileAccessError("Library error: %s.", exc)
        else:
            wide = ''
            ## Look for libecdriver.so in order of location precedence.
            liblocs = [(prefix, dirname, libname)
                       for dirname in ("encConverters", "fieldworks")
                       for prefix in ("/usr/local", "/usr")
                       for libname in ("libecdriver.so", "libecdriver_64.so")]
            libfile = ""
            for prefix, dirname, libname in liblocs:
                filepath = os.path.join(prefix, "lib", dirname, libname)
                if os.path.exists(filepath):
                    libfile = filepath
                    break
            if not libfile:
                # Perhaps it is in current dir, LD_LIBRARY_PATH or ldconfig.
                libfile = "libecdriver.so"
            logger.debug("Loading %s", libfile)
            try:
                libecdriver = ctypes.cdll.LoadLibrary(libfile)
            except OSError as exc:
                raise exceptions.FileAccessError("Library error: %s.", exc)

        logger.debug("Getting functions from library")
        try:
            self.funcIsEcInstalled = libecdriver.IsEcInstalled
            self.funcSelectConverter = getattr(
                libecdriver, 'EncConverterSelectConverter' + wide)
            self.funcInitConverter = getattr(
                libecdriver, 'EncConverterInitializeConverter' + wide)
            self.funcConvertString = getattr(
                libecdriver, 'EncConverterConvertString' + wide)
            self.funcDescription = getattr(
                libecdriver, 'EncConverterConverterDescription' + wide)
            if platform.system() == "Linux":
                self.funcCleanup = libecdriver.Cleanup
        except AttributeError as exc:
            raise exceptions.FileAccessError("Library error: %s.", exc)
        logger.debug("Library successfully loaded.")
        try:
            self.funcAddConverter = getattr(
                libecdriver, 'EncConverterAddConverter' + wide)
        except AttributeError as exc:
            logger.warning("Could not load AddConverter function.")
        self.loaded = True

    def pickConverter(self):
        """Let the user pick a converter."""
        logger.debug(util.funcName('begin'))
        self.loadLibrary()
        if not self.loaded:
            return
        if not self.funcIsEcInstalled():
            raise exceptions.FileAccessError(
                "EncConverters does not seem to be installed properly.")
        bufConverterName = createBuffer(1024)
        c_forward = ctypes.c_bool(False)
        c_normForm = ctypes.c_ushort(0)
        logger.debug("Calling funcSelectConverter.")
        status = self.funcSelectConverter(
            bufConverterName,
            ctypes.byref(c_forward),
            ctypes.byref(c_normForm))
        if status == -1:
            logger.debug(
                "EncConverters returned %d.  User probably pressed Cancel.",
                status)
            return
        verifyStatusOk(status)

        logger.debug("Converter name was %r", bufConverterName.value)
        self.config = ConverterSettings(self.config.userVars)
        if platform.system() == "Windows":
            self.config.convName = bufConverterName.value
        else:
            self.config.convName = bufConverterName.value.decode("utf-8")
        self.config.forward = c_forward.value
        self.config.normForm = c_normForm.value
        logger.debug(util.funcName('end'))

    def setConverter(self, newConfig=None):
        """Initialize a converter to the specified values.
        :param newConfig: type ConverterSettings
        """
        logger.debug(util.funcName('begin'))
        if not newConfig:
            # Useful for multiple converter objects with different settings.
            newConfig = self.config
        self.loadLibrary()
        if not self.funcIsEcInstalled():
            raise exceptions.FileAccessError(
                "EncConverters does not seem to be installed properly.")
        c_convName = getStringParam(newConfig.convName)
        if c_convName is None:
            raise exceptions.LogicError("No converter was specified.")
        c_forward = ctypes.c_bool(newConfig.forward)
        c_normForm = ctypes.c_ushort(newConfig.normForm)
        logger.debug("calling funcInitConverter with %r", newConfig)
        status = self.funcInitConverter(c_convName, c_forward, c_normForm)
        verifyStatusOk(status)
        self.config = newConfig
        logger.debug(util.funcName('end'))

    def addConverter(self, mappingName, converterSpec, conversionType,
                     leftEncoding, rightEncoding, processType):
        """Add a converter to the repository.
        Used for automated testing.

        :param mappingName: friendly name key that the converter is to be
                            accessed with
        :param converterSpec: technical spec of the converter
                              (e.g. TECkit & CC = filespec to map)
        :param conversionType: ConvType parameter indicating the type of
                               conversion (e.g. "Legacy_to_from_Unicode")
        :param leftEncoding: optional technical name of the left-hand side
                             encoding (e.g. SIL-ANNAPURNA-05)
        :param rightEncoding: optional technical name of the right-hand side
                              encoding (e.g. UNICODE)
        :param processType: ProcessTypeFlags flag to indicate the
                            implementation/transduction
                            type (e.g. UnicodeEncodingConversion) from which
                            you can do later filtering (e.g. ByEncodingID)
        """
        logger.debug(
            util.funcName(
                'begin', args=(
                    mappingName, converterSpec, conversionType, leftEncoding,
                    rightEncoding, processType)))
        self.loadLibrary()
        if not self.funcIsEcInstalled():
            raise exceptions.FileAccessError(
                "EncConverters does not seem to be installed properly.")
        if not self.funcAddConverter:
            raise exceptions.FileAccessError(
                "Could not get AddConverter function.  "
                "Automatically adding a converter requires SEC4.0 or higher.")
        c_convName = getStringParam(mappingName)
        if not c_convName:
            raise exceptions.LogicError("No converter was specified.")
        c_convSpec = getStringParam(converterSpec)
        c_convType = ctypes.c_ushort(conversionType)
        c_leftEnc = getStringParam(leftEncoding)
        c_rightEnc = getStringParam(rightEncoding)
        c_processType = ctypes.c_ushort(processType)
        logger.debug("Calling funcAddConverter.")
        status = self.funcAddConverter(
            c_convName, c_convSpec, c_convType, c_leftEnc, c_rightEnc,
            c_processType)
        verifyStatusOk(status)
        logger.debug(util.funcName('end'))

    def convert(self, sInput):
        """:returns: converted unicode string"""
        logger.debug(util.funcName('begin'))
        if not self.config.convName:
            raise exceptions.LogicError("No converter was specified.")
        logger.debug("Using conv name %r", self.config.convName)
        c_convName = getStringParam(self.config.convName)
        logger.debug(repr(sInput))
        c_input = getStringParam(sInput)
        if c_input is None:
            raise exceptions.DataNotFoundError("No conversion result.")
        # ECDriver will truncate the result if we go over this amount.
        c_outSize = ctypes.c_int(10000)
        bufOutput = createBuffer(c_outSize.value)
        logger.debug("Calling ConvertString using %s.", self.config.convName)
        status = self.funcConvertString(
            c_convName, c_input, bufOutput, c_outSize)
        verifyStatusOk(status)
        sOutput = bufOutput.value
        if platform.system() != "Windows":
            sOutput = sOutput.decode("utf-8")
        logger.debug(repr(sOutput))
        logger.debug(util.funcName('end'))
        return sOutput


class ErrStatus:
    """Possible values for error codes.
    Values taken from ECInterfaces.cs.
    """
    # this is usually the desired result!
    NoError = 0

    # positive values are informational status values
    OutputBufferFull = 1
    NeedMoreInput = 2

    # negative values are errors
    InvalidForm = -1
    ConverterBusy = -2
    InvalidConverter = -3
    InvalidMapping = -4
    BadMappingVersion = -5
    ExceptionOccurred = -6  # name in ECInterfaces.cs is "Exception"
    NameNotFound = -7
    IncompleteChar = -8
    CompilationFailed = -9
    OutOfMemory = -10
    CantOpenReadMap = -11
    InEncFormNotSupported = -12
    OutEncFormNotSupported = -13
    NoAvailableConverters = -14
    SyntaxErrorInTable = -15
    NoErrorCode = -16
    NotEnoughBuffer = -17
    RegistryCorrupt = -18
    MissingConverter = -19
    NoConverter = -20
    InvalidConversionType = -21
    EncodingConvTypeNotSpecified = -22
    ConverterPluginUninstall = -23
    InvalidCharFound = -24
    TruncatedCharFound = -25
    IllegalCharFound = -26
    InvalidTableFormat = -27
    NoReturnData = -28
    NoReturnDataBadOutForm = -29
    AddFontFirst = -30
    InvalidNormalizeForm = -31
    NoAliasName = -32
    ConverterAlreadyExists = -33
    NoImplementDetails = -34
    NoEncodingName = -35
    NeedSpecTypeInfo = -36
    InvalidAliasName = -37
    FallbackTwoStepsRequired = -38
    FallbackSimilarConvType = -39
    InvalidMappingName = -40
    InstallFont = -41

    DESCRIPTIONS = {
        ExceptionOccurred: "Exception",
        InvalidConversionType: "Invalid Conversion Type",
        NameNotFound: "Converter Name Not Found",
        RegistryCorrupt: "Registry Corrupt",
    }

def verifyStatusOk(status):
    """Raises exception if not ok."""
    if status == ErrStatus.NoError:
        return
    description = ""
    if status in ErrStatus.DESCRIPTIONS:
        description = " (%s)" % ErrStatus.DESCRIPTIONS[status]
    raise exceptions.FileAccessError(
        "Error: EncConverters returned %d%s.", status, description)


class ProcessTypeFlags:
    """Possible values for SEC_wrapper.AddConverter() parameter.
    Values taken from ECInterfaces.cs.
    """
    DontKnow = 0x0000
    UnicodeEncodingConversion = 0x0001
    Transliteration = 0x0002
    ICUTransliteration = 0x0004
    ICUConverter = 0x0008
    CodePageConversion = 0x0010
    NonUnicodeEncodingConversion = 0x0020
    SpellingFixerProject = 0x0040
    ICURegularExpression = 0x0080
    PythonScript = 0x0100
    PerlExpression = 0x0200
    UserDefinedSpare1 = 0x0400
    UserDefinedSpare2 = 0x0800


class ConvType:
    """Possible values for SEC_wrapper.AddConverter() parameter.
    Values taken from ECInterfaces.cs.
    Definition of IEncConverter(s) interfaces and associated Enums.
    """
    Unknown = 0

    # bidirectional conversion types
    Legacy_to_from_Unicode = 1
    Legacy_to_from_Legacy = 2
    Unicode_to_from_Legacy = 3
    Unicode_to_from_Unicode = 4

    # unidirectional conversion
    Legacy_to_Unicode = 5
    Legacy_to_Legacy = 6
    Unicode_to_Legacy = 7
    Unicode_to_Unicode = 8


def getStringParam(strval):
    """Prepare the string to pass as a parameter to C++ code.
    :returns: None if an error occurs

    On Windows, with the converter name, either using c_char_p or else
    encoding results in ECDriver returning -7 Name Not Found error.
    """
    try:
        if platform.system() == "Windows":
            return ctypes.c_wchar_p(strval)
        byteStr = strval.encode('utf-8')
        return ctypes.c_char_p(byteStr)
    except UnicodeEncodeError:
        raise exceptions.DataNotFoundError(
            "Failed to encode string properly.")


def createBuffer(size):
    """Get a writable buffer that can be used to return a string from C++
    code.
    """
    if platform.system() == "Windows":
        # In C++ this is wchar_t *
        # In Python this is unicode string
        return ctypes.create_unicode_buffer(size)
    # In C++ this is char * for UTF-8
    # In Python this is bytes
    return ctypes.create_string_buffer(size)
