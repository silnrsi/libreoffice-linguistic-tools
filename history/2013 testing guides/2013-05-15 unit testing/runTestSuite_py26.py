#!/usr/bin/python
# -*- coding: UTF-8 -*-

## Import standard modules
import uno
from  com.sun.star.awt import XActionListener
from  com.sun.star.awt import XItemListener
from  com.sun.star.awt import XTextListener
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.sheet.CellFlags import VALUE as NUM_VAL, DATETIME, STRING
from com.sun.star.uno       import RuntimeException
from com.sun.star.uno import RuntimeException
import codecs
import copy
import ctypes
import datetime
import inspect
import logging
import os
import os.path
import platform
import re
import time
import unittest
import uno  # needed to import RuntimeException
import unohelper
import xml.dom.minidom
import xml.parsers.expat

#-------------------------------------------------------------------------------
# Start of Exceptions.py
#-------------------------------------------------------------------------------

class LingtError(Exception):
    """Base class for custom exceptions."""
    def __init__(self):
        if self.__class__ is LingtError:   # if base class is instantiated
            raise NotImplementedError

class MessageError(LingtError):
    """Base class for exceptions that can be used to display messages."""
    def __init__(self, msg, msg_args=None):
        if self.__class__ is MessageError:   # if base class is instantiated
            raise NotImplementedError
        self.msg      = msg
        self.msg_args = msg_args

class UserInterrupt(LingtError):
    """When the user presses Cancel to interrupt something."""
    pass

class DocAccessError(LingtError):
    """
    The current document could not be accessed, perhaps because it was closed.
    """
    pass

class FileAccessError(MessageError):
    """
    Error reading or writing files.
    """
    pass

class StyleError(MessageError):
    """Exception raised when there is a problem with styles."""
    pass

class ScopeError(MessageError):
    """A problem with the selection or cursor location."""
    pass

class ChoiceProblem(MessageError):
    """There is some problem with the options the user chose."""
    pass

class LogicError(MessageError):
    """Something wrong with program flow."""
    pass

#-------------------------------------------------------------------------------
# End of Exceptions.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Utils.py
#-------------------------------------------------------------------------------



#-------------------------------------------------------------------------------
# Initialize logging.
# - Executes when this module is loaded for the first time.
#-------------------------------------------------------------------------------
LOGGING_ENABLED  = True
#LOGGING_ENABLED  = False    # Set to False for production.

# These paths are used for logging and testing.
# Change them depending on your system.
if platform.system() == "Windows" :
    ROOTDIR = r"D:" + os.sep
else:
    ROOTDIR = r"/media/winD"
BASE_FOLDER = os.path.join(ROOTDIR, "dev", "OOoLT")
LOGGING_FILEPATH = os.path.join(BASE_FOLDER, "debug.txt")
TESTDATA_FOLDER  = os.path.join(BASE_FOLDER,
                   "LinguisticTools", "developing", "tests", "data files")

topLogger = logging.getLogger("lingt")
topLogger.setLevel(logging.ERROR)
if LOGGING_ENABLED:
    if os.path.exists(os.path.dirname(LOGGING_FILEPATH)):
        loggingFh = logging.FileHandler(LOGGING_FILEPATH)
        loggingFh.setLevel(logging.DEBUG)
        topFormatter = logging.Formatter(
                    "%(asctime)s - %(filename)s %(lineno)d - %(message)s")
        loggingFh.setFormatter(topFormatter)
        for previousHandler in topLogger.handlers:
            topLogger.removeHandler(previousHandler)
        topLogger.addHandler(loggingFh)

## Configure the values here to debug various packages.
## Set either the entire application or else a
## specific package to logging.DEBUG as desired.

#configLogger = logging.getLogger("lingt.UI")
configLogger = logging.getLogger("lingt")
configLogger.setLevel(logging.DEBUG)

#for loggerName in ("Frames",
#                   "Tables"):
#    configLogger = logging.getLogger(loggerName)
#    configLogger.setLevel(logging.WARN)


def safeStr(s):
    """Make the string so it won't crash when concatenating."""
    if s is None: return ""
    return s

class UnoObjs:
    """A data structure to manage UNO context and document objects."""
    def __init__(self, ctx, newDoctype='writer',
                 loadFromContext=True, loadDocObjs=True):
        # Calling uno.getComponentContext() here causes a bad crash.
        # Apparently in components, it is necessary to use the provided
        # context.
        self.ctx = ctx
        if loadFromContext:
            self.smgr       = ctx.ServiceManager
            self.desktop    = self.smgr.createInstanceWithContext(
                              "com.sun.star.frame.Desktop", ctx)
            self.dispatcher = self.smgr.createInstanceWithContext (
                              "com.sun.star.frame.DispatchHelper", ctx)
            self.document   = None
            if loadDocObjs:
                self.loadDocObjs(doctype=newDoctype)

    def loadDocObjs(self, newDocument=None, doctype='writer'):
        """
        Load UNO objects from self.document into the current object.
        """
        self.document = newDocument
        if newDocument is None:
            # Get whatever has the active focus.
            # This is not always reliable on Linux when opening and closing
            # documents because of focus rules, so hang on to a reference to
            # the document when possible.
            self.document = self.desktop.getCurrentComponent()
        try:
            # This will fail if either the document was not obtained (a simple
            # NoneType error) or if the document was disposed.
            self.controller = self.document.getCurrentController()
        except AttributeError:
            raise AttributeError('Could not get document.')
        self.frame      = self.controller.getFrame()
        self.window     = self.frame.getContainerWindow()
        self.dlgprov    = self.smgr.createInstanceWithArgumentsAndContext(
                          "com.sun.star.awt.DialogProvider",
                          (self.document,), self.ctx)
        self.text       = None
        self.viewcursor = None
        self.sheets     = None
        self.sheet      = None
        if doctype == 'writer':
            try:
                self.text = self.document.getText()
            except AttributeError:
                raise AttributeError('Could not get Writer document.')
            self.viewcursor = self.controller.getViewCursor()
        elif doctype == 'calc':
            try:
                self.sheets = self.document.getSheets()
                self.sheet  = self.sheets.getByIndex(0)
            except AttributeError:
                raise AttributeError('Could not get Calc spreadsheet.')
        else:
            raise AttributeError('Unexpected doc type ' + doctype)

    def getDocObjs(self, newDocument, doctype='writer'):
        """
        Factory method to manufacture new UnoObjs based on current UnoObjs
        and the given document.
        Returns the new UnoObjs object, and does not modify the current object.
        """
        newObjs = UnoObjs(self.ctx, loadFromContext=False)
        newObjs.smgr       = self.smgr
        newObjs.desktop    = self.desktop
        newObjs.dispatcher = self.dispatcher
        newObjs.loadDocObjs(newDocument, doctype)
        return newObjs

    @classmethod
    def getCtxFromSocket(cls):
        """Use when connecting from outside OOo, such as when testing."""
        localContext = uno.getComponentContext()
        resolver     = localContext.ServiceManager.createInstanceWithContext(
                       "com.sun.star.bridge.UnoUrlResolver", localContext)
        ctx          = resolver.resolve(
                       "uno:socket,host=localhost,port=2002;urp;"
                       "StarOffice.ComponentContext")
        return ctx

    def getOpenDocs(self, doctype='any'):
        """Returns unoObjs of currently open documents of type doctype."""
        doclist = []
        oComponents = self.desktop.getComponents()
        oDocs       = oComponents.createEnumeration()
        while oDocs.hasMoreElements():
            oDoc = oDocs.nextElement()
            if oDoc.supportsService("com.sun.star.text.TextDocument"):
                if doctype in ['any', 'writer']:
                    doclist.append(self.getDocObjs(oDoc, 'writer'))
            elif oDoc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                if doctype in ['any', 'calc']:
                    doclist.append(self.getDocObjs(oDoc, 'calc'))
        return doclist

def getControl(dlg, name):
    """Raises LogicError if control is not found."""
    ctrl = dlg.getControl(name)
    if not ctrl:
        raise LogicError("Error showing dialog: No %s control.",
                                    (name,))
    return ctrl

def createProp(name, value):
    """Creates an uno property."""
    prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    prop.Name  = name
    prop.Value = value
    return prop

def sameName(control1, control2):
    """
    Returns True if the UNO controls have the same name.
    This is the control name that is in the dialog designer,
    and also used with dlg.getControl().
    """
    return (control1.getModel().Name == control2.getModel().Name)

def xray(myObject, unoObjs):
    """For debugging.  To use this function, the XRay extension is required."""
    mspf = unoObjs.smgr.createInstanceWithContext(
        "com.sun.star.script.provider.MasterScriptProviderFactory",
        unoObjs.ctx)
    scriptPro = mspf.createScriptProvider("")
    try:
        xScript = scriptPro.getScript(
            "vnd.sun.star.script:XrayTool._Main.Xray?" +
            "language=Basic&location=application")
    except:
        raise RuntimeException(
            "\nBasic library Xray is not installed", unoObjs.ctx)
    xScript.invoke((myObject,), (), ())

class ConfigOptions:
    """
    A flexible structure to hold configuration options,
    typically settings that the user has selected or entered.
    Attributes can be created and used as needed.
    """
    pass

def uniqueList(seq): 
    """
    Return a list with duplicates removed and order preserved.
    Taken from http://www.peterbe.com/plog/uniqifiers-benchmark
    """
    checked = []
    for e in seq:
        if e not in checked:
            checked.append(e)
    return checked

def debug_tellNextChar(oCurs):
    """Returns a message that tells the character to the right of where the
    cursor is at.  This is useful for debugging.
    """
    try:
        oCursDbg = oCurs.getText().createTextCursorByRange(oCurs.getStart())
        oCursDbg.goRight(1, True)
        val = oCursDbg.getString()
        return "cursAtChar '" + val + "'"
    except:
        return "cursAtChar cannot get"

#-------------------------------------------------------------------------------
# End of Utils.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of FilePicker.py
#-------------------------------------------------------------------------------


def showFilePicker(
    genericUnoObjs, save=False, filters=[], defaultFilename=None):
    """Adapted from DannyB 2008"""

    logger = logging.getLogger("lingt.UI.FilePicker")
    logger.debug("showFilePicker begin")
    logger.debug("_")

    # Create a FilePicker dialog.
    dlg  = genericUnoObjs.smgr.createInstanceWithContext(
           "com.sun.star.ui.dialogs.FilePicker", genericUnoObjs.ctx)
    logger.debug("_")
    for name, ext in filters:
        dlg.appendFilter(name, ext)
    logger.debug("_")
    if defaultFilename:
        logger.debug("Default filename %s" % (defaultFilename)) 
        dlg.setDefaultName(defaultFilename)
    logger.debug("_")
    if save:
        logger.debug("_")
        dlgType = uno.getConstantByName(
            "com.sun.star.ui.dialogs.TemplateDescription.FILESAVE_SIMPLE")
    else:
        logger.debug("_")
        dlgType = uno.getConstantByName(
            "com.sun.star.ui.dialogs.TemplateDescription.FILEOPEN_SIMPLE")
    # Initialization is required for OOo3.0 on Vista
    logger.debug("_")
    dlg.initialize((dlgType,))

    # Execute it.
    logger.debug("_")
    dlg.execute()
    logger.debug("_")

    # Get an array of the files that the user picked.
    # There will only be one file in this array, because we did
    # not enable the multi-selection feature.
    filesList = dlg.getFiles()
    logger.debug("_")
    filepath = ""
    if filesList != None and len(filesList) > 0:
        filepath = filesList[0]
        # this line is like convertFromURL in OOo Basic
        filepath = unohelper.fileUrlToSystemPath(filepath)
        if os.path.exists(filepath):
            if os.path.isdir(filepath) or os.path.islink(filepath):
                # no file was selected
                filepath = ""
    logger.debug("filepath = " + filepath)
    return filepath

#-------------------------------------------------------------------------------
# End of FilePicker.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Locale.py
#-------------------------------------------------------------------------------


class Locale:
    def __init__(self, genericUnoObjs):
        """Initialize and get current OOo locale."""
        self.unoObjs = genericUnoObjs
        self.logger  = logging.getLogger("lingt.Locale")

        ## Get locale setting

        configProvider = self.unoObjs.smgr.createInstanceWithContext(
                         "com.sun.star.configuration.ConfigurationProvider",
                         self.unoObjs.ctx)
        args = (
            # trailing comma is required to make a tuple
            createProp("nodepath", "/org.openoffice.Setup/L10N"),
        )
        settings = configProvider.createInstanceWithArguments(
                   "com.sun.star.configuration.ConfigurationAccess", args)
        OOLang = settings.getByName("ooLocale")
        self.locale = OOLang[:2]  # grab first two characters
        self.logger.debug("locale = " + safeStr(self.locale))

        ## Make the English key values case insensitive

        translationsLower = dict()
        for en in self.translations.keys():
            translationsLower[en.lower()] = self.translations[en]
        self.translations.update(translationsLower)

    def getText(self, message_en):
        """Return L10N value.  If no translation is found for the current
        locale, returns the English message.
        """
        if message_en is None:
            return ""
        if self.locale == "en":
            return message_en
        key = message_en.lower()
        if key in self.translations:
            phrase_translations = self.translations.get(key)
            message_other = phrase_translations.get(self.locale)
            if message_other is not None and message_other != "":
                return message_other
        return message_en

    # ISO language codes used in struct com.sun.star.lang.Locale
    LANG_CODES = {
        'aa' : "Afar",
        'ab' : "Abkhazian",
        'af' : "Afrikaans",
        'am' : "Amharic",
        'ar' : "Arabic",
        'as' : "Assamese",
        'ay' : "Aymara",
        'az' : "Azerbaijani",
        'ba' : "Bashkir",
        'be' : "Byelorussian",
        'bg' : "Bulgarian",
        'bh' : "Bihari",
        'bi' : "Bislama",
        'bn' : "Bengali",
        'bo' : "Tibetan",
        'br' : "Breton",
        'ca' : "Catalan",
        'co' : "Corsican",
        'cs' : "Czech",
        'cy' : "Welsh",
        'da' : "Danish",
        'de' : "German",
        'dz' : "Bhutani",
        'el' : "Greek",
        'en' : "English",
        'eo' : "Esperanto",
        'es' : "Spanish",
        'et' : "Estonian",
        'eu' : "Basque",
        'fa' : "Persian",
        'fi' : "Finnish",
        'fj' : "Fiji",
        'fo' : "Faroese",
        'fr' : "French",
        'fy' : "Frisian",
        'ga' : "Irish",
        'gd' : "Scots Gaelic",
        'gl' : "Galician",
        'gn' : "Guarani",
        'gu' : "Gujarati",
        'ha' : "Hausa",
        'he' : "Hebrew",
        'hi' : "Hindi",
        'hr' : "Croatian",
        'hu' : "Hungarian",
        'hy' : "Armenian",
        'ia' : "Interlingua",
        'id' : "Indonesian",
        'ie' : "Interlingue",
        'ik' : "Inupiak",
        'is' : "Icelandic",
        'it' : "Italian",
        'iu' : "Inuktitut",
        'ja' : "Japanese",
        'jw' : "Javanese",
        'ka' : "Georgian",
        'kk' : "Kazakh",
        'kl' : "Greenlandic",
        'km' : "Cambodian",
        'kn' : "Kannada",
        'ko' : "Korean",
        'ks' : "Kashmiri",
        'ku' : "Kurdish",
        'ky' : "Kirghiz",
        'la' : "Latin",
        'ln' : "Lingala",
        'lo' : "Laothian",
        'lt' : "Lithuanian",
        'lv' : "Latvian",
        'mg' : "Malagasy",
        'mi' : "Maori",
        'mk' : "Macedonian",
        'ml' : "Malayalam",
        'mn' : "Mongolian",
        'mo' : "Moldavian",
        'mr' : "Marathi",
        'ms' : "Malay",
        'mt' : "Maltese",
        'my' : "Burmese",
        'na' : "Nauru",
        'ne' : "Nepali",
        'nl' : "Dutch",
        'no' : "Norwegian",
        'oc' : "Occitan",
        'om' : "Oromo (Afan)",
        'or' : "Oriya",
        'pa' : "Punjabi",
        'pl' : "Polish",
        'ps' : "Pashto, Pushto",
        'pt' : "Portuguese",
        'qu' : "Quechua",
        'rm' : "Rhaeto-Romance",
        'rn' : "Kirundi",
        'ro' : "Romanian",
        'ru' : "Russian",
        'rw' : "Kinyarwanda",
        'sa' : "Sanskrit",
        'sd' : "Sindhi",
        'sg' : "Sangho",
        'sh' : "Serbo-Croatian",
        'si' : "Sinhalese",
        'sk' : "Slovak",
        'sl' : "Slovenian",
        'sm' : "Samoan",
        'sn' : "Shona",
        'so' : "Somali",
        'sq' : "Albanian",
        'sr' : "Serbian",
        'ss' : "Siswati",
        'st' : "Sesotho",
        'su' : "Sundanese",
        'sv' : "Swedish",
        'sw' : "Swahili",
        'ta' : "Tamil",
        'te' : "Telugu",
        'tg' : "Tajik",
        'th' : "Thai",
        'ti' : "Tigrinya",
        'tk' : "Turkmen",
        'tl' : "Tagalog",
        'tn' : "Setswana",
        'to' : "Tonga",
        'tr' : "Turkish",
        'ts' : "Tsonga",
        'tt' : "Tatar",
        'tw' : "Twi",
        'ug' : "Uighur",
        'uk' : "Ukrainian",
        'ur' : "Urdu",
        'uz' : "Uzbek",
        'vi' : "Vietnamese",
        'vo' : "Volapuk",
        'wo' : "Wolof",
        'xh' : "Xhosa",
        'yi' : "Yiddish",
        'yo' : "Yoruba",
        'za' : "Zhuang",
        'zh' : "Chinese",
        'zu' : "Zulu"}

    def getLocaleList(self):
        """
        Returns a list of tuples with locale description and locale obj.
        This only shows a few locales set by the user, not a big list.
        """
        oLingu = self.unoObjs.smgr.createInstanceWithContext(
                 "com.sun.star.linguistic2.LinguServiceManager",
                 self.unoObjs.ctx)
 
        # css.linguistic2.Thesaurus, SpellChecker and Proofreader are allowed
        localeObjs = oLingu.getAvailableLocales(
                      "com.sun.star.linguistic2.Thesaurus")
 
        descList = []
        for localeObj in localeObjs:
            desc = "%s (%s)" % (Locale.LANG_CODES[localeObj.Language],
                                localeObj.Country)
            descList.append((desc, localeObj))
        return descList

    def sameLocale(self, loc1, loc2):
        """Compares two locale structures."""
        if loc1.Language == loc2.Language and loc1.Country == loc2.Country:
            return True
        return False

    translations = {

        ## Dynamic labels in dialogs

        u"Back to Settings" : {
            'es' :
            u"Volver a la configuraci\xF3n",
            'fr' :
            u"Atteindre la configuration",
        },
        u"Column" : {
            'es' :
            u"Columna",
            'fr' :
            u"Colonne",
        },
        u"Get Phonology Examples" : {
            'es' :
            u"Obtener ejemplos de fonolog\xEDa",
            'fr' :
            u"Obtenir des exemples de phonologie",
        },
        u"Get Interlinear Grammar Examples" : {
            'es' :
            u"Obtener ejemplos de gram\xE1tica",
            'fr' :
            u"Obtenir des exemples de grammaire",
        },
        u"Get words" : {
            'es' :
            u"Obtener palabras",
            'fr' :
            u"Obtenir mots",
        },
        u"Go to Practice" : {
            'es' :
            u"Ir a la pr\xE1ctica",
            'fr' :
            u"Atteindre exercices",
        },
        u"Make Empty List" : {
            'es' :
            u"Hacer una lista vac\xEDa",
            'fr' :
            u"Cr\xE9er liste vide",
        },
        u"Make List" : {
            'es' :
            u"Hacer una lista",
            'fr' :
            u"Cr\xE9er liste",
        },
        u"Replace with Example" : {
            'es' :
            u"Reemplazar con ejemplo",
            'fr' :
            u"Remplacer par exemple",
        },
        u"Replace All" : {
            'es' :
            u"Reemplazar todo",
            'fr' :
            u"Remplacer tout",
        },
        u"Script Practice" : {
            'es' :
            u"Practica de script",
            'fr' :
            u"Exercices d'\xE9criture",
        },
        u"Script Practice - Settings" : {
            'es' :
            u"Practica de script - Configuraci\xF3n",
            'fr' :
            u"Exercices d'\xE9criture - Configuration",
        },
        u"Spelling" : {
            'es' :
            u"Ortograf\xEDa",
            'fr' :
            u"V\xE9rification d'orthographe",
        },
        u"Update Example" : {
            'es' :
            u"Actualizar el ejemplo",
            'fr' :
            u"Mettre l'exemple \xE0 jour",
        },
        u"Update All" : {
            'es' :
            u"Actualizar todos",
            'fr' :
            u"Tout mettre \xE0 jour",
        },
        u"Word List and Spelling" : {
            'es' :
            u"Lista de palabras y ortograf\xEDa",
            'fr' :
            u"Liste de mots et orthographe",
        },

        ## Localized text values

        u"(none)" : {
            'es' :
            u"(ninguno)",
            'fr' :
            u"(aucun)",
        },
        u"(cannot make word)" : {
            'es' :
            u"(no puede hacer la palabra)",
            'fr' :
            u"(impossible de cr\xE9er mot)",
        },
        u"(no words found)" : {
            'es' :
            u"(no hay palabras encontradas)",
            'fr' :
            u"(aucun mot trouv\xE9)",
        },
        u"Whole Document" : {
            'es' :
            u"Documento completo",
            'fr' :
            u"Document entier",
        },

        ## Status messages for ProgressBar

        u"Converting..." : {
            'es' :
            u"Convirtiendo...",
            'fr' :
            u"Conversion en cours...",
        },
        u"Finding text..." : {
            'es' :
            u"Buscando texto...",
            'fr' :
            u"Recherche de texte...",
        },
        u"Generating List..." : {
            'es' :
            u"Generando lista...",
            'fr' :
            u"Cr\xE9ation de liste...",
        },
        u"Getting data..." : {
            'es' :
            u"Obteniendo datos...",
            'fr' :
            u"L\x92obtention des donn\xE9es...",
        },
        u"Saving file..." : {
            'es' :
            u"Guardando archivo...",
            'fr' :
            u"Enregistrement de fichier...",
        },
        u"Searching for occurrences..." : {
            'es' :
            u"Buscando ocurrencias...",
            'fr' :
            u"Recherche des occurrences...",
        },
        u"Sorting..." : {
            'es' :
            u"Ordenando...",
            'fr' :
            u"Triage...",
        },
        u"Loading data..." : {
            'es' :
            u"Cargando datos...",
            'fr' :
            u"Chargement des donn\xE9es...",
        },

        ## Error messages

        u"%s is already in the list." : {
            'es' :
            u"%s ya est\xE1 en la lista.",
            'fr' :
            u"%s est d\xE9j\xE0 dans la liste.",
        },
        u"Add '%s' as a new abbreviation?" : {
            'es' :
            u"Agregar '%s' como una abreviatura de nuevo?",
            'fr' :
            u"Ajouter '%s' comme nouvelle abr\xE9viation ?",
        },
        u"Cannot be in a header or footer." : {
            'es' :
            u"No puede ser en un encabezado o un pie de p\xE1gina.",
            'fr' :
            u"Interdit dans un en-t\xEAte ou pied de page.",
        },
        u"Cannot be inside a table or frame." : {
            'es' :
            u"No se puede estar dentro de una tabla o un marco.",
            'fr' :
            u"Interdit dans un tableau ou cadre",
        },
        u"Cannot find file %s" : {
            'es' :
            u"No se puede encontrar el archivo %s",
            'fr' :
            u"Impossible de trouver le fichier %s",
        },
        u"Cannot insert text here." : {
            'es' :
            u"No se puede insertar texto aqu\xED.",
            'fr' :
            u"Impossible d'ins\xE9rer texte ici.",
        },
        u"Character style '%s' is missing" : {
            'es' :
            u"No se encuentra el estilo de car\xE1cter '%s'",
            'fr' :
            u"Style de caract\xE8re '%s' introuvable",
        },
        u"Column width is not a number." : {
            'es' :
            u"El ancho de columna no es un n\xFAmero.",
            'fr' :
            u"La largeur de colonne n'est pas un nombre.",
        },
        u"Converting..." : {
            'es' :
            u"Conversi\xF3n en proceso...",
            'fr' :
            u"Conversion en cours...",
        },
        u"Could not find ref number %s" : {
            'es' :
            u"No se encuentra el n\xFAmero de referencia %s",
            'fr' :
            u"Num\xE9ro de r\xE9f\xE9rence %s introuvable.",
        },
        u"Could not find ref number %s\n\nSuggestions\n%s" : {
            'es' :
            u"No se encuentra el n\xFAmero de referencia %s\n\nSugerencias\n%s",
            'fr' :
            u"Num\xE9ro de r\xE9f\xE9rence %s introuvable.\n\nSuggestions\n%s",
        },
        u"Did not find any data in file %s" : {
            'es' :
            u"No ha encontrado ning\xFAn dato en el archivo %s",
            'fr' :
            u"Aucune donn\xE9e n'a \xE9t\xE9 trouv\xE9e dans le fichier %s",
        },
        u"Did not find any similar words." : {
            'es' :
            u"No encontr\xF3 algunas palabras similares.",
            'fr' :
            u"On n'a trouv\xE9 aucun mot similaire.",
        },
        u"Did not find any words for the list." : {
            'es' :
            u"No encontr\xF3 algunas palabras para la lista.",
            'fr' :
            u"On n'a trouv\xE9 aucun mot pour la liste.",
        },
        u"Did not find anything in column %s." : {
            'es' :
            u"No encontr\xF3 nada en la columna %s.",
            'fr' :
            u"On n'a rien trouv\xE9 dans colonne %s.",
        },
        u"Did not find scope of change." : {
            'es' :
            u"No ha encontrado el \xE1mbito del cambio.",
            'fr' :
            u"L'\xE9tendue de changement n'a pas \xE9t\xE9 trouv\xE9e.",
        },
        u"EncConverters does not seem to be installed properly." : {
            'es' :
            u"EncConverters no parece que se haya instalado correctamente.",
            'fr' :
            u"EncConverters semble \xEAtre mal install\xE9",
        },
        u"Error parsing %s user variable. Please go to Insert -> Fields and "
        u"fix the problem." : {
            'es' :
            u"Error al analizar %s variable de usuario. Por favor, vaya a "
            u"Insertar -> Campos y solucionar el problema.",
            'fr' :
            u"Erreur en analysant la variable utilisateur %s. Veuillez "
            u"atteindre Insertion -> Champs pour r\xE9soudre le probl\xE8me.",
        },
        u"Error reading file %s" : {
            'es' :
            u"Error al leer el archivo %s",
            'fr' :
            u"Erreur en lisant le fichier %s",
        },
        u"Error reading file %s\n\n%s" : {
            'es' :
            u"Error al leer el archivo %s\n\n%s",
            'fr' :
            u"Erreur en lisant le fichier %s\n\n%s",
        },
        u"Error with file: %s" : {
            'es' :
            u"Error con el archivo: %s",
            'fr' :
            u"Erreur de fichier : %s",
        },
        u"Error reading spreadsheet." : {
            'es' :
            u"Error al leer la hoja de c\xE1lculo",
            'fr' :
            u"Erreur de lecture de classeur",
        },
        u"Error reading the list.\n\n%s" : {
            'es' :
            u"Error al leer la lista.\n\n%s",
            'fr' :
            u"Erreur de lecture de liste.\n\n%s",
        },
        u"Error writing to spreadsheet." : {
            'es' :
            u"Error al escribir al hoja de c\xE1lculo.",
            'fr' :
            u"Erreur d'\xE9criture de classeur.",
        },
        u"Error: Could not create dialog." : {
            'es' :
            u"Error: No se pudo crear el di\xE1logo.",
            'fr' :
            u"Erreur : Impossible de cr\xE9er dialogue.",
        },
        u"Error: Could not show dialog window." : {
            'es' :
            u"Error: No se pudo mostrar el cuadro de di\xE1logo.",
            'fr' :
            u"Erreur : Impossible d'afficher dialogue.",
        },
        u"Error: EncConverters returned %d%s." : {
            'es' :
            u"Error: EncConverters devolvi\xF3 %d%s.",
            'fr' :
            u"Erreur: EncConverters a r\xE9pondu %d%s.",
        },
        u"Failed to encode string properly." : {
            'es' :
            u"No pudo codificar correctamente la cadena.",
            'fr' :
            u"Impossible d'encoder correctement la cha\xEEne.",
        },
        u"File does not seem to be from Toolbox or FieldWorks: %s" : {
            'es' :
            u"El archivo no parece ser del Toolbox o Fieldworks: %s",
            'fr' :
            u"Il semble que ce fichier n'a pas \xE9t\xE9 cr\xE9\xE9 par Toolbox ou "
            u"FieldWorks: %s",
        },
        u"File is already in the list." : {
            'es' :
            u"El archivo ya est\xE1 en la lista.",
            'fr' :
            u"Le fichier est d\xE9j\xE0 dans la liste.",
        },
        u"Found %d similar words." : {
            'es' :
            u"Encontrado %d palabras similares.",
            'fr' :
            u"%d mots similaires trouv\xE9s.",
        },
        u"Found %d words." : {
            'es' :
            u"Encontrado %d palabras.",
            'fr' :
            u"%d mots trouv\xE9s.",
        },
        u"Found %d paragraphs and made %d change%s." : {
            'es' :
            u"Ha encontrado %d p\xE1rrafos y hizo %d cambio%s.",
            'fr' :
            u"%d paragraphes trouv\xE9s et %d changement%s faits.",
        },
        u"Found a ref number, but it must be in an outer table in order to "
        u"be updated." : {
            'es' :
            u"Ha encontrado un n\xFAmero de referencia, pero debe estar en una "
            u"tabla de exterior para ser actualizados.",
            'fr' :
            u"N\xB0 de r\xE9f. trouv\xE9, mais pour l'actualier il doit \xEAtre dans un "
            u"cadre exterieur",
        },
        u"Frame style '%s' is missing" : {
            'es' :
            u"No se encuentra el estilo del marco '%s'",
            'fr' :
            u"Style de cadre '%s' introuvable",
        },
        u"If you want to use LIFT data, then first specify a LIFT file "
        u"exported from FieldWorks." : {
            'es' :
            u"Si desea utilizar los datos LIFT, en primer lugar especificar "
            u"un archivo LIFT exportados de Fieldworks.",
            'fr' :
            u"Pour utiliser des donn\xE9es LIFT il faut sp\xE9cifier un fichier "
            u"LIFT export\xE9 de FieldWorks.",
        },
        u"Library error: %s." : {
            'es' :
            u"Error de rutinas: %s.",
            'fr' :
            u"Erreur de logiciel: %s.",
        },
        u"Made %d change%s." : {
            'es' :
            u"Hizo %d cambio%s.",
            'fr' :
            u"%d changement%s faits.",
        },
        u"Made %d correction%s." : {
            'es' :
            u"Hizo %d correccione%s.",
            'fr' :
            u"On a fait %d correction%s.",
        },
        u"Made list of %d words." : {
            'es' :
            u"Hizo una lista de %d palabras.",
            'fr' :
            u"On a cr\xE9\xE9 une liste de %d mots.",
        },
        u"Make this change?" : {
            'es' :
            u"\xBFHacer este cambio?",
            'fr' :
            u"Modifier ceci?",
        },
        u"Make this change? (%s -> %s)" : {
            'es' :
            u"\xBFHacer este cambio? (%s -> %s)",
            'fr' :
            u"Modifier ceci? (%s -> %s)",
        },
        u"Missed word '%s'. Keep going?" : {
            'es' :
            u"Hubo un problema con la palabra '%s'. \xBFSeguir adelante?",
            'fr' :
            u"Un probl\xE8me en le mot '%s'. Continuer ?",
        },
        u"No changes, but modified style of %d paragraph%s." : {
            'es' :
            u"No hubo cambios, pero el estilo de %d p\xE1rrafo%s se ha "
            u"modificado.",
            'fr' :
            u"Pas de changements, mais le style de %d paragraphe%s a \xE9t\xE9 "
            u"chang\xE9.",
        },
        u"No changes." : {
            'es' :
            u"No hubo cambios.",
            'fr' :
            u"Pas de changements.",
        },
        u"No converter was specified." : {
            'es' :
            u"No convertidor se ha especificado.",
            'fr' :
            u"Aucun convertisseur sp\xE9cifi\xE9.",
        },
        u"No data found." : {
            'es' :
            u"No se encontraron datos",
            'fr' :
            u"Aucune donn\xE9e trouv\xE9e.",
        },
        u"No locale was specified." : {
            'es' :
            u"Un locale no se ha especificado",
            'fr' :
            u"Aucuns param\xE8tres r\xE9gionaux sp\xE9cifi\xE9s.",
        },
        u"No more existing examples found." : {
            'es' :
            u"No se ha encontrado m\xE1s ejemplos existentes",
            'fr' :
            u"Il n'y a plus d'exemples trouv\xE9s.",
        },
        u"No more possible abbreviations found." : {
            'es' :
            u"No se ha encontrado m\xE1s abreviaturas posibles",
            'fr' :
            u"On ne trouve plus des abr\xE9viations possibles.",
        },
        u"No more reference numbers found." : {
            'es' :
            u"No se ha encontrado m\xE1s n\xFAmeros de referencia",
            'fr' :
            u"On ne trouve plus des num\xE9ros de r\xE9f\xE9rence.",
        },
        u"No SF markers were specified. Continue anyway?" : {
            'es' :
            u"Ning\xFAn marcadores SFM fueron especificados. \xBFDesea continuar?",
            'fr' :
            u"Aucune balise SFM sp\xE9cifi\xE9e. Continuer quand m\xEAme?",
        },
        u"No spreadsheet is open." : {
            'es' :
            u"No hay ninguna hoja de c\xE1lculo abierto.",
            'fr' :
            u"Aucun classeur est ouvert.",
        },
        u"No writing systems found." : {
            'es' :
            u"No se encontraron sistemas de escritura.",
            'fr' :
            u"Aucune syst\xE8mes d'\xE9criture trouv\xE9e.",
        },
        u"No Xpath expressions were specified. Continue anyway?" : {
            'es' :
            u"Ning\xFAn expresiones XPath fueron especificadas. \xBFDesea continuar?",
            'fr' :
            u"Aucune expression Xpath sp\xE9cifi\xE9e. Continuer quand m\xEAme?",
        },
        u"No text is selected." : {
            'es' :
            u"No hay texto seleccionado.",
            'fr' :
            u"Aucun texte s\xE9lectionn\xE9. ",
        },
        u"Paragraph style '%s' is missing" : {
            'es' :
            u"No se encuentra el estilo de p\xE1rrafo '%s'",
            'fr' :
            u"Style de paragraphe '%s' introuvable",
        },
        u"Please add a file to get words." : {
            'es' :
            u"Por favor, a\xF1ada un archivo para obtener las palabras.",
            'fr' :
            u"Veuillez ajouter un fichier duquel on peut obtenir des mots.",
        },
        u"Please do not select individual table cells." : {
            'es' :
            u"Por favor, no seleccione las celdas individuales de la tabla.",
            'fr' :
            u"Veuillez ne pas choisir des cellules individuelles.",
        },
        u"Please enter a number for max length." : {
            'es' :
            u"Por favor, introduzca un n\xFAmero para la longitud m\xE1xima.",
            'fr' :
            u"Veuillez entrer la longueur maximum.",
        },
        u"Please enter a ref number." : {
            'es' :
            u"Por favor, introduzca un n\xFAmero de referencia.",
            'fr' :
            u"Veuillez entrer un num\xE9ro de r\xE9f\xE9rence.",
        },
        u"Please enter a value for column width." : {
            'es' :
            u"Por favor, introduzca un valor para el ancho de la columna.",
            'fr' :
            u"Veuillez entrer la largeur de colonne.",
        },
        u"Please go to Grammar Settings and specify a file." : {
            'es' :
            u"Por favor, vaya a la Configuraci\xF3n de gram\xE1tica y especifique "
            u"un archivo.",
            'fr' :
            u"Veuillez choisir un fichier dans Configuration de grammaire.",
        },
        u"Please go to Phonology Settings and specify a file." : {
            'es' :
            u"Por favor, vaya a la Configuraci\xF3n de fonolog\xEDa y especifique "
            u"un archivo.",
            'fr' :
            u"Veuillez sp\xE9cifier un fichier dans Configuration de phonologie.",
        },
        u"Please load a word list by clicking on the Files... button.  When "
        u"file settings are finished, click Get words." : {
            'es' :
            u"Por favor, cargue una lista de palabras haciendo clic en el "
            u"bot\xF3n Archivos. Cuando la configuraci\xF3n de archivo se haya "
            u"terminado, haga clic en Obtener palabras.",
            'fr' :
            u"Veuillez charger une liste de mots en cliquant sur Fichiers... "
            u"Apr\xE8s avoir fait la configuration de fichier",
        },
        u"Please open one or more documents to search." : {
            'es' :
            u"Por favor, abrir uno o m\xE1s documentos para la b\xFAsqueda.",
            'fr' :
            u"Veuillez ouvrir un ou plusieurs documents \xE0 rechercher.",
        },
        u"Please save the current document first." : {
            'es' :
            u"Por favor, primero guarde el documento actual.",
            'fr' :
            u"Veuillez enregistrer d'abord le document actuel.",
        },
        u"Please save the spreadsheet first." : {
            'es' :
            u"Por favor, primero guarde la hoja de c\xE1lculo.",
            'fr' :
            u"Veuillez d'abord enregistrer le classeur",
        },
        u"Please select a converter." : {
            'es' :
            u"Por favor, seleccione un convertidor.",
            'fr' :
            u"Veuillez choisir un convertisseur.",
        },
        u"Please select a file in the list." : {
            'es' :
            u"Por favor, seleccione un archivo en la lista.",
            'fr' :
            u"Veuillez choisir un fichier dans la liste.",
        },
        u"Please select a language name." : {
            'es' :
            u"Por favor, seleccione un nombre de idioma.",
            'fr' :
            u"Veuillez s\xE9lectionner un nom de langue.",
        },
        u"Please select a scope character style." : {
            'es' :
            u"Por favor, seleccione un estilo de car\xE1cter \xE1mbito.",
            'fr' :
            u"Veuillez choisir un style de caract\xE8re pour l'\xE9tendue.",
        },
        u"Please select a scope font." : {
            'es' :
            u"Por favor, seleccione una fuente \xE1mbito.",
            'fr' :
            u"Veuillez choisir une police pour l'\xE9tendue.",
        },
        u"Please select a scope paragraph style." : {
            'es' :
            u"Por favor, seleccione un estilo de p\xE1rrafo \xE1mbito.",
            'fr' :
            u"Veuillez choisir un style de paragraphe pour l'\xE9tendue.",
        },
        u"Please select a script." : {
            'es' :
            u"Por favor, seleccione un script.",
            'fr' :
            u"Veuillez choisir un \xE9criture.",
        },
        u"Please select a target font." : {
            'es' :
            u"Por favor, seleccione una fuente destino.",
            'fr' :
            u"Veuillez choisir une police cible.",
        },
        u"Please select a target style." : {
            'es' :
            u"Por favor, seleccione un estilo destino.",
            'fr' :
            u"Veuillez choisir un style cible.",
        },
        u"Please select an item in the list." : {
            'es' :
            u"Por favor, seleccione un elemento de la lista.",
            'fr' :
            u"Veuillez choisir un \xE9l\xE9ment dans la liste.",
        },
        u"Please select or enter something to find." : {
            'es' :
            u"Por favor seleccione o escriba algo para buscar.",
            'fr' :
            u"Veuillez s\xE9lectionner ou saisir quelque chose \xE0 rechercher.",
        },
        u"Please select the converter again." : {
            'es' :
            u"Por favor, seleccione el convertidor de nuevo.",
            'fr' :
            u"Veuillez choisir encore le convertisseur.",
        },
        u"Please specify SFMs." : {
            'es' :
            u"Por favor, especifique los SFMs.",
            'fr' :
            u"Veuillez sp\xE9cifier les balises (SFMs).",
        },
        u"Please specify a file to export." : {
            'es' :
            u"Por favor, especifique un archivo para exportar.",
            'fr' :
            u"Veuillez sp\xE9cifier un fichier \xE0 exporter.",
        },
        u"Please specify a row between 2 and %d." : {
            'es' :
            u"Por favor, especifica una fila entre 2 y %d.",
            'fr' :
            u"Veuillez sp\xE9cifier une ligne entre 2 et %d.",
        },
        u"Please specify a scope." : {
            'es' :
            u"Por favor, especifique un \xE1mbito.",
            'fr' :
            u"Veuillez sp\xE9cifier l'\xE9tendue.",
        },
        u"Please specify a word list file. To make a new empty list, go to "
        u"Word List and Spelling and then save the spreadsheet file." : {
            'es' :
            u"Por favor, especifique un archivo de una lista de palabras. "
            u"Para crear una nueva lista vac\xEDa, vaya a Lista de palabras y "
            u"ortograf\xEDa y guarde el archivo de hoja de c\xE1lculo.",
            'fr' :
            u"Veuillez sp\xE9cifier un fichier de liste de mots. Pour cr\xE9er une "
            u"nouvelle liste vide, atteindre Liste de mots et orthographe, "
            u"puis enregistrer le classeur.",
        },
        u"Replaced %d example%s." : {
            'es' :
            u"reemplazado %d ejemplo%s.",
            'fr' :
            u"%d exemple%s a \xE9t\xE9 remplas\xE9.",
        },
        u"Searching for occurrences..." : {
            'es' :
            u"Buscando ocurrencias...",
            'fr' :
            u"Recherche des occurrences...",
        },
        u"Some words could not be converted." : {
            'es' :
            u"Algunas palabras no se pueden convertir.",
            'fr' :
            u"Impossible de convertir certains mots",
        },
        u"Spell check finished." : {
            'es' :
            u"Spell check finished.",
            'fr' :
            u"V\xE9rification d'orthographe termin\xE9e.",
        },
        u"Successfully finished conversion." : {
            'es' :
            u"Terminado con \xE9xito la conversi\xF3n.",
            'fr' :
            u"Conversion termin\xE9e avec succ\xE8s.",
        },
        u"System error: Unable to get UNO object." : {
            'es' :
            u"Error del sistema: No se puede obtener objeto UNO.",
            'fr' :
            u"Erreur de syst\xE8me\xA0: Impossible d'acc\xE9der \xE0 l'objet UNO.",
        },
        u"The cursor cannot be in a header or footer." : {
            'es' :
            u"El cursor no puede estar en un encabezado o en un pie de p\xE1gina.",
            'fr' :
            u"Le curseur ne peut pas se trouver dans un en-t\xEAte ou dans un "
            u"pied de page.",
        },
        u"The cursor cannot be inside a table or frame." : {
            'es' :
            u"El cursor no puede estar dentro de una tabla o un marco.",
            'fr' :
            u"Le curseur ne peut pas se trouver dans un tableau ou dans un "
            u"cadre.",
        },
        u"There do not seem to be any examples to insert." : {
            'es' :
            u"No parece haber ning\xFAn ejemplo para insertar.",
            'fr' :
            u"Il semble qu'il n'existe pas d'exemples \xE0 ins\xE9rer.",
        },
        u"There was a problem while writing the list.\n\n%s" : {
            'es' :
            u"Hubo un problema al escribir la lista.\n\n%s",
            'fr' :
            u"Un probl\xE8me est survenu en \xE9crivant la liste.\n\n%s",
        },
        u"This document stores %s settings.  "
        u"Please leave it open while using %s.  "
        u"If you want to keep the settings to use again later, "
        u"then save this document." : {
            'es' :
            u"Este documento guarda la configuraci\xF3n de %s. "
            u"Por favor, dejarlo abierto durante el uso de %s. "
            u"Si desea mantener la configuraci\xF3n para utilizarlo m\xE1s adelante, "
            u"guarde este documento.",
            'fr' :
            u"Ce document contient la configuration de la fonction %s. "
            u"Veuillez le laisser ouvert en utilisant %s. "
            u"Pour garder la configuration afin de la r\xE9utiliser plus tard, "
            u"enregistrer ce document.",
        },
        u"This expression is already in the list." : {
            'es' :
            u"Esta expresi\xF3n est\xE1 ya en la lista.",
            'fr' :
            u"Cette expression est d\xE9j\xE0 dans la liste.",
        },
        u"This will change the case of the entire list from '%s' to '%s.' "
        u"Continue?" : {
            'es' :
            u"Esto cambiar\xE1 el caso de la lista completa de '%s' a '%s'. "
            u"\xBFDesea continuar?",
            'fr' :
            u"Ceci changera la casse de toute la liste de '%s' \xE0 '%s'. "
            u"Continuer ?",
        },
        u"To update examples, 'Outer table' must be marked in Grammar "
        u"Settings." : {
            'es' :
            u"'Tabla de exterior' debe estar en la Configuraci\xF3n de gram\xE1tica.",
            'fr' :
            u"'Cadre exterieur' doit \xEAtre dans Configuration de grammaire.",
        },
        u"Unexpected file type %s" : {
            'es' :
            u"Tipo de archivo inesperado %s",
            'fr' :
            u"Type de fichier %s inattendu",
        },
        u"Unexpected font type %s." : {
            'es' :
            u"Tipo de fuente inesperada %s.",
            'fr' :
            u"Police de type %s inattendue.",
        },
        u"Unexpected new value %s." : {
            'es' :
            u"Nuevo valor inesperado %s.",
            'fr' :
            u"Nouvelle valeur inattendue %s.",
        },
        u"Unexpected value %s" : {
            'es' :
            u"Valor inesperado %s.",
            'fr' :
            u"Valeur inattendue %s",
        },
        u"Unknown file type for %s" : {
            'es' :
            u"Tipo de archivo desconocido para %s",
            'fr' :
            u"Type de fichier inconnu pour %s",
        },
        u"Update all examples now?  It is recommended to save a copy of your "
        u"document first." : {
            'es' :
            u"\xBFActualizar todos los ejemplos ahora?  Se recomienda que "
            u"primero guarde una copia de su documento.",
            'fr' :
            u"Actualiser tous les exemples maintenant ? Il est conseill\xE9 "
            u"d'enregistrer le document d'abord.",
        },
        u"Updated '%s' %d times in a row. Keep going?" : {
            'es' :
            u"Actualizado '%s' %d veces seguidas. \xBFSeguir adelante?",
            'fr' :
            u"'%s' a \xE9t\xE9 actualis\xE9 %d fois de suite. Continuer ?",
        },
        u"Updated %d example%s." : {
            'es' :
            u"Actualizado %d ejemplo%s.",
            'fr' :
            u"%d exemple%s a \xE9t\xE9 actualis\xE9.",
        },
        u"Value %d for column width is too high." : {
            'es' :
            u"El valor de %d para el ancho de columna es demasiado alta.",
            'fr' :
            u"%d est trop grande comme largeur de colonne.",
        },
        u"Value for column width must be more than zero." : {
            'es' :
            u"El valor para el ancho de columna debe ser mayor de cero.",
            'fr' :
            u"La largeur de colonne doit \xEAtre sup\xE9rieure \xE0 z\xE9ro.",
        },
        u"'Whole Document' must be the only thing to find." : {
            'es' :
            u"'Documento Completo' debe ser la \xFAnica cosa para buscar.",
            'fr' :
            u"'Document entier' doit \xEAtre la seule chose \xE0 rechercher",
        },
        u"You did not specify anything to find. Continue anyway?" : {
            'es' :
            u"No ha especificado nada que encontrar. \xBFDesea continuar?",
            'fr' :
            u"Vous n'avez sp\xE9cifier aucune chose \xE0 rechercher. Continuer "
            u"quand m\xEAme?",
        },
    }

#-------------------------------------------------------------------------------
# End of Locale.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of MessageBox.py
#-------------------------------------------------------------------------------



class MessageBox:
    """
    Message box for python, like OOo Basic MsgBox.
    Localizes messages before displaying.
    Modified from Villeroy 2007.
    """
    STYPE_ERROR = 'errorbox'
    STYPE_QUERY = 'querybox'
    STYPE_WARN  = 'warningbox' 
    STYPE_INFO  = 'infobox' # info always shows one OK button alone! 
    BUTTONS_OK            = 1
    BUTTONS_OK_CANCEL     = 2
    BUTTONS_YES_NO        = 3 
    BUTTONS_YES_NO_CANCEL = 4 
    RESULT_CANCEL = 0
    RESULT_OK     = 1
    RESULT_YES    = 2
    RESULT_NO     = 3 

    def __init__(self, genericUnoObjs):
        """
        Requires the frame of the higher level window.
        May throw com.sun.star.lang.DisposedException.
        Do not call logging methods from this __init__ routine.
        """
        self.parent  = genericUnoObjs.frame.getContainerWindow() 
        self.toolkit = self.parent.getToolkit()
        self.logger  = logging.getLogger("lingt.UI.MessageBox")
        self.locale  = Locale(genericUnoObjs)

    def display(self, message='', vals=None, title=''):
        self.logger.debug("Displaying message box.")
        buttons = MessageBox.BUTTONS_OK
        self.__showDialog(message, vals, title, buttons, MessageBox.STYPE_INFO)

    def displayOkCancel(self, message='', vals=None, title=''):
        """Returns True if OK was pressed, False for Cancel."""
        buttons = MessageBox.BUTTONS_OK_CANCEL
        r = self.__showDialog(
                    message, vals, title, buttons, MessageBox.STYPE_WARN)
        if r == MessageBox.RESULT_OK:
            return True
        return False

    def displayYesNoCancel(self, message='', vals=None, title=''):
        """Returns a string: 'yes','no', or 'cancel'"""
        self.logger.debug("Displaying yes/no/cancel dialog.")
        buttons = MessageBox.BUTTONS_YES_NO_CANCEL
        r = self.__showDialog(
                    message, vals, title, buttons, MessageBox.STYPE_QUERY)
        if r == MessageBox.RESULT_YES:
            return "yes"
        elif r == MessageBox.RESULT_NO:
            return "no"
        return "cancel"

    def __showDialog(self, message, vals, title, buttons, stype):
        """Wrapper for com.sun.star.awt.XMessageBoxFactory.
        Private function.
        To include variables, specify them in vals (tuple,) and put %s %d etc
        in the message.
        """
        rect = uno.createUnoStruct('com.sun.star.awt.Rectangle')
        message = self.locale.getText(message)
        if vals is not None:
            try:
                message = message % vals    # for example "%d" % (50)
            except (TypeError, UnicodeDecodeError):
                self.logger.warn("message \"" + repr(message) +
                                 "\" failed to interpolate vals " + repr(vals))
        message = message + " "  # padding so that it displays better
        self.logger.warn(message)
        box = self.toolkit.createMessageBox(
              self.parent, rect, stype, buttons, title, message)
        return box.execute()

class FourButtonDialog(unohelper.Base, XActionListener):
    """
    toolkit.createMessageBox() only allows up to three buttons of certain
    types. Use this class for more flexibility with button number and names.
    """
    DefaultButtons = [['yes',      "Yes"],
                      ['no',       "No"],
                      ['yesToAll', "Yes to All"],
                      ['cancel',   "Cancel"]]

    def __init__(self, genericUnoObjs):
        self.unoObjs = genericUnoObjs
        self.locale  = Locale(self.unoObjs)
        self.logger  = logging.getLogger("lingt.UI.FourButtonDialog")

    def display(self, message='', vals=None, title='', buttons=None):
        self.result = None

        # create the dialog model and set the properties 
        # create the dialog control and set the model 
        dlgModel = self.unoObjs.smgr.createInstanceWithContext( 
                   "com.sun.star.awt.UnoControlDialogModel", self.unoObjs.ctx)
        dlgModel.PositionX = 100
        dlgModel.PositionY = 100
        dlgModel.Width     = 250 
        dlgModel.Height    = 70
        dlgModel.Title     = self.locale.getText(title)
        ctrlContainer = self.unoObjs.smgr.createInstanceWithContext( 
                        "com.sun.star.awt.UnoControlDialog", self.unoObjs.ctx)

        # create the label model and set the properties 
        message = self.locale.getText(message)
        if vals is not None:
            try:
                message = message % vals    # for example "%d" % (50)
            except (TypeError, UnicodeDecodeError):
                self.logger.warn("message \"" + repr(message) +
                                 "\" failed to interpolate vals " + repr(vals))
        message = message + " "  # padding so that it displays better
        lblModel = dlgModel.createInstance( 
                   "com.sun.star.awt.UnoControlFixedTextModel")
        lblModel.PositionX = 10 
        lblModel.PositionY = 10 
        lblModel.Width     = 150 
        lblModel.Height    = 14 
        lblModel.Name      = "lblMessage" 
        lblModel.TabIndex  = 0
        lblModel.Label     = message
        dlgModel.insertByName("lblMessage", lblModel); 

        # create the button models and set the properties 
        if not buttons:
            buttons = FourButtonDialog.DefaultButtons
        for btn_i, btn in enumerate(buttons):
            btnVal, btnText = btn
            btnName  = "btn_" + btnVal
            btnModel = dlgModel.createInstance( 
                       "com.sun.star.awt.UnoControlButtonModel")
            btnModel.PositionX  = 10 + (btn_i * 60)
            btnModel.PositionY  = 45 
            btnModel.Width      = 50 
            btnModel.Height     = 14
            btnModel.Name       = btnName
            btnModel.TabIndex   = btn_i + 1        
            btnModel.Label      = self.locale.getText(btnText)
            dlgModel.insertByName(btnName, btnModel)

        ctrlContainer.setModel(dlgModel)
        for btn_i, btn in enumerate(buttons):
            btnVal, btnText = btn
            btnName  = "btn_" + btnVal
            ctrl = ctrlContainer.getControl(btnName)
            ctrl.setActionCommand(btnVal)
            ctrl.addActionListener(self)
            self.logger.debug("Added button " + btnName)

        # create a peer and execute the dialog
        toolkit = self.unoObjs.smgr.createInstanceWithContext( 
            "com.sun.star.awt.ExtToolkit", self.unoObjs.ctx);       

        ctrlContainer.setVisible(False);       
        ctrlContainer.createPeer(toolkit, None);
        self.dlgClose = ctrlContainer.endExecute
        ctrlContainer.execute()

        # dispose the dialog 
        ctrlContainer.dispose()
        return self.result

    def actionPerformed(self, event):
        """Handle which button was pressed."""
        self.logger.debug(
            "Button pressed: " + safeStr(event.ActionCommand))
        self.result = event.ActionCommand
        self.dlgClose()
        self.logger.debug("Action finished.")

#-------------------------------------------------------------------------------
# Everything below this point is for testing only
#-------------------------------------------------------------------------------
def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.MessageBox")
    logger.debug("----ShowDlg()----------------------------------------------")
    genericUnoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = FourButtonDialog(genericUnoObjs)
    dlg.display("Testing")

# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of MessageBox.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of WordListStructs.py
#-------------------------------------------------------------------------------


class WordInList:
    """
    A word that can be used in word lists.
    It can be grouped to represent multiple occurences, or left single to
    represent a specific occurrence in a specific text.
    """
    def __init__(self):
        self.text         = ""     # the word
        self.source       = ""     # file name where it occurs, if not grouping
        self.sources      = dict() # file names where it occurs and number of
                                   # occurrences, if grouping
        self.occurrences  = 0      # number of occurences, if grouping
        self.isCorrect    = None   # Change to True or False for spelling.
                                   # Since this can have three values, compare
                                   # by: is True, is False, is None.
        self.correction   = ""     # corrected spelling
        self.similarWords = []     # candidates for corrected spelling
        self.converted1   = ""     # often used for romanizing the word
        self.converted2   = ""     # could be used for romanizing another field

    def similarWords_str(self):
        return "  ".join(self.similarWords)

    def setSimilarWords(self, delimitedString):
        self.similarWords = delimitedString.split()

    def isCorrect_str(self):
        if self.isCorrect is None:
            return ""
        elif self.isCorrect:
            return "OK"
        return "X"

    def setIsCorrect(self, strval):
        self.isCorrect = None
        if strval.lower() in ("ok", "yes", "+"):
            self.isCorrect = True
        elif strval.lower() in ("x", "no", "-"):
            self.isCorrect = False

    def sources_str(self):
        if len(self.sources) == 1:
            filepath = next(iter(self.sources.keys()))  # iter for python2.x
            return os.path.basename(filepath)
        elif len(self.sources) > 1:
            strlist = []
            for filepath,fileoccur in self.sources.items():
                strlist.append("%s(%s)" % (os.path.basename(filepath),
                                           fileoccur))
            return ", ".join(sorted(strlist))
        return ""

    def setSources(self, delimitedString):
        self.sources.clear()
        strlist = delimitedString.split(",")
        for strval in strlist:
            strval = strval.strip()  # remove whitespace
            matchObj = re.match(r'(.+)\((\d+)\)', strval)
            if matchObj:
                filepath  = matchObj.group(1)
                fileoccur = matchObj.group(2)
                self.sources[filepath] = fileoccur
            else:
                self.sources[strval] = self.occurrences

    @staticmethod
    def fromStringList(stringList):
        """Factory method to create a list of WordInList objects."""
        words = []
        for text in stringList:
            newWord = WordInList()
            newWord.text = text
            words.append(newWord)
        return words

    @staticmethod
    def toStringList(wordList):
        """Return a plain list of strings."""
        return [word.text for word in wordList]

class ColumnOrder:
    """Columns based on WordInList fields."""
    COL_WORD          = 1
    COL_OCCURRENCES   = 2
    COL_IS_CORRECT    = 3
    COL_CORRECTION    = 4
    COL_SOURCES       = 5
    COL_SIMILAR_WORDS = 6
    COL_CONVERTED1    = 7
    COL_CONVERTED2    = 8

    DEFAULT_ORDER = [
            COL_WORD,
            COL_CORRECTION,
            COL_SIMILAR_WORDS,
            COL_OCCURRENCES,
            COL_SOURCES,
            COL_CONVERTED1,
            COL_CONVERTED2,
            COL_IS_CORRECT]

    HEADINGS = {COL_WORD          : "Word",
                COL_OCCURRENCES   : "Occurrences",
                COL_IS_CORRECT    : "Correct?",
                COL_CORRECTION    : "Correction",
                COL_SOURCES       : "Sources",
                COL_SIMILAR_WORDS : "Similar Words",
                COL_CONVERTED1    : "Converted 1",
                COL_CONVERTED2    : "Converted 2"}

    def __init__(self, userVars):
        self.userVars = userVars
        self.sortOrder = ColumnOrder.DEFAULT_ORDER[:]
        self.resetRowData()

    def moveUp(self, elem_i):
        """
        Moves the specified element in self.sortOrder.
        Returns True if a change was made.
        """
        if elem_i == 0:
            return False
        return self.moveDown(elem_i - 1)

    def moveDown(self, elem_i):
        """
        Moves the specified element in self.sortOrder.
        Returns True if a change was made.
        """
        if elem_i == len(self.sortOrder) - 1:
            return False
        l = self.sortOrder  # shorthand variable name
        l[elem_i], l[elem_i + 1] = l[elem_i + 1], l[elem_i]   # swap
        return True

    def getTitles(self):
        return [ColumnOrder.HEADINGS[colID] for colID in self.sortOrder]

    def getTitle(self, elem_i):
        return ColumnOrder.HEADINGS[self.sortOrder[elem_i]]

    def getColLetter(self, colID):
        return chr(ord('A') + self.sortOrder.index(colID))
        
    def maxColLetter(self):
        return chr(ord('A') + len(ColumnOrder.DEFAULT_ORDER) - 1)

    def resetRowData(self):
        self.rowData = [""] * len(ColumnOrder.DEFAULT_ORDER)

    def setRowVal(self, colID, newVal):
        sortedIndex = self.sortOrder.index(colID)
        self.rowData[sortedIndex] = newVal

    def getRowTuple(self):
        """Returns a tuple."""
        return tuple(self.rowData)

    def setRowTuple(self, newTuple):
        """
        After calling this method, use getRowVal() to unpack.
        This is the reverse of resetRowData() and getRowTuple().
        """
        self.rowTuple = newTuple

    def getRowVal(self, colID):
        sortedIndex = self.sortOrder.index(colID)
        return self.rowTuple[sortedIndex]

    def getVarName(self, colID):
        return "column_" + ColumnOrder.HEADINGS[colID]

    def saveUserVars(self):
        colNum = 0
        for colID in self.sortOrder:
            self.userVars.set(self.getVarName(colID), chr(ord('A') + colNum))
            colNum += 1

    def loadFromUserVars(self):
        letters = []
        if self.userVars.isEmpty(self.getVarName(ColumnOrder.COL_WORD)):
            # just use the default list
            return
        for colID in ColumnOrder.DEFAULT_ORDER:
            letters.append(self.userVars.get(self.getVarName(colID)))
        zippedList = list(zip(letters, ColumnOrder.DEFAULT_ORDER))
        zippedList.sort()           # sort by letters
        unused, self.sortOrder = zip(*zippedList)
        self.sortOrder = list(self.sortOrder)

class DataField:
    """Description of field to grab information from."""
    NO_TYPE       = -1
    FIELD         = 0     # Toolbox or FieldWorks field, or XML field
    PARASTYLE     = 1
    CHARSTYLE     = 2
    FONTNAME      = 3
    SFM_MARKER    = 4
    COLUMN_LETTER = 5     # spreadsheets
    PART          = 6     # Writer documents

    names = {FIELD         : "Field",
             PARASTYLE     : "Paragraph Style",
             CHARSTYLE     : "Character Style",
             FONTNAME      : "Font",
             SFM_MARKER    : "SFM Marker",
             COLUMN_LETTER : "Column",
             PART          : "Part"}

    def __init__(self, locale=None):
        """If locale is given, it will be used to translate in toItemText()."""
        self.locale     = locale
        self.fieldType  = DataField.NO_TYPE
        self.fieldValue = ""
        self.fontType   = ""    # for fieldType FONTNAME

    def toItemText(self):
        if self.fieldType in self.names:
            if self.locale:
                name = self.locale.getText(self.names[self.fieldType])
                if (self.fieldType == DataField.FONTNAME and
                    self.fontType in ["Complex", "Asian"]
                   ):
                    name += " (%s)" % (self.locale.getText(self.fontType))
                val = self.fieldValue
                if self.fieldType == DataField.FIELD:
                    val = self.locale.getText(self.fieldValue)
                return name + ": " + val
            return self.names[self.fieldType] + " " + self.fieldValue
        return ""

    @staticmethod
    def getFromUserVars(prefix, userVars):
        """Factory method."""
        newField = DataField()
        newField.fieldType  = userVars.getInt(prefix + "type")
        newField.fieldValue = userVars.get(   prefix + "val")
        if newField.fieldType == DataField.FONTNAME:
            newField.fontType = userVars.get(prefix + "fontType")
        return newField

    def setUserVars(self, prefix, userVars):
        """Sets the user vars for this item."""
        userVars.set(prefix + "type", str(self.fieldType))
        userVars.set(prefix + "val",      self.fieldValue)
        if self.fieldType == DataField.FONTNAME:
            userVars.set(prefix + "fontType", self.fontType)

    def deepCopy(self):
        """A replacement for copy.deepcopy()."""
        newField = self.__class__()
        newField.fieldType  = self.fieldType
        newField.fieldValue = self.fieldValue
        newField.fontType   = self.fontType
        return newField

#-------------------------------------------------------------------------------
# End of WordListStructs.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of FileItemList.py
#-------------------------------------------------------------------------------



class LingExFileItem:
    """Stores information about a ling example file item in the list."""

    fileCountVar = "XML_fileCount"

    def __init__(self):
        self.filepath   = ""
        self.prefix     = ""

    @staticmethod
    def getItemFromUserVars(fileNumStr, userVars):
        """Factory method."""
        filepath = userVars.get("XML_filePath"   + fileNumStr)
        prefix   = userVars.get("XML_filePrefix" + fileNumStr)
        if filepath != "":
            newItem = LingExFileItem()
            newItem.filepath = filepath
            newItem.setPrefixNoSpaces(prefix)
            return newItem
        return None

    def setUserVars(self, fileNumStr, userVars):
        """Sets the user vars for this item."""
        userVars.set("XML_filePath"   + fileNumStr, self.filepath)
        userVars.set("XML_filePrefix" + fileNumStr, self.prefix)

    @staticmethod
    def cleanupUserVars(fileNumStr, userVars):
        """Returns True if something was cleaned up."""
        del1 = userVars.delete("XML_filePath"   + fileNumStr)
        del2 = userVars.delete("XML_filePrefix" + fileNumStr)
        return del1 and del2

    def setPrefixNoSpaces(self, newPrefix):
        self.prefix = ""
        if not newPrefix: return
        newPrefix = re.sub(r"\s", r"", newPrefix) # remove any spaces
        if newPrefix == "None": newPrefix = ""
        self.prefix = newPrefix

    def toItemText(self):
        itemtext = os.path.basename(self.filepath)
        if self.prefix != "" and self.prefix != "None":
            itemtext = self.prefix + "    " + itemtext
        return itemtext

class WordListFileItem:
    """Stores information about a file to read from to make a word list."""

    fileCountVar = "datafile_count"

    def __init__(self):
        self.filepath            = ""
        self.filetype            = ""
        self.writingSystem       = ""
        self.dataFields          = []    # List of DataField.
                                         # Fields to harvest words from.
        self.includeMisspellings = True
        self.skipFirstRow        = True  # first spreadsheet row has headings
        self.splitByWhitespace   = True  # split into words

    @staticmethod
    def getItemFromUserVars(fileNumStr, userVars):
        """Factory method."""
        prefix = "datafile" + fileNumStr + "_"
        filepath = userVars.get(prefix + "path")
        if filepath != "":
            newItem = WordListFileItem()
            newItem.filepath      = filepath
            newItem.filetype      = userVars.get(prefix + "type")
            newItem.writingSystem = userVars.get(prefix + "writingSys")
            fieldCount = userVars.getInt(prefix + "fieldCount")
            for fieldnum in range(0, fieldCount):
                fieldNumStr = "%02d" % (fieldnum)
                fieldprefix = prefix + "f" + fieldNumStr + "_"
                dataField = DataField().getFromUserVars(
                            fieldprefix, userVars)
                newItem.dataFields.append(dataField)
            newItem.includeMisspellings = (
                userVars.getInt(prefix + "includeMisspell") == 1)
            newItem.skipFirstRow = (
                userVars.getInt(prefix + "skipFirstRow") == 1)
            newItem.splitByWhitespace = (
                userVars.getInt(prefix + "splitPhrases") == 1)
            return newItem
        return None

    def setUserVars(self, fileNumStr, userVars):
        """Sets the user vars for this item."""
        prefix = "datafile" + fileNumStr + "_"
        userVars.set(prefix + "path",       self.filepath)
        userVars.set(prefix + "type",       self.filetype)
        userVars.set(prefix + "writingSys", self.writingSystem)
        userVars.set(prefix + "fieldCount", str(len(self.dataFields)))
        for fieldnum, dataField in enumerate(self.dataFields):
            fieldNumStr = "%02d" % (fieldnum)
            fieldprefix = prefix + "f" + fieldNumStr + "_"
            dataField.setUserVars(fieldprefix, userVars)
        userVars.set(prefix + "includeMisspell",
                     str(int(self.includeMisspellings)))
        userVars.set(prefix + "skipFirstRow",
                     str(int(self.skipFirstRow)))
        userVars.set(prefix + "splitPhrases",
                     str(int(self.splitByWhitespace)))

    @staticmethod
    def cleanupUserVars(fileNumStr, userVars):
        """Returns True if something was cleaned up."""
        prefix = "datafile" + fileNumStr + "_"
        del1 = userVars.delete(prefix + "path")
        userVars.delete(prefix + "type")
        userVars.delete(prefix + "fieldCount")
        for fieldnum in range(0, 100):   # 100 should be more than enough
            fieldNumStr = "%02d" % (fieldnum)
            fieldprefix = prefix + "f" + fieldNumStr + "_"
            del2 = userVars.delete(fieldprefix + "type")
            userVars.delete(fieldprefix + "val")
            if not del2:
                break
        userVars.delete(prefix + "includeMisspell")
        userVars.delete(prefix + "skipFirstRow")
        userVars.delete(prefix + "splitPhrases")
        return del1

    def deepCopy(self):
        """A replacement for copy.deepcopy()."""
        newItem = self.__class__()
        newItem.filepath      = self.filepath
        newItem.filetype      = self.filetype
        newItem.writingSystem = self.writingSystem
        for dataField in self.dataFields:
            newItem.dataFields.append(dataField.deepCopy())
        newItem.includeMisspellings = self.includeMisspellings
        newItem.skipFirstRow        = self.skipFirstRow
        newItem.splitByWhitespace   = self.splitByWhitespace
        return newItem

    def toItemText(self):
        itemtext = os.path.basename(self.filepath)
        return itemtext

class FileItemList:
    """Maintains a list of file items."""

    def __init__(self, fileItemClass, unoObjs, userVars):
        self.fileItemClass  = fileItemClass
        self.unoObjs        = unoObjs
        self.userVars       = userVars
        self.logger         = logging.getLogger("lingt.App.FileItemList")
        self.msgbox         = MessageBox(unoObjs)
        self.fileItems      = []    # list of FileItem objects

    def getItem(self, list_i):
        return self.fileItems[list_i]

    def getList(self):
        """Return a copy of the list."""
        return self.fileItems[:]

    def __getitem__(self, index):
         return self.fileItems[index]

    def getItemTextList(self):
        """Returns a list of strings for display in a control."""
        self.logger.debug("getItemTextList")
        strList = []
        for fileItem in self.fileItems:
            strList.append(fileItem.toItemText())
        return strList

    def getCount(self):
        return len(self.fileItems)

    def loadFromUserVars(self):
        """Loads from user vars into self.fileItems."""
        self.logger.debug("Loading list from user vars.")
        self.fileItems = []
        num_files = self.userVars.getInt(self.fileItemClass.fileCountVar)
        for filenum in range(0, num_files):
            fileNumStr = "%02d" % (filenum)
            newItem = self.fileItemClass.getItemFromUserVars (
                      fileNumStr, self.userVars)
            if newItem:
                self.fileItems.append(newItem)
        self.sort()

    def setUserVars(self):
        self.logger.debug("Setting user vars.")
        self.userVars.set(self.fileItemClass.fileCountVar, str(self.getCount()))
        self.logger.debug("_")
        for filenum, fileItem in enumerate(self.fileItems):
            fileNumStr = "%02d" % (filenum)
            self.logger.debug("_")
            fileItem.setUserVars(fileNumStr, self.userVars)

        ## Delete unused variables

        filenum = len(self.fileItems)
        while True:
            fileNumStr = "%02d" % (filenum)
            somethingFound = self.fileItemClass.cleanupUserVars(
                             fileNumStr, self.userVars)
            if not somethingFound:
                break
            filenum += 1

    def sort(self):
        """Sort by filename."""
        self.logger.debug("Sorting list.")
        try:
            self.fileItems.sort(key=fileItemSortKey)
            self.logger.debug("Finished sorting list.")
        except AttributeError:
            self.logger.warn("Couldn't sort list.")

    def alreadyContains(self, newItem, excludeItemPos=-1):
        """Make the list unique."""
        for i in range(0, len(self.fileItems)):
            if excludeItemPos > -1:
                if i == excludeItemPos:
                    continue
            if self.fileItems[i].filepath.lower() == newItem.filepath.lower():
                return True
        return False

    def updateItem(self, itemPos, newItem):
        """Returns True on success."""
        if self.alreadyContains(newItem, excludeItemPos=itemPos):
            self.msgbox.display("File is already in the list.")
            return False
        self.logger.debug("Updating item.")
        self.fileItems[itemPos] = newItem
        self.sort()
        self.changed = True
        return True

    def addItem(self, newFileItem):
        """Returns True on success."""
        if self.alreadyContains(newFileItem):
            self.msgbox.display("File is already in the list.")
            return False
        self.logger.debug("Adding item.")
        self.fileItems.append(newFileItem)
        self.sort()
        self.changed = True
        return True

    def deleteItem(self, itemPos):
        self.logger.debug("Deleting item.")
        del self.fileItems[itemPos]
        self.changed = True

def fileItemSortKey(fileItem):
    """Function for sorting File Item objects."""
    return os.path.basename(fileItem.filepath.lower())

#-------------------------------------------------------------------------------
# End of FileItemList.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Styles.py
#-------------------------------------------------------------------------------



class FontDefStruct:
    def __init__(self, fontName, fontType, size):
        self.fontName = fontName
        self.fontType = fontType
        self.size     = size

class Styles:
    """Parent class for managing styles."""
    styleVars    = []
    defaultNames = {}
    INCH_TO_CM = 2540  # convert 1/1000 cm to inches

    def __init__(self, unoObjs, userVars):
        self.unoObjs     = unoObjs
        self.userVars    = userVars
        self.logger      = logging.getLogger("lingt.Access.Styles")
        self.msgbox      = MessageBox(unoObjs)
        self.locale      = Locale(unoObjs)
        self.families    = unoObjs.document.getStyleFamilies()
        self.charStyles  = None
        self.paraStyles  = None
        self.frameStyles = None

        self.fontOrth  = FontDefStruct("Latha",           "Complex", 14)
        self.fontVern  = FontDefStruct("Doulos SIL",      "Western", 14)
        self.fontGloss = FontDefStruct("Times New Roman", "Western", 12)
        self.fontFixed = FontDefStruct("Courier New",     "Western", 12)

        self.__determineNames()
        self.logger.debug("Styles init() finished")

    def __determineNames(self):
        """Sets self.styleNames based on user vars and defaults."""
        self.styleNames = {}
        for key, var in self.styleVars:
            name = self.userVars.get(var)
            if name == "":
                name = self.defaultNames[key]
                self.userVars.set(var, name)
            self.styleNames[key] = name

    def getStyleNames(self):
        return self.styleNames

    def requireCharStyle(self, styleKey):
        """Raises an exception if style does not exist."""
        if not self.hasCharStyle(styleKey):
            raise StyleError("Character style '%s' is missing",
                                        (self.styleNames[styleKey],))

    def hasCharStyle(self, styleKey):
        """Returns True if the style exists.  Sets self.charStyles."""
        if self.charStyles is None:
            self.charStyles = self.families.getByName("CharacterStyles")
        styleName = self.styleNames[styleKey]
        return self.charStyles.hasByName(styleName)

    def createCharStyle(self, styleKey, fontDef=None, color=None):
        """Returns true if a new style is created."""
        styleName = self.styleNames[styleKey]
        if not self.hasCharStyle(styleKey):
            self.logger.debug("Creating style " + styleName)
            self.newStyle = self.unoObjs.document.createInstance(
                            "com.sun.star.style.CharacterStyle")
            self.charStyles.insertByName(styleName, self.newStyle)
            if fontDef:
                propSuffix = fontDef.fontType
                if propSuffix == 'Western':
                    propSuffix = ""
                if fontDef.fontName:
                    self.newStyle.setPropertyValue(
                        'CharFontName' + propSuffix, fontDef.fontName)
                    if fontDef.size is not None and fontDef.size > 0:
                        self.newStyle.setPropertyValue(
                            'CharHeight' + propSuffix, fontDef.size)
            if color is not None:
                self.newStyle.CharColor = color
            return True
        return False

    def requireParaStyle(self, styleKey):
        """Raises an exception if style does not exist."""
        if not self.hasParaStyle(styleKey):
            raise StyleError("Paragraph style '%s' is missing",
                                        (self.styleNames[styleKey],))

    def hasParaStyle(self, styleKey):
        """Returns True if the style exists.  Sets self.paraStyles."""
        if self.paraStyles is None:
            self.paraStyles = self.families.getByName("ParagraphStyles")
        styleName = self.styleNames[styleKey]
        return self.paraStyles.hasByName(styleName)

    def createParaStyle(self, styleKey, fontDef=None, color=None):
        """Returns true if a new style is created."""
        styleName = self.styleNames[styleKey]
        if not self.hasParaStyle(styleKey):
            self.logger.debug("Creating style " + styleName)
            self.newStyle = self.unoObjs.document.createInstance(
                            "com.sun.star.style.ParagraphStyle")
            self.paraStyles.insertByName(styleName, self.newStyle)
            if fontDef:
                propSuffix = fontDef.fontType
                if propSuffix == "Western":
                    propSuffix = ""
                if fontDef.fontName:
                    self.newStyle.setPropertyValue(
                        'CharFontName' + propSuffix, fontDef.fontName)
                    if fontDef.size is not None and fontDef.size > 0:
                        self.newStyle.setPropertyValue(
                            'CharHeight' + propSuffix, fontDef.size)
            if color is not None:
                self.newStyle.CharColor = color
            return True
        return False

    def requireFrameStyle(self, styleKey):
        """Raises an exception if style does not exist."""
        if not self.hasFrameStyle(styleKey):
            raise StyleError("Frame style '%s' is missing",
                                        (self.styleNames[styleKey],))

    def hasFrameStyle(self, styleKey):
        """Returns True if the style exists.  Sets self.frameStyles."""
        if self.frameStyles is None:
            self.frameStyles = self.families.getByName("FrameStyles")
        styleName = self.styleNames[styleKey]
        return self.frameStyles.hasByName(styleName)

    def createFrameStyle(self, styleKey, rightMargin, bottomMargin):
        """Returns true if a new style is created."""
        styleName = self.styleNames[styleKey]
        if not self.hasFrameStyle(styleKey):
            self.logger.debug("Creating style " + styleName)
            self.newStyle = self.unoObjs.document.createInstance(
                            "com.sun.star.style.FrameStyle")
            self.frameStyles.insertByName(styleName, self.newStyle)
            self.newStyle.AnchorType = uno.getConstantByName(
                "com.sun.star.text.TextContentAnchorType.AS_CHARACTER" ) 
            self.newStyle.VertOrient = uno.getConstantByName(
                "com.sun.star.text.VertOrientation.LINE_TOP" ) 
            self.newStyle.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")
            self.newStyle.LeftMargin     = 0
            self.newStyle.TopMargin      = 0
            self.newStyle.RightMargin    = rightMargin  * self.INCH_TO_CM
            self.newStyle.BottomMargin   = bottomMargin * self.INCH_TO_CM
            self.newStyle.BorderDistance = 0
            BORDER_WIDTH = 0
            borderLine = self.newStyle.getPropertyValue("LeftBorder")
            borderLine.OuterLineWidth = BORDER_WIDTH
            self.newStyle.setPropertyValue("LeftBorder",   borderLine)
            self.newStyle.setPropertyValue("RightBorder",  borderLine)
            self.newStyle.setPropertyValue("TopBorder",    borderLine)
            self.newStyle.setPropertyValue("BottomBorder", borderLine)
            return True
        return False

class PhonologyStyles(Styles):
    styleVars  = [['phonemic', "StyleName_Phonemic"],
                  ['phonetic', "StyleName_Phonetic"],
                  ['gloss'   , "StyleName_Gloss"],
                  ['ref'     , "StyleName_RefNum"],
                  ['exPara'  , "StyleName_ExamplePara"]]

    defaultNames = {'phonemic' : "Lex Phonemic",
                    'phonetic' : "Lex Phonetic",
                    'gloss'    : "Lex Gloss",
                    'ref'      : "Lex Reference Number",
                    'exPara'   : "Lex Example"}

    def createStyles(self):
        """Create styles if they don't already exist."""

        ## Create character styles

        self.logger.debug("Creating character styles")
        styleDefs = [
            ('phonemic', self.fontVern,  int("008000", 16)), # green
            ('phonetic', self.fontVern,  int("0000FF", 16)), # blue
            ('gloss',    self.fontGloss, int("000000", 16)), # black
            ('ref',      self.fontFixed, int("FF0000", 16))] # light red
        for styleKey, font, color in styleDefs:
            self.createCharStyle(styleKey, font, color)

        ## The paragraph style

        createdNew = self.createParaStyle("exPara")
        if createdNew:
            self.newStyle.setParentStyle("Standard")

            ## set tabs on paragraph style
            stops = []
            position = 0
            for width in [self.INCH_TO_CM * 1/2,
                          self.INCH_TO_CM * 1.5,
                          self.INCH_TO_CM * 1.5,
                          self.INCH_TO_CM * 1.5,
                          self.INCH_TO_CM * 1.5]:
                position += width
                tabStop = uno.createUnoStruct('com.sun.star.style.TabStop')
                tabStop.Position    = position    # 1/1000cm: 2540 = 1 inch
                tabStop.Alignment   = uno.getConstantByName(
                                      "com.sun.star.style.TabAlign.LEFT") 
                tabStop.DecimalChar = "."
                tabStop.FillChar    = " "
                stops.append(tabStop)
            self.newStyle.ParaTabStops = tuple(stops)

class GrammarStyles(Styles):
    """Make changes to styles and the document itself."""
    styleVars  = [['orth',  "StyleName_Orthographic"],
                  ['text',  "StyleName_Text"],
                  ['morph', "StyleName_Morpheme"],
                  ['orthm', "StyleName_OrthographicMorph"],
                  ['pos',   "StyleName_POS"],
                  ['gloss', "StyleName_Gloss"],
                  ['ft',    "StyleName_FreeTxln"],
                  ['ref',   "StyleName_RefNum"],
                  ['numP',  "StyleName_NumPara"],
                  ['intF',  "StyleName_InterlinearFrame"],
                  ['morF',  "StyleName_MorphemeFrame"]]

    defaultNames = {'orth'  : "Interlin Orthographic",
                    'text'  : "Interlin Base",
                    'morph' : "Interlin Morph",
                    'orthm' : "Interlin Orthographic Morph",
                    'pos'   : "Interlin POS",
                    'gloss' : "Interlin Gloss",
                    'ft'    : "Interlin Freeform Gloss",
                    'ref'   : "Interlin Reference Number",
                    'numP'  : "Interlin Example Number",
                    'intF'  : "Interlin Frame",
                    'morF'  : "Interlin Morpheme Frame"}

    def __init__(self, unoObjs, userVars):
        Styles.__init__(self, unoObjs, userVars)

    def createStyles(self):
        """Create styles if they don't already exist."""
        self.logger.debug("createStyles BEGIN")

        ## Paragraph styles

        self.logger.debug("Modifying styles of interlinear lines")
        styleDefs = [
            ('orth',  self.fontOrth,  int("000000", 16)), # black
            ('text',  self.fontVern,  int("0000FF", 16)), # blue
            ('orthm', self.fontOrth,  int("000000", 16)), # black
            ('morph', self.fontVern,  int("800080", 16)), # magenta
            ('pos',   self.fontGloss, int("FF0000", 16)), # light red
            ('gloss', self.fontGloss, int("FF00FF", 16)), # light magenta
            ('ft',    self.fontGloss, int("008000", 16))] # green
        for styleKey, font, color in styleDefs:
            self.createParaStyle(styleKey, font, color)

        ## A character style

        styleDefs = [('ref', self.fontFixed, int("800000", 16))] # red
        for styleKey, font, color in styleDefs:
            self.createCharStyle(styleKey, font, color)

        ## Styles for spacing

        styleDefs = [('numP',  0.07, 0.0)]
        for styleDef in styleDefs:
            styleKey, topMargin, bottomMargin = styleDef
            createdNew = self.createParaStyle(styleKey)
            if createdNew:
                self.newStyle.ParaTopMargin    = topMargin    * self.INCH_TO_CM
                self.newStyle.ParaBottomMargin = bottomMargin * self.INCH_TO_CM

        ## Styles for frames

        self.logger.debug("Modifying styles of frames")
        styleDefs = [('intF', 0.1, 0.1),
                     ('morF', 0.1, 0.0)]
        for styleDef in styleDefs:
            styleKey, rightMargin, bottomMargin = styleDef
            self.createFrameStyle(styleKey, rightMargin, bottomMargin)

        self.logger.debug("createStyles END")

    def resizeNumberingCol(self, colWidthText, prevColWidth):
        """Resize the width of the column that contains example numbering.
        Size is an integer percentage of the page width.
        @param string colWidthText
        @param int    prevColWidth
        throws ChoiceProblem

        It would be nice if there were such a thing as table styles.
        Then this function would presumably not be needed.
        """
        self.logger.debug("resizeNumberingCol BEGIN")
        if colWidthText == "":
            raise ChoiceProblem(
                "Please enter a value for column width.")
        try:
            newVal = int(colWidthText)
        except:
            raise ChoiceProblem("Column width is not a number.")
        if newVal == prevColWidth:
            self.logger.debug("No need to change.")
            return
        if newVal > 50:     # more than 50% is unreasonable
            raise ChoiceProblem(
                "Value %d for column width is too high.", (newVal,))
        elif newVal <= 0:
            raise ChoiceProblem(
                "Value for column width must be more than zero.")

        PERCENT_TO_SEP  = 100  # Separator width 10,000 is 100%.
                               # The user enters a number like 5 meaning 5%.
                               # So 5 * 100 would be 500 which is 5% of 10,000
        MARGIN_OF_ERROR = 2
        prevVal = prevColWidth * PERCENT_TO_SEP
        newVal  = newVal       * PERCENT_TO_SEP
        tables = self.unoObjs.document.getTextTables()
        self.logger.debug("looping through " + str(tables.getCount()) +
                          " tables. prevVal = %d" % (prevVal))
        for t in range(0, tables.getCount()):
            table = tables.getByIndex(t)
            separators = table.getPropertyValue("TableColumnSeparators")
            if separators is None:
                self.logger.debug("No separators set for table " +
                                  table.getName())
                continue
            self.logger.debug("table " + table.getName() + " separator is " +
                      str(separators[0].Position))
            if separators[0].Position  > prevVal - MARGIN_OF_ERROR and \
                separators[0].Position < prevVal + MARGIN_OF_ERROR:

                separators[0].Position = newVal
                table.TableColumnSeparators = separators
                self.logger.debug("changed to " + str(separators[0].Position))

        self.userVars.set("NumberingColWidth", str(newVal // PERCENT_TO_SEP))
        self.logger.debug("resizeNumberingCol END")

class AbbrevStyles(Styles):
    styleVars    = [['abbr', "StyleName_Abbrev"]]
    defaultNames = {'abbr' : "Abbreviation Item"}

    def createStyles(self):
        self.logger.debug("createStyles BEGIN")
        self.createParaStyle('abbr', self.fontGloss)
        self.logger.debug("createStyles END")

class StyleFonts(Styles):
    """Manages the font of a style.  Used in Data Conversion."""

    def __init__(self, unoObjs, userVars):
        Styles.__init__(self, unoObjs, userVars)
        self.paraStyles = self.families.getByName("ParagraphStyles")
        self.charStyles = self.families.getByName("CharacterStyles")

    def getFontOfStyle(self, styleName, styleFamily, fontType):
        """
        Returns font name and size of the specified type.
        """
        styles = self.paraStyles
        if styleFamily == "Character":
            styles = self.charStyles
        if styles.hasByName(styleName):
            style = styles.getByName(styleName)
            propSuffix = fontType
            if propSuffix == "Western":
                propSuffix = ""
            fontName = style.getPropertyValue('CharFontName' + propSuffix)
            fontSize = style.getPropertyValue('CharHeight'   + propSuffix)
            return fontName, fontSize
        return None, 0

    def setParaStyleWithFont(self, styleName, fontDef):
        if self.paraStyles.hasByName(styleName):
            style = self.paraStyles.getByName(styleName)
            propSuffix = fontDef.fontType
            if propSuffix == "Western":
                propSuffix = ""
            if fontDef.fontName:
                style.setPropertyValue(
                    'CharFontName' + propSuffix, fontDef.fontName)
                if fontDef.size > 0:
                    style.setPropertyValue(
                        'CharHeight' + propSuffix, fontDef.size)
        else:
            self.styleNames[styleName] = styleName  # for createParaStyle()
            self.createParaStyle(styleName, fontDef)

    def setCharStyleWithFont(self, styleName, fontDef):
        if self.charStyles.hasByName(styleName):
            style = self.charStyles.getByName(styleName)
            propSuffix = fontDef.fontType
            if propSuffix == "Western":
                propSuffix = ""
            if fontDef.fontName:
                style.setPropertyValue(
                    'CharFontName' + propSuffix, fontDef.fontName)
                if fontDef.size > 0:
                    style.setPropertyValue(
                        'CharHeight' + propSuffix, fontDef.size)
        else:
            self.styleNames[styleName] = styleName  # for createCharStyle()
            self.createCharStyle(styleName, fontDef)

def getListOfStyles(familyName, unoObjs):
    """
    Returns a list of tuples (underlying name, display name)
    The display name may be localized or changed for readability.
    """
    logger = logging.getLogger("Styles")
    logger.debug("getListOfSTyles")
    families     = unoObjs.document.getStyleFamilies()
    styles       = families.getByName(familyName)
    styleNames      = []
    for i in range(0, styles.getCount()):
        style = styles.getByIndex(i)
        styleNames.append( (style.getPropertyValue("DisplayName"),
                            style.getName()) )
    styleNames.sort(key=lambda tupl: tupl[0])   # sort by display name
    logger.debug("styleNames has " + str(len(styleNames)) + " elements")
    return styleNames

def getListOfFonts(unoObjs, addBlank=False):
    logger = logging.getLogger("Styles")
    logger.debug("getListOfFonts")
    toolkit         = unoObjs.smgr.createInstanceWithContext(
                      "com.sun.star.awt.Toolkit", unoObjs.ctx)
    device          = toolkit.createScreenCompatibleDevice(0, 0)
    fontDescriptors = device.getFontDescriptors()
    fontList        = []
    for fontDescriptor in fontDescriptors:
        fontList.append(fontDescriptor.Name)
    fontList = list(set(fontList))  # get unique list
    if addBlank:
        fontList.insert(0, "(None)")
    fontList.sort()
    logger.debug("fontList has " + str(len(fontList)) + " elements")
    return tuple(fontList)

#-------------------------------------------------------------------------------
# End of Styles.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of TestingUtils.py
#-------------------------------------------------------------------------------



# required when "exec(code)"

ctx = None  # store for all tests

def getContext():
    global ctx
    if ctx is None:
        ctx = UnoObjs.getCtxFromSocket()
    return ctx

def setContext(newCtx):
    global ctx
    ctx = newCtx

currentComponent = None  # store for all tests

def getCurrentDoc():
    global currentComponent
    return currentComponent

def blankWriterDoc(unoObjs):
    """
    Closes all current documents and opens a new writer doc.
    Sets unoObjs to the new blank document.
    Be sure to update any objects that reference the old unoObjs.
    """
    doclist = unoObjs.getOpenDocs()
    for docUnoObjs in doclist:
        docUnoObjs.document.close(True)
    newDoc = unoObjs.desktop.loadComponentFromURL(
             "private:factory/swriter", "_blank", 0, ())
    unoObjs.loadDocObjs(newDoc)
    global currentComponent
    currentComponent = unoObjs.document

def unoObjsForCurrentDoc():
    # Load uno objs based on stored currentComponent
    unoObjs = UnoObjs(getContext(), loadDocObjs=False)
    unoObjs.loadDocObjs(getCurrentDoc())
    return unoObjs

PARAGRAPH_BREAK = uno.getConstantByName(
    "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK")

## Set up a logger that will ignore most messages

#topLogger = logging.getLogger("lingt")
#topLogger.setLevel(logging.ERROR)
#loggingSh = logging.StreamHandler()
#topLogger.addHandler(loggingSh)

class MyActionEvent:
    """Objects to pass to actionPerformed()."""
    def __init__(self, actionCommand):
        self.ActionCommand = actionCommand

# Don't inspect the same function twice, because the second time the
# source code is just a string rather than stored in a file.
# Inspect.findsource() requires a file, so it will fail the second time.
modifiedFunctions = set()

def modifyClass_showDlg(klass):
    """
    Modify showDlg() to call useDialog() instead of execute().
    As a result, the dialog does not wait for user interaction.
    """
    fnStr = "%s.showDlg" % (klass)
    #print fnStr
    global modifiedFunctions
    if fnStr in modifiedFunctions:
        return
    modifiedFunctions.add(fnStr)

    code = inspect.getsource(klass.showDlg)
    code = re.sub("showDlg", "showDlgModified", code)
    code = re.sub("dlg.execute\(\)", "self.useDialog()", code)
    code = re.sub("dlg.dispose\(\)", "self.dlgDispose = dlg.dispose", code)
    pat = re.compile("^    ", re.M)
    code = re.sub(pat, "", code)    # decrease indent
    #print(code)  # for debugging
    exec(code, globals())
    klass.showDlg = showDlgModified

def modifyMsgboxDisplay():
    """
    Modify display() to throw MsgSentException instead of
    actually displaying a message.
    """
    def newDisplay(self, message='', vals=None, title=''):
        raise MsgSentException(message, vals)
    MessageBox.display = newDisplay

def modifyMsgboxOkCancel(retval):
    """
    Modify displayOkCancel() to return the specified value
    instead of actually displaying a message.
    """
    def newOkCancel(self, message='', vals=None, title=''):
        return retval
    MessageBox.displayOkCancel = newOkCancel

def modifyMsgboxYesNoCancel(retval):
    """
    Modify displayYesNoCancel() to return the specified
    value instead of actually displaying a message.
    """
    def newYesNoCancel(self, message='', vals=None, title=''):
        return retval
    MessageBox.displayYesNoCancel = newYesNoCancel

def modifyFilePicker(retval):
    """
    Modify showFilePicker() to return the specified
    value instead of actually displaying a message.
    """
    def newFilePicker(unoObjs, save=False, filters=[], defaultFilename=None):
        return retval
    global showFilePicker   # needed for assimilated code
    showFilePicker = newFilePicker

class MsgSentException(MessageError):
    """Capture the message instead of displaying it to the user."""
    pass

#-------------------------------------------------------------------------------
# End of TestingUtils.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of ProgressBar.py
#-------------------------------------------------------------------------------



class ProgressBar:
    MAXVAL = 100
    def __init__(self, genericUnoObjs, title):
        self.unoObjs    = genericUnoObjs
        self.logger     = logging.getLogger("lingt.UI.ProgressBar")
        locale          = Locale(self.unoObjs)
        self.titleText  = locale.getText(title)
        self.progress   = None
        self.val        = 0   # needed because self.progress.Value is write-only

    def show(self):
        self.logger.debug("ProgressBar.show() BEGIN")
        self.progress = self.unoObjs.controller.StatusIndicator
        self.progress.start(self.titleText, self.MAXVAL)
        self.logger.debug("ProgressBar show() Finished")

    def updateBeginning(self):
        """Sets to 10% and waits a short time so the user can see it."""
        self.val = 10
        self.progress.setValue(self.val)
        self.pause()

    def updateFinishing(self):
        """Sets to 100%."""
        self.val = self.MAXVAL
        self.progress.setValue(self.val)
        self.pause()

    def pause(self):
        """Wait a short time so the user can see the bar."""
        time.sleep(0.1)

    def updatePercent(self, percent):
        """Set the percentage finished. Maximum value is 100."""
        self.logger.debug("ProgressBar updatePercent " + str(percent))
        self.val = percent
        self.progress.setValue(self.val)

    def percentMore(self, percent):
        """Increases progress bar by the amount specified."""
        self.logger.debug("ProgressBar percentMore")
        self.val += percent
        self.progress.setValue(self.val)

    def getPercent(self):
        return self.val

    def close(self):
        """
        This method will throw an exception if show() has not been called.
        """
        self.logger.debug("ProgressBar close")
        self.progress.end()

#-------------------------------------------------------------------------------
# End of ProgressBar.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SEC_wrapper.py
#-------------------------------------------------------------------------------


class SEC_wrapper:
    def __init__(self, msgbox):
        self.msgbox = msgbox
        self.logger = logging.getLogger("lingt.Access.SEC_wrapper")

        self.funcIsEcInstalled   = None
        self.funcSelectConverter = None
        self.funcInitConverter   = None
        self.funcConvertString   = None
        self.funcDescription     = None
        self.funcCleanup         = None

        self.loaded        = False
        self.converterName = None
        self.directionFw   = None
        self.normForm      = None

    def __del__(self):
        if self.loaded and self.funcCleanup is not None:
            self.funcCleanup()

    def loadLibrary(self):
        if self.loaded:
            return
        if platform.system() == "Windows" :
            libfile = "ECDriver"
            wide    = 'W'  # use functions named with 'W' for wide characters
        else :
            libfile = "libecdriver.so.1"
            wide    = ''
        self.logger.debug("Loading " + libfile)
        try:
            libecdriver = ctypes.cdll.LoadLibrary(libfile)
        except OSError as exc:
            self.msgbox.display ("Library error: %s." % (exc.message))
            return

        self.logger.debug("Getting functions from library")
        try:
            self.funcIsEcInstalled = libecdriver.IsEcInstalled
            self.funcSelectConverter = getattr (
                libecdriver, 'EncConverterSelectConverter' + wide)
            self.funcInitConverter = getattr (
                libecdriver, 'EncConverterInitializeConverter' + wide)
            self.funcConvertString = getattr (
                libecdriver, 'EncConverterConvertString' + wide)
            self.funcDescription = getattr (
                libecdriver, 'EncConverterConverterDescription' + wide)
            if platform.system() == "Linux" :
                self.funcCleanup = libecdriver.Cleanup
        except AttributeError as exc:
            self.msgbox.display ("Library error: %s." % (exc))
            return
        self.logger.debug("Library successfully loaded.")
        self.loaded = True

    def PickConverter(self):
        self.logger.debug("PickConverter BEGIN")
        self.loadLibrary()
        if not self.loaded: return
        if not self.funcIsEcInstalled():
            self.msgbox.display (
                "EncConverters does not seem to be installed properly.")
            return False

        bufConverterName = self.createBuffer(1024)
        c_directionFw    = ctypes.c_bool(False)
        c_normForm       = ctypes.c_ushort(0)
        self.logger.debug("calling funcSelectConverter")
        status = self.funcSelectConverter (
                    bufConverterName,
                    ctypes.byref(c_directionFw),
                    ctypes.byref(c_normForm))
        if (status != 0):
            self.logger.debug (
                "EncConverters returned %d. User probably pressed Cancel." %
                (status))
            return False

        self.logger.debug("Converter name was " + bufConverterName.value)
        self.converterName = bufConverterName.value
        self.directionFw   = c_directionFw.value
        self.normForm      = c_normForm.value
        self.logger.debug("PickConverter END")
        return True

    def SetConverter(self, convName, directionFw, normForm):
        self.logger.debug("SetConverter BEGIN")
        self.loadLibrary()
        if not self.loaded: return
        if not self.funcIsEcInstalled():
            self.msgbox.display (
                "EncConverters does not seem to be installed properly.")
            return False

        c_convName = self.getStringParam(convName)
        if c_convName is None: return False
        c_directionFw = ctypes.c_bool(directionFw)
        c_normForm    = ctypes.c_ushort(normForm)
        self.logger.debug("calling funcInitConverter")
        status = self.funcInitConverter (
                 c_convName, c_directionFw, c_normForm)
        if (status != 0):
            description = ''
            if status == -7:
                description = " (Converter Name Not Found)"
            elif status == -18:
                description = " (Registry Corrupt)"
            self.msgbox.display (
                "Error: EncConverters returned %d%s." % (status, description))
            return False

        self.converterName = convName
        self.directionFw   = directionFw
        self.normForm      = normForm
        self.logger.debug("SetConverter END")
        return True

    def Convert(self, sInput):
        """
        First return value is status, True if successful.
        Second value is converted string.
        """
        self.logger.debug("convert BEGIN")
        if not self.converterName:
            self.msgbox.display ("No converter was specified.")
            return False, ""
        self.logger.debug("Using converter " + self.converterName)
        c_convName = self.getStringParam(self.converterName)
        if c_convName is None: return False, ""
        self.logger.debug(repr(sInput))
        c_input    = self.getStringParam(sInput)
        if c_input is None: return False, ""
        c_outSize  = ctypes.c_int(10000)   # ECDriver will truncate the result
                                           # if we go over this amount.
        bufOutput  = self.createBuffer(c_outSize.value)
        self.logger.debug ("Calling ConvertString.")
        status = self.funcConvertString (
                 c_convName, c_input, bufOutput, c_outSize);
        if status != 0:
            description = ''
            if status == -7:
                description = " (Converter Name Not Found)"
            elif status == -18:
                description = " (Registry Corrupt)"
            self.msgbox.display (
                "Error: EncConverters returned %d%s." % (status, description))
            return False, ""
        self.logger.debug("convert END")
        return True, bufOutput.value

    def createBuffer(self, size):
        """
        Get a writable buffer that can be used to return a string from C++ code.
        """
        if platform.system() == "Windows" :
            # Type wchar_t *
            return ctypes.create_unicode_buffer(size)
        else:
            # Ordinary strings in Linux are UTF-8, so type char * works.
            return ctypes.create_string_buffer(size)

    def getStringParam(self, strval):
        """
        Prepare the string to pass as a parameter to C++ code.
        Returns None if an error occurs.

        On Windows, with the converter name, either using c_char_p or else
        encoding results in ECDriver returning -7 Name Not Found error.
        """
        try:
            if platform.system() == "Windows":
                encName  = 'utf-16-le'
                char_ptr = ctypes.c_wchar_p    # constructor for wchar_t *
                byteStr = strval
            else:
                encName  = 'utf-8'
                char_ptr = ctypes.c_char_p     # constructor for char *
                byteStr  = strval.encode(encName)
            #if isinstance(strval, unicode) and encName == 'utf-8':
            #    self.logger.debug("input contains unicode chars")
            #    byteStr = strval.encode(encName)
            #else:
            #    self.logger.debug (
            #        "input does not contain unicode chars; may be legacy")
            #    byteStr = strval
            return char_ptr(byteStr)
        except UnicodeEncodeError:
            self.msgbox.display("Failed to encode string properly.")
            return None

#-------------------------------------------------------------------------------
# End of SEC_wrapper.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SpreadsheetOutput.py
#-------------------------------------------------------------------------------



class SpreadsheetOutput:
    """
    Sends output to the Calc spreadsheet.
    Returns True if successful.
    """
    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        self.logger  = logging.getLogger("lingt.Access.SpreadsheetOutput")

    def outputToColumn(self, colLetter, stringList, skipFirstRow=True):
        """Takes a list of strings."""
        self.logger.debug("outputToColumn BEGIN")

        chunkSize = 25  # make this value bigger or smaller for optimization
        for i1 in range(0, len(stringList), chunkSize):
            i2 = i1 + chunkSize - 1
            if i2 >= len(stringList):
                i2 = len(stringList) - 1

            data = []
            for i in range(i1, i2 + 1):
                data.append((stringList[i],))
            if skipFirstRow:
                offset = 2  # start at second row
            else:
                offset = 1
            row1 = str(i1 + offset)
            row2 = str(i2 + offset)
            rangeName = colLetter + row1 + ":" + colLetter + row2
            self.logger.debug(rangeName)
            self.logger.debug(repr(data))
            try:
                oRange = self.unoObjs.sheet.getCellRangeByName(rangeName)
                oRange.setDataArray(tuple(data))
            except RuntimeException:
                raise DocAccessError()
        self.logger.debug("outputToColumn END")

    def outputString(self, colLetter, row, strval):
        """This will probably work fine for numbers too."""
        cellName = "%s%d" % (colLetter, row)
        self.logger.debug("Writing '%s' to %s" % (strval, cellName))
        try:
            cell = self.unoObjs.sheet.getCellRangeByName(cellName)
            cell.setString(strval)
        except RuntimeException:
            raise DocAccessError()

    def createSpreadsheet(self):
        """
        Create an empty calc spreadsheet.
        """
        self.logger.debug("opening new spreadsheet")
        newDoc = self.unoObjs.desktop.loadComponentFromURL(
                 "private:factory/scalc", "_blank", 0, ())
        newDocObjs = self.unoObjs.getDocObjs(newDoc, doctype='calc')
        self.logger.debug("createSpreadsheet() END")
        return newDocObjs

#-------------------------------------------------------------------------------
# End of SpreadsheetOutput.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of FileReader.py
#-------------------------------------------------------------------------------



class FileReader:
    """Abstract base class for XML file readers."""

    SUPPORTED_FORMATS = []  # list of tuples of name, text description

    def __init__(self, unoObjs):
        if self.__class__ is FileReader:   # if base class is instantiated
            raise NotImplementedError

        self.unoObjs     = unoObjs
        self.logger      = logging.getLogger("lingt.Access.FileReader")
        self.msgbox      = MessageBox(unoObjs)
        self.progressBar = ProgressBar(unoObjs, "Loading data...")
        self.dom         = None

    @classmethod
    def supportedNames(cls):
        names = [name for name,desc in cls.SUPPORTED_FORMATS]
        return names

    def read(self):
        """Pychecker will be upset if this method is not implemented."""
        raise NotImplementedError

    def getSuggestions(self):
        """Get suggested ref numbers. Intended for linguistic examples only,
        so subclasses are not required to redefine this method.
        """
        return []

#-------------------------------------------------------------------------------
# End of FileReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SpreadsheetReader.py
#-------------------------------------------------------------------------------



class SpreadsheetReader:
    """
    Methods to read from an open spreadsheet.
    """
    def __init__(self, calcUnoObjs):
        self.unoObjs = calcUnoObjs
        self.logger  = logging.getLogger("lingt.Access.SpreadsheetReader")

    def getColumnStringList(self, colLetter, skipFirstRow):
        """
        Returns a list of strings.
        Stops when no more strings are below in that column.
        """
        self.logger.debug("getColumnStringList BEGIN")

        colNum  = ord(colLetter) - ord('A')
        try:
            oColumn = self.unoObjs.sheet.getColumns().getByIndex(colNum)
            self.logger.debug("Using column " + oColumn.getName())
            oRanges = self.unoObjs.document.createInstance(
                      "com.sun.star.sheet.SheetCellRanges")
            oRanges.insertByName("", oColumn)
            cellFlags   = STRING | NUM_VAL | DATETIME   # any string or number
            oCellRanges = oRanges.queryContentCells(cellFlags)
            if oCellRanges.getCount() == 0:
                self.logger.debug("No data found.")
                return []
            rangeAddress = oCellRanges.getRangeAddresses()[-1]
            rowEnd       = rangeAddress.EndRow + 1   # EndRow is 0-based
            self.logger.debug("Found data up to row %d" % (rowEnd))
            rowStart = 1
            if skipFirstRow:
                rowStart = 2
            listLen = rowEnd - rowStart + 1
        except RuntimeException:
            raise DocAccessError()
        return self.getColumnStringListByLen(colLetter, skipFirstRow, listLen)

    def getColumnStringListByLen(self, colLetter, skipFirstRow, listLen):
        """
        Returns a list of length listLen of strings.
        Cells may be empty.
        """
        self.logger.debug("getColumnStringListByLen BEGIN")
        row1 = 1
        if skipFirstRow:
            row1 = 2
        row2 = row1 + listLen - 1
        if row2 < row1:
            self.logger.debug("Range too small to contain data.")
            return []
        rangeName = "%s%d:%s%d" % (colLetter, row1, colLetter, row2)
        self.logger.debug(rangeName)
        try:
            oRange = self.unoObjs.sheet.getCellRangeByName(rangeName)
            rowTuples = oRange.getDataArray()
        except RuntimeException:
            raise DocAccessError()
        if len(rowTuples) == 0:
            self.logger.debug("Could not get data.")
            return []
        columnTuples = list(zip(*rowTuples))  # arrange the data by columns
        self.logger.debug("getColumnStringListByLen END")
        return list(columnTuples[0])

class CalcFileReader(FileReader):
    """Use Calc to read a file such as .ods"""

    SUPPORTED_FORMATS = [
        ('spreadsheet', "Spreadsheet (.ods .xls .xlsx .csv) for Calc")]

    def __init__(self, genericUnoObjs):
        FileReader.__init__(self, genericUnoObjs)
        self.locale = Locale(genericUnoObjs)
        self.calcUnoObjs = None

    def setFileConfig(self, fileconfig):
        self.fileconfig = fileconfig

    def read(self):
        """Harvest data by grabbing word strings from one or more columns."""
        self.logger.debug("read_file BEGIN")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        self.progressBar.updatePercent(20)
        ok = self.loadDoc(self.fileconfig.filepath)
        if not ok:
            self.progressBar.close()
            return list()
        spreadsheetReader = SpreadsheetReader(self.calcUnoObjs)
        self.progressBar.updatePercent(60)
        self.words = [] # list to store examples
        for dataField in self.fileconfig.dataFields:
            if dataField.fieldType == DataField.COLUMN_LETTER:
                try:
                    stringList = spreadsheetReader.getColumnStringList(
                                 dataField.fieldValue,
                                 self.fileconfig.skipFirstRow)
                except DocAccessError:
                    self.msgbox.display(
                        "Error reading file %s", (self.fileconfig.filepath,))
                    self.progressBar.close()
                    return []
                for text in stringList:
                    if text != "":
                        ## Add word
                        word = WordInList()
                        word.text = text
                        word.source = self.fileconfig.filepath
                        self.words.append(word)
        self.logger.debug("Setting visible.")
        self.calcUnoObjs.window.setVisible(True)
        if len(self.words) == 0:
            self.msgbox.display(
                "Did not find any data in file %s", (self.fileconfig.filepath,))
        self.progressBar.updateFinishing()
        self.progressBar.close()
        return self.words

    def getSpreadsheetReader(self):
        """
        Use this method as an alternative to read().
        This is a more general approach for loading data, not just for
        harvesting data to make a word list.
        """
        if self.calcUnoObjs is None:
            return None
        return SpreadsheetReader(self.calcUnoObjs)

    def loadDoc(self, filepath):
        """
        Sets self.calcUnoObjs to a loaded Calc doc.
        File will open minimized if not already open.
        """
        self.logger.debug("Opening file " + filepath)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", (filepath,))
            return False
        fileUrl = uno.systemPathToFileUrl(os.path.realpath(filepath))
        uno_args = (
            createProp("Minimized", True),
        )
        newDoc  = self.unoObjs.desktop.loadComponentFromURL(
                  fileUrl, "_default", 0, uno_args)
        try:
            self.calcUnoObjs = self.unoObjs.getDocObjs(newDoc, doctype='calc')
        except AttributeError as exc:
            self.msgbox.display(str(exc))
            return False
        self.calcUnoObjs.window.setVisible(True)  # otherwise it will be hidden
        self.logger.debug("Opened file.")
        return True

#-------------------------------------------------------------------------------
# End of SpreadsheetReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Search.py
#-------------------------------------------------------------------------------



class ExampleSearch:
    def __init__(self, unoObjs):
        self.unoObjs        = unoObjs
        self.logger         = logging.getLogger("lingt.Access.Search")
        self.msgbox         = MessageBox(unoObjs)
        self.foundSomething = False
        self.search         = None
        self.logger.debug("ExampleSearch init() finished")

    def findRefNumber(self, startFromBeginning, findingAll=False):
        """Returns the string found, or None."""
        self.logger.debug("findRefNumber BEGIN")

        ## Set up the search

        if self.search is None:
            self.search = self.unoObjs.document.createSearchDescriptor()
            self.search.SearchRegularExpression = True
            self.search.SearchString = \
                "#[a-zA-Z0-9][a-zA-Z0-9\._\-]*[a-zA-Z0-9][:space:]*"

        ## Do the search

        found = None
        if startFromBeginning:
            found = self.unoObjs.document.findFirst( self.search )
        else:
            found = self.unoObjs.document.findNext(
                        self.unoObjs.viewcursor.getEnd(), self.search)
        ## Results

        if found:
            self.logger.debug("Found " + found.String)
            self.unoObjs.controller.select(found)
            self.foundSomething = True
            return found.String
        else:
            if self.foundSomething:
                message = "No more reference numbers found."
                self.foundSomething = False
            else:
                message = "Did not find a reference number."
                if findingAll:
                    self.msgbox.display(message)
                if not startFromBeginning:
                    message += \
                        "\n Try checking the box to search from beginning."
                else:
                    message += \
                        "\n Make sure to type # in front."
            if not findingAll:
                self.msgbox.display(message)
            return None

    def findRefCharStyle(
            self, charStyleName, startFromBeginning, findingAll=False):
        """returns the string found, or None."""
        self.logger.debug("findRefCharStyle BEGIN")

        foundText = self.__findRefCharStyle(charStyleName, startFromBeginning)
        if foundText is not None:
            self.logger.debug("Found " + foundText)
            self.foundSomething = True
            return foundText
        else:
            if self.foundSomething:
                message = "No more existing examples found."
                self.foundSomething = False
            else:
                message = "Did not find an existing example."
                if findingAll:
                    self.msgbox.display(message)
                if not startFromBeginning:
                    message += \
                        "\n Try checking the box to search from beginning."
                else:
                    message += \
                        "\n Verify the example reference number's style."
            if not findingAll:
                self.msgbox.display(message)
            return None

    def __findRefCharStyle(self, charStyleName, startFromBeginning):
        """Given a char style name, finds the next ref of that style.
        Returns the entire string that uses the style.
        If nothing is found, returns None.
        """
        self.logger.debug("findTextByCharStyle " + safeStr(charStyleName))

        oVC = self.unoObjs.viewcursor   # shorthand variable name
        if startFromBeginning:
            self.logger.debug("going to beginning")
            oLCurs = self.unoObjs.text.createTextCursor()
            oLCurs.gotoStart(False)
            oVC.gotoRange(oLCurs, False)
        oVC.collapseToEnd()  # make sure nothing is selected
        if oVC.TextFrame:
            # Need to get outside of the frame
            self.logger.debug("escaping from text frame")
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:Escape", "", 0, ())
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:Escape", "", 0, ())

        ## Now start looking for the character style

        afterViewCursor = False  # ignore elements before viewcursor
        if startFromBeginning:
            afterViewCursor = True
        reachedVCTable  = False  # ignore tables before viewcursor
        vcTableName     = None
        if oVC.TextTable:
            vcTableName = oVC.TextTable.getName()
        oParEnum = self.unoObjs.text.createEnumeration()
        while oParEnum.hasMoreElements():
            oPar = oParEnum.nextElement()
            if oPar.supportsService("com.sun.star.text.Paragraph"):
                self.logger.debug("looking at para")
                if not afterViewCursor:
                    rc = RangeCompare(oPar.getEnd(), oVC)
                    if rc.compareVCtoRange() != -1:
                        # The paragraph is not after the viewcursor, so 
                        # skip this paragraph.
                        #self.logger.debug("para before oVC")
                        continue
                    afterViewCursor = True
                oSectionEnum = oPar.createEnumeration()
                while oSectionEnum.hasMoreElements():
                    oSection = oSectionEnum.nextElement()
                    if oSection.TextPortionType == "Text":
                        if oSection.CharStyleName == charStyleName:
                            self.logger.debug("Found style " +
                                              safeStr(charStyleName))
                            result = oSection.getString()
                            if result:
                                oVC.gotoRange(oSection.getStart(), False)
                                oVC.gotoRange(oSection.getEnd(),   True)
                                #self.logger.debug("returning a string")
                                self.logger.debug("returning a string: '%s'" %
                                                  (result))
                                return result
            elif oPar.supportsService("com.sun.star.text.TextTable"):
                oTable = oPar
                self.logger.debug("looking at table " + oTable.getName())
                if not afterViewCursor:
                    # Note: As explained in the API, oTable.getAnchor() cannot
                    # be used to determine where the table is.
                    # Instead, comparing names works well for our needs.
                    if vcTableName:
                        if oTable.getName() == vcTableName:
                            reachedVCTable = True
                            continue
                        elif reachedVCTable:
                            afterViewCursor = True
                        else:
                            continue
                    else:
                        # Move the viewcursor to a new location: this table.
                        originalRange = oVC.getEnd()
                        self.unoObjs.controller.select(oTable) # go to 1st cell
                        oVC.gotoEnd(False) # goto end of cell if cell not empty
                        rc = RangeCompare(originalRange, oVC)
                        if rc.compareVCtoRange() < 0:
                            oVC.gotoRange(originalRange, False)
                            continue
                        else:
                            afterViewCursor = True
                self.logger.debug("searching " + oTable.getName())
                self.unoObjs.controller.select(oTable)  # go to first cell
                firstCell = oVC.Cell
                oVC.gotoEnd(False) # go to end of cell if cell is not empty
                if oVC.Cell.CellName == firstCell.CellName:
                    oVC.gotoEnd(False) # go to end of last cell in table
                oTextCurs = oVC.getText().createTextCursorByRange(
                            oVC.getStart())
                while not oTextCurs.CharStyleName == charStyleName:
                    if not oTextCurs.goLeft(1, False):
                        break
                foundSomething = False
                while oTextCurs.CharStyleName == charStyleName:
                    if not oTextCurs.goLeft(1, True):
                        break
                    foundSomething = True
                if foundSomething:
                    oTextCurs.goRight(1, True)
                result = oTextCurs.getString()
                if foundSomething and result:
                    oVC.gotoRange(oTextCurs.getStart(), False)
                    oVC.gotoRange(oTextCurs.getEnd(),   True)
                    #self.logger.debug("returning a string")
                    self.logger.debug("returning a string: '%s'" % (result))
                    return result
                self.logger.debug("no ref found in this table")
        self.logger.debug("returning None")
        return None

    def refInTable(self):
        """
        Returns True if the selected ref is in a TextTable.
        Otherwise deselects the ref and returns False.
        """
        if not self.unoObjs.viewcursor.TextTable:
            self.unoObjs.viewcursor.collapseToEnd()
            self.unoObjs.viewcursor.goRight(0, False)
            return False
        return True

class RangeCompare:
    """
    Compare the viewcursor to a text range (a location).
    Can be useful when traversing a cursor over a range.
    The range is expected not to be modified.
    """
    def __init__(self, rangeEnd, viewCursor):
        self.oVC        = viewCursor
        self.rangeEnd   = rangeEnd
        self.logger     = logging.getLogger("lingt.Access.Search")
        self.endX       = -1
        self.endY       = -1

    def getCoords(self):
        if self.endY > -1:
            return
        # remember where we were, because we'll need to use the viewcursor
        originalVC = self.oVC.getText().createTextCursorByRange(self.oVC)

        self.oVC.gotoRange(self.rangeEnd, False)
        self.endX = self.oVC.getPosition().X;
        self.endY = self.oVC.getPosition().Y;

        self.oVC.gotoRange(originalVC, False)

    def compareVCtoRange(self):
        """
        Compare the viewcursor to the range.
        Assume we are travelling with the viewcursor.
        See if it is up to the end yet or not.
        The comparison is done by checking the physical position of the cursor.
        Returns -1 if the VC location is less than self.rangeEnd, 0 if it is
        the same, and 1 if it is greater.
        Returns -2 if they are on the same line but not in the same spot, and
        it's not certain which location is greater.
        """
        self.getCoords()
        curX = self.oVC.getPosition().X;
        curY = self.oVC.getPosition().Y;
        if curY < self.endY:
            self.logger.debug(str(curY) + " < " + str(self.endY))
            return -1;
        elif curY > self.endY:
            self.logger.debug(str(curY) + " > " + str(self.endY))
            return 1;
        elif curY == self.endY:
            if curX == self.endX:
                if self.differentPlaces(self.oVC, self.rangeEnd):
                    # There is probably a word-final diacritic that doesn't
                    # change the position, so we're not to the end yet.
                    self.logger.debug("Including word-final diacritic.")
                    return -2;
                # We're at the end.
                self.logger.debug(
                    "VC same loc as text range (%d, %d)." % (curX, curY))
                return 0;
            else:
                # Probably we haven't gone far enough.
                # If there is some problem we may have gone too far, in which
                # case the method will return -1 when we get to the next line.
                # There are several advantages of not comparing curX and
                # self.endX here.  First, this handles right-to-left scripts.
                # Second, some fonts render badly and so going right one
                # character may not always be moving physically to the right.
                self.logger.debug("Probably haven't gone far enough.")
                return -2;

    def differentPlaces(self, oCurs1, oCurs2):
        """
        Test using compareRegion to see if two cursors are in different places.
        If compareRegion fails, such as after a nested table, return False.
        """
        try:
            oText = oCurs1.getText()
            return oText.compareRegionEnds(oCurs1, oCurs2) != 0
        except:
            return False

    #def moreToGoInRegion(self, oLCurs, oRCurs):
    #    """
    #    As of OOoLT 1.2.5, compareVCtoRange() is used instead of this method
    #    because it works better with nested tables.
    #    Returns 1 if more to go, 0 if same, and -1 if past the end.
    #    If comparison is not possible, returns 1.
    #    """
    #    try:
    #        oText = oRCurs.getText()
    #        return oText.compareRegionEnds(oLCurs, oRCurs)
    #    except IllegalArgumentException:
    #        self.logger.debug(
    #            "compareRegion failed, perhaps because of nested tables")
    #        rText = InText(oRCurs)
    #        lText = InText(oLCurs)
    #        self.logger.debug(rText.describeComparison(lText))
    #        return 1

class TextSearch:
    """Execute a search to find some text and get resulting text ranges."""

    def __init__(self, unoObjs, progressBar, checkForFormatting=True):
        self.unoObjs            = unoObjs
        self.progressBar        = progressBar
        self.logger             = logging.getLogger("lingt.Access.Search")
        self.locale             = Locale(unoObjs)
        self.ranges             = []   # list of TxtRange objects
        self.checkForFormatting = checkForFormatting

    def setConfig(self, config):
        """Setttings typically specified by the user."""
        self.fontToFind   = config.scopeFont
        self.fontType     = config.fontType
        self.styleToFind  = config.scopeStyle
        self.localeToFind = config.localeToFind
        self.SFMsToFind   = config.scopeSFMs
        self.matchesLimit = config.matchesLimit

    def getRanges(self):
        return self.ranges

    def scopeWholeDoc(self):
        self.logger.debug("scopeWholeDoc BEGIN")
        self.ranges   = []

        self.addRangeList(
            self.getTextSectionsForParEnumerator(self.unoObjs.text))

        ## Footnotes

        self.logger.debug("looking for footnotes")
        footnotes = self.unoObjs.document.getFootnotes()
        endnotes  = self.unoObjs.document.getEndnotes()
        for notes in (footnotes, endnotes):
            for i in range(0, notes.getCount()):
                oNote    = notes.getByIndex(i) 
                oParEnum = oNote.createEnumeration()
                while oParEnum.hasMoreElements():
                    oPar = oParEnum.nextElement()
                    if oPar.supportsService("com.sun.star.text.Paragraph"):
                        oSectionEnum = oPar.createEnumeration()
                        while oSectionEnum.hasMoreElements():
                            oSection = oSectionEnum.nextElement()
                            if oSection.TextPortionType == "Text":
                                # TextPortions include the TextRange service.
                                self.addRange(oSection)
        self.logger.debug("scopeWholeDoc END")

    def scopeWholeDocTraverse(self):
        """
        Enumerating often splits up words because new sections get created
        when a character is typed out of order.
        Here is a presumably slower, less accurate method that preserves whole
        words.
        Traverse the document with cursors to split into chunks,
        since just adding self.unoObjs.text whole gets slow after about 100
        pages.
        """
        self.logger.debug("scopeWholeDocTraverse BEGIN")
        oText = self.unoObjs.text
        oCursor = oText.createTextCursorByRange(oText.getStart())
        oCursor.collapseToStart()
        MANY_CHARACTERS = 16384     # perhaps 5 pages, but this varies greatly
        oLCurs = oText.createTextCursorByRange(oCursor.getStart())
        oLCurs.collapseToStart()
        while oCursor.goRight(MANY_CHARACTERS, True):
            while oCursor.goRight(1, True):
                # Find a wordbreak
                if oCursor.getString().endswith(" "):
                    break
            oRCurs = oText.createTextCursorByRange(oLCurs.getStart())
            oRCurs.collapseToStart()
            oRCurs.gotoRange(oCursor.getEnd(), True)
            self.addRange(oRCurs)
            oLCurs.gotoRange(oCursor.getEnd(), False)
            oLCurs.collapseToStart()
        oRCurs = oText.createTextCursorByRange(oLCurs.getStart())
        oRCurs.collapseToStart()
        oRCurs.gotoRange(oText.getEnd(), True)
        self.addRange(oRCurs)
        self.logger.debug("scopeWholeDocTraverse END")

    def scopeSelection(self):
        self.logger.debug("scopeSelection BEGIN")
        self.ranges   = []

        oSels = self.unoObjs.controller.getSelection()
        if oSels is None:
            raise ScopeError("No text is selected.")
        if not oSels.supportsService("com.sun.star.text.TextRanges"):
            # When cells are selected rather than text,
            # the selection is a TextTableCursor and has no text ranges.
            raise ScopeError(
                "Please do not select individual table cells.")
        #self.logger.debug("getCount() = " + str(oSels.getCount()))
        if oSels.getCount() == 1:
            oSel = oSels.getByIndex(0)
            if oSel.supportsService("com.sun.star.text.TextRange"):
                oCursor = oSel.getText().createTextCursorByRange(oSel)
                if oCursor.isCollapsed():
                    raise ScopeError("No text is selected.")
        for i in range(0, oSels.getCount()):
            oSel = oSels.getByIndex(i)
            if oSel.supportsService("com.sun.star.text.TextRange"):
                self.addRangeList(
                    self.getRangesForCursor(oSel))

    def scopeFont(self):
        """
        This only searches direct formatting, that is, not including styles.
        """
        self.logger.debug("scopeFont BEGIN")

        if self.fontType in ['Complex', 'Asian']:
            self.scopeComplexFont()
            return
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchString = ""
        search.SearchAll    = True
        attrName = "CharFontName"
        self.logger.debug("Searching for %s='%s'" % (attrName, self.fontToFind))
        attrs = (
            # trailing comma is required to make a tuple
            createProp(attrName, self.fontToFind),
        )
        search.setSearchAttributes(attrs)
        self.doSearch(search)

    def scopeParaStyle(self):
        """
        self.styleToFind should be the DISPLAY NAME of a paragraph style.
        For example, LO 4.0 EN-US will find "Default Style" but not "Standard".
        """
        self.logger.debug("scopeParaStyle BEGIN")
        self.logger.debug("looking for " + str(self.styleToFind))
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchStyles = True
        search.SearchString = self.styleToFind
        search.SearchAll    = True

        self.doSearch(search)

    def scopeCharStyle(self):
        """
        OOo does not currently have a built-in way to search for character
        styles, so we must go through the document to look for the style.

        self.styleToFind should be the UNDERLYING NAME of a character style.
        For example, "Standard", not "Default Style".
        """
        self.logger.debug("scopeCharStyle BEGIN")
        self.logger.debug("looking for " + str(self.styleToFind))
        simpleTextSections = self.getTextSectionsForParEnumerator (
                             self.unoObjs.text)
        for simpleTextSection in simpleTextSections:
            if simpleTextSection.CharStyleName == self.styleToFind:
                self.logger.debug("Found style " +
                    safeStr(self.styleToFind))
                # TextPortions include the TextRange service.
                self.addRange(simpleTextSection)

    def scopeComplexFont(self):
        """
        Similar to character styles, 
        searching for complex fonts using a search descriptor is currently
        buggy, so we enumerate instead.
        """
        self.logger.debug("scopeCharStyle BEGIN")
        simpleTextSections = self.getTextSectionsForParEnumerator (
                             self.unoObjs.text)
        for simpleTextSection in simpleTextSections:
            if self.fontType == "Complex":
                sectionFont = simpleTextSection.CharFontNameComplex
            elif self.fontType == "Asian":
                sectionFont = simpleTextSection.CharFontNameAsian
            else:
                raise ScopeError(
                    "Unexpected font type %s.", (self.fontType))
            if sectionFont == self.fontToFind:
                self.logger.debug("Found font " +
                    safeStr(self.fontToFind))
                # TextPortions include the TextRange service.
                self.addRange(simpleTextSection)

    def scopeLocale(self):
        """
        This is similar to searching for a character style.
        """
        self.logger.debug("scopeLocale BEGIN")
        lang = self.localeToFind    # two-letter language code
        if not lang:
            raise ScopeError("No locale was specified.")
        simpleTextSections = self.getTextSectionsForParEnumerator (
                             self.unoObjs.text)
        for simpleTextSection in simpleTextSections:
            if (simpleTextSection.CharLocale.Language == lang or
                simpleTextSection.CharLocaleComplex.Language == lang or
                simpleTextSection.CharLocaleAsian.Language == lang
               ):
                # TextPortions include the TextRange service.
                self.addRange(simpleTextSection)

    def scopeSFMs(self):
        sfm_str      = re.sub(r'\\', r'', self.SFMsToFind)
        sfms         = re.split(r'\s+', sfm_str)
        sfm_expr     = r'|'.join(sfms)
        search_regex = r"^\\(" + sfm_expr + ") (.+)$"
        self.logger.debug("Searching " + search_regex)

        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchRegularExpression = True
        search.SearchString            = search_regex
        self.doSearch(search)

        ## Modify the range starts so that the SFM markers are not included.

        self.logger.debug("Moving the start to after the SFM marker.")
        for txtRange in self.ranges:
            oSel = txtRange.sel
            oText = oSel.getText()
            oCursor = oText.createTextCursorByRange(oSel)
            oCursor.collapseToStart()
            while oCursor.goRight(1, True):
                if oCursor.getString().endswith(" "):
                    oCursor.collapseToEnd()
                    oCursor.gotoRange(oSel.getEnd(), True)
                    txtRange.sel = oCursor
                    break
                elif oText.compareRegionEnds(oCursor, oSel.getEnd()) < 0:
                    self.logger.debug("passed end")
                    break

    def doSearch(self, search):
        self.logger.debug("doSearch BEGIN")
        self.ranges = []

        selsFound = self.unoObjs.document.findAll( search )
        self.progressBar.updatePercent(12)

        self.selsCount = selsFound.getCount()
        if selsFound.getCount() == 0:
            self.logger.debug("Did not find anything.")
            return
        for i in range(0, selsFound.getCount()):
            self.logger.debug("Found selection " + str(i))
            selectionFound = selsFound.getByIndex(i)
            self.addRangeList(
                self.getRangesForCursor(selectionFound))
            nextProgress = 15 + int(25 * float(i) / selsFound.getCount())
            self.progressBar.updatePercent(nextProgress)
            if self.matchesLimit > 0 and i >= self.matchesLimit:
                # Stop here. This may help with large documents, doing a little
                # at a time. Ideally Data Conversion would be robust
                # enough to handle large amounts of data, but this is a
                # workable solution in the meantime.
                self.logger.debug("Stopping at this match")
                return

    def getTextSectionsForParEnumerator(self, oParEnumerator):
        """Get text sections for all paragraphs that are enumerated by the 
        given object.
        Do not pass a cursor inside a table as the oParEnumerator, because it
        will work but the entire table
        or paragraph will be enumerated, not just the selection.
        Instead use getRangesForCursor().
        """
        simpleTextSections = []
        oParEnumeration = oParEnumerator.createEnumeration()
        i = 0
        while oParEnumeration.hasMoreElements():
            oPar = oParEnumeration.nextElement()
            i += 1
            self.logger.debug("par " + str(i) + ": " + oPar.ImplementationName)
            simpleTextSections += self.getTextSections(oPar)
        return simpleTextSections

    def getTextSections(self, oPar, recursive=False):
        """Recursively enumerate paragraphs, tables and frames.
        Sets self.simpleTextSections.
        Tables may be nested.
        """
        if not recursive:
            ## Initialize
            self.simpleTextSections = []

        if oPar.supportsService("com.sun.star.text.Paragraph"):
            oSectionEnum = oPar.createEnumeration()
            while oSectionEnum.hasMoreElements():
                oSection = oSectionEnum.nextElement()
                if oSection.TextPortionType == "Text":
                    # TextPortions include the TextRange service.
                    self.logger.debug("simple text portion")
                    self.simpleTextSections.append(oSection)
                elif oSection.TextPortionType == "Frame":
                    self.logger.debug("Frame text portion")
                    oFrameEnum = oSection.createContentEnumeration(
                        "com.sun.star.text.TextFrame")
                    while oFrameEnum.hasMoreElements():  # always only 1 item?
                        oFrame = oFrameEnum.nextElement()
                        self.getTextSections(oFrame, recursive=True)
        elif oPar.supportsService("com.sun.star.text.TextTable"):
            oTable = oPar
            self.logger.debug("table " + oTable.getName())
            self.unoObjs.controller.select(oTable)  # go to first cell
            sNames = oTable.getCellNames()
            for sName in sNames:
                self.logger.debug("cell " + oTable.getName() + ":" + sName)
                oCell = oTable.getCellByName(sName)
                oParEnum = oCell.createEnumeration()
                while oParEnum.hasMoreElements():
                    oPar2 = oParEnum.nextElement()
                    self.getTextSections(oPar2, recursive=True)
        elif oPar.supportsService("com.sun.star.text.TextFrame"):
            oFrame = oPar
            self.logger.debug("frame " + oFrame.getName())
            oParEnum = oFrame.createEnumeration()
            while oParEnum.hasMoreElements():
                oPar2 = oParEnum.nextElement()
                self.getTextSections(oPar2, recursive=True)

        return self.simpleTextSections

    def getRangesForCursor(self, oSel):
        """
        If there is different formatting, then we handle each string separately
        that is formatted differently.
        """
        self.logger.debug("getRangesForCursor BEGIN")
        if not self.checkForFormatting:
            return [oSel]
        simpleTextRanges = []   # a range that has only one formatting
        oText     = oSel.getText()
        oSelLeft  = oSel.getStart()
        oSelRight = oSel.getEnd()
        try:
            if oText.compareRegionStarts(oSel.getEnd(), oSel) >= 0:
                self.logger.debug("start of selection is on the right")
                oSelLeft, oSelRight = oSelRight, oSelLeft     # swap
        except IllegalArgumentException:
            self.logger.warn("could not get range from selection")

        try:
            oCursTmp = oText.createTextCursorByRange(oSelLeft)
        except:
            self.logger.warn("Failed to go to text range.");
            return
        oCursTmp.gotoRange(oSelRight, True)
        self.logger.debug("text = '" + oCursTmp.getString() + "'")

        # We use the viewcursor because text cursors cannot goRight into tables
        oVC      = self.unoObjs.viewcursor
        oVC.gotoRange(oSelLeft, False)
        #self.logger.debug(debug_tellNextChar(oVC))
        oLCurs   = oVC.getText().createTextCursorByRange(oVC)
        oRCurs   = oText.createTextCursorByRange(oSelRight)
        traveler = RangeCompare(oRCurs, self.unoObjs.viewcursor)

        MAX_STRING_LENGTH = 4096   # handle the input in chunks if needed
        stringLen         = 0
        stringNum         = 1
        selFormatting     = None   # formatting of selected string

        while True:

            ## Check for formatting changes at the current location

            splitAtFormattingChange = False
            if selFormatting is None:
                selFormatting = Formatting(oVC, self.logger)
            oVCTextCurs = oVC.getText().createTextCursorByRange(oVC)
            if oVCTextCurs.isEndOfParagraph():
                self.logger.debug("at end of paragraph")
                splitAtFormattingChange = True
            elif traveler.compareVCtoRange() < 0:
                # We need to look ahead because the different formatting is
                # only seen when the cursor is on the right side of the
                # character.
                oVC.goRight(1, False)
                #self.logger.debug(debug_tellNextChar(oVC))
                nextFormatting = Formatting(oVC, self.logger)
                if not nextFormatting.sameCharForm(selFormatting):
                    self.logger.debug("found different formatting")
                    splitAtFormattingChange = True
                oVC.goLeft(1, False)

            #self.logger.debug("moreToGo = " + str(traveler.compareVCtoRange()))
            if (splitAtFormattingChange or
                traveler.compareVCtoRange() == 0 or
                stringLen >= MAX_STRING_LENGTH
               ):
                    ## Add this range

                    oLCurs.gotoRange(oVC, True)  # select the string
                    self.logger.debug("String " + str(stringNum) + " = '" + 
                                      oLCurs.getString() + "'")
                    oTextCursTmp = oLCurs.getText().createTextCursorByRange (
                                   oLCurs)
                    simpleTextRanges.append(oTextCursTmp)

                    oLCurs.goRight(0, False)  # deselect
                    stringLen = 0
                    selFormatting = None
                    stringNum += 1

            ## Go on to the next character

            if traveler.compareVCtoRange() < 0:
                prevInText = InText(oVC)
                #self.logger.debug("oVC goRight")
                if not oVC.goRight(1, False):
                    self.logger.warn("cannot go any further")
                    break
                #self.logger.debug(debug_tellNextChar(oVC))
                stringLen += 1

                nextInText = InText(oVC)
                if not nextInText.inSameText(prevInText):
                    ## Going into a new text such as a TextTable.
                    self.logger.debug("Going into new text.")
                    oLCurs = oVC.getText().createTextCursorByRange(oVC)
            else:
                # We've reached the end of the string
                self.logger.debug("reached end of string")
                break

        self.logger.debug("getRangesForCursor END")
        return simpleTextRanges

    def addRangeList(self, rangeList):
        """Convenience function to handle a list."""
        for aRange in rangeList:
            self.addRange(aRange)

    def addRange(self, oSel):
        """Adds the selection to self.ranges
        oSels implements type com.sun.star.text.XTextRange.
        """
        self.logger.debug("adding range")
        #xray(oSel, self.unoObjs)
        txtRange         = TxtRange()
        txtRange.sel     = oSel     # contains the location range
        txtRange.inTable = False
        txtRange.inFrame = False
        txtRange.inSomething = False

        # These attributes are mentioned in TextRangeContentProperties
        try:
            if oSel.TextTable: txtRange.inTable = True
            if oSel.TextFrame: txtRange.inFrame = True
            if oSel.TextTable or oSel.TextFrame or oSel.TextField:
                txtRange.inSomething = True
        except AttributeError:
            # leave them all set to False
            pass

        self.ranges.append(txtRange)

        # -- For debugging only --
        # Note: oSel.getString() isn't as reliable as this method.
        #
        #oCursor = oSel.getText().createTextCursorByRange(oSel)
        #self.logger.debug("range text = " + oCursor.getString())

        self.logger.debug("addRange END")

class Formatting:
    """To hold cursor formatting attributes such as CharFontName"""
    #ATTR_NAMES = [
    #    'CharFontName', 'CharFontNameAsian', 'CharFontNameComplex',
    #    'CharFontStyleName', 'CharFontStyleNameAsian',
    #    'CharFontStyleNameComplex', 'CharStyleName', 'DropCapCharStyleName',
    #    'CharCombinePrefix', 'CharCombineSuffix',
    #    'HyperLinkName', 'HyperLinkTarget', 'HyperLinkURL',
    #    'ListId', 'ListLabelString',
    #    'NumberingStyleName', 'PageDescName', 'PageStyleName',
    #    'ParaAutoStyleName', 'ParaBackGraphicFilter', 'ParaBackGraphicURL',
    #    'ParaConditionalStyleName', 'ParaStyleName',
    #    'RubyCharStyleName', 'RubyText', 'UnvisitedCharStyleName',
    #    'VisitedCharStyleName', 'CharAutoEscapement', 'CharAutoKerning',
    #    'CharBackTransparent', 'CharCombineIsOn', 'CharContoured',
    #    'CharCrossedOut', 'CharFlash', 'CharHidden', 'CharNoHyphenation',
    #    'CharOverlineHasColor', 'CharRotationIsFitToLine', 'CharShadowed',
    #    'CharUnderlineHasColor', 'CharWordMode', 'ContinueingPreviousSubTree',
    #    'DropCapWholeWord', 'IsSkipHiddenText', 'IsSkipProtectedText',
    #    'NumberingIsNumber', 'ParaBackTransparent', 'ParaExpandSingleWord',
    #    'ParaIsAutoFirstLineIndent', 'ParaIsCharacterDistance',
    #    'ParaIsConnectBorder', 'ParaIsForbiddenRules',
    #    'ParaIsHangingPunctuation', 'ParaIsHyphenation',
    #    'ParaIsNumberingRestart', 'ParaKeepTogether', 'ParaLineNumberCount',
    #    'ParaRegisterModeActive', 'ParaSplit', 'RubyIsAbove', 'SnapToGrid',
    #    'CharCaseMap', 'CharEmphasis', 'CharEscapement',
    #    'CharEscapementHeight', 'CharFontCharSet', 'CharFontCharSetAsian',
    #    'CharFontCharSetComplex', 'CharFontFamily', 'CharFontFamilyAsian',
    #    'CharFontFamilyComplex', 'CharFontPitch', 'CharFontPitchAsian',
    #    'CharFontPitchComplex', 'CharKerning', 'CharOverline', 'CharRelief',
    #    'CharRotation', 'CharScaleWidth', 'CharStrikeout', 'CharUnderline',
    #    'NumberingLevel', 'NumberingStartValue', 'OutlineLevel',
    #    'PageNumberOffset', 'ParaAdjust',
    #    'ParaHyphenationMaxHyphens', 'ParaHyphenationMaxLeadingChars',
    #    'ParaHyphenationMaxTrailingChars', 'ParaLastLineAdjust',
    #    'ParaOrphans', 'ParaVertAlignment', 'ParaWidows', 'RubyAdjust',
    #    'WritingMode', 'BorderDistance', 'BottomBorderDistance',
    #    'BreakType', 'CharBackColor', 'CharColor', 'CharOverlineColor',
    #    'CharPosture', 'CharPostureAsian', 'CharPostureComplex',
    #    'CharUnderlineColor', 'LeftBorderDistance', 'ParaBackColor',
    #    'ParaBackGraphicLocation', 'ParaBottomMargin',
    #    'ParaFirstLineIndent', 'ParaLeftMargin', 'ParaLineNumberStartValue',
    #    'ParaRightMargin', 'ParaTopMargin', 'RightBorderDistance',
    #    'TopBorderDistance', 'CharHeight', 'CharHeightAsian',
    #    'CharHeightComplex']

    ## The value CharAutoStyleName is apparently a summary of formatting.
    ## It is MUCH faster than checking for each different type of formatting.
    ## In addition to formatting, check for character styles (CharStyleName).
    ATTR_NAMES = ['CharAutoStyleName', 'CharStyleName']

    def __init__(self, oSel, logger):
        self.logger = logger
        self.attrs = {}
        for attr in self.ATTR_NAMES:
            self.attrs[attr] = ""
            if oSel != None:
                self.attrs[attr] = oSel.getPropertyValue(attr)
                #self.logger.debug(oSel.getString() + " attr " + attr + " = " +
                #          self.attrs[attr])

    def sameCharForm(self, otherFormatting):
        for attr in self.ATTR_NAMES:
            if self.attrs[attr] != otherFormatting.attrs[attr]:
                #self.logger.debug(attr + " '" + self.attrs[attr] + "' != '" +
                #                  otherFormatting.attrs[attr] + "'")
                return False
        #self.logger.debug("same formatting")
        return True

class InText:
    """To hold cursor attributes about which text we are in."""
    #ATTR_NAMES = ['CharAutoStyleName', 'TextTable', 'TextFrame', 'Cell',
    #              'TextSection', 'TextField', 'Footnote']
    ATTR_NAMES = ['TextTable', 'CellName', 'TextFrame']

    def __init__(self, oSel):
        self.attrs = {}
        for attr in self.ATTR_NAMES:
            self.attrs[attr] = ""
            if oSel != None:
                self.attrs[attr] = self.getAttr(oSel, attr)

    def getAttr(self, oSel, attrName):
        if attrName == "CellName":
            if oSel.Cell is not None:
                return oSel.Cell.CellName
            return ""
        elif attrName == "TextTable":
            if oSel.TextTable is not None:
                return oSel.TextTable.getName()
            return ""
        elif attrName == "TextFrame":
            if oSel.TextFrame is not None:
                return oSel.TextFrame.getName()
            return ""
        return ""

    def inSameText(self, otherFormatting):
        for attr in self.ATTR_NAMES:  
            if self.attrs[attr] != otherFormatting.attrs[attr]:
                return False
        return True

    def describeComparison(self, otherFormatting):
        for attr in self.ATTR_NAMES:  
            if self.attrs[attr] != otherFormatting.attrs[attr]:
                return self.attrs[attr] + " != " + otherFormatting.attrs[attr]
        return "seem to be the same"

class SearchSettings:
    """A structure to hold settings for AbbrevSearch."""
    def __init__(self):
        self.searchUpperCase    = False
        self.maxSearchLength    = -1
        self.searchAffix        = ""
        self.searchDelimiters   = ""
        self.startFromBeginning = False
        self.searchParaStyle    = ""

class AbbrevSearch:
    """Search for unknown abbreviations and add them to the list."""
    def __init__(self, unoObjs):
        self.unoObjs          = unoObjs
        self.logger           = logging.getLogger("lingt.Access.Search")
        self.msgbox           = MessageBox(unoObjs)
        self.selectionFound   = None
        self.alreadyAskedList = []
        self.logger.debug("AbbrevSearch init() finished")

    def findOccurrences(self, abbrevList):
        """Modify abbrevList."""
        progressBar = ProgressBar(self.unoObjs, "Searching for occurrences...")
        progressBar.show()
        progressBar.updateBeginning()

        abbrevs = abbrevList.getList()
        for itemPos in range(0, len(abbrevs)):
            search = self.unoObjs.document.createSearchDescriptor()
            search.SearchString        = abbrevs[itemPos].abbrev
            search.SearchCaseSensitive = False
            search.SearchWords         = True

            selectionsFound = self.unoObjs.document.findAll(search)
            occurrences = selectionsFound.getCount()
            abbrevList.setOccurrences(itemPos, occurrences)
            percentFinished = 10 + int(float(itemPos) / len(abbrevs) * 80)
            progressBar.updatePercent(percentFinished)
        progressBar.updateFinishing()
        progressBar.close()

    def findNext(self, searchConfig, currentAbbrevList):
        """Look for possible abbreviations.
        Search by regular expression on a certain paragraph style.
        """
        self.logger.debug("findNext BEGIN")
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchStyles = True
        search.SearchString = searchConfig.searchParaStyle

        if searchConfig.startFromBeginning:
            self.logger.debug("Start from beginning")
            self.selectionFound = self.unoObjs.document.findFirst( search )
            searchConfig.startFromBeginning = False
        elif self.selectionFound:
            # Start from previous match
            self.logger.debug("Start from previous match")
            self.selectionFound = self.unoObjs.document.findNext(
                self.selectionFound.getEnd(), search)
        else:
            # Start from current location
            self.logger.debug("Start from current loc")
            self.selectionFound = self.unoObjs.document.findNext(
                self.unoObjs.viewcursor.getEnd(), search)
        while self.selectionFound:
            possibilities = []
            string = self.selectionFound.String
            self.logger.debug("Selection found: " + string)
            delims = "- "
            if searchConfig.searchDelimiters != "":
                delims = searchConfig.searchDelimiters
            morphs = re.split('[' + delims + ']', string)
            if searchConfig.searchAffix == "suffix":
                morphs = morphs[1:]
            elif searchConfig.searchAffix == "prefix":
                morphs = morphs[:-1]
            for morph in morphs:
                self.logger.debug("Checking morph " + morph)
                words = re.split(r'[.\',()_;]', morph)
                for word in words:
                    self.logger.debug("Checking word " + word)
                    if len(word) > searchConfig.maxSearchLength:
                        continue
                    if word.lower() in currentAbbrevList:
                        # Already in the list, so no need to add it.
                        continue
                    if word.lower() in self.alreadyAskedList:
                        continue
                    if searchConfig.searchUpperCase and word.upper() != word:
                        continue

                    ## Found a possibility.
                    if len(possibilities) == 0:
                        self.logger.debug("Selecting")
                        start  = self.selectionFound.getStart()
                        end    = self.selectionFound.getEnd()
                        if self.selectionFound.getText().compareRegionStarts(
                            start, self.selectionFound) >= 0:
                                end, start = start, end     # swap
                        self.unoObjs.viewcursor.gotoRange(start, False)
                        self.unoObjs.viewcursor.gotoRange(end,   True)
                    self.logger.debug("Adding to alreadyAskedList")
                    self.alreadyAskedList.append(word.lower())
                    possibilities.append(word)

            self.logger.debug("Possibilities: " + str(len(possibilities)))
            if len(possibilities) > 0:
                return possibilities

            ## Nothing found yet. Try the next found.
            self.selectionFound = self.unoObjs.document.findNext(
                self.selectionFound.getEnd(), search)
        self.logger.debug("findNext END")
        return []

class TxtRange:
    """A structure to store a range of text."""
    def __init__(self):
        self.sel     = None
        self.start   = None
        self.end     = None
        self.inTable = False
        self.inFrame = False
        self.inSomething = False

#-------------------------------------------------------------------------------
# End of Search.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of UserVars.py
#-------------------------------------------------------------------------------



class UserVars:
    """
    Access to the user variables of the Writer document.
    These can be viewed using Insert -> Fields -> Other.
    """
    def __init__(self, VAR_PREFIX, writer_document, logger):
        """
        VAR_PREFIX:         For each module, we use a prefix to the variable
                            name, for example all variables used in phonology
                            begin with "LTp_"
        writer_document:    The UNO document object, not available for Calc.
        logger:             For debugging the file that is using this class.
        """
        self.VAR_PREFIX = VAR_PREFIX
        self.document   = writer_document
        self.logger     = logger

    def set(self, baseVarName, stringVal):
        """Stores a value in a Writer doc that is persistent across macro
        calls."""
        varName = self.getVarName(baseVarName)
        self.logger.debug("setUserVar " + varName)
        if stringVal is None:
            stringVal = ""
        fieldMasters = self.document.getTextFieldMasters()
        fieldName    = "com.sun.star.text.FieldMaster.User." + varName
        if fieldMasters.hasByName(fieldName):
            field = fieldMasters.getByName(fieldName)
            field.setPropertyValue("Content", stringVal)
        else:
            xMaster = self.document.createInstance(
                      "com.sun.star.text.fieldmaster.User")
            xMaster.Name    = varName
            xMaster.Content = stringVal
            xUserField = self.document.createInstance(
                         "com.sun.star.text.textfield.User")
            xUserField.attachTextFieldMaster(xMaster)

    def get(self, baseVarName):
        """Returns the value of a user variable as a string"""
        varName = self.getVarName(baseVarName)
        self.logger.debug("getUserVar " + varName)
        fieldMasters = self.document.getTextFieldMasters()
        fieldName    = "com.sun.star.text.FieldMaster.User." + varName
        if fieldMasters.hasByName(fieldName):
            field = fieldMasters.getByName(fieldName)
            stringVal = field.getPropertyValue("Content")
            return stringVal
        else:
            return ""

    def getVarName(self, baseVarName):
        """
        Punctuation shouldn't be used in names, because Writer doesn't always
        handle it correctly.
        """
        varName = baseVarName.replace("?", "")
        return self.VAR_PREFIX + varName

    def getInt(self, varName):
        """Returns the value of a user variable as an integer.
        If string is empty or not numeric, returns 0.
        """
        val = self.get(varName)
        try:
            return int(val)
        except ValueError:
            # raised for strings like "" and "5a"
            return 0

    def getFloat(self, varName):
        """Returns the value of a user variable as a float.
        If string is empty or not numeric, returns 0.0
        """
        val = self.get(varName)
        try:
            return float(val)
        except ValueError:
            # raised for strings like "" and "5a"
            return 0.

    def isEmpty(self, varName):
        """Returns True if string is empty, otherwise False."""
        val = self.get(varName)
        return (val == "")

    def delete(self, varName):
        """Deletes a user variable if it exists.
        Returns True if a variable was deleted.
        """
        varName = self.VAR_PREFIX + varName
        self.logger.debug("delUserVar " + varName)
        fieldMasters = self.document.getTextFieldMasters()
        fieldName    = "com.sun.star.text.FieldMaster.User." + varName
        if fieldMasters.hasByName(fieldName):
            field = fieldMasters.getByName(fieldName)
            field.setPropertyValue("Content", "")
            field.dispose()
            self.logger.debug("Field deleted")
            return True
        else:
            self.logger.debug("Field not found")
            return False

class SettingsDocPreparer:
    """Prepares a Writer document to contain user variables."""
    def __init__(self, VAR_PREFIX, writerUnoObjs):
        self.VAR_PREFIX = VAR_PREFIX
        self.unoObjs    = writerUnoObjs
        self.logger     = logging.getLogger("lingt.Access.SettingsDocPreparer")

    def prepare(self):
        """
        Called from a Writer doc.
        Make sure the current document is ready to use for settings.

        Any item in the Writer Linguistics menu that doesn't require document
        contents but uses user var settings should call this method.
        """
        finder = SettingsDocFinder(self.VAR_PREFIX, self.unoObjs)
        maxHasSettings, twoDocsHaveMax, unused = finder.findBestDoc()
        userVars = UserVars(self.VAR_PREFIX, self.unoObjs.document, self.logger)
        alreadyHasSettings = self.setHasSettings(
                             userVars, maxHasSettings, twoDocsHaveMax)
        if alreadyHasSettings:
            return

        oParEnumeration = self.unoObjs.text.createEnumeration()
        if oParEnumeration.hasMoreElements():
            oParEnumeration.nextElement() # empty docs have one paragraph
        hasContents = oParEnumeration.hasMoreElements()
        parCount = 0
        while oParEnumeration.hasMoreElements():
            parCount += 1
            oParEnumeration.nextElement()
        self.logger.debug("Found %d paragraphs in current doc." % (parCount))
        if not hasContents:
            self.addContents()

    def addContents(self):
        """Add explanation text to the document."""
        PARAGRAPH_BREAK = uno.getConstantByName(
            "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK")
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        oVC.gotoEnd(False)
        locale   = Locale(self.unoObjs)
        componentName = ""
        if self.VAR_PREFIX == "LTscr_":
            componentName = locale.getText("Script Practice")
        elif self.VAR_PREFIX == "LTw_":
            componentName = locale.getText("Word List and Spelling")
        elif self.VAR_PREFIX == "LTsp_":
            componentName = locale.getText("Spelling")
        message = locale.getText(
            "This document stores %s settings.  "
            "Please leave it open while using %s.  "
            "If you want to keep the settings to use again later, "
            "then save this document.") % (componentName, componentName)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        self.unoObjs.text.insertString(oVC, message, 0)
        self.unoObjs.text.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)

    def setHasSettings(self, userVars, maxHasSettings, twoDocsHaveMax):
        """
        Sets HasSettings to the highest value of any open documents.
        Returns True if HasSettings was set previously.
        """
        varname            = "HasSettings"
        alreadyHasSettings = False
        if not userVars.isEmpty(varname):
            alreadyHasSettings = True
            currentSettingsVal = userVars.getInt(varname)
            if currentSettingsVal == maxHasSettings and not twoDocsHaveMax:
                # No need to make any changes
                return alreadyHasSettings
        if maxHasSettings == -1:
            newVal = 1
        else:
            newVal = maxHasSettings + 1
        userVars.set(varname, str(newVal))
        return alreadyHasSettings

class SettingsDocFinder:
    """Helps a Calc document that references user variables."""
    def __init__(self, VAR_PREFIX, genericUnoObjs):
        self.VAR_PREFIX = VAR_PREFIX
        self.unoObjs    = genericUnoObjs
        self.logger     = logging.getLogger("lingt.Access.SettingsDocFinder")

    def getWriterDoc(self):
        """
        Typically called from a Calc spreadsheet.
        Make sure we have a Writer document ready for user variables.

        Takes an object of type UnoObjs that has service objs but
        probably not writer doc objs.
        Returns unoObjs of a writer document to hold UserVars settings.

        Finds the best candidate found to store user variables.
        If no candidate is found, opens a blank document.
        """
        maxHasSettings, twoDocsHaveMax, docFound = self.findBestDoc()
        if docFound:
            return docFound
        else:
            ## Open a blank document in the background.
            uno_args = (
                createProp("Minimized", True),
            )
            newDoc  = self.unoObjs.desktop.loadComponentFromURL(
                      "private:factory/swriter", "_blank", 0, uno_args)
            # this won't modify the original reference kept by calling code
            writerUnoObjs = self.unoObjs.getDocObjs(newDoc)
            writerUnoObjs.window.setVisible(True)
            userVars = UserVars(
                       self.VAR_PREFIX, writerUnoObjs.document, self.logger)
            preparer = SettingsDocPreparer(self.VAR_PREFIX, writerUnoObjs)
            preparer.setHasSettings(userVars, maxHasSettings, twoDocsHaveMax)
            preparer.addContents()
            return writerUnoObjs

    def findBestDoc(self):
        """
        Searches all open documents for a Writer document.
        If more than one is found, chooses the one with the highest value of
        HasSettings, which will usually be the most recent.

        @returns highest value found of HasSettings
        @returns true if two or more docs have the same highest value
        @returns UNO objects of document with highest value
        """
        maxVal         = -1
        bestDoc        = None
        twoDocsHaveMax = False  # if two or more docs have the same max value
        doclist        = self.unoObjs.getOpenDocs('writer')
        for docUnoObjs in doclist:
            self.logger.debug("Checking writer document for settings.")
            userVars = UserVars(
                       self.VAR_PREFIX, docUnoObjs.document, self.logger)
            val = userVars.getInt("HasSettings")
            if val > 0 and val > maxVal:
                self.logger.debug(
                    "Found doc with HasSettings value %s." % (val))
                maxVal         = val
                bestDoc        = docUnoObjs
                twoDocsHaveMax = False
            elif val == maxVal:
                twoDocsHaveMax = True
        return maxVal, twoDocsHaveMax, bestDoc

#-------------------------------------------------------------------------------
# End of UserVars.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of TextChanges.py
#-------------------------------------------------------------------------------



class TextChanger:
    def __init__(self, unoObjs, progressBar):
        self.unoObjs      = unoObjs
        self.progressBar  = progressBar
        self.logger       = logging.getLogger("lingt.Access.TextChanges")
        self.msgboxFour   = FourButtonDialog(unoObjs)
        self.secCall      = None
        self.styleType    = None
        self.newStyleName = None
        self.newFontName  = None
        self.newFontSize  = 0
        self.numChanges   = 0
        self.askEach      = False

    def setConverterCall(self, secCall):
        self.secCall = secCall

    def setStyleToChange(self, styleType, styleName):
        self.styleType    = styleType
        self.newStyleName = styleName

    def setFontToChange(self, fontName, fontSize, fontType):
        self.styleType = "FontOnly"
        self.newFontName = fontName
        self.newFontSize = fontSize
        self.newFontType = fontType

    def doChanges(self, ranges, askEach):
        """
        ranges is a list of Search.TxtRange objects.
        Returns number of changes made
        """
        self.logger.debug("doChanges BEGIN")
        self.numChanges      = 0
        self.numStyleChanges = 0
        self.askEach         = askEach
        originalRange        = self.unoObjs.viewcursor.getStart()
        rangeLastChanged     = None

        rangeNum = 1
        for txtRange in ranges: 
            changed = False
            try:
                changed = self.changeTextRange(txtRange)
            except UserInterrupt:
                return self.numChanges, self.numStyleChanges
            if changed:
                self.logger.debug("Converted.")
                try:
                    rangeLastChanged = txtRange.sel.getStart()
                except:
                    # Just give up; it's not essential.
                    self.logger.warn("Failed to get text range.")
                    pass
            nextProgress = 40 + int(50 * float(rangeNum) / len(ranges))
            self.progressBar.updatePercent(nextProgress)
            rangeNum += 1

        try:
            if rangeLastChanged is None:
                self.unoObjs.viewcursor.gotoRange(originalRange, False)
            else:
                self.unoObjs.viewcursor.gotoRange(rangeLastChanged, False)
        except:
            # Just give up; it's not essential.
            self.logger.warn("Failed to go to text range.")
            pass

        self.logger.debug("doChanges END")
        return self.numChanges, self.numStyleChanges

    def changeTextRange(self, txtRange):
        self.logger.debug("changeTextRange BEGIN")
        oSel = txtRange.sel
        try:
            oCursor = oSel.getText().createTextCursorByRange(oSel)
        except:
            self.logger.warn("Failed to go to text range.");
            return
        self.logger.debug("String = '" + oCursor.getString() + "'")
        if self.askEach:
            self.unoObjs.viewcursor.gotoRange(oSel.getStart(), False)
            self.unoObjs.viewcursor.gotoRange(oSel.getEnd(),   True) # select
            result = self.msgboxFour.display("Make this change?")
            if result == "yes":
                # keep going
                pass
            elif result == "no":
                return False
            elif result == "yesToAll":
                self.askEach = False
            else:
                raise UserInterrupt()
        return self.convertString(oCursor)

    def convertString(self, oCurs):
        """Here is where the call to SEC Converters is actually done.
        It calls an OOo C++ component which calls the SEC dll file.
        Then it makes the change in Writer.
        Also sets the new style.
        Returns True if a change is made.
        """
        inValue = oCurs.getString()

        ## Get the converted value

        changedText = False
        if self.secCall is not None:
            success, outValue = self.secCall.Convert(inValue)
            if not success:
                return False
            changedText = True
            if outValue == inValue:
                changedText = False
            outValue = self.prepareNewlines(outValue)
            if outValue == inValue:
                changedText = False
            self.logger.debug("converted text '" + outValue + "'")

        if self.styleType == "ParaStyleName":
            self.changeParaStyle(oCurs)
        elif self.styleType == "CharStyleName":
            self.changeCharStyle(oCurs)
        elif self.styleType == "FontOnly":
            self.changeFont(oCurs)

        if not changedText:
            return False
        changeString(oCurs, outValue)
        self.numChanges += 1
        return True

    def prepareNewlines(self, value):
        """CR+LF creates an unwanted line break when inserting
        back into Writer.  So we change it to just CR before inserting.
        Inserting LF creates a line break, and CR creates a paragraph break.

        Tips for figuring out newlines:
        + In OOo go to View -> Nonprinting characters.
          This shows paragraph breaks and line breaks distinctly.
          Type Shift+Enter to create a line break.
        + Open the debug file in Notepad++ and View -> Show symbol -> EOL.
        """
        newValue = value
        regex1 = re.compile(r"(\x0d\x0a)", re.S);    # CR+LF for para break
        newValue = re.sub(regex1, "\x0d", newValue)
        return newValue

    def changeParaStyle(self, oCurs):
        """Goes to the paragraph and sets the style.
        Changes any directly formatted font name and size to the default.
        """
        self.logger.debug("changeParaStyle BEGIN")
        oCursDbg = oCurs.getText().createTextCursorByRange(oCurs.getStart())
        oCursDbg.gotoRange(oCurs.getEnd(), True)
        self.logger.debug("oCursText = '" + oCursDbg.getString() + "'")
        oTextEnum = oCurs.createEnumeration()   # enumerate current paragraph
        firstCellName = ""
        while oTextEnum.hasMoreElements():
            oTextElem = oTextEnum.nextElement()
            self.logger.debug("oTextElem " + oTextElem.getString())
            if oTextElem.TextTable:
                curCurs = oTextElem.getText().createTextCursorByRange(
                            oTextElem.getStart())
                if curCurs is None:
                    ## This happens after the first cell; I don't know why.
                    curCellName = "none"
                else:
                    curCurs.goRight(0, False)
                    curCellName = curCurs.Cell.CellName
                self.logger.debug("cell " + curCellName)
                if firstCellName == "":
                    firstCellName = curCellName
                elif curCellName != firstCellName:
                    ## Somehow we've gotten out of the cell
                    self.logger.debug("moved out of " + firstCellName +
                                      " to " + curCellName)
                    break
            if oTextElem.supportsService("com.sun.star.text.Paragraph"):
                curStyleName = oTextElem.getPropertyValue(self.styleType)
                if curStyleName != self.newStyleName:
                    self.logger.debug("Setting style " + self.newStyleName)
                    oTextElem.setPropertyValue(
                        self.styleType, self.newStyleName)
                    self.numStyleChanges += 1
                oTextPortionsEnum = oTextElem.createEnumeration()
                while oTextPortionsEnum.hasMoreElements():
                    oTextPortion = oTextPortionsEnum.nextElement()
                    DIRECT = uno.Enum("com.sun.star.beans.PropertyState",
                                      "DIRECT_VALUE")
                    for propName in ("CharFontName", "CharHeight"):
                        if oTextPortion.getPropertyState(propName) == DIRECT:
                            oTextPortion.setPropertyToDefault(propName)
                            self.logger.debug("setToDefault " + propName)
        self.clearFont(oCurs)
        self.logger.debug("changeParaStyle END")

    def changeCharStyle(self, oCurs):
        """Change character style."""
        curStyleName = oCurs.getPropertyValue(self.styleType)
        if curStyleName != self.newStyleName:
            self.logger.debug("Setting style " + self.newStyleName +
                              " from " + curStyleName)
            oCurs.setPropertyValue(self.styleType, self.newStyleName)
            self.numStyleChanges += 1
        self.clearFont(oCurs)

    def clearFont(self, oCurs):
        """
        Setting a character or paragraph style doesn't clear font
        formatting. It just overrides it. This can be a problem when changing
        encoding using a font as the scope, because it will still find the
        font even after the conversion is done.
        To make sure this doesn't happen, reset the font when changing styles.
        """
        self.newFontType = 'Western'
        self.newFontName = None
        self.newFontSize = None
        self.changeFont(oCurs)

    def changeFont(self, oCurs):
        for propSuffix in ['', 'Complex', 'Asian']:
            oCurs.setPropertyToDefault("CharFontName" + propSuffix)
            oCurs.setPropertyToDefault("CharHeight"   + propSuffix)
        propSuffix = self.newFontType
        if propSuffix == 'Western':
            propSuffix = ""
        if self.newFontName and self.newFontName.strip():
            self.setCursProp(
                oCurs, 'CharFontName' + propSuffix, self.newFontName)
        if self.newFontSize and self.newFontSize > 0:
            self.setCursProp(
                oCurs, 'CharHeight'   + propSuffix, self.newFontSize)

    def setCursProp(self, oCurs, propName, newVal):
        curVal = oCurs.getPropertyValue(propName)
        if curVal != newVal:
            self.logger.debug("Setting %s from %s" % (propName, curVal))
            oCurs.setPropertyValue(propName, newVal)
            self.numStyleChanges += 1

class FindAndReplace:
    def __init__(self, writerUnoObjs, askEach=True):
        self.unoObjs      = writerUnoObjs
        self.logger       = logging.getLogger("lingt.Access.FindAndReplace")
        self.msgboxFour   = FourButtonDialog(writerUnoObjs)
        self.askEach      = askEach

    def replace(self, oldString, newString):
        changesMade = 0
        search = self.unoObjs.document.createSearchDescriptor()
        search.SearchString        = oldString
        search.SearchAll           = True
        search.SearchWords         = True
        search.SearchCaseSensitive = False
        selsFound      = self.unoObjs.document.findAll( search )
        self.selsCount = selsFound.getCount()
        if selsFound.getCount() == 0:
            self.logger.debug("Did not find anything.")
            return changesMade
        for i in range(0, selsFound.getCount()):
            self.logger.debug("Found selection " + str(i))
            oSel = selsFound.getByIndex(i)
            if self.askEach:
                self.unoObjs.viewcursor.gotoRange(oSel.getStart(), False)
                self.unoObjs.viewcursor.gotoRange(oSel.getEnd(),   True)
                result = self.msgboxFour.display(
                         "Make this change? (%s -> %s)", (oldString,newString))
                if result == "yes":
                    # keep going
                    pass
                elif result == "no":
                    continue
                elif result == "yesToAll":
                    self.askEach = False
                else:
                    raise UserInterrupt()
                self.unoObjs.viewcursor.goRight(0, False) # deselect
            oTextCursTmp = oSel.getText().createTextCursorByRange(oSel)
            changeString(oTextCursTmp, newString)
            changesMade += 1
        return changesMade

def changeString(oCurs, stringVal):
    """
    Make the change in Writer
    
    To preserve formatting, add extra characters to surround the text.
    We use the "+" character for this purpose.
    Since the "+" characters are inserted following the old string,
    they will take on the old string's attributes.
    Also the starting range will be preserved by this method.
    """
    ## Insert word in between ++.
    start = oCurs.getStart()
    oCurs.collapseToEnd()
    oCurs.getText().insertString(oCurs, "++", False)
    oCurs.goLeft(2, False)
    oCurs.gotoRange(start, True)
    oCurs.setString("")     # deletes all but the extra characters
    oCurs.goRight(1, False) # move in between the two "+" characters.
    oCurs.collapseToEnd()   # Not sure why this is needed, since going right
                            # with False should deselect -- but it didn't.
    oCurs.getText().insertString(oCurs, stringVal, True)

    ## Remove the surrounding '+' characters.
    start = oCurs.getStart()
    end   = oCurs.getEnd()
    oCurs.gotoRange(start, False)
    oCurs.goLeft(1, True)
    oCurs.setString("")     # delete the first extra character
    oCurs.gotoRange(end, False)
    oCurs.goRight(1, True)
    oCurs.setString("")     # delete the second extra character
    oCurs.goRight(0, False)

#-------------------------------------------------------------------------------
# End of TextChanges.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DataConversion.py
#-------------------------------------------------------------------------------



class DataConversion:
    def __init__(self, docUnoObjs, userVars, styleFonts):
        """
        unoObjs needs to be for a writer doc if calling doConversions_writer(),
        and for a calc spreadsheet if calling doConversion_calc().
        """
        self.unoObjs        = docUnoObjs
        self.styleFonts     = styleFonts
        self.logger         = logging.getLogger("lingt.App.DataConversion")
        self.userVars       = userVars
        self.msgbox         = MessageBox(self.unoObjs)
        self.secCall        = SEC_wrapper(self.msgbox)
        self.searchConfig   = None
        self.convName       = ""
        self.directionFw    = True

    def selectConverter(self):
        """
        Returns success, name and whether direction is forward.
        Saves normalization value, since it is not configurable in the dialog.
        """
        self.logger.debug("selectConverter BEGIN")
        success = self.secCall.PickConverter()
        if not success:
            self.logger.debug("User probably pressed cancel.")
            return False, "", False
        self.logger.debug("Picked converter.")
        self.convName    = self.secCall.converterName
        self.directionFw = self.secCall.directionFw
        normalize        = self.secCall.normForm
        self.userVars.set("ConvNormalize", str(normalize))
        self.logger.debug("Converter name is " + self.convName)
        return True, self.convName, self.directionFw

    def setAndVerifyConverter(self, convName, directionFw):
        """
        Call this method before calling one of the doConversion() methods.
        """
        ## Get the converter if not yet done

        if convName == "":
            raise ChoiceProblem("Please select a converter.")
        if convName == "<No converter>":
            return
        if self.convName != convName or self.directionFw != directionFw:

            ## Set the converter

            normalize = self.userVars.getInt("ConvNormalize")
            success = self.secCall.SetConverter (
                      convName, directionFw, normalize)
            if success:
                self.convName    = convName
                self.directionFw = directionFw
            else:
                self.convName    = ""
                raise ChoiceProblem(
                    "Please select the converter again.")
            self.logger.debug("Did set converter.")

    def setAndVerifyConfig(self, config):
        """Reads values from self.config
        Throws ChoiceProblem if the choices are not acceptable.
        """
        self.logger.debug("verifyResults BEGIN")

        ## Verify choices

        if config.whichScope == "":
            raise ChoiceProblem("Please specify a scope.")
        elif config.whichScope == "ParaStyle":
            if config.scopeStyle == "":
                raise ChoiceProblem(
                    "Please select a scope paragraph style.")
        elif config.whichScope == "CharStyle":
            if config.scopeStyle == "":
                raise ChoiceProblem(
                    "Please select a scope character style.")
        elif config.whichScope == "Font":
            if config.scopeFont == "":
                raise ChoiceProblem("Please select a scope font.")
        elif config.whichScope == "SFMs":
            if config.scopeSFMs == "":
                raise ChoiceProblem("Please specify SFMs.")
        self.whichScope   = config.whichScope
        self.searchConfig = ConfigOptions()
        self.searchConfig.scopeStyle   = config.scopeStyle 
        self.searchConfig.scopeFont    = config.scopeFont
        self.searchConfig.fontType     = config.scopeFontType 
        self.searchConfig.scopeSFMs    = config.scopeSFMs 
        self.searchConfig.localeToFind = None
        self.searchConfig.matchesLimit = config.matchesLimit 

        if config.whichTarget == "ParaStyle":
            if config.targetStyle == "":
                raise ChoiceProblem("Please select a target style.")
            fontDef = FontDefStruct(config.targetFontName,
                                           config.targetFontType,
                                           config.targetFontSize)
            self.styleFonts.setParaStyleWithFont(config.targetStyle, fontDef)
        elif config.whichTarget == "CharStyle":
            if config.targetStyle == "":
                raise ChoiceProblem("Please select a target style.")
            fontDef = FontDefStruct(config.targetFontName,
                                           config.targetFontType,
                                           config.targetFontSize)
            self.styleFonts.setCharStyleWithFont(config.targetStyle, fontDef)
        elif config.whichTarget == "FontOnly":
            if config.targetFontName == "":
                raise ChoiceProblem("Please select a target font.")
        self.whichTarget    = config.whichTarget
        self.targetStyle    = config.targetStyle
        self.targetFontName = config.targetFontName
        self.targetFontSize = config.targetFontSize
        self.targetFontType = config.targetFontType 

        self.askEach        = config.askEach
        self.logger.debug("verifyResults END")

    def doConversions_writer(self):
        """For converting data in a Writer doc."""
        self.logger.debug("doConversions_writer BEGIN")

        ## Start progress bar

        progressBar = ProgressBar(self.unoObjs, "Converting...")
        progressBar.show()
        progressBar.updateBeginning()

        ## Find the text ranges

        textSearch = TextSearch(self.unoObjs, progressBar)
        textSearch.setConfig(self.searchConfig)
        try:
            if self.whichScope == "WholeDoc":
                textSearch.scopeWholeDoc()
            elif self.whichScope == "Selection":
                textSearch.scopeSelection()
            elif self.whichScope == "ParaStyle":
                textSearch.scopeParaStyle()
            elif self.whichScope == "CharStyle":
                textSearch.scopeCharStyle()
            elif self.whichScope == "Font":
                textSearch.scopeFont()
            elif self.whichScope == "SFMs":
                textSearch.scopeSFMs()
            else:
                self.msgbox.display("Unexpected value %s", (self.whichScope,))
                progressBar.close()
                return
        except ScopeError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            progressBar.close()
            return
        rangesFound = textSearch.getRanges()

        if progressBar.getPercent() < 40:
            progressBar.updatePercent(40)

        ## Do the changes to those ranges

        textChanger = TextChanger(self.unoObjs, progressBar)
        if self.convName:
            textChanger.setConverterCall(self.secCall)
        if self.whichTarget == "ParaStyle":
            textChanger.setStyleToChange(
                "ParaStyleName", self.targetStyle)
        elif self.whichTarget == "CharStyle":
            textChanger.setStyleToChange(
                "CharStyleName", self.targetStyle)
        elif self.whichTarget == "FontOnly":
            textChanger.setFontToChange(
                self.targetFontName, self.targetFontSize, self.targetFontType)
        numChanges, numStyleChanges = \
            textChanger.doChanges(rangesFound, self.askEach)

        progressBar.updateFinishing()
        progressBar.close()

        ## Display results

        paragraphsFound = len(rangesFound)
        if paragraphsFound == 0:
            self.msgbox.display("Did not find scope of change.")
        elif numChanges == 0:
            if numStyleChanges == 0:
                self.msgbox.display("No changes.")
            else:
                plural = "" if numStyleChanges == 1 else "s"
                    # add "s" if plural
                self.msgbox.display(
                    "No changes, but modified style of %d paragraph%s.",
                    (numStyleChanges, plural))
        elif paragraphsFound == 1:
            plural = "" if numChanges == 1 else "s" # add "s" if plural
            self.msgbox.display("Made %d change%s.", (numChanges, plural))
        else:
            plural = "" if numChanges == 1 else "s" # add "s" if plural
            self.msgbox.display(
                "Found %d paragraphs and made %d change%s.",
                (paragraphsFound, numChanges, plural))

    def doConversions_calc(self, sourceCol, destCol, skipFirstRow):
        """For converting data in a Calc spreadsheet."""
        self.logger.debug("doConversions_calc BEGIN")

        ## Start progress bar

        progressBar = ProgressBar(self.unoObjs, "Converting...")
        progressBar.show()
        progressBar.updateBeginning()

        ## Get list of words from source column
        #  (just strings are enough, no need for a special object)

        reader = SpreadsheetReader(self.unoObjs)
        try:
            inputList = reader.getColumnStringList(sourceCol, skipFirstRow)
        except DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
            progressBar.close()
        if len(inputList) == 0:
            self.msgbox.display(
                "Did not find anything in column %s.", (sourceCol,))
            progressBar.close()
            return

        if progressBar.getPercent() < 40:
            progressBar.updatePercent(40)

        ## Convert

        outList = []
        problems = False
        numChanges = 0
        for inValue in inputList:
            success, outValue = self.secCall.Convert(inValue)
            if success:
                outList.append(outValue)
                if outValue != inValue:
                    numChanges += 1
            else:
                problems = True
                outList.append("")
            
        ## Output results

        outputter = SpreadsheetOutput(self.unoObjs)
        try:
            outputter.outputToColumn(destCol, outList, skipFirstRow)
        except DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")

        progressBar.updateFinishing()
        progressBar.close()

        ## Display results

        if numChanges == 0:
            self.msgbox.display("No changes.")
        elif problems:
            self.msgbox.display("Some words could not be converted.")
        else:
            self.msgbox.display("Successfully finished conversion.")
#-------------------------------------------------------------------------------
# End of DataConversion.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgDataConv.py
#-------------------------------------------------------------------------------



def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.DlgDataConv")
    logger.debug("----ShowDlg()----------------------------------------------")
    unoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgDataConversion(unoObjs, logger)
    dlg.showDlg()

class DlgDataConversion(XActionListener, XItemListener, XTextListener,
                        unohelper.Base):
    """The dialog implementation."""

    def __init__(self, unoObjs, logger):
        self.unoObjs        = unoObjs
        self.logger         = logger
        USERVAR_PREFIX      = 'LTc_'  # LinguisticTools Data Conversion vars
        self.userVars       = UserVars(USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox         = MessageBox(unoObjs)
        self.styleFonts     = StyleFonts(unoObjs, self.userVars)
        self.app            = DataConversion(
                              unoObjs, self.userVars, self.styleFonts)
        self.convertOnClose = False

    def showDlg(self):
        self.logger.debug("DlgDataConversion.showDlg BEGIN")
        dlg = None
        try:
            dlg = self.unoObjs.dlgprov.createDialog(
                  "vnd.sun.star.script:LingToolsBasic.DlgDataConversion"
                  "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not create dialog.")
            return
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.txtConverterName     = getControl(dlg, 'txtCnvtrName')
            self.chkDirectionReverse  = getControl(dlg,
                                        'chkDirectionReverse')
            self.chkVerify            = getControl(dlg, 'chkVerify')
            self.optScopeWholeDoc     = getControl(dlg,
                                        'optScopeWholeDoc')
            self.optScopeSelection    = getControl(dlg,
                                        'optScopeSelection')
            self.optScopeFont         = getControl(dlg, 'optScopeFont')
            self.optScopeParaStyle    = getControl(dlg,
                                        'optScopeParaStyle')
            self.optScopeCharStyle    = getControl(dlg,
                                        'optScopeCharStyle')
            self.optScopeSFMs         = getControl(dlg, 'optScopeSFMs')
            self.optScopeFontWestern  = getControl(dlg,
                                        'optScopeFontRegular')
            self.optScopeFontComplex  = getControl(dlg,
                                        'optScopeFontCTL')
            self.optScopeFontAsian    = getControl(dlg,
                                        'optScopeFontAsian')
            self.optTargetFontWestern = getControl(dlg,
                                        'optTargetFontRegular')
            self.optTargetFontComplex = getControl(dlg,
                                        'optTargetFontCTL')
            self.optTargetFontAsian   = getControl(dlg,
                                        'optTargetFontAsian')
            self.optTargetNoChange    = getControl(dlg,
                                        'optTargetNoChange')
            self.optTargetParaStyle   = getControl(dlg,
                                        'optTargetParaStyle')
            self.optTargetCharStyle   = getControl(dlg,
                                        'optTargetCharStyle')
            self.optTargetFontOnly    = getControl(dlg,
                                        'optTargetFontOnly')
            self.comboScopeParaStyle  = getControl(dlg,
                                        'cmbxScopeParaStyle')
            self.comboScopeCharStyle  = getControl(dlg,
                                        'cmbxScopeCharStyle')
            self.comboScopeFont       = getControl(dlg, 'cmbxScopeFont')
            self.comboTargetParaStyle = getControl(dlg,
                                        'cmbxTargetParaStyle')
            self.comboTargetCharStyle = getControl(dlg,
                                        'cmbxTargetCharStyle')
            self.listTargetStyleFont  = getControl(dlg, 'listStyleFont')
            self.txtSFM               = getControl(dlg, 'txbxSFM')
            self.txtFontSize          = getControl(dlg, 'txtFontSize')
            btnSelectConv             = getControl(dlg, 'BtnSelectConv')
            btnNoConverter            = getControl(dlg, 'BtnNoConverter')
            btnOK                     = getControl(dlg, 'BtnOK')
            btnCancel                 = getControl(dlg, "BtnCancel")
        except LogicError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        self.txtConverterName.setText(self.userVars.get('ConverterName'))
        self.chkDirectionReverse.setState(0)
        varname = 'ConvDirectionFw'
        if (not self.userVars.isEmpty(varname) and
            self.userVars.getInt(varname) == 0
           ):
            self.chkDirectionReverse.setState(1)
        self.chkVerify.setState(
            self.userVars.getInt('AskEachChange'))

        ## Option buttons

        whichScope = self.userVars.get('WhichScope')
        if whichScope == 'WholeDoc':
            self.optScopeWholeDoc.setState(1)   # set to selected
        elif whichScope == 'Selection':
            self.optScopeSelection.setState(1)   # set to selected
        elif whichScope == 'Font':
            self.optScopeFont.setState(1)   # set to selected
        elif whichScope == 'ParaStyle':
            self.optScopeParaStyle.setState(1)   # set to selected
        elif whichScope == 'CharStyle':
            self.optScopeCharStyle.setState(1)   # set to selected
        elif whichScope == 'SFMs':
            self.optScopeSFMs.setState(1)   # set to selected

        fontType = self.userVars.get('ScopeFontType')
        if fontType == 'Western':
            self.optScopeFontWestern.setState(1)   # set to selected
        elif fontType == 'Complex':
            self.optScopeFontComplex.setState(1)   # set to selected
        elif fontType == 'Asian':
            self.optScopeFontAsian.setState(1)     # set to selected
        fontType = self.userVars.get('TargetFontType')
        if fontType == 'Western':
            self.optTargetFontWestern.setState(1)   # set to selected
        elif fontType == 'Complex':
            self.optTargetFontComplex.setState(1)   # set to selected
        elif fontType == 'Asian':
            self.optTargetFontAsian.setState(1)     # set to selected

        whichTarget = self.userVars.get('WhichTarget')
        if whichTarget == 'NoChange':
            self.optTargetNoChange.setState(1)   # set to selected
        elif whichTarget == 'ParaStyle':
            self.optTargetParaStyle.setState(1)   # set to selected
        elif whichTarget == 'CharStyle':
            self.optTargetCharStyle.setState(1)   # set to selected
        elif whichTarget == 'FontOnly':
            self.optTargetFontOnly.setState(1)   # set to selected

        ## Combo box lists

        self.logger.debug("Getting styles...")
        styleNames = getListOfStyles('ParagraphStyles', self.unoObjs)
        self.paraStyleNames = dict(styleNames)
        paraStyleDispNames = tuple([dispName for dispName, name in styleNames])
        styleNames = getListOfStyles('CharacterStyles', self.unoObjs)
        self.charStyleNames = dict(styleNames)
        charStyleDispNames = tuple([dispName for dispName, name in styleNames])

        self.logger.debug("Populating font and styles lists")
        control = self.comboScopeParaStyle
        control.addItems(paraStyleDispNames, 0)
        selectedValue = self.userVars.get('ScopeParaStyle')
        control.setText(selectedValue)

        control = self.comboScopeCharStyle
        control.addItems(charStyleDispNames, 0)
        selectedValue = self.userVars.get('ScopeCharStyle')
        control.setText(selectedValue)

        control = self.comboScopeFont
        fontNames = getListOfFonts(self.unoObjs)
        control.addItems(fontNames, 0)
        selectedValue = self.userVars.get('ScopeFont')
        control.setText(selectedValue)

        control = self.comboTargetParaStyle
        control.addItems(paraStyleDispNames, 0)
        selectedValue = self.userVars.get('TargetParaStyle')
        control.setText(selectedValue)

        control = self.comboTargetCharStyle
        control.addItems(charStyleDispNames, 0)
        selectedValue = self.userVars.get('TargetCharStyle')
        control.setText(selectedValue)

        control = self.listTargetStyleFont
        fontNames = getListOfFonts(self.unoObjs, addBlank=True)
        control.addItems(fontNames, 0)
        control.selectItemPos(0, True)
        self.logger.debug("Finished populating font and styles lists.")

        ## Other fields

        varname = 'SFM_Markers'
        if self.userVars.isEmpty(varname):
            defaultCtrlText = "\\tx \\mb"
            self.userVars.set(varname, defaultCtrlText)
            userVarVal = defaultCtrlText
        else:
            userVarVal = self.userVars.get(varname)
        self.txtSFM.setText(userVarVal)

        ## Enabling and disabling

        self.enableDisable()

        self.optTargetNoChange.addItemListener(self)  # calls itemStateChanged
        self.optTargetParaStyle.addItemListener(self)
        self.optTargetCharStyle.addItemListener(self)
        self.optTargetFontOnly.addItemListener(self)

        self.comboTargetParaStyle.addTextListener(self) # calls textChanged
        self.comboTargetCharStyle.addTextListener(self)

        ## Command buttons

        btnSelectConv.setActionCommand('SelectConverter')
        btnSelectConv.addActionListener(self)
        btnNoConverter.setActionCommand('NoConverter')
        btnNoConverter.addActionListener(self)
        btnOK.setActionCommand('Close_and_Convert')
        btnOK.addActionListener(self)
        btnCancel.setActionCommand('Cancel')
        btnCancel.addActionListener(self)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.convertOnClose:
            self.app.doConversions_writer()
        dlg.dispose()

    def itemStateChanged(self, unused_itemEvent):
        """XItemListener event handler."""
        self.logger.debug("itemStateChanged BEGIN")
        self.enableDisable()

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        listCtrl   = self.listTargetStyleFont  # shorthand variable
        textCtrl   = self.txtFontSize
        if self.optTargetNoChange.getState() == 1:
            listCtrl.selectItemPos(0, True)
            listCtrl.getModel().Enabled = False
            textCtrl.getModel().Enabled = False
        elif self.optTargetFontOnly.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            self.selectTargetFont(None, None)
        elif self.optTargetParaStyle.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            self.selectTargetFont(self.comboTargetParaStyle, 'Paragraph')
        elif self.optTargetCharStyle.getState() == 1:
            listCtrl.getModel().Enabled = True
            textCtrl.getModel().Enabled = True
            self.selectTargetFont(self.comboTargetParaStyle, 'Character')

    def textChanged(self, textEvent):
        self.logger.debug("textChanged BEGIN")
        src = textEvent.Source
        if sameName(src, self.comboTargetParaStyle):
            if self.optTargetParaStyle.getState() == 1:
                self.selectTargetFont(src, 'Paragraph')
        elif sameName(src, self.comboTargetCharStyle):
            if self.optTargetCharStyle.getState() == 1:
                self.selectTargetFont(src, 'Character')
        else:
            self.logger.warn("unexpected source %s" %
                             safeStr(src.Model.Name))

    def selectTargetFont(self, control, family):
        """
        Selects the font based on the value specified in the control.
        If control is None (for initialization or testing), gets values from
        user variables instead.
        """
        self.logger.debug("selectTargetFont BEGIN")
        listCtrl   = self.listTargetStyleFont  # shorthand variable
        listValues = listCtrl.Items
        if control:
            fontType = 'Western'
            if self.optTargetFontComplex.getState() == 1:
                fontType = 'Complex'
            elif self.optTargetFontAsian.getState() == 1:
                fontType = 'Asian'
            displayName = control.getText()
            try:
                if family == 'Paragraph':
                    styleName = self.paraStyleNames[displayName]
                elif family == 'Character':
                    styleName = self.charStyleNames[displayName]
            except KeyError:
                # Perhaps a new style to be created
                self.logger.debug("%s is not a known style." % (displayName))
                return
            fontName, fontSize = self.styleFonts.getFontOfStyle(
                                 styleName, family, fontType)
        else:
            fontName = self.userVars.get(     'TargetFontName')
            fontSize = self.userVars.getFloat('TargetFontSize')
        if fontName and fontName in listValues:
            listCtrl.selectItem(fontName, True)
        else:
            listCtrl.selectItemPos(0, True)
        if fontSize > 0:
            fontSizeStr = "%1.1f" % fontSize
            if fontSizeStr.endswith(".0"):
                fontSizeStr = fontSizeStr[:-2]  # remove trailing ".0"
            self.txtFontSize.setText(fontSizeStr)
        else:
            self.txtFontSize.setText("")

    def actionPerformed(self, event):
        """Handle which button was pressed."""
        self.logger.debug("An action happened: " + event.ActionCommand)
        if event.ActionCommand == 'SelectConverter':
            self.logger.debug("Selecting a converter...")
            success, convName, forward = self.app.selectConverter()
            if success:
                self.txtConverterName.setText(convName)
                self.chkDirectionReverse.setState(not forward)
        elif event.ActionCommand == 'NoConverter':
            self.logger.debug("Clearing converter...")
            self.txtConverterName.setText("<No converter>")
        elif event.ActionCommand == 'Cancel':
            self.logger.debug("Action command was Cancel")
            self.dlgClose()
            return
        elif event.ActionCommand == 'Close_and_Convert':
            self.logger.debug("Closing and Converting...")
            self.getFormResults()
            try:
                self.app.setAndVerifyConverter(
                    self.config.convName, self.config.directionFw)
                self.app.setAndVerifyConfig(self.config)
                self.convertOnClose = True
                self.dlgClose()
            except ChoiceProblem as exc:
                self.msgbox.display(exc.msg, exc.msg_args)

    def getFormResults(self):
        """Reads form fields and sets self.config."""
        self.logger.debug("getFormResults() BEGIN")
        self.config = ConfigOptions()

        ## Converter

        self.config.convName    = self.txtConverterName.getText()
        self.config.directionFw = (self.chkDirectionReverse.getState() == 0) 
        self.config.askEach     = (self.chkVerify.getState()           == 1) 
        self.userVars.set('ConverterName',   self.config.convName)
        self.userVars.set('ConvDirectionFw', str(int(self.config.directionFw)))

        ## Radio buttons and the corresponding combo box selection

        self.config.whichScope    = ""
        self.config.scopeStyle    = ""
        self.config.scopeFont     = ""
        self.config.scopeFontType = ""
        self.config.scopeSFMs     = ""
        if self.optScopeWholeDoc.getState() == 1:   # checked
            self.config.whichScope = 'WholeDoc'
        elif self.optScopeSelection.getState() == 1:   # checked
            self.config.whichScope = 'Selection'
        elif self.optScopeFont.getState() == 1:   # checked
            self.config.whichScope = 'Font'
            self.config.scopeFont = self.comboScopeFont.getText()
            self.config.scopeFontType = 'Western'
            if self.optScopeFontComplex.getState() == 1:
                self.config.scopeFontType = 'Complex'
            elif self.optScopeFontAsian.getState() == 1:
                self.config.scopeFontType = 'Asian'
            self.userVars.set('ScopeFontType', self.config.scopeFontType)
        elif self.optScopeParaStyle.getState() == 1:   # checked
            self.config.whichScope = 'ParaStyle'
            displayName = self.comboScopeParaStyle.getText()
            # use display name when searching
            self.config.scopeStyle = displayName
        elif self.optScopeCharStyle.getState() == 1:   # checked
            self.config.whichScope = 'CharStyle'
            displayName = self.comboScopeCharStyle.getText()
            if displayName in self.charStyleNames:
                self.config.scopeStyle = self.charStyleNames[displayName]
            else:
                self.config.scopeStyle = displayName
        elif self.optScopeSFMs.getState() == 1:   # checked
            self.config.whichScope = 'SFMs'
            self.config.scopeSFMs = self.txtSFM.getText()
        self.userVars.set('WhichScope', self.config.whichScope)

        self.config.whichTarget = ''
        self.config.targetStyle = ''
        if self.optTargetNoChange.getState() == 1:  # checked
            self.config.whichTarget = 'NoChange'
        elif self.optTargetParaStyle.getState() == 1:   # checked
            self.config.whichTarget = 'ParaStyle'
            displayName = self.comboTargetParaStyle.getText()
            if displayName in self.paraStyleNames:
                self.config.targetStyle = self.paraStyleNames[displayName]
            else:
                # Perhaps a new style to be created
                self.config.targetStyle = displayName
        elif self.optTargetCharStyle.getState() == 1:   # checked
            self.config.whichTarget = 'CharStyle'
            displayName = self.comboTargetCharStyle.getText()
            if displayName in self.charStyleNames:
                self.config.targetStyle = self.charStyleNames[displayName]
            else:
                # Perhaps a new style to be created
                self.config.targetStyle = displayName
        elif self.optTargetFontOnly.getState() == 1:   # checked
            self.config.whichTarget = 'FontOnly'
        self.userVars.set('WhichTarget', self.config.whichTarget)

        ## Target font

        self.config.targetFontName = \
            self.listTargetStyleFont.getSelectedItem()
        if self.config.targetFontName == "(None)":
            self.config.targetFontName = None
        try:
            self.config.targetFontSize = float(self.txtFontSize.getText())
        except ValueError:
            self.config.targetFontSize = 0    # unspecified
        if self.config.whichTarget == 'FontOnly':
            self.userVars.set('TargetFontName', self.config.targetFontName)
            self.userVars.set('TargetFontSize',
                              "%1.1f" % self.config.targetFontSize)
        self.config.targetFontType = 'Western'
        if self.optTargetFontComplex.getState() == 1:
            self.config.targetFontType = 'Complex'
        elif self.optTargetFontAsian.getState() == 1:
            self.config.targetFontType = 'Asian'
        self.userVars.set('TargetFontType', self.config.targetFontType)

        ## Hidden variables

        varname = 'MatchLimit'
        if self.userVars.isEmpty(varname):
            self.config.matchesLimit = 0
            self.userVars.set(varname, 0)  # make sure it exists
        else:
            self.config.matchesLimit = self.userVars.getInt(varname)
            self.logger.debug(
                "Using match limit " + str(self.config.matchesLimit))

        ## Save selections for next time

        ctrls = [
          (self.comboScopeParaStyle,  'ScopeParaStyle'),
          (self.comboScopeCharStyle,  'ScopeCharStyle'),
          (self.comboScopeFont,       'ScopeFont'),
          (self.comboTargetParaStyle, 'TargetParaStyle'),
          (self.comboTargetCharStyle, 'TargetCharStyle'),
          (self.txtSFM,               'SFM_Markers')]
        for ctrl in ctrls:
            control, userVar = ctrl
            self.userVars.set(userVar, control.getText())

        self.userVars.set('AskEachChange', str(self.chkVerify.getState()))

        self.logger.debug("getFormResults() END")

#-------------------------------------------------------------------------------
# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of DlgDataConv.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgDataConv_test.py
#-------------------------------------------------------------------------------




class DlgDataConvTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.logger = logging.getLogger("lingt.TestDlg")
        modifyClass_showDlg(DlgDataConversion)

    def setUp(self):
        self.unoObjs = unoObjsForCurrentDoc()
        self.dlg     = DlgDataConversion(self.unoObjs, self.logger)

    def test_scope1(self):
        def useDialog(selfNew):
            selfNew.optScopeWholeDoc.setState(1)
            selfNew.optScopeFont.setState(1)
            selfNew.optScopeParaStyle.setState(1)
            selfNew.optScopeCharStyle.setState(1)
            selfNew.optScopeSFMs.setState(1)
            selfNew.optScopeSelection.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.assertEqual(self.dlg.optScopeWholeDoc.getState(), 0)
        self.assertEqual(self.dlg.optScopeSelection.getState(), 1)
        self.assertEqual(self.dlg.optScopeFont.getState(), 0)
        self.assertEqual(self.dlg.optScopeParaStyle.getState(), 0)
        self.assertEqual(self.dlg.optScopeCharStyle.getState(), 0)
        self.assertEqual(self.dlg.optScopeSFMs.getState(), 0)
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichScope, "Selection")
        self.assertEqual(self.dlg.config.scopeFont, "")
        self.assertEqual(self.dlg.config.scopeStyle, "")
        self.assertEqual(self.dlg.config.scopeSFMs, "")

    def test_scope2(self):
        def useDialog(selfNew):
            selfNew.optScopeFont.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assert_(hasattr(self.dlg.config, "scopeFont"))

    def test_scope3(self):
        def useDialog(selfNew):
            selfNew.optScopeParaStyle.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assert_(hasattr(self.dlg.config, "scopeStyle"))

    def test_scope4(self):
        #return # when was this added?
        def useDialog(selfNew):
            selfNew.optScopeCharStyle.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assert_(hasattr(self.dlg.config, "scopeStyle"))

    def test_target1(self):

        ## Define a function to manipulate dialog controls
        def useDialog(selfNew):
            selfNew.optTargetParaStyle.setState(1)
            selfNew.optTargetCharStyle.setState(1)
        DlgDataConversion.useDialog = useDialog

        ## Now run the modified code
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "CharStyle")

    def test_target2(self):
        def useDialog(selfNew):
            selfNew.optTargetCharStyle.setState(1)
            selfNew.optTargetParaStyle.setState(1)
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "ParaStyle")

    def test_target3(self):
        def useDialog(selfNew):
            selfNew.optTargetParaStyle.setState(1)
            selfNew.optTargetFontComplex.setState(1)
            #selfNew.comboTargetParaStyle.setText("Default Style")
            selfNew.comboTargetParaStyle.setText("Default")
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "ParaStyle")
        if platform.system() == "Windows":
            self.assertEqual(self.dlg.config.targetFontName, "Mangal")
        else:
            self.assertEqual(self.dlg.config.targetFontName, "Lohit Hindi")
        self.assertEqual(self.dlg.config.targetFontSize, 12.)

    def test_target4(self):
        def useDialog(selfNew):
            selfNew.optTargetParaStyle.setState(1)
            selfNew.optTargetFontWestern.setState(1)
            selfNew.comboTargetParaStyle.setText("Preformatted Text")
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "ParaStyle")
        if platform.system() == "Windows":
            self.assertEqual(self.dlg.config.targetFontName, "Courier New")
        else:
            self.assertEqual(self.dlg.config.targetFontName, "DejaVu Sans Mono")
        self.assertEqual(self.dlg.config.targetFontSize, 10.)

    def test_target5(self):
        def useDialog(selfNew):
            selfNew.optTargetFontOnly.setState(1)
            selfNew.listTargetStyleFont.selectItem("Arial Black", True)
            selfNew.txtFontSize.setText("15")
        DlgDataConversion.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.getFormResults()
        self.assertEqual(self.dlg.config.whichTarget, "FontOnly")
        self.assertEqual(self.dlg.config.targetFontName, "Arial Black")
        self.assertEqual(self.dlg.config.targetFontSize, 15.)

    def tearDown(self):
        if self.dlg:
            if hasattr(self.dlg, "dlgDispose"):
                self.dlg.dlgDispose()


#-------------------------------------------------------------------------------
# End of DlgDataConv_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of FieldTags.py
#-------------------------------------------------------------------------------

class FieldTags:
    """Parent class for managing tags."""
    tagVars     = []
    defaultTags = {}

    def __init__(self, userVars):
        if self.__class__ is FieldTags:   # if base class is instantiated
            raise NotImplementedError
        self.userVars = userVars
        self.__determineNames()

    def __determineNames(self):
        """Sets self.tags based on user vars and defaults."""
        self.tags = {}
        for key, var in self.tagVars:
            name = self.userVars.get(var)
            if name == "":
                name = self.defaultTags[key]
                self.userVars.set(var, name)
            self.tags[key] = name

    def getTags(self):
        return self.tags

class GrammarTags(FieldTags):
    tagVars  = [['ref',   "SFMarker_RefNum"],
                ['orth',  "SFMarker_Orthographic"],
                ['text',  "SFMarker_Text"],
                ['orthm', "SFMarker_OrthographicMorph"],
                ['morph', "SFMarker_Morpheme"],
                ['gloss', "SFMarker_Gloss"],
                ['pos',   "SFMarker_POS"],
                ['ft',    "SFMarker_FreeTxln"]]

    defaultTags = {'ref'   : "ref",
                   'orth'  : "tor",
                   'text'  : "tx",
                   'orthm' : "mor",
                   'morph' : "mb",
                   'gloss' : "ge",
                   'pos'   : "ps",
                   'ft'    : "ft"}

class PhonologyTags(FieldTags):
    tagVars  = [['phonemic', "SFMarker_Phonemic"],
                ['phonetic', "SFMarker_Phonetic"],
                ['gloss'   , "SFMarker_Gloss"],
                ['ref'     , "SFMarker_RefNum"]]

    defaultTags = {'phonemic' : "phm",
                   'phonetic' : "pht",
                   'gloss'    : "ge",
                   'ref'      : "ref"}

#-------------------------------------------------------------------------------
# End of FieldTags.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgGramSettings.py
#-------------------------------------------------------------------------------



def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.DlgGramSettings")
    logger.debug("----ShowDlg()----------------------------------------------")
    unoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgGramSettings(unoObjs, logger)
    dlg.showDlg()

class DlgGramSettings(XActionListener, XItemListener, unohelper.Base):
    """The dialog implementation."""

    def __init__(self, unoObjs, logger):
        self.unoObjs   = unoObjs
        self.logger    = logger
        USERVAR_PREFIX = "LTg_"  # for LinguisticTools Grammar variables
        self.userVars  = UserVars(USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox    = MessageBox(unoObjs)
        self.fileItems = FileItemList(
                         LingExFileItem, self.unoObjs,
                         self.userVars)

    def showDlg(self):
        self.logger.debug("showDlg BEGIN")
        dlg = None
        try:
            dlg = self.unoObjs.dlgprov.createDialog(
                  "vnd.sun.star.script:LingToolsBasic.DlgGrammarSettings"
                  "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not create dialog.")
            return
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.chkOrthoTextLine     = getControl(dlg,
                                        "chkOrthoTextLine")
            self.chkTextLine          = getControl(dlg, "chkTextLine")
            self.chkOrthoMorphLine    = getControl(dlg,
                                        "chkOrthMorphLine")
            self.chkMorphLine         = getControl(dlg, "ChkMorphLine")
            self.chkMorphsSeparate    = getControl(dlg,
                                        "chkMorphemesSeparateCols")
            self.chkPOS_Line          = getControl(dlg, "ChkPOS_Line")
            self.chkFT_inQuotes       = getControl(dlg, "chkFT_inQuotes")
            self.chkPOS_aboveGloss    = getControl(dlg,
                                        "chkPOS_aboveGloss")
            self.chkNumbering         = getControl(dlg,
                                        "chkInsertNumbering")
            self.chkOuterTable        = getControl(dlg, "chkOuterTable")
            self.listboxFiles         = getControl(dlg, "ListboxFiles")
            self.txtPrefix            = getControl(dlg, "TxtRefPrefix")
            txtNumColWidth            = getControl(dlg, "TxtNumColWidth")
            self.lblNumberingColWidth = getControl(dlg, "lblNumColWidth")
            self.optionTables         = getControl(dlg,
                                        "OptionMethodTables")
            self.optionFrames         = getControl(dlg,
                                        "OptionMethodFrames")
            btnFileAdd                = getControl(dlg, "BtnFileAdd")
            btnFileRemove             = getControl(dlg, "BtnFileRemove")
            btnFileUpdate             = getControl(dlg, "BtnFileUpdate")
            btnOk                     = getControl(dlg, "BtnOk")
            btnCancel                 = getControl(dlg, "BtnCancel")
        except LogicError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        ## Initialize checkboxes

        self.logger.debug("Initializing checkboxes")
        ctrls = self.getControlVarList()
        for ctrl in ctrls:
            control, varname = ctrl
            if not self.userVars.isEmpty(varname):
                ## TESTME: does setting value to e.g. 5 make it crash?
                control.setState(self.userVars.getInt(varname))

        ## Initialize list of files

        self.logger.debug("Initializing list of files")
        self.fileItems.loadFromUserVars()
        stringList = self.fileItems.getItemTextList()
        self.listboxFiles.addItems(tuple(stringList), 0)
        self.listboxFiles.addItemListener(self) # calls itemStateChanged

        ## Numbering column width

        self.logger.debug("Numbering column width")
        varname = "NumberingColWidth"
        if self.userVars.isEmpty(varname):
            defaultCtrlText = "7"
            self.userVars.set(varname, defaultCtrlText)
            self.prevNumberingColWidth = int(defaultCtrlText)
        else:
            self.prevNumberingColWidth = self.userVars.getInt(varname)
        txtNumColWidth.setText(self.prevNumberingColWidth)
        self.txtNumberingColWidth = txtNumColWidth

        ## Hidden options

        varname = "ComparisonDoc"
        if self.userVars.isEmpty(varname):
            self.userVars.set(varname, "1") # default is True

        varname = "TableBottomMargin"
        if self.userVars.isEmpty(varname):
            self.userVars.set(varname, "0.13")

        ## Output method

        method = self.userVars.get("Method")
        if method == "tables":
            self.optionTables.setState(1)   # set to selected

        ## Enabling and disabling

        self.enableDisable()

        self.chkMorphLine.addItemListener(self) # calls itemStateChanged
        self.chkPOS_Line.addItemListener(self)
        self.optionTables.addItemListener(self)
        self.optionFrames.addItemListener(self)
        self.chkOuterTable.addItemListener(self)

        ## Buttons

        self.logger.debug("Adding listeners for buttons")
        btnFileAdd.setActionCommand("FileAdd")
        btnFileAdd.addActionListener(self)
        btnFileRemove.setActionCommand("FileRemove")
        btnFileRemove.addActionListener(self)
        btnFileUpdate.setActionCommand("FileUpdate")
        btnFileUpdate.addActionListener(self)

        btnOk.setActionCommand("UpdateSettings")
        btnOk.addActionListener(self)
        btnCancel.setActionCommand("Cancel")
        btnCancel.addActionListener(self)

        ## Finish creating dialog

        self.logger.debug("Finishing dialog creation")

        self.dlgClose = dlg.endExecute
        dlg.execute()
        dlg.dispose()

    def getControlVarList(self):
        return [(self.chkOrthoTextLine,   "ShowOrthoTextLine"),
                (self.chkTextLine,        "ShowText"),
                (self.chkOrthoMorphLine,  "ShowOrthoMorphLine"),
                (self.chkMorphLine,       "ShowMorphBreaks"),
                (self.chkMorphsSeparate,  "SeparateMorphColumns"),
                (self.chkPOS_Line,        "ShowPartOfSpeech"),
                (self.chkFT_inQuotes,     "FreeTransInQuotes"),
                (self.chkPOS_aboveGloss,  "POS_AboveGloss"),
                (self.chkNumbering,       "InsertNumbering"),
                (self.chkOuterTable,      "MakeOuterTable")]

    def itemStateChanged(self, unused_itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        self.logger.debug("itemStateChanged BEGIN")
        self.enableDisable()

        ## Handle selected list item
        itemPos  = self.listboxFiles.getSelectedItemPos()
        if itemPos == None or itemPos < 0:
            return
        self.logger.debug("Item " + str(itemPos) + " selected.")
        fileItem = self.fileItems.getItem(itemPos)
        self.logger.debug("Filepath " + fileItem.filepath)
        self.txtPrefix.setText(fileItem.prefix)

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        if self.chkMorphLine.getState() == 1:
            self.chkMorphsSeparate.getModel().Enabled = True
            self.chkOrthoMorphLine.getModel().Enabled = True
        else:
            self.chkMorphsSeparate.getModel().Enabled = False
            self.chkOrthoMorphLine.getModel().Enabled = False

        if self.chkOuterTable.getState() == 1 or \
            self.optionTables.getState() == 1:
            self.txtNumberingColWidth.getModel().Enabled = True
            self.lblNumberingColWidth.getModel().Enabled = True
        else:
            self.txtNumberingColWidth.getModel().Enabled = False
            self.lblNumberingColWidth.getModel().Enabled = False

        if self.chkPOS_Line.getState() == 1:
            self.chkPOS_aboveGloss.getModel().Enabled = True
        else:
            self.chkPOS_aboveGloss.getModel().Enabled = False

    def actionPerformed(self, event):
        self.logger.debug("An action happened: " + event.ActionCommand)

        if event.ActionCommand == "FileAdd":
            self.logger.debug("FileAdd begin")
            filepath = showFilePicker(self.unoObjs)
            if filepath != "":
                newItem          = LingExFileItem()
                newItem.filepath = filepath
                itemtext         = newItem.toItemText()
                self.logger.debug("Adding item text " + itemtext)
                success = self.fileItems.addItem(newItem)
                if not success: return
                self.logger.debug("Successfully added.")

                count = self.listboxFiles.getItemCount()
                self.listboxFiles.removeItems(0, count)
                stringList = self.fileItems.getItemTextList()
                self.listboxFiles.addItems(tuple(stringList), 0)
                self.listboxFiles.selectItem(newItem.toItemText(), True)

        elif event.ActionCommand == "FileRemove":
            self.logger.debug("FileRemove begin")
            itemPos = self.listboxFiles.getSelectedItemPos()
            if itemPos == None or itemPos < 0:
                if self.listboxFiles.getItemCount() == 1:
                    itemPos = 0
                else:
                    self.msgbox.display("Please select a file in the list.")
                    return
            self.logger.debug("Removing item at " + str(itemPos))
            self.fileItems.deleteItem(itemPos)
            self.listboxFiles.removeItems(itemPos, 1)

            ## Select the next item

            selItemPos = itemPos
            if selItemPos > self.listboxFiles.getItemCount() - 1:
                selItemPos = self.listboxFiles.getItemCount() - 1
            if selItemPos >= 0:
                self.listboxFiles.selectItemPos(selItemPos, True)
            else:
                ## The list is empty. Clear the text field.
                self.txtPrefix.setText("")
            self.logger.debug("FileRemove end")

        elif event.ActionCommand == "FileUpdate":
            self.logger.debug("FileUpdate begin")
            itemPos  = self.listboxFiles.getSelectedItemPos()
            if itemPos == None or itemPos < 0:
                if self.listboxFiles.getItemCount() == 1:
                    itemPos = 0
                else:
                    self.msgbox.display("Please select a file in the list.")
                    return
            newItem          = LingExFileItem()
            newItem.filepath = self.fileItems.getItem(itemPos).filepath
            newItem.prefix   = self.txtPrefix.getText()
            # remove any spaces
            newItem.prefix   = re.sub(r"\s", r"", newItem.prefix)
            self.fileItems.updateItem(itemPos, newItem)

            self.logger.debug("Removing item at " + str(itemPos))
            self.listboxFiles.removeItems(itemPos, 1)
            add_at_index = itemPos
            self.logger.debug("Adding item at " + str(add_at_index))
            self.listboxFiles.addItem(newItem.toItemText(), add_at_index)
            self.listboxFiles.selectItemPos(add_at_index, True)
            self.logger.debug("FileUpdate end")

        elif event.ActionCommand == "UpdateSettings":
            self.logger.debug("UpdateSettings begin")
            try:
                self.updateSettings()
                self.dlgClose()
            except ChoiceProblem as exc:
                self.msgbox.display(exc.msg, exc.msg_args)

        elif event.ActionCommand == "Cancel":
            self.logger.debug("Action command was Cancel")
            self.dlgClose()

    def updateSettings(self):
        """
        Get settings from form and update user variables and
        document settings.
        Returns True if ok.
        """
        userVars = self.userVars # shorthand variable name

        ## Set list of files

        self.fileItems.setUserVars()

        ## Save checkbox values

        ctrls = self.getControlVarList()
        for ctrl in ctrls:
            control, varname = ctrl
            state = control.getState() # 0 not checked, 1 checked
            userVars.set(varname, str(state))

        ## Option buttons

        state = self.optionTables.getState()
        if state == 1:  # selected
            userVars.set("Method", "tables")
        else:
            userVars.set("Method", "frames")

        ## Modify document settings

        styles = GrammarStyles(self.unoObjs, self.userVars)
        styles.createStyles()
        unused = GrammarTags(self.userVars) # set tag names 

        ctrlText = self.txtNumberingColWidth.getText()
        styles.resizeNumberingCol(ctrlText, self.prevNumberingColWidth)

#-------------------------------------------------------------------------------
# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of DlgGramSettings.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgGramSettings_test.py
#-------------------------------------------------------------------------------




class DlgGramSettingsTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.logger = logging.getLogger("lingt.TestGramSettings")
        modifyClass_showDlg(DlgGramSettings)

    @classmethod
    def setUpClass(cls):
        unoObjs = UnoObjs(getContext(), loadDocObjs=False)
        blankWriterDoc(unoObjs)

    def setUp(self):
        self.setUpClass()
        self.logger.debug("DlgGramSettingsTestCase setUp()")
        self.unoObjs   = unoObjsForCurrentDoc()
        USERVAR_PREFIX = "LTg_"  # for LinguisticTools Grammar variables
        self.userVars  = UserVars(
                         USERVAR_PREFIX, self.unoObjs.document, self.logger)
        self.dlg       = DlgGramSettings(self.unoObjs, self.logger)

    def test1_enableDisable(self):
        # For this test, dialog should be set to its default settings.
        def useDialog(selfNew):
            pass
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.enableDisable()
        self.assertEqual(self.dlg.chkMorphsSeparate.getModel().Enabled, True)
        self.assertEqual(self.dlg.chkPOS_aboveGloss.getModel().Enabled, False)

    def test2_enableDisable(self):
        def useDialog(selfNew):
            selfNew.chkMorphLine.setState(0)
            selfNew.chkPOS_Line.setState(1)
            selfNew.chkOuterTable.setState(0)
            selfNew.optionTables.setState(0)
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.enableDisable()
        self.assertEqual(self.dlg.chkMorphLine.getState(), 0)
        self.assertEqual(self.dlg.chkMorphLine.getModel().Enabled, True)
        self.assertEqual(self.dlg.chkMorphsSeparate.getModel().Enabled, False)
        self.assertEqual(self.dlg.chkPOS_aboveGloss.getModel().Enabled, True)
        self.assertEqual(
            self.dlg.txtNumberingColWidth.getModel().Enabled, False)
        self.assertEqual(
            self.dlg.lblNumberingColWidth.getModel().Enabled, False)

    def test3_enableDisable(self):
        def useDialog(selfNew):
            selfNew.chkMorphLine.setState(1)
            selfNew.chkPOS_Line.setState(0)
            selfNew.chkOuterTable.setState(1)
            selfNew.optionTables.setState(1)
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.dlg.enableDisable()
        self.assertEqual(self.dlg.chkMorphsSeparate.getModel().Enabled, True)
        self.assertEqual(self.dlg.chkPOS_aboveGloss.getModel().Enabled, False)
        self.assertEqual(self.dlg.txtNumberingColWidth.getModel().Enabled, True)
        self.assertEqual(self.dlg.lblNumberingColWidth.getModel().Enabled, True)

    def test4_interlinLines(self):
        def useDialog(selfNew):
            selfNew.chkOrthoTextLine.setState(1)
            selfNew.chkTextLine.setState(0)
            selfNew.chkOrthoMorphLine.setState(1)
            selfNew.chkMorphLine.setState(1)
            selfNew.chkPOS_Line.setState(1)
            selfNew.optionTables.setState(1)
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.assertEqual(self.dlg.chkPOS_Line.getState(), 1)
        self.assertEqual(self.dlg.chkTextLine.getState(), 0)
        self.assertEqual(self.dlg.optionFrames.getState(), 0)
        self.assertEqual(self.dlg.optionTables.getState(), 1)
        self.dlg.actionPerformed(MyActionEvent("UpdateSettings"))
        self.dlg = None
        self.assertEqual(self.userVars.get("Method"), "tables")
        self.assertEqual(self.userVars.getInt("ShowPartOfSpeech"), 1)

    def test5_fileList(self):
        def useDialog(selfNew):
            pass
        DlgGramSettings.useDialog = useDialog
        self.dlg.showDlg()
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 0)
        filepath = os.path.join(TESTDATA_FOLDER, "testText1.xml")
        modifyFilePicker(filepath)
        self.dlg.actionPerformed(MyActionEvent("FileAdd"))
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 1)
        self.assertEqual(self.dlg.fileItems.getCount(), 1)

        filepath = os.path.join(TESTDATA_FOLDER, "testText2.xml")
        modifyFilePicker(filepath)
        self.dlg.actionPerformed(MyActionEvent("FileAdd"))
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 2)
        self.assertEqual(self.dlg.fileItems.getCount(), 2)
        self.assertEqual(self.dlg.listboxFiles.getSelectedItemPos(), 1)

        filepath = os.path.join(TESTDATA_FOLDER, "a_testText3.xml")
        modifyFilePicker(filepath)
        self.dlg.actionPerformed(MyActionEvent("FileAdd"))
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 3)
        self.assertEqual(self.dlg.fileItems.getCount(), 3)
        self.assertEqual(self.dlg.listboxFiles.getSelectedItemPos(), 0)

        self.dlg.listboxFiles.selectItemPos(1, True)    # testText1.xml
        self.dlg.txtPrefix.setText("PREF-")
        self.dlg.actionPerformed(MyActionEvent("FileUpdate"))
        fileItem = self.dlg.fileItems.getItem(1)
        self.assertEqual(fileItem.prefix, "PREF-")
        self.assertEqual(fileItem.toItemText(), "PREF-    testText1.xml")

        self.dlg.actionPerformed(MyActionEvent("FileRemove"))
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 2)
        self.assertEqual(self.dlg.fileItems.getCount(), 2)
        self.assertEqual(self.dlg.listboxFiles.getSelectedItemPos(), 1)
        fileItem = self.dlg.fileItems.getItem(1)
        self.assertEqual(fileItem.toItemText(), "testText2.xml")

        self.dlg.actionPerformed(MyActionEvent("FileRemove"))
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 1)
        self.assertEqual(self.dlg.fileItems.getCount(), 1)
        self.assertEqual(self.dlg.listboxFiles.getSelectedItemPos(), 0)
        fileItem = self.dlg.fileItems.getItem(0)
        self.assertEqual(fileItem.toItemText(), "a_testText3.xml")

        self.dlg.actionPerformed(MyActionEvent("FileRemove"))
        self.assertEqual(self.dlg.listboxFiles.getItemCount(), 0)
        self.assertEqual(self.dlg.fileItems.getCount(), 0)

    def tearDown(self):
        if self.dlg:
            if hasattr(self.dlg, "dlgDispose"):
                self.dlg.dlgDispose()
                self.dlg = None


#-------------------------------------------------------------------------------
# End of DlgGramSettings_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of MessageBox_test.py
#-------------------------------------------------------------------------------




class MessageBoxTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = unoObjsForCurrentDoc()
        self.logger  = logging.getLogger("lingt.TestMessageBox")

    def testMessageBox(self):
        msgbox = MessageBox(self.unoObjs)
        msgbox.display("Hello there\n\n\tHow are you?\nFine, thank you\t",
                       None, 
                       "An unimportant testing message")
        # The constructor should fail if we don't pass any unoObjs.
        self.assertRaises(AttributeError, MessageBox, None)


#-------------------------------------------------------------------------------
# End of MessageBox_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgSpellReplace.py
#-------------------------------------------------------------------------------



class DlgSpellingReplace(XActionListener, XItemListener, unohelper.Base):

    def __init__(self, unoObjs):
        self.unoObjs = unoObjs
        self.logger  = logging.getLogger("lingt.UI.DlgSpellReplace")
        self.msgbox  = MessageBox(unoObjs)

    def makeDlg(self):
        """
        This method will neither show nor destroy the dialog.
        That is left up to the calling code, via
        doExecute() and doDispose().
        """
        self.logger.debug("DlgSpellingReplace.showDlg BEGIN")
        dlg = None
        try:
            dlg = self.unoObjs.dlgprov.createDialog(
                  "vnd.sun.star.script:LingToolsBasic.DlgSpellReplace"
                  "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not create dialog.")
            return
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.listSuggestions = getControl(dlg, "listboxSuggestions")
            self.txtChangeTo     = getControl(dlg, "txtChangeTo")
            self.lblFoundText    = getControl(dlg, "lblFoundText")
            self.lblContext      = getControl(dlg, "lblContext")
            btnAdd               = getControl(dlg, "btnAdd")
            btnChange            = getControl(dlg, "btnChange")
            btnChangeAll         = getControl(dlg, "btnChangeAll")
            btnIgnore            = getControl(dlg, "btnIgnore")
            btnIgnoreAll         = getControl(dlg, "btnIgnoreAll")
            btnClose             = getControl(dlg, "btnClose")
        except LogicError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        self.listSuggestions.addItemListener(self)

        ## Command buttons

        btnAdd.setActionCommand('Add')
        btnAdd.addActionListener(self)
        btnChange.setActionCommand('Change')
        btnChange.addActionListener(self)
        btnChangeAll.setActionCommand('ChangeAll')
        btnChangeAll.addActionListener(self)
        btnIgnore.setActionCommand('Ignore')
        btnIgnore.addActionListener(self)
        btnIgnoreAll.setActionCommand('IgnoreAll')
        btnIgnoreAll.addActionListener(self)
        btnClose.setActionCommand('Close')
        btnClose.addActionListener(self)

        ## Methods to display and close the dialog

        self.doExecute    = dlg.execute
        self.doEndExecute = dlg.endExecute  # hide the dialog and cause the
                                            # execute() method to return
        self.doDispose    = dlg.dispose     # destroy the dialog

    def setContents(self, textFound, suggestions, context):
        self.buttonPressed = ""
        self.changeTo      = textFound
        self.lblFoundText.setText(textFound)
        self.lblContext.setText(context)
        self.txtChangeTo.setText(textFound)

        control = self.listSuggestions
        count   = control.getItemCount()
        control.removeItems(0, count)
        self.logger.debug(repr(suggestions))
        control.addItems(tuple(suggestions), 0)
        self.logger.debug("Finished populating font and styles lists.")

    def itemStateChanged(self, unused_itemEvent):
        """XItemListener event handler."""
        self.logger.debug("itemStateChanged BEGIN")
        self.txtChangeTo.setText(
            self.listSuggestions.getSelectedItem())

    def actionPerformed(self, event):
        """Handle which button was pressed."""
        self.logger.debug("An action happened: " + event.ActionCommand)
        if event.ActionCommand in ['Change', 'ChangeAll']:
            if self.txtChangeTo.getText() == self.lblFoundText.getText():
                self.msgbox.display(
                    "You did not made any changes to the word.")
                return
        self.buttonPressed = event.ActionCommand
        self.changeTo      = self.txtChangeTo.getText()
        self.doEndExecute()   # return from the execute() loop

    def getResults(self):
        return self.buttonPressed, self.changeTo

#-------------------------------------------------------------------------------
# End of DlgSpellReplace.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Letters.py
#-------------------------------------------------------------------------------

try:
    # verify that it is defined
    unichr
except NameError:
    # define it for Python 3
    unichr = chr

class Letters:
    def __init__(self):
        self.LetterIndex = dict()   # useful to look up values by letter
        for script in self.ScriptLetters.keys():
            for lettertype in self.ScriptLetters[script].keys():
                for code in self.ScriptLetters[script][lettertype]:
                    self.LetterIndex[code] = lettertype
        for lettertype in self.OtherKnownLetters:
            for code in self.OtherKnownLetters[lettertype]:
                self.LetterIndex[code] = lettertype

    # used to strip punctuation and numbers from words
    Punctuation = (
        [chr(i)    for i in range(33,47+1)] +
        [chr(i)    for i in range(48,57+1)] +               # digits
        [chr(i)    for i in range(58,64+1)] +
        [chr(i)    for i in range(91,96+1)] +
        [unichr(i) for i in range(0x2018, 0x201F)]) # smart quotes

    Virama = {
        "BENGALI":    u"\u09CD",    # Halant
        "DEVANAGARI": u"\u094D",
        "GUJARATI":   u"\u0ACD",
        "GURMUKHI":   u"\u0A4D",
        "HEBREW":     u"\u05B0",    # Sheva
        "KANNADA":    u"\u0CCD",
        "MALAYALAM":  u"\u0D4D",
        "ORIYA":      u"\u0B4D",
        "TAMIL":      u"\u0BCD",
        "TELUGU":     u"\u0C4D",
    }
    ScriptFonts = {
        "ARABIC":     ["Simplified Arabic", "Traditional Arabic",
                       "Estrangelo Edessa", "Microsoft Uighur",
                       "Arabic Transparent", "Scheherazade", "Andalus",
                       "Geeza Pro", "AlBayan", "Baghdad", "DecoTypeNaskh",
                       "KufiStandarGK", "Nadeem", "TLArabic",
                       "Kalyani", "TAMu_Kalyani", "TAMu_Kadambri",
                       "Kalimati", "TAMu_Maduram"],
        "ARMENIAN":   ["Sylfaen","JF Armenian Serif"],
        "BALINESE":   [],
        "BAMUM":      [],
        "BATAK":      [],
        "BENGALI":    ["Vrinda", "Ani","Jamrul","Likhan","Lohit Bengali",
                       "Mitra Mono",
                       "Mikti Narrow"],
        "BOPOMOFO":   [],
        "BUGINESE":   [],
        "BUHID":      [],
        "CHAM":       [],
        "CHEROKEE":   ["Plantagenet Cherokee"],
        "COPTIC":     ["Sinaiticus"],
        "CYRILLIC":   [],
        "DEVANAGARI": ["Mangal","Annapurna","CDAC-GIST Surekh","Jana Hindi",
                       "Saraswati5", "Xdvng", "Yogesh", "Raghu8",
                       "Raavi","DevanagariMT","Chandas","gargi",
                       "Kalimati","Lohit Hindi","Samanata"],
        "GEORGIAN":   ["JF Georgian Contrast"],
        "GLAGOLITIC": [],
        "GREEK":      [],
        "GUJARATI":   ["Shruti","GujaratiMT","aakar","Lohit Gujarati","padmaa",
                       "Rekha","Saab"],
        "GURMUKHI":   ["Raavi","Gurmukhi",],
        "HANGUL":     ["AppleGothic","#Pilgiche","#Gungseouche",
                       "Baekmuk Batang", "Baekmuk Dotum","Baekmuk Gulim"],
        "HANUNOO":    [],
        "HEBREW":     ["Ezra SIL", "Narkisim", "FrankRuehl","Gisha",
                       "David","Miriam","Levenim MT","Aharoni", "Rod",
                       "ArialHB", "Corsiva", "NewPeninimMT",
                       "Raanana"],
        "HIRAGANA":   [],
        "JAPANESE":   ["Meiryo","Osaka","AquaKanaRegular", "Kochi Mincho"],
        "JAVANESE":   [],
        "KANNADA":    ["Tunga","Kedage","Mallig"],
        "KATAKANA":   [],
        "KHMER":      ["DaunPenh","MoolBoran"],
        "LAO":        [],
        "LATIN":      ["Times New Roman","Arial","Verdana","Courier New"],
        "LEPCHA":     [],
        "LIMBU":      [],
        "LISU":       [],
        "MALAYALAM":  ["Kartika", "Lohit Malayalam"],
        "MANDAIC":    [],
        "MONGOLIAN":  ["Mongolian Baiti"],
        "MYANMAR":    [],
        "NKO":        [],
        "OGHAM":      [],
        "ORIYA":      ["Kalinga", "Lohit Oriya","oriUni","Oriya","Khondi",
                       "Santali"],
        "PUNJABI":    ["Lohit Punjabi"],
        "REJANG":     [],
        "RUNIC":      [],
        "SAMARITAN":  [],
        "SAURASHTRA": [],
        "SINHALA":    ["Iskoola Pota"],
        "SUNDANESE":  [],
        "SYRIAC":     ["Extrangelo Edessa"],
        "TAGALOG":    [],
        "TAGBANWA":   [],
        "TAMIL":      ["Latha","aAvarangal","JanaTamil","ThendraUni",
                       "TheneeUni","Tau Elango Barathi","VaigaiUni",
                       "InaiMathi","Lohit Tamil"],
        "TELUGU":     ["Gautami", "Lohit Telugu", "Pothana2000", "Vemana2000"],
        "THAANA":     ["MV Boli"],
        "THAI":       ["Ayuthaya","Angsana New","Browallia","Cordia New",
                        "Dillenia","Leelawadee",
                        "Eucrosia","Freesia","IrisUPC","JasmineUPC","Jumpa",
                        "KodchiangUPC","LilyUPC","Krungthep","Sathu","Silom",
                        "Thonburi",
                        "Garuda","Loma","Norasi","Purisa"],
        "TIBETAN":    [],
        "TIFINAGH":   [],
    }
    # For fonts that support a number of different scripts
    FontScripts = {
        "Akshar Unicode" :   ["DEVANAGARI","KANNADA",
                              "MALAYALAM","TAMIL","TELUGU"],
        "Arial Unicode MS" : ["ARABIC","ARMENIAN","CYRILLIC","DEVANAGARI",
                              "GEORGIAN","GREEK","GURMUKHI","HEBREW",
                              "JAPANESE","KANNADA","HANGUL","TAMIL","THAI"],
        "DejaVu Serif" :     ["ARABIC","ARMENIAN","CYRILLIC","GREEK","HEBREW",
                              "LAO"],
        "Gentium" :          ["GREEK","CYRILLIC"],
        "FreeSerif" :        ["BENGALI","CYRILLIC","GREEK","DEVANAGARI",
                              "GURMUKHI", "HEBREW","HIRAGANA","KATAKANA",
                              "MALAYALAM","TAMIL", "TELUGU","THAANA","THAI"],
    }

    CaseCapitals = [
            u"\u0041",u"\u0042",u"\u0043",u"\u0044",u"\u0045",u"\u0046",
            u"\u0047",u"\u0048",u"\u0049",u"\u004A",u"\u004B",u"\u004C",
            u"\u004D",u"\u004E",u"\u004F",u"\u0050",u"\u0051",u"\u0052",
            u"\u0053",u"\u0054",u"\u0055",u"\u0056",u"\u0057",u"\u0058",
            u"\u0059",u"\u005A",u"\u00C6",u"\u00D0",u"\u00DE",u"\u014A",
            u"\u018F",u"\u0194",u"\u0196",u"\u01A2",u"\u01A9",u"\u01B1",
            u"\u01B7",u"\u01F6",u"\u01F7",u"\u021C",u"\u0222",u"\u0370",
            u"\u0391",u"\u0392",u"\u0393",u"\u0394",u"\u0395",u"\u0396",
            u"\u0397",u"\u0398",u"\u0399",u"\u039A",u"\u039B",u"\u039C",
            u"\u039D",u"\u039E",u"\u039F",u"\u03A0",u"\u03A1",u"\u03A3",
            u"\u03A4",u"\u03A5",u"\u03A6",u"\u03A7",u"\u03A8",u"\u03A9",
            u"\u03E2",u"\u03E4",u"\u03E6",u"\u03E8",u"\u03EA",u"\u03EC",
            u"\u03EE",u"\u03F7",u"\u03FA",u"\u0401",u"\u0402",u"\u0403",
            u"\u0405",u"\u0407",u"\u0408",u"\u0409",u"\u040A",u"\u040B",
            u"\u040C",u"\u040F",u"\u0410",u"\u0411",u"\u0412",u"\u0413",
            u"\u0414",u"\u0415",u"\u0416",u"\u0417",u"\u0418",u"\u041A",
            u"\u041B",u"\u041C",u"\u041D",u"\u041E",u"\u041F",u"\u0420",
            u"\u0421",u"\u0422",u"\u0423",u"\u0424",u"\u0425",u"\u0426",
            u"\u0427",u"\u0428",u"\u0429",u"\u042B",u"\u042D",u"\u042E",
            u"\u042F",u"\u0460",u"\u0462",u"\u046E",u"\u0470",u"\u0472",
            u"\u0474",u"\u0478",u"\u047E",u"\u0480",u"\u04BA",u"\u04D8",
            u"\u0514",u"\u0516",u"\u0518",u"\u051A",u"\u051C",u"\u0531",
            u"\u0532",u"\u0533",u"\u0534",u"\u0535",u"\u0536",u"\u0537",
            u"\u0538",u"\u0539",u"\u053A",u"\u053B",u"\u053C",u"\u053D",
            u"\u053E",u"\u053F",u"\u0540",u"\u0541",u"\u0542",u"\u0543",
            u"\u0544",u"\u0545",u"\u0546",u"\u0547",u"\u0548",u"\u0549",
            u"\u054A",u"\u054B",u"\u054C",u"\u054D",u"\u054E",u"\u054F",
            u"\u0550",u"\u0551",u"\u0552",u"\u0553",u"\u0554",u"\u0555",
            u"\u0556",u"\u10A0",u"\u10A1",u"\u10A2",u"\u10A3",u"\u10A4",
            u"\u10A5",u"\u10A6",u"\u10A7",u"\u10A8",u"\u10A9",u"\u10AA",
            u"\u10AB",u"\u10AC",u"\u10AD",u"\u10AE",u"\u10AF",u"\u10B0",
            u"\u10B1",u"\u10B2",u"\u10B3",u"\u10B4",u"\u10B5",u"\u10B6",
            u"\u10B7",u"\u10B8",u"\u10B9",u"\u10BA",u"\u10BB",u"\u10BC",
            u"\u10BD",u"\u10BE",u"\u10BF",u"\u10C0",u"\u10C1",u"\u10C2",
            u"\u10C3",u"\u10C4",u"\u10C5",u"\u2C00",u"\u2C01",u"\u2C02",
            u"\u2C03",u"\u2C04",u"\u2C05",u"\u2C06",u"\u2C07",u"\u2C08",
            u"\u2C09",u"\u2C0B",u"\u2C0C",u"\u2C0D",u"\u2C0E",u"\u2C0F",
            u"\u2C10",u"\u2C11",u"\u2C12",u"\u2C13",u"\u2C14",u"\u2C15",
            u"\u2C16",u"\u2C17",u"\u2C18",u"\u2C19",u"\u2C1A",u"\u2C1B",
            u"\u2C1C",u"\u2C1D",u"\u2C1E",u"\u2C1F",u"\u2C20",u"\u2C21",
            u"\u2C23",u"\u2C26",u"\u2C2A",u"\u2C2B",u"\u2C2C",u"\u2C6D",
            u"\u2C80",u"\u2C82",u"\u2C84",u"\u2C86",u"\u2C88",u"\u2C8A",
            u"\u2C8C",u"\u2C8E",u"\u2C90",u"\u2C92",u"\u2C94",u"\u2C96",
            u"\u2C98",u"\u2C9A",u"\u2C9C",u"\u2C9E",u"\u2CA0",u"\u2CA2",
            u"\u2CA4",u"\u2CA6",u"\u2CA8",u"\u2CAA",u"\u2CAC",u"\u2CAE",
            u"\u2CB0",u"\u2CC0",u"\uA640",u"\uA642",u"\uA646",u"\uA648",
            u"\uA65E",u"\uA680",u"\uA682",u"\uA684",u"\uA686",u"\uA688",
            u"\uA68C",u"\uA68E",u"\uA690",u"\uA692",u"\uA694",u"\uA696",
            u"\uA726",u"\uA728",u"\uA72A",u"\uA72C",u"\uA732",u"\uA734",
            u"\uA736",u"\uA738",u"\uA73C",u"\uA74E",u"\uA760",u"\uA768",
            u"\uA76A",u"\uA76C",u"\uA76E",u"\uA78B"    ]

    # lower case equivalent of CaseCapital at same index
    CaseLower = [
            u"\u0061",u"\u0062",u"\u0063",u"\u0064",u"\u0065",u"\u0066",
            u"\u0067",u"\u0068",u"\u0069",u"\u006A",u"\u006B",u"\u006C",
            u"\u006D",u"\u006E",u"\u006F",u"\u0070",u"\u0071",u"\u0072",
            u"\u0073",u"\u0074",u"\u0075",u"\u0076",u"\u0077",u"\u0078",
            u"\u0079",u"\u007A",u"\u00E6",u"\u00F0",u"\u00FE",u"\u014B",
            u"\u0259",u"\u0263",u"\u0269",u"\u01A3",u"\u0283",u"\u028A",
            u"\u0292",u"\u0195",u"\u01BF",u"\u021D",u"\u0223",u"\u0371",
            u"\u03B1",u"\u03B2",u"\u03B3",u"\u03B4",u"\u03B5",u"\u03B6",
            u"\u03B7",u"\u03B8",u"\u03B9",u"\u03BA",u"\u03BB",u"\u03BC",
            u"\u03BD",u"\u03BE",u"\u03BF",u"\u03C0",u"\u03C1",u"\u03C3",
            u"\u03C4",u"\u03C5",u"\u03C6",u"\u03C7",u"\u03C8",u"\u03C9",
            u"\u03E3",u"\u03E5",u"\u03E7",u"\u03E9",u"\u03EB",u"\u03ED",
            u"\u03EF",u"\u03F8",u"\u03FB",u"\u0451",u"\u0452",u"\u0453",
            u"\u0455",u"\u0457",u"\u0458",u"\u0459",u"\u045A",u"\u045B",
            u"\u045C",u"\u045F",u"\u0430",u"\u0431",u"\u0432",u"\u0433",
            u"\u0434",u"\u0435",u"\u0436",u"\u0437",u"\u0438",u"\u043A",
            u"\u043B",u"\u043C",u"\u043D",u"\u043E",u"\u043F",u"\u0440",
            u"\u0441",u"\u0442",u"\u0443",u"\u0444",u"\u0445",u"\u0446",
            u"\u0447",u"\u0448",u"\u0449",u"\u044B",u"\u044D",u"\u044E",
            u"\u044F",u"\u0461",u"\u0463",u"\u046F",u"\u0471",u"\u0473",
            u"\u0475",u"\u0479",u"\u047F",u"\u0481",u"\u04BB",u"\u04D9",
            u"\u0515",u"\u0517",u"\u0519",u"\u051B",u"\u051D",u"\u0561",
            u"\u0562",u"\u0563",u"\u0564",u"\u0565",u"\u0566",u"\u0567",
            u"\u0568",u"\u0569",u"\u056A",u"\u056B",u"\u056C",u"\u056D",
            u"\u056E",u"\u056F",u"\u0570",u"\u0571",u"\u0572",u"\u0573",
            u"\u0574",u"\u0575",u"\u0576",u"\u0577",u"\u0578",u"\u0579",
            u"\u057A",u"\u057B",u"\u057C",u"\u057D",u"\u057E",u"\u057F",
            u"\u0580",u"\u0581",u"\u0582",u"\u0583",u"\u0584",u"\u0585",
            u"\u0586",u"\u2D00",u"\u2D01",u"\u2D02",u"\u2D03",u"\u2D04",
            u"\u2D05",u"\u2D06",u"\u2D07",u"\u2D08",u"\u2D09",u"\u2D0A",
            u"\u2D0B",u"\u2D0C",u"\u2D0D",u"\u2D0E",u"\u2D0F",u"\u2D10",
            u"\u2D11",u"\u2D12",u"\u2D13",u"\u2D14",u"\u2D15",u"\u2D16",
            u"\u2D17",u"\u2D18",u"\u2D19",u"\u2D1A",u"\u2D1B",u"\u2D1C",
            u"\u2D1D",u"\u2D1E",u"\u2D1F",u"\u2D20",u"\u2D21",u"\u2D22",
            u"\u2D23",u"\u2D24",u"\u2D25",u"\u2C30",u"\u2C31",u"\u2C32",
            u"\u2C33",u"\u2C34",u"\u2C35",u"\u2C36",u"\u2C37",u"\u2C38",
            u"\u2C39",u"\u2C3B",u"\u2C3C",u"\u2C3D",u"\u2C3E",u"\u2C3F",
            u"\u2C40",u"\u2C41",u"\u2C42",u"\u2C43",u"\u2C44",u"\u2C45",
            u"\u2C46",u"\u2C47",u"\u2C48",u"\u2C49",u"\u2C4A",u"\u2C4B",
            u"\u2C4C",u"\u2C4D",u"\u2C4E",u"\u2C4F",u"\u2C50",u"\u2C51",
            u"\u2C53",u"\u2C56",u"\u2C5A",u"\u2C5B",u"\u2C5C",u"\u0251",
            u"\u2C81",u"\u2C83",u"\u2C85",u"\u2C87",u"\u2C89",u"\u2C8B",
            u"\u2C8D",u"\u2C8F",u"\u2C91",u"\u2C93",u"\u2C95",u"\u2C97",
            u"\u2C99",u"\u2C9B",u"\u2C9D",u"\u2C9F",u"\u2CA1",u"\u2CA3",
            u"\u2CA5",u"\u2CA7",u"\u2CA9",u"\u2CAB",u"\u2CAD",u"\u2CAF",
            u"\u2CB1",u"\u2CC1",u"\uA641",u"\uA643",u"\uA647",u"\uA649",
            u"\uA65F",u"\uA681",u"\uA683",u"\uA685",u"\uA687",u"\uA689",
            u"\uA68D",u"\uA68F",u"\uA691",u"\uA693",u"\uA695",u"\uA697",
            u"\uA727",u"\uA729",u"\uA72B",u"\uA72D",u"\uA733",u"\uA735",
            u"\uA737",u"\uA739",u"\uA73D",u"\uA74F",u"\uA761",u"\uA769",
            u"\uA76B",u"\uA76D",u"\uA76F",u"\uA78C"    ]

    ScriptLetters = {
        "ARABIC": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u0627",u"\u0648",u"\u06CC"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0621",u"\u0628",u"\u062A",u"\u062B",u"\u062C",u"\u062D",
                u"\u062E",u"\u062F",u"\u0630",u"\u0631",u"\u0632",u"\u0633",
                u"\u0634",u"\u0635",u"\u0636",u"\u0637",u"\u0638",u"\u0639",
                u"\u063A",u"\u0641",u"\u0642",u"\u0643",u"\u0644",u"\u0645",
                u"\u0646",u"\u0647",u"\u064A"],
            "WF_Consonants" : [],
        },
        "ARMENIAN": {
            "WI_Vowels" : [
                u"\u0545"],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u0575"],
            "WI_Consonants" : [
                u"\u0532",u"\u0533",u"\u0534",u"\u0535",u"\u0536",u"\u0537",
                u"\u0538",u"\u0539",u"\u053A",u"\u053B",u"\u053C",u"\u053D",
                u"\u053E",u"\u053F",u"\u0540",u"\u0541",u"\u0542",u"\u0543",
                u"\u0544",u"\u0546",u"\u0547",u"\u0548",u"\u0549",u"\u054A",
                u"\u054B",u"\u054C",u"\u054D",u"\u054E",u"\u054F",u"\u0550",
                u"\u0551",u"\u0552",u"\u0553",u"\u0554",u"\u0555",u"\u0556"],
            "AnyConsonants" : [
                u"\u0562",u"\u0563",u"\u0564",u"\u0565",u"\u0566",u"\u0567",
                u"\u0568",u"\u0569",u"\u056A",u"\u056B",u"\u056C",u"\u056D",
                u"\u056E",u"\u056F",u"\u0570",u"\u0571",u"\u0572",u"\u0573",
                u"\u0574",u"\u0576",u"\u0577",u"\u0578",u"\u0579",u"\u057A",
                u"\u057B",u"\u057C",u"\u057D",u"\u057E",u"\u057F",u"\u0580",
                u"\u0581",u"\u0582",u"\u0583",u"\u0584",u"\u0585",u"\u0586"],
            "WF_Consonants" : [],
        },
        "BALINESE": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1B35",u"\u1B36",u"\u1B38",u"\u1B3E",u"\u1B42"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1B05",u"\u1B07",u"\u1B09",u"\u1B0F",u"\u1B10",u"\u1B11",
                u"\u1B13",u"\u1B15",u"\u1B17",u"\u1B18",u"\u1B1A",u"\u1B1C",
                u"\u1B22",u"\u1B24",u"\u1B26",u"\u1B27",u"\u1B29",u"\u1B2B",
                u"\u1B2C",u"\u1B2D",u"\u1B2E",u"\u1B2F",u"\u1B32",u"\u1B33"],
            "WF_Consonants" : [],
        },
        "BAMUM": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\uA6A0",u"\uA6A2",u"\uA6A4",u"\uA6A7",u"\uA6A9"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\uA6A1",u"\uA6A3",u"\uA6A5",u"\uA6A6",u"\uA6A8",u"\uA6AA",
                u"\uA6AB",u"\uA6AC",u"\uA6AD",u"\uA6AE",u"\uA6AF",u"\uA6B0",
                u"\uA6B1",u"\uA6B2",u"\uA6B3",u"\uA6B4",u"\uA6B5",u"\uA6B6",
                u"\uA6B7",u"\uA6B8",u"\uA6B9",u"\uA6BA",u"\uA6BB",u"\uA6BC",
                u"\uA6BD",u"\uA6BE",u"\uA6BF",u"\uA6C0",u"\uA6C1",u"\uA6C2",
                u"\uA6C3",u"\uA6C4",u"\uA6C5",u"\uA6C6",u"\uA6C7",u"\uA6C8",
                u"\uA6C9",u"\uA6CA",u"\uA6CB",u"\uA6CC",u"\uA6CD",u"\uA6CE",
                u"\uA6CF",u"\uA6D0",u"\uA6D1",u"\uA6D2",u"\uA6D3",u"\uA6D4",
                u"\uA6D5",u"\uA6D6",u"\uA6D7",u"\uA6D8",u"\uA6D9",u"\uA6DA",
                u"\uA6DB",u"\uA6DC",u"\uA6DD",u"\uA6DE",u"\uA6DF",u"\uA6E0",
                u"\uA6E1",u"\uA6E2",u"\uA6E3",u"\uA6E4",u"\uA6E5",u"\uA6E6",
                u"\uA6E7",u"\uA6E8",u"\uA6E9",u"\uA6EA",u"\uA6EB",u"\uA6EC",
                u"\uA6ED",u"\uA6EE",u"\uA6EF"],
            "WF_Consonants" : [],
        },
        "BATAK": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1BE7",u"\u1BE9",u"\u1BEA",u"\u1BEC",u"\u1BEE"],
            "AnyVowels" : [
                u"\u1BC0",u"\u1BE4",u"\u1BE5"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1BC2",u"\u1BC5",u"\u1BC7",u"\u1BC9",u"\u1BCB",u"\u1BCE",
                u"\u1BD0",u"\u1BD1",u"\u1BD2",u"\u1BD4",u"\u1BD8",u"\u1BDB",
                u"\u1BDD",u"\u1BDE",u"\u1BE0",u"\u1BE1",u"\u1BE2",u"\u1BE3"],
            "WF_Consonants" : [],
        },
        "BENGALI": {
            "WI_Vowels" : [
                u"\u0985",u"\u0986",u"\u0987",u"\u0988",u"\u0989",u"\u098A",
                u"\u098F",u"\u0990",u"\u0993",u"\u0994"],
            "DepVowels" : [
                u"\u09BE",u"\u09BF",u"\u09C0",u"\u09C1",u"\u09C2",u"\u09C7",
                u"\u09C8",u"\u09CB",u"\u09CC"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0995",u"\u0996",u"\u0997",u"\u0998",u"\u0999",u"\u099A",
                u"\u099B",u"\u099C",u"\u099D",u"\u099E",u"\u099F",u"\u09A0",
                u"\u09A1",u"\u09A2",u"\u09A3",u"\u09A4",u"\u09A5",u"\u09A6",
                u"\u09A7",u"\u09A8",u"\u09AA",u"\u09AB",u"\u09AC",u"\u09AD",
                u"\u09AE",u"\u09AF",u"\u09B0",u"\u09B2",u"\u09B6",u"\u09B7",
                u"\u09B8",u"\u09B9"],
            "WF_Consonants" : [],
        },
        "BOPOMOFO": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u311A",u"\u311B",u"\u311C",u"\u311E",u"\u311F",u"\u3120",
                u"\u3121",u"\u3127",u"\u3128",u"\u3129",u"\u31A4",u"\u31A6"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u3105",u"\u3106",u"\u3107",u"\u3108",u"\u3109",u"\u310A",
                u"\u310B",u"\u310C",u"\u310D",u"\u310E",u"\u310F",u"\u3110",
                u"\u3111",u"\u3112",u"\u3113",u"\u3114",u"\u3115",u"\u3116",
                u"\u3117",u"\u3118",u"\u3119",u"\u311D",u"\u3122",u"\u3123",
                u"\u3124",u"\u3125",u"\u3126",u"\u312A",u"\u312B",u"\u312C",
                u"\u312D",u"\u31A0",u"\u31A1",u"\u31A2",u"\u31A3",u"\u31A5",
                u"\u31A7",u"\u31A8",u"\u31A9",u"\u31AA",u"\u31AB",u"\u31AC",
                u"\u31AD",u"\u31AE",u"\u31AF",u"\u31B0",u"\u31B1",u"\u31B2",
                u"\u31B3",u"\u31B8",u"\u31B9",u"\u31BA"],
            "WF_Consonants" : [],
        },
        "BUGINESE": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1A17",u"\u1A18",u"\u1A19",u"\u1A1A",u"\u1A1B"],
            "AnyVowels" : [
                u"\u1A15"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1A00",u"\u1A01",u"\u1A02",u"\u1A03",u"\u1A04",u"\u1A05",
                u"\u1A06",u"\u1A07",u"\u1A08",u"\u1A09",u"\u1A0A",u"\u1A0B",
                u"\u1A0C",u"\u1A0D",u"\u1A0E",u"\u1A0F",u"\u1A10",u"\u1A11",
                u"\u1A12",u"\u1A13",u"\u1A14",u"\u1A16"],
            "WF_Consonants" : [],
        },
        "BUHID": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1752",u"\u1753"],
            "AnyVowels" : [
                u"\u1740",u"\u1741",u"\u1742"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1743",u"\u1744",u"\u1745",u"\u1746",u"\u1747",u"\u1748",
                u"\u1749",u"\u174A",u"\u174B",u"\u174C",u"\u174D",u"\u174E",
                u"\u174F",u"\u1750",u"\u1751"],
            "WF_Consonants" : [],
        },
        "CHAM": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\uAA29",u"\uAA2A",u"\uAA2B",u"\uAA2C",u"\uAA2D",u"\uAA2E",
                u"\uAA2F",u"\uAA30",u"\uAA31",u"\uAA32"],
            "AnyVowels" : [
                u"\uAA00",u"\uAA01",u"\uAA02",u"\uAA03",u"\uAA04",u"\uAA05"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\uAA06",u"\uAA07",u"\uAA08",u"\uAA09",u"\uAA0A",u"\uAA0B",
                u"\uAA0C",u"\uAA0D",u"\uAA0E",u"\uAA0F",u"\uAA10",u"\uAA11",
                u"\uAA12",u"\uAA13",u"\uAA14",u"\uAA15",u"\uAA16",u"\uAA17",
                u"\uAA18",u"\uAA19",u"\uAA1A",u"\uAA1B",u"\uAA1C",u"\uAA1D",
                u"\uAA1E",u"\uAA1F",u"\uAA20",u"\uAA21",u"\uAA22",u"\uAA23",
                u"\uAA24",u"\uAA25",u"\uAA26",u"\uAA27",u"\uAA28"],
            "WF_Consonants" : [
                u"\uAA40",u"\uAA41",u"\uAA42",u"\uAA44",u"\uAA45",u"\uAA46",
                u"\uAA47",u"\uAA48",u"\uAA49",u"\uAA4A",u"\uAA4B"],
        },
        "CHEROKEE": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u13A0",u"\u13A1",u"\u13A2",u"\u13A3",u"\u13A4",u"\u13F0",
                u"\u13F1",u"\u13F2",u"\u13F3"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u13A5",u"\u13A6",u"\u13A7",u"\u13A8",u"\u13A9",u"\u13AA",
                u"\u13AB",u"\u13AC",u"\u13AD",u"\u13AE",u"\u13AF",u"\u13B0",
                u"\u13B1",u"\u13B2",u"\u13B3",u"\u13B4",u"\u13B5",u"\u13B6",
                u"\u13B7",u"\u13B8",u"\u13B9",u"\u13BA",u"\u13BB",u"\u13BC",
                u"\u13BD",u"\u13BE",u"\u13BF",u"\u13C0",u"\u13C1",u"\u13C2",
                u"\u13C3",u"\u13C4",u"\u13C5",u"\u13C6",u"\u13C7",u"\u13C8",
                u"\u13C9",u"\u13CA",u"\u13CB",u"\u13CC",u"\u13CD",u"\u13CE",
                u"\u13CF",u"\u13D0",u"\u13D1",u"\u13D2",u"\u13D3",u"\u13D4",
                u"\u13D5",u"\u13D6",u"\u13D7",u"\u13D8",u"\u13D9",u"\u13DA",
                u"\u13DB",u"\u13DC",u"\u13DD",u"\u13DE",u"\u13DF",u"\u13E0",
                u"\u13E1",u"\u13E2",u"\u13E3",u"\u13E4",u"\u13E5",u"\u13E6",
                u"\u13E7",u"\u13E8",u"\u13E9",u"\u13EA",u"\u13EB",u"\u13EC",
                u"\u13ED",u"\u13EE",u"\u13EF",u"\u13F4"],
            "WF_Consonants" : [],
        },
        "COPTIC": {
            "WI_Vowels" : [
                u"\u2C88",u"\u2C9E",u"\u2CA8",u"\u2CB0"],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u2C89",u"\u2C9F",u"\u2CA9",u"\u2CB1"],
            "WI_Consonants" : [
                u"\u03E2",u"\u03E4",u"\u03E6",u"\u03E8",u"\u03EA",u"\u03EC",
                u"\u03EE",u"\u2C80",u"\u2C82",u"\u2C84",u"\u2C86",u"\u2C8A",
                u"\u2C8C",u"\u2C8E",u"\u2C90",u"\u2C92",u"\u2C94",u"\u2C96",
                u"\u2C98",u"\u2C9A",u"\u2C9C",u"\u2CA0",u"\u2CA2",u"\u2CA4",
                u"\u2CA6",u"\u2CAA",u"\u2CAC",u"\u2CAE",u"\u2CC0"],
            "AnyConsonants" : [
                u"\u03E3",u"\u03E5",u"\u03E7",u"\u03E9",u"\u03EB",u"\u03ED",
                u"\u03EF",u"\u2C81",u"\u2C83",u"\u2C85",u"\u2C87",u"\u2C8B",
                u"\u2C8D",u"\u2C8F",u"\u2C91",u"\u2C93",u"\u2C95",u"\u2C97",
                u"\u2C99",u"\u2C9B",u"\u2C9D",u"\u2CA1",u"\u2CA3",u"\u2CA5",
                u"\u2CA7",u"\u2CAB",u"\u2CAD",u"\u2CAF",u"\u2CC1"],
            "WF_Consonants" : [],
        },
        "CYRILLIC": {
            "WI_Vowels" : [
                u"\u0401",u"\u0407",u"\u0410",u"\u0415",u"\u0418",u"\u041E",
                u"\u0423",u"\u042D",u"\u042E"],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u0430",u"\u0435",u"\u0438",u"\u043E",u"\u0443",u"\u044D",
                u"\u044E"],
            "WI_Consonants" : [
                u"\u0402",u"\u0403",u"\u0405",u"\u0408",u"\u0409",u"\u040A",
                u"\u040B",u"\u040C",u"\u040F",u"\u0411",u"\u0412",u"\u0413",
                u"\u0414",u"\u0416",u"\u0417",u"\u041A",u"\u041B",u"\u041C",
                u"\u041D",u"\u041F",u"\u0420",u"\u0421",u"\u0422",u"\u0424",
                u"\u0425",u"\u0426",u"\u0427",u"\u0428",u"\u0429",u"\u042B",
                u"\u042F",u"\uA640",u"\uA642",u"\uA646",u"\uA648",u"\uA65E"],
            "AnyConsonants" : [
                u"\u0431",u"\u0432",u"\u0433",u"\u0434",u"\u0436",u"\u0437",
                u"\u043A",u"\u043B",u"\u043C",u"\u043D",u"\u043F",u"\u0440",
                u"\u0441",u"\u0442",u"\u0444",u"\u0445",u"\u0446",u"\u0447",
                u"\u0448",u"\u0449",u"\u044B",u"\u044F",u"\uA641",u"\uA643",
                u"\uA647",u"\uA649",u"\uA65F"],
            "WF_Consonants" : [],
        },
        "DEVANAGARI": {
            "WI_Vowels" : [
                u"\u0905",u"\u0906",u"\u0907",u"\u0908",u"\u0909",u"\u090A",
                u"\u090F",u"\u0910",u"\u0913",u"\u0914"],
            "DepVowels" : [
                u"\u093E",u"\u093F",u"\u0940",u"\u0941",u"\u0942",u"\u0947",
                u"\u0948",u"\u094B",u"\u094C"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0915",u"\u0916",u"\u0917",u"\u0918",u"\u0919",u"\u091A",
                u"\u091B",u"\u091C",u"\u091D",u"\u091E",u"\u091F",u"\u0920",
                u"\u0921",u"\u0922",u"\u0923",u"\u0924",u"\u0925",u"\u0926",
                u"\u0927",u"\u0928",u"\u092A",u"\u092B",u"\u092C",u"\u092D",
                u"\u092E",u"\u092F",u"\u0930",u"\u0932",u"\u0935",u"\u0936",
                u"\u0937",u"\u0938",u"\u0939"],
            "WF_Consonants" : [],
        },
        "GEORGIAN": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u10D0",u"\u10D1",u"\u10D2",u"\u10D3",u"\u10D4",u"\u10D5",
                u"\u10D6",u"\u10D7",u"\u10D8",u"\u10D9",u"\u10DA",u"\u10DB",
                u"\u10DC",u"\u10DD",u"\u10DE",u"\u10DF",u"\u10E0",u"\u10E1",
                u"\u10E2",u"\u10E3",u"\u10E4",u"\u10E5",u"\u10E6",u"\u10E7",
                u"\u10E8",u"\u10E9",u"\u10EA",u"\u10EB",u"\u10EC",u"\u10ED",
                u"\u10EE",u"\u10EF",u"\u10F0",u"\u10F1",u"\u10F2",u"\u10F3",
                u"\u10F4",u"\u10F5",u"\u10F6",u"\u10F7",u"\u10F8",u"\u10FA"],
            "WF_Consonants" : [],
        },
        "GLAGOLITIC": {
            "WI_Vowels" : [
                u"\u2C0B",u"\u2C23",u"\u2C26"],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u2C3B",u"\u2C53",u"\u2C56"],
            "WI_Consonants" : [
                u"\u2C00",u"\u2C01",u"\u2C02",u"\u2C03",u"\u2C04",u"\u2C05",
                u"\u2C06",u"\u2C07",u"\u2C08",u"\u2C09",u"\u2C0C",u"\u2C0D",
                u"\u2C0E",u"\u2C0F",u"\u2C10",u"\u2C11",u"\u2C12",u"\u2C13",
                u"\u2C14",u"\u2C15",u"\u2C16",u"\u2C17",u"\u2C18",u"\u2C19",
                u"\u2C1A",u"\u2C1B",u"\u2C1C",u"\u2C1D",u"\u2C1E",u"\u2C1F",
                u"\u2C20",u"\u2C21",u"\u2C2A",u"\u2C2B",u"\u2C2C"],
            "AnyConsonants" : [
                u"\u2C30",u"\u2C31",u"\u2C32",u"\u2C33",u"\u2C34",u"\u2C35",
                u"\u2C36",u"\u2C37",u"\u2C38",u"\u2C39",u"\u2C3C",u"\u2C3D",
                u"\u2C3E",u"\u2C3F",u"\u2C40",u"\u2C41",u"\u2C42",u"\u2C43",
                u"\u2C44",u"\u2C45",u"\u2C46",u"\u2C47",u"\u2C48",u"\u2C49",
                u"\u2C4A",u"\u2C4B",u"\u2C4C",u"\u2C4D",u"\u2C4E",u"\u2C4F",
                u"\u2C50",u"\u2C51",u"\u2C5A",u"\u2C5B",u"\u2C5C"],
            "WF_Consonants" : [],
        },
        "GREEK": {
            "WI_Vowels" : [
                u"\u0391",u"\u0392",u"\u0395",u"\u0396",u"\u0397",u"\u0398",
                u"\u0399",u"\u039F",u"\u03A5",u"\u03A9"],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u03B1",u"\u03B2",u"\u03B5",u"\u03B6",u"\u03B7",u"\u03B8",
                u"\u03B9",u"\u03BF",u"\u03C5",u"\u03C9"],
            "WI_Consonants" : [
                u"\u0393",u"\u0394",u"\u039A",u"\u039B",u"\u039C",u"\u039D",
                u"\u039E",u"\u03A0",u"\u03A1",u"\u03A3",u"\u03A4",u"\u03A6",
                u"\u03A7",u"\u03A8"],
            "AnyConsonants" : [
                u"\u03B3",u"\u03B4",u"\u03BA",u"\u03BB",u"\u03BC",u"\u03BD",
                u"\u03BE",u"\u03C0",u"\u03C1",u"\u03C3",u"\u03C4",u"\u03C6",
                u"\u03C7",u"\u03C8"],
            "WF_Consonants" : [
                u"\u03C2"],
        },
        "GUJARATI": {
            "WI_Vowels" : [
                u"\u0A85",u"\u0A86",u"\u0A87",u"\u0A88",u"\u0A89",u"\u0A8A",
                u"\u0A8F",u"\u0A90",u"\u0A93",u"\u0A94"],
            "DepVowels" : [
                u"\u0ABE",u"\u0ABF",u"\u0AC0",u"\u0AC1",u"\u0AC2",u"\u0AC7",
                u"\u0AC8",u"\u0ACB",u"\u0ACC"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0A95",u"\u0A96",u"\u0A97",u"\u0A98",u"\u0A99",u"\u0A9A",
                u"\u0A9B",u"\u0A9C",u"\u0A9D",u"\u0A9E",u"\u0A9F",u"\u0AA0",
                u"\u0AA1",u"\u0AA2",u"\u0AA3",u"\u0AA4",u"\u0AA5",u"\u0AA6",
                u"\u0AA7",u"\u0AA8",u"\u0AAA",u"\u0AAB",u"\u0AAC",u"\u0AAD",
                u"\u0AAE",u"\u0AAF",u"\u0AB0",u"\u0AB2",u"\u0AB3",u"\u0AB5",
                u"\u0AB6",u"\u0AB7",u"\u0AB8",u"\u0AB9"],
            "WF_Consonants" : [],
        },
        "GURMUKHI": {
            "WI_Vowels" : [
                u"\u0A05",u"\u0A06",u"\u0A07",u"\u0A08",u"\u0A09",u"\u0A0A",
                u"\u0A0F",u"\u0A10",u"\u0A13",u"\u0A14"],
            "DepVowels" : [
                u"\u0A3E",u"\u0A3F",u"\u0A40",u"\u0A41",u"\u0A42",u"\u0A47",
                u"\u0A48",u"\u0A4B",u"\u0A4C"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0A15",u"\u0A16",u"\u0A17",u"\u0A18",u"\u0A19",u"\u0A1A",
                u"\u0A1B",u"\u0A1C",u"\u0A1D",u"\u0A1E",u"\u0A1F",u"\u0A20",
                u"\u0A21",u"\u0A22",u"\u0A23",u"\u0A24",u"\u0A25",u"\u0A26",
                u"\u0A27",u"\u0A28",u"\u0A2A",u"\u0A2B",u"\u0A2C",u"\u0A2D",
                u"\u0A2E",u"\u0A2F",u"\u0A30",u"\u0A32",u"\u0A33",u"\u0A35",
                u"\u0A36",u"\u0A38",u"\u0A39"],
            "WF_Consonants" : [],
        },
        "HANGUL": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1161",u"\u1162",u"\u1163",u"\u1164",u"\u1165",u"\u1166",
                u"\u1167",u"\u1168",u"\u1169",u"\u116A",u"\u116B",u"\u116C",
                u"\u116D",u"\u116E",u"\u116F",u"\u1170",u"\u1171",u"\u1172",
                u"\u1173",u"\u1174",u"\u1175",u"\u119E",u"\u11A2"],
            "AnyVowels" : [],
            "WI_Consonants" : [
                u"\u1100",u"\u1101",u"\u1102",u"\u1103",u"\u1104",u"\u1105",
                u"\u1106",u"\u1107",u"\u1108",u"\u1109",u"\u110A",u"\u110B",
                u"\u110C",u"\u110D",u"\u110E",u"\u110F",u"\u1110",u"\u1111",
                u"\u1112",u"\u1114",u"\u1119",u"\u111B",u"\u111D",u"\u112B",
                u"\u112C",u"\u113C",u"\u113D",u"\u113E",u"\u113F",u"\u1140",
                u"\u1147",u"\u114C",u"\u114E",u"\u114F",u"\u1150",u"\u1151",
                u"\u1154",u"\u1155",u"\u1157",u"\u1158",u"\u1159",u"\uA979",
                u"\uA97C"],
            "AnyConsonants" : [],
            "WF_Consonants" : [
                u"\u11A8",u"\u11A9",u"\u11AB",u"\u11AE",u"\u11AF",u"\u11B7",
                u"\u11B8",u"\u11BA",u"\u11BB",u"\u11BC",u"\u11BD",u"\u11BE",
                u"\u11BF",u"\u11C0",u"\u11C1",u"\u11C2",u"\u11D0",u"\u11E2",
                u"\u11E6",u"\u11EB",u"\u11EE",u"\u11F0",u"\u11F4",u"\u11F9",
                u"\u11FF",u"\uD7CD",u"\uD7DD",u"\uD7E0",u"\uD7E6",u"\uD7F9"],
        },
        "HANUNOO": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1732",u"\u1733"],
            "AnyVowels" : [
                u"\u1720",u"\u1721",u"\u1722"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1723",u"\u1724",u"\u1725",u"\u1726",u"\u1727",u"\u1728",
                u"\u1729",u"\u172A",u"\u172B",u"\u172C",u"\u172D",u"\u172E",
                u"\u172F",u"\u1730",u"\u1731"],
            "WF_Consonants" : [],
        },
        "HEBREW": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u05B0",u"\u05B1",u"\u05B2",u"\u05B3",u"\u05B4",u"\u05B5",
                u"\u05B6",u"\u05B7",u"\u05B8",u"\u05B9",u"\u05BB",u"\u05BC",
                u"\u05BD",u"\u05BF"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u05D0",u"\u05D1",u"\u05D2",u"\u05D3",u"\u05D4",u"\u05D5",
                u"\u05D6",u"\u05D7",u"\u05D8",u"\u05D9",u"\u05DB",u"\u05DC",
                u"\u05DE",u"\u05E0",u"\u05E1",u"\u05E2",u"\u05E4",u"\u05E6",
                u"\u05E7",u"\u05E8",u"\u05E9",u"\u05EA"],
            "WF_Consonants" : [
                u"\u05DA",u"\u05DD",u"\u05DF",u"\u05E3",u"\u05E5"],
        },
        "HIRAGANA": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u3042",u"\u3044",u"\u3046",u"\u3048",u"\u304A",u"\u3086",
                u"\u3088"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u304B",u"\u304C",u"\u304D",u"\u304E",u"\u304F",u"\u3050",
                u"\u3051",u"\u3052",u"\u3053",u"\u3054",u"\u3055",u"\u3056",
                u"\u3057",u"\u3058",u"\u3059",u"\u305A",u"\u305B",u"\u305C",
                u"\u305D",u"\u305E",u"\u305F",u"\u3060",u"\u3061",u"\u3062",
                u"\u3064",u"\u3065",u"\u3066",u"\u3067",u"\u3068",u"\u3069",
                u"\u306A",u"\u306B",u"\u306C",u"\u306D",u"\u306E",u"\u306F",
                u"\u3070",u"\u3071",u"\u3072",u"\u3073",u"\u3074",u"\u3075",
                u"\u3076",u"\u3077",u"\u3078",u"\u3079",u"\u307A",u"\u307B",
                u"\u307C",u"\u307D",u"\u307E",u"\u307F",u"\u3080",u"\u3081",
                u"\u3082",u"\u3084",u"\u3089",u"\u308A",u"\u308B",u"\u308C",
                u"\u308D",u"\u308F",u"\u3090",u"\u3091",u"\u3092",u"\u3093",
                u"\u3094"],
            "WF_Consonants" : [],
        },
        "JAVANESE": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\uA9B4",u"\uA9B5",u"\uA9B6",u"\uA9B8",u"\uA9BA",u"\uA9BC"],
            "AnyVowels" : [
                u"\uA984",u"\uA986",u"\uA987",u"\uA988",u"\uA98C",u"\uA98D",
                u"\uA98E"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\uA98F",u"\uA992",u"\uA994",u"\uA995",u"\uA997",u"\uA99A",
                u"\uA99B",u"\uA99D",u"\uA9A0",u"\uA9A2",u"\uA9A4",u"\uA9A5",
                u"\uA9A7",u"\uA9A9",u"\uA9AA",u"\uA9AB",u"\uA9AD",u"\uA9AE",
                u"\uA9B1",u"\uA9B2"],
            "WF_Consonants" : [],
        },
        "KANNADA": {
            "WI_Vowels" : [
                u"\u0C85",u"\u0C86",u"\u0C87",u"\u0C88",u"\u0C89",u"\u0C8A",
                u"\u0C8E",u"\u0C8F",u"\u0C90",u"\u0C92",u"\u0C93",u"\u0C94"],
            "DepVowels" : [
                u"\u0CBE",u"\u0CBF",u"\u0CC0",u"\u0CC1",u"\u0CC2",u"\u0CC6",
                u"\u0CC7",u"\u0CC8",u"\u0CCA",u"\u0CCB",u"\u0CCC"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0C95",u"\u0C96",u"\u0C97",u"\u0C98",u"\u0C99",u"\u0C9A",
                u"\u0C9B",u"\u0C9C",u"\u0C9D",u"\u0C9E",u"\u0C9F",u"\u0CA0",
                u"\u0CA1",u"\u0CA2",u"\u0CA3",u"\u0CA4",u"\u0CA5",u"\u0CA6",
                u"\u0CA7",u"\u0CA8",u"\u0CAA",u"\u0CAB",u"\u0CAC",u"\u0CAD",
                u"\u0CAE",u"\u0CAF",u"\u0CB0",u"\u0CB1",u"\u0CB2",u"\u0CB3",
                u"\u0CB5",u"\u0CB6",u"\u0CB7",u"\u0CB8",u"\u0CB9"],
            "WF_Consonants" : [],
        },
        "KATAKANA": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u30A2",u"\u30A4",u"\u30A6",u"\u30A8",u"\u30AA",u"\u30E6",
                u"\u30E8"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u30AB",u"\u30AC",u"\u30AD",u"\u30AE",u"\u30AF",u"\u30B0",
                u"\u30B1",u"\u30B2",u"\u30B3",u"\u30B4",u"\u30B5",u"\u30B6",
                u"\u30B7",u"\u30B8",u"\u30B9",u"\u30BA",u"\u30BB",u"\u30BC",
                u"\u30BD",u"\u30BE",u"\u30BF",u"\u30C0",u"\u30C1",u"\u30C2",
                u"\u30C4",u"\u30C5",u"\u30C6",u"\u30C7",u"\u30C8",u"\u30C9",
                u"\u30CA",u"\u30CB",u"\u30CC",u"\u30CD",u"\u30CE",u"\u30CF",
                u"\u30D0",u"\u30D1",u"\u30D2",u"\u30D3",u"\u30D4",u"\u30D5",
                u"\u30D6",u"\u30D7",u"\u30D8",u"\u30D9",u"\u30DA",u"\u30DB",
                u"\u30DC",u"\u30DD",u"\u30DE",u"\u30DF",u"\u30E0",u"\u30E1",
                u"\u30E2",u"\u30E4",u"\u30E9",u"\u30EA",u"\u30EB",u"\u30EC",
                u"\u30ED",u"\u30EF",u"\u30F0",u"\u30F1",u"\u30F2",u"\u30F3",
                u"\u30F4",u"\u30F7",u"\u30F8",u"\u30F9",u"\u30FA"],
            "WF_Consonants" : [],
        },
        "KHMER": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u17B6",u"\u17B7",u"\u17B8",u"\u17B9",u"\u17BA",u"\u17BB",
                u"\u17BC",u"\u17BD",u"\u17BE",u"\u17BF",u"\u17C0",u"\u17C1",
                u"\u17C2",u"\u17C3",u"\u17C4",u"\u17C5"],
            "AnyVowels" : [
                u"\u1799"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1780",u"\u1781",u"\u1782",u"\u1783",u"\u1784",u"\u1785",
                u"\u1786",u"\u1787",u"\u1788",u"\u1789",u"\u178A",u"\u178B",
                u"\u178C",u"\u178D",u"\u178E",u"\u178F",u"\u1790",u"\u1791",
                u"\u1792",u"\u1793",u"\u1794",u"\u1795",u"\u1796",u"\u1797",
                u"\u1798",u"\u179A",u"\u179B",u"\u179C",u"\u179D",u"\u179E",
                u"\u179F",u"\u17A0",u"\u17A1",u"\u17A2"],
            "WF_Consonants" : [],
        },
        "LAO": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u0EB0",u"\u0EB2",u"\u0EB3",u"\u0EB4",u"\u0EB5",u"\u0EB6",
                u"\u0EB7",u"\u0EB8",u"\u0EB9",u"\u0EC0",u"\u0EC1",u"\u0EC2",
                u"\u0EC3",u"\u0EC4"],
            "AnyVowels" : [
                u"\u0EA2",u"\u0EAD"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0E81",u"\u0E87",u"\u0E88",u"\u0E8D",u"\u0E94",u"\u0E95",
                u"\u0E99",u"\u0E9A",u"\u0E9B",u"\u0EA1",u"\u0EA7"],
            "WF_Consonants" : [],
        },
        "LATIN": {
            "WI_Vowels" : [
                u"\u0041",u"\u0045",u"\u0049",u"\u004F",u"\u0055"],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u0061",u"\u0065",u"\u0069",u"\u006F",u"\u0075"],
            "WI_Consonants" : [
                u"\u0042",u"\u0043",u"\u0044",u"\u0046",u"\u0047",u"\u0048",
                u"\u004A",u"\u004B",u"\u004C",u"\u004D",u"\u004E",u"\u0050",
                u"\u0051",u"\u0052",u"\u0053",u"\u0054",u"\u0056",u"\u0057",
                u"\u0058",u"\u0059",u"\u005A"],
            "AnyConsonants" : [
                u"\u0062",u"\u0063",u"\u0064",u"\u0066",u"\u0067",u"\u0068",
                u"\u006A",u"\u006B",u"\u006C",u"\u006D",u"\u006E",u"\u0070",
                u"\u0071",u"\u0072",u"\u0073",u"\u0074",u"\u0076",u"\u0077",
                u"\u0078",u"\u0079",u"\u007A"],
            "WF_Consonants" : [],
        },
        "LEPCHA": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1C26",u"\u1C27",u"\u1C28",u"\u1C29",u"\u1C2A",u"\u1C2B",
                u"\u1C2C"],
            "AnyVowels" : [
                u"\u1C23"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1C00",u"\u1C01",u"\u1C02",u"\u1C03",u"\u1C04",u"\u1C05",
                u"\u1C06",u"\u1C07",u"\u1C08",u"\u1C09",u"\u1C0A",u"\u1C0B",
                u"\u1C0C",u"\u1C0D",u"\u1C0E",u"\u1C0F",u"\u1C10",u"\u1C11",
                u"\u1C12",u"\u1C13",u"\u1C14",u"\u1C15",u"\u1C16",u"\u1C17",
                u"\u1C18",u"\u1C19",u"\u1C1A",u"\u1C1B",u"\u1C1C",u"\u1C1D",
                u"\u1C1E",u"\u1C1F",u"\u1C20",u"\u1C21",u"\u1C22",u"\u1C4D",
                u"\u1C4E",u"\u1C4F"],
            "WF_Consonants" : [],
        },
        "LIMBU": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1920",u"\u1921",u"\u1922",u"\u1923",u"\u1924",u"\u1925",
                u"\u1926",u"\u1927",u"\u1928"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1901",u"\u1902",u"\u1903",u"\u1904",u"\u1905",u"\u1906",
                u"\u1907",u"\u1908",u"\u1909",u"\u190A",u"\u190B",u"\u190C",
                u"\u190D",u"\u190E",u"\u190F",u"\u1910",u"\u1911",u"\u1912",
                u"\u1913",u"\u1914",u"\u1915",u"\u1916",u"\u1917",u"\u1918",
                u"\u1919",u"\u191A",u"\u191B",u"\u191C",u"\u1930",u"\u1931",
                u"\u1932",u"\u1933",u"\u1934",u"\u1935",u"\u1936",u"\u1937",
                u"\u1938"],
            "WF_Consonants" : [],
        },
        "LISU": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\uA4EE",u"\uA4EF",u"\uA4F0",u"\uA4F1",u"\uA4F2",u"\uA4F3",
                u"\uA4F4",u"\uA4F5",u"\uA4F7"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\uA4D0",u"\uA4D1",u"\uA4D2",u"\uA4D3",u"\uA4D4",u"\uA4D5",
                u"\uA4D6",u"\uA4D7",u"\uA4D8",u"\uA4D9",u"\uA4DA",u"\uA4DB",
                u"\uA4DC",u"\uA4DD",u"\uA4DE",u"\uA4DF",u"\uA4E0",u"\uA4E1",
                u"\uA4E2",u"\uA4E3",u"\uA4E4",u"\uA4E5",u"\uA4E6",u"\uA4E7",
                u"\uA4E8",u"\uA4E9",u"\uA4EA",u"\uA4EB",u"\uA4EC",u"\uA4ED",
                u"\uA4F6"],
            "WF_Consonants" : [],
        },
        "MALAYALAM": {
            "WI_Vowels" : [
                u"\u0D05",u"\u0D06",u"\u0D07",u"\u0D08",u"\u0D09",u"\u0D0A",
                u"\u0D0E",u"\u0D0F",u"\u0D10",u"\u0D12",u"\u0D13",u"\u0D14"],
            "DepVowels" : [
                u"\u0D3E",u"\u0D3F",u"\u0D40",u"\u0D41",u"\u0D42",u"\u0D46",
                u"\u0D47",u"\u0D48",u"\u0D4A",u"\u0D4B"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0D15",u"\u0D16",u"\u0D17",u"\u0D18",u"\u0D19",u"\u0D1A",
                u"\u0D1B",u"\u0D1C",u"\u0D1D",u"\u0D1E",u"\u0D1F",u"\u0D20",
                u"\u0D21",u"\u0D22",u"\u0D23",u"\u0D24",u"\u0D25",u"\u0D26",
                u"\u0D27",u"\u0D28",u"\u0D2A",u"\u0D2B",u"\u0D2C",u"\u0D2D",
                u"\u0D2E",u"\u0D2F",u"\u0D30",u"\u0D31",u"\u0D32",u"\u0D33",
                u"\u0D34",u"\u0D35",u"\u0D36",u"\u0D37",u"\u0D38",u"\u0D39"],
            "WF_Consonants" : [],
        },
        "MANDAIC": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0840",u"\u0842",u"\u0843",u"\u0844",u"\u0845",u"\u0846",
                u"\u0847",u"\u0848",u"\u0849",u"\u084A",u"\u084B",u"\u084C",
                u"\u084D",u"\u084E",u"\u084F",u"\u0850",u"\u0851",u"\u0852",
                u"\u0853",u"\u0854",u"\u0855",u"\u0856",u"\u0857",u"\u0858"],
            "WF_Consonants" : [],
        },
        "MONGOLIAN": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u1820",u"\u1821",u"\u1822",u"\u1823",u"\u1824",u"\u1825",
                u"\u1826",u"\u1827"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1828",u"\u1829",u"\u182A",u"\u182B",u"\u182C",u"\u182D",
                u"\u182E",u"\u182F",u"\u1830",u"\u1831",u"\u1832",u"\u1833",
                u"\u1834",u"\u1835",u"\u1836",u"\u1837",u"\u1838",u"\u1839",
                u"\u183A",u"\u183B",u"\u183C",u"\u183D",u"\u183E",u"\u183F",
                u"\u1840",u"\u1841",u"\u1842"],
            "WF_Consonants" : [],
        },
        "MYANMAR": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u102C",u"\u102D",u"\u102E",u"\u102F",u"\u1030",u"\u1031",
                u"\u1032"],
            "AnyVowels" : [
                u"\u1021",u"\u1023",u"\u1024",u"\u1025",u"\u1026",u"\u1027",
                u"\u1029",u"\u102A"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1000",u"\u1001",u"\u1002",u"\u1003",u"\u1004",u"\u1005",
                u"\u1006",u"\u1007",u"\u1008",u"\u1009",u"\u100A",u"\u100B",
                u"\u100C",u"\u100D",u"\u100E",u"\u100F",u"\u1010",u"\u1011",
                u"\u1012",u"\u1013",u"\u1014",u"\u1015",u"\u1016",u"\u1017",
                u"\u1018",u"\u1019",u"\u101A",u"\u101B",u"\u101C",u"\u101D",
                u"\u101E",u"\u101F",u"\u1020",u"\u1050",u"\u1051"],
            "WF_Consonants" : [],
        },
        "NKO": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u07CA",u"\u07CB",u"\u07CC",u"\u07CD",u"\u07CE",u"\u07CF",
                u"\u07D0"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u07D1",u"\u07D2",u"\u07D3",u"\u07D4",u"\u07D5",u"\u07D6",
                u"\u07D7",u"\u07D8",u"\u07D9",u"\u07DA",u"\u07DB",u"\u07DC",
                u"\u07DD",u"\u07DE",u"\u07DF",u"\u07E1",u"\u07E2",u"\u07E3",
                u"\u07E4",u"\u07E5",u"\u07E6"],
            "WF_Consonants" : [],
        },
        "OGHAM": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1681",u"\u1682",u"\u1683",u"\u1684",u"\u1685",u"\u1686",
                u"\u1687",u"\u1688",u"\u1689",u"\u168A",u"\u168B",u"\u168C",
                u"\u168D",u"\u168E",u"\u168F",u"\u1690",u"\u1691",u"\u1692",
                u"\u1693",u"\u1694",u"\u1695",u"\u1696",u"\u1697",u"\u1698",
                u"\u1699",u"\u169A"],
            "WF_Consonants" : [],
        },
        "ORIYA": {
            "WI_Vowels" : [
                u"\u0B05",u"\u0B06",u"\u0B07",u"\u0B08",u"\u0B09",u"\u0B0A",
                u"\u0B0F",u"\u0B10",u"\u0B13",u"\u0B14"],
            "DepVowels" : [
                u"\u0B3E",u"\u0B3F",u"\u0B40",u"\u0B41",u"\u0B42",u"\u0B47",
                u"\u0B48",u"\u0B4B",u"\u0B4C"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0B15",u"\u0B16",u"\u0B17",u"\u0B18",u"\u0B19",u"\u0B1A",
                u"\u0B1B",u"\u0B1C",u"\u0B1D",u"\u0B1E",u"\u0B1F",u"\u0B20",
                u"\u0B21",u"\u0B22",u"\u0B23",u"\u0B24",u"\u0B25",u"\u0B26",
                u"\u0B27",u"\u0B28",u"\u0B2A",u"\u0B2B",u"\u0B2C",u"\u0B2D",
                u"\u0B2E",u"\u0B2F",u"\u0B30",u"\u0B32",u"\u0B33",u"\u0B35",
                u"\u0B36",u"\u0B37",u"\u0B38",u"\u0B39",u"\u0B5F",u"\u0B71"],
            "WF_Consonants" : [],
        },
        "REJANG": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\uA947",u"\uA948",u"\uA949",u"\uA94A",u"\uA94B",u"\uA94C",
                u"\uA94D",u"\uA94E"],
            "AnyVowels" : [
                u"\uA946"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\uA930",u"\uA931",u"\uA932",u"\uA933",u"\uA934",u"\uA935",
                u"\uA936",u"\uA937",u"\uA938",u"\uA939",u"\uA93A",u"\uA93B",
                u"\uA93C",u"\uA93D",u"\uA93E",u"\uA93F",u"\uA940",u"\uA941",
                u"\uA942",u"\uA943",u"\uA944",u"\uA945"],
            "WF_Consonants" : [],
        },
        "RUNIC": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u16AE",u"\u16AF",u"\u16C2"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u16A1",u"\u16A3",u"\u16A4",u"\u16A5",u"\u16A7",u"\u16AB",
                u"\u16B0",u"\u16B2",u"\u16B3",u"\u16B5",u"\u16B6",u"\u16B8",
                u"\u16C4",u"\u16CD",u"\u16CE",u"\u16D1",u"\u16DC",u"\u16DD",
                u"\u16E0",u"\u16E1",u"\u16E2",u"\u16E3",u"\u16E4",u"\u16E5",
                u"\u16E9",u"\u16EA"],
            "WF_Consonants" : [],
        },
        "SAMARITAN": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u081D",u"\u0820",u"\u0823",u"\u0827",u"\u082A",u"\u082B",
                u"\u082C"],
            "AnyVowels" : [
                u"\u0804"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0800",u"\u0801",u"\u0802",u"\u0803",u"\u0805",u"\u0806",
                u"\u0807",u"\u0808",u"\u0809",u"\u080A",u"\u080B",u"\u080C",
                u"\u080D",u"\u080E",u"\u080F",u"\u0810",u"\u0811",u"\u0812",
                u"\u0813",u"\u0814",u"\u0815"],
            "WF_Consonants" : [],
        },
        "SAURASHTRA": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\uA8B5",u"\uA8B6",u"\uA8B7",u"\uA8B8",u"\uA8B9",u"\uA8BE",
                u"\uA8BF",u"\uA8C0",u"\uA8C1",u"\uA8C2",u"\uA8C3"],
            "AnyVowels" : [
                u"\uA882",u"\uA883",u"\uA884",u"\uA885",u"\uA886",u"\uA887",
                u"\uA88C",u"\uA88D",u"\uA88E",u"\uA88F",u"\uA890",u"\uA891"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\uA892",u"\uA893",u"\uA894",u"\uA895",u"\uA896",u"\uA897",
                u"\uA898",u"\uA899",u"\uA89A",u"\uA89B",u"\uA89C",u"\uA89D",
                u"\uA89E",u"\uA89F",u"\uA8A0",u"\uA8A1",u"\uA8A2",u"\uA8A3",
                u"\uA8A4",u"\uA8A5",u"\uA8A6",u"\uA8A7",u"\uA8A8",u"\uA8A9",
                u"\uA8AA",u"\uA8AB",u"\uA8AC",u"\uA8AD",u"\uA8AE",u"\uA8AF",
                u"\uA8B0",u"\uA8B1",u"\uA8B2",u"\uA8B3"],
            "WF_Consonants" : [],
        },
        "SINHALA": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u0DD0",u"\u0DD1",u"\u0DD2",u"\u0DD3",u"\u0DD4",u"\u0DD6",
                u"\u0DD9",u"\u0DDA",u"\u0DDB",u"\u0DDF",u"\u0DF2",u"\u0DF3"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0D85",u"\u0D86",u"\u0D87",u"\u0D88",u"\u0D89",u"\u0D8A",
                u"\u0D8B",u"\u0D8C",u"\u0D8D",u"\u0D8E",u"\u0D8F",u"\u0D90",
                u"\u0D91",u"\u0D92",u"\u0D93",u"\u0D94",u"\u0D95",u"\u0D96",
                u"\u0D9A",u"\u0D9B",u"\u0D9C",u"\u0D9D",u"\u0D9E",u"\u0D9F",
                u"\u0DA0",u"\u0DA1",u"\u0DA2",u"\u0DA3",u"\u0DA4",u"\u0DA6",
                u"\u0DA7",u"\u0DA8",u"\u0DA9",u"\u0DAA",u"\u0DAB",u"\u0DAC",
                u"\u0DAD",u"\u0DAE",u"\u0DAF",u"\u0DB0",u"\u0DB1",u"\u0DB3",
                u"\u0DB4",u"\u0DB5",u"\u0DB6",u"\u0DB7",u"\u0DB8",u"\u0DB9",
                u"\u0DBA",u"\u0DBB",u"\u0DBD",u"\u0DC0",u"\u0DC1",u"\u0DC2",
                u"\u0DC3",u"\u0DC4",u"\u0DC5",u"\u0DC6"],
            "WF_Consonants" : [],
        },
        "SUNDANESE": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1BA4",u"\u1BA5",u"\u1BA6",u"\u1BA7",u"\u1BA8",u"\u1BA9"],
            "AnyVowels" : [
                u"\u1B83",u"\u1B84",u"\u1B85",u"\u1B86",u"\u1B87",u"\u1B88",
                u"\u1B89"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1B8A",u"\u1B8B",u"\u1B8C",u"\u1B8D",u"\u1B8E",u"\u1B8F",
                u"\u1B90",u"\u1B91",u"\u1B92",u"\u1B93",u"\u1B94",u"\u1B95",
                u"\u1B96",u"\u1B97",u"\u1B98",u"\u1B99",u"\u1B9A",u"\u1B9B",
                u"\u1B9C",u"\u1B9D",u"\u1B9E",u"\u1B9F",u"\u1BA0",u"\u1BAE",
                u"\u1BAF"],
            "WF_Consonants" : [],
        },
        "SYRIAC": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u0725"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0710",u"\u0712",u"\u0713",u"\u0715",u"\u0717",u"\u0718",
                u"\u0719",u"\u071A",u"\u071B",u"\u071D",u"\u071F",u"\u0720",
                u"\u0721",u"\u0722",u"\u0723",u"\u0726",u"\u0728",u"\u0729",
                u"\u072A",u"\u072B",u"\u072C"],
            "WF_Consonants" : [
                u"\u0724"],
        },
        "TAGALOG": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1712",u"\u1713"],
            "AnyVowels" : [
                u"\u1700",u"\u1701",u"\u1702"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1703",u"\u1704",u"\u1705",u"\u1706",u"\u1707",u"\u1708",
                u"\u1709",u"\u170A",u"\u170B",u"\u170C",u"\u170E",u"\u170F",
                u"\u1710",u"\u1711"],
            "WF_Consonants" : [],
        },
        "TAGBANWA": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u1772",u"\u1773"],
            "AnyVowels" : [
                u"\u1760",u"\u1761",u"\u1762"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u1763",u"\u1764",u"\u1765",u"\u1766",u"\u1767",u"\u1768",
                u"\u1769",u"\u176A",u"\u176B",u"\u176C",u"\u176E",u"\u176F",
                u"\u1770"],
            "WF_Consonants" : [],
        },
        "TAMIL": {
            "WI_Vowels" : [
                u"\u0B85",u"\u0B86",u"\u0B87",u"\u0B88",u"\u0B89",u"\u0B8A",
                u"\u0B8E",u"\u0B8F",u"\u0B90",u"\u0B92",u"\u0B93",u"\u0B94"],
            "DepVowels" : [
                u"\u0BBE",u"\u0BBF",u"\u0BC0",u"\u0BC1",u"\u0BC2",u"\u0BC6",
                u"\u0BC7",u"\u0BC8",u"\u0BCA",u"\u0BCB",u"\u0BCC"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0B95",u"\u0B99",u"\u0B9A",u"\u0B9C",u"\u0B9E",u"\u0B9F",
                u"\u0BA3",u"\u0BA4",u"\u0BA8",u"\u0BA9",u"\u0BAA",u"\u0BAE",
                u"\u0BAF",u"\u0BB0",u"\u0BB1",u"\u0BB2",u"\u0BB3",u"\u0BB4",
                u"\u0BB5",u"\u0BB6",u"\u0BB7",u"\u0BB8",u"\u0BB9"],
            "WF_Consonants" : [],
        },
        "TELUGU": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u0C3E",u"\u0C3F",u"\u0C40",u"\u0C41",u"\u0C42",u"\u0C46",
                u"\u0C47",u"\u0C48",u"\u0C4A",u"\u0C4B",u"\u0C4C"],
            "AnyVowels" : [
                u"\u0C05",u"\u0C06",u"\u0C07",u"\u0C08",u"\u0C09",u"\u0C0A",
                u"\u0C0E",u"\u0C0F",u"\u0C10",u"\u0C12",u"\u0C13",u"\u0C14"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0C15",u"\u0C16",u"\u0C17",u"\u0C18",u"\u0C19",u"\u0C1A",
                u"\u0C1B",u"\u0C1C",u"\u0C1D",u"\u0C1E",u"\u0C1F",u"\u0C20",
                u"\u0C21",u"\u0C22",u"\u0C23",u"\u0C24",u"\u0C25",u"\u0C26",
                u"\u0C27",u"\u0C28",u"\u0C2A",u"\u0C2B",u"\u0C2C",u"\u0C2D",
                u"\u0C2E",u"\u0C2F",u"\u0C30",u"\u0C31",u"\u0C32",u"\u0C33",
                u"\u0C35",u"\u0C36",u"\u0C37",u"\u0C38",u"\u0C39"],
            "WF_Consonants" : [],
        },
        "THAANA": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u0794"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0780",u"\u0781",u"\u0782",u"\u0783",u"\u0784",u"\u0785",
                u"\u0786",u"\u0787",u"\u0788",u"\u0789",u"\u078A",u"\u078B",
                u"\u078C",u"\u078D",u"\u078E",u"\u078F",u"\u0790",u"\u0791",
                u"\u0792",u"\u0793",u"\u0795",u"\u0796",u"\u0797",u"\u0798",
                u"\u0799",u"\u079A",u"\u079B",u"\u079C",u"\u079D",u"\u079E",
                u"\u079F",u"\u07A0",u"\u07A1",u"\u07A2",u"\u07A3",u"\u07A4",
                u"\u07A5"],
            "WF_Consonants" : [],
        },
        "THAI": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u0E30",u"\u0E32",u"\u0E33",u"\u0E34",u"\u0E35",u"\u0E36",
                u"\u0E38",u"\u0E39",u"\u0E40",u"\u0E41",u"\u0E42",u"\u0E43",
                u"\u0E44"],
            "AnyVowels" : [],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0E01",u"\u0E02",u"\u0E03",u"\u0E04",u"\u0E05",u"\u0E06",
                u"\u0E07",u"\u0E08",u"\u0E09",u"\u0E0A",u"\u0E0B",u"\u0E0C",
                u"\u0E0D",u"\u0E0E",u"\u0E0F",u"\u0E10",u"\u0E11",u"\u0E12",
                u"\u0E13",u"\u0E14",u"\u0E15",u"\u0E16",u"\u0E17",u"\u0E18",
                u"\u0E19",u"\u0E1A",u"\u0E1B",u"\u0E1C",u"\u0E1D",u"\u0E1E",
                u"\u0E1F",u"\u0E20",u"\u0E21",u"\u0E22",u"\u0E23",u"\u0E25",
                u"\u0E27",u"\u0E28",u"\u0E29",u"\u0E2A",u"\u0E2B",u"\u0E2C",
                u"\u0E2D",u"\u0E2E",u"\u0E31",u"\u0E47"],
            "WF_Consonants" : [],
        },
        "TIBETAN": {
            "WI_Vowels" : [],
            "DepVowels" : [
                u"\u0F71",u"\u0F72",u"\u0F73",u"\u0F74",u"\u0F75",u"\u0F7A",
                u"\u0F7B",u"\u0F7C",u"\u0F7D"],
            "AnyVowels" : [
                u"\u0F68"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u0F40",u"\u0F41",u"\u0F42",u"\u0F43",u"\u0F44",u"\u0F45",
                u"\u0F46",u"\u0F47",u"\u0F49",u"\u0F4A",u"\u0F4B",u"\u0F4C",
                u"\u0F4D",u"\u0F4E",u"\u0F4F",u"\u0F50",u"\u0F51",u"\u0F52",
                u"\u0F53",u"\u0F54",u"\u0F55",u"\u0F56",u"\u0F57",u"\u0F58",
                u"\u0F59",u"\u0F5A",u"\u0F5B",u"\u0F5C",u"\u0F5D",u"\u0F5E",
                u"\u0F5F",u"\u0F61",u"\u0F62",u"\u0F63",u"\u0F64",u"\u0F65",
                u"\u0F66",u"\u0F67",u"\u0F69",u"\u0F6B",u"\u0F6C"],
            "WF_Consonants" : [],
        },
        "TIFINAGH": {
            "WI_Vowels" : [],
            "DepVowels" : [],
            "AnyVowels" : [
                u"\u2D3B",u"\u2D44",u"\u2D49",u"\u2D53",u"\u2D62"],
            "WI_Consonants" : [],
            "AnyConsonants" : [
                u"\u2D30",u"\u2D32",u"\u2D33",u"\u2D34",u"\u2D36",u"\u2D37",
                u"\u2D38",u"\u2D39",u"\u2D3A",u"\u2D3C",u"\u2D3D",u"\u2D3F",
                u"\u2D40",u"\u2D43",u"\u2D45",u"\u2D47",u"\u2D4A",u"\u2D4D",
                u"\u2D4E",u"\u2D4F",u"\u2D52",u"\u2D54",u"\u2D55",u"\u2D56",
                u"\u2D59",u"\u2D5A",u"\u2D5B",u"\u2D5C",u"\u2D5D",u"\u2D5E",
                u"\u2D5F",u"\u2D60",u"\u2D61",u"\u2D63",u"\u2D65"],
            "WF_Consonants" : [],
        },
    }

    OtherKnownLetters = {
    "WI_Vowels" : [],
    "DepVowels" : [
        u"\u0000",u"\u0001",u"\u0002",u"\u0003",u"\u0004",u"\u0005",u"\u0006",
        u"\u0007",u"\u0008",u"\u0009",u"\u000A",u"\u000B",u"\u000C",u"\u000D",
        u"\u000E",u"\u000F",u"\u0010",u"\u0011",u"\u0012",u"\u0013",u"\u0014",
        u"\u0015",u"\u0016",u"\u0017",u"\u0018",u"\u0019",u"\u001A",u"\u001B",
        u"\u001C",u"\u001D",u"\u001E",u"\u001F",u"\u0020",u"\u0021",u"\u0022",
        u"\u0023",u"\u0024",u"\u0025",u"\u0026",u"\u0027",u"\u0028",u"\u0029",
        u"\u002A",u"\u002B",u"\u002C",u"\u002D",u"\u002E",u"\u002F",u"\u0030",
        u"\u0031",u"\u0032",u"\u0033",u"\u0034",u"\u0035",u"\u0036",u"\u0037",
        u"\u0038",u"\u0039",u"\u003A",u"\u003B",u"\u003C",u"\u003D",u"\u003E",
        u"\u003F",u"\u0040",u"\u005B",u"\u005C",u"\u005D",u"\u005E",u"\u005F",
        u"\u0060",u"\u007B",u"\u007C",u"\u007D",u"\u007E",u"\u007F",u"\u0080",
        u"\u0081",u"\u0082",u"\u0083",u"\u0084",u"\u0085",u"\u0086",u"\u0087",
        u"\u0088",u"\u0089",u"\u008A",u"\u008B",u"\u008C",u"\u008D",u"\u008E",
        u"\u008F",u"\u0090",u"\u0091",u"\u0092",u"\u0093",u"\u0094",u"\u0095",
        u"\u0096",u"\u0097",u"\u0098",u"\u0099",u"\u009A",u"\u009B",u"\u009C",
        u"\u009D",u"\u009E",u"\u009F",u"\u00A0",u"\u00A1",u"\u00A2",u"\u00A3",
        u"\u00A4",u"\u00A5",u"\u00A6",u"\u00A7",u"\u00A8",u"\u00A9",u"\u00AB",
        u"\u00AC",u"\u00AD",u"\u00AE",u"\u00AF",u"\u00B0",u"\u00B1",u"\u00B2",
        u"\u00B3",u"\u00B4",u"\u00B6",u"\u00B7",u"\u00B8",u"\u00B9",u"\u00BB",
        u"\u00BC",u"\u00BD",u"\u00BE",u"\u00BF",u"\u00D7",u"\u00F7",u"\u02C2",
        u"\u02C3",u"\u02C4",u"\u02C5",u"\u02D2",u"\u02D3",u"\u02D4",u"\u02D5",
        u"\u02D6",u"\u02D7",u"\u02D8",u"\u02D9",u"\u02DA",u"\u02DB",u"\u02DC",
        u"\u02DD",u"\u02DE",u"\u02DF",u"\u02E5",u"\u02E6",u"\u02E7",u"\u02E8",
        u"\u02E9",u"\u02EA",u"\u02EB",u"\u02EF",u"\u02F0",u"\u02F1",u"\u02F2",
        u"\u02F3",u"\u02F4",u"\u02F5",u"\u02F6",u"\u02F7",u"\u02F8",u"\u02F9",
        u"\u02FA",u"\u02FB",u"\u02FC",u"\u02FE",u"\u02FF",u"\u0300",u"\u0301",
        u"\u0302",u"\u0303",u"\u0304",u"\u0305",u"\u0306",u"\u0307",u"\u0308",
        u"\u0309",u"\u030A",u"\u030B",u"\u030C",u"\u030D",u"\u030E",u"\u030F",
        u"\u0310",u"\u0311",u"\u0312",u"\u0313",u"\u0314",u"\u0315",u"\u0316",
        u"\u0317",u"\u0318",u"\u0319",u"\u031A",u"\u031B",u"\u031C",u"\u031D",
        u"\u031E",u"\u031F",u"\u0320",u"\u0321",u"\u0322",u"\u0323",u"\u0324",
        u"\u0325",u"\u0326",u"\u0327",u"\u0328",u"\u0329",u"\u032A",u"\u032B",
        u"\u032C",u"\u032D",u"\u032E",u"\u032F",u"\u0330",u"\u0331",u"\u0332",
        u"\u0333",u"\u0334",u"\u0335",u"\u0336",u"\u0337",u"\u0338",u"\u0339",
        u"\u033A",u"\u033B",u"\u033C",u"\u033D",u"\u033E",u"\u033F",u"\u0340",
        u"\u0341",u"\u0342",u"\u0343",u"\u0344",u"\u0345",u"\u0346",u"\u0347",
        u"\u0348",u"\u0349",u"\u034A",u"\u034B",u"\u034C",u"\u034D",u"\u034E",
        u"\u034F",u"\u0350",u"\u0351",u"\u0352",u"\u0353",u"\u0354",u"\u0355",
        u"\u0356",u"\u0357",u"\u0358",u"\u0359",u"\u035A",u"\u035B",u"\u035C",
        u"\u035D",u"\u035E",u"\u035F",u"\u0360",u"\u0361",u"\u0362",u"\u0363",
        u"\u0364",u"\u0365",u"\u0366",u"\u0367",u"\u0368",u"\u0369",u"\u036A",
        u"\u036B",u"\u036C",u"\u036D",u"\u036E",u"\u036F",u"\u0375",u"\u037E",
        u"\u0384",u"\u0385",u"\u0387",u"\u03F6",u"\u0482",u"\u0483",u"\u0484",
        u"\u0485",u"\u0486",u"\u0487",u"\u0488",u"\u0489",u"\u055A",u"\u055B",
        u"\u055C",u"\u055D",u"\u055E",u"\u055F",u"\u0589",u"\u058A",u"\u0591",
        u"\u0592",u"\u0593",u"\u0594",u"\u0595",u"\u0596",u"\u0597",u"\u0598",
        u"\u0599",u"\u059A",u"\u059B",u"\u059C",u"\u059D",u"\u059E",u"\u059F",
        u"\u05A0",u"\u05A1",u"\u05A2",u"\u05A3",u"\u05A4",u"\u05A5",u"\u05A6",
        u"\u05A7",u"\u05A8",u"\u05A9",u"\u05AA",u"\u05AB",u"\u05AC",u"\u05AD",
        u"\u05AE",u"\u05AF",u"\u05BA",u"\u05BE",u"\u05C0",u"\u05C1",u"\u05C2",
        u"\u05C3",u"\u05C4",u"\u05C5",u"\u05C6",u"\u05C7",u"\u05F3",u"\u05F4",
        u"\u0600",u"\u0601",u"\u0602",u"\u0603",u"\u0606",u"\u0607",u"\u0608",
        u"\u0609",u"\u060A",u"\u060B",u"\u060C",u"\u060D",u"\u060E",u"\u060F",
        u"\u0610",u"\u0611",u"\u0612",u"\u0613",u"\u0614",u"\u0615",u"\u0616",
        u"\u0617",u"\u0618",u"\u0619",u"\u061A",u"\u061B",u"\u061E",u"\u061F",
        u"\u064B",u"\u064C",u"\u064D",u"\u064E",u"\u064F",u"\u0650",u"\u0651",
        u"\u0652",u"\u0653",u"\u0654",u"\u0655",u"\u0656",u"\u0657",u"\u0658",
        u"\u0659",u"\u065A",u"\u065B",u"\u065C",u"\u065D",u"\u065E",u"\u065F",
        u"\u0660",u"\u0661",u"\u0662",u"\u0663",u"\u0664",u"\u0665",u"\u0666",
        u"\u0667",u"\u0668",u"\u0669",u"\u066A",u"\u066B",u"\u066C",u"\u066D",
        u"\u0670",u"\u06D4",u"\u06D6",u"\u06D7",u"\u06D8",u"\u06D9",u"\u06DA",
        u"\u06DB",u"\u06DC",u"\u06DD",u"\u06DE",u"\u06DF",u"\u06E0",u"\u06E1",
        u"\u06E2",u"\u06E3",u"\u06E4",u"\u06E7",u"\u06E8",u"\u06E9",u"\u06EA",
        u"\u06EB",u"\u06EC",u"\u06ED",u"\u06F0",u"\u06F1",u"\u06F2",u"\u06F3",
        u"\u06F4",u"\u06F5",u"\u06F6",u"\u06F7",u"\u06F8",u"\u06F9",u"\u06FD",
        u"\u06FE",u"\u0700",u"\u0701",u"\u0702",u"\u0703",u"\u0704",u"\u0705",
        u"\u0706",u"\u0707",u"\u0708",u"\u0709",u"\u070A",u"\u070B",u"\u070C",
        u"\u070D",u"\u070F",u"\u0711",u"\u0730",u"\u0731",u"\u0732",u"\u0733",
        u"\u0734",u"\u0735",u"\u0736",u"\u0737",u"\u0738",u"\u0739",u"\u073A",
        u"\u073B",u"\u073C",u"\u073D",u"\u073E",u"\u073F",u"\u0740",u"\u0741",
        u"\u0742",u"\u0743",u"\u0744",u"\u0745",u"\u0746",u"\u0747",u"\u0748",
        u"\u0749",u"\u074A",u"\u07A6",u"\u07A7",u"\u07A8",u"\u07A9",u"\u07AA",
        u"\u07AB",u"\u07AC",u"\u07AD",u"\u07AE",u"\u07AF",u"\u07B0",u"\u07C0",
        u"\u07C1",u"\u07C2",u"\u07C3",u"\u07C4",u"\u07C5",u"\u07C6",u"\u07C7",
        u"\u07C8",u"\u07C9",u"\u07EB",u"\u07EC",u"\u07ED",u"\u07EE",u"\u07EF",
        u"\u07F0",u"\u07F1",u"\u07F2",u"\u07F3",u"\u07F6",u"\u07F7",u"\u07F8",
        u"\u07F9",u"\u0816",u"\u0817",u"\u0818",u"\u0819",u"\u081B",u"\u081C",
        u"\u081E",u"\u081F",u"\u0821",u"\u0822",u"\u0825",u"\u0826",u"\u0829",
        u"\u082D",u"\u0830",u"\u0831",u"\u0832",u"\u0833",u"\u0834",u"\u0835",
        u"\u0836",u"\u0837",u"\u0838",u"\u0839",u"\u083A",u"\u083B",u"\u083C",
        u"\u083D",u"\u083E",u"\u0859",u"\u085A",u"\u085B",u"\u085E",u"\u0900",
        u"\u0901",u"\u0902",u"\u0903",u"\u093A",u"\u093B",u"\u093C",u"\u0943",
        u"\u0944",u"\u0945",u"\u0946",u"\u0949",u"\u094A",u"\u094D",u"\u094E",
        u"\u094F",u"\u0951",u"\u0952",u"\u0953",u"\u0954",u"\u0955",u"\u0956",
        u"\u0957",u"\u0962",u"\u0963",u"\u0964",u"\u0965",u"\u0966",u"\u0967",
        u"\u0968",u"\u0969",u"\u096A",u"\u096B",u"\u096C",u"\u096D",u"\u096E",
        u"\u096F",u"\u0970",u"\u0981",u"\u0982",u"\u0983",u"\u09BC",u"\u09C3",
        u"\u09C4",u"\u09CD",u"\u09D7",u"\u09E2",u"\u09E3",u"\u09E6",u"\u09E7",
        u"\u09E8",u"\u09E9",u"\u09EA",u"\u09EB",u"\u09EC",u"\u09ED",u"\u09EE",
        u"\u09EF",u"\u09F2",u"\u09F3",u"\u09F4",u"\u09F5",u"\u09F6",u"\u09F7",
        u"\u09F8",u"\u09F9",u"\u09FA",u"\u09FB",u"\u0A01",u"\u0A02",u"\u0A03",
        u"\u0A3C",u"\u0A4D",u"\u0A51",u"\u0A66",u"\u0A67",u"\u0A68",u"\u0A69",
        u"\u0A6A",u"\u0A6B",u"\u0A6C",u"\u0A6D",u"\u0A6E",u"\u0A6F",u"\u0A70",
        u"\u0A71",u"\u0A75",u"\u0A81",u"\u0A82",u"\u0A83",u"\u0ABC",u"\u0AC3",
        u"\u0AC4",u"\u0AC5",u"\u0AC9",u"\u0ACD",u"\u0AE2",u"\u0AE3",u"\u0AE6",
        u"\u0AE7",u"\u0AE8",u"\u0AE9",u"\u0AEA",u"\u0AEB",u"\u0AEC",u"\u0AED",
        u"\u0AEE",u"\u0AEF",u"\u0AF1",u"\u0B01",u"\u0B02",u"\u0B03",u"\u0B3C",
        u"\u0B43",u"\u0B44",u"\u0B4D",u"\u0B56",u"\u0B57",u"\u0B62",u"\u0B63",
        u"\u0B66",u"\u0B67",u"\u0B68",u"\u0B69",u"\u0B6A",u"\u0B6B",u"\u0B6C",
        u"\u0B6D",u"\u0B6E",u"\u0B6F",u"\u0B70",u"\u0B72",u"\u0B73",u"\u0B74",
        u"\u0B75",u"\u0B76",u"\u0B77",u"\u0B82",u"\u0BCD",u"\u0BD7",u"\u0BE6",
        u"\u0BE7",u"\u0BE8",u"\u0BE9",u"\u0BEA",u"\u0BEB",u"\u0BEC",u"\u0BED",
        u"\u0BEE",u"\u0BEF",u"\u0BF0",u"\u0BF1",u"\u0BF2",u"\u0BF3",u"\u0BF4",
        u"\u0BF5",u"\u0BF6",u"\u0BF7",u"\u0BF8",u"\u0BF9",u"\u0BFA",u"\u0C01",
        u"\u0C02",u"\u0C03",u"\u0C43",u"\u0C44",u"\u0C4D",u"\u0C55",u"\u0C56",
        u"\u0C62",u"\u0C63",u"\u0C66",u"\u0C67",u"\u0C68",u"\u0C69",u"\u0C6A",
        u"\u0C6B",u"\u0C6C",u"\u0C6D",u"\u0C6E",u"\u0C6F",u"\u0C78",u"\u0C79",
        u"\u0C7A",u"\u0C7B",u"\u0C7C",u"\u0C7D",u"\u0C7E",u"\u0C7F",u"\u0C82",
        u"\u0C83",u"\u0CBC",u"\u0CC3",u"\u0CC4",u"\u0CCD",u"\u0CD5",u"\u0CD6",
        u"\u0CE2",u"\u0CE3",u"\u0CE6",u"\u0CE7",u"\u0CE8",u"\u0CE9",u"\u0CEA",
        u"\u0CEB",u"\u0CEC",u"\u0CED",u"\u0CEE",u"\u0CEF",u"\u0D02",u"\u0D03",
        u"\u0D43",u"\u0D44",u"\u0D4C",u"\u0D4D",u"\u0D57",u"\u0D62",u"\u0D63",
        u"\u0D66",u"\u0D67",u"\u0D68",u"\u0D69",u"\u0D6A",u"\u0D6B",u"\u0D6C",
        u"\u0D6D",u"\u0D6E",u"\u0D6F",u"\u0D70",u"\u0D71",u"\u0D72",u"\u0D73",
        u"\u0D74",u"\u0D75",u"\u0D79",u"\u0D82",u"\u0D83",u"\u0DCA",u"\u0DCF",
        u"\u0DD8",u"\u0DDC",u"\u0DDD",u"\u0DDE",u"\u0DF4",u"\u0E37",u"\u0E3A",
        u"\u0E3F",u"\u0E48",u"\u0E49",u"\u0E4A",u"\u0E4B",u"\u0E4C",u"\u0E4D",
        u"\u0E4E",u"\u0E4F",u"\u0E50",u"\u0E51",u"\u0E52",u"\u0E53",u"\u0E54",
        u"\u0E55",u"\u0E56",u"\u0E57",u"\u0E58",u"\u0E59",u"\u0E5A",u"\u0E5B",
        u"\u0EB1",u"\u0EBB",u"\u0EBC",u"\u0EC8",u"\u0EC9",u"\u0ECA",u"\u0ECB",
        u"\u0ECC",u"\u0ECD",u"\u0ED0",u"\u0ED1",u"\u0ED2",u"\u0ED3",u"\u0ED4",
        u"\u0ED5",u"\u0ED6",u"\u0ED7",u"\u0ED8",u"\u0ED9",u"\u0F01",u"\u0F02",
        u"\u0F03",u"\u0F04",u"\u0F05",u"\u0F06",u"\u0F07",u"\u0F08",u"\u0F09",
        u"\u0F0A",u"\u0F0B",u"\u0F0C",u"\u0F0D",u"\u0F0E",u"\u0F0F",u"\u0F10",
        u"\u0F11",u"\u0F12",u"\u0F13",u"\u0F14",u"\u0F15",u"\u0F16",u"\u0F17",
        u"\u0F18",u"\u0F19",u"\u0F1A",u"\u0F1B",u"\u0F1C",u"\u0F1D",u"\u0F1E",
        u"\u0F1F",u"\u0F20",u"\u0F21",u"\u0F22",u"\u0F23",u"\u0F24",u"\u0F25",
        u"\u0F26",u"\u0F27",u"\u0F28",u"\u0F29",u"\u0F2A",u"\u0F2B",u"\u0F2C",
        u"\u0F2D",u"\u0F2E",u"\u0F2F",u"\u0F30",u"\u0F31",u"\u0F32",u"\u0F33",
        u"\u0F34",u"\u0F35",u"\u0F36",u"\u0F37",u"\u0F38",u"\u0F39",u"\u0F3A",
        u"\u0F3B",u"\u0F3C",u"\u0F3D",u"\u0F3E",u"\u0F3F",u"\u0F76",u"\u0F77",
        u"\u0F78",u"\u0F79",u"\u0F7E",u"\u0F7F",u"\u0F80",u"\u0F81",u"\u0F82",
        u"\u0F83",u"\u0F84",u"\u0F85",u"\u0F86",u"\u0F87",u"\u0F8D",u"\u0F8E",
        u"\u0F8F",u"\u0F90",u"\u0F91",u"\u0F92",u"\u0F93",u"\u0F94",u"\u0F95",
        u"\u0F96",u"\u0F97",u"\u0F99",u"\u0F9A",u"\u0F9B",u"\u0F9C",u"\u0F9D",
        u"\u0F9E",u"\u0F9F",u"\u0FA0",u"\u0FA1",u"\u0FA2",u"\u0FA3",u"\u0FA4",
        u"\u0FA5",u"\u0FA6",u"\u0FA7",u"\u0FA8",u"\u0FA9",u"\u0FAA",u"\u0FAB",
        u"\u0FAC",u"\u0FAD",u"\u0FAE",u"\u0FAF",u"\u0FB0",u"\u0FB1",u"\u0FB2",
        u"\u0FB3",u"\u0FB4",u"\u0FB5",u"\u0FB6",u"\u0FB7",u"\u0FB8",u"\u0FB9",
        u"\u0FBA",u"\u0FBB",u"\u0FBC",u"\u0FBE",u"\u0FBF",u"\u0FC0",u"\u0FC1",
        u"\u0FC2",u"\u0FC3",u"\u0FC4",u"\u0FC5",u"\u0FC6",u"\u0FC7",u"\u0FC8",
        u"\u0FC9",u"\u0FCA",u"\u0FCB",u"\u0FCC",u"\u0FCE",u"\u0FCF",u"\u0FD0",
        u"\u0FD1",u"\u0FD2",u"\u0FD3",u"\u0FD4",u"\u0FD5",u"\u0FD6",u"\u0FD7",
        u"\u0FD8",u"\u0FD9",u"\u0FDA",u"\u102B",u"\u1033",u"\u1034",u"\u1035",
        u"\u1036",u"\u1037",u"\u1038",u"\u1039",u"\u103A",u"\u103B",u"\u103C",
        u"\u103D",u"\u103E",u"\u1040",u"\u1041",u"\u1042",u"\u1043",u"\u1044",
        u"\u1045",u"\u1046",u"\u1047",u"\u1048",u"\u1049",u"\u104A",u"\u104B",
        u"\u104C",u"\u104D",u"\u104E",u"\u104F",u"\u1056",u"\u1057",u"\u1058",
        u"\u1059",u"\u105E",u"\u105F",u"\u1060",u"\u1062",u"\u1063",u"\u1064",
        u"\u1067",u"\u1068",u"\u1069",u"\u106A",u"\u106B",u"\u106C",u"\u106D",
        u"\u1071",u"\u1072",u"\u1073",u"\u1074",u"\u1082",u"\u1083",u"\u1084",
        u"\u1085",u"\u1086",u"\u1087",u"\u1088",u"\u1089",u"\u108A",u"\u108B",
        u"\u108C",u"\u108D",u"\u108F",u"\u1090",u"\u1091",u"\u1092",u"\u1093",
        u"\u1094",u"\u1095",u"\u1096",u"\u1097",u"\u1098",u"\u1099",u"\u109A",
        u"\u109B",u"\u109C",u"\u109D",u"\u109E",u"\u109F",u"\u10FB",u"\u135D",
        u"\u135E",u"\u135F",u"\u1360",u"\u1361",u"\u1362",u"\u1363",u"\u1364",
        u"\u1365",u"\u1366",u"\u1367",u"\u1368",u"\u1369",u"\u136A",u"\u136B",
        u"\u136C",u"\u136D",u"\u136E",u"\u136F",u"\u1370",u"\u1371",u"\u1372",
        u"\u1373",u"\u1374",u"\u1375",u"\u1376",u"\u1377",u"\u1378",u"\u1379",
        u"\u137A",u"\u137B",u"\u137C",u"\u1390",u"\u1391",u"\u1392",u"\u1393",
        u"\u1394",u"\u1395",u"\u1396",u"\u1397",u"\u1398",u"\u1399",u"\u1400",
        u"\u166D",u"\u166E",u"\u1680",u"\u169B",u"\u169C",u"\u16EB",u"\u16EC",
        u"\u16ED",u"\u16EE",u"\u16EF",u"\u16F0",u"\u1714",u"\u1734",u"\u1735",
        u"\u1736",u"\u17B4",u"\u17B5",u"\u17C6",u"\u17C7",u"\u17C8",u"\u17C9",
        u"\u17CA",u"\u17CB",u"\u17CC",u"\u17CD",u"\u17CE",u"\u17CF",u"\u17D0",
        u"\u17D1",u"\u17D2",u"\u17D3",u"\u17D4",u"\u17D5",u"\u17D6",u"\u17D8",
        u"\u17D9",u"\u17DA",u"\u17DB",u"\u17DD",u"\u17E0",u"\u17E1",u"\u17E2",
        u"\u17E3",u"\u17E4",u"\u17E5",u"\u17E6",u"\u17E7",u"\u17E8",u"\u17E9",
        u"\u17F0",u"\u17F1",u"\u17F2",u"\u17F3",u"\u17F4",u"\u17F5",u"\u17F6",
        u"\u17F7",u"\u17F8",u"\u17F9",u"\u1800",u"\u1801",u"\u1802",u"\u1803",
        u"\u1804",u"\u1805",u"\u1806",u"\u1807",u"\u1808",u"\u1809",u"\u180A",
        u"\u180B",u"\u180C",u"\u180D",u"\u180E",u"\u1810",u"\u1811",u"\u1812",
        u"\u1813",u"\u1814",u"\u1815",u"\u1816",u"\u1817",u"\u1818",u"\u1819",
        u"\u18A9",u"\u1929",u"\u192A",u"\u192B",u"\u1939",u"\u193A",u"\u193B",
        u"\u1940",u"\u1944",u"\u1945",u"\u1946",u"\u1947",u"\u1948",u"\u1949",
        u"\u194A",u"\u194B",u"\u194C",u"\u194D",u"\u194E",u"\u194F",u"\u19B0",
        u"\u19B1",u"\u19B2",u"\u19B3",u"\u19B4",u"\u19B5",u"\u19B6",u"\u19B7",
        u"\u19B8",u"\u19B9",u"\u19BA",u"\u19BB",u"\u19BC",u"\u19BD",u"\u19BE",
        u"\u19BF",u"\u19C0",u"\u19C8",u"\u19C9",u"\u19D0",u"\u19D1",u"\u19D2",
        u"\u19D3",u"\u19D4",u"\u19D5",u"\u19D6",u"\u19D7",u"\u19D8",u"\u19D9",
        u"\u19DA",u"\u19DE",u"\u19DF",u"\u19E0",u"\u19E1",u"\u19E2",u"\u19E3",
        u"\u19E4",u"\u19E5",u"\u19E6",u"\u19E7",u"\u19E8",u"\u19E9",u"\u19EA",
        u"\u19EB",u"\u19EC",u"\u19ED",u"\u19EE",u"\u19EF",u"\u19F0",u"\u19F1",
        u"\u19F2",u"\u19F3",u"\u19F4",u"\u19F5",u"\u19F6",u"\u19F7",u"\u19F8",
        u"\u19F9",u"\u19FA",u"\u19FB",u"\u19FC",u"\u19FD",u"\u19FE",u"\u19FF",
        u"\u1A1E",u"\u1A1F",u"\u1A55",u"\u1A56",u"\u1A57",u"\u1A58",u"\u1A59",
        u"\u1A5A",u"\u1A5B",u"\u1A5C",u"\u1A5D",u"\u1A5E",u"\u1A60",u"\u1A61",
        u"\u1A62",u"\u1A63",u"\u1A64",u"\u1A65",u"\u1A66",u"\u1A67",u"\u1A68",
        u"\u1A69",u"\u1A6A",u"\u1A6B",u"\u1A6C",u"\u1A6D",u"\u1A6E",u"\u1A6F",
        u"\u1A70",u"\u1A71",u"\u1A72",u"\u1A73",u"\u1A74",u"\u1A75",u"\u1A76",
        u"\u1A77",u"\u1A78",u"\u1A79",u"\u1A7A",u"\u1A7B",u"\u1A7C",u"\u1A7F",
        u"\u1A80",u"\u1A81",u"\u1A82",u"\u1A83",u"\u1A84",u"\u1A85",u"\u1A86",
        u"\u1A87",u"\u1A88",u"\u1A89",u"\u1A90",u"\u1A91",u"\u1A92",u"\u1A93",
        u"\u1A94",u"\u1A95",u"\u1A96",u"\u1A97",u"\u1A98",u"\u1A99",u"\u1AA0",
        u"\u1AA1",u"\u1AA2",u"\u1AA3",u"\u1AA4",u"\u1AA5",u"\u1AA6",u"\u1AA8",
        u"\u1AA9",u"\u1AAA",u"\u1AAB",u"\u1AAC",u"\u1AAD",u"\u1B00",u"\u1B01",
        u"\u1B02",u"\u1B03",u"\u1B04",u"\u1B34",u"\u1B37",u"\u1B39",u"\u1B3A",
        u"\u1B3B",u"\u1B3C",u"\u1B3D",u"\u1B3F",u"\u1B40",u"\u1B41",u"\u1B43",
        u"\u1B44",u"\u1B50",u"\u1B51",u"\u1B52",u"\u1B53",u"\u1B54",u"\u1B55",
        u"\u1B56",u"\u1B57",u"\u1B58",u"\u1B59",u"\u1B5A",u"\u1B5B",u"\u1B5C",
        u"\u1B5D",u"\u1B5E",u"\u1B5F",u"\u1B60",u"\u1B61",u"\u1B62",u"\u1B63",
        u"\u1B64",u"\u1B65",u"\u1B66",u"\u1B67",u"\u1B68",u"\u1B69",u"\u1B6A",
        u"\u1B6B",u"\u1B6C",u"\u1B6D",u"\u1B6E",u"\u1B6F",u"\u1B70",u"\u1B71",
        u"\u1B72",u"\u1B73",u"\u1B74",u"\u1B75",u"\u1B76",u"\u1B77",u"\u1B78",
        u"\u1B79",u"\u1B7A",u"\u1B7B",u"\u1B7C",u"\u1B80",u"\u1B81",u"\u1B82",
        u"\u1BA1",u"\u1BA2",u"\u1BA3",u"\u1BAA",u"\u1BB0",u"\u1BB1",u"\u1BB2",
        u"\u1BB3",u"\u1BB4",u"\u1BB5",u"\u1BB6",u"\u1BB7",u"\u1BB8",u"\u1BB9",
        u"\u1BE6",u"\u1BE8",u"\u1BEB",u"\u1BED",u"\u1BEF",u"\u1BF0",u"\u1BF1",
        u"\u1BF2",u"\u1BF3",u"\u1BFC",u"\u1BFD",u"\u1BFE",u"\u1BFF",u"\u1C24",
        u"\u1C25",u"\u1C2D",u"\u1C2E",u"\u1C2F",u"\u1C30",u"\u1C31",u"\u1C32",
        u"\u1C33",u"\u1C34",u"\u1C35",u"\u1C36",u"\u1C37",u"\u1C3B",u"\u1C3C",
        u"\u1C3D",u"\u1C3E",u"\u1C3F",u"\u1C40",u"\u1C41",u"\u1C42",u"\u1C43",
        u"\u1C44",u"\u1C45",u"\u1C46",u"\u1C47",u"\u1C48",u"\u1C49",u"\u1C50",
        u"\u1C51",u"\u1C52",u"\u1C53",u"\u1C54",u"\u1C55",u"\u1C56",u"\u1C57",
        u"\u1C58",u"\u1C59",u"\u1C7E",u"\u1C7F",u"\u1CD0",u"\u1CD1",u"\u1CD2",
        u"\u1CD3",u"\u1CD4",u"\u1CD5",u"\u1CD6",u"\u1CD7",u"\u1CD8",u"\u1CD9",
        u"\u1CDA",u"\u1CDB",u"\u1CDC",u"\u1CDD",u"\u1CDE",u"\u1CDF",u"\u1CE0",
        u"\u1CE1",u"\u1CE2",u"\u1CE3",u"\u1CE4",u"\u1CE5",u"\u1CE6",u"\u1CE7",
        u"\u1CE8",u"\u1CED",u"\u1CF2",u"\u1DC0",u"\u1DC1",u"\u1DC2",u"\u1DC3",
        u"\u1DC4",u"\u1DC5",u"\u1DC6",u"\u1DC7",u"\u1DC8",u"\u1DC9",u"\u1DCA",
        u"\u1DCB",u"\u1DCC",u"\u1DCD",u"\u1DCE",u"\u1DCF",u"\u1DD0",u"\u1DD1",
        u"\u1DD2",u"\u1DD3",u"\u1DD4",u"\u1DD5",u"\u1DD6",u"\u1DD7",u"\u1DD8",
        u"\u1DD9",u"\u1DDA",u"\u1DDB",u"\u1DDC",u"\u1DDD",u"\u1DDE",u"\u1DDF",
        u"\u1DE0",u"\u1DE1",u"\u1DE2",u"\u1DE3",u"\u1DE4",u"\u1DE5",u"\u1DE6",
        u"\u1DFC",u"\u1DFD",u"\u1DFE",u"\u1DFF",u"\u1FBD",u"\u1FBF",u"\u1FC0",
        u"\u1FC1",u"\u1FCD",u"\u1FCE",u"\u1FCF",u"\u1FDD",u"\u1FDE",u"\u1FDF",
        u"\u1FED",u"\u1FEE",u"\u1FEF",u"\u1FFD",u"\u1FFE",u"\u2000",u"\u2001",
        u"\u2002",u"\u2003",u"\u2004",u"\u2005",u"\u2006",u"\u2007",u"\u2008",
        u"\u2009",u"\u200A",u"\u200B",u"\u200C",u"\u200D",u"\u200E",u"\u200F",
        u"\u2010",u"\u2011",u"\u2012",u"\u2013",u"\u2014",u"\u2015",u"\u2016",
        u"\u2017",u"\u2018",u"\u2019",u"\u201A",u"\u201B",u"\u201C",u"\u201D",
        u"\u201E",u"\u201F",u"\u2020",u"\u2021",u"\u2022",u"\u2023",u"\u2024",
        u"\u2025",u"\u2026",u"\u2027",u"\u2028",u"\u2029",u"\u202A",u"\u202B",
        u"\u202C",u"\u202D",u"\u202E",u"\u202F",u"\u2030",u"\u2031",u"\u2032",
        u"\u2033",u"\u2034",u"\u2035",u"\u2036",u"\u2037",u"\u2038",u"\u2039",
        u"\u203A",u"\u203B",u"\u203C",u"\u203D",u"\u203E",u"\u203F",u"\u2040",
        u"\u2041",u"\u2042",u"\u2043",u"\u2044",u"\u2045",u"\u2046",u"\u2047",
        u"\u2048",u"\u2049",u"\u204A",u"\u204B",u"\u204C",u"\u204D",u"\u204E",
        u"\u204F",u"\u2050",u"\u2051",u"\u2052",u"\u2053",u"\u2054",u"\u2055",
        u"\u2056",u"\u2057",u"\u2058",u"\u2059",u"\u205A",u"\u205B",u"\u205C",
        u"\u205D",u"\u205E",u"\u205F",u"\u2060",u"\u2061",u"\u2062",u"\u2063",
        u"\u2064",u"\u206A",u"\u206B",u"\u206C",u"\u206D",u"\u206E",u"\u206F",
        u"\u2070",u"\u2074",u"\u2075",u"\u2076",u"\u2077",u"\u2078",u"\u2079",
        u"\u207A",u"\u207B",u"\u207C",u"\u207D",u"\u207E",u"\u2080",u"\u2081",
        u"\u2082",u"\u2083",u"\u2084",u"\u2085",u"\u2086",u"\u2087",u"\u2088",
        u"\u2089",u"\u208A",u"\u208B",u"\u208C",u"\u208D",u"\u208E",u"\u20A0",
        u"\u20A1",u"\u20A2",u"\u20A3",u"\u20A4",u"\u20A5",u"\u20A6",u"\u20A7",
        u"\u20A8",u"\u20A9",u"\u20AA",u"\u20AB",u"\u20AC",u"\u20AD",u"\u20AE",
        u"\u20AF",u"\u20B0",u"\u20B1",u"\u20B2",u"\u20B3",u"\u20B4",u"\u20B5",
        u"\u20B6",u"\u20B7",u"\u20B8",u"\u20B9",u"\u20D0",u"\u20D1",u"\u20D2",
        u"\u20D3",u"\u20D4",u"\u20D5",u"\u20D6",u"\u20D7",u"\u20D8",u"\u20D9",
        u"\u20DA",u"\u20DB",u"\u20DC",u"\u20DD",u"\u20DE",u"\u20DF",u"\u20E0",
        u"\u20E1",u"\u20E2",u"\u20E3",u"\u20E4",u"\u20E5",u"\u20E6",u"\u20E7",
        u"\u20E8",u"\u20E9",u"\u20EA",u"\u20EB",u"\u20EC",u"\u20ED",u"\u20EE",
        u"\u20EF",u"\u20F0",u"\u2100",u"\u2101",u"\u2103",u"\u2104",u"\u2105",
        u"\u2106",u"\u2108",u"\u2109",u"\u2114",u"\u2116",u"\u2117",u"\u2118",
        u"\u211E",u"\u211F",u"\u2120",u"\u2121",u"\u2122",u"\u2123",u"\u2125",
        u"\u2127",u"\u2129",u"\u212E",u"\u213A",u"\u213B",u"\u2140",u"\u2141",
        u"\u2142",u"\u2143",u"\u2144",u"\u214A",u"\u214B",u"\u214C",u"\u214D",
        u"\u214F",u"\u2150",u"\u2151",u"\u2152",u"\u2153",u"\u2154",u"\u2155",
        u"\u2156",u"\u2157",u"\u2158",u"\u2159",u"\u215A",u"\u215B",u"\u215C",
        u"\u215D",u"\u215E",u"\u215F",u"\u2160",u"\u2161",u"\u2162",u"\u2163",
        u"\u2164",u"\u2165",u"\u2166",u"\u2167",u"\u2168",u"\u2169",u"\u216A",
        u"\u216B",u"\u216C",u"\u216D",u"\u216E",u"\u216F",u"\u2170",u"\u2171",
        u"\u2172",u"\u2173",u"\u2174",u"\u2175",u"\u2176",u"\u2177",u"\u2178",
        u"\u2179",u"\u217A",u"\u217B",u"\u217C",u"\u217D",u"\u217E",u"\u217F",
        u"\u2180",u"\u2181",u"\u2182",u"\u2185",u"\u2186",u"\u2187",u"\u2188",
        u"\u2189",u"\u2190",u"\u2191",u"\u2192",u"\u2193",u"\u2194",u"\u2195",
        u"\u2196",u"\u2197",u"\u2198",u"\u2199",u"\u219A",u"\u219B",u"\u219C",
        u"\u219D",u"\u219E",u"\u219F",u"\u21A0",u"\u21A1",u"\u21A2",u"\u21A3",
        u"\u21A4",u"\u21A5",u"\u21A6",u"\u21A7",u"\u21A8",u"\u21A9",u"\u21AA",
        u"\u21AB",u"\u21AC",u"\u21AD",u"\u21AE",u"\u21AF",u"\u21B0",u"\u21B1",
        u"\u21B2",u"\u21B3",u"\u21B4",u"\u21B5",u"\u21B6",u"\u21B7",u"\u21B8",
        u"\u21B9",u"\u21BA",u"\u21BB",u"\u21BC",u"\u21BD",u"\u21BE",u"\u21BF",
        u"\u21C0",u"\u21C1",u"\u21C2",u"\u21C3",u"\u21C4",u"\u21C5",u"\u21C6",
        u"\u21C7",u"\u21C8",u"\u21C9",u"\u21CA",u"\u21CB",u"\u21CC",u"\u21CD",
        u"\u21CE",u"\u21CF",u"\u21D0",u"\u21D1",u"\u21D2",u"\u21D3",u"\u21D4",
        u"\u21D5",u"\u21D6",u"\u21D7",u"\u21D8",u"\u21D9",u"\u21DA",u"\u21DB",
        u"\u21DC",u"\u21DD",u"\u21DE",u"\u21DF",u"\u21E0",u"\u21E1",u"\u21E2",
        u"\u21E3",u"\u21E4",u"\u21E5",u"\u21E6",u"\u21E7",u"\u21E8",u"\u21E9",
        u"\u21EA",u"\u21EB",u"\u21EC",u"\u21ED",u"\u21EE",u"\u21EF",u"\u21F0",
        u"\u21F1",u"\u21F2",u"\u21F3",u"\u21F4",u"\u21F5",u"\u21F6",u"\u21F7",
        u"\u21F8",u"\u21F9",u"\u21FA",u"\u21FB",u"\u21FC",u"\u21FD",u"\u21FE",
        u"\u21FF",u"\u2200",u"\u2201",u"\u2202",u"\u2203",u"\u2204",u"\u2205",
        u"\u2206",u"\u2207",u"\u2208",u"\u2209",u"\u220A",u"\u220B",u"\u220C",
        u"\u220D",u"\u220E",u"\u220F",u"\u2210",u"\u2211",u"\u2212",u"\u2213",
        u"\u2214",u"\u2215",u"\u2216",u"\u2217",u"\u2218",u"\u2219",u"\u221A",
        u"\u221B",u"\u221C",u"\u221D",u"\u221E",u"\u221F",u"\u2220",u"\u2221",
        u"\u2222",u"\u2223",u"\u2224",u"\u2225",u"\u2226",u"\u2227",u"\u2228",
        u"\u2229",u"\u222A",u"\u222B",u"\u222C",u"\u222D",u"\u222E",u"\u222F",
        u"\u2230",u"\u2231",u"\u2232",u"\u2233",u"\u2234",u"\u2235",u"\u2236",
        u"\u2237",u"\u2238",u"\u2239",u"\u223A",u"\u223B",u"\u223C",u"\u223D",
        u"\u223E",u"\u223F",u"\u2240",u"\u2241",u"\u2242",u"\u2243",u"\u2244",
        u"\u2245",u"\u2246",u"\u2247",u"\u2248",u"\u2249",u"\u224A",u"\u224B",
        u"\u224C",u"\u224D",u"\u224E",u"\u224F",u"\u2250",u"\u2251",u"\u2252",
        u"\u2253",u"\u2254",u"\u2255",u"\u2256",u"\u2257",u"\u2258",u"\u2259",
        u"\u225A",u"\u225B",u"\u225C",u"\u225D",u"\u225E",u"\u225F",u"\u2260",
        u"\u2261",u"\u2262",u"\u2263",u"\u2264",u"\u2265",u"\u2266",u"\u2267",
        u"\u2268",u"\u2269",u"\u226A",u"\u226B",u"\u226C",u"\u226D",u"\u226E",
        u"\u226F",u"\u2270",u"\u2271",u"\u2272",u"\u2273",u"\u2274",u"\u2275",
        u"\u2276",u"\u2277",u"\u2278",u"\u2279",u"\u227A",u"\u227B",u"\u227C",
        u"\u227D",u"\u227E",u"\u227F",u"\u2280",u"\u2281",u"\u2282",u"\u2283",
        u"\u2284",u"\u2285",u"\u2286",u"\u2287",u"\u2288",u"\u2289",u"\u228A",
        u"\u228B",u"\u228C",u"\u228D",u"\u228E",u"\u228F",u"\u2290",u"\u2291",
        u"\u2292",u"\u2293",u"\u2294",u"\u2295",u"\u2296",u"\u2297",u"\u2298",
        u"\u2299",u"\u229A",u"\u229B",u"\u229C",u"\u229D",u"\u229E",u"\u229F",
        u"\u22A0",u"\u22A1",u"\u22A2",u"\u22A3",u"\u22A4",u"\u22A5",u"\u22A6",
        u"\u22A7",u"\u22A8",u"\u22A9",u"\u22AA",u"\u22AB",u"\u22AC",u"\u22AD",
        u"\u22AE",u"\u22AF",u"\u22B0",u"\u22B1",u"\u22B2",u"\u22B3",u"\u22B4",
        u"\u22B5",u"\u22B6",u"\u22B7",u"\u22B8",u"\u22B9",u"\u22BA",u"\u22BB",
        u"\u22BC",u"\u22BD",u"\u22BE",u"\u22BF",u"\u22C0",u"\u22C1",u"\u22C2",
        u"\u22C3",u"\u22C4",u"\u22C5",u"\u22C6",u"\u22C7",u"\u22C8",u"\u22C9",
        u"\u22CA",u"\u22CB",u"\u22CC",u"\u22CD",u"\u22CE",u"\u22CF",u"\u22D0",
        u"\u22D1",u"\u22D2",u"\u22D3",u"\u22D4",u"\u22D5",u"\u22D6",u"\u22D7",
        u"\u22D8",u"\u22D9",u"\u22DA",u"\u22DB",u"\u22DC",u"\u22DD",u"\u22DE",
        u"\u22DF",u"\u22E0",u"\u22E1",u"\u22E2",u"\u22E3",u"\u22E4",u"\u22E5",
        u"\u22E6",u"\u22E7",u"\u22E8",u"\u22E9",u"\u22EA",u"\u22EB",u"\u22EC",
        u"\u22ED",u"\u22EE",u"\u22EF",u"\u22F0",u"\u22F1",u"\u22F2",u"\u22F3",
        u"\u22F4",u"\u22F5",u"\u22F6",u"\u22F7",u"\u22F8",u"\u22F9",u"\u22FA",
        u"\u22FB",u"\u22FC",u"\u22FD",u"\u22FE",u"\u22FF",u"\u2300",u"\u2301",
        u"\u2302",u"\u2303",u"\u2304",u"\u2305",u"\u2306",u"\u2307",u"\u2308",
        u"\u2309",u"\u230A",u"\u230B",u"\u230C",u"\u230D",u"\u230E",u"\u230F",
        u"\u2310",u"\u2311",u"\u2312",u"\u2313",u"\u2314",u"\u2315",u"\u2316",
        u"\u2317",u"\u2318",u"\u2319",u"\u231A",u"\u231B",u"\u231C",u"\u231D",
        u"\u231E",u"\u231F",u"\u2320",u"\u2321",u"\u2322",u"\u2323",u"\u2324",
        u"\u2325",u"\u2326",u"\u2327",u"\u2328",u"\u2329",u"\u232A",u"\u232B",
        u"\u232C",u"\u232D",u"\u232E",u"\u232F",u"\u2330",u"\u2331",u"\u2332",
        u"\u2333",u"\u2334",u"\u2335",u"\u2336",u"\u2337",u"\u2338",u"\u2339",
        u"\u233A",u"\u233B",u"\u233C",u"\u233D",u"\u233E",u"\u233F",u"\u2340",
        u"\u2341",u"\u2342",u"\u2343",u"\u2344",u"\u2345",u"\u2346",u"\u2347",
        u"\u2348",u"\u2349",u"\u234A",u"\u234B",u"\u234C",u"\u234D",u"\u234E",
        u"\u234F",u"\u2350",u"\u2351",u"\u2352",u"\u2353",u"\u2354",u"\u2355",
        u"\u2356",u"\u2357",u"\u2358",u"\u2359",u"\u235A",u"\u235B",u"\u235C",
        u"\u235D",u"\u235E",u"\u235F",u"\u2360",u"\u2361",u"\u2362",u"\u2363",
        u"\u2364",u"\u2365",u"\u2366",u"\u2367",u"\u2368",u"\u2369",u"\u236A",
        u"\u236B",u"\u236C",u"\u236D",u"\u236E",u"\u236F",u"\u2370",u"\u2371",
        u"\u2372",u"\u2373",u"\u2374",u"\u2375",u"\u2376",u"\u2377",u"\u2378",
        u"\u2379",u"\u237A",u"\u237B",u"\u237C",u"\u237D",u"\u237E",u"\u237F",
        u"\u2380",u"\u2381",u"\u2382",u"\u2383",u"\u2384",u"\u2385",u"\u2386",
        u"\u2387",u"\u2388",u"\u2389",u"\u238A",u"\u238B",u"\u238C",u"\u238D",
        u"\u238E",u"\u238F",u"\u2390",u"\u2391",u"\u2392",u"\u2393",u"\u2394",
        u"\u2395",u"\u2396",u"\u2397",u"\u2398",u"\u2399",u"\u239A",u"\u239B",
        u"\u239C",u"\u239D",u"\u239E",u"\u239F",u"\u23A0",u"\u23A1",u"\u23A2",
        u"\u23A3",u"\u23A4",u"\u23A5",u"\u23A6",u"\u23A7",u"\u23A8",u"\u23A9",
        u"\u23AA",u"\u23AB",u"\u23AC",u"\u23AD",u"\u23AE",u"\u23AF",u"\u23B0",
        u"\u23B1",u"\u23B2",u"\u23B3",u"\u23B4",u"\u23B5",u"\u23B6",u"\u23B7",
        u"\u23B8",u"\u23B9",u"\u23BA",u"\u23BB",u"\u23BC",u"\u23BD",u"\u23BE",
        u"\u23BF",u"\u23C0",u"\u23C1",u"\u23C2",u"\u23C3",u"\u23C4",u"\u23C5",
        u"\u23C6",u"\u23C7",u"\u23C8",u"\u23C9",u"\u23CA",u"\u23CB",u"\u23CC",
        u"\u23CD",u"\u23CE",u"\u23CF",u"\u23D0",u"\u23D1",u"\u23D2",u"\u23D3",
        u"\u23D4",u"\u23D5",u"\u23D6",u"\u23D7",u"\u23D8",u"\u23D9",u"\u23DA",
        u"\u23DB",u"\u23DC",u"\u23DD",u"\u23DE",u"\u23DF",u"\u23E0",u"\u23E1",
        u"\u23E2",u"\u23E3",u"\u23E4",u"\u23E5",u"\u23E6",u"\u23E7",u"\u23E8",
        u"\u23E9",u"\u23EA",u"\u23EB",u"\u23EC",u"\u23ED",u"\u23EE",u"\u23EF",
        u"\u23F0",u"\u23F1",u"\u23F2",u"\u23F3",u"\u2400",u"\u2401",u"\u2402",
        u"\u2403",u"\u2404",u"\u2405",u"\u2406",u"\u2407",u"\u2408",u"\u2409",
        u"\u240A",u"\u240B",u"\u240C",u"\u240D",u"\u240E",u"\u240F",u"\u2410",
        u"\u2411",u"\u2412",u"\u2413",u"\u2414",u"\u2415",u"\u2416",u"\u2417",
        u"\u2418",u"\u2419",u"\u241A",u"\u241B",u"\u241C",u"\u241D",u"\u241E",
        u"\u241F",u"\u2420",u"\u2421",u"\u2422",u"\u2423",u"\u2424",u"\u2425",
        u"\u2426",u"\u2440",u"\u2441",u"\u2442",u"\u2443",u"\u2444",u"\u2445",
        u"\u2446",u"\u2447",u"\u2448",u"\u2449",u"\u244A",u"\u2460",u"\u2461",
        u"\u2462",u"\u2463",u"\u2464",u"\u2465",u"\u2466",u"\u2467",u"\u2468",
        u"\u2469",u"\u246A",u"\u246B",u"\u246C",u"\u246D",u"\u246E",u"\u246F",
        u"\u2470",u"\u2471",u"\u2472",u"\u2473",u"\u2474",u"\u2475",u"\u2476",
        u"\u2477",u"\u2478",u"\u2479",u"\u247A",u"\u247B",u"\u247C",u"\u247D",
        u"\u247E",u"\u247F",u"\u2480",u"\u2481",u"\u2482",u"\u2483",u"\u2484",
        u"\u2485",u"\u2486",u"\u2487",u"\u2488",u"\u2489",u"\u248A",u"\u248B",
        u"\u248C",u"\u248D",u"\u248E",u"\u248F",u"\u2490",u"\u2491",u"\u2492",
        u"\u2493",u"\u2494",u"\u2495",u"\u2496",u"\u2497",u"\u2498",u"\u2499",
        u"\u249A",u"\u249B",u"\u249C",u"\u249D",u"\u249E",u"\u249F",u"\u24A0",
        u"\u24A1",u"\u24A2",u"\u24A3",u"\u24A4",u"\u24A5",u"\u24A6",u"\u24A7",
        u"\u24A8",u"\u24A9",u"\u24AA",u"\u24AB",u"\u24AC",u"\u24AD",u"\u24AE",
        u"\u24AF",u"\u24B0",u"\u24B1",u"\u24B2",u"\u24B3",u"\u24B4",u"\u24B5",
        u"\u24B6",u"\u24B7",u"\u24B8",u"\u24B9",u"\u24BA",u"\u24BB",u"\u24BC",
        u"\u24BD",u"\u24BE",u"\u24BF",u"\u24C0",u"\u24C1",u"\u24C2",u"\u24C3",
        u"\u24C4",u"\u24C5",u"\u24C6",u"\u24C7",u"\u24C8",u"\u24C9",u"\u24CA",
        u"\u24CB",u"\u24CC",u"\u24CD",u"\u24CE",u"\u24CF",u"\u24D0",u"\u24D1",
        u"\u24D2",u"\u24D3",u"\u24D4",u"\u24D5",u"\u24D6",u"\u24D7",u"\u24D8",
        u"\u24D9",u"\u24DA",u"\u24DB",u"\u24DC",u"\u24DD",u"\u24DE",u"\u24DF",
        u"\u24E0",u"\u24E1",u"\u24E2",u"\u24E3",u"\u24E4",u"\u24E5",u"\u24E6",
        u"\u24E7",u"\u24E8",u"\u24E9",u"\u24EA",u"\u24EB",u"\u24EC",u"\u24ED",
        u"\u24EE",u"\u24EF",u"\u24F0",u"\u24F1",u"\u24F2",u"\u24F3",u"\u24F4",
        u"\u24F5",u"\u24F6",u"\u24F7",u"\u24F8",u"\u24F9",u"\u24FA",u"\u24FB",
        u"\u24FC",u"\u24FD",u"\u24FE",u"\u24FF",u"\u2500",u"\u2501",u"\u2502",
        u"\u2503",u"\u2504",u"\u2505",u"\u2506",u"\u2507",u"\u2508",u"\u2509",
        u"\u250A",u"\u250B",u"\u250C",u"\u250D",u"\u250E",u"\u250F",u"\u2510",
        u"\u2511",u"\u2512",u"\u2513",u"\u2514",u"\u2515",u"\u2516",u"\u2517",
        u"\u2518",u"\u2519",u"\u251A",u"\u251B",u"\u251C",u"\u251D",u"\u251E",
        u"\u251F",u"\u2520",u"\u2521",u"\u2522",u"\u2523",u"\u2524",u"\u2525",
        u"\u2526",u"\u2527",u"\u2528",u"\u2529",u"\u252A",u"\u252B",u"\u252C",
        u"\u252D",u"\u252E",u"\u252F",u"\u2530",u"\u2531",u"\u2532",u"\u2533",
        u"\u2534",u"\u2535",u"\u2536",u"\u2537",u"\u2538",u"\u2539",u"\u253A",
        u"\u253B",u"\u253C",u"\u253D",u"\u253E",u"\u253F",u"\u2540",u"\u2541",
        u"\u2542",u"\u2543",u"\u2544",u"\u2545",u"\u2546",u"\u2547",u"\u2548",
        u"\u2549",u"\u254A",u"\u254B",u"\u254C",u"\u254D",u"\u254E",u"\u254F",
        u"\u2550",u"\u2551",u"\u2552",u"\u2553",u"\u2554",u"\u2555",u"\u2556",
        u"\u2557",u"\u2558",u"\u2559",u"\u255A",u"\u255B",u"\u255C",u"\u255D",
        u"\u255E",u"\u255F",u"\u2560",u"\u2561",u"\u2562",u"\u2563",u"\u2564",
        u"\u2565",u"\u2566",u"\u2567",u"\u2568",u"\u2569",u"\u256A",u"\u256B",
        u"\u256C",u"\u256D",u"\u256E",u"\u256F",u"\u2570",u"\u2571",u"\u2572",
        u"\u2573",u"\u2574",u"\u2575",u"\u2576",u"\u2577",u"\u2578",u"\u2579",
        u"\u257A",u"\u257B",u"\u257C",u"\u257D",u"\u257E",u"\u257F",u"\u2580",
        u"\u2581",u"\u2582",u"\u2583",u"\u2584",u"\u2585",u"\u2586",u"\u2587",
        u"\u2588",u"\u2589",u"\u258A",u"\u258B",u"\u258C",u"\u258D",u"\u258E",
        u"\u258F",u"\u2590",u"\u2591",u"\u2592",u"\u2593",u"\u2594",u"\u2595",
        u"\u2596",u"\u2597",u"\u2598",u"\u2599",u"\u259A",u"\u259B",u"\u259C",
        u"\u259D",u"\u259E",u"\u259F",u"\u25A0",u"\u25A1",u"\u25A2",u"\u25A3",
        u"\u25A4",u"\u25A5",u"\u25A6",u"\u25A7",u"\u25A8",u"\u25A9",u"\u25AA",
        u"\u25AB",u"\u25AC",u"\u25AD",u"\u25AE",u"\u25AF",u"\u25B0",u"\u25B1",
        u"\u25B2",u"\u25B3",u"\u25B4",u"\u25B5",u"\u25B6",u"\u25B7",u"\u25B8",
        u"\u25B9",u"\u25BA",u"\u25BB",u"\u25BC",u"\u25BD",u"\u25BE",u"\u25BF",
        u"\u25C0",u"\u25C1",u"\u25C2",u"\u25C3",u"\u25C4",u"\u25C5",u"\u25C6",
        u"\u25C7",u"\u25C8",u"\u25C9",u"\u25CA",u"\u25CB",u"\u25CC",u"\u25CD",
        u"\u25CE",u"\u25CF",u"\u25D0",u"\u25D1",u"\u25D2",u"\u25D3",u"\u25D4",
        u"\u25D5",u"\u25D6",u"\u25D7",u"\u25D8",u"\u25D9",u"\u25DA",u"\u25DB",
        u"\u25DC",u"\u25DD",u"\u25DE",u"\u25DF",u"\u25E0",u"\u25E1",u"\u25E2",
        u"\u25E3",u"\u25E4",u"\u25E5",u"\u25E6",u"\u25E7",u"\u25E8",u"\u25E9",
        u"\u25EA",u"\u25EB",u"\u25EC",u"\u25ED",u"\u25EE",u"\u25EF",u"\u25F0",
        u"\u25F1",u"\u25F2",u"\u25F3",u"\u25F4",u"\u25F5",u"\u25F6",u"\u25F7",
        u"\u25F8",u"\u25F9",u"\u25FA",u"\u25FB",u"\u25FC",u"\u25FD",u"\u25FE",
        u"\u25FF",u"\u2600",u"\u2601",u"\u2602",u"\u2603",u"\u2604",u"\u2605",
        u"\u2606",u"\u2607",u"\u2608",u"\u2609",u"\u260A",u"\u260B",u"\u260C",
        u"\u260D",u"\u260E",u"\u260F",u"\u2610",u"\u2611",u"\u2612",u"\u2613",
        u"\u2614",u"\u2615",u"\u2616",u"\u2617",u"\u2618",u"\u2619",u"\u261A",
        u"\u261B",u"\u261C",u"\u261D",u"\u261E",u"\u261F",u"\u2620",u"\u2621",
        u"\u2622",u"\u2623",u"\u2624",u"\u2625",u"\u2626",u"\u2627",u"\u2628",
        u"\u2629",u"\u262A",u"\u262B",u"\u262C",u"\u262D",u"\u262E",u"\u262F",
        u"\u2630",u"\u2631",u"\u2632",u"\u2633",u"\u2634",u"\u2635",u"\u2636",
        u"\u2637",u"\u2638",u"\u2639",u"\u263A",u"\u263B",u"\u263C",u"\u263D",
        u"\u263E",u"\u263F",u"\u2640",u"\u2641",u"\u2642",u"\u2643",u"\u2644",
        u"\u2645",u"\u2646",u"\u2647",u"\u2648",u"\u2649",u"\u264A",u"\u264B",
        u"\u264C",u"\u264D",u"\u264E",u"\u264F",u"\u2650",u"\u2651",u"\u2652",
        u"\u2653",u"\u2654",u"\u2655",u"\u2656",u"\u2657",u"\u2658",u"\u2659",
        u"\u265A",u"\u265B",u"\u265C",u"\u265D",u"\u265E",u"\u265F",u"\u2660",
        u"\u2661",u"\u2662",u"\u2663",u"\u2664",u"\u2665",u"\u2666",u"\u2667",
        u"\u2668",u"\u2669",u"\u266A",u"\u266B",u"\u266C",u"\u266D",u"\u266E",
        u"\u266F",u"\u2670",u"\u2671",u"\u2672",u"\u2673",u"\u2674",u"\u2675",
        u"\u2676",u"\u2677",u"\u2678",u"\u2679",u"\u267A",u"\u267B",u"\u267C",
        u"\u267D",u"\u267E",u"\u267F",u"\u2680",u"\u2681",u"\u2682",u"\u2683",
        u"\u2684",u"\u2685",u"\u2686",u"\u2687",u"\u2688",u"\u2689",u"\u268A",
        u"\u268B",u"\u268C",u"\u268D",u"\u268E",u"\u268F",u"\u2690",u"\u2691",
        u"\u2692",u"\u2693",u"\u2694",u"\u2695",u"\u2696",u"\u2697",u"\u2698",
        u"\u2699",u"\u269A",u"\u269B",u"\u269C",u"\u269D",u"\u269E",u"\u269F",
        u"\u26A0",u"\u26A1",u"\u26A2",u"\u26A3",u"\u26A4",u"\u26A5",u"\u26A6",
        u"\u26A7",u"\u26A8",u"\u26A9",u"\u26AA",u"\u26AB",u"\u26AC",u"\u26AD",
        u"\u26AE",u"\u26AF",u"\u26B0",u"\u26B1",u"\u26B2",u"\u26B3",u"\u26B4",
        u"\u26B5",u"\u26B6",u"\u26B7",u"\u26B8",u"\u26B9",u"\u26BA",u"\u26BB",
        u"\u26BC",u"\u26BD",u"\u26BE",u"\u26BF",u"\u26C0",u"\u26C1",u"\u26C2",
        u"\u26C3",u"\u26C4",u"\u26C5",u"\u26C6",u"\u26C7",u"\u26C8",u"\u26C9",
        u"\u26CA",u"\u26CB",u"\u26CC",u"\u26CD",u"\u26CE",u"\u26CF",u"\u26D0",
        u"\u26D1",u"\u26D2",u"\u26D3",u"\u26D4",u"\u26D5",u"\u26D6",u"\u26D7",
        u"\u26D8",u"\u26D9",u"\u26DA",u"\u26DB",u"\u26DC",u"\u26DD",u"\u26DE",
        u"\u26DF",u"\u26E0",u"\u26E1",u"\u26E2",u"\u26E3",u"\u26E4",u"\u26E5",
        u"\u26E6",u"\u26E7",u"\u26E8",u"\u26E9",u"\u26EA",u"\u26EB",u"\u26EC",
        u"\u26ED",u"\u26EE",u"\u26EF",u"\u26F0",u"\u26F1",u"\u26F2",u"\u26F3",
        u"\u26F4",u"\u26F5",u"\u26F6",u"\u26F7",u"\u26F8",u"\u26F9",u"\u26FA",
        u"\u26FB",u"\u26FC",u"\u26FD",u"\u26FE",u"\u26FF",u"\u2701",u"\u2702",
        u"\u2703",u"\u2704",u"\u2705",u"\u2706",u"\u2707",u"\u2708",u"\u2709",
        u"\u270A",u"\u270B",u"\u270C",u"\u270D",u"\u270E",u"\u270F",u"\u2710",
        u"\u2711",u"\u2712",u"\u2713",u"\u2714",u"\u2715",u"\u2716",u"\u2717",
        u"\u2718",u"\u2719",u"\u271A",u"\u271B",u"\u271C",u"\u271D",u"\u271E",
        u"\u271F",u"\u2720",u"\u2721",u"\u2722",u"\u2723",u"\u2724",u"\u2725",
        u"\u2726",u"\u2727",u"\u2728",u"\u2729",u"\u272A",u"\u272B",u"\u272C",
        u"\u272D",u"\u272E",u"\u272F",u"\u2730",u"\u2731",u"\u2732",u"\u2733",
        u"\u2734",u"\u2735",u"\u2736",u"\u2737",u"\u2738",u"\u2739",u"\u273A",
        u"\u273B",u"\u273C",u"\u273D",u"\u273E",u"\u273F",u"\u2740",u"\u2741",
        u"\u2742",u"\u2743",u"\u2744",u"\u2745",u"\u2746",u"\u2747",u"\u2748",
        u"\u2749",u"\u274A",u"\u274B",u"\u274C",u"\u274D",u"\u274E",u"\u274F",
        u"\u2750",u"\u2751",u"\u2752",u"\u2753",u"\u2754",u"\u2755",u"\u2756",
        u"\u2757",u"\u2758",u"\u2759",u"\u275A",u"\u275B",u"\u275C",u"\u275D",
        u"\u275E",u"\u275F",u"\u2760",u"\u2761",u"\u2762",u"\u2763",u"\u2764",
        u"\u2765",u"\u2766",u"\u2767",u"\u2768",u"\u2769",u"\u276A",u"\u276B",
        u"\u276C",u"\u276D",u"\u276E",u"\u276F",u"\u2770",u"\u2771",u"\u2772",
        u"\u2773",u"\u2774",u"\u2775",u"\u2776",u"\u2777",u"\u2778",u"\u2779",
        u"\u277A",u"\u277B",u"\u277C",u"\u277D",u"\u277E",u"\u277F",u"\u2780",
        u"\u2781",u"\u2782",u"\u2783",u"\u2784",u"\u2785",u"\u2786",u"\u2787",
        u"\u2788",u"\u2789",u"\u278A",u"\u278B",u"\u278C",u"\u278D",u"\u278E",
        u"\u278F",u"\u2790",u"\u2791",u"\u2792",u"\u2793",u"\u2794",u"\u2795",
        u"\u2796",u"\u2797",u"\u2798",u"\u2799",u"\u279A",u"\u279B",u"\u279C",
        u"\u279D",u"\u279E",u"\u279F",u"\u27A0",u"\u27A1",u"\u27A2",u"\u27A3",
        u"\u27A4",u"\u27A5",u"\u27A6",u"\u27A7",u"\u27A8",u"\u27A9",u"\u27AA",
        u"\u27AB",u"\u27AC",u"\u27AD",u"\u27AE",u"\u27AF",u"\u27B0",u"\u27B1",
        u"\u27B2",u"\u27B3",u"\u27B4",u"\u27B5",u"\u27B6",u"\u27B7",u"\u27B8",
        u"\u27B9",u"\u27BA",u"\u27BB",u"\u27BC",u"\u27BD",u"\u27BE",u"\u27BF",
        u"\u27C0",u"\u27C1",u"\u27C2",u"\u27C3",u"\u27C4",u"\u27C5",u"\u27C6",
        u"\u27C7",u"\u27C8",u"\u27C9",u"\u27CA",u"\u27CC",u"\u27CE",u"\u27CF",
        u"\u27D0",u"\u27D1",u"\u27D2",u"\u27D3",u"\u27D4",u"\u27D5",u"\u27D6",
        u"\u27D7",u"\u27D8",u"\u27D9",u"\u27DA",u"\u27DB",u"\u27DC",u"\u27DD",
        u"\u27DE",u"\u27DF",u"\u27E0",u"\u27E1",u"\u27E2",u"\u27E3",u"\u27E4",
        u"\u27E5",u"\u27E6",u"\u27E7",u"\u27E8",u"\u27E9",u"\u27EA",u"\u27EB",
        u"\u27EC",u"\u27ED",u"\u27EE",u"\u27EF",u"\u27F0",u"\u27F1",u"\u27F2",
        u"\u27F3",u"\u27F4",u"\u27F5",u"\u27F6",u"\u27F7",u"\u27F8",u"\u27F9",
        u"\u27FA",u"\u27FB",u"\u27FC",u"\u27FD",u"\u27FE",u"\u27FF",u"\u2800",
        u"\u2801",u"\u2802",u"\u2803",u"\u2804",u"\u2805",u"\u2806",u"\u2807",
        u"\u2808",u"\u2809",u"\u280A",u"\u280B",u"\u280C",u"\u280D",u"\u280E",
        u"\u280F",u"\u2810",u"\u2811",u"\u2812",u"\u2813",u"\u2814",u"\u2815",
        u"\u2816",u"\u2817",u"\u2818",u"\u2819",u"\u281A",u"\u281B",u"\u281C",
        u"\u281D",u"\u281E",u"\u281F",u"\u2820",u"\u2821",u"\u2822",u"\u2823",
        u"\u2824",u"\u2825",u"\u2826",u"\u2827",u"\u2828",u"\u2829",u"\u282A",
        u"\u282B",u"\u282C",u"\u282D",u"\u282E",u"\u282F",u"\u2830",u"\u2831",
        u"\u2832",u"\u2833",u"\u2834",u"\u2835",u"\u2836",u"\u2837",u"\u2838",
        u"\u2839",u"\u283A",u"\u283B",u"\u283C",u"\u283D",u"\u283E",u"\u283F",
        u"\u2840",u"\u2841",u"\u2842",u"\u2843",u"\u2844",u"\u2845",u"\u2846",
        u"\u2847",u"\u2848",u"\u2849",u"\u284A",u"\u284B",u"\u284C",u"\u284D",
        u"\u284E",u"\u284F",u"\u2850",u"\u2851",u"\u2852",u"\u2853",u"\u2854",
        u"\u2855",u"\u2856",u"\u2857",u"\u2858",u"\u2859",u"\u285A",u"\u285B",
        u"\u285C",u"\u285D",u"\u285E",u"\u285F",u"\u2860",u"\u2861",u"\u2862",
        u"\u2863",u"\u2864",u"\u2865",u"\u2866",u"\u2867",u"\u2868",u"\u2869",
        u"\u286A",u"\u286B",u"\u286C",u"\u286D",u"\u286E",u"\u286F",u"\u2870",
        u"\u2871",u"\u2872",u"\u2873",u"\u2874",u"\u2875",u"\u2876",u"\u2877",
        u"\u2878",u"\u2879",u"\u287A",u"\u287B",u"\u287C",u"\u287D",u"\u287E",
        u"\u287F",u"\u2880",u"\u2881",u"\u2882",u"\u2883",u"\u2884",u"\u2885",
        u"\u2886",u"\u2887",u"\u2888",u"\u2889",u"\u288A",u"\u288B",u"\u288C",
        u"\u288D",u"\u288E",u"\u288F",u"\u2890",u"\u2891",u"\u2892",u"\u2893",
        u"\u2894",u"\u2895",u"\u2896",u"\u2897",u"\u2898",u"\u2899",u"\u289A",
        u"\u289B",u"\u289C",u"\u289D",u"\u289E",u"\u289F",u"\u28A0",u"\u28A1",
        u"\u28A2",u"\u28A3",u"\u28A4",u"\u28A5",u"\u28A6",u"\u28A7",u"\u28A8",
        u"\u28A9",u"\u28AA",u"\u28AB",u"\u28AC",u"\u28AD",u"\u28AE",u"\u28AF",
        u"\u28B0",u"\u28B1",u"\u28B2",u"\u28B3",u"\u28B4",u"\u28B5",u"\u28B6",
        u"\u28B7",u"\u28B8",u"\u28B9",u"\u28BA",u"\u28BB",u"\u28BC",u"\u28BD",
        u"\u28BE",u"\u28BF",u"\u28C0",u"\u28C1",u"\u28C2",u"\u28C3",u"\u28C4",
        u"\u28C5",u"\u28C6",u"\u28C7",u"\u28C8",u"\u28C9",u"\u28CA",u"\u28CB",
        u"\u28CC",u"\u28CD",u"\u28CE",u"\u28CF",u"\u28D0",u"\u28D1",u"\u28D2",
        u"\u28D3",u"\u28D4",u"\u28D5",u"\u28D6",u"\u28D7",u"\u28D8",u"\u28D9",
        u"\u28DA",u"\u28DB",u"\u28DC",u"\u28DD",u"\u28DE",u"\u28DF",u"\u28E0",
        u"\u28E1",u"\u28E2",u"\u28E3",u"\u28E4",u"\u28E5",u"\u28E6",u"\u28E7",
        u"\u28E8",u"\u28E9",u"\u28EA",u"\u28EB",u"\u28EC",u"\u28ED",u"\u28EE",
        u"\u28EF",u"\u28F0",u"\u28F1",u"\u28F2",u"\u28F3",u"\u28F4",u"\u28F5",
        u"\u28F6",u"\u28F7",u"\u28F8",u"\u28F9",u"\u28FA",u"\u28FB",u"\u28FC",
        u"\u28FD",u"\u28FE",u"\u28FF",u"\u2900",u"\u2901",u"\u2902",u"\u2903",
        u"\u2904",u"\u2905",u"\u2906",u"\u2907",u"\u2908",u"\u2909",u"\u290A",
        u"\u290B",u"\u290C",u"\u290D",u"\u290E",u"\u290F",u"\u2910",u"\u2911",
        u"\u2912",u"\u2913",u"\u2914",u"\u2915",u"\u2916",u"\u2917",u"\u2918",
        u"\u2919",u"\u291A",u"\u291B",u"\u291C",u"\u291D",u"\u291E",u"\u291F",
        u"\u2920",u"\u2921",u"\u2922",u"\u2923",u"\u2924",u"\u2925",u"\u2926",
        u"\u2927",u"\u2928",u"\u2929",u"\u292A",u"\u292B",u"\u292C",u"\u292D",
        u"\u292E",u"\u292F",u"\u2930",u"\u2931",u"\u2932",u"\u2933",u"\u2934",
        u"\u2935",u"\u2936",u"\u2937",u"\u2938",u"\u2939",u"\u293A",u"\u293B",
        u"\u293C",u"\u293D",u"\u293E",u"\u293F",u"\u2940",u"\u2941",u"\u2942",
        u"\u2943",u"\u2944",u"\u2945",u"\u2946",u"\u2947",u"\u2948",u"\u2949",
        u"\u294A",u"\u294B",u"\u294C",u"\u294D",u"\u294E",u"\u294F",u"\u2950",
        u"\u2951",u"\u2952",u"\u2953",u"\u2954",u"\u2955",u"\u2956",u"\u2957",
        u"\u2958",u"\u2959",u"\u295A",u"\u295B",u"\u295C",u"\u295D",u"\u295E",
        u"\u295F",u"\u2960",u"\u2961",u"\u2962",u"\u2963",u"\u2964",u"\u2965",
        u"\u2966",u"\u2967",u"\u2968",u"\u2969",u"\u296A",u"\u296B",u"\u296C",
        u"\u296D",u"\u296E",u"\u296F",u"\u2970",u"\u2971",u"\u2972",u"\u2973",
        u"\u2974",u"\u2975",u"\u2976",u"\u2977",u"\u2978",u"\u2979",u"\u297A",
        u"\u297B",u"\u297C",u"\u297D",u"\u297E",u"\u297F",u"\u2980",u"\u2981",
        u"\u2982",u"\u2983",u"\u2984",u"\u2985",u"\u2986",u"\u2987",u"\u2988",
        u"\u2989",u"\u298A",u"\u298B",u"\u298C",u"\u298D",u"\u298E",u"\u298F",
        u"\u2990",u"\u2991",u"\u2992",u"\u2993",u"\u2994",u"\u2995",u"\u2996",
        u"\u2997",u"\u2998",u"\u2999",u"\u299A",u"\u299B",u"\u299C",u"\u299D",
        u"\u299E",u"\u299F",u"\u29A0",u"\u29A1",u"\u29A2",u"\u29A3",u"\u29A4",
        u"\u29A5",u"\u29A6",u"\u29A7",u"\u29A8",u"\u29A9",u"\u29AA",u"\u29AB",
        u"\u29AC",u"\u29AD",u"\u29AE",u"\u29AF",u"\u29B0",u"\u29B1",u"\u29B2",
        u"\u29B3",u"\u29B4",u"\u29B5",u"\u29B6",u"\u29B7",u"\u29B8",u"\u29B9",
        u"\u29BA",u"\u29BB",u"\u29BC",u"\u29BD",u"\u29BE",u"\u29BF",u"\u29C0",
        u"\u29C1",u"\u29C2",u"\u29C3",u"\u29C4",u"\u29C5",u"\u29C6",u"\u29C7",
        u"\u29C8",u"\u29C9",u"\u29CA",u"\u29CB",u"\u29CC",u"\u29CD",u"\u29CE",
        u"\u29CF",u"\u29D0",u"\u29D1",u"\u29D2",u"\u29D3",u"\u29D4",u"\u29D5",
        u"\u29D6",u"\u29D7",u"\u29D8",u"\u29D9",u"\u29DA",u"\u29DB",u"\u29DC",
        u"\u29DD",u"\u29DE",u"\u29DF",u"\u29E0",u"\u29E1",u"\u29E2",u"\u29E3",
        u"\u29E4",u"\u29E5",u"\u29E6",u"\u29E7",u"\u29E8",u"\u29E9",u"\u29EA",
        u"\u29EB",u"\u29EC",u"\u29ED",u"\u29EE",u"\u29EF",u"\u29F0",u"\u29F1",
        u"\u29F2",u"\u29F3",u"\u29F4",u"\u29F5",u"\u29F6",u"\u29F7",u"\u29F8",
        u"\u29F9",u"\u29FA",u"\u29FB",u"\u29FC",u"\u29FD",u"\u29FE",u"\u29FF",
        u"\u2A00",u"\u2A01",u"\u2A02",u"\u2A03",u"\u2A04",u"\u2A05",u"\u2A06",
        u"\u2A07",u"\u2A08",u"\u2A09",u"\u2A0A",u"\u2A0B",u"\u2A0C",u"\u2A0D",
        u"\u2A0E",u"\u2A0F",u"\u2A10",u"\u2A11",u"\u2A12",u"\u2A13",u"\u2A14",
        u"\u2A15",u"\u2A16",u"\u2A17",u"\u2A18",u"\u2A19",u"\u2A1A",u"\u2A1B",
        u"\u2A1C",u"\u2A1D",u"\u2A1E",u"\u2A1F",u"\u2A20",u"\u2A21",u"\u2A22",
        u"\u2A23",u"\u2A24",u"\u2A25",u"\u2A26",u"\u2A27",u"\u2A28",u"\u2A29",
        u"\u2A2A",u"\u2A2B",u"\u2A2C",u"\u2A2D",u"\u2A2E",u"\u2A2F",u"\u2A30",
        u"\u2A31",u"\u2A32",u"\u2A33",u"\u2A34",u"\u2A35",u"\u2A36",u"\u2A37",
        u"\u2A38",u"\u2A39",u"\u2A3A",u"\u2A3B",u"\u2A3C",u"\u2A3D",u"\u2A3E",
        u"\u2A3F",u"\u2A40",u"\u2A41",u"\u2A42",u"\u2A43",u"\u2A44",u"\u2A45",
        u"\u2A46",u"\u2A47",u"\u2A48",u"\u2A49",u"\u2A4A",u"\u2A4B",u"\u2A4C",
        u"\u2A4D",u"\u2A4E",u"\u2A4F",u"\u2A50",u"\u2A51",u"\u2A52",u"\u2A53",
        u"\u2A54",u"\u2A55",u"\u2A56",u"\u2A57",u"\u2A58",u"\u2A59",u"\u2A5A",
        u"\u2A5B",u"\u2A5C",u"\u2A5D",u"\u2A5E",u"\u2A5F",u"\u2A60",u"\u2A61",
        u"\u2A62",u"\u2A63",u"\u2A64",u"\u2A65",u"\u2A66",u"\u2A67",u"\u2A68",
        u"\u2A69",u"\u2A6A",u"\u2A6B",u"\u2A6C",u"\u2A6D",u"\u2A6E",u"\u2A6F",
        u"\u2A70",u"\u2A71",u"\u2A72",u"\u2A73",u"\u2A74",u"\u2A75",u"\u2A76",
        u"\u2A77",u"\u2A78",u"\u2A79",u"\u2A7A",u"\u2A7B",u"\u2A7C",u"\u2A7D",
        u"\u2A7E",u"\u2A7F",u"\u2A80",u"\u2A81",u"\u2A82",u"\u2A83",u"\u2A84",
        u"\u2A85",u"\u2A86",u"\u2A87",u"\u2A88",u"\u2A89",u"\u2A8A",u"\u2A8B",
        u"\u2A8C",u"\u2A8D",u"\u2A8E",u"\u2A8F",u"\u2A90",u"\u2A91",u"\u2A92",
        u"\u2A93",u"\u2A94",u"\u2A95",u"\u2A96",u"\u2A97",u"\u2A98",u"\u2A99",
        u"\u2A9A",u"\u2A9B",u"\u2A9C",u"\u2A9D",u"\u2A9E",u"\u2A9F",u"\u2AA0",
        u"\u2AA1",u"\u2AA2",u"\u2AA3",u"\u2AA4",u"\u2AA5",u"\u2AA6",u"\u2AA7",
        u"\u2AA8",u"\u2AA9",u"\u2AAA",u"\u2AAB",u"\u2AAC",u"\u2AAD",u"\u2AAE",
        u"\u2AAF",u"\u2AB0",u"\u2AB1",u"\u2AB2",u"\u2AB3",u"\u2AB4",u"\u2AB5",
        u"\u2AB6",u"\u2AB7",u"\u2AB8",u"\u2AB9",u"\u2ABA",u"\u2ABB",u"\u2ABC",
        u"\u2ABD",u"\u2ABE",u"\u2ABF",u"\u2AC0",u"\u2AC1",u"\u2AC2",u"\u2AC3",
        u"\u2AC4",u"\u2AC5",u"\u2AC6",u"\u2AC7",u"\u2AC8",u"\u2AC9",u"\u2ACA",
        u"\u2ACB",u"\u2ACC",u"\u2ACD",u"\u2ACE",u"\u2ACF",u"\u2AD0",u"\u2AD1",
        u"\u2AD2",u"\u2AD3",u"\u2AD4",u"\u2AD5",u"\u2AD6",u"\u2AD7",u"\u2AD8",
        u"\u2AD9",u"\u2ADA",u"\u2ADB",u"\u2ADC",u"\u2ADD",u"\u2ADE",u"\u2ADF",
        u"\u2AE0",u"\u2AE1",u"\u2AE2",u"\u2AE3",u"\u2AE4",u"\u2AE5",u"\u2AE6",
        u"\u2AE7",u"\u2AE8",u"\u2AE9",u"\u2AEA",u"\u2AEB",u"\u2AEC",u"\u2AED",
        u"\u2AEE",u"\u2AEF",u"\u2AF0",u"\u2AF1",u"\u2AF2",u"\u2AF3",u"\u2AF4",
        u"\u2AF5",u"\u2AF6",u"\u2AF7",u"\u2AF8",u"\u2AF9",u"\u2AFA",u"\u2AFB",
        u"\u2AFC",u"\u2AFD",u"\u2AFE",u"\u2AFF",u"\u2B00",u"\u2B01",u"\u2B02",
        u"\u2B03",u"\u2B04",u"\u2B05",u"\u2B06",u"\u2B07",u"\u2B08",u"\u2B09",
        u"\u2B0A",u"\u2B0B",u"\u2B0C",u"\u2B0D",u"\u2B0E",u"\u2B0F",u"\u2B10",
        u"\u2B11",u"\u2B12",u"\u2B13",u"\u2B14",u"\u2B15",u"\u2B16",u"\u2B17",
        u"\u2B18",u"\u2B19",u"\u2B1A",u"\u2B1B",u"\u2B1C",u"\u2B1D",u"\u2B1E",
        u"\u2B1F",u"\u2B20",u"\u2B21",u"\u2B22",u"\u2B23",u"\u2B24",u"\u2B25",
        u"\u2B26",u"\u2B27",u"\u2B28",u"\u2B29",u"\u2B2A",u"\u2B2B",u"\u2B2C",
        u"\u2B2D",u"\u2B2E",u"\u2B2F",u"\u2B30",u"\u2B31",u"\u2B32",u"\u2B33",
        u"\u2B34",u"\u2B35",u"\u2B36",u"\u2B37",u"\u2B38",u"\u2B39",u"\u2B3A",
        u"\u2B3B",u"\u2B3C",u"\u2B3D",u"\u2B3E",u"\u2B3F",u"\u2B40",u"\u2B41",
        u"\u2B42",u"\u2B43",u"\u2B44",u"\u2B45",u"\u2B46",u"\u2B47",u"\u2B48",
        u"\u2B49",u"\u2B4A",u"\u2B4B",u"\u2B4C",u"\u2B50",u"\u2B51",u"\u2B52",
        u"\u2B53",u"\u2B54",u"\u2B55",u"\u2B56",u"\u2B57",u"\u2B58",u"\u2B59",
        u"\u2CE5",u"\u2CE6",u"\u2CE7",u"\u2CE8",u"\u2CE9",u"\u2CEA",u"\u2CEF",
        u"\u2CF0",u"\u2CF1",u"\u2CF9",u"\u2CFA",u"\u2CFB",u"\u2CFC",u"\u2CFD",
        u"\u2CFE",u"\u2CFF",u"\u2D70",u"\u2D7F",u"\u2DE0",u"\u2DE1",u"\u2DE2",
        u"\u2DE3",u"\u2DE4",u"\u2DE5",u"\u2DE6",u"\u2DE7",u"\u2DE8",u"\u2DE9",
        u"\u2DEA",u"\u2DEB",u"\u2DEC",u"\u2DED",u"\u2DEE",u"\u2DEF",u"\u2DF0",
        u"\u2DF1",u"\u2DF2",u"\u2DF3",u"\u2DF4",u"\u2DF5",u"\u2DF6",u"\u2DF7",
        u"\u2DF8",u"\u2DF9",u"\u2DFA",u"\u2DFB",u"\u2DFC",u"\u2DFD",u"\u2DFE",
        u"\u2DFF",u"\u2E00",u"\u2E01",u"\u2E02",u"\u2E03",u"\u2E04",u"\u2E05",
        u"\u2E06",u"\u2E07",u"\u2E08",u"\u2E09",u"\u2E0A",u"\u2E0B",u"\u2E0C",
        u"\u2E0D",u"\u2E0E",u"\u2E0F",u"\u2E10",u"\u2E11",u"\u2E12",u"\u2E13",
        u"\u2E14",u"\u2E15",u"\u2E16",u"\u2E17",u"\u2E18",u"\u2E19",u"\u2E1A",
        u"\u2E1B",u"\u2E1C",u"\u2E1D",u"\u2E1E",u"\u2E1F",u"\u2E20",u"\u2E21",
        u"\u2E22",u"\u2E23",u"\u2E24",u"\u2E25",u"\u2E26",u"\u2E27",u"\u2E28",
        u"\u2E29",u"\u2E2A",u"\u2E2B",u"\u2E2C",u"\u2E2D",u"\u2E2E",u"\u2E30",
        u"\u2E31",u"\u2E80",u"\u2E81",u"\u2E82",u"\u2E83",u"\u2E84",u"\u2E85",
        u"\u2E86",u"\u2E87",u"\u2E88",u"\u2E89",u"\u2E8A",u"\u2E8B",u"\u2E8C",
        u"\u2E8D",u"\u2E8E",u"\u2E8F",u"\u2E90",u"\u2E91",u"\u2E92",u"\u2E93",
        u"\u2E94",u"\u2E95",u"\u2E96",u"\u2E97",u"\u2E98",u"\u2E99",u"\u2E9B",
        u"\u2E9C",u"\u2E9D",u"\u2E9E",u"\u2E9F",u"\u2EA0",u"\u2EA1",u"\u2EA2",
        u"\u2EA3",u"\u2EA4",u"\u2EA5",u"\u2EA6",u"\u2EA7",u"\u2EA8",u"\u2EA9",
        u"\u2EAA",u"\u2EAB",u"\u2EAC",u"\u2EAD",u"\u2EAE",u"\u2EAF",u"\u2EB0",
        u"\u2EB1",u"\u2EB2",u"\u2EB3",u"\u2EB4",u"\u2EB5",u"\u2EB6",u"\u2EB7",
        u"\u2EB8",u"\u2EB9",u"\u2EBA",u"\u2EBB",u"\u2EBC",u"\u2EBD",u"\u2EBE",
        u"\u2EBF",u"\u2EC0",u"\u2EC1",u"\u2EC2",u"\u2EC3",u"\u2EC4",u"\u2EC5",
        u"\u2EC6",u"\u2EC7",u"\u2EC8",u"\u2EC9",u"\u2ECA",u"\u2ECB",u"\u2ECC",
        u"\u2ECD",u"\u2ECE",u"\u2ECF",u"\u2ED0",u"\u2ED1",u"\u2ED2",u"\u2ED3",
        u"\u2ED4",u"\u2ED5",u"\u2ED6",u"\u2ED7",u"\u2ED8",u"\u2ED9",u"\u2EDA",
        u"\u2EDB",u"\u2EDC",u"\u2EDD",u"\u2EDE",u"\u2EDF",u"\u2EE0",u"\u2EE1",
        u"\u2EE2",u"\u2EE3",u"\u2EE4",u"\u2EE5",u"\u2EE6",u"\u2EE7",u"\u2EE8",
        u"\u2EE9",u"\u2EEA",u"\u2EEB",u"\u2EEC",u"\u2EED",u"\u2EEE",u"\u2EEF",
        u"\u2EF0",u"\u2EF1",u"\u2EF2",u"\u2EF3",u"\u2F00",u"\u2F01",u"\u2F02",
        u"\u2F03",u"\u2F04",u"\u2F05",u"\u2F06",u"\u2F07",u"\u2F08",u"\u2F09",
        u"\u2F0A",u"\u2F0B",u"\u2F0C",u"\u2F0D",u"\u2F0E",u"\u2F0F",u"\u2F10",
        u"\u2F11",u"\u2F12",u"\u2F13",u"\u2F14",u"\u2F15",u"\u2F16",u"\u2F17",
        u"\u2F18",u"\u2F19",u"\u2F1A",u"\u2F1B",u"\u2F1C",u"\u2F1D",u"\u2F1E",
        u"\u2F1F",u"\u2F20",u"\u2F21",u"\u2F22",u"\u2F23",u"\u2F24",u"\u2F25",
        u"\u2F26",u"\u2F27",u"\u2F28",u"\u2F29",u"\u2F2A",u"\u2F2B",u"\u2F2C",
        u"\u2F2D",u"\u2F2E",u"\u2F2F",u"\u2F30",u"\u2F31",u"\u2F32",u"\u2F33",
        u"\u2F34",u"\u2F35",u"\u2F36",u"\u2F37",u"\u2F38",u"\u2F39",u"\u2F3A",
        u"\u2F3B",u"\u2F3C",u"\u2F3D",u"\u2F3E",u"\u2F3F",u"\u2F40",u"\u2F41",
        u"\u2F42",u"\u2F43",u"\u2F44",u"\u2F45",u"\u2F46",u"\u2F47",u"\u2F48",
        u"\u2F49",u"\u2F4A",u"\u2F4B",u"\u2F4C",u"\u2F4D",u"\u2F4E",u"\u2F4F",
        u"\u2F50",u"\u2F51",u"\u2F52",u"\u2F53",u"\u2F54",u"\u2F55",u"\u2F56",
        u"\u2F57",u"\u2F58",u"\u2F59",u"\u2F5A",u"\u2F5B",u"\u2F5C",u"\u2F5D",
        u"\u2F5E",u"\u2F5F",u"\u2F60",u"\u2F61",u"\u2F62",u"\u2F63",u"\u2F64",
        u"\u2F65",u"\u2F66",u"\u2F67",u"\u2F68",u"\u2F69",u"\u2F6A",u"\u2F6B",
        u"\u2F6C",u"\u2F6D",u"\u2F6E",u"\u2F6F",u"\u2F70",u"\u2F71",u"\u2F72",
        u"\u2F73",u"\u2F74",u"\u2F75",u"\u2F76",u"\u2F77",u"\u2F78",u"\u2F79",
        u"\u2F7A",u"\u2F7B",u"\u2F7C",u"\u2F7D",u"\u2F7E",u"\u2F7F",u"\u2F80",
        u"\u2F81",u"\u2F82",u"\u2F83",u"\u2F84",u"\u2F85",u"\u2F86",u"\u2F87",
        u"\u2F88",u"\u2F89",u"\u2F8A",u"\u2F8B",u"\u2F8C",u"\u2F8D",u"\u2F8E",
        u"\u2F8F",u"\u2F90",u"\u2F91",u"\u2F92",u"\u2F93",u"\u2F94",u"\u2F95",
        u"\u2F96",u"\u2F97",u"\u2F98",u"\u2F99",u"\u2F9A",u"\u2F9B",u"\u2F9C",
        u"\u2F9D",u"\u2F9E",u"\u2F9F",u"\u2FA0",u"\u2FA1",u"\u2FA2",u"\u2FA3",
        u"\u2FA4",u"\u2FA5",u"\u2FA6",u"\u2FA7",u"\u2FA8",u"\u2FA9",u"\u2FAA",
        u"\u2FAB",u"\u2FAC",u"\u2FAD",u"\u2FAE",u"\u2FAF",u"\u2FB0",u"\u2FB1",
        u"\u2FB2",u"\u2FB3",u"\u2FB4",u"\u2FB5",u"\u2FB6",u"\u2FB7",u"\u2FB8",
        u"\u2FB9",u"\u2FBA",u"\u2FBB",u"\u2FBC",u"\u2FBD",u"\u2FBE",u"\u2FBF",
        u"\u2FC0",u"\u2FC1",u"\u2FC2",u"\u2FC3",u"\u2FC4",u"\u2FC5",u"\u2FC6",
        u"\u2FC7",u"\u2FC8",u"\u2FC9",u"\u2FCA",u"\u2FCB",u"\u2FCC",u"\u2FCD",
        u"\u2FCE",u"\u2FCF",u"\u2FD0",u"\u2FD1",u"\u2FD2",u"\u2FD3",u"\u2FD4",
        u"\u2FD5",u"\u2FF0",u"\u2FF1",u"\u2FF2",u"\u2FF3",u"\u2FF4",u"\u2FF5",
        u"\u2FF6",u"\u2FF7",u"\u2FF8",u"\u2FF9",u"\u2FFA",u"\u2FFB",u"\u3000",
        u"\u3001",u"\u3002",u"\u3003",u"\u3004",u"\u3007",u"\u3008",u"\u3009",
        u"\u300A",u"\u300B",u"\u300C",u"\u300D",u"\u300E",u"\u300F",u"\u3010",
        u"\u3011",u"\u3012",u"\u3013",u"\u3014",u"\u3015",u"\u3016",u"\u3017",
        u"\u3018",u"\u3019",u"\u301A",u"\u301B",u"\u301C",u"\u301D",u"\u301E",
        u"\u301F",u"\u3020",u"\u3021",u"\u3022",u"\u3023",u"\u3024",u"\u3025",
        u"\u3026",u"\u3027",u"\u3028",u"\u3029",u"\u302A",u"\u302B",u"\u302C",
        u"\u302D",u"\u302E",u"\u302F",u"\u3030",u"\u3036",u"\u3037",u"\u3038",
        u"\u3039",u"\u303A",u"\u303D",u"\u303E",u"\u303F",u"\u3099",u"\u309A",
        u"\u309B",u"\u309C",u"\u30A0",u"\u30FB",u"\u3190",u"\u3191",u"\u3192",
        u"\u3193",u"\u3194",u"\u3195",u"\u3196",u"\u3197",u"\u3198",u"\u3199",
        u"\u319A",u"\u319B",u"\u319C",u"\u319D",u"\u319E",u"\u319F",u"\u31C0",
        u"\u31C1",u"\u31C2",u"\u31C3",u"\u31C4",u"\u31C5",u"\u31C6",u"\u31C7",
        u"\u31C8",u"\u31C9",u"\u31CA",u"\u31CB",u"\u31CC",u"\u31CD",u"\u31CE",
        u"\u31CF",u"\u31D0",u"\u31D1",u"\u31D2",u"\u31D3",u"\u31D4",u"\u31D5",
        u"\u31D6",u"\u31D7",u"\u31D8",u"\u31D9",u"\u31DA",u"\u31DB",u"\u31DC",
        u"\u31DD",u"\u31DE",u"\u31DF",u"\u31E0",u"\u31E1",u"\u31E2",u"\u31E3",
        u"\u3200",u"\u3201",u"\u3202",u"\u3203",u"\u3204",u"\u3205",u"\u3206",
        u"\u3207",u"\u3208",u"\u3209",u"\u320A",u"\u320B",u"\u320C",u"\u320D",
        u"\u320E",u"\u320F",u"\u3210",u"\u3211",u"\u3212",u"\u3213",u"\u3214",
        u"\u3215",u"\u3216",u"\u3217",u"\u3218",u"\u3219",u"\u321A",u"\u321B",
        u"\u321C",u"\u321D",u"\u321E",u"\u3220",u"\u3221",u"\u3222",u"\u3223",
        u"\u3224",u"\u3225",u"\u3226",u"\u3227",u"\u3228",u"\u3229",u"\u322A",
        u"\u322B",u"\u322C",u"\u322D",u"\u322E",u"\u322F",u"\u3230",u"\u3231",
        u"\u3232",u"\u3233",u"\u3234",u"\u3235",u"\u3236",u"\u3237",u"\u3238",
        u"\u3239",u"\u323A",u"\u323B",u"\u323C",u"\u323D",u"\u323E",u"\u323F",
        u"\u3240",u"\u3241",u"\u3242",u"\u3243",u"\u3244",u"\u3245",u"\u3246",
        u"\u3247",u"\u3248",u"\u3249",u"\u324A",u"\u324B",u"\u324C",u"\u324D",
        u"\u324E",u"\u324F",u"\u3250",u"\u3251",u"\u3252",u"\u3253",u"\u3254",
        u"\u3255",u"\u3256",u"\u3257",u"\u3258",u"\u3259",u"\u325A",u"\u325B",
        u"\u325C",u"\u325D",u"\u325E",u"\u325F",u"\u3260",u"\u3261",u"\u3262",
        u"\u3263",u"\u3264",u"\u3265",u"\u3266",u"\u3267",u"\u3268",u"\u3269",
        u"\u326A",u"\u326B",u"\u326C",u"\u326D",u"\u326E",u"\u326F",u"\u3270",
        u"\u3271",u"\u3272",u"\u3273",u"\u3274",u"\u3275",u"\u3276",u"\u3277",
        u"\u3278",u"\u3279",u"\u327A",u"\u327B",u"\u327C",u"\u327D",u"\u327E",
        u"\u327F",u"\u3280",u"\u3281",u"\u3282",u"\u3283",u"\u3284",u"\u3285",
        u"\u3286",u"\u3287",u"\u3288",u"\u3289",u"\u328A",u"\u328B",u"\u328C",
        u"\u328D",u"\u328E",u"\u328F",u"\u3290",u"\u3291",u"\u3292",u"\u3293",
        u"\u3294",u"\u3295",u"\u3296",u"\u3297",u"\u3298",u"\u3299",u"\u329A",
        u"\u329B",u"\u329C",u"\u329D",u"\u329E",u"\u329F",u"\u32A0",u"\u32A1",
        u"\u32A2",u"\u32A3",u"\u32A4",u"\u32A5",u"\u32A6",u"\u32A7",u"\u32A8",
        u"\u32A9",u"\u32AA",u"\u32AB",u"\u32AC",u"\u32AD",u"\u32AE",u"\u32AF",
        u"\u32B0",u"\u32B1",u"\u32B2",u"\u32B3",u"\u32B4",u"\u32B5",u"\u32B6",
        u"\u32B7",u"\u32B8",u"\u32B9",u"\u32BA",u"\u32BB",u"\u32BC",u"\u32BD",
        u"\u32BE",u"\u32BF",u"\u32C0",u"\u32C1",u"\u32C2",u"\u32C3",u"\u32C4",
        u"\u32C5",u"\u32C6",u"\u32C7",u"\u32C8",u"\u32C9",u"\u32CA",u"\u32CB",
        u"\u32CC",u"\u32CD",u"\u32CE",u"\u32CF",u"\u32D0",u"\u32D1",u"\u32D2",
        u"\u32D3",u"\u32D4",u"\u32D5",u"\u32D6",u"\u32D7",u"\u32D8",u"\u32D9",
        u"\u32DA",u"\u32DB",u"\u32DC",u"\u32DD",u"\u32DE",u"\u32DF",u"\u32E0",
        u"\u32E1",u"\u32E2",u"\u32E3",u"\u32E4",u"\u32E5",u"\u32E6",u"\u32E7",
        u"\u32E8",u"\u32E9",u"\u32EA",u"\u32EB",u"\u32EC",u"\u32ED",u"\u32EE",
        u"\u32EF",u"\u32F0",u"\u32F1",u"\u32F2",u"\u32F3",u"\u32F4",u"\u32F5",
        u"\u32F6",u"\u32F7",u"\u32F8",u"\u32F9",u"\u32FA",u"\u32FB",u"\u32FC",
        u"\u32FD",u"\u32FE",u"\u3300",u"\u3301",u"\u3302",u"\u3303",u"\u3304",
        u"\u3305",u"\u3306",u"\u3307",u"\u3308",u"\u3309",u"\u330A",u"\u330B",
        u"\u330C",u"\u330D",u"\u330E",u"\u330F",u"\u3310",u"\u3311",u"\u3312",
        u"\u3313",u"\u3314",u"\u3315",u"\u3316",u"\u3317",u"\u3318",u"\u3319",
        u"\u331A",u"\u331B",u"\u331C",u"\u331D",u"\u331E",u"\u331F",u"\u3320",
        u"\u3321",u"\u3322",u"\u3323",u"\u3324",u"\u3325",u"\u3326",u"\u3327",
        u"\u3328",u"\u3329",u"\u332A",u"\u332B",u"\u332C",u"\u332D",u"\u332E",
        u"\u332F",u"\u3330",u"\u3331",u"\u3332",u"\u3333",u"\u3334",u"\u3335",
        u"\u3336",u"\u3337",u"\u3338",u"\u3339",u"\u333A",u"\u333B",u"\u333C",
        u"\u333D",u"\u333E",u"\u333F",u"\u3340",u"\u3341",u"\u3342",u"\u3343",
        u"\u3344",u"\u3345",u"\u3346",u"\u3347",u"\u3348",u"\u3349",u"\u334A",
        u"\u334B",u"\u334C",u"\u334D",u"\u334E",u"\u334F",u"\u3350",u"\u3351",
        u"\u3352",u"\u3353",u"\u3354",u"\u3355",u"\u3356",u"\u3357",u"\u3358",
        u"\u3359",u"\u335A",u"\u335B",u"\u335C",u"\u335D",u"\u335E",u"\u335F",
        u"\u3360",u"\u3361",u"\u3362",u"\u3363",u"\u3364",u"\u3365",u"\u3366",
        u"\u3367",u"\u3368",u"\u3369",u"\u336A",u"\u336B",u"\u336C",u"\u336D",
        u"\u336E",u"\u336F",u"\u3370",u"\u3371",u"\u3372",u"\u3373",u"\u3374",
        u"\u3375",u"\u3376",u"\u3377",u"\u3378",u"\u3379",u"\u337A",u"\u337B",
        u"\u337C",u"\u337D",u"\u337E",u"\u337F",u"\u3380",u"\u3381",u"\u3382",
        u"\u3383",u"\u3384",u"\u3385",u"\u3386",u"\u3387",u"\u3388",u"\u3389",
        u"\u338A",u"\u338B",u"\u338C",u"\u338D",u"\u338E",u"\u338F",u"\u3390",
        u"\u3391",u"\u3392",u"\u3393",u"\u3394",u"\u3395",u"\u3396",u"\u3397",
        u"\u3398",u"\u3399",u"\u339A",u"\u339B",u"\u339C",u"\u339D",u"\u339E",
        u"\u339F",u"\u33A0",u"\u33A1",u"\u33A2",u"\u33A3",u"\u33A4",u"\u33A5",
        u"\u33A6",u"\u33A7",u"\u33A8",u"\u33A9",u"\u33AA",u"\u33AB",u"\u33AC",
        u"\u33AD",u"\u33AE",u"\u33AF",u"\u33B0",u"\u33B1",u"\u33B2",u"\u33B3",
        u"\u33B4",u"\u33B5",u"\u33B6",u"\u33B7",u"\u33B8",u"\u33B9",u"\u33BA",
        u"\u33BB",u"\u33BC",u"\u33BD",u"\u33BE",u"\u33BF",u"\u33C0",u"\u33C1",
        u"\u33C2",u"\u33C3",u"\u33C4",u"\u33C5",u"\u33C6",u"\u33C7",u"\u33C8",
        u"\u33C9",u"\u33CA",u"\u33CB",u"\u33CC",u"\u33CD",u"\u33CE",u"\u33CF",
        u"\u33D0",u"\u33D1",u"\u33D2",u"\u33D3",u"\u33D4",u"\u33D5",u"\u33D6",
        u"\u33D7",u"\u33D8",u"\u33D9",u"\u33DA",u"\u33DB",u"\u33DC",u"\u33DD",
        u"\u33DE",u"\u33DF",u"\u33E0",u"\u33E1",u"\u33E2",u"\u33E3",u"\u33E4",
        u"\u33E5",u"\u33E6",u"\u33E7",u"\u33E8",u"\u33E9",u"\u33EA",u"\u33EB",
        u"\u33EC",u"\u33ED",u"\u33EE",u"\u33EF",u"\u33F0",u"\u33F1",u"\u33F2",
        u"\u33F3",u"\u33F4",u"\u33F5",u"\u33F6",u"\u33F7",u"\u33F8",u"\u33F9",
        u"\u33FA",u"\u33FB",u"\u33FC",u"\u33FD",u"\u33FE",u"\u33FF",u"\u4DC0",
        u"\u4DC1",u"\u4DC2",u"\u4DC3",u"\u4DC4",u"\u4DC5",u"\u4DC6",u"\u4DC7",
        u"\u4DC8",u"\u4DC9",u"\u4DCA",u"\u4DCB",u"\u4DCC",u"\u4DCD",u"\u4DCE",
        u"\u4DCF",u"\u4DD0",u"\u4DD1",u"\u4DD2",u"\u4DD3",u"\u4DD4",u"\u4DD5",
        u"\u4DD6",u"\u4DD7",u"\u4DD8",u"\u4DD9",u"\u4DDA",u"\u4DDB",u"\u4DDC",
        u"\u4DDD",u"\u4DDE",u"\u4DDF",u"\u4DE0",u"\u4DE1",u"\u4DE2",u"\u4DE3",
        u"\u4DE4",u"\u4DE5",u"\u4DE6",u"\u4DE7",u"\u4DE8",u"\u4DE9",u"\u4DEA",
        u"\u4DEB",u"\u4DEC",u"\u4DED",u"\u4DEE",u"\u4DEF",u"\u4DF0",u"\u4DF1",
        u"\u4DF2",u"\u4DF3",u"\u4DF4",u"\u4DF5",u"\u4DF6",u"\u4DF7",u"\u4DF8",
        u"\u4DF9",u"\u4DFA",u"\u4DFB",u"\u4DFC",u"\u4DFD",u"\u4DFE",u"\u4DFF",
        u"\uA490",u"\uA491",u"\uA492",u"\uA493",u"\uA494",u"\uA495",u"\uA496",
        u"\uA497",u"\uA498",u"\uA499",u"\uA49A",u"\uA49B",u"\uA49C",u"\uA49D",
        u"\uA49E",u"\uA49F",u"\uA4A0",u"\uA4A1",u"\uA4A2",u"\uA4A3",u"\uA4A4",
        u"\uA4A5",u"\uA4A6",u"\uA4A7",u"\uA4A8",u"\uA4A9",u"\uA4AA",u"\uA4AB",
        u"\uA4AC",u"\uA4AD",u"\uA4AE",u"\uA4AF",u"\uA4B0",u"\uA4B1",u"\uA4B2",
        u"\uA4B3",u"\uA4B4",u"\uA4B5",u"\uA4B6",u"\uA4B7",u"\uA4B8",u"\uA4B9",
        u"\uA4BA",u"\uA4BB",u"\uA4BC",u"\uA4BD",u"\uA4BE",u"\uA4BF",u"\uA4C0",
        u"\uA4C1",u"\uA4C2",u"\uA4C3",u"\uA4C4",u"\uA4C5",u"\uA4C6",u"\uA4FE",
        u"\uA4FF",u"\uA60D",u"\uA60E",u"\uA60F",u"\uA620",u"\uA621",u"\uA622",
        u"\uA623",u"\uA624",u"\uA625",u"\uA626",u"\uA627",u"\uA628",u"\uA629",
        u"\uA66F",u"\uA670",u"\uA671",u"\uA672",u"\uA673",u"\uA67C",u"\uA67D",
        u"\uA67E",u"\uA6F0",u"\uA6F1",u"\uA6F2",u"\uA6F3",u"\uA6F4",u"\uA6F5",
        u"\uA6F6",u"\uA6F7",u"\uA700",u"\uA701",u"\uA702",u"\uA703",u"\uA704",
        u"\uA705",u"\uA706",u"\uA707",u"\uA708",u"\uA709",u"\uA70A",u"\uA70B",
        u"\uA70C",u"\uA70D",u"\uA70E",u"\uA70F",u"\uA710",u"\uA711",u"\uA712",
        u"\uA713",u"\uA714",u"\uA715",u"\uA716",u"\uA720",u"\uA721",u"\uA78A",
        u"\uA802",u"\uA806",u"\uA80B",u"\uA823",u"\uA824",u"\uA825",u"\uA826",
        u"\uA827",u"\uA828",u"\uA829",u"\uA82A",u"\uA82B",u"\uA830",u"\uA831",
        u"\uA832",u"\uA833",u"\uA834",u"\uA835",u"\uA836",u"\uA837",u"\uA838",
        u"\uA839",u"\uA874",u"\uA875",u"\uA876",u"\uA877",u"\uA880",u"\uA881",
        u"\uA8B4",u"\uA8BA",u"\uA8BB",u"\uA8BC",u"\uA8BD",u"\uA8C4",u"\uA8CE",
        u"\uA8CF",u"\uA8D0",u"\uA8D1",u"\uA8D2",u"\uA8D3",u"\uA8D4",u"\uA8D5",
        u"\uA8D6",u"\uA8D7",u"\uA8D8",u"\uA8D9",u"\uA8E0",u"\uA8E1",u"\uA8E2",
        u"\uA8E3",u"\uA8E4",u"\uA8E5",u"\uA8E6",u"\uA8E7",u"\uA8E8",u"\uA8E9",
        u"\uA8EA",u"\uA8EB",u"\uA8EC",u"\uA8ED",u"\uA8EE",u"\uA8EF",u"\uA8F0",
        u"\uA8F1",u"\uA8F8",u"\uA8F9",u"\uA8FA",u"\uA900",u"\uA901",u"\uA902",
        u"\uA903",u"\uA904",u"\uA905",u"\uA906",u"\uA907",u"\uA908",u"\uA909",
        u"\uA926",u"\uA927",u"\uA928",u"\uA929",u"\uA92A",u"\uA92B",u"\uA92C",
        u"\uA92D",u"\uA92E",u"\uA92F",u"\uA94F",u"\uA950",u"\uA951",u"\uA952",
        u"\uA953",u"\uA95F",u"\uA980",u"\uA981",u"\uA982",u"\uA983",u"\uA9B3",
        u"\uA9B7",u"\uA9B9",u"\uA9BB",u"\uA9BD",u"\uA9BE",u"\uA9BF",u"\uA9C0",
        u"\uA9C1",u"\uA9C2",u"\uA9C3",u"\uA9C4",u"\uA9C5",u"\uA9C6",u"\uA9C7",
        u"\uA9C8",u"\uA9C9",u"\uA9CA",u"\uA9CB",u"\uA9CC",u"\uA9CD",u"\uA9D0",
        u"\uA9D1",u"\uA9D2",u"\uA9D3",u"\uA9D4",u"\uA9D5",u"\uA9D6",u"\uA9D7",
        u"\uA9D8",u"\uA9D9",u"\uA9DE",u"\uA9DF",u"\uAA33",u"\uAA34",u"\uAA35",
        u"\uAA36",u"\uAA43",u"\uAA4C",u"\uAA4D",u"\uAA50",u"\uAA51",u"\uAA52",
        u"\uAA53",u"\uAA54",u"\uAA55",u"\uAA56",u"\uAA57",u"\uAA58",u"\uAA59",
        u"\uAA5C",u"\uAA5D",u"\uAA5E",u"\uAA5F",u"\uAA77",u"\uAA78",u"\uAA79",
        u"\uAA7B",u"\uAAB0",u"\uAAB2",u"\uAAB3",u"\uAAB4",u"\uAAB7",u"\uAAB8",
        u"\uAABE",u"\uAABF",u"\uAAC1",u"\uAADE",u"\uAADF",u"\uABE3",u"\uABE4",
        u"\uABE5",u"\uABE6",u"\uABE7",u"\uABE8",u"\uABE9",u"\uABEA",u"\uABEB",
        u"\uABEC",u"\uABED",u"\uABF0",u"\uABF1",u"\uABF2",u"\uABF3",u"\uABF4",
        u"\uABF5",u"\uABF6",u"\uABF7",u"\uABF8",u"\uABF9",u"\uD800",u"\uDB7F",
        u"\uDB80",u"\uDBFF",u"\uDC00",u"\uDFFF",u"\uE000",u"\uF8FF",u"\uFB1E",
        u"\uFB29",u"\uFBB2",u"\uFBB3",u"\uFBB4",u"\uFBB5",u"\uFBB6",u"\uFBB7",
        u"\uFBB8",u"\uFBB9",u"\uFBBA",u"\uFBBB",u"\uFBBC",u"\uFBBD",u"\uFBBE",
        u"\uFBBF",u"\uFBC0",u"\uFBC1",u"\uFD3E",u"\uFD3F",u"\uFDFD",u"\uFE00",
        u"\uFE01",u"\uFE02",u"\uFE03",u"\uFE04",u"\uFE05",u"\uFE06",u"\uFE07",
        u"\uFE08",u"\uFE09",u"\uFE0A",u"\uFE0B",u"\uFE0C",u"\uFE0D",u"\uFE0E",
        u"\uFE0F",u"\uFE10",u"\uFE11",u"\uFE12",u"\uFE13",u"\uFE14",u"\uFE15",
        u"\uFE16",u"\uFE17",u"\uFE18",u"\uFE19",u"\uFE20",u"\uFE21",u"\uFE22",
        u"\uFE23",u"\uFE24",u"\uFE25",u"\uFE26",u"\uFE30",u"\uFE31",u"\uFE32",
        u"\uFE33",u"\uFE34",u"\uFE35",u"\uFE36",u"\uFE37",u"\uFE38",u"\uFE39",
        u"\uFE3A",u"\uFE3B",u"\uFE3C",u"\uFE3D",u"\uFE3E",u"\uFE3F",u"\uFE40",
        u"\uFE41",u"\uFE42",u"\uFE43",u"\uFE44",u"\uFE45",u"\uFE46",u"\uFE47",
        u"\uFE48",u"\uFE49",u"\uFE4A",u"\uFE4B",u"\uFE4C",u"\uFE4D",u"\uFE4E",
        u"\uFE4F",u"\uFE50",u"\uFE51",u"\uFE52",u"\uFE54",u"\uFE55",u"\uFE56",
        u"\uFE57",u"\uFE58",u"\uFE59",u"\uFE5A",u"\uFE5B",u"\uFE5C",u"\uFE5D",
        u"\uFE5E",u"\uFE5F",u"\uFE60",u"\uFE61",u"\uFE62",u"\uFE63",u"\uFE64",
        u"\uFE65",u"\uFE66",u"\uFE68",u"\uFE69",u"\uFE6A",u"\uFE6B",u"\uFEFF",
        u"\uFF01",u"\uFF02",u"\uFF03",u"\uFF04",u"\uFF05",u"\uFF06",u"\uFF07",
        u"\uFF08",u"\uFF09",u"\uFF0A",u"\uFF0B",u"\uFF0C",u"\uFF0D",u"\uFF0E",
        u"\uFF0F",u"\uFF10",u"\uFF11",u"\uFF12",u"\uFF13",u"\uFF14",u"\uFF15",
        u"\uFF16",u"\uFF17",u"\uFF18",u"\uFF19",u"\uFF1A",u"\uFF1B",u"\uFF1C",
        u"\uFF1D",u"\uFF1E",u"\uFF1F",u"\uFF20",u"\uFF3B",u"\uFF3C",u"\uFF3D",
        u"\uFF3E",u"\uFF3F",u"\uFF40",u"\uFF5B",u"\uFF5C",u"\uFF5D",u"\uFF5E",
        u"\uFF5F",u"\uFF60",u"\uFF61",u"\uFF62",u"\uFF63",u"\uFF64",u"\uFF65",
        u"\uFFE0",u"\uFFE1",u"\uFFE2",u"\uFFE3",u"\uFFE4",u"\uFFE5",u"\uFFE6",
        u"\uFFE8",u"\uFFE9",u"\uFFEA",u"\uFFEB",u"\uFFEC",u"\uFFED",u"\uFFEE",
        u"\uFFF9",u"\uFFFA",u"\uFFFB",u"\uFFFC",u"\uFFFD"],
    "AnyVowels" : [],
    "WI_Consonants" : [
        u"\u00C0",u"\u00C1",u"\u00C2",u"\u00C3",u"\u00C4",u"\u00C5",u"\u00C6",
        u"\u00C7",u"\u00C8",u"\u00C9",u"\u00CA",u"\u00CB",u"\u00CC",u"\u00CD",
        u"\u00CE",u"\u00CF",u"\u00D0",u"\u00D1",u"\u00D2",u"\u00D3",u"\u00D4",
        u"\u00D5",u"\u00D6",u"\u00D8",u"\u00D9",u"\u00DA",u"\u00DB",u"\u00DC",
        u"\u00DD",u"\u00DE",u"\u0100",u"\u0102",u"\u0104",u"\u0106",u"\u0108",
        u"\u010A",u"\u010C",u"\u010E",u"\u0110",u"\u0112",u"\u0114",u"\u0116",
        u"\u0118",u"\u011A",u"\u011C",u"\u011E",u"\u0120",u"\u0122",u"\u0124",
        u"\u0126",u"\u0128",u"\u012A",u"\u012C",u"\u012E",u"\u0130",u"\u0132",
        u"\u0134",u"\u0136",u"\u0139",u"\u013B",u"\u013D",u"\u013F",u"\u0141",
        u"\u0143",u"\u0145",u"\u0147",u"\u014A",u"\u014C",u"\u014E",u"\u0150",
        u"\u0152",u"\u0154",u"\u0156",u"\u0158",u"\u015A",u"\u015C",u"\u015E",
        u"\u0160",u"\u0162",u"\u0164",u"\u0166",u"\u0168",u"\u016A",u"\u016C",
        u"\u016E",u"\u0170",u"\u0172",u"\u0174",u"\u0176",u"\u0178",u"\u0179",
        u"\u017B",u"\u017D",u"\u0181",u"\u0182",u"\u0184",u"\u0186",u"\u0187",
        u"\u0189",u"\u018A",u"\u018B",u"\u018E",u"\u018F",u"\u0190",u"\u0191",
        u"\u0193",u"\u0194",u"\u0196",u"\u0197",u"\u0198",u"\u019C",u"\u019D",
        u"\u019F",u"\u01A0",u"\u01A2",u"\u01A4",u"\u01A6",u"\u01A7",u"\u01A9",
        u"\u01AC",u"\u01AE",u"\u01AF",u"\u01B1",u"\u01B2",u"\u01B3",u"\u01B5",
        u"\u01B7",u"\u01B8",u"\u01BC",u"\u01C4",u"\u01C5",u"\u01C7",u"\u01C8",
        u"\u01CA",u"\u01CB",u"\u01CD",u"\u01CF",u"\u01D1",u"\u01D3",u"\u01D5",
        u"\u01D7",u"\u01D9",u"\u01DB",u"\u01DE",u"\u01E0",u"\u01E2",u"\u01E4",
        u"\u01E6",u"\u01E8",u"\u01EA",u"\u01EC",u"\u01EE",u"\u01F1",u"\u01F2",
        u"\u01F4",u"\u01F6",u"\u01F7",u"\u01F8",u"\u01FA",u"\u01FC",u"\u01FE",
        u"\u0200",u"\u0202",u"\u0204",u"\u0206",u"\u0208",u"\u020A",u"\u020C",
        u"\u020E",u"\u0210",u"\u0212",u"\u0214",u"\u0216",u"\u0218",u"\u021A",
        u"\u021C",u"\u021E",u"\u0220",u"\u0222",u"\u0224",u"\u0226",u"\u0228",
        u"\u022A",u"\u022C",u"\u022E",u"\u0230",u"\u0232",u"\u023A",u"\u023B",
        u"\u023D",u"\u023E",u"\u0241",u"\u0243",u"\u0244",u"\u0245",u"\u0246",
        u"\u0248",u"\u024A",u"\u024C",u"\u024E",u"\u0370",u"\u0372",u"\u0376",
        u"\u0386",u"\u0388",u"\u0389",u"\u038A",u"\u038C",u"\u038E",u"\u038F",
        u"\u03AA",u"\u03AB",u"\u03CF",u"\u03D2",u"\u03D3",u"\u03D4",u"\u03D8",
        u"\u03DA",u"\u03DC",u"\u03DE",u"\u03E0",u"\u03F4",u"\u03F7",u"\u03F9",
        u"\u03FA",u"\u03FD",u"\u03FE",u"\u03FF",u"\u0400",u"\u0404",u"\u0406",
        u"\u040D",u"\u040E",u"\u0419",u"\u042A",u"\u042C",u"\u0460",u"\u0462",
        u"\u0464",u"\u0466",u"\u0468",u"\u046A",u"\u046C",u"\u046E",u"\u0470",
        u"\u0472",u"\u0474",u"\u0476",u"\u0478",u"\u047A",u"\u047C",u"\u047E",
        u"\u0480",u"\u048A",u"\u048C",u"\u048E",u"\u0490",u"\u0492",u"\u0494",
        u"\u0496",u"\u0498",u"\u049A",u"\u049C",u"\u049E",u"\u04A0",u"\u04A2",
        u"\u04A4",u"\u04A6",u"\u04A8",u"\u04AA",u"\u04AC",u"\u04AE",u"\u04B0",
        u"\u04B2",u"\u04B4",u"\u04B6",u"\u04B8",u"\u04BA",u"\u04BC",u"\u04BE",
        u"\u04C0",u"\u04C1",u"\u04C3",u"\u04C5",u"\u04C7",u"\u04C9",u"\u04CB",
        u"\u04CD",u"\u04D0",u"\u04D2",u"\u04D4",u"\u04D6",u"\u04D8",u"\u04DA",
        u"\u04DC",u"\u04DE",u"\u04E0",u"\u04E2",u"\u04E4",u"\u04E6",u"\u04E8",
        u"\u04EA",u"\u04EC",u"\u04EE",u"\u04F0",u"\u04F2",u"\u04F4",u"\u04F6",
        u"\u04F8",u"\u04FA",u"\u04FC",u"\u04FE",u"\u0500",u"\u0502",u"\u0504",
        u"\u0506",u"\u0508",u"\u050A",u"\u050C",u"\u050E",u"\u0510",u"\u0512",
        u"\u0514",u"\u0516",u"\u0518",u"\u051A",u"\u051C",u"\u051E",u"\u0520",
        u"\u0522",u"\u0524",u"\u0526",u"\u10A0",u"\u10A1",u"\u10A2",u"\u10A3",
        u"\u10A4",u"\u10A5",u"\u10A6",u"\u10A7",u"\u10A8",u"\u10A9",u"\u10AA",
        u"\u10AB",u"\u10AC",u"\u10AD",u"\u10AE",u"\u10AF",u"\u10B0",u"\u10B1",
        u"\u10B2",u"\u10B3",u"\u10B4",u"\u10B5",u"\u10B6",u"\u10B7",u"\u10B8",
        u"\u10B9",u"\u10BA",u"\u10BB",u"\u10BC",u"\u10BD",u"\u10BE",u"\u10BF",
        u"\u10C0",u"\u10C1",u"\u10C2",u"\u10C3",u"\u10C4",u"\u10C5",u"\u1E00",
        u"\u1E02",u"\u1E04",u"\u1E06",u"\u1E08",u"\u1E0A",u"\u1E0C",u"\u1E0E",
        u"\u1E10",u"\u1E12",u"\u1E14",u"\u1E16",u"\u1E18",u"\u1E1A",u"\u1E1C",
        u"\u1E1E",u"\u1E20",u"\u1E22",u"\u1E24",u"\u1E26",u"\u1E28",u"\u1E2A",
        u"\u1E2C",u"\u1E2E",u"\u1E30",u"\u1E32",u"\u1E34",u"\u1E36",u"\u1E38",
        u"\u1E3A",u"\u1E3C",u"\u1E3E",u"\u1E40",u"\u1E42",u"\u1E44",u"\u1E46",
        u"\u1E48",u"\u1E4A",u"\u1E4C",u"\u1E4E",u"\u1E50",u"\u1E52",u"\u1E54",
        u"\u1E56",u"\u1E58",u"\u1E5A",u"\u1E5C",u"\u1E5E",u"\u1E60",u"\u1E62",
        u"\u1E64",u"\u1E66",u"\u1E68",u"\u1E6A",u"\u1E6C",u"\u1E6E",u"\u1E70",
        u"\u1E72",u"\u1E74",u"\u1E76",u"\u1E78",u"\u1E7A",u"\u1E7C",u"\u1E7E",
        u"\u1E80",u"\u1E82",u"\u1E84",u"\u1E86",u"\u1E88",u"\u1E8A",u"\u1E8C",
        u"\u1E8E",u"\u1E90",u"\u1E92",u"\u1E94",u"\u1E9E",u"\u1EA0",u"\u1EA2",
        u"\u1EA4",u"\u1EA6",u"\u1EA8",u"\u1EAA",u"\u1EAC",u"\u1EAE",u"\u1EB0",
        u"\u1EB2",u"\u1EB4",u"\u1EB6",u"\u1EB8",u"\u1EBA",u"\u1EBC",u"\u1EBE",
        u"\u1EC0",u"\u1EC2",u"\u1EC4",u"\u1EC6",u"\u1EC8",u"\u1ECA",u"\u1ECC",
        u"\u1ECE",u"\u1ED0",u"\u1ED2",u"\u1ED4",u"\u1ED6",u"\u1ED8",u"\u1EDA",
        u"\u1EDC",u"\u1EDE",u"\u1EE0",u"\u1EE2",u"\u1EE4",u"\u1EE6",u"\u1EE8",
        u"\u1EEA",u"\u1EEC",u"\u1EEE",u"\u1EF0",u"\u1EF2",u"\u1EF4",u"\u1EF6",
        u"\u1EF8",u"\u1EFA",u"\u1EFC",u"\u1EFE",u"\u1F08",u"\u1F09",u"\u1F0A",
        u"\u1F0B",u"\u1F0C",u"\u1F0D",u"\u1F0E",u"\u1F0F",u"\u1F18",u"\u1F19",
        u"\u1F1A",u"\u1F1B",u"\u1F1C",u"\u1F1D",u"\u1F28",u"\u1F29",u"\u1F2A",
        u"\u1F2B",u"\u1F2C",u"\u1F2D",u"\u1F2E",u"\u1F2F",u"\u1F38",u"\u1F39",
        u"\u1F3A",u"\u1F3B",u"\u1F3C",u"\u1F3D",u"\u1F3E",u"\u1F3F",u"\u1F48",
        u"\u1F49",u"\u1F4A",u"\u1F4B",u"\u1F4C",u"\u1F4D",u"\u1F59",u"\u1F5B",
        u"\u1F5D",u"\u1F5F",u"\u1F68",u"\u1F69",u"\u1F6A",u"\u1F6B",u"\u1F6C",
        u"\u1F6D",u"\u1F6E",u"\u1F6F",u"\u1F88",u"\u1F89",u"\u1F8A",u"\u1F8B",
        u"\u1F8C",u"\u1F8D",u"\u1F8E",u"\u1F8F",u"\u1F98",u"\u1F99",u"\u1F9A",
        u"\u1F9B",u"\u1F9C",u"\u1F9D",u"\u1F9E",u"\u1F9F",u"\u1FA8",u"\u1FA9",
        u"\u1FAA",u"\u1FAB",u"\u1FAC",u"\u1FAD",u"\u1FAE",u"\u1FAF",u"\u1FB8",
        u"\u1FB9",u"\u1FBA",u"\u1FBB",u"\u1FBC",u"\u1FC8",u"\u1FC9",u"\u1FCA",
        u"\u1FCB",u"\u1FCC",u"\u1FD8",u"\u1FD9",u"\u1FDA",u"\u1FDB",u"\u1FE8",
        u"\u1FE9",u"\u1FEA",u"\u1FEB",u"\u1FEC",u"\u1FF8",u"\u1FF9",u"\u1FFA",
        u"\u1FFB",u"\u1FFC",u"\u2102",u"\u2107",u"\u210B",u"\u210C",u"\u210D",
        u"\u2110",u"\u2111",u"\u2112",u"\u2115",u"\u2119",u"\u211A",u"\u211B",
        u"\u211C",u"\u211D",u"\u2124",u"\u2126",u"\u2128",u"\u212A",u"\u212B",
        u"\u212C",u"\u212D",u"\u2130",u"\u2131",u"\u2132",u"\u2133",u"\u213E",
        u"\u213F",u"\u2145",u"\u2183",u"\u2C0A",u"\u2C22",u"\u2C24",u"\u2C25",
        u"\u2C27",u"\u2C28",u"\u2C29",u"\u2C2D",u"\u2C2E",u"\u2C60",u"\u2C62",
        u"\u2C63",u"\u2C64",u"\u2C67",u"\u2C69",u"\u2C6B",u"\u2C6D",u"\u2C6E",
        u"\u2C6F",u"\u2C70",u"\u2C72",u"\u2C75",u"\u2C7E",u"\u2C7F",u"\u2CB2",
        u"\u2CB4",u"\u2CB6",u"\u2CB8",u"\u2CBA",u"\u2CBC",u"\u2CBE",u"\u2CC2",
        u"\u2CC4",u"\u2CC6",u"\u2CC8",u"\u2CCA",u"\u2CCC",u"\u2CCE",u"\u2CD0",
        u"\u2CD2",u"\u2CD4",u"\u2CD6",u"\u2CD8",u"\u2CDA",u"\u2CDC",u"\u2CDE",
        u"\u2CE0",u"\u2CE2",u"\u2CEB",u"\u2CED",u"\uA644",u"\uA64A",u"\uA64C",
        u"\uA64E",u"\uA650",u"\uA652",u"\uA654",u"\uA656",u"\uA658",u"\uA65A",
        u"\uA65C",u"\uA660",u"\uA662",u"\uA664",u"\uA666",u"\uA668",u"\uA66A",
        u"\uA66C",u"\uA680",u"\uA682",u"\uA684",u"\uA686",u"\uA688",u"\uA68A",
        u"\uA68C",u"\uA68E",u"\uA690",u"\uA692",u"\uA694",u"\uA696",u"\uA722",
        u"\uA724",u"\uA726",u"\uA728",u"\uA72A",u"\uA72C",u"\uA72E",u"\uA732",
        u"\uA734",u"\uA736",u"\uA738",u"\uA73A",u"\uA73C",u"\uA73E",u"\uA740",
        u"\uA742",u"\uA744",u"\uA746",u"\uA748",u"\uA74A",u"\uA74C",u"\uA74E",
        u"\uA750",u"\uA752",u"\uA754",u"\uA756",u"\uA758",u"\uA75A",u"\uA75C",
        u"\uA75E",u"\uA760",u"\uA762",u"\uA764",u"\uA766",u"\uA768",u"\uA76A",
        u"\uA76C",u"\uA76E",u"\uA779",u"\uA77B",u"\uA77D",u"\uA77E",u"\uA780",
        u"\uA782",u"\uA784",u"\uA786",u"\uA78B",u"\uA78D",u"\uA790",u"\uA7A0",
        u"\uA7A2",u"\uA7A4",u"\uA7A6",u"\uA7A8",u"\uFB50",u"\uFB52",u"\uFB54",
        u"\uFB56",u"\uFB58",u"\uFB5A",u"\uFB5C",u"\uFB5E",u"\uFB60",u"\uFB62",
        u"\uFB64",u"\uFB66",u"\uFB68",u"\uFB6A",u"\uFB6C",u"\uFB6E",u"\uFB70",
        u"\uFB72",u"\uFB74",u"\uFB76",u"\uFB78",u"\uFB7A",u"\uFB7C",u"\uFB7E",
        u"\uFB80",u"\uFB82",u"\uFB84",u"\uFB86",u"\uFB88",u"\uFB8A",u"\uFB8C",
        u"\uFB8E",u"\uFB90",u"\uFB92",u"\uFB94",u"\uFB96",u"\uFB98",u"\uFB9A",
        u"\uFB9C",u"\uFB9E",u"\uFBA0",u"\uFBA2",u"\uFBA4",u"\uFBA6",u"\uFBA8",
        u"\uFBAA",u"\uFBAC",u"\uFBAE",u"\uFBB0",u"\uFBD3",u"\uFBD5",u"\uFBD7",
        u"\uFBD9",u"\uFBDB",u"\uFBDD",u"\uFBDE",u"\uFBE0",u"\uFBE2",u"\uFBE4",
        u"\uFBE6",u"\uFBE8",u"\uFBEA",u"\uFBEC",u"\uFBEE",u"\uFBF0",u"\uFBF2",
        u"\uFBF4",u"\uFBF6",u"\uFBF8",u"\uFBF9",u"\uFBFB",u"\uFBFC",u"\uFBFE",
        u"\uFC00",u"\uFC01",u"\uFC02",u"\uFC03",u"\uFC04",u"\uFC05",u"\uFC06",
        u"\uFC07",u"\uFC08",u"\uFC09",u"\uFC0A",u"\uFC0B",u"\uFC0C",u"\uFC0D",
        u"\uFC0E",u"\uFC0F",u"\uFC10",u"\uFC11",u"\uFC12",u"\uFC13",u"\uFC14",
        u"\uFC15",u"\uFC16",u"\uFC17",u"\uFC18",u"\uFC19",u"\uFC1A",u"\uFC1B",
        u"\uFC1C",u"\uFC1D",u"\uFC1E",u"\uFC1F",u"\uFC20",u"\uFC21",u"\uFC22",
        u"\uFC23",u"\uFC24",u"\uFC25",u"\uFC26",u"\uFC27",u"\uFC28",u"\uFC29",
        u"\uFC2A",u"\uFC2B",u"\uFC2C",u"\uFC2D",u"\uFC2E",u"\uFC2F",u"\uFC30",
        u"\uFC31",u"\uFC32",u"\uFC33",u"\uFC34",u"\uFC35",u"\uFC36",u"\uFC37",
        u"\uFC38",u"\uFC39",u"\uFC3A",u"\uFC3B",u"\uFC3C",u"\uFC3D",u"\uFC3E",
        u"\uFC3F",u"\uFC40",u"\uFC41",u"\uFC42",u"\uFC43",u"\uFC44",u"\uFC45",
        u"\uFC46",u"\uFC47",u"\uFC48",u"\uFC49",u"\uFC4A",u"\uFC4B",u"\uFC4C",
        u"\uFC4D",u"\uFC4E",u"\uFC4F",u"\uFC50",u"\uFC51",u"\uFC52",u"\uFC53",
        u"\uFC54",u"\uFC55",u"\uFC56",u"\uFC57",u"\uFC58",u"\uFC59",u"\uFC5A",
        u"\uFC5B",u"\uFC5C",u"\uFC5D",u"\uFC5E",u"\uFC5F",u"\uFC60",u"\uFC61",
        u"\uFC62",u"\uFC63",u"\uFC97",u"\uFC98",u"\uFC99",u"\uFC9A",u"\uFC9B",
        u"\uFC9C",u"\uFC9D",u"\uFC9E",u"\uFC9F",u"\uFCA0",u"\uFCA1",u"\uFCA2",
        u"\uFCA3",u"\uFCA4",u"\uFCA5",u"\uFCA6",u"\uFCA7",u"\uFCA8",u"\uFCA9",
        u"\uFCAA",u"\uFCAB",u"\uFCAC",u"\uFCAD",u"\uFCAE",u"\uFCAF",u"\uFCB0",
        u"\uFCB1",u"\uFCB2",u"\uFCB3",u"\uFCB4",u"\uFCB5",u"\uFCB6",u"\uFCB7",
        u"\uFCB8",u"\uFCB9",u"\uFCBA",u"\uFCBB",u"\uFCBC",u"\uFCBD",u"\uFCBE",
        u"\uFCBF",u"\uFCC0",u"\uFCC1",u"\uFCC2",u"\uFCC3",u"\uFCC4",u"\uFCC5",
        u"\uFCC6",u"\uFCC7",u"\uFCC8",u"\uFCC9",u"\uFCCA",u"\uFCCB",u"\uFCCC",
        u"\uFCCD",u"\uFCCE",u"\uFCCF",u"\uFCD0",u"\uFCD1",u"\uFCD2",u"\uFCD3",
        u"\uFCD4",u"\uFCD5",u"\uFCD6",u"\uFCD7",u"\uFCD8",u"\uFCD9",u"\uFCDA",
        u"\uFCDB",u"\uFCDC",u"\uFCDD",u"\uFCDE",u"\uFCF5",u"\uFCF6",u"\uFCF7",
        u"\uFCF8",u"\uFCF9",u"\uFCFA",u"\uFCFB",u"\uFCFC",u"\uFCFD",u"\uFCFE",
        u"\uFCFF",u"\uFD00",u"\uFD01",u"\uFD02",u"\uFD03",u"\uFD04",u"\uFD05",
        u"\uFD06",u"\uFD07",u"\uFD08",u"\uFD09",u"\uFD0A",u"\uFD0B",u"\uFD0C",
        u"\uFD0D",u"\uFD0E",u"\uFD0F",u"\uFD10",u"\uFD2D",u"\uFD2E",u"\uFD2F",
        u"\uFD30",u"\uFD31",u"\uFD32",u"\uFD33",u"\uFD3D",u"\uFD50",u"\uFD52",
        u"\uFD53",u"\uFD54",u"\uFD55",u"\uFD56",u"\uFD57",u"\uFD59",u"\uFD5C",
        u"\uFD5D",u"\uFD60",u"\uFD61",u"\uFD63",u"\uFD65",u"\uFD68",u"\uFD6B",
        u"\uFD6D",u"\uFD70",u"\uFD72",u"\uFD73",u"\uFD77",u"\uFD7D",u"\uFD83",
        u"\uFD86",u"\uFD88",u"\uFD89",u"\uFD8A",u"\uFD8C",u"\uFD8D",u"\uFD8E",
        u"\uFD8F",u"\uFD92",u"\uFD93",u"\uFD94",u"\uFD95",u"\uFD98",u"\uFD9D",
        u"\uFDB4",u"\uFDB5",u"\uFDB8",u"\uFDBA",u"\uFDC3",u"\uFDC4",u"\uFDC5",
        u"\uFDF0",u"\uFDF1",u"\uFDF2",u"\uFDF3",u"\uFDF4",u"\uFDF5",u"\uFDF6",
        u"\uFDF7",u"\uFDF8",u"\uFDF9",u"\uFDFA",u"\uFDFB",u"\uFDFC",u"\uFE70",
        u"\uFE72",u"\uFE74",u"\uFE76",u"\uFE78",u"\uFE7A",u"\uFE7C",u"\uFE7E",
        u"\uFE80",u"\uFE81",u"\uFE83",u"\uFE85",u"\uFE87",u"\uFE89",u"\uFE8B",
        u"\uFE8D",u"\uFE8F",u"\uFE91",u"\uFE93",u"\uFE95",u"\uFE97",u"\uFE99",
        u"\uFE9B",u"\uFE9D",u"\uFE9F",u"\uFEA1",u"\uFEA3",u"\uFEA5",u"\uFEA7",
        u"\uFEA9",u"\uFEAB",u"\uFEAD",u"\uFEAF",u"\uFEB1",u"\uFEB3",u"\uFEB5",
        u"\uFEB7",u"\uFEB9",u"\uFEBB",u"\uFEBD",u"\uFEBF",u"\uFEC1",u"\uFEC3",
        u"\uFEC5",u"\uFEC7",u"\uFEC9",u"\uFECB",u"\uFECD",u"\uFECF",u"\uFED1",
        u"\uFED3",u"\uFED5",u"\uFED7",u"\uFED9",u"\uFEDB",u"\uFEDD",u"\uFEDF",
        u"\uFEE1",u"\uFEE3",u"\uFEE5",u"\uFEE7",u"\uFEE9",u"\uFEEB",u"\uFEED",
        u"\uFEEF",u"\uFEF1",u"\uFEF3",u"\uFEF5",u"\uFEF7",u"\uFEF9",u"\uFEFB",
        u"\uFF21",u"\uFF22",u"\uFF23",u"\uFF24",u"\uFF25",u"\uFF26",u"\uFF27",
        u"\uFF28",u"\uFF29",u"\uFF2A",u"\uFF2B",u"\uFF2C",u"\uFF2D",u"\uFF2E",
        u"\uFF2F",u"\uFF30",u"\uFF31",u"\uFF32",u"\uFF33",u"\uFF34",u"\uFF35",
        u"\uFF36",u"\uFF37",u"\uFF38",u"\uFF39",u"\uFF3A"],
    "AnyConsonants" : [
        u"\u00AA",u"\u00B5",u"\u00BA",u"\u00DF",u"\u00E0",u"\u00E1",u"\u00E2",
        u"\u00E3",u"\u00E4",u"\u00E5",u"\u00E6",u"\u00E7",u"\u00E8",u"\u00E9",
        u"\u00EA",u"\u00EB",u"\u00EC",u"\u00ED",u"\u00EE",u"\u00EF",u"\u00F0",
        u"\u00F1",u"\u00F2",u"\u00F3",u"\u00F4",u"\u00F5",u"\u00F6",u"\u00F8",
        u"\u00F9",u"\u00FA",u"\u00FB",u"\u00FC",u"\u00FD",u"\u00FE",u"\u00FF",
        u"\u0101",u"\u0103",u"\u0105",u"\u0107",u"\u0109",u"\u010B",u"\u010D",
        u"\u010F",u"\u0111",u"\u0113",u"\u0115",u"\u0117",u"\u0119",u"\u011B",
        u"\u011D",u"\u011F",u"\u0121",u"\u0123",u"\u0125",u"\u0127",u"\u0129",
        u"\u012B",u"\u012D",u"\u012F",u"\u0131",u"\u0133",u"\u0135",u"\u0137",
        u"\u0138",u"\u013A",u"\u013C",u"\u013E",u"\u0140",u"\u0142",u"\u0144",
        u"\u0146",u"\u0148",u"\u0149",u"\u014B",u"\u014D",u"\u014F",u"\u0151",
        u"\u0153",u"\u0155",u"\u0157",u"\u0159",u"\u015B",u"\u015D",u"\u015F",
        u"\u0161",u"\u0163",u"\u0165",u"\u0167",u"\u0169",u"\u016B",u"\u016D",
        u"\u016F",u"\u0171",u"\u0173",u"\u0175",u"\u0177",u"\u017A",u"\u017C",
        u"\u017E",u"\u017F",u"\u0180",u"\u0183",u"\u0185",u"\u0188",u"\u018C",
        u"\u018D",u"\u0192",u"\u0195",u"\u0199",u"\u019A",u"\u019B",u"\u019E",
        u"\u01A1",u"\u01A3",u"\u01A5",u"\u01A8",u"\u01AA",u"\u01AB",u"\u01AD",
        u"\u01B0",u"\u01B4",u"\u01B6",u"\u01B9",u"\u01BA",u"\u01BB",u"\u01BD",
        u"\u01BE",u"\u01BF",u"\u01C0",u"\u01C1",u"\u01C2",u"\u01C3",u"\u01C6",
        u"\u01C9",u"\u01CC",u"\u01CE",u"\u01D0",u"\u01D2",u"\u01D4",u"\u01D6",
        u"\u01D8",u"\u01DA",u"\u01DC",u"\u01DD",u"\u01DF",u"\u01E1",u"\u01E3",
        u"\u01E5",u"\u01E7",u"\u01E9",u"\u01EB",u"\u01ED",u"\u01EF",u"\u01F0",
        u"\u01F3",u"\u01F5",u"\u01F9",u"\u01FB",u"\u01FD",u"\u01FF",u"\u0201",
        u"\u0203",u"\u0205",u"\u0207",u"\u0209",u"\u020B",u"\u020D",u"\u020F",
        u"\u0211",u"\u0213",u"\u0215",u"\u0217",u"\u0219",u"\u021B",u"\u021D",
        u"\u021F",u"\u0221",u"\u0223",u"\u0225",u"\u0227",u"\u0229",u"\u022B",
        u"\u022D",u"\u022F",u"\u0231",u"\u0233",u"\u0234",u"\u0235",u"\u0236",
        u"\u0237",u"\u0238",u"\u0239",u"\u023C",u"\u023F",u"\u0240",u"\u0242",
        u"\u0247",u"\u0249",u"\u024B",u"\u024D",u"\u024F",u"\u0250",u"\u0251",
        u"\u0252",u"\u0253",u"\u0254",u"\u0255",u"\u0256",u"\u0257",u"\u0258",
        u"\u0259",u"\u025A",u"\u025B",u"\u025C",u"\u025D",u"\u025E",u"\u025F",
        u"\u0260",u"\u0261",u"\u0262",u"\u0263",u"\u0264",u"\u0265",u"\u0266",
        u"\u0267",u"\u0268",u"\u0269",u"\u026A",u"\u026B",u"\u026C",u"\u026D",
        u"\u026E",u"\u026F",u"\u0270",u"\u0271",u"\u0272",u"\u0273",u"\u0274",
        u"\u0275",u"\u0276",u"\u0277",u"\u0278",u"\u0279",u"\u027A",u"\u027B",
        u"\u027C",u"\u027D",u"\u027E",u"\u027F",u"\u0280",u"\u0281",u"\u0282",
        u"\u0283",u"\u0284",u"\u0285",u"\u0286",u"\u0287",u"\u0288",u"\u0289",
        u"\u028A",u"\u028B",u"\u028C",u"\u028D",u"\u028E",u"\u028F",u"\u0290",
        u"\u0291",u"\u0292",u"\u0293",u"\u0294",u"\u0295",u"\u0296",u"\u0297",
        u"\u0298",u"\u0299",u"\u029A",u"\u029B",u"\u029C",u"\u029D",u"\u029E",
        u"\u029F",u"\u02A0",u"\u02A1",u"\u02A2",u"\u02A3",u"\u02A4",u"\u02A5",
        u"\u02A6",u"\u02A7",u"\u02A8",u"\u02A9",u"\u02AA",u"\u02AB",u"\u02AC",
        u"\u02AD",u"\u02AE",u"\u02AF",u"\u02B0",u"\u02B1",u"\u02B2",u"\u02B3",
        u"\u02B4",u"\u02B5",u"\u02B6",u"\u02B7",u"\u02B8",u"\u02BA",u"\u02BB",
        u"\u02BD",u"\u02BE",u"\u02BF",u"\u02C0",u"\u02C1",u"\u02C6",u"\u02C7",
        u"\u02C8",u"\u02CA",u"\u02CB",u"\u02CC",u"\u02CD",u"\u02CE",u"\u02CF",
        u"\u02D0",u"\u02D1",u"\u02E0",u"\u02E1",u"\u02E2",u"\u02E3",u"\u02E4",
        u"\u02EE",u"\u0371",u"\u0373",u"\u0374",u"\u0377",u"\u037A",u"\u037B",
        u"\u037C",u"\u037D",u"\u0390",u"\u03AC",u"\u03AD",u"\u03AE",u"\u03AF",
        u"\u03B0",u"\u03CA",u"\u03CB",u"\u03CC",u"\u03CD",u"\u03CE",u"\u03D0",
        u"\u03D1",u"\u03D5",u"\u03D6",u"\u03D7",u"\u03D9",u"\u03DB",u"\u03DD",
        u"\u03DF",u"\u03E1",u"\u03F0",u"\u03F1",u"\u03F2",u"\u03F3",u"\u03F5",
        u"\u03F8",u"\u03FB",u"\u03FC",u"\u0439",u"\u044A",u"\u044C",u"\u0450",
        u"\u0451",u"\u0452",u"\u0453",u"\u0454",u"\u0455",u"\u0456",u"\u0457",
        u"\u0458",u"\u0459",u"\u045A",u"\u045B",u"\u045C",u"\u045D",u"\u045E",
        u"\u045F",u"\u0461",u"\u0463",u"\u0465",u"\u0467",u"\u0469",u"\u046B",
        u"\u046D",u"\u046F",u"\u0471",u"\u0473",u"\u0475",u"\u0477",u"\u0479",
        u"\u047B",u"\u047D",u"\u047F",u"\u0481",u"\u048B",u"\u048D",u"\u048F",
        u"\u0491",u"\u0493",u"\u0495",u"\u0497",u"\u0499",u"\u049B",u"\u049D",
        u"\u049F",u"\u04A1",u"\u04A3",u"\u04A5",u"\u04A7",u"\u04A9",u"\u04AB",
        u"\u04AD",u"\u04AF",u"\u04B1",u"\u04B3",u"\u04B5",u"\u04B7",u"\u04B9",
        u"\u04BB",u"\u04BD",u"\u04BF",u"\u04C2",u"\u04C4",u"\u04C6",u"\u04C8",
        u"\u04CA",u"\u04CC",u"\u04CE",u"\u04CF",u"\u04D1",u"\u04D3",u"\u04D5",
        u"\u04D7",u"\u04D9",u"\u04DB",u"\u04DD",u"\u04DF",u"\u04E1",u"\u04E3",
        u"\u04E5",u"\u04E7",u"\u04E9",u"\u04EB",u"\u04ED",u"\u04EF",u"\u04F1",
        u"\u04F3",u"\u04F5",u"\u04F7",u"\u04F9",u"\u04FB",u"\u04FD",u"\u04FF",
        u"\u0501",u"\u0503",u"\u0505",u"\u0507",u"\u0509",u"\u050B",u"\u050D",
        u"\u050F",u"\u0511",u"\u0513",u"\u0515",u"\u0517",u"\u0519",u"\u051B",
        u"\u051D",u"\u051F",u"\u0521",u"\u0523",u"\u0525",u"\u0527",u"\u0559",
        u"\u0587",u"\u05F0",u"\u05F1",u"\u05F2",u"\u0620",u"\u0622",u"\u0623",
        u"\u0624",u"\u0625",u"\u0626",u"\u0629",u"\u063B",u"\u063C",u"\u063D",
        u"\u063E",u"\u063F",u"\u0640",u"\u0649",u"\u066E",u"\u066F",u"\u0671",
        u"\u0672",u"\u0673",u"\u0674",u"\u0675",u"\u0676",u"\u0677",u"\u0678",
        u"\u0679",u"\u067A",u"\u067B",u"\u067C",u"\u067D",u"\u067E",u"\u067F",
        u"\u0680",u"\u0681",u"\u0682",u"\u0683",u"\u0684",u"\u0685",u"\u0686",
        u"\u0687",u"\u0688",u"\u0689",u"\u068A",u"\u068B",u"\u068C",u"\u068D",
        u"\u068E",u"\u068F",u"\u0690",u"\u0691",u"\u0692",u"\u0693",u"\u0694",
        u"\u0695",u"\u0696",u"\u0697",u"\u0698",u"\u0699",u"\u069A",u"\u069B",
        u"\u069C",u"\u069D",u"\u069E",u"\u069F",u"\u06A0",u"\u06A1",u"\u06A2",
        u"\u06A3",u"\u06A4",u"\u06A5",u"\u06A6",u"\u06A7",u"\u06A8",u"\u06A9",
        u"\u06AA",u"\u06AB",u"\u06AC",u"\u06AD",u"\u06AE",u"\u06AF",u"\u06B0",
        u"\u06B1",u"\u06B2",u"\u06B3",u"\u06B4",u"\u06B5",u"\u06B6",u"\u06B7",
        u"\u06B8",u"\u06B9",u"\u06BA",u"\u06BB",u"\u06BC",u"\u06BD",u"\u06BE",
        u"\u06BF",u"\u06C0",u"\u06C1",u"\u06C2",u"\u06C3",u"\u06C4",u"\u06C5",
        u"\u06C6",u"\u06C7",u"\u06C8",u"\u06C9",u"\u06CA",u"\u06CB",u"\u06CD",
        u"\u06CE",u"\u06CF",u"\u06D0",u"\u06D1",u"\u06D2",u"\u06D3",u"\u06D5",
        u"\u06E5",u"\u06E6",u"\u06EE",u"\u06EF",u"\u06FA",u"\u06FB",u"\u06FC",
        u"\u06FF",u"\u0714",u"\u0716",u"\u071C",u"\u071E",u"\u0727",u"\u072D",
        u"\u072E",u"\u072F",u"\u074D",u"\u074E",u"\u074F",u"\u0750",u"\u0751",
        u"\u0752",u"\u0753",u"\u0754",u"\u0755",u"\u0756",u"\u0757",u"\u0758",
        u"\u0759",u"\u075A",u"\u075B",u"\u075C",u"\u075D",u"\u075E",u"\u075F",
        u"\u0760",u"\u0761",u"\u0762",u"\u0763",u"\u0764",u"\u0765",u"\u0766",
        u"\u0767",u"\u0768",u"\u0769",u"\u076A",u"\u076B",u"\u076C",u"\u076D",
        u"\u076E",u"\u076F",u"\u0770",u"\u0771",u"\u0772",u"\u0773",u"\u0774",
        u"\u0775",u"\u0776",u"\u0777",u"\u0778",u"\u0779",u"\u077A",u"\u077B",
        u"\u077C",u"\u077D",u"\u077E",u"\u077F",u"\u07B1",u"\u07E0",u"\u07E7",
        u"\u07E8",u"\u07E9",u"\u07EA",u"\u07F4",u"\u07F5",u"\u07FA",u"\u081A",
        u"\u0824",u"\u0828",u"\u0904",u"\u090B",u"\u090C",u"\u090D",u"\u090E",
        u"\u0911",u"\u0912",u"\u0929",u"\u0931",u"\u0933",u"\u0934",u"\u093D",
        u"\u0950",u"\u0958",u"\u0959",u"\u095A",u"\u095B",u"\u095C",u"\u095D",
        u"\u095E",u"\u095F",u"\u0960",u"\u0961",u"\u0971",u"\u0972",u"\u0973",
        u"\u0974",u"\u0975",u"\u0976",u"\u0977",u"\u0979",u"\u097A",u"\u097B",
        u"\u097C",u"\u097D",u"\u097E",u"\u097F",u"\u098B",u"\u098C",u"\u09BD",
        u"\u09CE",u"\u09DC",u"\u09DD",u"\u09DF",u"\u09E0",u"\u09E1",u"\u09F0",
        u"\u09F1",u"\u0A59",u"\u0A5A",u"\u0A5B",u"\u0A5C",u"\u0A5E",u"\u0A72",
        u"\u0A73",u"\u0A74",u"\u0A8B",u"\u0A8C",u"\u0A8D",u"\u0A91",u"\u0ABD",
        u"\u0AD0",u"\u0AE0",u"\u0AE1",u"\u0B0B",u"\u0B0C",u"\u0B3D",u"\u0B5C",
        u"\u0B5D",u"\u0B60",u"\u0B61",u"\u0B83",u"\u0BD0",u"\u0C0B",u"\u0C0C",
        u"\u0C3D",u"\u0C58",u"\u0C59",u"\u0C60",u"\u0C61",u"\u0C8B",u"\u0C8C",
        u"\u0CBD",u"\u0CDE",u"\u0CE0",u"\u0CE1",u"\u0CF1",u"\u0CF2",u"\u0D0B",
        u"\u0D0C",u"\u0D29",u"\u0D3A",u"\u0D3D",u"\u0D4E",u"\u0D60",u"\u0D61",
        u"\u0D7A",u"\u0D7B",u"\u0D7C",u"\u0D7D",u"\u0D7E",u"\u0D7F",u"\u0DA5",
        u"\u0E24",u"\u0E26",u"\u0E2F",u"\u0E45",u"\u0E46",u"\u0E82",u"\u0E84",
        u"\u0E8A",u"\u0E96",u"\u0E97",u"\u0E9C",u"\u0E9D",u"\u0E9E",u"\u0E9F",
        u"\u0EA3",u"\u0EA5",u"\u0EAA",u"\u0EAB",u"\u0EAE",u"\u0EAF",u"\u0EBD",
        u"\u0EC6",u"\u0EDC",u"\u0EDD",u"\u0F00",u"\u0F60",u"\u0F6A",u"\u0F88",
        u"\u0F89",u"\u0F8A",u"\u0F8B",u"\u0F8C",u"\u1022",u"\u1028",u"\u103F",
        u"\u1052",u"\u1053",u"\u1054",u"\u1055",u"\u105A",u"\u105B",u"\u105C",
        u"\u105D",u"\u1061",u"\u1065",u"\u1066",u"\u106E",u"\u106F",u"\u1070",
        u"\u1075",u"\u1076",u"\u1077",u"\u1078",u"\u1079",u"\u107A",u"\u107B",
        u"\u107C",u"\u107D",u"\u107E",u"\u107F",u"\u1080",u"\u1081",u"\u108E",
        u"\u10F9",u"\u10FC",u"\u1113",u"\u1115",u"\u1116",u"\u1117",u"\u1118",
        u"\u111A",u"\u111C",u"\u111E",u"\u111F",u"\u1120",u"\u1121",u"\u1122",
        u"\u1123",u"\u1124",u"\u1125",u"\u1126",u"\u1127",u"\u1128",u"\u1129",
        u"\u112A",u"\u112D",u"\u112E",u"\u112F",u"\u1130",u"\u1131",u"\u1132",
        u"\u1133",u"\u1134",u"\u1135",u"\u1136",u"\u1137",u"\u1138",u"\u1139",
        u"\u113A",u"\u113B",u"\u1141",u"\u1142",u"\u1143",u"\u1144",u"\u1145",
        u"\u1146",u"\u1148",u"\u1149",u"\u114A",u"\u114B",u"\u114D",u"\u1152",
        u"\u1153",u"\u1156",u"\u115A",u"\u115B",u"\u115C",u"\u115D",u"\u115E",
        u"\u115F",u"\u1160",u"\u1176",u"\u1177",u"\u1178",u"\u1179",u"\u117A",
        u"\u117B",u"\u117C",u"\u117D",u"\u117E",u"\u117F",u"\u1180",u"\u1181",
        u"\u1182",u"\u1183",u"\u1184",u"\u1185",u"\u1186",u"\u1187",u"\u1188",
        u"\u1189",u"\u118A",u"\u118B",u"\u118C",u"\u118D",u"\u118E",u"\u118F",
        u"\u1190",u"\u1191",u"\u1192",u"\u1193",u"\u1194",u"\u1195",u"\u1196",
        u"\u1197",u"\u1198",u"\u1199",u"\u119A",u"\u119B",u"\u119C",u"\u119D",
        u"\u119F",u"\u11A0",u"\u11A1",u"\u11A3",u"\u11A4",u"\u11A5",u"\u11A6",
        u"\u11A7",u"\u11AA",u"\u11AC",u"\u11AD",u"\u11B0",u"\u11B1",u"\u11B2",
        u"\u11B3",u"\u11B4",u"\u11B5",u"\u11B6",u"\u11B9",u"\u11C3",u"\u11C4",
        u"\u11C5",u"\u11C6",u"\u11C7",u"\u11C8",u"\u11C9",u"\u11CA",u"\u11CB",
        u"\u11CC",u"\u11CD",u"\u11CE",u"\u11CF",u"\u11D1",u"\u11D2",u"\u11D3",
        u"\u11D4",u"\u11D5",u"\u11D6",u"\u11D7",u"\u11D8",u"\u11D9",u"\u11DA",
        u"\u11DB",u"\u11DC",u"\u11DD",u"\u11DE",u"\u11DF",u"\u11E0",u"\u11E1",
        u"\u11E3",u"\u11E4",u"\u11E5",u"\u11E7",u"\u11E8",u"\u11E9",u"\u11EA",
        u"\u11EC",u"\u11ED",u"\u11EF",u"\u11F1",u"\u11F2",u"\u11F3",u"\u11F5",
        u"\u11F6",u"\u11F7",u"\u11F8",u"\u11FA",u"\u11FB",u"\u11FC",u"\u11FD",
        u"\u11FE",u"\u1200",u"\u1201",u"\u1202",u"\u1203",u"\u1204",u"\u1205",
        u"\u1206",u"\u1207",u"\u1208",u"\u1209",u"\u120A",u"\u120B",u"\u120C",
        u"\u120D",u"\u120E",u"\u120F",u"\u1210",u"\u1211",u"\u1212",u"\u1213",
        u"\u1214",u"\u1215",u"\u1216",u"\u1217",u"\u1218",u"\u1219",u"\u121A",
        u"\u121B",u"\u121C",u"\u121D",u"\u121E",u"\u121F",u"\u1220",u"\u1221",
        u"\u1222",u"\u1223",u"\u1224",u"\u1225",u"\u1226",u"\u1227",u"\u1228",
        u"\u1229",u"\u122A",u"\u122B",u"\u122C",u"\u122D",u"\u122E",u"\u122F",
        u"\u1230",u"\u1231",u"\u1232",u"\u1233",u"\u1234",u"\u1235",u"\u1236",
        u"\u1237",u"\u1238",u"\u1239",u"\u123A",u"\u123B",u"\u123C",u"\u123D",
        u"\u123E",u"\u123F",u"\u1240",u"\u1241",u"\u1242",u"\u1243",u"\u1244",
        u"\u1245",u"\u1246",u"\u1247",u"\u1248",u"\u124A",u"\u124B",u"\u124C",
        u"\u124D",u"\u1250",u"\u1251",u"\u1252",u"\u1253",u"\u1254",u"\u1255",
        u"\u1256",u"\u1258",u"\u125A",u"\u125B",u"\u125C",u"\u125D",u"\u1260",
        u"\u1261",u"\u1262",u"\u1263",u"\u1264",u"\u1265",u"\u1266",u"\u1267",
        u"\u1268",u"\u1269",u"\u126A",u"\u126B",u"\u126C",u"\u126D",u"\u126E",
        u"\u126F",u"\u1270",u"\u1271",u"\u1272",u"\u1273",u"\u1274",u"\u1275",
        u"\u1276",u"\u1277",u"\u1278",u"\u1279",u"\u127A",u"\u127B",u"\u127C",
        u"\u127D",u"\u127E",u"\u127F",u"\u1280",u"\u1281",u"\u1282",u"\u1283",
        u"\u1284",u"\u1285",u"\u1286",u"\u1287",u"\u1288",u"\u128A",u"\u128B",
        u"\u128C",u"\u128D",u"\u1290",u"\u1291",u"\u1292",u"\u1293",u"\u1294",
        u"\u1295",u"\u1296",u"\u1297",u"\u1298",u"\u1299",u"\u129A",u"\u129B",
        u"\u129C",u"\u129D",u"\u129E",u"\u129F",u"\u12A0",u"\u12A1",u"\u12A2",
        u"\u12A3",u"\u12A4",u"\u12A5",u"\u12A6",u"\u12A7",u"\u12A8",u"\u12A9",
        u"\u12AA",u"\u12AB",u"\u12AC",u"\u12AD",u"\u12AE",u"\u12AF",u"\u12B0",
        u"\u12B2",u"\u12B3",u"\u12B4",u"\u12B5",u"\u12B8",u"\u12B9",u"\u12BA",
        u"\u12BB",u"\u12BC",u"\u12BD",u"\u12BE",u"\u12C0",u"\u12C2",u"\u12C3",
        u"\u12C4",u"\u12C5",u"\u12C8",u"\u12C9",u"\u12CA",u"\u12CB",u"\u12CC",
        u"\u12CD",u"\u12CE",u"\u12CF",u"\u12D0",u"\u12D1",u"\u12D2",u"\u12D3",
        u"\u12D4",u"\u12D5",u"\u12D6",u"\u12D8",u"\u12D9",u"\u12DA",u"\u12DB",
        u"\u12DC",u"\u12DD",u"\u12DE",u"\u12DF",u"\u12E0",u"\u12E1",u"\u12E2",
        u"\u12E3",u"\u12E4",u"\u12E5",u"\u12E6",u"\u12E7",u"\u12E8",u"\u12E9",
        u"\u12EA",u"\u12EB",u"\u12EC",u"\u12ED",u"\u12EE",u"\u12EF",u"\u12F0",
        u"\u12F1",u"\u12F2",u"\u12F3",u"\u12F4",u"\u12F5",u"\u12F6",u"\u12F7",
        u"\u12F8",u"\u12F9",u"\u12FA",u"\u12FB",u"\u12FC",u"\u12FD",u"\u12FE",
        u"\u12FF",u"\u1300",u"\u1301",u"\u1302",u"\u1303",u"\u1304",u"\u1305",
        u"\u1306",u"\u1307",u"\u1308",u"\u1309",u"\u130A",u"\u130B",u"\u130C",
        u"\u130D",u"\u130E",u"\u130F",u"\u1310",u"\u1312",u"\u1313",u"\u1314",
        u"\u1315",u"\u1318",u"\u1319",u"\u131A",u"\u131B",u"\u131C",u"\u131D",
        u"\u131E",u"\u131F",u"\u1320",u"\u1321",u"\u1322",u"\u1323",u"\u1324",
        u"\u1325",u"\u1326",u"\u1327",u"\u1328",u"\u1329",u"\u132A",u"\u132B",
        u"\u132C",u"\u132D",u"\u132E",u"\u132F",u"\u1330",u"\u1331",u"\u1332",
        u"\u1333",u"\u1334",u"\u1335",u"\u1336",u"\u1337",u"\u1338",u"\u1339",
        u"\u133A",u"\u133B",u"\u133C",u"\u133D",u"\u133E",u"\u133F",u"\u1340",
        u"\u1341",u"\u1342",u"\u1343",u"\u1344",u"\u1345",u"\u1346",u"\u1347",
        u"\u1348",u"\u1349",u"\u134A",u"\u134B",u"\u134C",u"\u134D",u"\u134E",
        u"\u134F",u"\u1350",u"\u1351",u"\u1352",u"\u1353",u"\u1354",u"\u1355",
        u"\u1356",u"\u1357",u"\u1358",u"\u1359",u"\u135A",u"\u1380",u"\u1381",
        u"\u1382",u"\u1383",u"\u1384",u"\u1385",u"\u1386",u"\u1387",u"\u1388",
        u"\u1389",u"\u138A",u"\u138B",u"\u138C",u"\u138D",u"\u138E",u"\u138F",
        u"\u1401",u"\u1402",u"\u1403",u"\u1404",u"\u1405",u"\u1406",u"\u1407",
        u"\u1408",u"\u1409",u"\u140A",u"\u140B",u"\u140C",u"\u140D",u"\u140E",
        u"\u140F",u"\u1410",u"\u1411",u"\u1412",u"\u1413",u"\u1414",u"\u1415",
        u"\u1416",u"\u1417",u"\u1418",u"\u1419",u"\u141A",u"\u141B",u"\u141C",
        u"\u141D",u"\u141E",u"\u141F",u"\u1420",u"\u1421",u"\u1422",u"\u1423",
        u"\u1424",u"\u1425",u"\u1426",u"\u1427",u"\u1428",u"\u1429",u"\u142A",
        u"\u142B",u"\u142C",u"\u142D",u"\u142E",u"\u142F",u"\u1430",u"\u1431",
        u"\u1432",u"\u1433",u"\u1434",u"\u1435",u"\u1436",u"\u1437",u"\u1438",
        u"\u1439",u"\u143A",u"\u143B",u"\u143C",u"\u143D",u"\u143E",u"\u143F",
        u"\u1440",u"\u1441",u"\u1442",u"\u1443",u"\u1444",u"\u1445",u"\u1446",
        u"\u1447",u"\u1448",u"\u1449",u"\u144A",u"\u144B",u"\u144C",u"\u144D",
        u"\u144E",u"\u144F",u"\u1450",u"\u1451",u"\u1452",u"\u1453",u"\u1454",
        u"\u1455",u"\u1456",u"\u1457",u"\u1458",u"\u1459",u"\u145A",u"\u145B",
        u"\u145C",u"\u145D",u"\u145E",u"\u145F",u"\u1460",u"\u1461",u"\u1462",
        u"\u1463",u"\u1464",u"\u1465",u"\u1466",u"\u1467",u"\u1468",u"\u1469",
        u"\u146A",u"\u146B",u"\u146C",u"\u146D",u"\u146E",u"\u146F",u"\u1470",
        u"\u1471",u"\u1472",u"\u1473",u"\u1474",u"\u1475",u"\u1476",u"\u1477",
        u"\u1478",u"\u1479",u"\u147A",u"\u147B",u"\u147C",u"\u147D",u"\u147E",
        u"\u147F",u"\u1480",u"\u1481",u"\u1482",u"\u1483",u"\u1484",u"\u1485",
        u"\u1486",u"\u1487",u"\u1488",u"\u1489",u"\u148A",u"\u148B",u"\u148C",
        u"\u148D",u"\u148E",u"\u148F",u"\u1490",u"\u1491",u"\u1492",u"\u1493",
        u"\u1494",u"\u1495",u"\u1496",u"\u1497",u"\u1498",u"\u1499",u"\u149A",
        u"\u149B",u"\u149C",u"\u149D",u"\u149E",u"\u149F",u"\u14A0",u"\u14A1",
        u"\u14A2",u"\u14A3",u"\u14A4",u"\u14A5",u"\u14A6",u"\u14A7",u"\u14A8",
        u"\u14A9",u"\u14AA",u"\u14AB",u"\u14AC",u"\u14AD",u"\u14AE",u"\u14AF",
        u"\u14B0",u"\u14B1",u"\u14B2",u"\u14B3",u"\u14B4",u"\u14B5",u"\u14B6",
        u"\u14B7",u"\u14B8",u"\u14B9",u"\u14BA",u"\u14BB",u"\u14BC",u"\u14BD",
        u"\u14BE",u"\u14BF",u"\u14C0",u"\u14C1",u"\u14C2",u"\u14C3",u"\u14C4",
        u"\u14C5",u"\u14C6",u"\u14C7",u"\u14C8",u"\u14C9",u"\u14CA",u"\u14CB",
        u"\u14CC",u"\u14CD",u"\u14CE",u"\u14CF",u"\u14D0",u"\u14D1",u"\u14D2",
        u"\u14D3",u"\u14D4",u"\u14D5",u"\u14D6",u"\u14D7",u"\u14D8",u"\u14D9",
        u"\u14DA",u"\u14DB",u"\u14DC",u"\u14DD",u"\u14DE",u"\u14DF",u"\u14E0",
        u"\u14E1",u"\u14E2",u"\u14E3",u"\u14E4",u"\u14E5",u"\u14E6",u"\u14E7",
        u"\u14E8",u"\u14E9",u"\u14EA",u"\u14EB",u"\u14EC",u"\u14ED",u"\u14EE",
        u"\u14EF",u"\u14F0",u"\u14F1",u"\u14F2",u"\u14F3",u"\u14F4",u"\u14F5",
        u"\u14F6",u"\u14F7",u"\u14F8",u"\u14F9",u"\u14FA",u"\u14FB",u"\u14FC",
        u"\u14FD",u"\u14FE",u"\u14FF",u"\u1500",u"\u1501",u"\u1502",u"\u1503",
        u"\u1504",u"\u1505",u"\u1506",u"\u1507",u"\u1508",u"\u1509",u"\u150A",
        u"\u150B",u"\u150C",u"\u150D",u"\u150E",u"\u150F",u"\u1510",u"\u1511",
        u"\u1512",u"\u1513",u"\u1514",u"\u1515",u"\u1516",u"\u1517",u"\u1518",
        u"\u1519",u"\u151A",u"\u151B",u"\u151C",u"\u151D",u"\u151E",u"\u151F",
        u"\u1520",u"\u1521",u"\u1522",u"\u1523",u"\u1524",u"\u1525",u"\u1526",
        u"\u1527",u"\u1528",u"\u1529",u"\u152A",u"\u152B",u"\u152C",u"\u152D",
        u"\u152E",u"\u152F",u"\u1530",u"\u1531",u"\u1532",u"\u1533",u"\u1534",
        u"\u1535",u"\u1536",u"\u1537",u"\u1538",u"\u1539",u"\u153A",u"\u153B",
        u"\u153C",u"\u153D",u"\u153E",u"\u153F",u"\u1540",u"\u1541",u"\u1542",
        u"\u1543",u"\u1544",u"\u1545",u"\u1546",u"\u1547",u"\u1548",u"\u1549",
        u"\u154A",u"\u154B",u"\u154C",u"\u154D",u"\u154E",u"\u154F",u"\u1550",
        u"\u1551",u"\u1552",u"\u1553",u"\u1554",u"\u1555",u"\u1556",u"\u1557",
        u"\u1558",u"\u1559",u"\u155A",u"\u155B",u"\u155C",u"\u155D",u"\u155E",
        u"\u155F",u"\u1560",u"\u1561",u"\u1562",u"\u1563",u"\u1564",u"\u1565",
        u"\u1566",u"\u1567",u"\u1568",u"\u1569",u"\u156A",u"\u156B",u"\u156C",
        u"\u156D",u"\u156E",u"\u156F",u"\u1570",u"\u1571",u"\u1572",u"\u1573",
        u"\u1574",u"\u1575",u"\u1576",u"\u1577",u"\u1578",u"\u1579",u"\u157A",
        u"\u157B",u"\u157C",u"\u157D",u"\u157E",u"\u157F",u"\u1580",u"\u1581",
        u"\u1582",u"\u1583",u"\u1584",u"\u1585",u"\u1586",u"\u1587",u"\u1588",
        u"\u1589",u"\u158A",u"\u158B",u"\u158C",u"\u158D",u"\u158E",u"\u158F",
        u"\u1590",u"\u1591",u"\u1592",u"\u1593",u"\u1594",u"\u1595",u"\u1596",
        u"\u1597",u"\u1598",u"\u1599",u"\u159A",u"\u159B",u"\u159C",u"\u159D",
        u"\u159E",u"\u159F",u"\u15A0",u"\u15A1",u"\u15A2",u"\u15A3",u"\u15A4",
        u"\u15A5",u"\u15A6",u"\u15A7",u"\u15A8",u"\u15A9",u"\u15AA",u"\u15AB",
        u"\u15AC",u"\u15AD",u"\u15AE",u"\u15AF",u"\u15B0",u"\u15B1",u"\u15B2",
        u"\u15B3",u"\u15B4",u"\u15B5",u"\u15B6",u"\u15B7",u"\u15B8",u"\u15B9",
        u"\u15BA",u"\u15BB",u"\u15BC",u"\u15BD",u"\u15BE",u"\u15BF",u"\u15C0",
        u"\u15C1",u"\u15C2",u"\u15C3",u"\u15C4",u"\u15C5",u"\u15C6",u"\u15C7",
        u"\u15C8",u"\u15C9",u"\u15CA",u"\u15CB",u"\u15CC",u"\u15CD",u"\u15CE",
        u"\u15CF",u"\u15D0",u"\u15D1",u"\u15D2",u"\u15D3",u"\u15D4",u"\u15D5",
        u"\u15D6",u"\u15D7",u"\u15D8",u"\u15D9",u"\u15DA",u"\u15DB",u"\u15DC",
        u"\u15DD",u"\u15DE",u"\u15DF",u"\u15E0",u"\u15E1",u"\u15E2",u"\u15E3",
        u"\u15E4",u"\u15E5",u"\u15E6",u"\u15E7",u"\u15E8",u"\u15E9",u"\u15EA",
        u"\u15EB",u"\u15EC",u"\u15ED",u"\u15EE",u"\u15EF",u"\u15F0",u"\u15F1",
        u"\u15F2",u"\u15F3",u"\u15F4",u"\u15F5",u"\u15F6",u"\u15F7",u"\u15F8",
        u"\u15F9",u"\u15FA",u"\u15FB",u"\u15FC",u"\u15FD",u"\u15FE",u"\u15FF",
        u"\u1600",u"\u1601",u"\u1602",u"\u1603",u"\u1604",u"\u1605",u"\u1606",
        u"\u1607",u"\u1608",u"\u1609",u"\u160A",u"\u160B",u"\u160C",u"\u160D",
        u"\u160E",u"\u160F",u"\u1610",u"\u1611",u"\u1612",u"\u1613",u"\u1614",
        u"\u1615",u"\u1616",u"\u1617",u"\u1618",u"\u1619",u"\u161A",u"\u161B",
        u"\u161C",u"\u161D",u"\u161E",u"\u161F",u"\u1620",u"\u1621",u"\u1622",
        u"\u1623",u"\u1624",u"\u1625",u"\u1626",u"\u1627",u"\u1628",u"\u1629",
        u"\u162A",u"\u162B",u"\u162C",u"\u162D",u"\u162E",u"\u162F",u"\u1630",
        u"\u1631",u"\u1632",u"\u1633",u"\u1634",u"\u1635",u"\u1636",u"\u1637",
        u"\u1638",u"\u1639",u"\u163A",u"\u163B",u"\u163C",u"\u163D",u"\u163E",
        u"\u163F",u"\u1640",u"\u1641",u"\u1642",u"\u1643",u"\u1644",u"\u1645",
        u"\u1646",u"\u1647",u"\u1648",u"\u1649",u"\u164A",u"\u164B",u"\u164C",
        u"\u164D",u"\u164E",u"\u164F",u"\u1650",u"\u1651",u"\u1652",u"\u1653",
        u"\u1654",u"\u1655",u"\u1656",u"\u1657",u"\u1658",u"\u1659",u"\u165A",
        u"\u165B",u"\u165C",u"\u165D",u"\u165E",u"\u165F",u"\u1660",u"\u1661",
        u"\u1662",u"\u1663",u"\u1664",u"\u1665",u"\u1666",u"\u1667",u"\u1668",
        u"\u1669",u"\u166A",u"\u166B",u"\u166C",u"\u166F",u"\u1670",u"\u1671",
        u"\u1672",u"\u1673",u"\u1674",u"\u1675",u"\u1676",u"\u1677",u"\u1678",
        u"\u1679",u"\u167A",u"\u167B",u"\u167C",u"\u167D",u"\u167E",u"\u167F",
        u"\u16A0",u"\u16A2",u"\u16A6",u"\u16A8",u"\u16A9",u"\u16AA",u"\u16AC",
        u"\u16AD",u"\u16B1",u"\u16B4",u"\u16B7",u"\u16B9",u"\u16BA",u"\u16BB",
        u"\u16BC",u"\u16BD",u"\u16BE",u"\u16BF",u"\u16C0",u"\u16C1",u"\u16C3",
        u"\u16C5",u"\u16C6",u"\u16C7",u"\u16C8",u"\u16C9",u"\u16CA",u"\u16CB",
        u"\u16CC",u"\u16CF",u"\u16D0",u"\u16D2",u"\u16D3",u"\u16D4",u"\u16D5",
        u"\u16D6",u"\u16D7",u"\u16D8",u"\u16D9",u"\u16DA",u"\u16DB",u"\u16DE",
        u"\u16DF",u"\u16E6",u"\u16E7",u"\u16E8",u"\u17A3",u"\u17A4",u"\u17A5",
        u"\u17A6",u"\u17A7",u"\u17A8",u"\u17A9",u"\u17AA",u"\u17AB",u"\u17AC",
        u"\u17AD",u"\u17AE",u"\u17AF",u"\u17B0",u"\u17B1",u"\u17B2",u"\u17B3",
        u"\u17D7",u"\u17DC",u"\u1843",u"\u1844",u"\u1845",u"\u1846",u"\u1847",
        u"\u1848",u"\u1849",u"\u184A",u"\u184B",u"\u184C",u"\u184D",u"\u184E",
        u"\u184F",u"\u1850",u"\u1851",u"\u1852",u"\u1853",u"\u1854",u"\u1855",
        u"\u1856",u"\u1857",u"\u1858",u"\u1859",u"\u185A",u"\u185B",u"\u185C",
        u"\u185D",u"\u185E",u"\u185F",u"\u1860",u"\u1861",u"\u1862",u"\u1863",
        u"\u1864",u"\u1865",u"\u1866",u"\u1867",u"\u1868",u"\u1869",u"\u186A",
        u"\u186B",u"\u186C",u"\u186D",u"\u186E",u"\u186F",u"\u1870",u"\u1871",
        u"\u1872",u"\u1873",u"\u1874",u"\u1875",u"\u1876",u"\u1877",u"\u1880",
        u"\u1881",u"\u1882",u"\u1883",u"\u1884",u"\u1885",u"\u1886",u"\u1887",
        u"\u1888",u"\u1889",u"\u188A",u"\u188B",u"\u188C",u"\u188D",u"\u188E",
        u"\u188F",u"\u1890",u"\u1891",u"\u1892",u"\u1893",u"\u1894",u"\u1895",
        u"\u1896",u"\u1897",u"\u1898",u"\u1899",u"\u189A",u"\u189B",u"\u189C",
        u"\u189D",u"\u189E",u"\u189F",u"\u18A0",u"\u18A1",u"\u18A2",u"\u18A3",
        u"\u18A4",u"\u18A5",u"\u18A6",u"\u18A7",u"\u18A8",u"\u18AA",u"\u18B0",
        u"\u18B1",u"\u18B2",u"\u18B3",u"\u18B4",u"\u18B5",u"\u18B6",u"\u18B7",
        u"\u18B8",u"\u18B9",u"\u18BA",u"\u18BB",u"\u18BC",u"\u18BD",u"\u18BE",
        u"\u18BF",u"\u18C0",u"\u18C1",u"\u18C2",u"\u18C3",u"\u18C4",u"\u18C5",
        u"\u18C6",u"\u18C7",u"\u18C8",u"\u18C9",u"\u18CA",u"\u18CB",u"\u18CC",
        u"\u18CD",u"\u18CE",u"\u18CF",u"\u18D0",u"\u18D1",u"\u18D2",u"\u18D3",
        u"\u18D4",u"\u18D5",u"\u18D6",u"\u18D7",u"\u18D8",u"\u18D9",u"\u18DA",
        u"\u18DB",u"\u18DC",u"\u18DD",u"\u18DE",u"\u18DF",u"\u18E0",u"\u18E1",
        u"\u18E2",u"\u18E3",u"\u18E4",u"\u18E5",u"\u18E6",u"\u18E7",u"\u18E8",
        u"\u18E9",u"\u18EA",u"\u18EB",u"\u18EC",u"\u18ED",u"\u18EE",u"\u18EF",
        u"\u18F0",u"\u18F1",u"\u18F2",u"\u18F3",u"\u18F4",u"\u18F5",u"\u1900",
        u"\u1950",u"\u1951",u"\u1952",u"\u1953",u"\u1954",u"\u1955",u"\u1956",
        u"\u1957",u"\u1958",u"\u1959",u"\u195A",u"\u195B",u"\u195C",u"\u195D",
        u"\u195E",u"\u195F",u"\u1960",u"\u1961",u"\u1962",u"\u1963",u"\u1964",
        u"\u1965",u"\u1966",u"\u1967",u"\u1968",u"\u1969",u"\u196A",u"\u196B",
        u"\u196C",u"\u196D",u"\u1970",u"\u1971",u"\u1972",u"\u1973",u"\u1974",
        u"\u1980",u"\u1981",u"\u1982",u"\u1983",u"\u1984",u"\u1985",u"\u1986",
        u"\u1987",u"\u1988",u"\u1989",u"\u198A",u"\u198B",u"\u198C",u"\u198D",
        u"\u198E",u"\u198F",u"\u1990",u"\u1991",u"\u1992",u"\u1993",u"\u1994",
        u"\u1995",u"\u1996",u"\u1997",u"\u1998",u"\u1999",u"\u199A",u"\u199B",
        u"\u199C",u"\u199D",u"\u199E",u"\u199F",u"\u19A0",u"\u19A1",u"\u19A2",
        u"\u19A3",u"\u19A4",u"\u19A5",u"\u19A6",u"\u19A7",u"\u19A8",u"\u19A9",
        u"\u19AA",u"\u19AB",u"\u19C1",u"\u19C2",u"\u19C3",u"\u19C4",u"\u19C5",
        u"\u19C6",u"\u19C7",u"\u1A20",u"\u1A21",u"\u1A22",u"\u1A23",u"\u1A24",
        u"\u1A25",u"\u1A26",u"\u1A27",u"\u1A28",u"\u1A29",u"\u1A2A",u"\u1A2B",
        u"\u1A2C",u"\u1A2D",u"\u1A2E",u"\u1A2F",u"\u1A30",u"\u1A31",u"\u1A32",
        u"\u1A33",u"\u1A34",u"\u1A35",u"\u1A36",u"\u1A37",u"\u1A38",u"\u1A39",
        u"\u1A3A",u"\u1A3B",u"\u1A3C",u"\u1A3D",u"\u1A3E",u"\u1A3F",u"\u1A40",
        u"\u1A41",u"\u1A42",u"\u1A43",u"\u1A44",u"\u1A45",u"\u1A46",u"\u1A47",
        u"\u1A48",u"\u1A49",u"\u1A4A",u"\u1A4B",u"\u1A4C",u"\u1A4D",u"\u1A4E",
        u"\u1A4F",u"\u1A50",u"\u1A51",u"\u1A52",u"\u1A53",u"\u1A54",u"\u1AA7",
        u"\u1B06",u"\u1B08",u"\u1B0A",u"\u1B0B",u"\u1B0C",u"\u1B0D",u"\u1B0E",
        u"\u1B12",u"\u1B14",u"\u1B16",u"\u1B19",u"\u1B1B",u"\u1B1D",u"\u1B1E",
        u"\u1B1F",u"\u1B20",u"\u1B21",u"\u1B23",u"\u1B25",u"\u1B28",u"\u1B2A",
        u"\u1B30",u"\u1B31",u"\u1B45",u"\u1B46",u"\u1B47",u"\u1B48",u"\u1B49",
        u"\u1B4A",u"\u1B4B",u"\u1BC1",u"\u1BC3",u"\u1BC4",u"\u1BC6",u"\u1BC8",
        u"\u1BCA",u"\u1BCC",u"\u1BCD",u"\u1BCF",u"\u1BD3",u"\u1BD5",u"\u1BD6",
        u"\u1BD7",u"\u1BD9",u"\u1BDA",u"\u1BDC",u"\u1BDF",u"\u1C5A",u"\u1C5B",
        u"\u1C5C",u"\u1C5D",u"\u1C5E",u"\u1C5F",u"\u1C60",u"\u1C61",u"\u1C62",
        u"\u1C63",u"\u1C64",u"\u1C65",u"\u1C66",u"\u1C67",u"\u1C68",u"\u1C69",
        u"\u1C6A",u"\u1C6B",u"\u1C6C",u"\u1C6D",u"\u1C6E",u"\u1C6F",u"\u1C70",
        u"\u1C71",u"\u1C72",u"\u1C73",u"\u1C74",u"\u1C75",u"\u1C76",u"\u1C77",
        u"\u1C78",u"\u1C79",u"\u1C7A",u"\u1C7B",u"\u1C7C",u"\u1C7D",u"\u1CE9",
        u"\u1CEA",u"\u1CEB",u"\u1CEC",u"\u1CEE",u"\u1CEF",u"\u1CF0",u"\u1CF1",
        u"\u1D00",u"\u1D01",u"\u1D02",u"\u1D03",u"\u1D04",u"\u1D05",u"\u1D06",
        u"\u1D07",u"\u1D08",u"\u1D09",u"\u1D0A",u"\u1D0B",u"\u1D0C",u"\u1D0D",
        u"\u1D0E",u"\u1D0F",u"\u1D10",u"\u1D11",u"\u1D12",u"\u1D13",u"\u1D14",
        u"\u1D15",u"\u1D16",u"\u1D17",u"\u1D18",u"\u1D19",u"\u1D1A",u"\u1D1B",
        u"\u1D1C",u"\u1D1D",u"\u1D1E",u"\u1D1F",u"\u1D20",u"\u1D21",u"\u1D22",
        u"\u1D23",u"\u1D24",u"\u1D25",u"\u1D26",u"\u1D27",u"\u1D28",u"\u1D29",
        u"\u1D2A",u"\u1D2B",u"\u1D2C",u"\u1D2D",u"\u1D2E",u"\u1D2F",u"\u1D30",
        u"\u1D31",u"\u1D32",u"\u1D33",u"\u1D34",u"\u1D35",u"\u1D36",u"\u1D37",
        u"\u1D38",u"\u1D39",u"\u1D3A",u"\u1D3B",u"\u1D3C",u"\u1D3D",u"\u1D3E",
        u"\u1D3F",u"\u1D40",u"\u1D41",u"\u1D42",u"\u1D43",u"\u1D44",u"\u1D45",
        u"\u1D46",u"\u1D47",u"\u1D48",u"\u1D49",u"\u1D4A",u"\u1D4B",u"\u1D4C",
        u"\u1D4D",u"\u1D4E",u"\u1D4F",u"\u1D50",u"\u1D51",u"\u1D52",u"\u1D53",
        u"\u1D54",u"\u1D55",u"\u1D56",u"\u1D57",u"\u1D58",u"\u1D59",u"\u1D5A",
        u"\u1D5B",u"\u1D5C",u"\u1D5D",u"\u1D5E",u"\u1D5F",u"\u1D60",u"\u1D61",
        u"\u1D62",u"\u1D63",u"\u1D64",u"\u1D65",u"\u1D66",u"\u1D67",u"\u1D68",
        u"\u1D69",u"\u1D6A",u"\u1D6B",u"\u1D6C",u"\u1D6D",u"\u1D6E",u"\u1D6F",
        u"\u1D70",u"\u1D71",u"\u1D72",u"\u1D73",u"\u1D74",u"\u1D75",u"\u1D76",
        u"\u1D77",u"\u1D78",u"\u1D79",u"\u1D7A",u"\u1D7B",u"\u1D7C",u"\u1D7D",
        u"\u1D7E",u"\u1D7F",u"\u1D80",u"\u1D81",u"\u1D82",u"\u1D83",u"\u1D84",
        u"\u1D85",u"\u1D86",u"\u1D87",u"\u1D88",u"\u1D89",u"\u1D8A",u"\u1D8B",
        u"\u1D8C",u"\u1D8D",u"\u1D8E",u"\u1D8F",u"\u1D90",u"\u1D91",u"\u1D92",
        u"\u1D93",u"\u1D94",u"\u1D95",u"\u1D96",u"\u1D97",u"\u1D98",u"\u1D99",
        u"\u1D9A",u"\u1D9B",u"\u1D9C",u"\u1D9D",u"\u1D9E",u"\u1D9F",u"\u1DA0",
        u"\u1DA1",u"\u1DA2",u"\u1DA3",u"\u1DA4",u"\u1DA5",u"\u1DA6",u"\u1DA7",
        u"\u1DA8",u"\u1DA9",u"\u1DAA",u"\u1DAB",u"\u1DAC",u"\u1DAD",u"\u1DAE",
        u"\u1DAF",u"\u1DB0",u"\u1DB1",u"\u1DB2",u"\u1DB3",u"\u1DB4",u"\u1DB5",
        u"\u1DB6",u"\u1DB7",u"\u1DB8",u"\u1DB9",u"\u1DBA",u"\u1DBB",u"\u1DBC",
        u"\u1DBD",u"\u1DBE",u"\u1DBF",u"\u1E01",u"\u1E03",u"\u1E05",u"\u1E07",
        u"\u1E09",u"\u1E0B",u"\u1E0D",u"\u1E0F",u"\u1E11",u"\u1E13",u"\u1E15",
        u"\u1E17",u"\u1E19",u"\u1E1B",u"\u1E1D",u"\u1E1F",u"\u1E21",u"\u1E23",
        u"\u1E25",u"\u1E27",u"\u1E29",u"\u1E2B",u"\u1E2D",u"\u1E2F",u"\u1E31",
        u"\u1E33",u"\u1E35",u"\u1E37",u"\u1E39",u"\u1E3B",u"\u1E3D",u"\u1E3F",
        u"\u1E41",u"\u1E43",u"\u1E45",u"\u1E47",u"\u1E49",u"\u1E4B",u"\u1E4D",
        u"\u1E4F",u"\u1E51",u"\u1E53",u"\u1E55",u"\u1E57",u"\u1E59",u"\u1E5B",
        u"\u1E5D",u"\u1E5F",u"\u1E61",u"\u1E63",u"\u1E65",u"\u1E67",u"\u1E69",
        u"\u1E6B",u"\u1E6D",u"\u1E6F",u"\u1E71",u"\u1E73",u"\u1E75",u"\u1E77",
        u"\u1E79",u"\u1E7B",u"\u1E7D",u"\u1E7F",u"\u1E81",u"\u1E83",u"\u1E85",
        u"\u1E87",u"\u1E89",u"\u1E8B",u"\u1E8D",u"\u1E8F",u"\u1E91",u"\u1E93",
        u"\u1E95",u"\u1E96",u"\u1E97",u"\u1E98",u"\u1E99",u"\u1E9A",u"\u1E9B",
        u"\u1E9C",u"\u1E9D",u"\u1E9F",u"\u1EA1",u"\u1EA3",u"\u1EA5",u"\u1EA7",
        u"\u1EA9",u"\u1EAB",u"\u1EAD",u"\u1EAF",u"\u1EB1",u"\u1EB3",u"\u1EB5",
        u"\u1EB7",u"\u1EB9",u"\u1EBB",u"\u1EBD",u"\u1EBF",u"\u1EC1",u"\u1EC3",
        u"\u1EC5",u"\u1EC7",u"\u1EC9",u"\u1ECB",u"\u1ECD",u"\u1ECF",u"\u1ED1",
        u"\u1ED3",u"\u1ED5",u"\u1ED7",u"\u1ED9",u"\u1EDB",u"\u1EDD",u"\u1EDF",
        u"\u1EE1",u"\u1EE3",u"\u1EE5",u"\u1EE7",u"\u1EE9",u"\u1EEB",u"\u1EED",
        u"\u1EEF",u"\u1EF1",u"\u1EF3",u"\u1EF5",u"\u1EF7",u"\u1EF9",u"\u1EFB",
        u"\u1EFD",u"\u1EFF",u"\u1F00",u"\u1F01",u"\u1F02",u"\u1F03",u"\u1F04",
        u"\u1F05",u"\u1F06",u"\u1F07",u"\u1F10",u"\u1F11",u"\u1F12",u"\u1F13",
        u"\u1F14",u"\u1F15",u"\u1F20",u"\u1F21",u"\u1F22",u"\u1F23",u"\u1F24",
        u"\u1F25",u"\u1F26",u"\u1F27",u"\u1F30",u"\u1F31",u"\u1F32",u"\u1F33",
        u"\u1F34",u"\u1F35",u"\u1F36",u"\u1F37",u"\u1F40",u"\u1F41",u"\u1F42",
        u"\u1F43",u"\u1F44",u"\u1F45",u"\u1F50",u"\u1F51",u"\u1F52",u"\u1F53",
        u"\u1F54",u"\u1F55",u"\u1F56",u"\u1F57",u"\u1F60",u"\u1F61",u"\u1F62",
        u"\u1F63",u"\u1F64",u"\u1F65",u"\u1F66",u"\u1F67",u"\u1F70",u"\u1F71",
        u"\u1F72",u"\u1F73",u"\u1F74",u"\u1F75",u"\u1F76",u"\u1F77",u"\u1F78",
        u"\u1F79",u"\u1F7A",u"\u1F7B",u"\u1F7C",u"\u1F7D",u"\u1F80",u"\u1F81",
        u"\u1F82",u"\u1F83",u"\u1F84",u"\u1F85",u"\u1F86",u"\u1F87",u"\u1F90",
        u"\u1F91",u"\u1F92",u"\u1F93",u"\u1F94",u"\u1F95",u"\u1F96",u"\u1F97",
        u"\u1FA0",u"\u1FA1",u"\u1FA2",u"\u1FA3",u"\u1FA4",u"\u1FA5",u"\u1FA6",
        u"\u1FA7",u"\u1FB0",u"\u1FB1",u"\u1FB2",u"\u1FB3",u"\u1FB4",u"\u1FB6",
        u"\u1FB7",u"\u1FBE",u"\u1FC2",u"\u1FC3",u"\u1FC4",u"\u1FC6",u"\u1FC7",
        u"\u1FD0",u"\u1FD1",u"\u1FD2",u"\u1FD3",u"\u1FD6",u"\u1FD7",u"\u1FE0",
        u"\u1FE1",u"\u1FE2",u"\u1FE3",u"\u1FE4",u"\u1FE5",u"\u1FE6",u"\u1FE7",
        u"\u1FF2",u"\u1FF3",u"\u1FF4",u"\u1FF6",u"\u1FF7",u"\u2071",u"\u207F",
        u"\u2090",u"\u2091",u"\u2092",u"\u2093",u"\u2094",u"\u2095",u"\u2096",
        u"\u2097",u"\u2098",u"\u2099",u"\u209A",u"\u209B",u"\u209C",u"\u210A",
        u"\u210E",u"\u210F",u"\u2113",u"\u212F",u"\u2134",u"\u2135",u"\u2136",
        u"\u2137",u"\u2138",u"\u2139",u"\u213C",u"\u213D",u"\u2146",u"\u2147",
        u"\u2148",u"\u2149",u"\u214E",u"\u2184",u"\u2C3A",u"\u2C52",u"\u2C54",
        u"\u2C55",u"\u2C57",u"\u2C58",u"\u2C59",u"\u2C5D",u"\u2C5E",u"\u2C61",
        u"\u2C65",u"\u2C66",u"\u2C68",u"\u2C6A",u"\u2C6C",u"\u2C71",u"\u2C73",
        u"\u2C74",u"\u2C76",u"\u2C77",u"\u2C78",u"\u2C79",u"\u2C7A",u"\u2C7B",
        u"\u2C7C",u"\u2C7D",u"\u2CB3",u"\u2CB5",u"\u2CB7",u"\u2CB9",u"\u2CBB",
        u"\u2CBD",u"\u2CBF",u"\u2CC3",u"\u2CC5",u"\u2CC7",u"\u2CC9",u"\u2CCB",
        u"\u2CCD",u"\u2CCF",u"\u2CD1",u"\u2CD3",u"\u2CD5",u"\u2CD7",u"\u2CD9",
        u"\u2CDB",u"\u2CDD",u"\u2CDF",u"\u2CE1",u"\u2CE3",u"\u2CE4",u"\u2CEC",
        u"\u2CEE",u"\u2D00",u"\u2D01",u"\u2D02",u"\u2D03",u"\u2D04",u"\u2D05",
        u"\u2D06",u"\u2D07",u"\u2D08",u"\u2D09",u"\u2D0A",u"\u2D0B",u"\u2D0C",
        u"\u2D0D",u"\u2D0E",u"\u2D0F",u"\u2D10",u"\u2D11",u"\u2D12",u"\u2D13",
        u"\u2D14",u"\u2D15",u"\u2D16",u"\u2D17",u"\u2D18",u"\u2D19",u"\u2D1A",
        u"\u2D1B",u"\u2D1C",u"\u2D1D",u"\u2D1E",u"\u2D1F",u"\u2D20",u"\u2D21",
        u"\u2D22",u"\u2D23",u"\u2D24",u"\u2D25",u"\u2D35",u"\u2D3E",u"\u2D41",
        u"\u2D42",u"\u2D46",u"\u2D48",u"\u2D4B",u"\u2D4C",u"\u2D50",u"\u2D51",
        u"\u2D57",u"\u2D58",u"\u2D64",u"\u2D6F",u"\u2D80",u"\u2D81",u"\u2D82",
        u"\u2D83",u"\u2D84",u"\u2D85",u"\u2D86",u"\u2D87",u"\u2D88",u"\u2D89",
        u"\u2D8A",u"\u2D8B",u"\u2D8C",u"\u2D8D",u"\u2D8E",u"\u2D8F",u"\u2D90",
        u"\u2D91",u"\u2D92",u"\u2D93",u"\u2D94",u"\u2D95",u"\u2D96",u"\u2DA0",
        u"\u2DA1",u"\u2DA2",u"\u2DA3",u"\u2DA4",u"\u2DA5",u"\u2DA6",u"\u2DA8",
        u"\u2DA9",u"\u2DAA",u"\u2DAB",u"\u2DAC",u"\u2DAD",u"\u2DAE",u"\u2DB0",
        u"\u2DB1",u"\u2DB2",u"\u2DB3",u"\u2DB4",u"\u2DB5",u"\u2DB6",u"\u2DB8",
        u"\u2DB9",u"\u2DBA",u"\u2DBB",u"\u2DBC",u"\u2DBD",u"\u2DBE",u"\u2DC0",
        u"\u2DC1",u"\u2DC2",u"\u2DC3",u"\u2DC4",u"\u2DC5",u"\u2DC6",u"\u2DC8",
        u"\u2DC9",u"\u2DCA",u"\u2DCB",u"\u2DCC",u"\u2DCD",u"\u2DCE",u"\u2DD0",
        u"\u2DD1",u"\u2DD2",u"\u2DD3",u"\u2DD4",u"\u2DD5",u"\u2DD6",u"\u2DD8",
        u"\u2DD9",u"\u2DDA",u"\u2DDB",u"\u2DDC",u"\u2DDD",u"\u2DDE",u"\u2E2F",
        u"\u3005",u"\u3006",u"\u3031",u"\u3032",u"\u3033",u"\u3034",u"\u3035",
        u"\u303B",u"\u303C",u"\u3041",u"\u3043",u"\u3045",u"\u3047",u"\u3049",
        u"\u3063",u"\u3083",u"\u3085",u"\u3087",u"\u308E",u"\u3095",u"\u3096",
        u"\u309D",u"\u309E",u"\u309F",u"\u30A1",u"\u30A3",u"\u30A5",u"\u30A7",
        u"\u30A9",u"\u30C3",u"\u30E3",u"\u30E5",u"\u30E7",u"\u30EE",u"\u30F5",
        u"\u30F6",u"\u30FC",u"\u30FD",u"\u30FE",u"\u30FF",u"\u3131",u"\u3132",
        u"\u3133",u"\u3134",u"\u3135",u"\u3136",u"\u3137",u"\u3138",u"\u3139",
        u"\u313A",u"\u313B",u"\u313C",u"\u313D",u"\u313E",u"\u313F",u"\u3140",
        u"\u3141",u"\u3142",u"\u3143",u"\u3144",u"\u3145",u"\u3146",u"\u3147",
        u"\u3148",u"\u3149",u"\u314A",u"\u314B",u"\u314C",u"\u314D",u"\u314E",
        u"\u314F",u"\u3150",u"\u3151",u"\u3152",u"\u3153",u"\u3154",u"\u3155",
        u"\u3156",u"\u3157",u"\u3158",u"\u3159",u"\u315A",u"\u315B",u"\u315C",
        u"\u315D",u"\u315E",u"\u315F",u"\u3160",u"\u3161",u"\u3162",u"\u3163",
        u"\u3164",u"\u3165",u"\u3166",u"\u3167",u"\u3168",u"\u3169",u"\u316A",
        u"\u316B",u"\u316C",u"\u316D",u"\u316E",u"\u316F",u"\u3170",u"\u3171",
        u"\u3172",u"\u3173",u"\u3174",u"\u3175",u"\u3176",u"\u3177",u"\u3178",
        u"\u3179",u"\u317A",u"\u317B",u"\u317C",u"\u317D",u"\u317E",u"\u317F",
        u"\u3180",u"\u3181",u"\u3182",u"\u3183",u"\u3184",u"\u3185",u"\u3186",
        u"\u3187",u"\u3188",u"\u3189",u"\u318A",u"\u318B",u"\u318C",u"\u318D",
        u"\u318E",u"\u31B4",u"\u31B5",u"\u31B6",u"\u31B7",u"\u31F0",u"\u31F1",
        u"\u31F2",u"\u31F3",u"\u31F4",u"\u31F5",u"\u31F6",u"\u31F7",u"\u31F8",
        u"\u31F9",u"\u31FA",u"\u31FB",u"\u31FC",u"\u31FD",u"\u31FE",u"\u31FF",
        u"\u3400",u"\u4DB5",u"\u4E00",u"\u9FCB",u"\uA000",u"\uA001",u"\uA002",
        u"\uA003",u"\uA004",u"\uA005",u"\uA006",u"\uA007",u"\uA008",u"\uA009",
        u"\uA00A",u"\uA00B",u"\uA00C",u"\uA00D",u"\uA00E",u"\uA00F",u"\uA010",
        u"\uA011",u"\uA012",u"\uA013",u"\uA014",u"\uA015",u"\uA016",u"\uA017",
        u"\uA018",u"\uA019",u"\uA01A",u"\uA01B",u"\uA01C",u"\uA01D",u"\uA01E",
        u"\uA01F",u"\uA020",u"\uA021",u"\uA022",u"\uA023",u"\uA024",u"\uA025",
        u"\uA026",u"\uA027",u"\uA028",u"\uA029",u"\uA02A",u"\uA02B",u"\uA02C",
        u"\uA02D",u"\uA02E",u"\uA02F",u"\uA030",u"\uA031",u"\uA032",u"\uA033",
        u"\uA034",u"\uA035",u"\uA036",u"\uA037",u"\uA038",u"\uA039",u"\uA03A",
        u"\uA03B",u"\uA03C",u"\uA03D",u"\uA03E",u"\uA03F",u"\uA040",u"\uA041",
        u"\uA042",u"\uA043",u"\uA044",u"\uA045",u"\uA046",u"\uA047",u"\uA048",
        u"\uA049",u"\uA04A",u"\uA04B",u"\uA04C",u"\uA04D",u"\uA04E",u"\uA04F",
        u"\uA050",u"\uA051",u"\uA052",u"\uA053",u"\uA054",u"\uA055",u"\uA056",
        u"\uA057",u"\uA058",u"\uA059",u"\uA05A",u"\uA05B",u"\uA05C",u"\uA05D",
        u"\uA05E",u"\uA05F",u"\uA060",u"\uA061",u"\uA062",u"\uA063",u"\uA064",
        u"\uA065",u"\uA066",u"\uA067",u"\uA068",u"\uA069",u"\uA06A",u"\uA06B",
        u"\uA06C",u"\uA06D",u"\uA06E",u"\uA06F",u"\uA070",u"\uA071",u"\uA072",
        u"\uA073",u"\uA074",u"\uA075",u"\uA076",u"\uA077",u"\uA078",u"\uA079",
        u"\uA07A",u"\uA07B",u"\uA07C",u"\uA07D",u"\uA07E",u"\uA07F",u"\uA080",
        u"\uA081",u"\uA082",u"\uA083",u"\uA084",u"\uA085",u"\uA086",u"\uA087",
        u"\uA088",u"\uA089",u"\uA08A",u"\uA08B",u"\uA08C",u"\uA08D",u"\uA08E",
        u"\uA08F",u"\uA090",u"\uA091",u"\uA092",u"\uA093",u"\uA094",u"\uA095",
        u"\uA096",u"\uA097",u"\uA098",u"\uA099",u"\uA09A",u"\uA09B",u"\uA09C",
        u"\uA09D",u"\uA09E",u"\uA09F",u"\uA0A0",u"\uA0A1",u"\uA0A2",u"\uA0A3",
        u"\uA0A4",u"\uA0A5",u"\uA0A6",u"\uA0A7",u"\uA0A8",u"\uA0A9",u"\uA0AA",
        u"\uA0AB",u"\uA0AC",u"\uA0AD",u"\uA0AE",u"\uA0AF",u"\uA0B0",u"\uA0B1",
        u"\uA0B2",u"\uA0B3",u"\uA0B4",u"\uA0B5",u"\uA0B6",u"\uA0B7",u"\uA0B8",
        u"\uA0B9",u"\uA0BA",u"\uA0BB",u"\uA0BC",u"\uA0BD",u"\uA0BE",u"\uA0BF",
        u"\uA0C0",u"\uA0C1",u"\uA0C2",u"\uA0C3",u"\uA0C4",u"\uA0C5",u"\uA0C6",
        u"\uA0C7",u"\uA0C8",u"\uA0C9",u"\uA0CA",u"\uA0CB",u"\uA0CC",u"\uA0CD",
        u"\uA0CE",u"\uA0CF",u"\uA0D0",u"\uA0D1",u"\uA0D2",u"\uA0D3",u"\uA0D4",
        u"\uA0D5",u"\uA0D6",u"\uA0D7",u"\uA0D8",u"\uA0D9",u"\uA0DA",u"\uA0DB",
        u"\uA0DC",u"\uA0DD",u"\uA0DE",u"\uA0DF",u"\uA0E0",u"\uA0E1",u"\uA0E2",
        u"\uA0E3",u"\uA0E4",u"\uA0E5",u"\uA0E6",u"\uA0E7",u"\uA0E8",u"\uA0E9",
        u"\uA0EA",u"\uA0EB",u"\uA0EC",u"\uA0ED",u"\uA0EE",u"\uA0EF",u"\uA0F0",
        u"\uA0F1",u"\uA0F2",u"\uA0F3",u"\uA0F4",u"\uA0F5",u"\uA0F6",u"\uA0F7",
        u"\uA0F8",u"\uA0F9",u"\uA0FA",u"\uA0FB",u"\uA0FC",u"\uA0FD",u"\uA0FE",
        u"\uA0FF",u"\uA100",u"\uA101",u"\uA102",u"\uA103",u"\uA104",u"\uA105",
        u"\uA106",u"\uA107",u"\uA108",u"\uA109",u"\uA10A",u"\uA10B",u"\uA10C",
        u"\uA10D",u"\uA10E",u"\uA10F",u"\uA110",u"\uA111",u"\uA112",u"\uA113",
        u"\uA114",u"\uA115",u"\uA116",u"\uA117",u"\uA118",u"\uA119",u"\uA11A",
        u"\uA11B",u"\uA11C",u"\uA11D",u"\uA11E",u"\uA11F",u"\uA120",u"\uA121",
        u"\uA122",u"\uA123",u"\uA124",u"\uA125",u"\uA126",u"\uA127",u"\uA128",
        u"\uA129",u"\uA12A",u"\uA12B",u"\uA12C",u"\uA12D",u"\uA12E",u"\uA12F",
        u"\uA130",u"\uA131",u"\uA132",u"\uA133",u"\uA134",u"\uA135",u"\uA136",
        u"\uA137",u"\uA138",u"\uA139",u"\uA13A",u"\uA13B",u"\uA13C",u"\uA13D",
        u"\uA13E",u"\uA13F",u"\uA140",u"\uA141",u"\uA142",u"\uA143",u"\uA144",
        u"\uA145",u"\uA146",u"\uA147",u"\uA148",u"\uA149",u"\uA14A",u"\uA14B",
        u"\uA14C",u"\uA14D",u"\uA14E",u"\uA14F",u"\uA150",u"\uA151",u"\uA152",
        u"\uA153",u"\uA154",u"\uA155",u"\uA156",u"\uA157",u"\uA158",u"\uA159",
        u"\uA15A",u"\uA15B",u"\uA15C",u"\uA15D",u"\uA15E",u"\uA15F",u"\uA160",
        u"\uA161",u"\uA162",u"\uA163",u"\uA164",u"\uA165",u"\uA166",u"\uA167",
        u"\uA168",u"\uA169",u"\uA16A",u"\uA16B",u"\uA16C",u"\uA16D",u"\uA16E",
        u"\uA16F",u"\uA170",u"\uA171",u"\uA172",u"\uA173",u"\uA174",u"\uA175",
        u"\uA176",u"\uA177",u"\uA178",u"\uA179",u"\uA17A",u"\uA17B",u"\uA17C",
        u"\uA17D",u"\uA17E",u"\uA17F",u"\uA180",u"\uA181",u"\uA182",u"\uA183",
        u"\uA184",u"\uA185",u"\uA186",u"\uA187",u"\uA188",u"\uA189",u"\uA18A",
        u"\uA18B",u"\uA18C",u"\uA18D",u"\uA18E",u"\uA18F",u"\uA190",u"\uA191",
        u"\uA192",u"\uA193",u"\uA194",u"\uA195",u"\uA196",u"\uA197",u"\uA198",
        u"\uA199",u"\uA19A",u"\uA19B",u"\uA19C",u"\uA19D",u"\uA19E",u"\uA19F",
        u"\uA1A0",u"\uA1A1",u"\uA1A2",u"\uA1A3",u"\uA1A4",u"\uA1A5",u"\uA1A6",
        u"\uA1A7",u"\uA1A8",u"\uA1A9",u"\uA1AA",u"\uA1AB",u"\uA1AC",u"\uA1AD",
        u"\uA1AE",u"\uA1AF",u"\uA1B0",u"\uA1B1",u"\uA1B2",u"\uA1B3",u"\uA1B4",
        u"\uA1B5",u"\uA1B6",u"\uA1B7",u"\uA1B8",u"\uA1B9",u"\uA1BA",u"\uA1BB",
        u"\uA1BC",u"\uA1BD",u"\uA1BE",u"\uA1BF",u"\uA1C0",u"\uA1C1",u"\uA1C2",
        u"\uA1C3",u"\uA1C4",u"\uA1C5",u"\uA1C6",u"\uA1C7",u"\uA1C8",u"\uA1C9",
        u"\uA1CA",u"\uA1CB",u"\uA1CC",u"\uA1CD",u"\uA1CE",u"\uA1CF",u"\uA1D0",
        u"\uA1D1",u"\uA1D2",u"\uA1D3",u"\uA1D4",u"\uA1D5",u"\uA1D6",u"\uA1D7",
        u"\uA1D8",u"\uA1D9",u"\uA1DA",u"\uA1DB",u"\uA1DC",u"\uA1DD",u"\uA1DE",
        u"\uA1DF",u"\uA1E0",u"\uA1E1",u"\uA1E2",u"\uA1E3",u"\uA1E4",u"\uA1E5",
        u"\uA1E6",u"\uA1E7",u"\uA1E8",u"\uA1E9",u"\uA1EA",u"\uA1EB",u"\uA1EC",
        u"\uA1ED",u"\uA1EE",u"\uA1EF",u"\uA1F0",u"\uA1F1",u"\uA1F2",u"\uA1F3",
        u"\uA1F4",u"\uA1F5",u"\uA1F6",u"\uA1F7",u"\uA1F8",u"\uA1F9",u"\uA1FA",
        u"\uA1FB",u"\uA1FC",u"\uA1FD",u"\uA1FE",u"\uA1FF",u"\uA200",u"\uA201",
        u"\uA202",u"\uA203",u"\uA204",u"\uA205",u"\uA206",u"\uA207",u"\uA208",
        u"\uA209",u"\uA20A",u"\uA20B",u"\uA20C",u"\uA20D",u"\uA20E",u"\uA20F",
        u"\uA210",u"\uA211",u"\uA212",u"\uA213",u"\uA214",u"\uA215",u"\uA216",
        u"\uA217",u"\uA218",u"\uA219",u"\uA21A",u"\uA21B",u"\uA21C",u"\uA21D",
        u"\uA21E",u"\uA21F",u"\uA220",u"\uA221",u"\uA222",u"\uA223",u"\uA224",
        u"\uA225",u"\uA226",u"\uA227",u"\uA228",u"\uA229",u"\uA22A",u"\uA22B",
        u"\uA22C",u"\uA22D",u"\uA22E",u"\uA22F",u"\uA230",u"\uA231",u"\uA232",
        u"\uA233",u"\uA234",u"\uA235",u"\uA236",u"\uA237",u"\uA238",u"\uA239",
        u"\uA23A",u"\uA23B",u"\uA23C",u"\uA23D",u"\uA23E",u"\uA23F",u"\uA240",
        u"\uA241",u"\uA242",u"\uA243",u"\uA244",u"\uA245",u"\uA246",u"\uA247",
        u"\uA248",u"\uA249",u"\uA24A",u"\uA24B",u"\uA24C",u"\uA24D",u"\uA24E",
        u"\uA24F",u"\uA250",u"\uA251",u"\uA252",u"\uA253",u"\uA254",u"\uA255",
        u"\uA256",u"\uA257",u"\uA258",u"\uA259",u"\uA25A",u"\uA25B",u"\uA25C",
        u"\uA25D",u"\uA25E",u"\uA25F",u"\uA260",u"\uA261",u"\uA262",u"\uA263",
        u"\uA264",u"\uA265",u"\uA266",u"\uA267",u"\uA268",u"\uA269",u"\uA26A",
        u"\uA26B",u"\uA26C",u"\uA26D",u"\uA26E",u"\uA26F",u"\uA270",u"\uA271",
        u"\uA272",u"\uA273",u"\uA274",u"\uA275",u"\uA276",u"\uA277",u"\uA278",
        u"\uA279",u"\uA27A",u"\uA27B",u"\uA27C",u"\uA27D",u"\uA27E",u"\uA27F",
        u"\uA280",u"\uA281",u"\uA282",u"\uA283",u"\uA284",u"\uA285",u"\uA286",
        u"\uA287",u"\uA288",u"\uA289",u"\uA28A",u"\uA28B",u"\uA28C",u"\uA28D",
        u"\uA28E",u"\uA28F",u"\uA290",u"\uA291",u"\uA292",u"\uA293",u"\uA294",
        u"\uA295",u"\uA296",u"\uA297",u"\uA298",u"\uA299",u"\uA29A",u"\uA29B",
        u"\uA29C",u"\uA29D",u"\uA29E",u"\uA29F",u"\uA2A0",u"\uA2A1",u"\uA2A2",
        u"\uA2A3",u"\uA2A4",u"\uA2A5",u"\uA2A6",u"\uA2A7",u"\uA2A8",u"\uA2A9",
        u"\uA2AA",u"\uA2AB",u"\uA2AC",u"\uA2AD",u"\uA2AE",u"\uA2AF",u"\uA2B0",
        u"\uA2B1",u"\uA2B2",u"\uA2B3",u"\uA2B4",u"\uA2B5",u"\uA2B6",u"\uA2B7",
        u"\uA2B8",u"\uA2B9",u"\uA2BA",u"\uA2BB",u"\uA2BC",u"\uA2BD",u"\uA2BE",
        u"\uA2BF",u"\uA2C0",u"\uA2C1",u"\uA2C2",u"\uA2C3",u"\uA2C4",u"\uA2C5",
        u"\uA2C6",u"\uA2C7",u"\uA2C8",u"\uA2C9",u"\uA2CA",u"\uA2CB",u"\uA2CC",
        u"\uA2CD",u"\uA2CE",u"\uA2CF",u"\uA2D0",u"\uA2D1",u"\uA2D2",u"\uA2D3",
        u"\uA2D4",u"\uA2D5",u"\uA2D6",u"\uA2D7",u"\uA2D8",u"\uA2D9",u"\uA2DA",
        u"\uA2DB",u"\uA2DC",u"\uA2DD",u"\uA2DE",u"\uA2DF",u"\uA2E0",u"\uA2E1",
        u"\uA2E2",u"\uA2E3",u"\uA2E4",u"\uA2E5",u"\uA2E6",u"\uA2E7",u"\uA2E8",
        u"\uA2E9",u"\uA2EA",u"\uA2EB",u"\uA2EC",u"\uA2ED",u"\uA2EE",u"\uA2EF",
        u"\uA2F0",u"\uA2F1",u"\uA2F2",u"\uA2F3",u"\uA2F4",u"\uA2F5",u"\uA2F6",
        u"\uA2F7",u"\uA2F8",u"\uA2F9",u"\uA2FA",u"\uA2FB",u"\uA2FC",u"\uA2FD",
        u"\uA2FE",u"\uA2FF",u"\uA300",u"\uA301",u"\uA302",u"\uA303",u"\uA304",
        u"\uA305",u"\uA306",u"\uA307",u"\uA308",u"\uA309",u"\uA30A",u"\uA30B",
        u"\uA30C",u"\uA30D",u"\uA30E",u"\uA30F",u"\uA310",u"\uA311",u"\uA312",
        u"\uA313",u"\uA314",u"\uA315",u"\uA316",u"\uA317",u"\uA318",u"\uA319",
        u"\uA31A",u"\uA31B",u"\uA31C",u"\uA31D",u"\uA31E",u"\uA31F",u"\uA320",
        u"\uA321",u"\uA322",u"\uA323",u"\uA324",u"\uA325",u"\uA326",u"\uA327",
        u"\uA328",u"\uA329",u"\uA32A",u"\uA32B",u"\uA32C",u"\uA32D",u"\uA32E",
        u"\uA32F",u"\uA330",u"\uA331",u"\uA332",u"\uA333",u"\uA334",u"\uA335",
        u"\uA336",u"\uA337",u"\uA338",u"\uA339",u"\uA33A",u"\uA33B",u"\uA33C",
        u"\uA33D",u"\uA33E",u"\uA33F",u"\uA340",u"\uA341",u"\uA342",u"\uA343",
        u"\uA344",u"\uA345",u"\uA346",u"\uA347",u"\uA348",u"\uA349",u"\uA34A",
        u"\uA34B",u"\uA34C",u"\uA34D",u"\uA34E",u"\uA34F",u"\uA350",u"\uA351",
        u"\uA352",u"\uA353",u"\uA354",u"\uA355",u"\uA356",u"\uA357",u"\uA358",
        u"\uA359",u"\uA35A",u"\uA35B",u"\uA35C",u"\uA35D",u"\uA35E",u"\uA35F",
        u"\uA360",u"\uA361",u"\uA362",u"\uA363",u"\uA364",u"\uA365",u"\uA366",
        u"\uA367",u"\uA368",u"\uA369",u"\uA36A",u"\uA36B",u"\uA36C",u"\uA36D",
        u"\uA36E",u"\uA36F",u"\uA370",u"\uA371",u"\uA372",u"\uA373",u"\uA374",
        u"\uA375",u"\uA376",u"\uA377",u"\uA378",u"\uA379",u"\uA37A",u"\uA37B",
        u"\uA37C",u"\uA37D",u"\uA37E",u"\uA37F",u"\uA380",u"\uA381",u"\uA382",
        u"\uA383",u"\uA384",u"\uA385",u"\uA386",u"\uA387",u"\uA388",u"\uA389",
        u"\uA38A",u"\uA38B",u"\uA38C",u"\uA38D",u"\uA38E",u"\uA38F",u"\uA390",
        u"\uA391",u"\uA392",u"\uA393",u"\uA394",u"\uA395",u"\uA396",u"\uA397",
        u"\uA398",u"\uA399",u"\uA39A",u"\uA39B",u"\uA39C",u"\uA39D",u"\uA39E",
        u"\uA39F",u"\uA3A0",u"\uA3A1",u"\uA3A2",u"\uA3A3",u"\uA3A4",u"\uA3A5",
        u"\uA3A6",u"\uA3A7",u"\uA3A8",u"\uA3A9",u"\uA3AA",u"\uA3AB",u"\uA3AC",
        u"\uA3AD",u"\uA3AE",u"\uA3AF",u"\uA3B0",u"\uA3B1",u"\uA3B2",u"\uA3B3",
        u"\uA3B4",u"\uA3B5",u"\uA3B6",u"\uA3B7",u"\uA3B8",u"\uA3B9",u"\uA3BA",
        u"\uA3BB",u"\uA3BC",u"\uA3BD",u"\uA3BE",u"\uA3BF",u"\uA3C0",u"\uA3C1",
        u"\uA3C2",u"\uA3C3",u"\uA3C4",u"\uA3C5",u"\uA3C6",u"\uA3C7",u"\uA3C8",
        u"\uA3C9",u"\uA3CA",u"\uA3CB",u"\uA3CC",u"\uA3CD",u"\uA3CE",u"\uA3CF",
        u"\uA3D0",u"\uA3D1",u"\uA3D2",u"\uA3D3",u"\uA3D4",u"\uA3D5",u"\uA3D6",
        u"\uA3D7",u"\uA3D8",u"\uA3D9",u"\uA3DA",u"\uA3DB",u"\uA3DC",u"\uA3DD",
        u"\uA3DE",u"\uA3DF",u"\uA3E0",u"\uA3E1",u"\uA3E2",u"\uA3E3",u"\uA3E4",
        u"\uA3E5",u"\uA3E6",u"\uA3E7",u"\uA3E8",u"\uA3E9",u"\uA3EA",u"\uA3EB",
        u"\uA3EC",u"\uA3ED",u"\uA3EE",u"\uA3EF",u"\uA3F0",u"\uA3F1",u"\uA3F2",
        u"\uA3F3",u"\uA3F4",u"\uA3F5",u"\uA3F6",u"\uA3F7",u"\uA3F8",u"\uA3F9",
        u"\uA3FA",u"\uA3FB",u"\uA3FC",u"\uA3FD",u"\uA3FE",u"\uA3FF",u"\uA400",
        u"\uA401",u"\uA402",u"\uA403",u"\uA404",u"\uA405",u"\uA406",u"\uA407",
        u"\uA408",u"\uA409",u"\uA40A",u"\uA40B",u"\uA40C",u"\uA40D",u"\uA40E",
        u"\uA40F",u"\uA410",u"\uA411",u"\uA412",u"\uA413",u"\uA414",u"\uA415",
        u"\uA416",u"\uA417",u"\uA418",u"\uA419",u"\uA41A",u"\uA41B",u"\uA41C",
        u"\uA41D",u"\uA41E",u"\uA41F",u"\uA420",u"\uA421",u"\uA422",u"\uA423",
        u"\uA424",u"\uA425",u"\uA426",u"\uA427",u"\uA428",u"\uA429",u"\uA42A",
        u"\uA42B",u"\uA42C",u"\uA42D",u"\uA42E",u"\uA42F",u"\uA430",u"\uA431",
        u"\uA432",u"\uA433",u"\uA434",u"\uA435",u"\uA436",u"\uA437",u"\uA438",
        u"\uA439",u"\uA43A",u"\uA43B",u"\uA43C",u"\uA43D",u"\uA43E",u"\uA43F",
        u"\uA440",u"\uA441",u"\uA442",u"\uA443",u"\uA444",u"\uA445",u"\uA446",
        u"\uA447",u"\uA448",u"\uA449",u"\uA44A",u"\uA44B",u"\uA44C",u"\uA44D",
        u"\uA44E",u"\uA44F",u"\uA450",u"\uA451",u"\uA452",u"\uA453",u"\uA454",
        u"\uA455",u"\uA456",u"\uA457",u"\uA458",u"\uA459",u"\uA45A",u"\uA45B",
        u"\uA45C",u"\uA45D",u"\uA45E",u"\uA45F",u"\uA460",u"\uA461",u"\uA462",
        u"\uA463",u"\uA464",u"\uA465",u"\uA466",u"\uA467",u"\uA468",u"\uA469",
        u"\uA46A",u"\uA46B",u"\uA46C",u"\uA46D",u"\uA46E",u"\uA46F",u"\uA470",
        u"\uA471",u"\uA472",u"\uA473",u"\uA474",u"\uA475",u"\uA476",u"\uA477",
        u"\uA478",u"\uA479",u"\uA47A",u"\uA47B",u"\uA47C",u"\uA47D",u"\uA47E",
        u"\uA47F",u"\uA480",u"\uA481",u"\uA482",u"\uA483",u"\uA484",u"\uA485",
        u"\uA486",u"\uA487",u"\uA488",u"\uA489",u"\uA48A",u"\uA48B",u"\uA48C",
        u"\uA4F8",u"\uA4F9",u"\uA4FA",u"\uA4FB",u"\uA4FC",u"\uA4FD",u"\uA500",
        u"\uA501",u"\uA502",u"\uA503",u"\uA504",u"\uA505",u"\uA506",u"\uA507",
        u"\uA508",u"\uA509",u"\uA50A",u"\uA50B",u"\uA50C",u"\uA50D",u"\uA50E",
        u"\uA50F",u"\uA510",u"\uA511",u"\uA512",u"\uA513",u"\uA514",u"\uA515",
        u"\uA516",u"\uA517",u"\uA518",u"\uA519",u"\uA51A",u"\uA51B",u"\uA51C",
        u"\uA51D",u"\uA51E",u"\uA51F",u"\uA520",u"\uA521",u"\uA522",u"\uA523",
        u"\uA524",u"\uA525",u"\uA526",u"\uA527",u"\uA528",u"\uA529",u"\uA52A",
        u"\uA52B",u"\uA52C",u"\uA52D",u"\uA52E",u"\uA52F",u"\uA530",u"\uA531",
        u"\uA532",u"\uA533",u"\uA534",u"\uA535",u"\uA536",u"\uA537",u"\uA538",
        u"\uA539",u"\uA53A",u"\uA53B",u"\uA53C",u"\uA53D",u"\uA53E",u"\uA53F",
        u"\uA540",u"\uA541",u"\uA542",u"\uA543",u"\uA544",u"\uA545",u"\uA546",
        u"\uA547",u"\uA548",u"\uA549",u"\uA54A",u"\uA54B",u"\uA54C",u"\uA54D",
        u"\uA54E",u"\uA54F",u"\uA550",u"\uA551",u"\uA552",u"\uA553",u"\uA554",
        u"\uA555",u"\uA556",u"\uA557",u"\uA558",u"\uA559",u"\uA55A",u"\uA55B",
        u"\uA55C",u"\uA55D",u"\uA55E",u"\uA55F",u"\uA560",u"\uA561",u"\uA562",
        u"\uA563",u"\uA564",u"\uA565",u"\uA566",u"\uA567",u"\uA568",u"\uA569",
        u"\uA56A",u"\uA56B",u"\uA56C",u"\uA56D",u"\uA56E",u"\uA56F",u"\uA570",
        u"\uA571",u"\uA572",u"\uA573",u"\uA574",u"\uA575",u"\uA576",u"\uA577",
        u"\uA578",u"\uA579",u"\uA57A",u"\uA57B",u"\uA57C",u"\uA57D",u"\uA57E",
        u"\uA57F",u"\uA580",u"\uA581",u"\uA582",u"\uA583",u"\uA584",u"\uA585",
        u"\uA586",u"\uA587",u"\uA588",u"\uA589",u"\uA58A",u"\uA58B",u"\uA58C",
        u"\uA58D",u"\uA58E",u"\uA58F",u"\uA590",u"\uA591",u"\uA592",u"\uA593",
        u"\uA594",u"\uA595",u"\uA596",u"\uA597",u"\uA598",u"\uA599",u"\uA59A",
        u"\uA59B",u"\uA59C",u"\uA59D",u"\uA59E",u"\uA59F",u"\uA5A0",u"\uA5A1",
        u"\uA5A2",u"\uA5A3",u"\uA5A4",u"\uA5A5",u"\uA5A6",u"\uA5A7",u"\uA5A8",
        u"\uA5A9",u"\uA5AA",u"\uA5AB",u"\uA5AC",u"\uA5AD",u"\uA5AE",u"\uA5AF",
        u"\uA5B0",u"\uA5B1",u"\uA5B2",u"\uA5B3",u"\uA5B4",u"\uA5B5",u"\uA5B6",
        u"\uA5B7",u"\uA5B8",u"\uA5B9",u"\uA5BA",u"\uA5BB",u"\uA5BC",u"\uA5BD",
        u"\uA5BE",u"\uA5BF",u"\uA5C0",u"\uA5C1",u"\uA5C2",u"\uA5C3",u"\uA5C4",
        u"\uA5C5",u"\uA5C6",u"\uA5C7",u"\uA5C8",u"\uA5C9",u"\uA5CA",u"\uA5CB",
        u"\uA5CC",u"\uA5CD",u"\uA5CE",u"\uA5CF",u"\uA5D0",u"\uA5D1",u"\uA5D2",
        u"\uA5D3",u"\uA5D4",u"\uA5D5",u"\uA5D6",u"\uA5D7",u"\uA5D8",u"\uA5D9",
        u"\uA5DA",u"\uA5DB",u"\uA5DC",u"\uA5DD",u"\uA5DE",u"\uA5DF",u"\uA5E0",
        u"\uA5E1",u"\uA5E2",u"\uA5E3",u"\uA5E4",u"\uA5E5",u"\uA5E6",u"\uA5E7",
        u"\uA5E8",u"\uA5E9",u"\uA5EA",u"\uA5EB",u"\uA5EC",u"\uA5ED",u"\uA5EE",
        u"\uA5EF",u"\uA5F0",u"\uA5F1",u"\uA5F2",u"\uA5F3",u"\uA5F4",u"\uA5F5",
        u"\uA5F6",u"\uA5F7",u"\uA5F8",u"\uA5F9",u"\uA5FA",u"\uA5FB",u"\uA5FC",
        u"\uA5FD",u"\uA5FE",u"\uA5FF",u"\uA600",u"\uA601",u"\uA602",u"\uA603",
        u"\uA604",u"\uA605",u"\uA606",u"\uA607",u"\uA608",u"\uA609",u"\uA60A",
        u"\uA60B",u"\uA60C",u"\uA610",u"\uA611",u"\uA612",u"\uA613",u"\uA614",
        u"\uA615",u"\uA616",u"\uA617",u"\uA618",u"\uA619",u"\uA61A",u"\uA61B",
        u"\uA61C",u"\uA61D",u"\uA61E",u"\uA61F",u"\uA62A",u"\uA62B",u"\uA645",
        u"\uA64B",u"\uA64D",u"\uA64F",u"\uA651",u"\uA653",u"\uA655",u"\uA657",
        u"\uA659",u"\uA65B",u"\uA65D",u"\uA661",u"\uA663",u"\uA665",u"\uA667",
        u"\uA669",u"\uA66B",u"\uA66D",u"\uA66E",u"\uA67F",u"\uA681",u"\uA683",
        u"\uA685",u"\uA687",u"\uA689",u"\uA68B",u"\uA68D",u"\uA68F",u"\uA691",
        u"\uA693",u"\uA695",u"\uA697",u"\uA717",u"\uA718",u"\uA719",u"\uA71A",
        u"\uA71B",u"\uA71C",u"\uA71D",u"\uA71E",u"\uA71F",u"\uA723",u"\uA725",
        u"\uA727",u"\uA729",u"\uA72B",u"\uA72D",u"\uA72F",u"\uA730",u"\uA731",
        u"\uA733",u"\uA735",u"\uA737",u"\uA739",u"\uA73B",u"\uA73D",u"\uA73F",
        u"\uA741",u"\uA743",u"\uA745",u"\uA747",u"\uA749",u"\uA74B",u"\uA74D",
        u"\uA74F",u"\uA751",u"\uA753",u"\uA755",u"\uA757",u"\uA759",u"\uA75B",
        u"\uA75D",u"\uA75F",u"\uA761",u"\uA763",u"\uA765",u"\uA767",u"\uA769",
        u"\uA76B",u"\uA76D",u"\uA76F",u"\uA771",u"\uA772",u"\uA773",u"\uA774",
        u"\uA775",u"\uA776",u"\uA777",u"\uA778",u"\uA77A",u"\uA77C",u"\uA77F",
        u"\uA781",u"\uA783",u"\uA785",u"\uA787",u"\uA788",u"\uA78C",u"\uA78E",
        u"\uA791",u"\uA7A1",u"\uA7A3",u"\uA7A5",u"\uA7A7",u"\uA7A9",u"\uA7FA",
        u"\uA7FB",u"\uA7FC",u"\uA7FD",u"\uA7FE",u"\uA7FF",u"\uA800",u"\uA801",
        u"\uA803",u"\uA804",u"\uA805",u"\uA807",u"\uA808",u"\uA809",u"\uA80A",
        u"\uA80C",u"\uA80D",u"\uA80E",u"\uA80F",u"\uA810",u"\uA811",u"\uA812",
        u"\uA813",u"\uA814",u"\uA815",u"\uA816",u"\uA817",u"\uA818",u"\uA819",
        u"\uA81A",u"\uA81B",u"\uA81C",u"\uA81D",u"\uA81E",u"\uA81F",u"\uA820",
        u"\uA821",u"\uA822",u"\uA840",u"\uA841",u"\uA842",u"\uA843",u"\uA844",
        u"\uA845",u"\uA846",u"\uA847",u"\uA848",u"\uA849",u"\uA84A",u"\uA84B",
        u"\uA84C",u"\uA84D",u"\uA84E",u"\uA84F",u"\uA850",u"\uA851",u"\uA852",
        u"\uA853",u"\uA854",u"\uA855",u"\uA856",u"\uA857",u"\uA858",u"\uA859",
        u"\uA85A",u"\uA85B",u"\uA85C",u"\uA85D",u"\uA85E",u"\uA85F",u"\uA860",
        u"\uA861",u"\uA862",u"\uA863",u"\uA864",u"\uA865",u"\uA866",u"\uA867",
        u"\uA868",u"\uA869",u"\uA86A",u"\uA86B",u"\uA86C",u"\uA86D",u"\uA86E",
        u"\uA86F",u"\uA870",u"\uA871",u"\uA872",u"\uA873",u"\uA888",u"\uA889",
        u"\uA88A",u"\uA88B",u"\uA8F2",u"\uA8F3",u"\uA8F4",u"\uA8F5",u"\uA8F6",
        u"\uA8F7",u"\uA8FB",u"\uA90A",u"\uA90B",u"\uA90C",u"\uA90D",u"\uA90E",
        u"\uA90F",u"\uA910",u"\uA911",u"\uA912",u"\uA913",u"\uA914",u"\uA915",
        u"\uA916",u"\uA917",u"\uA918",u"\uA919",u"\uA91A",u"\uA91B",u"\uA91C",
        u"\uA91D",u"\uA91E",u"\uA91F",u"\uA920",u"\uA921",u"\uA922",u"\uA923",
        u"\uA924",u"\uA925",u"\uA960",u"\uA961",u"\uA962",u"\uA963",u"\uA964",
        u"\uA965",u"\uA966",u"\uA967",u"\uA968",u"\uA969",u"\uA96A",u"\uA96B",
        u"\uA96C",u"\uA96D",u"\uA96E",u"\uA96F",u"\uA970",u"\uA971",u"\uA972",
        u"\uA973",u"\uA974",u"\uA975",u"\uA976",u"\uA977",u"\uA978",u"\uA97A",
        u"\uA97B",u"\uA985",u"\uA989",u"\uA98A",u"\uA98B",u"\uA990",u"\uA991",
        u"\uA993",u"\uA996",u"\uA998",u"\uA999",u"\uA99C",u"\uA99E",u"\uA99F",
        u"\uA9A1",u"\uA9A3",u"\uA9A6",u"\uA9A8",u"\uA9AC",u"\uA9AF",u"\uA9B0",
        u"\uA9CF",u"\uAA60",u"\uAA61",u"\uAA62",u"\uAA63",u"\uAA64",u"\uAA65",
        u"\uAA66",u"\uAA67",u"\uAA68",u"\uAA69",u"\uAA6A",u"\uAA6B",u"\uAA6C",
        u"\uAA6D",u"\uAA6E",u"\uAA6F",u"\uAA70",u"\uAA71",u"\uAA72",u"\uAA73",
        u"\uAA74",u"\uAA75",u"\uAA76",u"\uAA7A",u"\uAA80",u"\uAA81",u"\uAA82",
        u"\uAA83",u"\uAA84",u"\uAA85",u"\uAA86",u"\uAA87",u"\uAA88",u"\uAA89",
        u"\uAA8A",u"\uAA8B",u"\uAA8C",u"\uAA8D",u"\uAA8E",u"\uAA8F",u"\uAA90",
        u"\uAA91",u"\uAA92",u"\uAA93",u"\uAA94",u"\uAA95",u"\uAA96",u"\uAA97",
        u"\uAA98",u"\uAA99",u"\uAA9A",u"\uAA9B",u"\uAA9C",u"\uAA9D",u"\uAA9E",
        u"\uAA9F",u"\uAAA0",u"\uAAA1",u"\uAAA2",u"\uAAA3",u"\uAAA4",u"\uAAA5",
        u"\uAAA6",u"\uAAA7",u"\uAAA8",u"\uAAA9",u"\uAAAA",u"\uAAAB",u"\uAAAC",
        u"\uAAAD",u"\uAAAE",u"\uAAAF",u"\uAAB1",u"\uAAB5",u"\uAAB6",u"\uAAB9",
        u"\uAABA",u"\uAABB",u"\uAABC",u"\uAABD",u"\uAAC0",u"\uAAC2",u"\uAADB",
        u"\uAADC",u"\uAADD",u"\uAB01",u"\uAB02",u"\uAB03",u"\uAB04",u"\uAB05",
        u"\uAB06",u"\uAB09",u"\uAB0A",u"\uAB0B",u"\uAB0C",u"\uAB0D",u"\uAB0E",
        u"\uAB11",u"\uAB12",u"\uAB13",u"\uAB14",u"\uAB15",u"\uAB16",u"\uAB20",
        u"\uAB21",u"\uAB22",u"\uAB23",u"\uAB24",u"\uAB25",u"\uAB26",u"\uAB28",
        u"\uAB29",u"\uAB2A",u"\uAB2B",u"\uAB2C",u"\uAB2D",u"\uAB2E",u"\uABC0",
        u"\uABC1",u"\uABC2",u"\uABC3",u"\uABC4",u"\uABC5",u"\uABC6",u"\uABC7",
        u"\uABC8",u"\uABC9",u"\uABCA",u"\uABCB",u"\uABCC",u"\uABCD",u"\uABCE",
        u"\uABCF",u"\uABD0",u"\uABD1",u"\uABD2",u"\uABD3",u"\uABD4",u"\uABD5",
        u"\uABD6",u"\uABD7",u"\uABD8",u"\uABD9",u"\uABDA",u"\uABDB",u"\uABDC",
        u"\uABDD",u"\uABDE",u"\uABDF",u"\uABE0",u"\uABE1",u"\uABE2",u"\uAC00",
        u"\uD7A3",u"\uD7B0",u"\uD7B1",u"\uD7B2",u"\uD7B3",u"\uD7B4",u"\uD7B5",
        u"\uD7B6",u"\uD7B7",u"\uD7B8",u"\uD7B9",u"\uD7BA",u"\uD7BB",u"\uD7BC",
        u"\uD7BD",u"\uD7BE",u"\uD7BF",u"\uD7C0",u"\uD7C1",u"\uD7C2",u"\uD7C3",
        u"\uD7C4",u"\uD7C5",u"\uD7C6",u"\uD7CB",u"\uD7CC",u"\uD7CE",u"\uD7CF",
        u"\uD7D0",u"\uD7D1",u"\uD7D2",u"\uD7D3",u"\uD7D4",u"\uD7D5",u"\uD7D6",
        u"\uD7D7",u"\uD7D8",u"\uD7D9",u"\uD7DA",u"\uD7DB",u"\uD7DC",u"\uD7DE",
        u"\uD7DF",u"\uD7E1",u"\uD7E2",u"\uD7E3",u"\uD7E4",u"\uD7E5",u"\uD7E7",
        u"\uD7E8",u"\uD7E9",u"\uD7EA",u"\uD7EB",u"\uD7EC",u"\uD7ED",u"\uD7EE",
        u"\uD7EF",u"\uD7F0",u"\uD7F1",u"\uD7F2",u"\uD7F3",u"\uD7F4",u"\uD7F5",
        u"\uD7F6",u"\uD7F7",u"\uD7F8",u"\uD7FA",u"\uD7FB",u"\uF900",u"\uF901",
        u"\uF902",u"\uF903",u"\uF904",u"\uF905",u"\uF906",u"\uF907",u"\uF908",
        u"\uF909",u"\uF90A",u"\uF90B",u"\uF90C",u"\uF90D",u"\uF90E",u"\uF90F",
        u"\uF910",u"\uF911",u"\uF912",u"\uF913",u"\uF914",u"\uF915",u"\uF916",
        u"\uF917",u"\uF918",u"\uF919",u"\uF91A",u"\uF91B",u"\uF91C",u"\uF91D",
        u"\uF91E",u"\uF91F",u"\uF920",u"\uF921",u"\uF922",u"\uF923",u"\uF924",
        u"\uF925",u"\uF926",u"\uF927",u"\uF928",u"\uF929",u"\uF92A",u"\uF92B",
        u"\uF92C",u"\uF92D",u"\uF92E",u"\uF92F",u"\uF930",u"\uF931",u"\uF932",
        u"\uF933",u"\uF934",u"\uF935",u"\uF936",u"\uF937",u"\uF938",u"\uF939",
        u"\uF93A",u"\uF93B",u"\uF93C",u"\uF93D",u"\uF93E",u"\uF93F",u"\uF940",
        u"\uF941",u"\uF942",u"\uF943",u"\uF944",u"\uF945",u"\uF946",u"\uF947",
        u"\uF948",u"\uF949",u"\uF94A",u"\uF94B",u"\uF94C",u"\uF94D",u"\uF94E",
        u"\uF94F",u"\uF950",u"\uF951",u"\uF952",u"\uF953",u"\uF954",u"\uF955",
        u"\uF956",u"\uF957",u"\uF958",u"\uF959",u"\uF95A",u"\uF95B",u"\uF95C",
        u"\uF95D",u"\uF95E",u"\uF95F",u"\uF960",u"\uF961",u"\uF962",u"\uF963",
        u"\uF964",u"\uF965",u"\uF966",u"\uF967",u"\uF968",u"\uF969",u"\uF96A",
        u"\uF96B",u"\uF96C",u"\uF96D",u"\uF96E",u"\uF96F",u"\uF970",u"\uF971",
        u"\uF972",u"\uF973",u"\uF974",u"\uF975",u"\uF976",u"\uF977",u"\uF978",
        u"\uF979",u"\uF97A",u"\uF97B",u"\uF97C",u"\uF97D",u"\uF97E",u"\uF97F",
        u"\uF980",u"\uF981",u"\uF982",u"\uF983",u"\uF984",u"\uF985",u"\uF986",
        u"\uF987",u"\uF988",u"\uF989",u"\uF98A",u"\uF98B",u"\uF98C",u"\uF98D",
        u"\uF98E",u"\uF98F",u"\uF990",u"\uF991",u"\uF992",u"\uF993",u"\uF994",
        u"\uF995",u"\uF996",u"\uF997",u"\uF998",u"\uF999",u"\uF99A",u"\uF99B",
        u"\uF99C",u"\uF99D",u"\uF99E",u"\uF99F",u"\uF9A0",u"\uF9A1",u"\uF9A2",
        u"\uF9A3",u"\uF9A4",u"\uF9A5",u"\uF9A6",u"\uF9A7",u"\uF9A8",u"\uF9A9",
        u"\uF9AA",u"\uF9AB",u"\uF9AC",u"\uF9AD",u"\uF9AE",u"\uF9AF",u"\uF9B0",
        u"\uF9B1",u"\uF9B2",u"\uF9B3",u"\uF9B4",u"\uF9B5",u"\uF9B6",u"\uF9B7",
        u"\uF9B8",u"\uF9B9",u"\uF9BA",u"\uF9BB",u"\uF9BC",u"\uF9BD",u"\uF9BE",
        u"\uF9BF",u"\uF9C0",u"\uF9C1",u"\uF9C2",u"\uF9C3",u"\uF9C4",u"\uF9C5",
        u"\uF9C6",u"\uF9C7",u"\uF9C8",u"\uF9C9",u"\uF9CA",u"\uF9CB",u"\uF9CC",
        u"\uF9CD",u"\uF9CE",u"\uF9CF",u"\uF9D0",u"\uF9D1",u"\uF9D2",u"\uF9D3",
        u"\uF9D4",u"\uF9D5",u"\uF9D6",u"\uF9D7",u"\uF9D8",u"\uF9D9",u"\uF9DA",
        u"\uF9DB",u"\uF9DC",u"\uF9DD",u"\uF9DE",u"\uF9DF",u"\uF9E0",u"\uF9E1",
        u"\uF9E2",u"\uF9E3",u"\uF9E4",u"\uF9E5",u"\uF9E6",u"\uF9E7",u"\uF9E8",
        u"\uF9E9",u"\uF9EA",u"\uF9EB",u"\uF9EC",u"\uF9ED",u"\uF9EE",u"\uF9EF",
        u"\uF9F0",u"\uF9F1",u"\uF9F2",u"\uF9F3",u"\uF9F4",u"\uF9F5",u"\uF9F6",
        u"\uF9F7",u"\uF9F8",u"\uF9F9",u"\uF9FA",u"\uF9FB",u"\uF9FC",u"\uF9FD",
        u"\uF9FE",u"\uF9FF",u"\uFA00",u"\uFA01",u"\uFA02",u"\uFA03",u"\uFA04",
        u"\uFA05",u"\uFA06",u"\uFA07",u"\uFA08",u"\uFA09",u"\uFA0A",u"\uFA0B",
        u"\uFA0C",u"\uFA0D",u"\uFA0E",u"\uFA0F",u"\uFA10",u"\uFA11",u"\uFA12",
        u"\uFA13",u"\uFA14",u"\uFA15",u"\uFA16",u"\uFA17",u"\uFA18",u"\uFA19",
        u"\uFA1A",u"\uFA1B",u"\uFA1C",u"\uFA1D",u"\uFA1E",u"\uFA1F",u"\uFA20",
        u"\uFA21",u"\uFA22",u"\uFA23",u"\uFA24",u"\uFA25",u"\uFA26",u"\uFA27",
        u"\uFA28",u"\uFA29",u"\uFA2A",u"\uFA2B",u"\uFA2C",u"\uFA2D",u"\uFA30",
        u"\uFA31",u"\uFA32",u"\uFA33",u"\uFA34",u"\uFA35",u"\uFA36",u"\uFA37",
        u"\uFA38",u"\uFA39",u"\uFA3A",u"\uFA3B",u"\uFA3C",u"\uFA3D",u"\uFA3E",
        u"\uFA3F",u"\uFA40",u"\uFA41",u"\uFA42",u"\uFA43",u"\uFA44",u"\uFA45",
        u"\uFA46",u"\uFA47",u"\uFA48",u"\uFA49",u"\uFA4A",u"\uFA4B",u"\uFA4C",
        u"\uFA4D",u"\uFA4E",u"\uFA4F",u"\uFA50",u"\uFA51",u"\uFA52",u"\uFA53",
        u"\uFA54",u"\uFA55",u"\uFA56",u"\uFA57",u"\uFA58",u"\uFA59",u"\uFA5A",
        u"\uFA5B",u"\uFA5C",u"\uFA5D",u"\uFA5E",u"\uFA5F",u"\uFA60",u"\uFA61",
        u"\uFA62",u"\uFA63",u"\uFA64",u"\uFA65",u"\uFA66",u"\uFA67",u"\uFA68",
        u"\uFA69",u"\uFA6A",u"\uFA6B",u"\uFA6C",u"\uFA6D",u"\uFA70",u"\uFA71",
        u"\uFA72",u"\uFA73",u"\uFA74",u"\uFA75",u"\uFA76",u"\uFA77",u"\uFA78",
        u"\uFA79",u"\uFA7A",u"\uFA7B",u"\uFA7C",u"\uFA7D",u"\uFA7E",u"\uFA7F",
        u"\uFA80",u"\uFA81",u"\uFA82",u"\uFA83",u"\uFA84",u"\uFA85",u"\uFA86",
        u"\uFA87",u"\uFA88",u"\uFA89",u"\uFA8A",u"\uFA8B",u"\uFA8C",u"\uFA8D",
        u"\uFA8E",u"\uFA8F",u"\uFA90",u"\uFA91",u"\uFA92",u"\uFA93",u"\uFA94",
        u"\uFA95",u"\uFA96",u"\uFA97",u"\uFA98",u"\uFA99",u"\uFA9A",u"\uFA9B",
        u"\uFA9C",u"\uFA9D",u"\uFA9E",u"\uFA9F",u"\uFAA0",u"\uFAA1",u"\uFAA2",
        u"\uFAA3",u"\uFAA4",u"\uFAA5",u"\uFAA6",u"\uFAA7",u"\uFAA8",u"\uFAA9",
        u"\uFAAA",u"\uFAAB",u"\uFAAC",u"\uFAAD",u"\uFAAE",u"\uFAAF",u"\uFAB0",
        u"\uFAB1",u"\uFAB2",u"\uFAB3",u"\uFAB4",u"\uFAB5",u"\uFAB6",u"\uFAB7",
        u"\uFAB8",u"\uFAB9",u"\uFABA",u"\uFABB",u"\uFABC",u"\uFABD",u"\uFABE",
        u"\uFABF",u"\uFAC0",u"\uFAC1",u"\uFAC2",u"\uFAC3",u"\uFAC4",u"\uFAC5",
        u"\uFAC6",u"\uFAC7",u"\uFAC8",u"\uFAC9",u"\uFACA",u"\uFACB",u"\uFACC",
        u"\uFACD",u"\uFACE",u"\uFACF",u"\uFAD0",u"\uFAD1",u"\uFAD2",u"\uFAD3",
        u"\uFAD4",u"\uFAD5",u"\uFAD6",u"\uFAD7",u"\uFAD8",u"\uFAD9",u"\uFB00",
        u"\uFB01",u"\uFB02",u"\uFB03",u"\uFB04",u"\uFB05",u"\uFB06",u"\uFB13",
        u"\uFB14",u"\uFB15",u"\uFB16",u"\uFB17",u"\uFB1D",u"\uFB1F",u"\uFB20",
        u"\uFB21",u"\uFB22",u"\uFB23",u"\uFB24",u"\uFB25",u"\uFB26",u"\uFB27",
        u"\uFB28",u"\uFB2A",u"\uFB2B",u"\uFB2C",u"\uFB2D",u"\uFB2E",u"\uFB2F",
        u"\uFB30",u"\uFB31",u"\uFB32",u"\uFB33",u"\uFB34",u"\uFB35",u"\uFB36",
        u"\uFB38",u"\uFB39",u"\uFB3A",u"\uFB3B",u"\uFB3C",u"\uFB3E",u"\uFB40",
        u"\uFB41",u"\uFB43",u"\uFB44",u"\uFB46",u"\uFB47",u"\uFB48",u"\uFB49",
        u"\uFB4A",u"\uFB4B",u"\uFB4C",u"\uFB4D",u"\uFB4E",u"\uFB4F",u"\uFE73",
        u"\uFF41",u"\uFF42",u"\uFF43",u"\uFF44",u"\uFF45",u"\uFF46",u"\uFF47",
        u"\uFF48",u"\uFF49",u"\uFF4A",u"\uFF4B",u"\uFF4C",u"\uFF4D",u"\uFF4E",
        u"\uFF4F",u"\uFF50",u"\uFF51",u"\uFF52",u"\uFF53",u"\uFF54",u"\uFF55",
        u"\uFF56",u"\uFF57",u"\uFF58",u"\uFF59",u"\uFF5A",u"\uFF66",u"\uFF67",
        u"\uFF68",u"\uFF69",u"\uFF6A",u"\uFF6B",u"\uFF6C",u"\uFF6D",u"\uFF6E",
        u"\uFF6F",u"\uFF70",u"\uFF71",u"\uFF72",u"\uFF73",u"\uFF74",u"\uFF75",
        u"\uFF76",u"\uFF77",u"\uFF78",u"\uFF79",u"\uFF7A",u"\uFF7B",u"\uFF7C",
        u"\uFF7D",u"\uFF7E",u"\uFF7F",u"\uFF80",u"\uFF81",u"\uFF82",u"\uFF83",
        u"\uFF84",u"\uFF85",u"\uFF86",u"\uFF87",u"\uFF88",u"\uFF89",u"\uFF8A",
        u"\uFF8B",u"\uFF8C",u"\uFF8D",u"\uFF8E",u"\uFF8F",u"\uFF90",u"\uFF91",
        u"\uFF92",u"\uFF93",u"\uFF94",u"\uFF95",u"\uFF96",u"\uFF97",u"\uFF98",
        u"\uFF99",u"\uFF9A",u"\uFF9B",u"\uFF9C",u"\uFF9D",u"\uFF9E",u"\uFF9F",
        u"\uFFA0",u"\uFFA1",u"\uFFA2",u"\uFFA3",u"\uFFA4",u"\uFFA5",u"\uFFA6",
        u"\uFFA7",u"\uFFA8",u"\uFFA9",u"\uFFAA",u"\uFFAB",u"\uFFAC",u"\uFFAD",
        u"\uFFAE",u"\uFFAF",u"\uFFB0",u"\uFFB1",u"\uFFB2",u"\uFFB3",u"\uFFB4",
        u"\uFFB5",u"\uFFB6",u"\uFFB7",u"\uFFB8",u"\uFFB9",u"\uFFBA",u"\uFFBB",
        u"\uFFBC",u"\uFFBD",u"\uFFBE",u"\uFFC2",u"\uFFC3",u"\uFFC4",u"\uFFC5",
        u"\uFFC6",u"\uFFC7",u"\uFFCA",u"\uFFCB",u"\uFFCC",u"\uFFCD",u"\uFFCE",
        u"\uFFCF",u"\uFFD2",u"\uFFD3",u"\uFFD4",u"\uFFD5",u"\uFFD6",u"\uFFD7",
        u"\uFFDA",u"\uFFDB",u"\uFFDC"],
    "WF_Consonants" : [
        u"\uFB51",u"\uFB53",u"\uFB55",u"\uFB57",u"\uFB59",u"\uFB5B",u"\uFB5D",
        u"\uFB5F",u"\uFB61",u"\uFB63",u"\uFB65",u"\uFB67",u"\uFB69",u"\uFB6B",
        u"\uFB6D",u"\uFB6F",u"\uFB71",u"\uFB73",u"\uFB75",u"\uFB77",u"\uFB79",
        u"\uFB7B",u"\uFB7D",u"\uFB7F",u"\uFB81",u"\uFB83",u"\uFB85",u"\uFB87",
        u"\uFB89",u"\uFB8B",u"\uFB8D",u"\uFB8F",u"\uFB91",u"\uFB93",u"\uFB95",
        u"\uFB97",u"\uFB99",u"\uFB9B",u"\uFB9D",u"\uFB9F",u"\uFBA1",u"\uFBA3",
        u"\uFBA5",u"\uFBA7",u"\uFBA9",u"\uFBAB",u"\uFBAD",u"\uFBAF",u"\uFBB1",
        u"\uFBD4",u"\uFBD6",u"\uFBD8",u"\uFBDA",u"\uFBDC",u"\uFBDF",u"\uFBE1",
        u"\uFBE3",u"\uFBE5",u"\uFBE7",u"\uFBE9",u"\uFBEB",u"\uFBED",u"\uFBEF",
        u"\uFBF1",u"\uFBF3",u"\uFBF5",u"\uFBF7",u"\uFBFA",u"\uFBFD",u"\uFBFF",
        u"\uFC64",u"\uFC65",u"\uFC66",u"\uFC67",u"\uFC68",u"\uFC69",u"\uFC6A",
        u"\uFC6B",u"\uFC6C",u"\uFC6D",u"\uFC6E",u"\uFC6F",u"\uFC70",u"\uFC71",
        u"\uFC72",u"\uFC73",u"\uFC74",u"\uFC75",u"\uFC76",u"\uFC77",u"\uFC78",
        u"\uFC79",u"\uFC7A",u"\uFC7B",u"\uFC7C",u"\uFC7D",u"\uFC7E",u"\uFC7F",
        u"\uFC80",u"\uFC81",u"\uFC82",u"\uFC83",u"\uFC84",u"\uFC85",u"\uFC86",
        u"\uFC87",u"\uFC88",u"\uFC89",u"\uFC8A",u"\uFC8B",u"\uFC8C",u"\uFC8D",
        u"\uFC8E",u"\uFC8F",u"\uFC90",u"\uFC91",u"\uFC92",u"\uFC93",u"\uFC94",
        u"\uFC95",u"\uFC96",u"\uFCDF",u"\uFCE0",u"\uFCE1",u"\uFCE2",u"\uFCE3",
        u"\uFCE4",u"\uFCE5",u"\uFCE6",u"\uFCE7",u"\uFCE8",u"\uFCE9",u"\uFCEA",
        u"\uFCEB",u"\uFCEC",u"\uFCED",u"\uFCEE",u"\uFCEF",u"\uFCF0",u"\uFCF1",
        u"\uFCF2",u"\uFCF3",u"\uFCF4",u"\uFD11",u"\uFD12",u"\uFD13",u"\uFD14",
        u"\uFD15",u"\uFD16",u"\uFD17",u"\uFD18",u"\uFD19",u"\uFD1A",u"\uFD1B",
        u"\uFD1C",u"\uFD1D",u"\uFD1E",u"\uFD1F",u"\uFD20",u"\uFD21",u"\uFD22",
        u"\uFD23",u"\uFD24",u"\uFD25",u"\uFD26",u"\uFD27",u"\uFD28",u"\uFD29",
        u"\uFD2A",u"\uFD2B",u"\uFD2C",u"\uFD34",u"\uFD35",u"\uFD36",u"\uFD37",
        u"\uFD38",u"\uFD39",u"\uFD3A",u"\uFD3B",u"\uFD3C",u"\uFD51",u"\uFD58",
        u"\uFD5A",u"\uFD5B",u"\uFD5E",u"\uFD5F",u"\uFD62",u"\uFD64",u"\uFD66",
        u"\uFD67",u"\uFD69",u"\uFD6A",u"\uFD6C",u"\uFD6E",u"\uFD6F",u"\uFD71",
        u"\uFD74",u"\uFD75",u"\uFD76",u"\uFD78",u"\uFD79",u"\uFD7A",u"\uFD7B",
        u"\uFD7C",u"\uFD7E",u"\uFD7F",u"\uFD80",u"\uFD81",u"\uFD82",u"\uFD84",
        u"\uFD85",u"\uFD87",u"\uFD8B",u"\uFD96",u"\uFD97",u"\uFD99",u"\uFD9A",
        u"\uFD9B",u"\uFD9C",u"\uFD9E",u"\uFD9F",u"\uFDA0",u"\uFDA1",u"\uFDA2",
        u"\uFDA3",u"\uFDA4",u"\uFDA5",u"\uFDA6",u"\uFDA7",u"\uFDA8",u"\uFDA9",
        u"\uFDAA",u"\uFDAB",u"\uFDAC",u"\uFDAD",u"\uFDAE",u"\uFDAF",u"\uFDB0",
        u"\uFDB1",u"\uFDB2",u"\uFDB3",u"\uFDB6",u"\uFDB7",u"\uFDB9",u"\uFDBB",
        u"\uFDBC",u"\uFDBD",u"\uFDBE",u"\uFDBF",u"\uFDC0",u"\uFDC1",u"\uFDC2",
        u"\uFDC6",u"\uFDC7",u"\uFE71",u"\uFE77",u"\uFE79",u"\uFE7B",u"\uFE7D",
        u"\uFE7F",u"\uFE82",u"\uFE84",u"\uFE86",u"\uFE88",u"\uFE8A",u"\uFE8C",
        u"\uFE8E",u"\uFE90",u"\uFE92",u"\uFE94",u"\uFE96",u"\uFE98",u"\uFE9A",
        u"\uFE9C",u"\uFE9E",u"\uFEA0",u"\uFEA2",u"\uFEA4",u"\uFEA6",u"\uFEA8",
        u"\uFEAA",u"\uFEAC",u"\uFEAE",u"\uFEB0",u"\uFEB2",u"\uFEB4",u"\uFEB6",
        u"\uFEB8",u"\uFEBA",u"\uFEBC",u"\uFEBE",u"\uFEC0",u"\uFEC2",u"\uFEC4",
        u"\uFEC6",u"\uFEC8",u"\uFECA",u"\uFECC",u"\uFECE",u"\uFED0",u"\uFED2",
        u"\uFED4",u"\uFED6",u"\uFED8",u"\uFEDA",u"\uFEDC",u"\uFEDE",u"\uFEE0",
        u"\uFEE2",u"\uFEE4",u"\uFEE6",u"\uFEE8",u"\uFEEA",u"\uFEEC",u"\uFEEE",
        u"\uFEF0",u"\uFEF2",u"\uFEF4",u"\uFEF6",u"\uFEF8",u"\uFEFA",u"\uFEFC"],
    }
    SimilarChars = {
        "ARABIC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0632",u"\u0633",u"\u0634",u"\u0639",u"\u063A",u"\u0645",
                u"\u0646"],
        ],
            "LIQUID" : [
            [u"\u0627",u"\u062F",u"\u0630",u"\u0631",u"\u0644"],
        ],
            "POA" : [
            [u"\u0621",u"\u062A",u"\u062B",u"\u0635",u"\u0636",u"\u0637",
                u"\u0638"],
            [u"\u0641"],
            [u"\u062E",u"\u0643"],
            [u"\u062C"],
            [u"\u0642"],
            [u"\u0628"],
        ],
            "ASP" : [],
        },
        "ARMENIAN": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0562",u"\u056B",u"\u056C",u"\u056F",u"\u0574",u"\u0576",
                u"\u057F",u"\u0582"],
        ],
            "LIQUID" : [
            [u"\u057C",u"\u0580"],
        ],
            "POA" : [
            [u"\u0564",u"\u0566",u"\u0569",u"\u056A",u"\u0572",u"\u0577",
                u"\u057D"],
            [u"\u0578",u"\u057E",u"\u0586"],
            [u"\u0563",u"\u056D",u"\u0584"],
            [u"\u0565",u"\u056E",u"\u0571",u"\u0573",u"\u0579",u"\u057B",
                u"\u0581"],
            [u"\u057A",u"\u0583"],
        ],
            "ASP" : [
            [u"\u056E",u"\u0579"],
        ],
        },
        "BALINESE": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1B17",u"\u1B1C",u"\u1B26",u"\u1B2B"],
        ],
            "LIQUID" : [
            [u"\u1B2D",u"\u1B2E"],
        ],
            "POA" : [
            [u"\u1B22",u"\u1B24",u"\u1B32"],
            [u"\u1B13",u"\u1B15"],
            [u"\u1B18",u"\u1B1A"],
            [u"\u1B27",u"\u1B29"],
        ],
            "ASP" : [],
        },
        "BAMUM": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\uA6A8",u"\uA6AF",u"\uA6B1",u"\uA6B2",u"\uA6B3",u"\uA6B5",
                u"\uA6BC",u"\uA6BD",u"\uA6BE",u"\uA6C3",u"\uA6C6",u"\uA6C7",
                u"\uA6CE",u"\uA6CF",u"\uA6D2",u"\uA6D3",u"\uA6D4",u"\uA6D5",
                u"\uA6DB",u"\uA6E0",u"\uA6E1",u"\uA6E2",u"\uA6E3",u"\uA6E6",
                u"\uA6E7",u"\uA6EA",u"\uA6EB"],
        ],
            "LIQUID" : [
            [u"\uA6A5",u"\uA6AA",u"\uA6AC",u"\uA6AD",u"\uA6AE",u"\uA6CC",
                u"\uA6CD",u"\uA6D0",u"\uA6D1",u"\uA6DC",u"\uA6DE"],
        ],
            "POA" : [
            [u"\uA6A6",u"\uA6B0",u"\uA6B4",u"\uA6B6",u"\uA6B7",u"\uA6B8",
                u"\uA6B9",u"\uA6C0",u"\uA6D6",u"\uA6E4",u"\uA6E8"],
            [u"\uA6CB",u"\uA6D8",u"\uA6D9",u"\uA6ED",u"\uA6EE"],
            [u"\uA6A1",u"\uA6A3",u"\uA6BA",u"\uA6BB",u"\uA6C4",u"\uA6DF",
                u"\uA6E5",u"\uA6E9",u"\uA6EF"],
            [u"\uA6AB",u"\uA6C5",u"\uA6C8",u"\uA6CA",u"\uA6D7",u"\uA6DD",
                u"\uA6EC"],
        ],
            "ASP" : [
            [u"\uA6B8",u"\uA6B9"],
        ],
        },
        "BATAK": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1BC9",u"\u1BD4",u"\u1BDD",u"\u1BE0",u"\u1BE2",u"\u1BE3"],
        ],
            "LIQUID" : [
            [u"\u1BD2",u"\u1BDE"],
        ],
            "POA" : [
            [u"\u1BD1",u"\u1BD8"],
            [u"\u1BCE"],
            [u"\u1BD0",u"\u1BE1"],
            [u"\u1BC5",u"\u1BC7"],
        ],
            "ASP" : [],
        },
        "BENGALI": {
            "VOW_LEN" : [
            [u"\u0987",u"\u0988"],
            [u"\u0985",u"\u0986"],
            [u"\u0989",u"\u098A"],
        ],
            "VOW_GLIDE" : [
            [u"\u0985",u"\u0990"],
        ],
            "NASAL" : [
            [u"\u0999",u"\u099E",u"\u09A3",u"\u09A8",u"\u09AE"],
        ],
            "LIQUID" : [
            [u"\u09B0",u"\u09B2"],
        ],
            "POA" : [
            [u"\u099F",u"\u09A0",u"\u09A1",u"\u09A2",u"\u09A4",u"\u09A5",
                u"\u09A6",u"\u09A7",u"\u09B6",u"\u09B7",u"\u09B8"],
            [u"\u0995",u"\u0996",u"\u0997",u"\u0998"],
            [u"\u099A",u"\u099B",u"\u099C",u"\u099D"],
            [u"\u09AA",u"\u09AB",u"\u09AC",u"\u09AD"],
        ],
            "ASP" : [
            [u"\u09AC",u"\u09AD"],
            [u"\u099F",u"\u09A0"],
            [u"\u09A4",u"\u09A5"],
            [u"\u09A1",u"\u09A2"],
            [u"\u099A",u"\u099B"],
            [u"\u0995",u"\u0996"],
            [u"\u099C",u"\u099D"],
            [u"\u09B6",u"\u09B8"],
            [u"\u09AA",u"\u09AB"],
            [u"\u0997",u"\u0998"],
            [u"\u09A6",u"\u09A7"],
        ],
        },
        "BOPOMOFO": {
            "VOW_LEN" : [
            [u"\u311C",u"\u31A4"],
            [u"\u311B",u"\u31A6"],
        ],
            "VOW_GLIDE" : [
            [u"\u3127",u"\u3129"],
            [u"\u311C",u"\u311F"],
            [u"\u311A",u"\u311E"],
            [u"\u311B",u"\u3121"],
        ],
            "NASAL" : [
            [u"\u3107",u"\u310B",u"\u3122",u"\u3123",u"\u3124",u"\u3125",
                u"\u312B",u"\u312C",u"\u31A5",u"\u31A7",u"\u31A9",u"\u31AA",
                u"\u31AB",u"\u31AD",u"\u31AE",u"\u31AF",u"\u31B2",u"\u31B3"],
        ],
            "LIQUID" : [
            [u"\u310C",u"\u3116",u"\u31B9"],
        ],
            "POA" : [
            [u"\u3109",u"\u310A",u"\u3113",u"\u3115",u"\u3117",u"\u3119",
                u"\u31A1",u"\u31BA"],
            [u"\u3108",u"\u312A"],
            [u"\u310D",u"\u310E",u"\u3112",u"\u31A3",u"\u31B8"],
            [u"\u3110",u"\u3114",u"\u3118",u"\u31A2"],
            [u"\u3111"],
            [u"\u3105",u"\u3106",u"\u31A0"],
        ],
            "ASP" : [
            [u"\u310D",u"\u31B8"],
            [u"\u3114",u"\u3118"],
            [u"\u3113",u"\u3117"],
            [u"\u3115",u"\u3119"],
        ],
        },
        "BUGINESE": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1A02",u"\u1A03",u"\u1A06",u"\u1A07",u"\u1A0A",u"\u1A0B",
                u"\u1A0E",u"\u1A0F"],
        ],
            "LIQUID" : [
            [u"\u1A11",u"\u1A12"],
        ],
            "POA" : [
            [u"\u1A08",u"\u1A09",u"\u1A14"],
            [u"\u1A13"],
            [u"\u1A00",u"\u1A01"],
            [u"\u1A0C",u"\u1A0D"],
            [u"\u1A04",u"\u1A05"],
        ],
            "ASP" : [],
        },
        "BUHID": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1745",u"\u1748",u"\u174B"],
        ],
            "LIQUID" : [
            [u"\u174D",u"\u174E"],
        ],
            "POA" : [
            [u"\u1746",u"\u1747",u"\u1750"],
            [u"\u1743",u"\u1744"],
            [u"\u1749",u"\u174A"],
        ],
            "ASP" : [],
        },
        "CHAM": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [
            [u"\uAA00",u"\uAA04"],
        ],
            "NASAL" : [
            [u"\uAA0A",u"\uAA0B",u"\uAA10",u"\uAA11",u"\uAA12",u"\uAA17",
                u"\uAA18",u"\uAA1F",u"\uAA20",u"\uAA42",u"\uAA46"],
        ],
            "LIQUID" : [
            [u"\uAA23",u"\uAA24",u"\uAA49",u"\uAA4A"],
        ],
            "POA" : [
            [u"\uAA13",u"\uAA14",u"\uAA15",u"\uAA16",u"\uAA19",u"\uAA26",
                u"\uAA27",u"\uAA45",u"\uAA4B"],
            [u"\uAA25"],
            [u"\uAA06",u"\uAA07",u"\uAA08",u"\uAA09",u"\uAA40",u"\uAA41"],
            [u"\uAA0C",u"\uAA0D",u"\uAA0E",u"\uAA0F",u"\uAA44"],
            [u"\uAA1A",u"\uAA1B",u"\uAA1C",u"\uAA1D",u"\uAA1E",u"\uAA21",
                u"\uAA47"],
        ],
            "ASP" : [
            [u"\uAA08",u"\uAA09"],
            [u"\uAA13",u"\uAA14"],
            [u"\uAA15",u"\uAA16"],
            [u"\uAA1D",u"\uAA1E"],
            [u"\uAA1A",u"\uAA1C"],
            [u"\uAA06",u"\uAA07"],
            [u"\uAA0E",u"\uAA0F"],
        ],
        },
        "CHEROKEE": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u13B9",u"\u13BA",u"\u13BB",u"\u13BC",u"\u13BD",u"\u13BE",
                u"\u13BF",u"\u13C0",u"\u13C1",u"\u13C2",u"\u13C3",u"\u13C4",
                u"\u13C5"],
        ],
            "LIQUID" : [
            [u"\u13B3",u"\u13B4",u"\u13B5",u"\u13B6",u"\u13B7",u"\u13B8",
                u"\u13DC",u"\u13DD",u"\u13DE",u"\u13DF",u"\u13E0",u"\u13E1",
                u"\u13E2"],
        ],
            "POA" : [
            [u"\u13CC",u"\u13CD",u"\u13CE",u"\u13CF",u"\u13D0",u"\u13D1",
                u"\u13D3",u"\u13D4",u"\u13D5",u"\u13D6",u"\u13D7",u"\u13D8",
                u"\u13D9",u"\u13DA",u"\u13E3",u"\u13E4",u"\u13E5",u"\u13E6",
                u"\u13E7"],
            [u"\u13A5",u"\u13AC",u"\u13B2",u"\u13CB",u"\u13D2",u"\u13DB",
                u"\u13E8",u"\u13EE",u"\u13F4"],
            [u"\u13A6",u"\u13A7",u"\u13A8",u"\u13A9",u"\u13AA",u"\u13AB"],
            [u"\u13C6",u"\u13C7",u"\u13C8",u"\u13C9",u"\u13CA"],
        ],
            "ASP" : [
            [u"\u13A5",u"\u13B2"],
        ],
        },
        "COPTIC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u03EB",u"\u2C99",u"\u2C9B"],
        ],
            "LIQUID" : [
            [u"\u2C81",u"\u2C87",u"\u2C97",u"\u2CA3"],
        ],
            "POA" : [
            [u"\u03E3",u"\u03ED",u"\u03EF",u"\u2C8B",u"\u2C8D",u"\u2C91",
                u"\u2C93",u"\u2C9D",u"\u2CA5",u"\u2CA7",u"\u2CC1"],
            [u"\u03E5",u"\u2C83",u"\u2CAB"],
            [u"\u03E7",u"\u2C85",u"\u2C95",u"\u2CAD"],
            [u"\u2CA1",u"\u2CAF"],
        ],
            "ASP" : [
            [u"\u03ED",u"\u2CA5"],
        ],
        },
        "CYRILLIC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [
            [u"\u0401",u"\u0438"],
        ],
            "NASAL" : [
            [u"\u040A",u"\u043D",u"\uA65F"],
        ],
            "LIQUID" : [
            [u"\u0409",u"\u043B",u"\uA641",u"\uA643"],
        ],
            "POA" : [
            [u"\u0402",u"\u0405",u"\u040B",u"\u040F",u"\u0434",u"\u0436",
                u"\u0437",u"\u0441",u"\u0442",u"\u0446",u"\u0448",u"\u0449"],
            [u"\u0432",u"\uA649"],
            [u"\u0403",u"\u040C",u"\u0433",u"\u043A"],
            [u"\u0408",u"\u0447"],
            [u"\u0431",u"\u043F"],
        ],
            "ASP" : [
            [u"\u040B",u"\u0446"],
            [u"\u0436",u"\u0437"],
            [u"\u0405",u"\u040F"],
        ],
        },
        "DEVANAGARI": {
            "VOW_LEN" : [
            [u"\u0907",u"\u0908"],
            [u"\u0909",u"\u090A"],
            [u"\u0905",u"\u0906"],
        ],
            "VOW_GLIDE" : [
            [u"\u0905",u"\u0910"],
        ],
            "NASAL" : [
            [u"\u0919",u"\u091E",u"\u0923",u"\u0928",u"\u092E"],
        ],
            "LIQUID" : [
            [u"\u0930",u"\u0932"],
        ],
            "POA" : [
            [u"\u091F",u"\u0920",u"\u0921",u"\u0922",u"\u0924",u"\u0925",
                u"\u0926",u"\u0927",u"\u0936",u"\u0937",u"\u0938"],
            [u"\u0935"],
            [u"\u0915",u"\u0916",u"\u0917",u"\u0918"],
            [u"\u091A",u"\u091B",u"\u091C",u"\u091D"],
            [u"\u092A",u"\u092B",u"\u092C",u"\u092D"],
        ],
            "ASP" : [
            [u"\u091A",u"\u091B"],
            [u"\u092C",u"\u092D"],
            [u"\u0915",u"\u0916"],
            [u"\u092A",u"\u092B"],
            [u"\u0936",u"\u0938"],
            [u"\u091F",u"\u0920"],
            [u"\u0921",u"\u0922"],
            [u"\u0924",u"\u0925"],
            [u"\u0917",u"\u0918"],
            [u"\u0926",u"\u0927"],
            [u"\u091C",u"\u091D"],
        ],
        },
        "GEORGIAN": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u10D0",u"\u10D1",u"\u10D2",u"\u10D3",u"\u10D4",u"\u10D5",
                u"\u10D6",u"\u10D7",u"\u10D8",u"\u10D9",u"\u10DB",u"\u10DC",
                u"\u10DD",u"\u10E1",u"\u10E3",u"\u10E6",u"\u10E8",u"\u10E9",
                u"\u10EA",u"\u10EE",u"\u10EF",u"\u10F7",u"\u10FA"],
        ],
            "LIQUID" : [
            [u"\u10DA",u"\u10E0",u"\u10EB",u"\u10EC",u"\u10F8"],
        ],
            "POA" : [
            [u"\u10DF",u"\u10E2"],
            [u"\u10F6"],
            [u"\u10E5"],
            [u"\u10ED"],
            [u"\u10E7"],
            [u"\u10DE",u"\u10E4"],
        ],
            "ASP" : [
            [u"\u10DE",u"\u10E4"],
        ],
        },
        "GLAGOLITIC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u2C3F",u"\u2C40",u"\u2C41"],
        ],
            "LIQUID" : [
            [u"\u2C33",u"\u2C37",u"\u2C38",u"\u2C3E",u"\u2C43",u"\u2C44"],
        ],
            "POA" : [
            [u"\u2C30",u"\u2C35",u"\u2C39",u"\u2C4B",u"\u2C4C",u"\u2C4E",
                u"\u2C5B",u"\u2C5C"],
            [u"\u2C32",u"\u2C36",u"\u2C3C",u"\u2C45",u"\u2C47",u"\u2C4D",
                u"\u2C5A"],
            [u"\u2C3D"],
            [u"\u2C31",u"\u2C34",u"\u2C42",u"\u2C4A"],
        ],
            "ASP" : [],
        },
        "GREEK": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u03BC",u"\u03BD"],
        ],
            "LIQUID" : [
            [u"\u03B4",u"\u03BB",u"\u03C1"],
        ],
            "POA" : [
            [u"\u03C3",u"\u03C4"],
            [u"\u03B3",u"\u03BA",u"\u03BE"],
            [u"\u03C7"],
            [u"\u03C0",u"\u03C6",u"\u03C8"],
        ],
            "ASP" : [
            [u"\u03C0",u"\u03C6"],
        ],
        },
        "GUJARATI": {
            "VOW_LEN" : [
            [u"\u0A85",u"\u0A86"],
            [u"\u0A89",u"\u0A8A"],
            [u"\u0A87",u"\u0A88"],
        ],
            "VOW_GLIDE" : [
            [u"\u0A85",u"\u0A90"],
        ],
            "NASAL" : [
            [u"\u0A99",u"\u0A9E",u"\u0AA3",u"\u0AA8",u"\u0AAE"],
        ],
            "LIQUID" : [
            [u"\u0AB0",u"\u0AB2",u"\u0AB3"],
        ],
            "POA" : [
            [u"\u0A9F",u"\u0AA0",u"\u0AA1",u"\u0AA2",u"\u0AA4",u"\u0AA5",
                u"\u0AA6",u"\u0AA7",u"\u0AB6",u"\u0AB7",u"\u0AB8"],
            [u"\u0AB5"],
            [u"\u0A95",u"\u0A96",u"\u0A97",u"\u0A98"],
            [u"\u0A9A",u"\u0A9B",u"\u0A9C",u"\u0A9D"],
            [u"\u0AAA",u"\u0AAB",u"\u0AAC",u"\u0AAD"],
        ],
            "ASP" : [
            [u"\u0A95",u"\u0A96"],
            [u"\u0A9A",u"\u0A9B"],
            [u"\u0AA4",u"\u0AA5"],
            [u"\u0AAA",u"\u0AAB"],
            [u"\u0AB6",u"\u0AB8"],
            [u"\u0A9C",u"\u0A9D"],
            [u"\u0AA6",u"\u0AA7"],
            [u"\u0A9F",u"\u0AA0"],
            [u"\u0A97",u"\u0A98"],
            [u"\u0AA1",u"\u0AA2"],
            [u"\u0AAC",u"\u0AAD"],
        ],
        },
        "GURMUKHI": {
            "VOW_LEN" : [
            [u"\u0A09",u"\u0A0A"],
            [u"\u0A07",u"\u0A08"],
            [u"\u0A05",u"\u0A06"],
        ],
            "VOW_GLIDE" : [
            [u"\u0A05",u"\u0A10"],
        ],
            "NASAL" : [
            [u"\u0A19",u"\u0A1E",u"\u0A23",u"\u0A28",u"\u0A2E"],
        ],
            "LIQUID" : [
            [u"\u0A30",u"\u0A32",u"\u0A33"],
        ],
            "POA" : [
            [u"\u0A1F",u"\u0A20",u"\u0A21",u"\u0A22",u"\u0A24",u"\u0A25",
                u"\u0A26",u"\u0A27",u"\u0A36",u"\u0A38"],
            [u"\u0A35"],
            [u"\u0A15",u"\u0A16",u"\u0A17",u"\u0A18"],
            [u"\u0A1A",u"\u0A1B",u"\u0A1C",u"\u0A1D"],
            [u"\u0A2A",u"\u0A2B",u"\u0A2C",u"\u0A2D"],
        ],
            "ASP" : [
            [u"\u0A1A",u"\u0A1B"],
            [u"\u0A2C",u"\u0A2D"],
            [u"\u0A36",u"\u0A38"],
            [u"\u0A24",u"\u0A25"],
            [u"\u0A15",u"\u0A16"],
            [u"\u0A21",u"\u0A22"],
            [u"\u0A1F",u"\u0A20"],
            [u"\u0A1C",u"\u0A1D"],
            [u"\u0A2A",u"\u0A2B"],
            [u"\u0A26",u"\u0A27"],
            [u"\u0A17",u"\u0A18"],
        ],
        },
        "HANGUL": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [
            [u"\u3157",u"\u315A"],
            [u"\u3153",u"\u3154",u"\u3161"],
            [u"\u314F",u"\u3150"],
        ],
            "NASAL" : [
            [u"\u3132",u"\u3134",u"\u3138",u"\u3141",u"\u3143",u"\u3146",
                u"\u3147",u"\u3149"],
        ],
            "LIQUID" : [
            [u"\u3139"],
        ],
            "POA" : [
            [u"\u3137",u"\u3145",u"\u314C"],
            [u"\u3131",u"\u314B"],
            [u"\u3148",u"\u314A"],
            [u"\u3142",u"\u314D"],
        ],
            "ASP" : [
            [u"\u3148",u"\u314A"],
            [u"\u3142",u"\u314D"],
        ],
        },
        "HANUNOO": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1725",u"\u1728",u"\u172B"],
        ],
            "LIQUID" : [
            [u"\u172D",u"\u172E"],
        ],
            "POA" : [
            [u"\u1726",u"\u1727",u"\u1730"],
            [u"\u1723",u"\u1724"],
            [u"\u1729",u"\u172A"],
        ],
            "ASP" : [],
        },
        "HEBREW": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u05D6",u"\u05DE",u"\u05E0",u"\u05E2",u"\u05E9"],
        ],
            "LIQUID" : [
            [u"\u05D0",u"\u05D2",u"\u05D3",u"\u05DC",u"\u05E8"],
        ],
            "POA" : [
            [u"\u05D8",u"\u05D9",u"\u05E1",u"\u05E6"],
            [u"\u05D5",u"\u05EA"],
            [u"\u05DB"],
            [u"\u05E7"],
            [u"\u05D1",u"\u05E4"],
        ],
            "ASP" : [],
        },
        "HIRAGANA": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u306A",u"\u306B",u"\u306C",u"\u306D",u"\u306E",u"\u307E",
                u"\u307F",u"\u3080",u"\u3081",u"\u3082",u"\u3093"],
        ],
            "LIQUID" : [
            [u"\u3089",u"\u308A",u"\u308B",u"\u308C",u"\u308D"],
        ],
            "POA" : [
            [u"\u3055",u"\u3056",u"\u3057",u"\u3058",u"\u3059",u"\u305A",
                u"\u305B",u"\u305C",u"\u305D",u"\u305E",u"\u305F",u"\u3060",
                u"\u3061",u"\u3062",u"\u3064",u"\u3065",u"\u3066",u"\u3067",
                u"\u3068",u"\u3069"],
            [u"\u3094"],
            [u"\u304B",u"\u304C",u"\u304D",u"\u304E",u"\u304F",u"\u3050",
                u"\u3051",u"\u3052",u"\u3053",u"\u3054"],
            [u"\u3070",u"\u3071",u"\u3073",u"\u3074",u"\u3076",u"\u3077",
                u"\u3079",u"\u307A",u"\u307C",u"\u307D"],
        ],
            "ASP" : [],
        },
        "JAVANESE": {
            "VOW_LEN" : [
            [u"\uA986",u"\uA987"],
        ],
            "VOW_GLIDE" : [
            [u"\uA984",u"\uA98D"],
        ],
            "NASAL" : [
            [u"\uA994",u"\uA99A",u"\uA9A4",u"\uA9A9"],
        ],
            "LIQUID" : [
            [u"\uA9AB",u"\uA9AD"],
        ],
            "POA" : [
            [u"\uA99B",u"\uA99D",u"\uA9A0",u"\uA9A2",u"\uA9B1"],
            [u"\uA98F",u"\uA992"],
            [u"\uA995",u"\uA997"],
            [u"\uA9A5",u"\uA9A7"],
        ],
            "ASP" : [],
        },
        "KANNADA": {
            "VOW_LEN" : [
            [u"\u0C87",u"\u0C88"],
            [u"\u0C85",u"\u0C86"],
            [u"\u0C8E",u"\u0C8F"],
            [u"\u0C89",u"\u0C8A"],
            [u"\u0C92",u"\u0C93"],
        ],
            "VOW_GLIDE" : [
            [u"\u0C85",u"\u0C90"],
        ],
            "NASAL" : [
            [u"\u0C99",u"\u0C9E",u"\u0CA3",u"\u0CA8",u"\u0CAE"],
        ],
            "LIQUID" : [
            [u"\u0CB0",u"\u0CB1",u"\u0CB2",u"\u0CB3"],
        ],
            "POA" : [
            [u"\u0C9F",u"\u0CA0",u"\u0CA1",u"\u0CA2",u"\u0CA4",u"\u0CA5",
                u"\u0CA6",u"\u0CA7",u"\u0CB6",u"\u0CB7",u"\u0CB8"],
            [u"\u0CB5"],
            [u"\u0C95",u"\u0C96",u"\u0C97",u"\u0C98"],
            [u"\u0C9A",u"\u0C9B",u"\u0C9C",u"\u0C9D"],
            [u"\u0CAA",u"\u0CAB",u"\u0CAC",u"\u0CAD"],
        ],
            "ASP" : [
            [u"\u0CB6",u"\u0CB8"],
            [u"\u0CA6",u"\u0CA7"],
            [u"\u0C95",u"\u0C96"],
            [u"\u0C97",u"\u0C98"],
            [u"\u0C9F",u"\u0CA0"],
            [u"\u0CAA",u"\u0CAB"],
            [u"\u0CA1",u"\u0CA2"],
            [u"\u0CA4",u"\u0CA5"],
            [u"\u0C9C",u"\u0C9D"],
            [u"\u0CAC",u"\u0CAD"],
            [u"\u0C9A",u"\u0C9B"],
        ],
        },
        "KATAKANA": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u30CA",u"\u30CB",u"\u30CC",u"\u30CD",u"\u30CE",u"\u30DE",
                u"\u30DF",u"\u30E0",u"\u30E1",u"\u30E2",u"\u30F3"],
        ],
            "LIQUID" : [
            [u"\u30E9",u"\u30EA",u"\u30EB",u"\u30EC",u"\u30ED"],
        ],
            "POA" : [
            [u"\u30B5",u"\u30B6",u"\u30B7",u"\u30B8",u"\u30B9",u"\u30BA",
                u"\u30BB",u"\u30BC",u"\u30BD",u"\u30BE",u"\u30BF",u"\u30C0",
                u"\u30C1",u"\u30C2",u"\u30C4",u"\u30C5",u"\u30C6",u"\u30C7",
                u"\u30C8",u"\u30C9"],
            [u"\u30F4",u"\u30F7",u"\u30F8",u"\u30F9",u"\u30FA"],
            [u"\u30AB",u"\u30AC",u"\u30AD",u"\u30AE",u"\u30AF",u"\u30B0",
                u"\u30B1",u"\u30B2",u"\u30B3",u"\u30B4"],
            [u"\u30D0",u"\u30D1",u"\u30D3",u"\u30D4",u"\u30D6",u"\u30D7",
                u"\u30D9",u"\u30DA",u"\u30DC",u"\u30DD"],
        ],
            "ASP" : [],
        },
        "KHMER": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1784",u"\u1789",u"\u178E",u"\u1793",u"\u1798"],
        ],
            "LIQUID" : [
            [u"\u179A",u"\u179B",u"\u17A1"],
        ],
            "POA" : [
            [u"\u178A",u"\u178B",u"\u178C",u"\u178D",u"\u178F",u"\u1790",
                u"\u1791",u"\u1792",u"\u179D",u"\u179E",u"\u179F"],
            [u"\u179C"],
            [u"\u1780",u"\u1781",u"\u1782",u"\u1783"],
            [u"\u1785",u"\u1786",u"\u1787",u"\u1788"],
            [u"\u17A2"],
            [u"\u1794",u"\u1795",u"\u1796",u"\u1797"],
        ],
            "ASP" : [
            [u"\u1787",u"\u1788"],
            [u"\u179D",u"\u179F"],
            [u"\u1782",u"\u1783"],
            [u"\u178F",u"\u1790"],
            [u"\u1796",u"\u1797"],
            [u"\u1785",u"\u1786"],
            [u"\u1780",u"\u1781"],
            [u"\u1791",u"\u1792"],
        ],
        },
        "LAO": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0E87",u"\u0E8D",u"\u0E99",u"\u0EA1"],
        ],
            "LIQUID" : [],
            "POA" : [
            [u"\u0E94",u"\u0E95"],
            [u"\u0E81"],
            [u"\u0E88"],
            [u"\u0E9A",u"\u0E9B"],
        ],
            "ASP" : [],
        },
        "LATIN": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u006D",u"\u006E"],
        ],
            "LIQUID" : [
            [u"\u006C",u"\u0072"],
        ],
            "POA" : [
            [u"\u0064",u"\u0073",u"\u0074",u"\u007A"],
            [u"\u0066",u"\u0076"],
            [u"\u0067",u"\u006B",u"\u0078"],
            [u"\u0063",u"\u006A"],
            [u"\u0071"],
            [u"\u0062",u"\u0070"],
        ],
            "ASP" : [],
        },
        "LEPCHA": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1C05",u"\u1C09",u"\u1C0D",u"\u1C15",u"\u1C16"],
        ],
            "LIQUID" : [
            [u"\u1C01",u"\u1C04",u"\u1C0F",u"\u1C12",u"\u1C14",u"\u1C1B",
                u"\u1C1C",u"\u1C1E"],
        ],
            "POA" : [
            [u"\u1C0A",u"\u1C0B",u"\u1C0C",u"\u1C17",u"\u1C18",u"\u1C19",
                u"\u1C20",u"\u1C21",u"\u1C4D",u"\u1C4E",u"\u1C4F"],
            [u"\u1C11",u"\u1C1F"],
            [u"\u1C00",u"\u1C02",u"\u1C03"],
            [u"\u1C06",u"\u1C07",u"\u1C08"],
            [u"\u1C0E",u"\u1C10",u"\u1C13"],
        ],
            "ASP" : [
            [u"\u1C06",u"\u1C07"],
            [u"\u1C20",u"\u1C21"],
            [u"\u1C17",u"\u1C18"],
            [u"\u1C0E",u"\u1C10"],
            [u"\u1C0A",u"\u1C0B"],
            [u"\u1C00",u"\u1C02"],
            [u"\u1C4D",u"\u1C4E"],
        ],
        },
        "LIMBU": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u190A",u"\u1931",u"\u1932",u"\u1934",u"\u1936"],
        ],
            "LIQUID" : [
            [u"\u1937",u"\u1938"],
        ],
            "POA" : [
            [u"\u190C",u"\u190D",u"\u190E",u"\u1919",u"\u191A",u"\u191B",
                u"\u1933"],
            [u"\u1902",u"\u1903",u"\u1904",u"\u1930"],
            [u"\u1906",u"\u1907",u"\u1908",u"\u1909"],
            [u"\u1911",u"\u1912",u"\u1913",u"\u1935"],
        ],
            "ASP" : [
            [u"\u1912",u"\u1913"],
            [u"\u1908",u"\u1909"],
            [u"\u1911",u"\u1935"],
            [u"\u1903",u"\u1904"],
            [u"\u1906",u"\u1907"],
            [u"\u1919",u"\u191B"],
            [u"\u1902",u"\u1930"],
            [u"\u190C",u"\u1933"],
            [u"\u190D",u"\u190E"],
        ],
        },
        "LISU": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [
            [u"\uA4F0",u"\uA4F1"],
            [u"\uA4F4",u"\uA4F5"],
            [u"\uA4EE",u"\uA4EF"],
            [u"\uA4F3",u"\uA4F7"],
        ],
            "NASAL" : [
            [u"\uA4DF",u"\uA4E0",u"\uA4E5"],
        ],
            "LIQUID" : [
            [u"\uA4E1"],
        ],
            "POA" : [
            [u"\uA4D3",u"\uA4D4",u"\uA4D5",u"\uA4DC",u"\uA4DD",u"\uA4DE",
                u"\uA4E2",u"\uA4E3",u"\uA4E4",u"\uA4EB"],
            [u"\uA4E9"],
            [u"\uA4D6",u"\uA4D7",u"\uA4D8",u"\uA4E7",u"\uA4ED"],
            [u"\uA4D9",u"\uA4DA",u"\uA4DB"],
            [u"\uA4D0",u"\uA4D1",u"\uA4D2"],
        ],
            "ASP" : [
            [u"\uA4DD",u"\uA4DE"],
            [u"\uA4D7",u"\uA4D8"],
            [u"\uA4D4",u"\uA4D5"],
            [u"\uA4D1",u"\uA4D2"],
            [u"\uA4E3",u"\uA4E4"],
            [u"\uA4E2",u"\uA4EB"],
            [u"\uA4D6",u"\uA4ED"],
            [u"\uA4DA",u"\uA4DB"],
        ],
        },
        "MALAYALAM": {
            "VOW_LEN" : [
            [u"\u0D09",u"\u0D0A"],
            [u"\u0D05",u"\u0D06"],
            [u"\u0D07",u"\u0D08"],
            [u"\u0D12",u"\u0D13"],
            [u"\u0D0E",u"\u0D0F"],
        ],
            "VOW_GLIDE" : [
            [u"\u0D05",u"\u0D10"],
        ],
            "NASAL" : [
            [u"\u0D19",u"\u0D1E",u"\u0D23",u"\u0D28",u"\u0D2E"],
        ],
            "LIQUID" : [
            [u"\u0D30",u"\u0D31",u"\u0D32",u"\u0D33",u"\u0D34"],
        ],
            "POA" : [
            [u"\u0D1F",u"\u0D20",u"\u0D21",u"\u0D22",u"\u0D24",u"\u0D25",
                u"\u0D26",u"\u0D27",u"\u0D36",u"\u0D37",u"\u0D38"],
            [u"\u0D35"],
            [u"\u0D15",u"\u0D16",u"\u0D17",u"\u0D18"],
            [u"\u0D1A",u"\u0D1B",u"\u0D1C",u"\u0D1D"],
            [u"\u0D2A",u"\u0D2B",u"\u0D2C",u"\u0D2D"],
        ],
            "ASP" : [
            [u"\u0D1A",u"\u0D1B"],
            [u"\u0D17",u"\u0D18"],
            [u"\u0D1F",u"\u0D20"],
            [u"\u0D2A",u"\u0D2B"],
            [u"\u0D36",u"\u0D38"],
            [u"\u0D26",u"\u0D27"],
            [u"\u0D24",u"\u0D25"],
            [u"\u0D2C",u"\u0D2D"],
            [u"\u0D1C",u"\u0D1D"],
            [u"\u0D21",u"\u0D22"],
            [u"\u0D15",u"\u0D16"],
        ],
        },
        "MANDAIC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0845",u"\u084D",u"\u084F",u"\u0856",u"\u0858"],
        ],
            "LIQUID" : [
            [u"\u0840",u"\u084B"],
        ],
            "POA" : [
            [u"\u0843",u"\u0846",u"\u0849",u"\u084E",u"\u0851",u"\u0854",
                u"\u0857"],
            [u"\u0842"],
        ],
            "ASP" : [
            [u"\u084E",u"\u0854"],
        ],
        },
        "MODIFIER": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u02C9",u"\u02EC",u"\u02ED",u"\uA789"],
        ],
            "LIQUID" : [
            [u"\u02FD"],
        ],
            "POA" : [
            [u"\u02BC",u"\uA770"],
            [u"\u02B9"],
        ],
            "ASP" : [],
        },
        "MONGOLIAN": {
            "VOW_LEN" : [
            [u"\u1821",u"\u1827"],
        ],
            "VOW_GLIDE" : [
            [u"\u1824",u"\u1826"],
            [u"\u1823",u"\u1825"],
        ],
            "NASAL" : [
            [u"\u1828",u"\u1829",u"\u182E"],
        ],
            "LIQUID" : [
            [u"\u182F",u"\u1837",u"\u1840"],
        ],
            "POA" : [
            [u"\u1830",u"\u1831",u"\u1832",u"\u1833",u"\u183C",u"\u183D",
                u"\u183F",u"\u1841"],
            [u"\u1839"],
            [u"\u182D",u"\u183A",u"\u183B"],
            [u"\u1834",u"\u1835",u"\u1842"],
            [u"\u182C"],
            [u"\u182A",u"\u182B"],
        ],
            "ASP" : [
            [u"\u183A",u"\u183B"],
            [u"\u1830",u"\u1831"],
        ],
        },
        "MYANMAR": {
            "VOW_LEN" : [
            [u"\u1023",u"\u1024"],
            [u"\u1025",u"\u1026"],
        ],
            "VOW_GLIDE" : [
            [u"\u1021",u"\u102A"],
        ],
            "NASAL" : [
            [u"\u1004",u"\u1009",u"\u100A",u"\u100F",u"\u1014",u"\u1019"],
        ],
            "LIQUID" : [
            [u"\u101B",u"\u101C",u"\u1020"],
        ],
            "POA" : [
            [u"\u100B",u"\u100C",u"\u100D",u"\u100E",u"\u1010",u"\u1011",
                u"\u1012",u"\u1013",u"\u101E",u"\u1050",u"\u1051"],
            [u"\u1000",u"\u1001",u"\u1002",u"\u1003"],
            [u"\u1005",u"\u1006",u"\u1007",u"\u1008"],
            [u"\u1015",u"\u1016",u"\u1017",u"\u1018"],
        ],
            "ASP" : [
            [u"\u1002",u"\u1003"],
            [u"\u1007",u"\u1008"],
            [u"\u1005",u"\u1006"],
            [u"\u1012",u"\u1013"],
            [u"\u100B",u"\u100C"],
            [u"\u1015",u"\u1016"],
            [u"\u1010",u"\u1011"],
            [u"\u1017",u"\u1018"],
            [u"\u100D",u"\u100E"],
            [u"\u101E",u"\u1050"],
            [u"\u1000",u"\u1001"],
        ],
        },
        "NKO": {
            "VOW_LEN" : [
            [u"\u07CB",u"\u07CD"],
            [u"\u07CF",u"\u07D0"],
        ],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u07D1",u"\u07D2",u"\u07E1",u"\u07E2",u"\u07E3"],
        ],
            "LIQUID" : [
            [u"\u07D9",u"\u07DA",u"\u07DF"],
        ],
            "POA" : [
            [u"\u07D5",u"\u07D8",u"\u07DB"],
            [u"\u07DD"],
            [u"\u07DE"],
            [u"\u07D6",u"\u07D7"],
            [u"\u07D3",u"\u07D4",u"\u07DC"],
        ],
            "ASP" : [],
        },
        "OGHAM": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1683",u"\u1685",u"\u1688",u"\u168B",u"\u168D",u"\u1691",
                u"\u1697",u"\u1698",u"\u1699"],
        ],
            "LIQUID" : [
            [u"\u1682",u"\u1684",u"\u1689",u"\u168F",u"\u1690"],
        ],
            "POA" : [
            [u"\u1687",u"\u168E",u"\u1693",u"\u1694"],
            [u"\u168C"],
            [u"\u168A"],
            [u"\u1681",u"\u1695",u"\u169A"],
        ],
            "ASP" : [],
        },
        "ORIYA": {
            "VOW_LEN" : [
            [u"\u0B05",u"\u0B06"],
            [u"\u0B07",u"\u0B08"],
            [u"\u0B09",u"\u0B0A"],
        ],
            "VOW_GLIDE" : [
            [u"\u0B05",u"\u0B10"],
        ],
            "NASAL" : [
            [u"\u0B19",u"\u0B1E",u"\u0B23",u"\u0B28",u"\u0B2E"],
        ],
            "LIQUID" : [
            [u"\u0B30",u"\u0B32",u"\u0B33"],
        ],
            "POA" : [
            [u"\u0B1F",u"\u0B20",u"\u0B21",u"\u0B22",u"\u0B24",u"\u0B25",
                u"\u0B26",u"\u0B27",u"\u0B36",u"\u0B37",u"\u0B38"],
            [u"\u0B35"],
            [u"\u0B15",u"\u0B16",u"\u0B17",u"\u0B18"],
            [u"\u0B1A",u"\u0B1B",u"\u0B1C",u"\u0B1D"],
            [u"\u0B2A",u"\u0B2B",u"\u0B2C",u"\u0B2D"],
        ],
            "ASP" : [
            [u"\u0B2A",u"\u0B2B"],
            [u"\u0B36",u"\u0B38"],
            [u"\u0B1A",u"\u0B1B"],
            [u"\u0B21",u"\u0B22"],
            [u"\u0B26",u"\u0B27"],
            [u"\u0B24",u"\u0B25"],
            [u"\u0B1C",u"\u0B1D"],
            [u"\u0B17",u"\u0B18"],
            [u"\u0B2C",u"\u0B2D"],
            [u"\u0B15",u"\u0B16"],
            [u"\u0B1F",u"\u0B20"],
        ],
        },
        "REJANG": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\uA932",u"\uA935",u"\uA938",u"\uA93B",u"\uA942",u"\uA943",
                u"\uA944",u"\uA945"],
        ],
            "LIQUID" : [
            [u"\uA93D",u"\uA93E"],
        ],
            "POA" : [
            [u"\uA933",u"\uA934",u"\uA93C"],
            [u"\uA930",u"\uA931"],
            [u"\uA939",u"\uA93A"],
            [u"\uA936",u"\uA937"],
        ],
            "ASP" : [],
        },
        "RUNIC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [
            [u"\u16AE",u"\u16AF"],
        ],
            "NASAL" : [
            [u"\u16B0",u"\u16B2",u"\u16B3",u"\u16B6",u"\u16DC",u"\u16DD",
                u"\u16E5"],
        ],
            "LIQUID" : [
            [u"\u16E3",u"\u16E4"],
        ],
            "POA" : [
            [u"\u16AB",u"\u16CE",u"\u16D1"],
            [u"\u16A1"],
            [u"\u16B5",u"\u16B8",u"\u16C4",u"\u16EA"],
            [u"\u16CD",u"\u16E2"],
            [u"\u16E9"],
        ],
            "ASP" : [],
        },
        "SAMARITAN": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0802",u"\u0806",u"\u080C",u"\u080D",u"\u080E",u"\u080F",
                u"\u0814"],
        ],
            "LIQUID" : [
            [u"\u0800",u"\u0803",u"\u080B",u"\u0813"],
        ],
            "POA" : [
            [u"\u0808",u"\u0811",u"\u0815"],
            [u"\u0810"],
            [u"\u080A"],
            [u"\u0812"],
            [u"\u0801",u"\u0805"],
        ],
            "ASP" : [],
        },
        "SAURASHTRA": {
            "VOW_LEN" : [
            [u"\uA884",u"\uA885"],
            [u"\uA88C",u"\uA88D"],
            [u"\uA886",u"\uA887"],
            [u"\uA882",u"\uA883"],
            [u"\uA88F",u"\uA890"],
        ],
            "VOW_GLIDE" : [
            [u"\uA882",u"\uA88E"],
        ],
            "NASAL" : [
            [u"\uA896",u"\uA89B",u"\uA8A0",u"\uA8A5",u"\uA8AA"],
        ],
            "LIQUID" : [
            [u"\uA8AC",u"\uA8AD",u"\uA8B3"],
        ],
            "POA" : [
            [u"\uA89C",u"\uA89D",u"\uA89E",u"\uA89F",u"\uA8A1",u"\uA8A2",
                u"\uA8A3",u"\uA8A4",u"\uA8AF",u"\uA8B0",u"\uA8B1"],
            [u"\uA8AE"],
            [u"\uA892",u"\uA893",u"\uA894",u"\uA895"],
            [u"\uA897",u"\uA898",u"\uA899",u"\uA89A"],
            [u"\uA8A6",u"\uA8A7",u"\uA8A8",u"\uA8A9"],
        ],
            "ASP" : [
            [u"\uA8A8",u"\uA8A9"],
            [u"\uA897",u"\uA898"],
            [u"\uA892",u"\uA893"],
            [u"\uA8A6",u"\uA8A7"],
            [u"\uA8A1",u"\uA8A2"],
            [u"\uA8A3",u"\uA8A4"],
            [u"\uA89E",u"\uA89F"],
            [u"\uA8AF",u"\uA8B1"],
            [u"\uA894",u"\uA895"],
            [u"\uA89C",u"\uA89D"],
            [u"\uA899",u"\uA89A"],
        ],
        },
        "SINHALA": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0D85",u"\u0D86",u"\u0D87",u"\u0D88",u"\u0D89",u"\u0D8A",
                u"\u0D8B",u"\u0D8C",u"\u0D8D",u"\u0D8E",u"\u0D8F",u"\u0D90",
                u"\u0D91",u"\u0D92",u"\u0D93",u"\u0D94",u"\u0D95",u"\u0D96",
                u"\u0D9E",u"\u0DB3",u"\u0DB6",u"\u0DB7",u"\u0DB8",u"\u0DBA",
                u"\u0DBB",u"\u0DC0",u"\u0DC3",u"\u0DC4",u"\u0DC5",u"\u0DC6"],
        ],
            "LIQUID" : [
            [u"\u0DC1"],
        ],
            "POA" : [
            [u"\u0DB9"],
        ],
            "ASP" : [],
        },
        "SUNDANESE": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [
            [u"\u1B88",u"\u1B89"],
            [u"\u1B83",u"\u1B86"],
        ],
            "NASAL" : [
            [u"\u1B8D",u"\u1B91",u"\u1B94",u"\u1B99"],
        ],
            "LIQUID" : [
            [u"\u1B9B",u"\u1B9C"],
        ],
            "POA" : [
            [u"\u1B90",u"\u1B92",u"\u1B93",u"\u1B9E",u"\u1BAF"],
            [u"\u1B96",u"\u1B97"],
            [u"\u1B8A",u"\u1B8C",u"\u1B9F",u"\u1BAE"],
            [u"\u1B8E",u"\u1B8F"],
            [u"\u1B8B"],
            [u"\u1B95",u"\u1B98"],
        ],
            "ASP" : [
            [u"\u1B8A",u"\u1BAE"],
        ],
        },
        "SYRIAC": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0719",u"\u0721",u"\u0722",u"\u072B"],
        ],
            "LIQUID" : [
            [u"\u0710",u"\u0713",u"\u0715",u"\u0720",u"\u072A"],
        ],
            "POA" : [
            [u"\u071B",u"\u071D",u"\u0724",u"\u0728",u"\u072C"],
            [u"\u071F"],
            [u"\u0729"],
            [u"\u0712",u"\u0726"],
        ],
            "ASP" : [],
        },
        "TAGALOG": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1705",u"\u1708",u"\u170B"],
        ],
            "LIQUID" : [
            [u"\u170E"],
        ],
            "POA" : [
            [u"\u1706",u"\u1707",u"\u1710"],
            [u"\u1703",u"\u1704"],
            [u"\u1709",u"\u170A"],
        ],
            "ASP" : [],
        },
        "TAGBANWA": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u1765",u"\u1768",u"\u176B"],
        ],
            "LIQUID" : [
            [u"\u176E"],
        ],
            "POA" : [
            [u"\u1766",u"\u1767",u"\u1770"],
            [u"\u1763",u"\u1764"],
            [u"\u1769",u"\u176A"],
        ],
            "ASP" : [],
        },
        "TAMIL": {
            "VOW_LEN" : [
            [u"\u0B8E",u"\u0B8F"],
            [u"\u0B85",u"\u0B86"],
            [u"\u0B87",u"\u0B88"],
            [u"\u0B89",u"\u0B8A"],
            [u"\u0B92",u"\u0B93"],
        ],
            "VOW_GLIDE" : [
            [u"\u0B85",u"\u0B90"],
        ],
            "NASAL" : [
            [u"\u0B99",u"\u0B9E",u"\u0BA3",u"\u0BA8",u"\u0BA9",u"\u0BAE"],
        ],
            "LIQUID" : [
            [u"\u0BB0",u"\u0BB1",u"\u0BB2",u"\u0BB3",u"\u0BB4"],
        ],
            "POA" : [
            [u"\u0B9F",u"\u0BA4",u"\u0BB6",u"\u0BB7",u"\u0BB8"],
            [u"\u0BB5"],
            [u"\u0B95"],
            [u"\u0B9A",u"\u0B9C"],
            [u"\u0BAA"],
        ],
            "ASP" : [
            [u"\u0BB6",u"\u0BB8"],
        ],
        },
        "TELUGU": {
            "VOW_LEN" : [
            [u"\u0C0E",u"\u0C0F"],
            [u"\u0C05",u"\u0C06"],
            [u"\u0C07",u"\u0C08"],
            [u"\u0C12",u"\u0C13"],
            [u"\u0C09",u"\u0C0A"],
        ],
            "VOW_GLIDE" : [
            [u"\u0C05",u"\u0C10"],
        ],
            "NASAL" : [
            [u"\u0C19",u"\u0C1E",u"\u0C23",u"\u0C28",u"\u0C2E"],
        ],
            "LIQUID" : [
            [u"\u0C30",u"\u0C31",u"\u0C32",u"\u0C33"],
        ],
            "POA" : [
            [u"\u0C1F",u"\u0C20",u"\u0C21",u"\u0C22",u"\u0C24",u"\u0C25",
                u"\u0C26",u"\u0C27",u"\u0C36",u"\u0C37",u"\u0C38"],
            [u"\u0C35"],
            [u"\u0C15",u"\u0C16",u"\u0C17",u"\u0C18"],
            [u"\u0C1A",u"\u0C1B",u"\u0C1C",u"\u0C1D"],
            [u"\u0C2A",u"\u0C2B",u"\u0C2C",u"\u0C2D"],
        ],
            "ASP" : [
            [u"\u0C15",u"\u0C16"],
            [u"\u0C1F",u"\u0C20"],
            [u"\u0C26",u"\u0C27"],
            [u"\u0C24",u"\u0C25"],
            [u"\u0C17",u"\u0C18"],
            [u"\u0C2C",u"\u0C2D"],
            [u"\u0C21",u"\u0C22"],
            [u"\u0C36",u"\u0C38"],
            [u"\u0C2A",u"\u0C2B"],
            [u"\u0C1A",u"\u0C1B"],
            [u"\u0C1C",u"\u0C1D"],
        ],
        },
        "THAANA": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0781",u"\u0782",u"\u0785",u"\u0789",u"\u078F",u"\u0790",
                u"\u0791",u"\u0792",u"\u0793",u"\u0795",u"\u0796",u"\u0797",
                u"\u079D",u"\u07A2",u"\u07A3"],
        ],
            "LIQUID" : [
            [u"\u0783",u"\u0787",u"\u078B",u"\u078D",u"\u079B"],
        ],
            "POA" : [
            [u"\u078C",u"\u0798",u"\u079C",u"\u079E",u"\u079F",u"\u07A0",
                u"\u07A1"],
            [u"\u0788",u"\u078A",u"\u07A5"],
            [u"\u0786",u"\u078E",u"\u079A"],
            [u"\u07A4"],
            [u"\u0784"],
        ],
            "ASP" : [],
        },
        "TIBETAN": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u0F44",u"\u0F49",u"\u0F4E",u"\u0F53",u"\u0F58"],
        ],
            "LIQUID" : [
            [u"\u0F62",u"\u0F63",u"\u0F6C"],
        ],
            "POA" : [
            [u"\u0F4A",u"\u0F4B",u"\u0F4C",u"\u0F4D",u"\u0F4F",u"\u0F50",
                u"\u0F51",u"\u0F52",u"\u0F59",u"\u0F5A",u"\u0F5B",u"\u0F5C",
                u"\u0F5E",u"\u0F5F",u"\u0F64",u"\u0F65",u"\u0F66",u"\u0F69"],
            [u"\u0F40",u"\u0F41",u"\u0F42",u"\u0F43",u"\u0F6B"],
            [u"\u0F45",u"\u0F46",u"\u0F47"],
            [u"\u0F54",u"\u0F55",u"\u0F56",u"\u0F57"],
        ],
            "ASP" : [
            [u"\u0F45",u"\u0F46"],
            [u"\u0F64",u"\u0F66"],
            [u"\u0F5E",u"\u0F5F"],
            [u"\u0F40",u"\u0F41"],
            [u"\u0F59",u"\u0F5A"],
            [u"\u0F54",u"\u0F55"],
            [u"\u0F4C",u"\u0F4D"],
            [u"\u0F56",u"\u0F57"],
            [u"\u0F4F",u"\u0F50"],
            [u"\u0F4A",u"\u0F4B"],
            [u"\u0F5B",u"\u0F5C"],
            [u"\u0F42",u"\u0F43"],
            [u"\u0F51",u"\u0F52"],
        ],
        },
        "TIFINAGH": {
            "VOW_LEN" : [],
            "VOW_GLIDE" : [],
            "NASAL" : [
            [u"\u2D4F"],
        ],
            "LIQUID" : [
            [u"\u2D4D"],
        ],
            "POA" : [
            [u"\u2D37",u"\u2D38",u"\u2D39",u"\u2D3A",u"\u2D4A",u"\u2D59",
                u"\u2D5A",u"\u2D5B",u"\u2D63",u"\u2D65"],
            [u"\u2D60"],
            [u"\u2D33",u"\u2D34",u"\u2D56"],
            [u"\u2D5E"],
            [u"\u2D32"],
        ],
            "ASP" : [
            [u"\u2D5C",u"\u2D5D"],
            [u"\u2D4A",u"\u2D63"],
            [u"\u2D59",u"\u2D5B"],
            [u"\u2D33",u"\u2D34",u"\u2D56"],
            [u"\u2D37",u"\u2D38"],
            [u"\u2D3D",u"\u2D45"],
            [u"\u2D39",u"\u2D3A"],
        ],
        },
    }
#-------------------------------------------------------------------------------
# End of Letters.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of CCT_Writer.py
#-------------------------------------------------------------------------------


class CCT_Writer:

    def __init__(self, filepath):
        self.logger   = logging.getLogger("lingt.Access.CCTWriter")
        self.filepath = filepath

    def writeSimpleReplacements(self, dataList):
        """
        @param dataList:        List with rows containing two elements,
                                the old value and the new value.
        """
        self.logger.debug("writing SFM file")
        now = datetime.datetime.now()
        outfile = codecs.open(self.filepath, 'w', 'UTF8')
        header = (
"c CC Table generated by the OpenOffice.org Linguistic Tools" + os.linesep +
"c from spelling checker data."                               + os.linesep +
"c"                                                           + os.linesep +
"c This simple CCT makes changes to words in order to make"   + os.linesep +
"c spellings consistent.  It can be run as a converter in"    + os.linesep +
"c software such as Flex."                                    + os.linesep +
"c"                                                           + os.linesep +
"c Generated %s."                                             + os.linesep +
""                                                            + os.linesep +
"group(main)"                                                 + os.linesep
            ) % now.strftime("%d-%b-%Y")
        outfile.write(header)
        for rec in dataList:
            oldValue, newValue = rec
            outfile.write(('"%s" > "%s"' + os.linesep) % (oldValue, newValue))
        outfile.close()
        self.logger.debug("finished writing file")

    def writeComplete(self, dataList, markersToSearch):
        """
        @param dataList:        List with rows containing two elements.
        @param markersToSearch: String of space-separated backslash markers.
        """
        self.logger.debug("writing SFM file")
        outfile = codecs.open(self.filepath, 'w', 'UTF8')
        now = datetime.datetime.now()
        header = (
"c CC Table generated by the OpenOffice.org Linguistic Tools" + os.linesep +
"c from spelling checker data."                               + os.linesep +
"c"                                                           + os.linesep +
"c This CCT makes global changes to"                          + os.linesep +
"c a data file in order to make spellings consistent."        + os.linesep +
"c"                                                           + os.linesep +
"c Date generated: %s."                                       + os.linesep +
""                                                            + os.linesep +
"begin > store(punct) d32 d33 d34 d35 d36 d37 d38 d39 d40"    + os.linesep +
"                     d41 d42 d43 d44 d45 d46 d47 d58 d59"    + os.linesep +
"                     d60 d61 d62 d63 d64 d91 d92 d93 d94"    + os.linesep +
"                     d95 d96 d9  d11 nl endstore"            + os.linesep +
""                                                            + os.linesep +
"group(main)"                                                 + os.linesep
            ) % now.strftime("%d-%b-%Y")
        outfile.write(header)

        sfMarkerList = markersToSearch.split()
        for marker in sfMarkerList[:-1]:
            # all but the last marker should say "next"
            outfile.write(
                ('nl "%s " > next'                  + os.linesep) % (marker))
        if len(sfMarkerList) > 0:
            # the last marker contains the reference to look4changes
            marker = sfMarkerList[-1]
            outfile.write(
                ('nl "%s " > dup use(look4changes)' + os.linesep) % (marker))

        outfile.write(
"group(look4changes)"                                         + os.linesep +
"nl '\\' > dup back(2) use(main)"                             + os.linesep)

        for rec in dataList:
            oldValue, newValue = rec
            if not oldValue or not newValue:
                continue
            outfile.write(('"%s"wd(punct) > "%s"' + os.linesep) %
                          (oldValue, newValue))
        outfile.close()
        self.logger.debug("finished writing file")

#-------------------------------------------------------------------------------
# End of CCT_Writer.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of XSLT_Writer.py
#-------------------------------------------------------------------------------


class XSLT_Writer:

    def __init__(self, filepath):
        self.logger   = logging.getLogger("lingt.Access.XSLTWriter")
        self.filepath = filepath

    def write(self, dataList, xpathsToSearch, matchPartial):
        """
        dataList:       List with rows containing two elements.
        xpathsToSearch: List of XPath expressions.
        """
        self.logger.debug("writing XSLT file")
        outfile = codecs.open(self.filepath, 'w', 'UTF8')
        now     = datetime.datetime.now()
        header  = ("""<?xml version="1.0" encoding="UTF-8"?>
<!--
================================================================================
This file was generated by the OpenOffice.org Linguistic Tools.
It makes changes to an XML file in order to correct spelling.

Date Generated: %s.
================================================================================
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
<xsl:output method="xml" omit-xml-declaration="no" encoding="utf-8"
    indent="no"
    doctype-system="" /><!-- Can specify DTD file here. -->

<!-- This is called the identity template, because it simply copies
 everything in the original file.  Everything, that is, except for certain
 things we want to change, which we specify in the template(s) that follow. -->
<xsl:template match="@*|node()"><!-- this is shorthand for everything -->
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/><!-- all children recursively -->
  </xsl:copy>
</xsl:template>
""") % now.strftime("%d-%b-%Y")
        outfile.writelines(header)

        for xpath in xpathsToSearch:
            outfile.writelines("""
<!-- Here is the element we want to change the value of. -->
<xsl:template match="%s">
    <xsl:call-template name="look4changes"/>
</xsl:template>
""" % (xpath))

        outfile.writelines("""
<xsl:template name="look4changes">
  <xsl:copy>
    <xsl:apply-templates select="@*" mode="copy_attrs"/>
    <xsl:choose>""")

        for replacement in dataList:
            oldValue, newValue = replacement
            if matchPartial:
                outfile.writelines("""
      <xsl:when test="contains(text(), '%s')">
        <xsl:value-of select="concat(substring-before(text(), '%s'),
                                     '%s',
                                     substring-after(text(),  '%s'))" />
      </xsl:when>""" % (oldValue, oldValue, newValue, oldValue) )
            else:
                outfile.writelines("""
      <xsl:when test="text() = '%s'">
        <xsl:text>%s</xsl:text>
      </xsl:when>""" % (oldValue, newValue) )

        outfile.write("""
      <xsl:otherwise>
        <xsl:value-of select="node()" /><!-- copy text unchanged -->
      </xsl:otherwise>
    </xsl:choose>
  </xsl:copy>
</xsl:template>

<!-- This simply copies all attributes of an element -->
<xsl:template match="@*" mode="copy_attrs">
  <xsl:copy/>
</xsl:template>

</xsl:stylesheet>
""")

        outfile.close()
        self.logger.debug("finished writing file")
#-------------------------------------------------------------------------------
# End of XSLT_Writer.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SpellingChanges.py
#-------------------------------------------------------------------------------



def getChangeList(calcUnoObjs, columnOrder):
    """Grabs a 'from' and 'to' list of words."""
    colLetterWord       = columnOrder.getColLetter(columnOrder.COL_WORD)
    colLetterCorrection = columnOrder.getColLetter(columnOrder.COL_CORRECTION)
    reader       = SpreadsheetReader(calcUnoObjs)
    listFrom     = reader.getColumnStringList(
                   colLetterWord, skipFirstRow=True)
    listTo       = reader.getColumnStringListByLen(
                   colLetterCorrection, True, len(listFrom))
    changeList = []
    for fromVal, toVal in zip(listFrom, listTo):
        if (not fromVal) or (not toVal) or (toVal == fromVal):
            continue
        changeList.append([fromVal, toVal])
    return changeList

class ChangerMaker:
    """
    Save a CC table or XSLT file from data in the spreadsheet.
    """
    def __init__(self, calcUnoObjs, userVars):
        self.unoObjs   = calcUnoObjs
        self.userVars  = userVars
        self.logger    = logging.getLogger("lingt.App.ChangerMaker")
        self.msgbox    = MessageBox(self.unoObjs)

    def setFilepath(self, newVal):
        self.filepath = newVal

    def setExportType(self, newVal):
        self.exportType = newVal

    def setSFM(self, newVal):
        self.sfMarkers = newVal

    def setMatchPartial(self, newVal):
        self.matchPartial = newVal

    def setXpathExprs(self, newVal):
        """Value should be an iterable containing strings."""
        self.xpathExprs = newVal

    def make(self):
        self.logger.debug("make() BEGIN")
        progressBar = ProgressBar(self.unoObjs, "Getting data...")
        progressBar.show()
        progressBar.updateBeginning()
        try:
            columnOrder = ColumnOrder(self.userVars)
            columnOrder.loadFromUserVars()
            changeList = getChangeList(self.unoObjs, columnOrder)
        except DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
            progressBar.close()
        progressBar.updatePercent(50)
        progressBar.close()
        progressBar = ProgressBar(self.unoObjs, "Saving file...")
        progressBar.show()
        progressBar.updatePercent(50)
        if self.exportType == "ReplacementCCT":
            outputter = CCT_Writer(self.filepath)
            outputter.writeSimpleReplacements(changeList)
        elif self.exportType == "SFM_CCT":
            outputter = CCT_Writer(self.filepath)
            outputter.writeComplete(changeList, self.sfMarkers)
        elif self.exportType == "XSLT":
            outputter = XSLT_Writer(self.filepath)
            outputter.write(changeList, self.xpathExprs, self.matchPartial)
        progressBar.updateFinishing()
        progressBar.close()
        self.logger.debug("make() END")

#-------------------------------------------------------------------------------
# End of SpellingChanges.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SpellingComparisons.py
#-------------------------------------------------------------------------------



class SpellingCharClasses:
    """
    Suggest spelling changes based on character classes.
    """
    def __init__(self, calcUnoObjs, userVars):
        self.unoObjs        = calcUnoObjs
        self.userVars       = userVars
        self.logger         = logging.getLogger("lingt.App.SpellingCharClasses")
        self.msgbox         = MessageBox(self.unoObjs)
        self.locale         = Locale(self.unoObjs)
        self.letters        = Letters()
        self.script         = ""
        self.charsComp      = list()   # lines of chars to compare
        self.datalist       = None
        self.displayResults = True

    def setScript(self, newName):
        self.script = newName

    def getAvailableScriptKeys(self):
        if self.script not in self.letters.SimilarChars:
            return []
        charsDict = self.letters.SimilarChars[self.script]
        keys = list(charsDict.keys())
        if 'AnyConsonants' in self.letters.ScriptLetters[self.script]:
            keys.append('GEMIN')
        return keys

    def setCharCompFromScript(self, charCompOpts):
        """Sets self.charsComp"""
        self.charsComp = []
        if self.script not in self.letters.SimilarChars:
            self.logger.debug("Did not find script '%s'" % (self.script))
            return
        charsDict = self.letters.SimilarChars[self.script]
        for key in charCompOpts:
            if key in charsDict:
                setList = charsDict[key]
                if len(setList) > 0:
                    setList.sort(key=lambda s: s[0])
                    self.charsComp.extend(setList)
            elif key == 'GEMIN':
                if self.script in self.letters.ScriptLetters:
                    consList = \
                        self.letters.ScriptLetters[self.script]['AnyConsonants']
                    gemList = []
                    for cons in consList:
                        if self.script in self.letters.Virama:
                            virama = self.letters.Virama[self.script]
                            gemChars = "".join([cons, virama, cons])
                        else:
                            gemChars = cons * 2
                        gemList.append([cons, gemChars])
                    self.charsComp.extend(gemList)

    def setCharCompFromInput(self, inputString):
        """Sets self.charsComp from input from user."""
        self.charsComp = []
        for line in inputString.splitlines():
            charlist = []
            for char in line:
                if not char.isspace():
                    charlist.append(char)
            self.charsComp.append(charlist)

    def getCharCompString(self):
        lines = list()
        for charlist in self.charsComp:
            lines.append("  ".join(charlist))
        return os.linesep.join(lines) + os.linesep

    def doChecks(self):
        """
        Reader beware: The second half of this method contains detailed
        logic, to compare words against each other in a reasonably efficient
        manner.
        """
        self.logger.debug("doChecks() BEGIN")
        columnOrder = ColumnOrder(self.userVars)
        columnOrder.loadFromUserVars()
        colLetter = columnOrder.getColLetter(columnOrder.COL_WORD)

        reader = SpreadsheetReader(self.unoObjs)
        try:
            wordStrings = reader.getColumnStringList(
                          colLetter, skipFirstRow=True)
        except DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
            return
        words       = WordInList.fromStringList(wordStrings)

        charSetList = []
        for charlist in self.charsComp:
            if len(charlist) < 2:
                # only useful to have at least two characters to compare
                continue
            charset = CharSet.getCharSet(charlist)
            # treat each similarity set as if it were an individual character
            wordChar = WordChar.getCharSetChar(charset)
            charSetList.append(wordChar)
            
        wordPatternHash = dict()    # keys are patterns, values are list of
                                    # WordInList. This lets us quickly
                                    # match up identical patterns.
        wordPatterns    = dict()    # keys are words, values are patterns.
                                    # This is just so we can remember what 
                                    # the patterns for that word were.
        for word in words:
            for i, char1 in enumerate(word.text):
                for charsetWordChar in charSetList:
                    for char2 in charsetWordChar.val.charList:
                        j = i + len(char2)
                        if (word.text[i:j] == char2):
                            newPattern = WordPattern.getLiteralPattern(
                                         word.text)
                            newPattern.replace(i, j, charsetWordChar)
                            if word not in wordPatterns:
                                wordPatterns[word] = list()
                            wordPatterns[word].append(newPattern)
                            hashKey = newPattern.getHashKey()
                            if hashKey not in wordPatternHash:
                                wordPatternHash[hashKey] = list()
                            wordPatternHash[hashKey].append(word)

        numSimilarWords = 0
        for word in words:
            if word in wordPatterns:
                for pattern in wordPatterns[word]:
                    hashKey = pattern.getHashKey()
                    if not hashKey in wordPatternHash:
                        raise LogicError("Hash key should be there.")
                    similarWords = wordPatternHash[hashKey]
                    for similarWord in similarWords:
                        if similarWord.text != word.text:
                            word.similarWords.append(similarWord.text)
                            numSimilarWords += 1

        similarWordsStrings = [word.similarWords_str() for word in words]
        colLetter = columnOrder.getColLetter(columnOrder.COL_SIMILAR_WORDS)
        outputter = SpreadsheetOutput(self.unoObjs)
        try:
            outputter.outputToColumn(colLetter, similarWordsStrings)
        except DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")

        if self.displayResults:
            if numSimilarWords == 0:
                self.msgbox.display("Did not find any similar words.")
            else:
                self.msgbox.display(
                    "Found %d similar words.", (numSimilarWords,))
        self.logger.debug("doChecks() END")

class SpellingSuggestions:
    """
    Logic to find similar words based on edit distance.
    """
    def __init__(self, msgbox, limit=20):
        self.limit        = limit
        self.logger       = logging.getLogger("lingt.App.SpellingSuggestions")
        self.msgbox       = msgbox
        self.listSorted   = []    # sorted by word
        self.listByLength = []    # sorted by length

    def setList(self, datalist):
        self.listSorted = datalist[:]
        try:
            self.listSorted = list(filter(lambda word: word.strip() != "",
                                          self.listSorted))
        except AttributeError:
            self.msgbox.display("Error reading the list.")
            self.listSorted = []
        self.listSorted.sort()
        self.listByLength = self.listSorted[:]
        self.listByLength.sort(key=lambda word: len(word))

    def getSuggestions(self, wordToFind):
        """
        The main function to get similar words.
        Returns a list.
        """
        ## Sort list by most likely first.

        # First compare by same beginning.
        rank               = dict()
        bestMatchingCount  = 0
        firstMatchingIndex = 0
        lastMatchingIndex  = 0
        for i, wordSorted in enumerate(self.listSorted):
            matchingCount = 0
            for j, c in enumerate(wordToFind.lower()):
                if len(wordSorted) > j and wordSorted[j].lower() == c:
                    matchingCount += 1
                else:
                    break
            if matchingCount > bestMatchingCount:
                firstMatchingIndex = i
                lastMatchingIndex  = i
                bestMatchingCount  = matchingCount
            elif matchingCount == bestMatchingCount:
                lastMatchingIndex = i
            elif matchingCount < bestMatchingCount:
                break
        median_i = firstMatchingIndex + \
                   (lastMatchingIndex - firstMatchingIndex) // 2
        for i, wordSorted in enumerate(self.listSorted):
            rank[wordSorted] = abs(i - median_i)

        # Next compare by similar length.
        bestDiff       = 1000     # an arbitrary big number
        firstBestIndex = 0
        lastBestIndex  = 0
        for i, wordByLength in enumerate(self.listByLength):
            diff = abs(len(wordToFind) - len(wordByLength))
            if diff < bestDiff:
                firstBestIndex = i
                lastBestIndex  = i
                bestDiff = diff
            elif diff == bestDiff:
                lastBestIndex  = i
            elif diff > bestDiff:
                break
        median_i = firstBestIndex + \
                   (lastBestIndex - firstBestIndex) // 2
        for i, wordByLength in enumerate(self.listByLength):
            rank[wordByLength] += abs(i - median_i)

        # Sort by combined ranks of same start and length.
        rankList = []
        for wordSorted in self.listSorted:
            rankList.append(rank[wordSorted])
        rankedList = list(zip(self.listSorted, rankList))
        rankedList.sort(key=lambda rec: rec[1])    # sort by rank

        # Now check edit distance by that order.
        # Don't go through the whole list unless needed.
        superStrings = []
        for i, rec in enumerate(rankedList):
            wordRanked = rec[0]
            if self.subSuperString(wordToFind, wordRanked):
                superStrings.append(wordRanked)
            if len(superStrings) > self.limit // 2:
                break
        self.logger.debug("Found %d sub/super strings." % (len(superStrings)))
        similarStrings = []
        FAR_ENOUGH     = 1000  # There's no need to check the whole list,
                               # since the most likely are towards the front.
        for i, rec in enumerate(rankedList):
            wordRanked = rec[0]
            editDistance = self.levenshteinDistance(wordToFind, wordRanked)
            isBetterMatch    = False
            for similarStrings_i, rec2 in enumerate(similarStrings):
                unused, dist = rec2
                if editDistance < dist:
                    isBetterMatch = True
                    break
            if isBetterMatch:
                similarStrings.insert(similarStrings_i,
                                      (wordRanked, editDistance))
                if len(similarStrings) > self.limit:
                    similarStrings.pop()
            elif len(similarStrings) < self.limit:
                similarStrings.append((wordRanked, editDistance))
            if i > FAR_ENOUGH:
                break
        suggestions = superStrings[:]
        for word, unused in similarStrings:
            if word not in suggestions:
                suggestions.append(word)
        return suggestions[:self.limit]

    def subSuperString(self, s1, s2):
        """
        Return true if word is either a substring or a superstring.
        Two-letter words don't count, because for example "am" is a substring
        of "hamster" and "madam" and lots of other words.
        """
        if len(s1) > len(s2):
            s1,s2 = s2,s1   # swap
        if len(s1) <= 2:
            return False
        return s1.lower() in s2.lower()

    def levenshteinDistance(self, s1,s2):
        """
        Returns the edit distance of two strings.
        From http://rosettacode.org/wiki/Levenshtein_distance.
        """
        if len(s1) > len(s2):
            s1,s2 = s2,s1
        distances = range(len(s1) + 1)
        for index2,char2 in enumerate(s2):
            newDistances = [index2+1]
            for index1,char1 in enumerate(s1):
                if char1.lower() == char2.lower():
                    newDistances.append(distances[index1])
                else:
                    newDistances.append(1 + min((
                                            distances[index1],
                                            distances[index1+1],
                                            newDistances[-1])))
            distances = newDistances
        return distances[-1]

class WordPattern:
    """The pattern rather than the actual text of the word."""
    def __init__(self):
        self.charList = []  # elements of type WordChar

    @staticmethod
    def getLiteralPattern(text):
        """Factory method."""
        newPattern = WordPattern()
        for char in text:
            newPattern.charList.append(WordChar.getLiteralChar(char))
        return newPattern

    def replace(self, i, j, newWordChar):
        if j == i + 1:
            self.charList[i] = newWordChar
        else:
            self.charList = self.charList[:i] + newWordChar + self.charList[j:]

    def getHashKey(self):
        """
        Returns a value that can be used as a dictionary key, and will be
        unique if and only if the WordChar list it contains is unique.
        """
        return "".join(wordChar.getHashKey() for wordChar in self.charList)

class WordChar:
    """
    Either a character in a string, or else a CharSet in place of the character.
    """
    LITERAL = 0
    CHARSET = 1
    def __init__(self):
        self.charType = -1
        self.val      = None        # could be a string or a ref to a list

    @staticmethod
    def getLiteralChar(char):
        """Factory method."""
        newChar          = WordChar()
        newChar.charType = WordChar.LITERAL
        newChar.val      = char
        return newChar

    @staticmethod
    def getCharSetChar(charSet):
        """Factory method."""
        newChar          = WordChar()
        newChar.charType = WordChar.CHARSET
        newChar.val      = charSet
        return newChar

    def getHashKey(self):
        if self.charType == WordChar.CHARSET:
            return str(self.val.setID)
        elif self.charType == WordChar.LITERAL:
            return self.val
        return "0"

class CharSet:
    """Uniquely label a character list."""
    COUNT = 0
    def __init__(self):
        self.charList = []
        self.setID    = -1  # a unique number

    @staticmethod
    def getCharSet(newCharList):
        """Factory method."""
        newCharSet = CharSet()
        CharSet.COUNT += 1
        newCharSet.setID    = CharSet.COUNT
        newCharSet.charList = newCharList
        return newCharSet

#-------------------------------------------------------------------------------
# End of SpellingComparisons.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of WordListIO.py
#-------------------------------------------------------------------------------



class WordListIO:
    def __init__(self, calcUnoObjs, colOrder):
        self.unoObjs  = calcUnoObjs
        self.colOrder = colOrder
        #self.logger  = logging.getLogger(__name__)
        #self.logger  = logging.getLogger("WordListIO")
            # This doesn't seem to work. Perhaps the name is too deep or long.
        self.logger  = logging.getLogger("lingt.Access.WordListIO")
        self.logger.debug(__name__)
        self.msgbox  = MessageBox(self.unoObjs)
        self.locale  = Locale(self.unoObjs)

    def getMsgbox(self):
        """After outputList(), self.msgbox will be for the spreadsheet."""
        return self.msgbox

    def outputList(self, wordList, progressBarWriter):
        """
        Sends output to the Calc spreadsheet.
        Takes a list of App.WordList.WordInList.
        Returns True if successful.
        """
        self.logger.debug("outputList BEGIN")

        outputter = SpreadsheetOutput(self.unoObjs)
        listDoc   = outputter.createSpreadsheet()
        if not listDoc:
            return False
        self.msgbox = MessageBox(listDoc)
        sheet       = listDoc.sheets.getByIndex(0)

        progressBarWriter.percentMore(20)
        progressStartVal = progressBarWriter.getPercent()
        progressBarCalc  = ProgressBar(listDoc, "Generating List...")
        progressBarCalc.show()
        progressBarCalc.updatePercent(progressStartVal)

        ## Column headings

        headingRow   = 0     # first row
        numberFormat = 0     # General format
        for colNum, heading in enumerate(self.colOrder.getTitles()):
            cell = sheet.getCellByPosition(colNum, headingRow)
            cell.setFormula("")
            cell.setPropertyValue("NumberFormat", numberFormat)
            cell.setString(self.locale.getText(heading))
        
        cellFreeze = sheet.getCellByPosition(0, 1)
        listDoc.controller.select(cellFreeze)
        self.unoObjs.dispatcher.executeDispatch(
            listDoc.frame, ".uno:FreezePanes", "", 0, ())

        ## Fill in the data

        chunkSize = 25  # make this value bigger or smaller for optimization
        #chunkSize = 1  # useful for debugging
        for word_i1 in range(0, len(wordList), chunkSize):
            word_i2 = word_i1 + chunkSize - 1
            if word_i2 >= len(wordList):
                word_i2 = len(wordList) - 1

            data = []
            for word_i in range(word_i1, word_i2 + 1):
                word   = wordList[word_i]
                colOrd = self.colOrder  # shorthand variable name
                colOrd.resetRowData()
                colOrd.setRowVal(colOrd.COL_WORD,        word.text)
                colOrd.setRowVal(colOrd.COL_OCCURRENCES, word.occurrences)
                colOrd.setRowVal(colOrd.COL_IS_CORRECT,  word.isCorrect_str())
                colOrd.setRowVal(colOrd.COL_CORRECTION,  word.correction)
                colOrd.setRowVal(colOrd.COL_SOURCES,     word.sources_str())
                data.append(colOrd.getRowTuple())

            row1 = str(word_i1 + 2)  # start at second row, so index 0 is row 2
            row2 = str(word_i2 + 2)
            col2 = chr(ord('A') + len(self.colOrder.DEFAULT_ORDER) - 1)
            rangeName = "A" + row1 + ":" + col2 + row2
            self.logger.debug("Adding %d rows to range %s" %
                              (len(data), rangeName))
            #self.logger.debug(repr(data))
            oRange = sheet.getCellRangeByName(rangeName)
            try:
                oRange.setDataArray(tuple(data))
            except RuntimeException as exc:
                self.msgbox.display(
                    "There was a problem while writing the list.\n\n%s",
                    str(exc))
                progressBarCalc.close()
                progressBarWriter.close()
                return False
            nextProgress = progressStartVal + \
                           int((float(word_i1) / len(wordList)) *
                           (95 - progressStartVal))
            progressBarWriter.updatePercent(nextProgress)
            progressBarCalc.updatePercent(  nextProgress)

        progressBarCalc.updateFinishing()
        progressBarCalc.close()
        progressBarWriter.updateFinishing()
        progressBarWriter.close()

        self.logger.debug("outputList END")
        return True

    def readList(self):
        """
        Expects input spreadsheet to have columns generated by word list app,
        including word, similar words, source, isCorrect, et cetera.
        Returns a list of App.WordList.WordInList.
        """
        self.logger.debug("readList BEGIN")

        colOrd = self.colOrder  # shorthand variable name
        colLetterWord = colOrd.getColLetter(colOrd.COL_WORD)
        reader        = SpreadsheetReader(self.unoObjs)
        stringList    = reader.getColumnStringList(colLetterWord, True)
        if len(stringList) == 0:
            self.logger.debug("No data found.")
            return []
        row1 = 2    # first row is heading, second row is beginning of data
        row2 = row1 + len(stringList) - 1
        rangeName = "%s%d:%s%d" % ('A', row1, colOrd.maxColLetter(), row2)
        try:
            oRange = self.unoObjs.sheet.getCellRangeByName(rangeName)
            rowTuples = oRange.getDataArray()
        except RuntimeError as exc:
            self.msgbox.display("Error reading the list.\n\n%s", str(exc))
            return []
        if len(rowTuples) == 0:
            self.logger.debug("Could not get data.")
            return []

        datalist = []
        for rowTuple in rowTuples:
            colOrd.setRowTuple(rowTuple)
            wordInList = WordInList()
            wordInList.text        = colOrd.getRowVal(colOrd.COL_WORD)
            wordInList.occurrences = colOrd.getRowVal(colOrd.COL_OCCURRENCES)
            wordInList.correction  = colOrd.getRowVal(colOrd.COL_CORRECTION)
            wordInList.converted1  = colOrd.getRowVal(colOrd.COL_CONVERTED1)
            wordInList.converted2  = colOrd.getRowVal(colOrd.COL_CONVERTED2)
            wordInList.setSources(
                colOrd.getRowVal(colOrd.COL_SOURCES))
            wordInList.setSimilarWords(
                colOrd.getRowVal(colOrd.COL_SIMILAR_WORDS))
            wordInList.setIsCorrect(
                colOrd.getRowVal(colOrd.COL_IS_CORRECT))
            datalist.append(wordInList)
        return datalist

#-------------------------------------------------------------------------------
# End of WordListIO.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Traveler.py
#-------------------------------------------------------------------------------



class Traveler:
    def __init__(self, unoObjs):
        self.unoObjs      = unoObjs
        self.logger       = logging.getLogger("lingt.Access.Traveler")
        self.text         = None
        self.rangeCursor  = None    # a textcursor to hold the whole range
        self.travelCursor = None    # a textcursor to travel in the range
        self.placeCursor  = None    # a textcursor to remember a position

    def setTextRange(self, txtRange):
        """
        txtRange is of type Search.TxtRange.
        Returns True for success.
        """
        oSel = txtRange.sel
        try:
            self.text         = oSel.getText()
            self.rangeCursor  = oSel.getText().createTextCursorByRange(oSel)
            self.travelCursor = oSel.getText().createTextCursorByRange(
                                               oSel.getStart())
            self.placeCursor  = oSel.getText().createTextCursorByRange(
                                               oSel.getStart())
        except:
            self.logger.warn("Failed to go to text range.");
            return False
        self.logger.debug("String = <<" + self.rangeCursor.getString() + ">>")
        return True

    def getString(self):
        """
        If a word in the range is changed, the range will be
        adjusted and getString will give the new value.
        """
        return self.rangeCursor.getString()

    def getStringBefore(self):
        self.travelCursor.gotoRange(self.rangeCursor.getStart(), False)
        self.travelCursor.gotoRange(self.placeCursor.getStart(), True)
        return self.travelCursor.getString()

    def changeString(self, changeTo):
        changeString(self.travelCursor, changeTo)
        self.placeCursor.gotoRange(self.travelCursor.getEnd(), False)

    def selectWord(self, stringBeforeWord, wordString):
        """
        Go to the word and select it.
        Returns True if the word was successfully selected.
        """
        self.logger.debug("selectWord BEGIN")
        self.logger.debug("stringBeforeWord = <<%s>>" % (stringBeforeWord))
        self.logger.debug("wordString = '%s'" % (wordString))
        self.gotoLoc(stringBeforeWord)
        selectedString = ""
        while len(selectedString) < len(wordString):
            if not self.travelCursor.goRight(1, True):
                self.logger.warn("Could not go right.")
                return False
            try:
                selectedString = self.travelCursor.getString()
                self.logger.debug("'%s'" % (selectedString))
            except RuntimeException:
                self.logger.warn("Could not get string from selection.")
                return False
        self.logger.debug("selectedString = '%s'" % (selectedString))
        try:
            # Select the word so the user can see it.
            self.unoObjs.viewcursor.gotoRange(self.travelCursor, False)
        except RuntimeException:
            self.logger.warn("Could not go to range.")
        return selectedString == wordString

    def gotoLoc(self, stringBeforeWord):
        """
        Within the range, go to a specific location specified by the string.
        Will move self.travelCursor to that position.

        Going through each character in a document with oCurs.goRight(1, True)
        can be pretty slow, so instead we narrow down the location
        by guessing and then comparing string lengths.
        """
        self.logger.debug("gotoLoc BEGIN")
        # Make a textcursor to find where the viewcursor should go.
        # The textcursor will guess by doubling each time until it gets
        # big enough, then it will start getting smaller as we
        # narrow down the right place.
        # When guessing, no need to compare ranges. Instead compare
        # string lengths.  If string lengths are the same, then that's
        # the exact spot.  Otherwise, whether beyond the end of the range or
        # not, we need to keep guessing.
        guess          = 2
        delta          = 1
        guessedHigh    = False   # have we guessed too high yet
        oneStepForward = False   # have we already tried just one step forward
        self.travelCursor.gotoRange(self.rangeCursor.getStart(), False)
        self.travelCursor.goRight(guess, True)
        while True:
            guessString = self.travelCursor.getString()
            if len(guessString) < len(stringBeforeWord):
                if not guessedHigh:
                    delta = delta * 2
                else:
                    # From here on out, guess changes will get smaller.
                    delta = delta // 2
                    if delta == 0:
                        delta = 1
                prevCurs = self.text.createTextCursorByRange(self.travelCursor)
                ok = cursorGo(self.travelCursor, 'right', delta, True)
                if delta == 1:
                    oneStepForward = True
                self.logger.debug("%d, %d up" % (len(guessString), delta))
                while not ok:
                    # Probably went beyond the text range
                    delta = delta // 2
                    if delta == 0:
                        break
                    self.travelCursor.gotoRange(prevCurs, False)
                    ok = cursorGo(self.travelCursor, 'right', delta, True)
                    guessedHigh = True
                    if delta == 1:
                        oneStepForward = True
                    self.logger.debug("%d, %d up2" % (len(guessString), delta))
            elif len(guessString) > len(stringBeforeWord):
                delta = delta // 2
                if delta == 0:
                    # this covers cases where len(stringBeforeWord) < 2
                    delta = 1
                if oneStepForward and delta == 1:
                    self.logger.warn("Couldn't move to exact spot.")
                    break
                cursorGo(self.travelCursor, 'left', delta, True)
                guessedHigh = True
                self.logger.debug("%d, %d down" % (len(guessString), delta))
            else:
                self.logger.debug("Found it")
                break
        self.travelCursor.collapseToEnd()
        self.logger.debug("gotoLoc END")

def cursorGo(oCurs, direction, count, doSel):
    """
    There is a limit to how big the parameter to oCurs.goRight() can be.
    To get around this, we simply call it several times with smaller numbers.
    """
    MAX_SIZE = pow(2,15) - 1  # this limit probably comes from C sizeof(int)
    parts = []
    div, mod = divmod(count, MAX_SIZE)
    div = int(div)  # first argument returned from divmod is a float
    parts.extend([MAX_SIZE] * div)
    if mod > 0 or div == 0:
        parts.append(mod)
    for part in parts:
        if direction == 'right':
            return oCurs.goRight(part, doSel)
        else:
            return oCurs.goLeft(part, doSel)

#-------------------------------------------------------------------------------
# End of Traveler.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SpellingChecks.py
#-------------------------------------------------------------------------------



class SpellingStepper:
    """
    Step through each row in a word list to check for spelling.
    """
    def __init__(self, calcUnoObjs, userVars):
        self.unoObjs         = calcUnoObjs
        self.userVars        = userVars
        self.logger          = logging.getLogger("lingt.App.DataConversion")
        self.msgbox          = MessageBox(self.unoObjs)
        self.suggestions     = SpellingSuggestions(self.msgbox)
        self.suggListSet     = False
        self.wantSuggestions = True
        self.currentRow      = -1
        self.datalist        = []   # List of WordInList items. Indices are
                                    # offset from row number by 2.

    def loadData(self):
        self.columnOrder = ColumnOrder(self.userVars)
        self.columnOrder.loadFromUserVars()

        wordlistIO    = WordListIO(self.unoObjs, self.columnOrder)
        self.datalist = wordlistIO.readList()
        self.setSuggestionList()
        return len(self.datalist)

    def gotoRow(self, rowNum):
        """Return copy of WordInList item of that row."""
        self.currentRow = rowNum
        return copy.deepcopy(self.currentRowData())

    def setSuggestionList(self):
        if not self.wantSuggestions:
            self.suggListSet = False
            return
        wordStrings = []
        for wordData in self.datalist:
            if wordData.isCorrect is not False and wordData.correction == "":
                wordStrings.append(wordData.text)
        self.suggestions.setList(wordStrings)
        self.suggListSet = True

    def getSuggestions(self, listToIgnore):
        if not self.suggListSet:
            self.setSuggestionList()
        wordData = self.currentRowData()
        suggList = self.suggestions.getSuggestions(wordData.text)

        ## Remove duplicate words
        wordData = self.currentRowData()
        for wordText in (listToIgnore + [wordData.text]):
            if wordText in suggList:
                suggList.remove(wordText)
        return suggList

    def setIsCorrect(self, newVal):
        """
        newVal should be either True, False or None.
        """
        outputter = SpreadsheetOutput(self.unoObjs)
        colLetterIsCorrect = self.columnOrder.getColLetter(
                             self.columnOrder.COL_IS_CORRECT)
        wordData = self.currentRowData()
        wordData.isCorrect = newVal
        try:
            outputter.outputString(
                colLetterIsCorrect, self.currentRow, wordData.isCorrect_str())
        except DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")
        self.setSuggestionList()

    def setCorrection(self, newText):
        outputter = SpreadsheetOutput(self.unoObjs)
        colLetterCorrection = self.columnOrder.getColLetter(
                              self.columnOrder.COL_CORRECTION)
        wordData = self.currentRowData()
        wordData.correction = newText
        try:
            outputter.outputString(
                colLetterCorrection, self.currentRow, newText)
        except DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")

    def currentRowData(self):
        return self.datalist[self.currentRow - 2]

class SpellingChecker:
    """
    Traverse words in a document to check and make spelling corrections.
    This is similar in concept to a traditional spell checker.
    Calls DlgSpellingReplace from the UI layer.
    """
    def __init__(self, writerUnoObjs, userVars, logger):
        self.unoObjs        = writerUnoObjs
        self.logger         = logger
        self.msgbox         = MessageBox(self.unoObjs)
        self.msgboxFour     = FourButtonDialog(self.unoObjs)
        self.userVars       = userVars
        self.suggestions    = SpellingSuggestions(self.msgbox)
        self.columnLetter   = ""
        self.dlg            = None
        self.listGoodWords  = []
        self.wordsToIgnore  = set()
        self.punctuation    = ""
        self.askEach        = True

    def setConfig(self, config):
        self.logger.debug("setConfig BEGIN")
        if config.filepath == "" or not config.filepath.lower().endswith(
            (".ods",".sxc", ".xls",".xlsx")
            ):
            raise ChoiceProblem(
                "Please specify a word list file. To make a new empty "
                "list, go to Word List and Spelling and then save the "
                "spreadsheet file.")
        self.wordListFile = config.filepath
        if config.whichTask == "":
            raise LogicError("No task was specified.")
        self.whichTask = config.whichTask

        if config.whichScope == "":
            raise LogicError("No scope was specified.")
        elif config.whichScope == "Language":
            if config.scopeLanguage == "":
                raise ChoiceProblem(
                    "Please select a language name.")
        elif config.whichScope == "ParaStyle":
            if config.scopeStyle == "":
                raise ChoiceProblem(
                    "Please select a scope paragraph style.")
        elif config.whichScope == "CharStyle":
            if config.scopeStyle == "":
                raise ChoiceProblem(
                    "Please select a scope character style.")
        elif config.whichScope == "Font":
            if config.scopeFont == "":
                raise ChoiceProblem("Please select a scope font.")
        elif config.whichScope == "SFMs":
            if config.scopeSFMs == "":
                raise ChoiceProblem("Please specify SFMs.")
        self.whichScope   = config.whichScope
        self.searchConfig = ConfigOptions()
        self.searchConfig.localeToFind = config.scopeLanguage
        self.searchConfig.scopeStyle   = config.scopeStyle 
        self.searchConfig.scopeFont    = config.scopeFont
        self.searchConfig.fontType     = config.fontType 
        self.searchConfig.scopeSFMs    = config.scopeSFMs 
        self.searchConfig.matchesLimit = config.matchesLimit 

        self.punctuation = config.punctuation
        self.matchCase   = config.matchCase
        self.prefixes    = []
        self.suffixes    = []
        affixes = config.affixes.split()
        for affix in affixes:
            if affix.startswith("-"):
                self.suffixes.append(affix.lstrip("-"))
            elif affix.endswith("-"):
                self.prefixes.append(affix.rstrip("-"))
            else:
                self.prefixes.append(affix)
                self.suffixes.append(affix)
        self.logger.debug("setConfig END")

    def doSearch(self):
        """
        Get text ranges and then check those ranges for words.
        Navigate to each word (perhaps using punctuation list) and
        verify each word against the word list.
        """
        self.logger.debug("doSearch() BEGIN")
        fileReader = CalcFileReader(self.unoObjs)
        ok = fileReader.loadDoc(self.wordListFile)
        if not ok:
            return
        self.calcUnoObjs = fileReader.calcUnoObjs
        columnOrder = ColumnOrder(self.userVars)
        columnOrder.loadFromUserVars()
        self.changeDict = dict()
        try:
            if self.whichTask == 'SpellCheck':
                self.logger.debug("Reading good list.")
                self.columnLetter  = columnOrder.getColLetter(
                                     columnOrder.COL_WORD)
                wordListReader     = fileReader.getSpreadsheetReader()
                self.listGoodWords = wordListReader.getColumnStringList(
                                     self.columnLetter, skipFirstRow=True)
            else:
                self.logger.debug("Reading change list.")
                changeList = getChangeList(
                             self.calcUnoObjs, columnOrder)
                for oldVal, newVal in changeList:
                    oldValLower, unused = self.getLowerCase(oldVal)
                    self.changeDict[oldValLower] = newVal
        except DocAccessError:
            self.msgbox.display("Error reading spreadsheet.")
            return
        self.suggestions.setList(self.listGoodWords)
        self.getLowerCaseList()

        self.dlg = DlgSpellingReplace(self.unoObjs)
        self.dlg.makeDlg()
        progressBar = ProgressBar(self.unoObjs, "Finding text...")
        progressBar.show()
        progressBar.updateBeginning()

        ## Find the text ranges

        textSearch = TextSearch(self.unoObjs, progressBar)
        textSearch.setConfig(self.searchConfig)
        try:
            if self.whichScope == "WholeDoc":
                textSearch.scopeWholeDocTraverse()
            elif self.whichScope == "Selection":
                textSearch.scopeSelection()
            elif self.whichScope == "Language":
                textSearch.scopeLocale()
            elif self.whichScope == "ParaStyle":
                textSearch.scopeParaStyle()
            elif self.whichScope == "CharStyle":
                textSearch.scopeCharStyle()
            elif self.whichScope == "Font":
                textSearch.scopeFont()
            elif self.whichScope == "SFMs":
                textSearch.scopeSFMs()
            else:
                self.msgbox.display("Unexpected value %s", (self.whichScope,))
                progressBar.close()
                return
        except ScopeError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            progressBar.close()
            return
        progressBar.updateFinishing()
        progressBar.close()
        rangesFound = textSearch.getRanges()

        interrupted = False
        changes     = 0
        try:
            for txtRange in rangesFound:
                self.traveler = Traveler(self.unoObjs)
                ok = self.traveler.setTextRange(txtRange)
                if not ok:
                    continue
                rangeTokens  = self.getTokens(self.traveler.getString())
                tokenNum     = -2   # because the loop starts by += 2
                while True:
                    tokenNum += 2   # tokens are in pairs: word, delim
                    self.logger.debug("Token '%d' of %d" %
                                      (tokenNum, len(rangeTokens)))
                    if tokenNum >= len(rangeTokens):
                        break
                    suspect           = True
                    word              = rangeTokens[tokenNum]
                    word              = word.strip(self.punctuation)
                    wordLower, unused = self.getLowerCase(word)
                    wordNoAffix       = self.removeAffixes(wordLower)
                    if (word == ""     or
                        word.isdigit() or
                        word.isspace() or
                        wordLower   in self.listLowerCase or
                        wordNoAffix in self.listLowerCase or
                        wordLower   in self.wordsToIgnore
                       ):
                        suspect = False
                    if self.whichTask == 'ApplyCorrections':
                        suspect = wordLower in self.changeDict
                    if suspect:
                        self.logger.debug("Word '%s' is suspect" % (word))
                        success = self.traveler.selectWord(
                                  ''.join(rangeTokens[:tokenNum]),
                                  rangeTokens[tokenNum])
                        if not success:
                            if self.msgbox.displayOkCancel(
                                "Missed word '%s'. Keep going?", (word)
                               ):
                                continue
                            else:
                                raise UserInterrupt()
                        changed = self.askAboutWord(
                                  word, rangeTokens, tokenNum)
                        if changed:
                            changes += 1
                            rangeTokens  = self.getTokens(
                                           self.traveler.getString())
                            tokensBefore = self.getTokens(
                                           self.traveler.getStringBefore())
                            tokenNum = len(tokensBefore)
                            tokenNum -= tokenNum % 2  # make sure it's even
        except UserInterrupt:
            # finish the loop
            interrupted = True
        except DocAccessError:
            self.msgbox.display("Error writing to spreadsheet.")
            interrupted = True

        self.dlg.doDispose()
        if not interrupted:
            if self.whichTask == 'ApplyCorrections':
                plural = "" if changes == 1 else "s" # add "s" if plural
                self.msgbox.display("Made %d correction%s.", (changes, plural))
            else:
                self.msgbox.display("Spell check finished.")

    def getLowerCaseList(self):
        if self.matchCase:
            self.listLowerCase = self.listGoodWords
            return
        self.listLowerCase = self.listGoodWords[:]
        for i, word in enumerate(self.listGoodWords):
            wordLower, changed = self.getLowerCase(word)
            if changed:
                self.listLowerCase[i] = wordLower

    def removeAffixes(self, wordText):
        for prefix in self.prefixes:
            if wordText.startswith(prefix):
                wordText = wordText[len(prefix):]
        for suffix in self.suffixes:
            if wordText.endswith(suffix):
                wordText = wordText[:-len(suffix)]
        return wordText

    def getLowerCase(self, wordText):
        """
        Sets the first character to lower case.
        Returns True if a change was made.
        """
        if self.matchCase:
            return wordText, False
        if len(wordText) == 0:
            return "", False
        c = wordText[0]
        if c in Letters.CaseCapitals:
            i = Letters.CaseCapitals.index(c)
            wordText = Letters.CaseLower[i] + wordText[1:]  # change 1st letter
            return wordText, True
        return wordText, False

    def getTokens(self, delimitedStr):
        """
        Split into tokens by white space.
        Will return an array with even elements as words (i.e. 0,2,4...),
        and odd elements as the white space delimiters.
        Element 0 will be empty if the string starts with delimiters.
        """
        tokens = re.split("(\\s+)", delimitedStr)   # split by whitespace
        if tokens[-1] == "":
            tokens.pop() # remove the empty final element
        return tokens

    def askAboutWord(self, wordText, tokens, wordTokenNum):
        """
        Returns True if string becomes dirty, else False.
        """
        wordWithPunct = tokens[wordTokenNum]
        withoutLPunct = wordWithPunct.lstrip(self.punctuation)
        withoutRPunct = wordWithPunct.rstrip(self.punctuation)
        punctBefore   = wordWithPunct[:-len(withoutLPunct)]
        punctAfter    = wordWithPunct[len(withoutRPunct):]
        if self.whichTask == "ApplyCorrections":
            lowerText, unused = self.getLowerCase(wordText)
            newWord           = self.changeDict[lowerText]
            if self.askEach:
                result = self.msgboxFour.display(
                         "Make this change? (%s -> %s)", (wordText,newWord))
                if result == "yes":
                    pass
                elif result == "no":
                    return False
                elif result == "yesToAll":
                    self.askEach = False
                else:
                    raise UserInterrupt()
            newString = punctBefore + newWord + punctAfter
            self.traveler.changeString(newString)
            return True
        suggestList = self.suggestions.getSuggestions(wordText)
        if not self.matchCase:
            ## Suggest only words of the same case as the word found.
            #  Non-roman characters will not be changed.
            firstChar = wordText[:1]
            if firstChar.isupper():
                suggestList = map(lambda s: s.capitalize(), suggestList)
                suggestList = uniqueList(suggestList)
            elif firstChar.islower():
                suggestList = map(lambda s: s.lower(),      suggestList)
                suggestList = uniqueList(suggestList)

        CONTEXT_LEN = 10   # probably use an even number
        contextBegin = wordTokenNum - CONTEXT_LEN
        contextEnd   = wordTokenNum + CONTEXT_LEN
        if contextBegin < 0: contextBegin = 0
        context = ''.join(tokens[contextBegin:contextEnd])
        self.dlg.setContents(wordText, suggestList, context)

        self.dlg.doExecute()
        action, changeTo = self.dlg.getResults()
        newString = punctBefore + changeTo + punctAfter
        if action == "Ignore":
            # just keep going
            return False
        elif action == "IgnoreAll":
            lowerText, unused = self.getLowerCase(wordText)
            self.wordsToIgnore.add(lowerText)
            return False
        elif action == "Change":
            self.traveler.changeString(newString)
            return True
        elif action == "ChangeAll":
            self.traveler.changeString(newString)
            replacer = FindAndReplace(self.unoObjs, False)
            replacer.replace(wordText, changeTo)
            return True
        elif action == "Add":
            wordSimplified = self.removeAffixes(wordText)
            self.listGoodWords.append(wordSimplified)
            self.suggestions.setList(self.listGoodWords)
            self.getLowerCaseList()
            spreadsheetOutput = SpreadsheetOutput(self.calcUnoObjs)
            spreadsheetOutput.outputToColumn(
                self.columnLetter, self.listGoodWords)
            return False
        # user probably pressed Close or x'd out of the dialog
        raise UserInterrupt()

#-------------------------------------------------------------------------------
# End of SpellingChecks.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SFM_Reader.py
#-------------------------------------------------------------------------------



class SFM_Reader(FileReader):

    SUPPORTED_FORMATS = [
        ("sfm", "Generic SFM file (markers like \\tx)"),
        ]

    def __init__(self, fileconfig, unoObjs):
        """Will grab fields based on fileconfig.dataFields."""
        FileReader.__init__(self, unoObjs)
        self.fileconfig  = fileconfig  # type FileItemList.WordListFileItem
        self.dataList    = []          # values are tuples of (marker, data)

    def read(self):
        """Read in the data.
        Returns list with elements of type WordInList.
        """
        self.logger.debug("read_file BEGIN")
        self.progressBar.show()
        self.progressBar.updateBeginning()

        self.words = [] # list to store examples
        filepath = self.fileconfig.filepath
        self.logger.debug("Parsing file " + filepath)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", (filepath,))
            self.progressBar.close()
            return list()
        self.progressBar.updatePercent(30)
        self.get_words_from_sfm()
        if len(self.words) == 0:
            self.msgbox.display(
                "Did not find any data in file %s", (filepath,))
        self.progressBar.updateFinishing()
        self.progressBar.close()
        self.logger.debug("SFM_Reader.read() END")
        return self.words

    def get_words_from_sfm(self):
        """Read in the data. Modifies self.words"""
        self.read_sfm_file()
        for marker, value in self.dataList:
            word = WordInList()
            word.text   = value
            word.source = self.fileconfig.filepath
            self.words.append(word)
        self.logger.debug("Found " + str(len(self.dataList)) + " words")

    def read_sfm_file(self):
        """
        Grabs a flat list of marker data, not organized by records of
        several markers.

        This should work whether self.fileconfig contains one field with
        several markers, or several fields with one marker each, or some
        combination of the two.

        Modifies self.dataList
        """
        self.logger.debug("reading SFM file")
        infile = codecs.open(self.fileconfig.filepath, 'r', 'UTF8')

        sfMarkerList = list()
        for dataField in self.fileconfig.dataFields:
            if dataField.fieldType == DataField.SFM_MARKER:
                sfMarkerList.extend(dataField.fieldValue.split())

        lineNum = 1
        try:
            for line in infile:
                self.logger.debug("Line #%d." % (lineNum))
                lineNum += 1
                for marker in sfMarkerList:
                    markerWithSpace = marker + " "
                    if line.startswith(markerWithSpace):
                        self.logger.debug("^" + markerWithSpace)
                        data = line[len(markerWithSpace):]
                        data = data.strip() # is this needed?
                        self.dataList.append( (marker, data) )
        except UnicodeDecodeError as exc:
            raise FileAccessError(
                "Error reading file %s\n\n%s" %
                (self.fileconfig.filepath, str(exc)))
        finally:
            infile.close()
        self.logger.debug("finished reading SFM file")

#-------------------------------------------------------------------------------
# End of SFM_Reader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DocReader.py
#-------------------------------------------------------------------------------



class DocReader(FileReader):

    SUPPORTED_FORMATS = [
        ('writerdoc', "Document (.odt .doc .docx .rtf) for Writer")]

    def __init__(self, fileconfig, unoObjs, matchesLimit):
        FileReader.__init__(self, unoObjs)
        self.locale       = Locale(unoObjs)
        self.fileconfig   = fileconfig   # type FileItemList.WordListFileItem
        self.matchesLimit = matchesLimit

    def read(self):
        """Read in the data.
        Returns list with elements of type WordInList.
        """
        self.logger.debug("read_file BEGIN")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        self.progressBar.updatePercent(20)

        self.words = [] # list to store examples
        ok = self.loadDoc(self.fileconfig.filepath)
        if not ok:
            self.progressBar.close()
            return list()
        self.progressBar.updatePercent(60)
        self.read_document()
        self.logger.debug("Setting visible.")
        self.doc.window.setVisible(True)
        if len(self.words) == 0:
            self.msgbox.display("Did not find any data in file %s",
                                (self.fileconfig.filepath,))
        self.progressBar.updateFinishing()
        self.progressBar.close()
        return self.words

    def read_document(self):
        """Sets self.words to list of WordInList objects."""
        self.logger.debug("read_document() BEGIN");
        textRanges = []
        textSearch = TextSearch(
                     self.doc, self.progressBar, checkForFormatting=False)
        for dataField in self.fileconfig.dataFields:
            config = ConfigOptions()
            config.matchesLimit = self.matchesLimit
            config.scopeFont    = ""
            config.fontType     = ""
            config.scopeStyle   = ""
            config.scopeSFMs    = ""
            config.localeToFind = None
            try:
                if dataField.fieldType == DataField.PARASTYLE:
                    config.scopeStyle = dataField.fieldValue
                    textSearch.setConfig(config)
                    textSearch.scopeParaStyle()
                elif dataField.fieldType == DataField.CHARSTYLE:
                    config.scopeStyle = dataField.fieldValue
                    textSearch.setConfig(config)
                    textSearch.scopeCharStyle()
                elif dataField.fieldType == DataField.FONTNAME:
                    config.scopeFont = dataField.fieldValue
                    config.fontType  = dataField.fontType
                    textSearch.setConfig(config)
                    textSearch.scopeFont()
                elif (dataField.fieldType == DataField.PART and
                      dataField.fieldValue == self.locale.getText(
                                              "Whole Document")
                     ):
                    textSearch.scopeWholeDocTraverse()
                else:
                    continue
            except ScopeError as exc:
                self.msgbox.display(exc.msg, exc.msg_args)
                return
            textRanges.extend(textSearch.getRanges())

        for txtRange in textRanges:    # txtRange is of type TxtRange
            oSel = txtRange.sel
            try:
                oCursor = oSel.getText().createTextCursorByRange(oSel)
            except:
                self.logger.warn("Failed to go to text range.");
                continue
            text = oCursor.getString()
            if text != "":
                ## Add word
                word = WordInList()
                word.text = text
                word.source = self.fileconfig.filepath
                self.words.append(word)
        self.logger.debug("read_document() END");

    def loadDoc(self, filepath):
        self.logger.debug("Opening file " + filepath)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", (filepath,))
            return False
        fileUrl = uno.systemPathToFileUrl(os.path.realpath(filepath))
        uno_args = (
            createProp("Minimized", True),
            # Setting a filter makes some files work but then .odt fails.
            # Instead just have the user open the file first.
            #createProp("FilterName", "Text"),
        )
        # Loading the document hidden was reported to frequently crash
        #       before OOo 2.0. It seems to work fine now though.
        newDoc  = self.unoObjs.desktop.loadComponentFromURL(
                  fileUrl, "_default", 0, uno_args)
        try:
            self.doc = self.unoObjs.getDocObjs(newDoc)
        except AttributeError as exc:
            self.msgbox.display(str(exc))
            return False
        self.logger.debug("Opened file.")
        return True

#-------------------------------------------------------------------------------
# End of DocReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of LingExStructs.py
#-------------------------------------------------------------------------------


class LingPhonExample:
    """A structure to hold one phonology example."""

    # Note: Translate these when putting in a dialog box, but be sure to
    #       pass the untranslated form to getByTitle().
    FIELD_TITLES = ["ref. number",
                    "phonetic",
                    "phonemic",
                    "gloss"]

    def __init__(self):
        self.refText     = ""
        self.phonetic    = ""
        self.phonemic    = ""
        self.gloss       = ""

    def getByTitle(self, title):
        """Return value of the specified field."""
        if title == self.FIELD_TITLES[0]:
            return self.refText
        return getattr(self, title)

class LingGramExample:
    """
    A structure to hold one grammar example.
    It contains zero or more words, which each contain zero or more morphs.
    """
    def __init__(self):
        self.refText     = ""
        self.wordList    = []   # list of LingGramWord
        self.__morphList = []   # list of LingGramMorph
        self.freeTrans   = ""

    def appendMorphObj(self, morph):
        """@arg1 type is LingGramMorph."""
        self.__morphList.append(morph)

    def appendMorph(self, morphOrth, morphText, morphEng, morphPS):
        """Temporarily store morph before assigning to a particular word."""
        m = LingGramMorph()
        m.orth  = morphOrth
        m.text  = morphText
        m.gloss = morphEng
        m.pos   = morphPS
        self.__morphList.append(m)

    def appendWord(self, wordText, wordOrth):
        if len(self.__morphList) == 0:
            ## add an entry so that the word shows up
            self.appendMorphObj(LingGramMorph())
        w           = LingGramWord()
        w.orth      = wordOrth
        w.text      = wordText
        w.morphList = self.__morphList
        self.wordList.append(w)
        self.__morphList = []

    def addPunctuation(self, punct):
        if len(self.wordList) == 0: return
        prevWord = self.wordList[-1]
        prevWord.text += punct

    # Normally I would put this at the top of the class, but here it's much
    # easier to compare with getByTitle().
    FIELD_TITLES = ["ref. number",
                    "free translation",
                    "text",          # word
                    "orthographic",  # word
                    "morphemes",     # text
                    "orth. morphemes",
                    "gloss",
                    "part of speech"]

    def getByTitle(self, title):
        """Return list of values of the specified field."""
        if title == self.FIELD_TITLES[0]:
            return [self.refText]
        elif title == self.FIELD_TITLES[1]:
            return [self.freeTrans]
        elif title == self.FIELD_TITLES[2]:
            return [word.text for word in self.wordList]
        elif title == self.FIELD_TITLES[3]:
            return [word.orth for word in self.wordList]
        elif title == self.FIELD_TITLES[4]:
            return [ morph.text for word in self.wordList
                     for morph in word.morphList ]
        elif title == self.FIELD_TITLES[5]:
            return [ morph.orth for word in self.wordList
                     for morph in word.morphList ]
        elif title == self.FIELD_TITLES[6]:
            return [ morph.gloss for word in self.wordList
                     for morph in word.morphList ]
        elif title == self.FIELD_TITLES[7]:
            return [ morph.pos for word in self.wordList
                     for morph in word.morphList ]
        raise LogicError("Unknown field title '%s'", str(title))

class LingGramMorph:
    """Used in LingGramExample"""
    def __init__(self):
        self.orth  = "" # orthographic representation of morpheme
        self.text  = "" # normal (typically IPA) representation of morpheme
        self.gloss = "" # gloss (typically English)
        self.pos   = "" # part of speech

class LingGramWord:
    """Used in LingGramExample"""
    def __init__(self):
        self.orth      = ""
        self.text      = ""
        self.morphList = []     # to handle one or more morphs
        self.morph     = None   # to handle only one morph

#-------------------------------------------------------------------------------
# End of LingExStructs.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of XmlUtils.py
#-------------------------------------------------------------------------------


def getTextByTagName(parent, tagname):
    """XML helper function. Gets text of the first and probably only tag."""
    elems = parent.getElementsByTagName(tagname)
    if len(elems) == 0: return ""
    elem = elems[0]
    return getElemText(elem)

def getElemText(elem):
    nodelist = elem.childNodes
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def getTextByWS(parent, preferredWS):
    """
    Returns the text content for the specified writing system.

    Expected structure <form lang="en"><text></text></form>
    This is handled too: <text></text>

    If more than one form is found, and none match the requested writing system,
    then the first form found is returned.
    """
    logger = logging.getLogger("lingt.Access.XmlUtils")
    if preferredWS is None or preferredWS == "":
        preferredWS = "en"  # default to English
    forms = parent.getElementsByTagName("form")
    if len(forms) == 0:
        return getTextByTagName(parent, "text")
    elif len(forms) == 1:
        return getTextByTagName(forms[0], "text")
    for form in forms:
        if form.attributes is not None:
            lang = form.getAttribute("lang")
            if lang == preferredWS:
                logger.debug("got lang " + str(preferredWS))
                return getTextByTagName(form, "text")
    logger.debug("could not get lang " + str(preferredWS))
    return getTextByTagName(forms[0], "text")

#-------------------------------------------------------------------------------
# End of XmlUtils.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of InterlinReader.py
#-------------------------------------------------------------------------------



class InterlinReader(FileReader):
    """For Grammar examples."""

    SUPPORTED_FORMATS = [
        ('flextext', "FieldWorks Interlinear XML (flextext)"),
        ('tbxint', "Toolbox Interlinear XML"),
        ]
    autoRefID = 0   # used if we need to generate IDs for keys to exampleDict

    def __init__(self, config, unoObjs, userVars):
        """config.fileList should be a list of type LingExFileItem."""
        FileReader.__init__(self, unoObjs)
        self.fileList             = config.fileList
        self.ShowMorphemeBreaks   = config.ShowMorphemeBreaks
        self.SeparateMorphColumns = config.SeparateMorphColumns
        self.userVars             = userVars
        self.suggestions          = []  # list of example ref numbers
        self.generateRefIDs       = False

    def getSuggestions(self):
        return self.suggestions

    def read(self):
        """Read in the data.
        Returns dictionary of examples keyed by lowercase reference number.
        Examples are of type LingGramExample.
        """
        self.logger.debug("read_files BEGIN")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        self.progressBar.updatePercent(20)
        percentStart     = 20
        percentIncrease  = 70
        percentEach      = percentIncrease // len(self.fileList)
        percentEachPart  = percentEach // 3

        self.exampleDict = {}  # dictionary to store examples
        self.suggestions = [] 
        list_index       = 1   # 1-based index of current element in list
        for fileItem in self.fileList:
            self.logger.debug("Parsing file " + fileItem.filepath)
            self.prefix = fileItem.prefix
            self.dom = None
            if not os.path.exists(fileItem.filepath):
                self.progressBar.percentMore(percentEachPart)
                self.msgbox.display (
                    "Cannot find file %s", (fileItem.filepath,))
                continue
            try:
                self.dom = xml.dom.minidom.parse(fileItem.filepath)
            except (xml.parsers.expat.ExpatError, IOError) as exc:
                self.progressBar.percentMore(percentEachPart)
                self.msgbox.display("Error reading file %s\n\n%s",
                                    (fileItem.filepath, str(exc).capitalize()))
                continue
            self.logger.debug("Parse finished.")
            self.progressBar.percentMore(percentEachPart)
            filetype = self.get_filetype(fileItem.filepath, self.dom)
            if filetype == "":
                self.progressBar.percentMore(percentEachPart)
                continue
            self.progressBar.percentMore(percentEachPart)

            prevLen = len(self.exampleDict)
            if filetype == "toolbox":
                self.read_toolbox_xml()
            elif filetype == "fieldworks":
                self.read_fieldworks_xml()
            if len(self.exampleDict) == prevLen:
                self.msgbox.display(
                    "Did not find any data in file %s", (fileItem.filepath,))
            self.progressBar.updatePercent(
                percentStart + percentEach * list_index)
            list_index += 1

        self.progressBar.updateFinishing()
        self.progressBar.close()
        return self.exampleDict

    def readWords(self, dataFields):
        """Return values in a flat list of words."""
        self.generateRefIDs = True
        self.read()
        words = []
        self.logger.debug("Grabbing " + str(len(dataFields)) + " data field(s)")
        for gramEx in self.exampleDict.values():
            for field in dataFields:
                if field.fieldType == DataField.FIELD:
                    try:
                        newList = gramEx.getByTitle(field.fieldValue)
                    except LogicError as exc:
                        self.msgbox.display(exc.msg, exc.msg_args)
                        return words
                    for text in newList:
                        newWord = WordInList()
                        newWord.text   = text
                        newWord.source = self.fileList[0].filepath
                        words.append(newWord)
        self.logger.debug("got " + str(len(words)) + " words")
        return words

    def get_filetype(self, filepath, dom):
        """Note to developer: Try to make it so that this function 
        can never silently fail, even if for example a JPEG file is attempted.
        """
        self.logger.debug("get_filetype BEGIN")
        filetype = ""
        if dom is None:
            self.msgbox.display("Error with file: %s", (filepath,))
            return ""
        docElem      = dom.documentElement
        docElemChild = None
        if docElem.hasChildNodes():
            if len(docElem.childNodes) >= 2:
                docElemChild = docElem.childNodes[1]
            else:
                docElemChild = docElem.childNodes[0]
        if docElemChild == None:
            self.msgbox.display(
                "File does not seem to be from Toolbox or FieldWorks: %s",
                (filepath,))
        elif docElem.nodeName == "database" and \
            re.match(r"[a-zA-Z0-9]+Group", docElemChild.nodeName):
                filetype = "toolbox"
        elif docElem.nodeName == "document" and \
            docElemChild.nodeName == "interlinear-text":
                filetype = "fieldworks"
        else:
            self.msgbox.display(
                "File does not seem to be from Toolbox or FieldWorks: %s",
                (filepath,))
        self.logger.debug("File type is " + filetype)
        return filetype

    def read_toolbox_xml(self):
        """Modifies self.exampleDict.

        Toolbox XML seems to follow this rule:
        If a marker has children, then it occurs within a group named after
        itself, and it is the first item.
        If there are other things associated with it,
        then they will also be in the group.
        """
        self.logger.debug("reading toolbox XML file")
        firstTime = True
        fieldTagsObj = GrammarTags(self.userVars)
        fieldTags    = fieldTagsObj.getTags()
        sentences    = self.dom.getElementsByTagName(
                       fieldTags["ref"] + "Group")
        for sentence in sentences:
            ex           = LingGramExample()
            ex.refText   = getTextByTagName(sentence, fieldTags["ref"])
            ex.freeTrans = getTextByTagName(sentence, fieldTags["ft"])
            orthoText    = getTextByTagName(sentence,
                                                     fieldTags["orth"])
            orthoWords   = orthoText.split()
            words        = sentence.getElementsByTagName(
                           fieldTags["text"] + "Group")
            for word in words:
                wordText  = getTextByTagName(word, fieldTags["text"])
                orthoWord = ""
                if len(orthoWords) > 0:
                    if len(words) == 1:
                        orthoWord = orthoText
                    else:
                        orthoWord = orthoWords.pop(0)
                morphemes = word.getElementsByTagName(
                           fieldTags["morph"] + "Group")
                mergedMorphemes = MergedMorphemes()
                for morpheme in morphemes:
                    morph = LingGramMorph()
                    morph.orth  = getTextByTagName(
                                  morpheme, fieldTags["orthm"])
                    morph.text  = getTextByTagName(
                                  morpheme, fieldTags["morph"])
                    morph.gloss = getTextByTagName(
                                  morpheme, fieldTags["gloss"])
                    morph.pos   = getTextByTagName(
                                  morpheme, fieldTags["pos"])
                    if self.SeparateMorphColumns:
                        ## store each morpheme separately
                        ex.appendMorphObj(morph)
                    else:
                        ## merge the morphemes
                        mergedMorphemes.add(morph)
                # } end for morpheme
                if not self.SeparateMorphColumns:
                    ex.appendMorphObj(
                        mergedMorphemes.getMorph(
                            self.ShowMorphemeBreaks))
                ex.appendWord(wordText, orthoWord)
            # } end for word in words
            if ex.refText == "" and self.generateRefIDs:
                InterlinReader.autoRefID += 1
                ex.refText = str(InterlinReader.autoRefID)
            if ex.refText != "":
                if self.prefix != "":
                    ex.refText = self.prefix + ex.refText
                ref_key = ex.refText.lower()
                self.exampleDict[ref_key] = ex
                if firstTime:
                    firstTime = False
                    self.suggestions.append(ex.refText)
        # } end for sentence in sentences:
        self.logger.debug("Read " + str(len(self.exampleDict)) + " examples.")

    def read_fieldworks_xml(self):
        """Modifies exampleDict (passed by reference)"""
        self.logger.debug("reading fieldworks XML file")
        firstTime = True
        paragraphs = self.dom.getElementsByTagName("paragraph")
        refTextPara = 1
        for paragraph in paragraphs:
            sentences = paragraph.getElementsByTagName("phrase")
            refTextSent = 1
            for sentence in sentences:
                ex           = LingGramExample()
                ex.refText   = str(refTextPara) + "." + str(refTextSent)
                words   = sentence.getElementsByTagName("word")
                items   = sentence.getElementsByTagName("item")
                for childNode in sentence.childNodes:
                    if childNode.attributes is None:
                        continue
                    if childNode.getAttribute("type") == "gls":
                        ex.freeTrans = getElemText(childNode)
                for word in words:
                    wordOrth = ""
                    wordText = ""
                    punct    = None
                    for childNode in word.childNodes:
                        if childNode.attributes is None:
                            continue
                        elif childNode.getAttribute("type") == "txt":
                            if wordText and not wordOrth:
                                wordOrth = wordText
                            wordText = getElemText(childNode)
                        elif childNode.getAttribute("type") == "punct":
                            punct = getElemText(childNode)
                            break
                    if punct is not None:
                        if len(ex.wordList) > 0:
                            ex.addPunctuation(punct)
                        else:
                            ex.appendWord(punct, punct)
                        continue
                    morphemes = word.getElementsByTagName("morph")
                    if len(morphemes) > 0:
                        mergedMorphemes = MergedMorphemes()
                        for morpheme in morphemes:
                            items = morpheme.getElementsByTagName("item")
                            morph = LingGramMorph()
                            for item in items:
                                if item.attributes is None:
                                    continue
                                itemType = item.getAttribute("type")
                                if itemType == "cf":
                                    if morph.text and not morph.orth:
                                        morph.orth = morph.text
                                    morph.text = getElemText(item)
                                elif itemType == "gls":
                                    morph.gloss = getElemText(item)
                                elif itemType == "msa":
                                    morph.pos = getElemText(item)

                            if self.SeparateMorphColumns:
                                ## store each morpheme separately
                                ex.appendMorphObj(morph)
                            else:
                                mergedMorphemes.add(morph)
                        # } end for morpheme
                        if not self.SeparateMorphColumns:
                            ex.appendMorphObj(
                                mergedMorphemes.getMorph(
                                    self.ShowMorphemeBreaks))
                    else:
                        ## Get word-level attributes instead of morpheme-level
                        morph = LingGramMorph()
                        items = word.getElementsByTagName("item")
                        for item in items:
                            if item.attributes is None:
                                continue
                            itemType = item.getAttribute("type")
                            if itemType == "gls":
                                if morph.gloss and not morph.orth:
                                    morph.orth = morph.gloss
                                morph.gloss = getElemText(item)
                            elif itemType == "msa":
                                morph.pos = getElemText(item)
                        ex.appendMorphObj(morph)
                    # } end if len(morphemes) > 0 
                    ex.appendWord(wordText, wordOrth)
                # } end for word in words
                if self.prefix != "":
                    ex.refText = self.prefix + ex.refText
                ref_key = ex.refText.lower()
                self.exampleDict[ref_key] = ex
                if firstTime:
                    firstTime = False
                    self.suggestions.append(ex.refText)
                refTextSent += 1
            # } end for sentence in sentences
            refTextPara += 1
        # } end for paragraph in paragraphs
        self.logger.debug("Read " + str(len(self.exampleDict)) + " examples.")

class MergedMorphemes(LingGramMorph):
    """Merge morphemes from data into a single dash-separated string."""

    def __init__(self):
        LingGramMorph.__init__(self)

    def add(self, morph):
        """@arg1 type LingGramMorph.
        Saves the values for later."""
        self.__addTo('orth',  morph.orth)
        self.__addTo('text',  morph.text)
        self.__addTo('gloss', morph.gloss)

        PREFIXES = ['det']
        if self.pos == "" or \
            (self.pos.lower() in PREFIXES and not morph.pos.startswith("-")):
            # Just grab the first part of speech.
            # (This works best for head-final languages.)
            self.pos = morph.pos

    def __addTo(self, varName, valToAdd):
        varVal = getattr(self, varName)
        DELIM = "-"     # delimiter between morphemes
        if varVal != "":
            if not valToAdd.startswith(DELIM) and not varVal.endswith(DELIM):
                varVal += DELIM
        varVal += valToAdd
        setattr(self, varName, varVal)

    def getMorph(self, ShowMorphemeBreaks):
        """@return type is a subclass of LingGramMorph"""
        if not ShowMorphemeBreaks:
            self.orth = ""
            self.text = ""
        return self

#-------------------------------------------------------------------------------
# End of InterlinReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of PhonReader.py
#-------------------------------------------------------------------------------



class PhonReader(FileReader):
    """For Phonology examples."""

    SUPPORTED_FORMATS = [
        ('lift', "LIFT dictionary format from FieldWorks (.lift)"),
            # also Phonology Assistant soon
        ('tbxphn', "Toolbox Phonology XML"),
        ('paxml', "Phonology Assistant PAXML (.paxml)")]

    def __init__(self, config, unoObjs, userVars):
        FileReader.__init__(self, unoObjs)
        self.filepath       = config.filepath
        self.phoneticWS     = config.phoneticWS
        self.userVars       = userVars
        self.suggestions    = []  # list of example ref numbers
        self.generateRefIDs = False

    def getSuggestions(self):
        return self.suggestions

    def read(self):
        """Read in the data.
        Returns dictionary of examples keyed by lowercase reference number.
        Examples are of type LingPhonExample.
        """
        self.logger.debug("read_file BEGIN")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        self.progressBar.updatePercent(20)

        self.exampleDict = {}  # dictionary to store examples
        self.suggestions = [] 
        filepath = self.filepath
        filetype = self.get_filetype(filepath)
        if filetype == "":
            self.progressBar.close()
            return dict()
        self.progressBar.updatePercent(30)
        self.logger.debug("Parsing file " + filepath)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", (filepath,))
            self.progressBar.close()
            return dict()
        try:
            self.dom = xml.dom.minidom.parse(filepath)
        except xml.parsers.expat.ExpatError as exc:
            self.msgbox.display("Error reading file %s\n\n%s",
                                (filepath, str(exc).capitalize()))
            self.progressBar.close()
            return dict()
        self.logger.debug("Parse finished.")
        self.progressBar.updatePercent(60)
        if filetype == "paxml":
            self.read_paxml_file()
        elif filetype == "lift":
            self.read_lift_file()
        elif filetype == "xml":
            self.read_toolbox_file()
        else:
            self.msgbox.display(
                "Unexpected file type %s", (filetype,))
            self.progressBar.close()
            return dict()
        if len(self.exampleDict) == 0:
            self.msgbox.display(
                "Did not find any data in file %s", (filepath,))
        self.progressBar.updateFinishing()
        self.progressBar.close()
        return self.exampleDict

    def readWords(self, dataFields):
        """Return values in a flat list of words."""
        self.generateRefIDs = True
        self.read()
        words = []
        for phonEx in self.exampleDict.values():
            for field in dataFields:
                if field.fieldType == DataField.FIELD:
                    text    = phonEx.getByTitle(field.fieldValue)
                    newWord = WordInList()
                    newWord.text   = text
                    newWord.source = self.filepath
                    words.append(newWord)
        return words

    def get_filetype(self, filepath):
        """Determines file type based on extension.
        Does not read file contents.
        """
        self.logger.debug("get_filetype BEGIN")
        filename = os.path.basename(filepath)
        filetype = ""
        if re.search(r"\.paxml$", filename):
            filetype = "paxml"
        elif re.search(r"\.lift$", filename):
            filetype = "lift"
        elif re.search(r"\.xml$", filename):
            filetype = "xml"
        else:
            self.msgbox.display("Unknown file type for %s", (filename,))
        self.logger.debug("File type is " + filetype)
        return filetype

    def read_paxml_file(self):
        """Read in the data from Phonology Assistant.
        Modifies self.examplesDict
        """
        self.logger.debug("reading Phonology Assistant file")
        fieldTags = dict()   # declaration to make pychecker happy
        fieldTags = {"phonetic" : "Phonetic",
                     "phonemic" : "Phonemic",
                     "gloss"    : "Gloss",
                     "ref"      : "Reference"}
        fieldHelper = PhonFieldHelper(self.exampleDict, self.suggestions)
        paRecords   = self.dom.getElementsByTagName("PaRecords")
        for paRecord in paRecords:
            fieldHelper.reset()
            experimentalTrans = None
            for fieldsNode in paRecord.childNodes:
                if fieldsNode.localName == "Fields":
                    fields = fieldsNode.getElementsByTagName("FieldValueInfo")
                    for field in fields:
                        if field.attributes is None:
                            continue
                        name  = field.getAttribute("FieldName")
                        value = field.getAttribute("Value")
                        for fieldName, tagName in fieldTags.items():
                            if name == tagName:
                                fieldHelper.add(fieldName, value)
                elif fieldsNode.localName == "ParsedFields":
                    fields = fieldsNode.getElementsByTagName("FieldValueInfo")
                    for field in fields:
                        if field.attributes is None:
                            continue
                        name  = field.getAttribute("FieldName")
                        value = field.getAttribute("Value")
                        if name == "Phonetic":
                            experimentalTrans = value
            if experimentalTrans:
                if self.userVars.getInt("ExperTrans_Phonemic") == 1:
                    fieldHelper.add("phonemic", experimentalTrans)
                else:
                    fieldHelper.add("phonetic", experimentalTrans)
            if fieldHelper.hasContents():
                fieldHelper.addEx(self.generateRefIDs)
        self.logger.debug("finished reading PA file")

    def read_lift_file(self):
        """Read in the LIFT data from FieldWorks.
        Modifies self.examplesDict
        """
        self.logger.debug("reading LIFT file")
        fieldHelper = PhonFieldHelper(self.exampleDict, self.suggestions)
        entries = self.dom.getElementsByTagName("entry")
        for entry in entries:
            fieldHelper.reset()
            lexical_units = entry.getElementsByTagName("lexical-unit")
            if len(lexical_units) > 0:
                lexical_unit = lexical_units[0]
                fieldHelper.add("phonemic", getTextByWS(
                    lexical_unit, self.phoneticWS))
            pronounces = entry.getElementsByTagName("pronunciation")
            if len(pronounces) > 0:
                pronounce = pronounces[0]
                fieldHelper.add("phonetic", getTextByWS(
                    pronounce, self.phoneticWS))
            senses = entry.getElementsByTagName("sense")
            fields = entry.getElementsByTagName("field")
            if len(senses) > 0:
                sense = senses[0]
                glossElems = sense.getElementsByTagName("gloss")
                if len(glossElems) > 0:
                    glossElem = glossElems[0]
                    fieldHelper.add("gloss", getTextByWS(
                        glossElem, ""))
                notes = sense.getElementsByTagName("note")
                for note in notes:
                    if note.attributes is None:
                        continue
                    if note.getAttribute("type") == "source":   # first choice
                        if fieldHelper.vals["ref"] == "":
                            fieldHelper.add("ref",
                                getTextByWS(note, ""))
                for note in notes:
                    if note.attributes is None:
                        continue
                    if note.getAttribute("type") == "reference": # second choice
                        if fieldHelper.vals["ref"] == "":
                            fieldHelper.add("ref",
                                getTextByWS(note, ""))
            for field in fields:
                if field.attributes is None:
                    continue
                if field.getAttribute("type") == "Reference":   # third choice
                    if fieldHelper.vals["ref"] == "":
                        fieldHelper.add("ref", getTextByWS(field, ""))
            if fieldHelper.hasContents():
                fieldHelper.addEx(self.generateRefIDs)
        self.logger.debug("finished reading LIFT file")

    def read_toolbox_file(self):
        """Read in the data exported directly from Toolbox.
        Modifies self.examplesDict
        """
        self.logger.debug("reading Toolbox file")
        fieldTagsObj = PhonologyTags(self.userVars)
        fieldTags    = fieldTagsObj.getTags()
        fieldHelper  = PhonFieldHelper(self.exampleDict, self.suggestions)
        groups = self.dom.getElementsByTagName("phtGroup")
        self.logger.debug(str(len(groups)) + " pht groups")
        for group in groups:
            fieldHelper.reset()
            for fieldName, tagName in fieldTags.items():
                txt = getTextByTagName(group, tagName)
                if txt != "":
                    fieldHelper.add(fieldName, txt)
            if fieldHelper.hasContents():
                fieldHelper.addEx(self.generateRefIDs)
        self.logger.debug("finished reading Toolbox file")

class PhonFieldHelper:
    """A data structure useful when reading phonology data.
    Values can be stored by string keys (using a dictionary).
    """
    autoRefID = 0   # used if we need to generate IDs for keys to exampleDict

    def __init__(self, exampleDict, suggestions):
        self.exampleDict = exampleDict
        self.suggestions = suggestions
        self.vals        = {}
        self.firstTime   = True
        self.reset()

    def reset(self):
        self.vals["ref"]      = ""
        self.vals["phonetic"] = ""
        self.vals["phonemic"] = ""
        self.vals["gloss"]    = ""
        self.hasSomeContents  = False

    def hasContents(self):
        return self.hasSomeContents

    def add(self, fieldname, val):
        self.vals[fieldname] = val
        self.hasSomeContents = True

    def addEx(self, generateRefIDs):
        ex          = LingPhonExample()
        ex.refText  = self.vals["ref"]
        ex.phonetic = self.vals["phonetic"] 
        ex.phonemic = self.vals["phonemic"]
        ex.gloss    = self.vals["gloss"]
        if ex.refText == "" and generateRefIDs:
            PhonFieldHelper.autoRefID += 1
            ex.refText = str(PhonFieldHelper.autoRefID)
        if ex.refText != "":
            self.exampleDict[ex.refText.lower()] = ex
            if self.firstTime:
                self.firstTime = False
                self.suggestions.append(ex.refText)
        self.reset()
#-------------------------------------------------------------------------------
# End of PhonReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of WordsReader.py
#-------------------------------------------------------------------------------



class WordsReader(FileReader):

    SUPPORTED_FORMATS = [
        ("spellingStatus", "Paratext Spelling Status XML"),
        ]

    def __init__(self, fileconfig, unoObjs):
        FileReader.__init__(self, unoObjs)
        self.fileconfig  = fileconfig   # type FileItemList.WordListFileItem

    def read(self):
        """Read in the data.
        Returns list with elements of type WordInList.
        """
        self.logger.debug("read_file BEGIN")
        self.progressBar.show()
        self.progressBar.updateBeginning()
        self.progressBar.updatePercent(20)

        self.words = [] # list to store examples
        filepath = self.fileconfig.filepath
        self.logger.debug("Parsing file " + filepath)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", (filepath,))
            self.progressBar.close()
            return list()
        try:
            self.dom = xml.dom.minidom.parse(filepath)
        except xml.parsers.expat.ExpatError as exc:
            self.msgbox.display("Error reading file %s\n\n%s",
                                (filepath, str(exc).capitalize()))
            self.progressBar.close()
            return list()
        self.logger.debug("Parse finished.")
        self.progressBar.updatePercent(60)
        if self.fileconfig.filetype == "spellingStatus":
            self.read_spellingStatus_file()
        else:
            self.msgbox.display(
                "Unexpected file type %s", (self.fileconfig.filetype,))
            self.progressBar.close()
            return list()
        if len(self.words) == 0:
            self.msgbox.display(
                "Did not find any data in file %s", (filepath,))
        self.progressBar.updateFinishing()
        self.progressBar.close()
        return self.words

    def read_spellingStatus_file(self):
        """Read in the data. Modifies self.words"""
        self.logger.debug("reading Spelling Status file")

        statuses = self.dom.getElementsByTagName("Status")
        for status in statuses:
            if status.attributes is None:
                continue
            text  = status.getAttribute("Word")
            state = status.getAttribute("State")
            if text == "":
                continue
            word = WordInList()
            word.text   = text
            word.source = self.fileconfig.filepath
            if state == "R":
                word.isCorrect = True
            elif state == "W":
                word.isCorrect = False
                if not self.fileconfig.includeMisspellings:
                    continue
                correction = getTextByTagName(status, "Correction")
                if correction != "":
                    word.correction = correction
                    self.logger.debug("got correction")
            self.words.append(word)
        self.logger.debug("finished reading file")

#-------------------------------------------------------------------------------
# End of WordsReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of WordList.py
#-------------------------------------------------------------------------------



class WordList:
    def __init__(self, writerUnoObjs, fileItems, columnOrder, userVars):
        self.unoObjs     = writerUnoObjs
        self.fileItems   = fileItems    # FileItemList of WordListFileItem
        self.columnOrder = columnOrder
        self.userVars    = userVars
        self.logger      = logging.getLogger("lingt.App.WordList")
        self.msgbox      = MessageBox(self.unoObjs)
        self.words       = []

    def generateList(self, punctToRemove, outputToCalc=True):
        """
        Harvest words from various files.
        If outputToCalc is True, then output a word list in Calc.
        """
        self.logger.debug("generateList BEGIN")

        all_words_read = []     # all the words that are read from files

        for fileItem in self.fileItems:
            new_words = None
            if fileItem.filetype in supportedNames():
                wordsReader = WordsReader(fileItem, self.unoObjs)
                new_words = wordsReader.read()
            elif fileItem.filetype in supportedNames():
                wordsReader = SFM_Reader(fileItem, self.unoObjs)
                try:
                    new_words = wordsReader.read()
                except LingtError as exc:
                    self.msgbox.display(exc.msg, exc.msg_args)
                    continue
            elif fileItem.filetype in supportedNames():
                config = ConfigOptions()
                config.ShowMorphemeBreaks   = True
                config.SeparateMorphColumns = True
                lingExFileItem = LingExFileItem()
                lingExFileItem.filepath = fileItem.filepath
                config.fileList = [lingExFileItem]
                reader = InterlinReader(config, self.unoObjs, self.userVars)
                new_words = reader.readWords(fileItem.dataFields)
            elif fileItem.filetype in supportedNames():
                config = ConfigOptions()
                config.filepath   = fileItem.filepath
                config.phoneticWS = fileItem.writingSystem
                reader = PhonReader(config, self.unoObjs, self.userVars)
                new_words = reader.readWords(fileItem.dataFields)
            elif fileItem.filetype in supportedNames():
                varname      = "MatchLimit"
                matchesLimit = 0
                if self.userVars.isEmpty(varname):
                    self.userVars.set(varname, 0)  # make sure it exists
                else:
                    matchesLimit = self.userVars.getInt(varname)
                    self.logger.debug(
                        "Using match limit " + str(matchesLimit))
                wordsReader = DocReader(fileItem, self.unoObjs, matchesLimit)
                new_words = wordsReader.read()
            elif fileItem.filetype in CalcFileReader.supportedNames():
                wordsReader = CalcFileReader(self.unoObjs)
                wordsReader.setFileConfig(fileItem)
                new_words = wordsReader.read()
            if new_words:
                self.logger.debug("New words: " + str(len(new_words)))
                all_words_read.extend(new_words)
                self.logger.debug("Word count: " + str(len(all_words_read)))
        self.logger.debug("Word count: " + str(len(all_words_read)))

        ## Sort and group list

        progressBar = ProgressBar(self.unoObjs, "Sorting...")
        progressBar.show()
        progressBar.updateBeginning()

        # split by whitespace
        for word_read in all_words_read[:]:   # iterate over a copy
            text = word_read.text
            text = text.strip()
            if re.search(r'\s', text):
                text_parts = re.split(r'\s+', text)
                if not fileItem.splitByWhitespace:
                    text_parts = [" ".join(text_parts)]
                for i,part in enumerate(text_parts):
                    if i == 0:
                        word_read.text = part
                    else:
                        newWord = WordInList()
                        newWord.text       = part
                        newWord.source     = word_read.source
                        newWord.isCorrect  = word_read.isCorrect
                        newWord.correction = word_read.correction
                        all_words_read.append(newWord)
        self.logger.debug("Word count: " + str(len(all_words_read)))

        # remove outer punctuation
        punctToRemove = re.sub(r"\s+", "", punctToRemove)
        self.logger.debug("punctToRemove = " + repr(punctToRemove))
        for word_read in all_words_read:
            word_read.text = word_read.text.strip()    # remove whitespace
            word_read.text = word_read.text.strip(punctToRemove)
            #self.logger.debug("text is now " + unicode(word_read.text))
 
        # group equal words
        unique_words = dict()
        for word_read in all_words_read:
            text = word_read.text
            if not text:
                continue
            if text in unique_words:
                word = unique_words[text]
            else:
                word = WordInList()
                word.text       = text
                word.isCorrect  = word_read.isCorrect
                word.correction = word_read.correction
                unique_words[text] = word
            word.occurrences += 1
            if word_read.source in word.sources:
                word.sources[word_read.source] += 1
            else:
                word.sources[word_read.source] = 1
        self.logger.debug("Word count: " + str(len(unique_words)))

        # sort
        progressBar.updatePercent(80)
        self.words = []
        for text in sorted(unique_words.keys()):
            self.words.append(unique_words[text])
        self.logger.debug("Word count: " + str(len(self.words)))

        ## Generate list in calc

        progressBar.updateFinishing()
        progressBar.close()
        if len(self.words) > 0 or self.fileItems.getCount() == 0:
            if outputToCalc:
                progressBar = ProgressBar(self.unoObjs, "Generating List...")
                progressBar.show()
                progressBar.updateBeginning()

                listOutput  = WordListIO(self.unoObjs, self.columnOrder)
                ok          = listOutput.outputList(self.words, progressBar)
                self.msgbox = listOutput.getMsgbox()    # for Calc spreadsheet

                ## Copy some user vars for the Spelling component.

                USERVAR_PREFIX_SP = "LTsp_"  # Ling Tools Spelling variables
                userVarsSp = UserVars(USERVAR_PREFIX_SP, self.unoObjs.document,
                                      self.logger)
                varname = "HasSettings"
                userVarsSp.set(varname, self.userVars.get(varname))
                columnOrderSp = ColumnOrder(userVarsSp)
                columnOrderSp.sortOrder = self.columnOrder.sortOrder
                columnOrderSp.saveUserVars()

                # Initialize some user vars for Calc dialogs. We do this here
                # to reset properly if a new word list is made.
                self.userVars.set("ConvSourceColumn",
                    self.columnOrder.getColLetter(
                    self.columnOrder.COL_WORD))
                self.userVars.set("ConvTargetColumn",
                    self.columnOrder.getColLetter(
                    self.columnOrder.COL_CONVERTED1))
                userVarsSp.set("CurrentRow", "")

                progressBar.updateFinishing()
                progressBar.close()
                if ok:
                    self.msgbox.display(
                        "Made list of %d words.", (len(self.words)))
            else:
                self.msgbox.display(
                    "Found %d words.", (len(self.words)))
        else:
            self.msgbox.display("Did not find any words for the list.")


#-------------------------------------------------------------------------------
# End of WordList.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of SpellingChecks_test.py
#-------------------------------------------------------------------------------




modifiedFunctions = set()

def modifyClass_makeDlg(klass):
    """
    Modify makeDlg() to call useDialog() instead of execute().
    As a result, the dialog does not wait for user interaction.
    """
    fnStr = "%s.makeDlg" % (klass)
    global modifiedFunctions
    if fnStr in modifiedFunctions:
        return
    modifiedFunctions.add(fnStr)

    code = inspect.getsource(klass.makeDlg)
    code = re.sub("makeDlg", "makeDlgModified", code)
    code = re.sub("dlg.execute", "self.useDialog", code)
    pat  = re.compile("^    ", re.M)
    code = re.sub(pat, "", code)    # decrease indent
    #print(code)  # for debugging
    exec(code, globals())
    klass.makeDlg = makeDlgModified

class SpellingChecksTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs     = unoObjsForCurrentDoc()
        self.logger      = logging.getLogger("lingt.TestSpellingChecks")
        modifyClass_makeDlg(DlgSpellingReplace)
        modifyMsgboxDisplay()
        USERVAR_PREFIX  = "LTsp_"  # Spelling variables
        self.userVars   = UserVars(
                          USERVAR_PREFIX, self.unoObjs.document, self.logger)
        self.msgbox     = MessageBox(self.unoObjs)

    def testAffixesEN(self):
        oText = self.unoObjs.text           # shorthand variable name
        oVC   = self.unoObjs.viewcursor     # shorthand variable name
        oText.insertString(oVC, "My dog is running and jumping.", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        oText.insertString(oVC, "Now he can jump.", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)
        oText.insertString(oVC, "Yesterday he jumped.", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)

        columnOrder = ColumnOrder(self.userVars)
        fileItemList = FileItemList(
                       WordListFileItem, self.unoObjs,
                       self.userVars)
        wordList = WordList(
                   self.unoObjs, fileItemList, columnOrder, self.userVars)
        punct = ""
        try:
            wordList.generateList(punct)
        except MsgSentException as exc:
            self.assertTrue(exc.msg.startswith("Made list"))
        else:
            self.fail("Expected error message.")

        doclist = self.unoObjs.getOpenDocs('calc')
        props = (
            createProp('FilterName', 0),
            createProp('Overwrite',  1),
        )
        FILEPATH = os.path.join(
                   os.path.expanduser("~"), "Documents", "wordListTemp.ods")
        FILE_URL = uno.systemPathToFileUrl(FILEPATH)
        #if FILEPATH.startswith("/"):
        #    FILE_URL = "file://"  + FILEPATH
        #else:
        #    FILE_URL = "file:///" + FILEPATH
        wordListDoc = doclist[0]
        wordListDoc.document.storeAsURL(FILE_URL, props)

        app = SpellingChecker(
              self.unoObjs, self.userVars, self.logger)
        config = ConfigOptions()
        config.filepath      = FILEPATH
        config.whichTask     = 'SpellCheck'
        config.whichScope    = 'WholeDoc'
        config.affixes       = "-ing\n-ed"
        config.scopeStyle    = ""
        config.scopeFont     = ""
        config.fontType      = ""
        config.scopeSFMs     = ""
        config.scopeLanguage = ""
        config.matchesLimit  = -1
        config.punctuation   = "."
        config.matchCase     = False
        app.setConfig(config)

        def useDialog(selfNew):
            selfNew.actionPerformed(MyActionEvent("Add"))
        DlgSpellingReplace.useDialog = useDialog
        try:
            app.doSearch()
        except MsgSentException as exc:
            self.assertEqual(exc.msg, "Spell check finished.")
        else:
            self.fail("Expected error message.")

        reader     = SpreadsheetReader(wordListDoc)
        stringList = reader.getColumnStringList("A", True)
        self.assertTrue(   "jump" in    stringList)
        self.assertFalse("jumping" in stringList)
        self.assertFalse("jumped" in  stringList)
        self.assertTrue(   "runn" in    stringList)
        self.assertFalse("running" in stringList)
        wordListDoc.document.close(True)
        self.unoObjs.window.setFocus()  # so that getCurrentController() works


#-------------------------------------------------------------------------------
# End of SpellingChecks_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of ExUpdater.py
#-------------------------------------------------------------------------------



LINE_BREAK = uno.getConstantByName(
    "com.sun.star.text.ControlCharacter.LINE_BREAK") 
PARAGRAPH_BREAK = uno.getConstantByName(
    "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK") 
PAGE_BEFORE = uno.getConstantByName(
    "com.sun.star.style.BreakType.PAGE_BEFORE")
BREAK_NONE = uno.getConstantByName(
    "com.sun.star.style.BreakType.NONE")

class ExUpdater:

    def __init__(self, unoObjs, exampleManager, VAR_PREFIX):
        self.unoObjs          = unoObjs
        self.exampleManager   = exampleManager
        self.VAR_PREFIX       = VAR_PREFIX
        self.logger           = logging.getLogger("lingt.Access.ExUpdater")
        self.compDoc          = None    # comparison writer doc
        self.MakeCompDoc      = True
        self.calledSetMainDoc = False
        self.logger.debug("ExUpdater init() finished")

    def doNotMakeCompDoc(self):
        self.MakeCompDoc = False

    def gotoAfterEx(self):
        """
        Move viewcursor to the next line.
        Before this method is called, the cursor is expected to be at
        the reference number of an example.
        """
        self.logger.debug("gotoAfterEx BEGIN")
        self.unoObjs.viewcursor.goDown(1, False)
        self.unoObjs.viewcursor.gotoStartOfLine(False)

    def moveExNumber(self):
        """
        Move the example number from the old example to the new one.

        Before this method is called, the cursor is expected to be one
        line below two tables with examples, and there should be no
        empty line between the two tables -- they should be touching.
        """
        self.logger.debug("moveExNumber BEGIN")
        oVC = self.unoObjs.viewcursor   # shorthand variable name

        ## Delete paragraph break inserted by OutputManager.insertEx()

        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Delete", "", 0, ())

        ## Go to ex number of old example.

        oVC.goUp(2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        oTextCurs = oVC.getText().createTextCursorByRange(oVC)
        strval    = oTextCurs.getString()

        self.logger.debug("Cut begin")
        # FIXME: The following line can cause a crash in some cases.
        #        It happened when repeatedly updating the same example.
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Cut", "", 0, ())
        self.logger.debug("Cut finished")

        ## Cut ex number from old example.
        ## Paste unformatted text of ex number.

        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Cut", "", 0, ())
        uno_args = (
            createProp("SelectedFormat", 1),    # paste unformatted
        )
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:ClipboardFormatItems", "", 0, uno_args) 

        ## Paste ex number into new example

        oVC.goDown(1, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Paste", "", 0, ()) 

        # If a new example was just added and then updated,
        # we need to save this range to add the example number.
        # The original range will be invalid now.
        if strval == "()":
            oVC.goLeft(1, False)
            self.exampleManager.exnumRanges.append(oVC.getStart())
        self.logger.debug("moveExNumber END")

    def moveExamplesToNewDoc(self):
        """Move the old example to a new comparison document, and copy the
        new example to the comparison document as well.
        """
        self.logger.debug("moveExamplesToNewDoc BEGIN")

        ## Open comparison document

        if self.MakeCompDoc:
            didCreate = self.createComparisonDoc()

        ## Cut and paste old example

        self.logger.debug("cutting old example")
        self.unoObjs.viewcursor.goUp(1, False)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Copy", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:DeleteTable", "", 0, ())
        if self.MakeCompDoc:
            self.pasteExample("old", insertPageBreak=not didCreate)

        ## Copy and paste new example

        if self.MakeCompDoc:
            self.logger.debug("copying new example")
            if self.unoObjs.viewcursor.TextTable:
                self.mainTableName = self.unoObjs.viewcursor.TextTable.getName()
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:Copy", "", 0, ())
                self.pasteExample("new")
            else:
                self.compDoc.text.insertControlCharacter(
                    self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
                self.compDoc.text.insertString(
                    self.compDoc.viewcursor,
                    "There was a problem with this example.", 0)
                self.compDoc.text.insertControlCharacter(
                    self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)

        ## Return to main doc and position cursor after example
        ## - This is important so that "Find Next" doesn't repeat this ex.

        self.unoObjs.window.toFront()
        oVC = self.unoObjs.viewcursor
        if oVC.TextTable:
            self.logger.debug("in TextTable")
            self.unoObjs.controller.select(oVC.TextTable)
            firstCell = oVC.Cell
            oVC.gotoEnd(False) # go to end of cell if cell is not empty
            if oVC.Cell.CellName == firstCell.CellName:
                oVC.gotoEnd(False) # go to end of last cell in table
        self.unoObjs.viewcursor.goRight(1, False)
        self.logger.debug("moveExamplesToNewDoc END")

    def disposing(self, unused_aEvent):
        self.logger.debug("Disposing")
        self.compDoc = None
        return None 

    def createComparisonDoc(self):
        """
        Create a temporary empty writer doc for comparing examples.
        If the main file has a saved path, then only one comparison doc
        should be created.
        Returns True if a new document was created.
        """
        if self.compDoc is not None:
            if self.compDoc.document is not None:
                ## Document is already open
                return False

        varname         = "ComparisonDocForFile"
        currentFilepath = None  # file path of main document
        url             = self.unoObjs.document.getURL()
        if url:
            currentFilepath = uno.fileUrlToSystemPath(url)
            doclist = self.unoObjs.getOpenDocs('writer')
            for docUnoObjs in doclist:
                self.logger.debug("Checking writer document for settings.")
                userVars = UserVars(
                           self.VAR_PREFIX, docUnoObjs.document, self.logger)
                if not userVars.isEmpty(varname):
                    varFilepath = userVars.get(varname)
                    if varFilepath == currentFilepath:
                        self.logger.debug("found comparison doc")
                        self.compDoc = docUnoObjs
                        return False
                    else:
                        self.logger.debug("%s != %s" % 
                            (varFilepath, currentFilepath))

        self.logger.debug("opening new document for comparison")
        newDoc = self.unoObjs.desktop.loadComponentFromURL(
                 "private:factory/swriter", "_blank", 0, ())
        self.compDoc = self.unoObjs.getDocObjs(newDoc)
        self.compDoc.text.insertString(self.compDoc.viewcursor,
            "Here are the changes that have been made.  " +
            "You may want to look through these changes, and make any " +
            "corrections in the main document.  " +
            "When finished checking, just close this window without saving.", 0)
        self.compDoc.text.insertControlCharacter(
            self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
        self.compDoc.text.insertControlCharacter(
            self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
        if currentFilepath:
            userVars = UserVars(
                       self.VAR_PREFIX, self.compDoc.document, self.logger)
            userVars.set(varname, currentFilepath)
        self.logger.debug("createComparisonDoc() END")
        return True

    def pasteExample(self, oldOrNew, insertPageBreak=False):
        self.logger.debug("pasting " + oldOrNew + "example")
        self.compDoc.viewcursor.gotoEnd(False)
        self.compDoc.viewcursor.jumpToLastPage()
        self.compDoc.viewcursor.jumpToEndOfPage()
        if insertPageBreak:
            self.insertPageBreak(self.compDoc.text, self.compDoc.viewcursor)
        if oldOrNew == "old":
            self.compDoc.text.insertControlCharacter(
                self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
        self.compDoc.viewcursor.goUp(1, False)

        bgcolor = int("FFFFCC", 16)   # yellow
        if oldOrNew == "old":
            bgcolor = int("F1F7FC", 16)   # light bluish grey 
        self.insertSection(bgcolor)
        self.compDoc.viewcursor.gotoRange(self.section.getAnchor(), False)

        title = oldOrNew.capitalize() + ":"
        self.compDoc.text.insertString(
            self.compDoc.viewcursor, title, 0)
        self.compDoc.text.insertControlCharacter(
            self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
        self.compDoc.text.insertControlCharacter(
            self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
        self.compDoc.text.insertControlCharacter(
            self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
        if oldOrNew == "old":
            self.compDoc.viewcursor.goUp(2, False)
            self.compDoc.dispatcher.executeDispatch(
                self.compDoc.frame, ".uno:Paste", "", 0, ()) 
        else:
            self.compDoc.text.insertControlCharacter(
                self.compDoc.viewcursor, PARAGRAPH_BREAK, 0)
            self.compDoc.viewcursor.goUp(3, False)
            self.compDoc.dispatcher.executeDispatch(
                self.compDoc.frame, ".uno:Paste", "", 0, ()) 

            ## Insert button to go to example in main doc

            self.logger.debug("Inserting button")
            self.compDoc.viewcursor.collapseToEnd()
            self.unoObjs.url = self.unoObjs.document.getURL()
            if self.unoObjs.url:
                oButtonModel = self.addNewButton()
                self.assignAction(oButtonModel, self.mainTableName)
                self.compDoc.controller.setFormDesignMode(False)
            else:
                self.logger.debug("Main doc has no filename.")
        self.logger.debug("pasteExample() FINISHED")

    def addNewButton(self):
        self.logger.debug("addNewButton()")
        oControlShape = self.compDoc.document.createInstance(
            "com.sun.star.drawing.ControlShape")
        aPoint = uno.createUnoStruct("com.sun.star.awt.Point")
        aPoint.X = 1000
        aPoint.Y = 1000
        oControlShape.setPosition(aPoint)
        aSize  = uno.createUnoStruct("com.sun.star.awt.Size")
        aSize.Width = 6000
        aSize.Height = 800
        oControlShape.setSize(aSize)
        oControlShape.AnchorType = uno.getConstantByName(
            "com.sun.star.text.TextContentAnchorType.AS_CHARACTER" ) 
        oButtonModel = self.unoObjs.smgr.createInstance(
                       "com.sun.star.form.component.CommandButton")
        oButtonModel.Label = "Go to example in main document"
        oControlShape.setControl(oButtonModel)
        self.compDoc.text.insertTextContent(
            self.compDoc.viewcursor, oControlShape, False)

        return oButtonModel

        # This approach didn't seem to work for URLs.
        #
        #sURL = "file:///D:/Jim/computing/Office/" + \
        #       "OOo%20Linguistic%20Tools/testing.odt#table1|table"
        #oButtonModel.ButtonType = uno.Enum(
        #    "com.sun.star.form.FormButtonType", "URL")
        #oButtonModel.TargetFrame = "_blank"
        #oButtonModel.TargetURL = sURL

        return nIndex

    def assignAction(self, oButtonModel, sDestination):
        """assign sScriptURL event as css.awt.XActionListener::actionPerformed.
        event is assigned to the control described by the nIndex in the oForm
        container
        """
        self.logger.debug("assignAction() BEGIN")
        self.logger.debug("specify which is the main document")
        if not self.calledSetMainDoc:
            sMacro = "macro:///LingToolsBasic.ModuleMain.setMainDocURL(\"" + \
                     self.unoObjs.url + "\")"
            self.logger.debug(sMacro)
            self.unoObjs.dispatcher.executeDispatch(
                self.compDoc.frame, sMacro, "", 0, ())
            self.calledSetMainDoc = True

        self.logger.debug("getting index of button")
        oDrawPage = self.compDoc.document.getDrawPage()
        oForm     = oDrawPage.getForms().getByIndex(0)
        self.logger.debug("looking for button: " + oButtonModel.getName())
        self.logger.debug("Form has " + str(oForm.getCount()) + " elements")
        nIndex = -1
        for i in range(0, oForm.getCount()):
            self.logger.debug(oForm.getByIndex(i).getName())
            if oForm.getByIndex(i).getName() == oButtonModel.getName():
                nIndex = i
        self.logger.debug("nIndex=" + str(nIndex))

        self.logger.debug("assigning action")
        oButtonModel.HelpText = sDestination   # a trick to pass the parameter
        sScriptURL = "vnd.sun.star.script:" + \
                     "LingToolsBasic.ModuleMain.GoToTableInOtherDoc?" + \
                     "language=Basic&location=application"
        aEvent = uno.createUnoStruct(
                 "com.sun.star.script.ScriptEventDescriptor")
        aEvent.AddListenerParam = ""
        aEvent.EventMethod = "actionPerformed"
        aEvent.ListenerType = "XActionListener"
        aEvent.ScriptCode = sScriptURL
        aEvent.ScriptType = "Script"
        oForm.registerScriptEvent(nIndex, aEvent)
        self.logger.debug("assignAction() END")

    def insertSection(self, bgcolor):
        self.logger.debug("insertSection()")
        self.section = self.compDoc.document.createInstance(
            "com.sun.star.text.TextSection")
        self.section.BackColor = bgcolor
        self.compDoc.text.insertTextContent(
            self.compDoc.viewcursor, self.section, False)

    def insertPageBreak(self, oText, oCursor):
        """Inserts a paragraph that has a page break."""
        oText.insertControlCharacter(oCursor, PARAGRAPH_BREAK, 0)
        oCursor.setPropertyValue('BreakType', PAGE_BEFORE)

    def deleteOldPhonEx(self):
        """
        Viewcursor should be at end of line of new example,
        with old example on line above.
        One line below new example, a new paragraph break has been inserted.
        """
        self.logger.debug("deleteOldPhonEx() BEGIN")
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        oVC.goUp(1, False)

        ## delete line
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SwBackspace", "", 0, ())

        ## delete paragraph break inserted by OutputManager.insertEx()
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:Delete", "", 0, ())

        ## finish
        oVC.gotoEndOfLine(False)
        self.logger.debug("deleteOldPhonEx() FINISH")

#-------------------------------------------------------------------------------
# End of ExUpdater.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Tables.py
#-------------------------------------------------------------------------------



class Tables:

    def __init__(self, exnumRanges, config, unoObjs, styles):
        self.exnumRanges = exnumRanges
        self.unoObjs     = unoObjs
        self.styles      = styles
        self.logger      = logging.getLogger("lingt.Access.Tables")
        self.msgbox      = MessageBox(unoObjs)
        self.updatingEx  = False

        self.styleNames             = config.styleNames
        self.MakeOuterTable         = config.MakeOuterTable
        self.MethodFrames           = config.MethodFrames
        self.ShowOrthoTextLine      = config.ShowOrthoTextLine
        self.ShowText               = config.ShowText
        self.ShowOrthoMorphLine     = config.ShowOrthoMorphLine
        self.ShowMorphemeBreaks     = config.ShowMorphemeBreaks
        self.ShowPartOfSpeech       = config.ShowPartOfSpeech
        self.InsertNumbering        = config.InsertNumbering
        self.SeparateMorphColumns   = config.SeparateMorphColumns
        self.POS_AboveGloss         = config.POS_AboveGloss
        self.startingOuterRowHeight = config.startingOuterRowHeight
        self.tableBottomMargin      = config.tableBottomMargin
        self.numberingColumnWidth   = config.numberingColumnWidth

    def outerTableAndNumbering(self, mainTextcursor, updatingEx):
        """Create outer table with example number in smaller left column and
        data in larger right column.
        Leaves viewcursor in smaller left column to the right of "()"
        """
        self.logger.debug("outerTableAndNumbering BEGIN")
        self.updatingEx  = updatingEx
        unoObjs          = self.unoObjs  # shorthand variable name
        self.inner_table = None
        self.innerTableMarkers = []

        ## Create outer table

        if self.MakeOuterTable:
            outer_table = unoObjs.document.createInstance(
                "com.sun.star.text.TextTable")
            outer_table.initialize(1, 2)    # 1 row, 2 columns
            unoObjs.text.insertTextContent(mainTextcursor, outer_table, False)
            self.set_noTableSpacing(outer_table)
            outer_table.Split        = False # Text Flow -> don't split pages
            outer_table.KeepTogether = True  # Text Flow -> keep w/next para
            rows = outer_table.getRows()
            self.top_row = rows.getByIndex(0)
            self.fixedSizeOuterTable()
            self.logger.debug("Created outer table " + outer_table.getName())

            cell   = outer_table.getCellByPosition(0, 0)  # first col
            cursor = cell.createTextCursor()
            self.innerTableNumbering = False
            self.insertNumber(cell, cursor, outer_table)

            # Get cursor in main column
            self.textOuter   = outer_table.getCellByPosition(1, 0) # second col
            self.cursorOuter = self.textOuter.createTextCursor()
        else:
            self.textOuter   = unoObjs.text
            self.cursorOuter = unoObjs.text.createTextCursorByRange(
                                mainTextcursor.getStart())
            if self.MethodFrames:
                self.innerTableNumbering = False
                self.insertNumber(self.textOuter, self.cursorOuter, None)

        self.logger.debug("outerTableAndNumbering END")
        return self.textOuter, self.cursorOuter

    def fixedSizeOuterTable(self):
        """We set the table to a fixed size because inserting contents is
        faster this way.
        Requires self.top_row.
        """
        if self.MakeOuterTable:
            self.top_row.IsAutoHeight = False
            self.top_row.Height = \
                self.startingOuterRowHeight * 2540   # inches

    def resizeOuterTable(self):
        """After the contents of the table are inserted, call this method
        to size the table correctly.
        """
        if self.MakeOuterTable:
            self.top_row.IsAutoHeight = True

    def createInnerTable(self):
        """Create a new inner table.
        Requires self.cellOuter and self.textOuter.
        """
        self.logger.debug("Preparing to create inner table.")

        self.firstInnerTable = False
        if self.inner_table is None:
            self.firstInnerTable = True

        self.INNER_TABLE_HEIGHT = 6
        if not self.ShowOrthoTextLine:  self.INNER_TABLE_HEIGHT -= 1
        if not self.ShowText:           self.INNER_TABLE_HEIGHT -= 1
        if not self.ShowOrthoMorphLine: self.INNER_TABLE_HEIGHT -= 1
        if not self.ShowMorphemeBreaks: self.INNER_TABLE_HEIGHT -= 1
        if not self.ShowPartOfSpeech:   self.INNER_TABLE_HEIGHT -= 1

        ## Create the table

        inner_table = self.unoObjs.document.createInstance(
                      "com.sun.star.text.TextTable")
        inner_table.initialize(self.INNER_TABLE_HEIGHT, 1)  # one column
        self.textOuter.insertTextContent(    
            self.cursorOuter, inner_table, False)

        # Insert a '+' to keep the table locations from getting messed up.
        # We will delete it later, after all the tables are finished.
        self.textOuter.insertString(self.cursorOuter, '+', 0)
        self.cursorOuter.goLeft(1, False)
        self.innerTableMarkers.append(
            self.cursorOuter.getStart())    # save the location for later
        self.cursorOuter.goRight(1, False)

        self.set_noTableBorders(inner_table)
        inner_table.Split        = False # Text Flow -> don't split acr pages
        inner_table.KeepTogether = True  # Text Flow -> keep with next para
        INCH_TO_CM = 2540  # convert 1/1000 cm to inches
        inner_table.BottomMargin = self.tableBottomMargin * INCH_TO_CM
        self.logger.debug("Created inner table %s with %d rows." % 
                            (inner_table.getName(), self.INNER_TABLE_HEIGHT))
        self.inner_table         = inner_table
        self.wordRow_cols        = 1     # counts merged word columns
        self.morphRow_cols       = 1     # count of all inserted columns
        self.lastColFilled       = False # table starts with an empty column
        self.innerTableNumbering = False

        ## Insert numbering if not already done outside of this table

        if (self.InsertNumbering and not self.MakeOuterTable
            and self.firstInnerTable
           ):
            # Add an empty column. This is needed in order to resize the
            # numbering column correctly.
            self.logger.debug("Inserting column after numbering.")
            oCols = self.inner_table.getColumns()
            self.inner_table.RelativeWidth = 40    # 40% of page width
            oCols.insertByIndex(self.wordRow_cols, 1)
            self.wordRow_cols  += 1
            self.morphRow_cols += 1

            self.innerTableNumbering = True
            cellInner = self.inner_table.getCellByPosition(0, 0)
            self.insertNumber(
                cellInner, cellInner.createTextCursor(), self.inner_table)

    def cleanupInnerTableMarkers(self):
        """
        Delete the extra '+'s that we inserted to keep the inner tables
        from getting messed up.
        If we don't insert '+' marks, the inner tables can become out of order
        in certain situations, especially when the numbering column width is
        set extremely high (50%), causing a lot of wrapping.
        """
        self.logger.debug("cleaning up innerTable markers")
        for loopIndex, markerRange in enumerate(self.innerTableMarkers):
            self.unoObjs.viewcursor.gotoRange(markerRange, False)
            # delete '+'
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:Delete", "", 0, ())
            if loopIndex < len(self.innerTableMarkers) - 1:
                # Delete newline that was created by inserting '+' after table.
                # We don't need to do this for the last '+' because we will
                # add the free translation and ref number on that line.
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:Delete", "", 0, ())

    def insertNumber(self, text, cursor, table):
        """Insert the example autonumber field.
        Actually just insert xxxx for a placeholder.
        Later the number will be added when the dialog is closed.
        Requires self.innerTableNumbering.
        """
        self.logger.debug("insertNumber BEGIN")
        if self.InsertNumbering or self.MakeOuterTable:
            # Set example number margin so it lines up with the table.
            self.styles.requireParaStyle('numP')
            cursor.setPropertyValue(
                "ParaStyleName", self.styleNames['numP'])

            text.insertString(cursor, "(", 0)  # Add parenthesis around number.
            # Since inserting fields does not work from within a dialog,
            # we save the range until after the dialog is closed.
            if self.InsertNumbering and not self.updatingEx:
                self.logger.debug("Adding range.")
                self.exnumRanges.append(cursor.getEnd())
            if self.innerTableNumbering:
                # Even though we can't insert the number yet, we need to keep
                # the proper width for when the table is optimized.
                cursor.goRight(0, False)  # deselect
                text.insertString(cursor, "xxxx", 0)
            cursor.goRight(0, False)  # deselect
            text.insertString(cursor, ")", 0)
            if self.MethodFrames and not self.MakeOuterTable:
                text.insertString(cursor, "  ", 0)

        if table is not None:
            separators = table.getPropertyValue("TableColumnSeparators")
            if separators is not None and len(separators) > 0:
                self.logger.debug("Resizing column to " +
                                  str(self.numberingColumnWidth))
                PERCENT_TO_SEP = 100  # Separator width 10,000 is 100%.
                separators[0].Position = \
                    self.numberingColumnWidth * PERCENT_TO_SEP
                table.TableColumnSeparators = separators
            else:
                self.logger.debug("No separators to resize.")

    def addWordData(self, word):
        """Add columns for one word, many morphemes.
        Creates a new inner table if needed.
        """
        ## Create inner table if this is the first word

        if self.inner_table is None:
            self.createInnerTable()

        ## Create a new column for this word

        if self.lastColFilled:
            self.logger.debug("Inserting a column at index " +
                              str(self.wordRow_cols))
            self.inner_table.RelativeWidth = 100        # 100% of page width
            oCols = self.inner_table.getColumns()
            oCols.insertByIndex(self.wordRow_cols, 1)   # add column
            self.wordRow_cols  += 1
            self.morphRow_cols += 1
        wordRow_col       = self.wordRow_cols  - 1
        morphRow_startCol = self.morphRow_cols - 1

        ## Split up the column for all morphemes of this word

        num_morphs = len(word.morphList) # will be 1 if not SeparateMorphColumns
        if num_morphs > 1:
            newCols = num_morphs - 1  # how many columns to add by splitting
            word_rows = 0
            if self.ShowOrthoTextLine:
                word_rows += 1
            if self.ShowText:
                word_rows += 1
            self.logger.debug("Splitting for %d new morph cols at %d, %d" %
                                (newCols, morphRow_startCol, word_rows))
            c1 = self.inner_table.getCellByPosition(
                             morphRow_startCol, word_rows)
            c2 = self.inner_table.getCellByPosition(
                             morphRow_startCol, self.INNER_TABLE_HEIGHT - 1)
            oTextTableCurs = self.inner_table.createCursorByCellName(
                             c1.CellName)
            oTextTableCurs.gotoCellByName(c2.CellName, True)
            bHorizontal = False
            oTextTableCurs.splitRange(newCols, bHorizontal)
            self.morphRow_cols += newCols
            if word_rows == 0:
                self.wordRow_cols += newCols

        ## Insert data in each morph column

        morphRow_col = morphRow_startCol
        isFirstMorph = True
        for morph in word.morphList:
            wordOneMorph       = LingGramWord()
            wordOneMorph.orth  = word.orth
            wordOneMorph.text  = word.text
            wordOneMorph.morph = morph
            self.insertColumnData(wordOneMorph, isFirstMorph, morphRow_col)
            morphRow_col += 1
            isFirstMorph       = False
            self.lastColFilled = True
        self.optimizeInnerTable()

        ## Check if the word fits on the current line, or whether
        ## we need to move the word to a new table instead.

        firstDataCol = 0
        if self.innerTableNumbering:
            firstDataCol = 1
        if wordRow_col > firstDataCol:
            if self.hasWrappingText(self.inner_table):
                ## Delete the column for the word we just added
                ## - Deleting 1 word column may delete several morph columns.
                self.logger.debug("Deleting word col(s) at " + str(wordRow_col))
                oWordRowCols = self.inner_table.getColumns()
                if (self.ShowText or self.ShowOrthoTextLine) and \
                    self.SeparateMorphColumns:
                    oWordRowCols.removeByIndex(wordRow_col, 1)
                    self.wordRow_cols -= 1
                else:
                    oWordRowCols.removeByIndex(wordRow_col, num_morphs)
                    self.wordRow_cols -= num_morphs
                self.morphRow_cols -= num_morphs

                ## Resize the current table to fix it
                self.optimizeInnerTable()

                ## Make a new table and call this function recursively to
                ## put this word in the new table.
                self.createInnerTable()
                self.addWordData(word)

    def insertColumnData(self, word, isFirstMorph, morphRow_col):
        """Add interlinear data for a single column.
        Expects word.morph to be set.
        Requires self.inner_table, self.wordRow_cols
        """
        if word.morph is None:
            self.logger.error("Expected a single morph to be set.")
            return
        self.logger.debug("Adding data '%s' to word col %d, morph col %d" %
                            (safeStr(word.morph.gloss),
                            self.wordRow_cols - 1, morphRow_col))
        row = -1

        ## Orthographic Word

        if self.ShowOrthoTextLine:
            row += 1
            if isFirstMorph:
                cellInner = self.inner_table.getCellByPosition(
                    self.wordRow_cols - 1, row)
                cellcursorInner = cellInner.createTextCursor()
                self.styles.requireParaStyle('orth')
                cellcursorInner.setPropertyValue(
                    "ParaStyleName", self.styleNames['orth'])
                cellInner.insertString(cellcursorInner, word.orth, 0)

        ## Word

        if self.ShowText:
            row += 1
            if isFirstMorph:
                cellInner = self.inner_table.getCellByPosition(
                    self.wordRow_cols - 1, row)
                cellcursorInner = cellInner.createTextCursor()
                self.styles.requireParaStyle('text')
                cellcursorInner.setPropertyValue(
                    "ParaStyleName", self.styleNames['text'])
                cellInner.insertString(cellcursorInner, word.text, 0)

        ## Orthographic Morpheme

        if self.ShowOrthoMorphLine:
            row += 1
            cellInner = self.inner_table.getCellByPosition(
                        morphRow_col, row)
            cellcursorInner = cellInner.createTextCursor()
            self.styles.requireParaStyle('orthm')
            cellcursorInner.setPropertyValue(
                "ParaStyleName", self.styleNames['orthm'])
            cellInner.insertString(cellcursorInner, word.morph.orth, 0)

        ## Morpheme

        if self.ShowMorphemeBreaks:
            row += 1
            cellInner = self.inner_table.getCellByPosition(
                        morphRow_col, row)
            cellcursorInner = cellInner.createTextCursor()
            self.styles.requireParaStyle('morph')
            cellcursorInner.setPropertyValue(
                "ParaStyleName", self.styleNames['morph'])
            cellInner.insertString(cellcursorInner, word.morph.text, 0)

        ## Gloss

        if self.POS_AboveGloss:
            row += 2
        else:
            row += 1
        cellInner = self.inner_table.getCellByPosition(morphRow_col, row)
        cellcursorInner = cellInner.createTextCursor()
        self.styles.requireParaStyle('gloss')
        cellcursorInner.setPropertyValue(
            "ParaStyleName", self.styleNames['gloss'])
        cellInner.insertString(cellcursorInner, word.morph.gloss, 0)

        ## Part of Speech

        if self.ShowPartOfSpeech:
            if self.POS_AboveGloss:
                row -= 1
            else:
                row += 1
            cellInner = self.inner_table.getCellByPosition(morphRow_col, row)
            cellcursorInner = cellInner.createTextCursor()
            self.styles.requireParaStyle('pos')
            cellcursorInner.setPropertyValue(
                "ParaStyleName", self.styleNames['pos'])
            cellInner.insertString(cellcursorInner, word.morph.pos, 0)

        self.logger.debug("insertColumnData END")

    def optimizeInnerTable(self):
        """Shrink the table to fit the text."""
        self.logger.debug("Resizing table BEGIN")
        #oldSel = self.unoObjs.controller.getSelection()
        addedExtraCol = False
        # The outer table row needs to be adjustable or else optimizing
        # a tall inner table can mess it up. This seems to be a bug in OOo.
        self.resizeOuterTable()
        if self.morphRow_cols == 1:
            # Insert an extra column, because optimization doesn't work
            # for single-column tables.
            self.logger.debug("Inserting extra column")
            self.unoObjs.controller.select(self.inner_table)
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:InsertColumns", "", 0, ())
            addedExtraCol = True
        endCol = self.morphRow_cols - 1
        if addedExtraCol:
            endCol += 1
        self.logger.debug("Optimizing %d, %d to %d, %d" % (0,0, endCol,
                  self.INNER_TABLE_HEIGHT - 1))
        cellsRange = self.inner_table.getCellRangeByPosition (
            0, 0, endCol, self.INNER_TABLE_HEIGHT - 1)
        self.unoObjs.controller.select(cellsRange)
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SetOptimalColumnWidth", "", 0, ())
        if addedExtraCol:
            cellsRange = self.inner_table.getCellRangeByPosition (1,0,1,0)
            self.unoObjs.controller.select(cellsRange)
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:DeleteColumns", "", 0, ())
        #self.unoObjs.controller.select(oldSel)
        self.unoObjs.controller.select(None)
        self.fixedSizeOuterTable()
        self.logger.debug("Resizing table END")

    def hasWrappingText(self, table):
        """Returns true if text in a cell wraps to another line.
        To do this, we move the viewcursor down one line.
        If it is still in the same cell, then the cell has wrapping text,
        which means that there is too much text in this table.
        """
        self.logger.debug("hasWrappingText BEGIN")
        viewcursor = self.unoObjs.viewcursor    # shorthand variable name
        for cellName in table.getCellNames():
            cell       = table.getCellByName(cellName)
            oldRange   = viewcursor.getStart()
            cellcursor = cell.createTextCursor()
            self.styles.requireParaStyle('numP')
            if cellcursor.getPropertyValue("ParaStyleName") == \
                self.styleNames['numP']:
                # Don't check whether the numbering wraps,
                # because moving the numbering to a new table won't help.
                continue
            viewcursor.gotoRange(cellcursor.getStart(), False)
            success    = viewcursor.goDown(1, False)
            cell2      = viewcursor.Cell
            table2     = viewcursor.TextTable
            viewcursor.gotoRange(oldRange, False)
            if not success:
                ## Failure to go down means there is no wrapping text.
                continue
            if cell2 is not None:
                if (cell2.CellName == cellName and
                    table2.getName() == table.getName()
                   ):
                    self.logger.debug("cell " + cellName + " in table " +
                                      table.getName() + " has wrapping text")
                    return True
        self.logger.debug("No wrapping text found.")
        return False


    def set_noTableBorders(self, table):
        """Sets a table to have no borders."""
        BORDER_WIDTH = 0
        v = table.getPropertyValue("TableBorder")
        x = v.TopLine
        x.OuterLineWidth = BORDER_WIDTH
        v.TopLine = x
        x = v.LeftLine
        x.OuterLineWidth = BORDER_WIDTH
        v.LeftLine       = x
        x = v.RightLine
        x.OuterLineWidth = BORDER_WIDTH
        v.RightLine      = x
        x = v.TopLine
        x.OuterLineWidth = BORDER_WIDTH
        v.TopLine        = x
        x = v.VerticalLine
        x.OuterLineWidth = BORDER_WIDTH
        v.VerticalLine   = x
        x = v.HorizontalLine
        x.OuterLineWidth = BORDER_WIDTH
        v.HorizontalLine = x
        x = v.BottomLine
        x.OuterLineWidth = BORDER_WIDTH
        v.BottomLine     = x
        table.setPropertyValue("TableBorder", v)

    def set_noTableSpacing(self, table):
        """Sets a table to have no spacing. As a side effect, this function
        also currently sets borders to none.
        """
        self.logger.debug("set_noTableSpacing BEGIN")
        # move view cursor to first cell in table
        self.unoObjs.controller.select(table)

        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
        uno_args = (
            createProp("BorderOuter.LeftBorder",    (0,0,0,0)),
            createProp("BorderOuter.LeftDistance",  0),
            createProp("BorderOuter.RightBorder",   (0,0,0,0)),
            createProp("BorderOuter.RightDistance", 0),
            createProp("BorderOuter.TopBorder",     (0,0,0,0)),
            createProp("BorderOuter.TopDistance",   0),
            createProp("BorderOuter.BottomBorder",  (0,0,0,0)),
            createProp("BorderOuter.BottomDistance", 0)
        )
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:BorderOuter", "", 0, uno_args)
        # move view cursor to first cell in table
        self.unoObjs.controller.select(table)

#-------------------------------------------------------------------------------
# End of Tables.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Frames.py
#-------------------------------------------------------------------------------



PARAGRAPH_BREAK = uno.getConstantByName(
    "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK")

class Frames:
    def __init__(self, config, unoObjs, styles, locale):
        self.unoObjs    = unoObjs
        self.styles     = styles
        self.locale     = locale
        self.logger     = logging.getLogger("lingt.Access.Frames")
        self.msgbox     = MessageBox(unoObjs)
        self.frameOuter = None

        self.styleNames           = config.styleNames
        self.ShowOrthoTextLine    = config.ShowOrthoTextLine
        self.ShowText             = config.ShowText
        self.SeparateMorphColumns = config.SeparateMorphColumns
        self.ShowOrthoMorphLine   = config.ShowOrthoMorphLine
        self.ShowMorphemeBreaks   = config.ShowMorphemeBreaks
        self.ShowPartOfSpeech     = config.ShowPartOfSpeech
        self.POS_AboveGloss       = config.POS_AboveGloss

    def createOuterFrame(self, textOuter, cursorOuter):
        """Create a new outer frame for the word."""
        self.logger.debug("Creating outer frame.")
        frameOuter = self.unoObjs.document.createInstance(
                     "com.sun.star.text.TextFrame")
        self.styles.requireFrameStyle('intF')
        frameOuter.setPropertyValue(
            "FrameStyleName", self.styleNames['intF'])
        
        ## Starting with variable size is exceedingly slow for CTL fonts.
        ## After the first character is inserted,
        ## we can change it back to variable size and it will work fine after
        ## that.
        #
        ## The width type doesn't seem to get taken from the style.
        
        frameOuter.WidthType = uno.getConstantByName(
                               "com.sun.star.text.SizeType.FIX")
        frameOuter.Width = 0.5 * 2540   # 0.5 inches
        textOuter.insertTextContent(cursorOuter, frameOuter, False)
        self.logger.debug("Created outer frame " + frameOuter.getName())

        # Get cursor in main column
        self.frameOuter       = frameOuter
        self.framecursorOuter = frameOuter.createTextCursor()

    def insertInnerFrameData(self, word, firstMorph):
        """Insert data into the outer frame.
        Optionally creates an inner frame for morpheme breaks.
        Expects word.morph to be set.
        Requires self.frameOuter, self.framecursorOuter
        """
        if word.morph is None:
            self.logger.error("Expected a single morph to be set.")
            return
        self.logger.debug(
            "Adding frame '" + safeStr(word.morph.gloss) + "'")

        ## Orthographic Word

        if firstMorph and self.ShowOrthoTextLine:
            self.styles.requireParaStyle('orth')
            self.framecursorOuter.setPropertyValue(
                "ParaStyleName", self.styleNames['orth'])
            self.frameOuter.insertString(
                self.framecursorOuter, word.orth, 0)
            self.frameOuter.insertControlCharacter(
                self.framecursorOuter, PARAGRAPH_BREAK, 0)
            self.framecursorOuter.setPropertyValue(
                "ParaStyleName", "Standard")
            self.frameOuter.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")

        ## Word

        if firstMorph and self.ShowText:
            self.styles.requireParaStyle('text')
            self.framecursorOuter.setPropertyValue(
                "ParaStyleName", self.styleNames['text'])
            self.frameOuter.insertString(
                self.framecursorOuter, word.text, 0)
            self.frameOuter.insertControlCharacter(
                self.framecursorOuter, PARAGRAPH_BREAK, 0)
            self.framecursorOuter.setPropertyValue(
                "ParaStyleName", "Standard")
            self.frameOuter.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")

        frameForGloss = None    # either outer or inner frame
        if self.SeparateMorphColumns:
            ## Create an inner frame for morpheme breaks.

            frameInner = self.unoObjs.document.createInstance(
                "com.sun.star.text.TextFrame")
            self.styles.requireFrameStyle('morF')
            frameInner.setPropertyValue(
                "FrameStyleName", self.styleNames['morF'])
            frameInner.WidthType = uno.getConstantByName(
                                   "com.sun.star.text.SizeType.FIX")
            frameInner.Width = 0.5 * 2540   # 0.5 inches
            self.frameOuter.insertTextContent(
                self.framecursorOuter, frameInner, False)
            self.logger.debug(
                "Created text frame " + frameInner.getName())

            frameForGloss = frameInner
            framecursor   = frameInner.createTextCursor()
        else:
            frameForGloss = self.frameOuter
            framecursor   = self.framecursorOuter

        ## Orthographic Morpheme

        if self.ShowOrthoMorphLine:
            self.logger.debug("_")
            self.styles.requireParaStyle('orthm')
            framecursor.setPropertyValue(
                "ParaStyleName", self.styleNames['orthm'])
            frameForGloss.insertString(framecursor, word.morph.orth, 0)
            frameForGloss.insertControlCharacter(
                framecursor, PARAGRAPH_BREAK, 0)
            frameForGloss.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")
            # in case it hasn't been done yet.
            self.frameOuter.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")

        ## Morpheme

        if self.ShowMorphemeBreaks:
            self.styles.requireParaStyle('morph')
            framecursor.setPropertyValue(
                "ParaStyleName", self.styleNames['morph'])
            frameForGloss.insertString(framecursor, word.morph.text, 0)
            frameForGloss.insertControlCharacter(
                framecursor, PARAGRAPH_BREAK, 0)
            frameForGloss.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")
            # in case it hasn't been done yet.
            self.frameOuter.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")

        ## Part of Speech - first option

        if self.ShowPartOfSpeech and self.POS_AboveGloss:
            self.styles.requireParaStyle('pos')
            framecursor.setPropertyValue(
                "ParaStyleName", self.styleNames['pos'])
            frameForGloss.insertString(framecursor, word.morph.pos, 0)
            frameForGloss.insertControlCharacter(
                framecursor, PARAGRAPH_BREAK, 0)
            # in case it hasn't been done yet.
            frameForGloss.WidthType = uno.getConstantByName(
                "com.sun.star.text.SizeType.VARIABLE")

        ## Gloss

        self.styles.requireParaStyle('gloss')
        framecursor.setPropertyValue(
            "ParaStyleName", self.styleNames['gloss'])
        frameForGloss.insertString(framecursor, word.morph.gloss, 0)
        # in case it hasn't been done yet.
        frameForGloss.WidthType = uno.getConstantByName(
            "com.sun.star.text.SizeType.VARIABLE")

        ## Part of Speech - second option

        if self.ShowPartOfSpeech and not self.POS_AboveGloss:
            frameForGloss.insertControlCharacter(
                framecursor, PARAGRAPH_BREAK, 0)
            self.styles.requireParaStyle('pos')
            framecursor.setPropertyValue(
                "ParaStyleName", self.styleNames['pos'])
            frameForGloss.insertString(framecursor, word.morph.pos, 0)
        self.logger.debug("insertInnerFrameData END")

    def insertInnerTempSpace(self, textOuter=None, cursorOuter=None):
        """
        In LibreOffice 4.0 frames get resized improperly if there
        is only one inner frame. A simple fix is to add and remove a space.
        """
        text   = self.frameOuter
        cursor = self.framecursorOuter
        if textOuter:
            text   = textOuter
            cursor = cursorOuter
        text.insertString(cursor, " ", 0)
        cursor.collapseToEnd()
        cursor.goLeft(0, False)
        cursor.goLeft(1, True)
        cursor.setString("")

    def set_noFrameBorders(self, textFrame):
        """Sets a TextFrame to have no borders."""
        BORDER_WIDTH = 0
        borderLine = textFrame.getPropertyValue("LeftBorder")
        borderLine.OuterLineWidth = BORDER_WIDTH
        textFrame.setPropertyValue("LeftBorder",   borderLine)
        textFrame.setPropertyValue("RightBorder",  borderLine)
        textFrame.setPropertyValue("TopBorder",    borderLine)
        textFrame.setPropertyValue("BottomBorder", borderLine)

#-------------------------------------------------------------------------------
# End of Frames.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of OutputManager.py
#-------------------------------------------------------------------------------



PARAGRAPH_BREAK = uno.getConstantByName(
    "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK")

class ExampleManager:
    """
    Abstract base class to manage output of linguistic examples to the Writer
    document.
    """
    def __init__(self, unoObjs, styles):
        if self.__class__ is ExampleManager:   # if base class is instantiated
            raise NotImplementedError
        self.unoObjs       = unoObjs
        self.styles        = styles
        self.logger        = logging.getLogger("lingt.Access.OutputManager")
        self.msgbox        = MessageBox(unoObjs)
        self.locale        = Locale(unoObjs)
        self.exnumRanges   = []
        self.logger.debug("ExampleManager init() finished")

    def setConfig(self, config):
        """Set options."""
        raise NotImplementedError

    def outputExample(self, example, deleteRefNum, updatingEx):
        """Output the example to the Writer document."""
        self.logger.debug("outputExamples BEGIN")
        oVC = self.unoObjs.viewcursor   # shorthand variable name

        ## Delete the selected reference number

        extraNewline = False # newline from ref number
        if deleteRefNum:
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:SwBackspace", "", 0, ())
            if oVC.isAtEndOfLine():
                extraNewline = True

        ## Start with default formatting at the beginning

        if oVC.TextTable or oVC.TextFrame:
            raise ScopeError("Cannot be inside a table or frame.")
        elif oVC.getText().getImplementationName() == "SwXHeadFootText":
            raise ScopeError("Cannot be in a header or footer.")
        try:
            self.textcursor = self.unoObjs.text.createTextCursorByRange(
                              oVC.getStart())
        except:
            raise ScopeError("Cannot insert text here.")
        self.logger.debug("Created a text cursor.")
        propNames = ['ParaStyleName', 'CharStyleName',
                    'CharFontName', 'CharFontNameComplex', 'CharFontNameAsian',
                    'CharHeight',   'CharHeightComplex',   'CharHeightAsian']
        nextProps = dict()
        if self.textcursor.goRight(1, False):
            # Look ahead for next style and font
            for propName in propNames:
                nextProps[propName] = self.textcursor.getPropertyValue(propName)
            self.textcursor.goLeft(1, False)
        self.textcursor.setAllPropertiesToDefault() # works for fonts
        self.textcursor.setPropertyValue('ParaStyleName', 'Standard')
        self.textcursor.setPropertyToDefault('CharStyleName')

        ## Insert examples

        self.logger.debug("Writing example.")
        self.insertEx(example, updatingEx)
        self.unoObjs.text.insertControlCharacter(
            self.textcursor, PARAGRAPH_BREAK, 0)
        for propName in propNames:
            propVal = ""
            if propName in nextProps:
                propVal = nextProps[propName]
            if propVal:
                ## Set property to look-ahead value
                self.logger.debug("PropName '%s' = '%s'" % (propName, propVal))
                self.textcursor.setPropertyValue(propName, propVal)
            else:
                ## Set property to default value
                if propName == 'ParaStyleName':
                    # Setting ParaStyleName to its default does not work.
                    # So we use the underlying default style name "Standard".
                    self.textcursor.setPropertyValue(propName, 'Standard')
                else:
                    self.textcursor.setPropertyToDefault(propName)
        if extraNewline:
            # Delete the extra newline from the #ref number.
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:Delete", "", 0, ())
        if updatingEx:
            # Go back to end of line before paragraph break,
            # in order to be ready to find the next ref number.
            oVC.goLeft(1, False)
        self.logger.debug("outputExamples FINISH")

    def insertEx(self, ex, updatingEx):
        raise NotImplementedError

class PhonMgr(ExampleManager):
    """Manages output of phonology examples."""

    def setConfig(self, config):
        self.styleNames       = config.styleNames
        self.showBrackets     = config.showBrackets
        self.PhonemicLeftmost = config.PhonemicLeftmost

    def insertEx(self, ex, unused_updatingEx):
        """ex is of type LingPhonExample"""
        self.styles.requireParaStyle('exPara')
        self.textcursor.setPropertyValue(
            "ParaStyleName", self.styleNames['exPara'])
        ex = copy.copy(ex)  # so we don't modify the original data
        if self.showBrackets:
            ex.phonemic = "/%s/" % (ex.phonemic)
            ex.phonetic = "[%s]" % (ex.phonetic)
            ex.gloss    = "'%s'" % (ex.gloss)

        if self.PhonemicLeftmost:
            self.styles.requireCharStyle('phonemic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonemic'])
            self.unoObjs.text.insertString(
                self.textcursor, "\t" + ex.phonemic + "\t", 0)
            self.styles.requireCharStyle('phonetic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonetic'])
            self.unoObjs.text.insertString(
                self.textcursor, ex.phonetic + "\t", 0)
        else:
            self.styles.requireCharStyle('phonetic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonetic'])
            self.unoObjs.text.insertString(
                self.textcursor, "\t" + ex.phonetic + "\t", 0)
            self.styles.requireCharStyle('phonemic')
            self.textcursor.setPropertyValue(
                "CharStyleName", self.styleNames['phonemic'])
            self.unoObjs.text.insertString(
                self.textcursor, ex.phonemic + "\t", 0)

        self.styles.requireCharStyle('gloss')
        self.textcursor.setPropertyValue(
            "CharStyleName", self.styleNames['gloss'])
        self.unoObjs.text.insertString(
            self.textcursor, ex.gloss + "\t", 0)
        self.styles.requireCharStyle('ref')
        self.textcursor.setPropertyValue(
            "CharStyleName", self.styleNames['ref'])
        self.unoObjs.text.insertString(
            self.textcursor, ex.refText, 0)

class InterlinMgr(ExampleManager):
    """Manages output of interlinear examples."""

    def setConfig(self, config):
        self.styleNames         = config.styleNames
        self.MethodTables       = config.MethodTables
        self.MethodFrames       = config.MethodFrames
        self.MakeOuterTable     = config.MakeOuterTable
        self.FreeTransInQuotes  = config.FreeTransInQuotes
        self.InsertNumbering    = config.InsertNumbering
        self.tables = Tables(self.exnumRanges, config, self.unoObjs,
                             self.styles)
        self.frames = Frames(config, self.unoObjs, self.styles, self.locale)

    def insertEx(self, ex, updatingEx):
        """ex is of type LingGramExample"""
        oVC = self.unoObjs.viewcursor   # shorthand variable name

        ## Insert outer table

        textOuter, cursorOuter = self.tables.outerTableAndNumbering(
                                 self.textcursor, updatingEx)
        ## Add word data

        self.logger.debug("Adding " + str(len(ex.wordList)) + " words")
        if self.MethodTables:
            for word in ex.wordList:
                self.tables.addWordData(word)
            self.tables.cleanupInnerTableMarkers()
            self.tables.resizeOuterTable()
        elif self.MethodFrames:
            INSERT_AFTER = 30   # insert a newline after so many frames
            frame_count  = 0
            insertedNewlineRanges = []
            for word in ex.wordList:
                self.frames.createOuterFrame(textOuter, cursorOuter)
                frame_count += 1
                self.logger.debug(
                    "Adding " + str(len(word.morphList)) + " morphemes")
                isFirstMorph = True
                for morph in word.morphList:
                    wordOneMorph       = LingGramWord()
                    wordOneMorph.orth  = word.orth
                    wordOneMorph.text  = word.text
                    wordOneMorph.morph = morph
                    self.frames.insertInnerFrameData(
                        wordOneMorph, isFirstMorph)
                    frame_count += 1
                    isFirstMorph = False
                if len(word.morphList) == 1:
                    self.frames.insertInnerTempSpace()
                if frame_count >= INSERT_AFTER:
                    ## Insert a newline because if there are a lot of
                    ## frames without newlines, then inserting frames 
                    ## becomes very slow.
                    self.logger.debug("Temporarily adding a newline.")
                    textOuter.insertControlCharacter(
                        cursorOuter, PARAGRAPH_BREAK, 0)
                    insertedNewlineRanges.append(cursorOuter.getEnd())
                    frame_count = 0
            if len(ex.wordList) == 1:
                self.frames.insertInnerTempSpace(textOuter, cursorOuter)

            ## Now remove the extra newlines we inserted

            self.logger.debug("Now removing any extra newlines.")
            self.tables.resizeOuterTable()
            originalRange = oVC.getStart()
            for txtRange in insertedNewlineRanges:
                oVC.gotoRange(txtRange, False)
                # Note: IsAutoHeight of the outer table should be True
                # before calling uno:SwBackspace.
                self.unoObjs.dispatcher.executeDispatch(
                    self.unoObjs.frame, ".uno:SwBackspace", "", 0, ())
            oVC.gotoRange(originalRange, False)

        ## Add free translation and reference

        self.logger.debug("Adding free translation")
        if self.MethodFrames:
            textOuter.insertControlCharacter(cursorOuter, PARAGRAPH_BREAK, 0)
        self.styles.requireParaStyle('ft')
        cursorOuter.setPropertyValue(
            "ParaStyleName", self.styleNames['ft'])
        ex = copy.copy(ex)  # so we don't modify the original data
        if self.FreeTransInQuotes:
            ex.freeTrans = "'%s'" % (ex.freeTrans)  # add single quotes
        textOuter.insertString(cursorOuter, ex.freeTrans, 0)
        spacer = " " * 4    # four spaces, probably in fixed-width font
        textOuter.insertString(cursorOuter, spacer + ex.refText, 1) # select
        self.styles.requireCharStyle('ref')
        cursorOuter.setPropertyValue(
            "CharStyleName", self.styleNames['ref'])
        cursorOuter.collapseToEnd()
        cursorOuter.goRight(0, False) # deselect

        ## Add extra space at the end with default formatting

        if self.MakeOuterTable:
            # viewcursor should be in numbering column after (),
            # because it goes in the first column when a table gets created.
            #
            # Go to beginning of next line.
            self.logger.debug("going after outer table")
            oVC.goDown(1, False)
            oVC.gotoStartOfLine(False)
        else:
            # viewcursor should be at end of ref number,
            # because it keeps being moved each time we insert something.
            self.logger.debug("adding para break")
            textOuter.insertControlCharacter(cursorOuter, PARAGRAPH_BREAK, 0)
            cursorOuter.setPropertyValue('ParaStyleName', 'Standard')
            cursorOuter.setPropertyToDefault('CharStyleName')
            oVC.gotoRange(cursorOuter.getEnd(), False)
        self.textcursor = self.unoObjs.text.createTextCursorByRange(
                          oVC.getStart())

    def addExampleNumbers(self):
        """Inserts example numbers at the specified locations.
        self.exnumRanges is of type com.sun.star.text.XTextRange.

        This function is needed because the .uno:InsertField call seems
        to fail when called within a dialog event handler.
        API calls succeed, but there does not seem to be a way to create
        a "Number Range" master field or text field with the API,
        only SetExpression items which are not as flexible.
        """
        self.logger.debug("addExampleNumbers BEGIN")

        originalRange = self.unoObjs.viewcursor.getStart()
        for exnumRange in self.exnumRanges: 
            self.logger.debug("Going to a range.")
            try:
                self.unoObjs.viewcursor.gotoRange(exnumRange, False)
            except (IllegalArgumentException, RuntimeException):
                # Give up on this range and go on to the next one.
                self.logger.warn("Failed to locate range.")
                continue
            if self.MethodTables and self.InsertNumbering \
                and not self.MakeOuterTable:
                ## Delete "xxxx" that we inserted earlier.
                self.unoObjs.viewcursor.goRight(4, True)
                self.unoObjs.viewcursor.String = ""
            uno_args = (
                createProp("Type",      23),
                createProp("SubType",   127),
                createProp("Name",      "AutoNr"),
                createProp("Content",   ""),
                createProp("Format",    4),
                createProp("Separator", " ")
            )
            self.unoObjs.dispatcher.executeDispatch(
                self.unoObjs.frame, ".uno:InsertField", "", 0, uno_args) 
            self.logger.debug("Inserted AutoNr field")
        self.unoObjs.viewcursor.gotoRange(originalRange, False)
        self.logger.debug("addExampleNumbers END")

class AbbrevManager:
    """Sends output to the Writer doc."""

    def __init__(self, unoObjs, styles):
        self.unoObjs    = unoObjs
        self.logger     = logging.getLogger("lingt.Access.OutputManager")
        self.msgbox     = MessageBox(unoObjs)
        self.styleNames = styles.getStyleNames()
        self.styles     = styles
        self.locale     = Locale(unoObjs)
        self.logger.debug("AbbrevManager init() finished")

    def outputList(self, abbrevList):
        self.logger.debug("outputList BEGIN")

        ## Start with default formatting at the beginning

        oVC = self.unoObjs.viewcursor
        if oVC.TextTable or oVC.TextFrame:
            self.msgbox.display("The cursor cannot be inside a table or frame.")
            return
        elif oVC.getText().getImplementationName() == "SwXHeadFootText":
            self.msgbox.display("The cursor cannot be in a header or footer.")
            return
        textcursor = self.unoObjs.text.createTextCursorByRange(
                     self.unoObjs.viewcursor.getStart())
        self.logger.debug("Created a text cursor.")
        textcursor.setPropertyValue('ParaStyleName', 'Standard')
        textcursor.setPropertyToDefault('CharStyleName')

        didOutput = False
        for abbr in abbrevList.getList():
            if not abbr.shouldOutput():
                self.logger.debug("Skipping abbrev " + abbr.abbrev)
                continue
            self.logger.debug("Outputting abbrev " + abbr.abbrev)
            didOutput = True
            self.styles.requireParaStyle('abbr')
            textcursor.setPropertyValue(
                "ParaStyleName", self.styleNames['abbr'])
            abbr_str = abbr.abbrev + "\t" + abbr.fullName
            self.unoObjs.text.insertString(textcursor, abbr_str, 0)
            self.unoObjs.text.insertControlCharacter(
                textcursor, PARAGRAPH_BREAK, 0)

        if didOutput:
            self.unoObjs.text.insertControlCharacter(
                textcursor, PARAGRAPH_BREAK, 0)
            textcursor.setPropertyValue("ParaStyleName", "Standard")
        else:
            self.unoObjs.text.insertString(
                textcursor, "No abbreviations found.", 0)
            self.unoObjs.text.insertControlCharacter(
                textcursor, PARAGRAPH_BREAK, 0)
        self.logger.debug("outputList END")

#-------------------------------------------------------------------------------
# End of OutputManager.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of ExUpdater_test.py
#-------------------------------------------------------------------------------




class ExUpdaterTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.logger  = logging.getLogger("lingt.TestExUpdater")
        self.unoObjs = None

    @classmethod
    def setUpClass(cls):
        unoObjs = UnoObjs(getContext(), loadDocObjs=False)
        blankWriterDoc(unoObjs)

    def setUp(self):
        self.setUpClass()
        self.unoObjs     = unoObjsForCurrentDoc()
        self.exnumRanges = []
        USERVAR_PREFIX   = "LTg_"    # for Grammar
        self.userVars    = UserVars(
                           USERVAR_PREFIX, self.unoObjs.document, self.logger)
        self.styles      = GrammarStyles(self.unoObjs, self.userVars)
        self.styles.createStyles()
        self.baseConfig                        = ConfigOptions()
        self.baseConfig.styleNames             = self.styles.getStyleNames()
        self.baseConfig.MethodTables           = False
        self.baseConfig.MethodFrames           = True
        self.baseConfig.MakeOuterTable         = True
        self.baseConfig.FreeTransInQuotes      = True
        self.baseConfig.InsertNumbering        = True

        self.baseConfig.ShowOrthoTextLine      = True
        self.baseConfig.ShowText               = True
        self.baseConfig.ShowOrthoMorphLine     = True
        self.baseConfig.ShowMorphemeBreaks     = True
        self.baseConfig.ShowPartOfSpeech       = True
        self.baseConfig.InsertNumbering        = True
        self.baseConfig.SeparateMorphColumns   = True
        self.baseConfig.POS_AboveGloss         = False
        self.baseConfig.startingOuterRowHeight = 2
        self.baseConfig.numberingColumnWidth   = 5
        self.baseConfig.tableBottomMargin      = 0.5

    def testUpdater(self):
        config    = copy.copy(self.baseConfig)
        exManager = InterlinMgr(self.unoObjs, self.styles)
        exManager.setConfig(config)
        ex = LingGramExample()
        ex.refText = "WORD01"
        ex.freeTrans = "ft1"
        ex.appendMorph("m1orth","m1text","m1Gloss","m1pos")
        ex.appendMorph("m2orth","m2text","m2Gloss","m2pos")
        ex.appendWord("word1_m1,2","word1Orth")
        ex.appendMorph("m3orth","m3text","m3Gloss","m3pos")
        ex.appendMorph("m4orth","m4text","m4Gloss","m4pos")
        ex.appendMorph("m5orth","m5text","m5Gloss","m5pos")
        ex.appendWord("word2_m3-5","word2Orth")
        exManager.outputExample(ex, False, False)
        exManager.addExampleNumbers()
        self.enumerateTextContent(self.unoObjs.text)
        self.assertEquals(self.tableCount, 1)
        self.assertEquals(self.frameCount, 7)

        # move cursor to end of ref number
        self.unoObjs.viewcursor.goUp(1, False)
        self.unoObjs.viewcursor.goLeft(1, False)

        updater = ExUpdater(self.unoObjs, exManager, "LTg_")
        updater.gotoAfterEx()
        ex.appendMorph("m6orth","m6text","m6Gloss","m6pos")
        ex.appendWord("word3_m6","word3Orth")
        exManager.outputExample(ex, False, True)

        updater.moveExNumber()
        updater.moveExamplesToNewDoc()
        self.enumerateTextContent(self.unoObjs.text)
        self.assertEquals(self.tableCount, 1)
        self.assertEquals(self.frameCount, 9)

        compDoc = updater.compDoc
        self.assertTrue(compDoc is not None)
        self.assertTrue(compDoc.document is not None)
        updater.compDoc.document.close(True)
        self.tearDownClass()

    def enumerateTextContent(self, oParEnumerator):
        """
        Hacked from Access/Search.py
        """
        self.frameCount = 0
        self.tableCount = 0
        oParEnumeration = oParEnumerator.createEnumeration()
        i = 0
        while oParEnumeration.hasMoreElements():
            oPar = oParEnumeration.nextElement()
            i += 1
            self.logger.debug("par " + str(i) + ": " + oPar.ImplementationName)
            self.enumeratePar(oPar)
        return self.frameCount

    def enumeratePar(self, oPar, recursive=False):
        """Recursively enumerate paragraphs, tables and frames.
        Tables may be nested.
        """
        if oPar.supportsService("com.sun.star.text.Paragraph"):
            oSectionEnum = oPar.createEnumeration()
            while oSectionEnum.hasMoreElements():
                oSection = oSectionEnum.nextElement()
                if oSection.TextPortionType == "Text":
                    self.logger.debug("simple text portion")
                elif oSection.TextPortionType == "Frame":
                    self.logger.debug("Frame text portion")
                    oFrameEnum = oSection.createContentEnumeration(
                        "com.sun.star.text.TextFrame")
                    while oFrameEnum.hasMoreElements():  # always only 1 item?
                        oFrame = oFrameEnum.nextElement()
                        self.enumeratePar(oFrame, recursive=True)
        elif oPar.supportsService("com.sun.star.text.TextTable"):
            oTable = oPar
            self.logger.debug("table " + oTable.getName())
            self.tableCount += 1
            self.unoObjs.controller.select(oTable)  # go to first cell
            sNames = oTable.getCellNames()
            for sName in sNames:
                self.logger.debug("cell " + oTable.getName() + ":" + sName)
                oCell = oTable.getCellByName(sName)
                oParEnum = oCell.createEnumeration()
                while oParEnum.hasMoreElements():
                    oPar2 = oParEnum.nextElement()
                    self.enumeratePar(oPar2, recursive=True)
        elif oPar.supportsService("com.sun.star.text.TextFrame"):
            oFrame = oPar
            self.logger.debug("frame " + oFrame.getName())
            self.frameCount += 1
            oParEnum = oFrame.createEnumeration()
            while oParEnum.hasMoreElements():
                oPar2 = oParEnum.nextElement()
                self.enumeratePar(oPar2, recursive=True)

    @classmethod
    def tearDownClass(cls):
        unoObjs = unoObjsForCurrentDoc()
        oVC = unoObjs.viewcursor
        unoObjs.dispatcher.executeDispatch(
            unoObjs.frame, ".uno:SelectTable", "", 0, ())
        unoObjs.dispatcher.executeDispatch(
            unoObjs.frame, ".uno:DeleteTable", "", 0, ())



#-------------------------------------------------------------------------------
# End of ExUpdater_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Search_test.py
#-------------------------------------------------------------------------------




class SearchTestCase(unittest.TestCase):

    INFILE = os.path.join(TESTDATA_FOLDER, "search nested items.odt")

    def setUp(self):
        unoObjs          = unoObjsForCurrentDoc()
        self.logger      = logging.getLogger("lingt.TestSearch")
        docReader        = DocReader(None, unoObjs, -1)
        docReader.loadDoc(self.INFILE)
        self.unoObjs     = docReader.doc
        self.progressBar = ProgressBar(self.unoObjs, "TestSearch")

    #def testTextSearch_selection(self):
    #    self.textSearch = TextSearch(self.unoObjs, self.progressBar)
    #    self.textSearch.scopeSelection()
    #    self.reportTextSearch()

    def testTextSearch_wholeDoc(self):
        self.textSearch = TextSearch(self.unoObjs, self.progressBar)
        self.textSearch.scopeWholeDoc()
        self.reportTextSearch(20)
        self.tearDownClass()

    def reportTextSearch(self, expected=-1):
        ranges = self.textSearch.getRanges()
        #print("found ", len(ranges), " ranges")
        if expected >= 0:
            self.assertEquals(len(ranges), expected)
        i = 1
        for txtRange in ranges:
            oSel = txtRange.sel
            oCursor = oSel.getText().createTextCursorByRange(oSel)
            if not oCursor:
                print("could not get range ", i)
                continue
            oCursor.CharBackColor = 15138560    # yellow
            oCursor.collapseToEnd()
            oCursor.getText().insertString(oCursor, "(" + str(i) + ")", False)
            i += 1

    @classmethod
    def tearDownClass(cls):
        unoObjs = UnoObjs(getContext(), loadDocObjs=False)
        blankWriterDoc(unoObjs)

#-------------------------------------------------------------------------------
# End of Search_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Tables_test.py
#-------------------------------------------------------------------------------




class TablesTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs     = unoObjsForCurrentDoc()
        self.logger      = logging.getLogger("lingt.TestTables")
        self.exnumRanges = []
        USERVAR_PREFIX   = "LTg_"    # for Grammar
        self.userVars    = UserVars(
                           USERVAR_PREFIX, self.unoObjs.document, self.logger)
        self.styles      = GrammarStyles(
                           self.unoObjs, self.userVars)
        self.config = ConfigOptions()
        self.config.MakeOuterTable  = True
        self.config.InsertNumbering = False
        self.config.MethodFrames    = True
        self.config.startingOuterRowHeight = 2
        self.config.numberingColumnWidth = 5
        self.config.ShowOrthoTextLine      = False 
        self.config.ShowText               = True
        self.config.ShowOrthoMorphLine     = False
        self.config.ShowMorphemeBreaks     = True
        self.config.ShowPartOfSpeech       = True
        self.config.InsertNumbering        = True
        self.config.SeparateMorphColumns   = True
        self.config.POS_AboveGloss         = False
        self.config.tableBottomMargin      = 0
        self.styles.createParaStyle("numP")
        self.config.styleNames = {}
        self.config.styleNames['numP'] = 'User Index 1'

    def test1_outerTable(self):
        writerTables = Tables(
                       self.exnumRanges, self.config, self.unoObjs, self.styles)
        oTextcursor = self.unoObjs.text.createTextCursorByRange(
                      self.unoObjs.viewcursor.getStart())
        tables = self.unoObjs.document.getTextTables()
        prevCount = tables.getCount()
        writerTables.outerTableAndNumbering(oTextcursor, False)
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, PARAGRAPH_BREAK, False)
        self.assertEqual(tables.getCount(), prevCount + 1)
        table  = tables.getByIndex(0)
        self.assertEqual(table.getName(), "Table1")
        self.unoObjs.viewcursor.goDown(1, False)

    def test2_hasWrappingText(self):
        writerTables = Tables(
                       self.exnumRanges, self.config, self.unoObjs, self.styles)
        oTable = self.unoObjs.document.createInstance(
                 "com.sun.star.text.TextTable")
        oTable.initialize(1, 1)
        self.unoObjs.text.insertTextContent(
            self.unoObjs.viewcursor, oTable, False)
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, PARAGRAPH_BREAK, False)
        oCell = oTable.getCellByPosition(0, 0)
        oCellCursor = oCell.createTextCursor()
        oCell.insertString(oCellCursor, "a" * 500, False)
        self.assert_(writerTables.hasWrappingText(oTable))

        oCell.setString("")
        oCell.insertString(oCellCursor, "a" * 5, False)
        self.assert_(not writerTables.hasWrappingText(oTable))

        oTable = self.unoObjs.document.createInstance(
                 "com.sun.star.text.TextTable")
        oTable.initialize(7, 7)
        self.unoObjs.text.insertTextContent(
            self.unoObjs.viewcursor, oTable, False)
        self.unoObjs.text.insertControlCharacter(
            self.unoObjs.viewcursor, PARAGRAPH_BREAK, False)
        oTextTableCurs = oTable.createCursorByCellName("B2")
        oTextTableCurs.gotoCellByName("B4", True)
        oTextTableCurs.mergeRange()
        oCell = oTable.getCellByPosition(2, 1)
        oCellCursor = oCell.createTextCursor()
        oCell.insertString(oCellCursor, "a" * 500, False)
        self.assert_(writerTables.hasWrappingText(oTable))
        self.tearDownClass()

    @classmethod
    def tearDownClass(cls):
        unoObjs = unoObjsForCurrentDoc()
        blankWriterDoc(unoObjs)


#-------------------------------------------------------------------------------
# End of Tables_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of TextChanges_test.py
#-------------------------------------------------------------------------------




class TextChangesTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = unoObjsForCurrentDoc()
        self.logger  = logging.getLogger("lingt.TestTextChanges")

    def testChangeString(self):
        oText = self.unoObjs.text           # shorthand variable name
        oVC   = self.unoObjs.viewcursor     # shorthand variable name

        oVC.gotoStartOfLine(False)
        oText.insertString(oVC, "Hello there, how are you?", 0)
        oText.insertControlCharacter(oVC, PARAGRAPH_BREAK, 0)

        oVC.goLeft(1, False)
        oVC.gotoStartOfLine(False)
        oVC.goRight(len("Hello "), False)
        oVC.goRight(len("there"), True)
        changeString(oVC, "THERE")

        oVC.gotoStartOfLine(False)
        oVC.goRight(len("Hello there"), True)
        self.assertEqual(oVC.getString(), "Hello THERE")
        oVC.collapseToEnd()
        oVC.goDown(1, False)


#-------------------------------------------------------------------------------
# End of TextChanges_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of UserVars_test.py
#-------------------------------------------------------------------------------




class UserVarsTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs = unoObjsForCurrentDoc()
        self.logger  = logging.getLogger("lingt.TestUserVars")

    def testUserVars(self):
        USERVAR_PREFIX  = "Test_"  # variables for testing
        userVars   = UserVars(
                     USERVAR_PREFIX, self.unoObjs.document, self.logger)
        userVars.set("TestVar_1", "hamburger")
        result = userVars.get("TestVar_1")
        self.assertEqual(result, "hamburger")

        userVars.set("TestVar_2", "0")
        result = userVars.get("TestVar_2")
        self.assertEqual(result, "0")

        result = userVars.get("TestVar_3")
        self.assertEqual(result, "")

        userVars.set("TestVar_4", "something")
        userVars.set("TestVar_4", "")
        result = userVars.get("TestVar_4")
        self.assertEqual(result, "")

        userVars.delete("TestVar_1")
        result = userVars.get("TestVar_1")
        self.assertEqual(result, "")
        result = userVars.get("TestVar_2")
        self.assertEqual(result, "0")

        userVars.delete("TestVar_2")
        userVars.delete("TestVar_3")
        userVars.delete("TestVar_4")
        result = userVars.get("TestVar_2")
        self.assertEqual(result, "")
        result = userVars.get("TestVar_3")
        self.assertEqual(result, "")


#-------------------------------------------------------------------------------
# End of UserVars_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of XML_Readers_test.py
#-------------------------------------------------------------------------------




class XML_Readers_PhonTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs    = unoObjsForCurrentDoc()
        self.logger     = logging.getLogger("lingt.TestPhonology")
        USERVAR_PREFIX  = "LTp_"  # LinguisticTools Phonology variables
        self.userVars   = UserVars(
                          USERVAR_PREFIX, self.unoObjs.document, self.logger)
        self.config     = ConfigOptions()

    def testPA(self):
        self.config.filepath = os.path.join(TESTDATA_FOLDER,
                                            "PAdata.paxml")
        self.config.phoneticWS = ""
        xmlReader = PhonReader(
                    self.config, self.unoObjs, self.userVars)
        self.assertEqual(xmlReader.get_filetype(self.config.filepath), "paxml")

        exampleDict = xmlReader.read()
        self.assert_(str.lower("JPDN23.1") in exampleDict)
        phonEx = exampleDict[str.lower("JPDN23.1")]
        self.assertEqual(phonEx.refText, "JPDN23.1")
        self.assertEqual(phonEx.gloss, "unmarried cousin")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        self.assert_(str.lower("JPDN37.4") in exampleDict)
        phonEx = exampleDict[str.lower("JPDN37.4")]
        self.assertEqual(phonEx.refText, "JPDN37.4")
        self.assertEqual(phonEx.gloss, "")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "JPDN58.02")

    def testTbx1(self):
        self.config.filepath = os.path.join(TESTDATA_FOLDER,
                                            "TbxPhonCorpus.xml")
        self.config.phoneticWS = ""
        xmlReader = PhonReader(
                    self.config, self.unoObjs, self.userVars)
        self.assertEqual(xmlReader.get_filetype(self.config.filepath), "xml")

        exampleDict = xmlReader.read()
        self.assert_(str.lower("JPDN21.5") in exampleDict)
        phonEx = exampleDict[str.lower("JPDN21.5")]
        self.assertEqual(phonEx.refText, "JPDN21.5")
        self.assertEqual(phonEx.gloss, "elder sister")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        self.assert_(str.lower("EGAN03.37") in exampleDict)
        phonEx = exampleDict[str.lower("EGAN03.37")]
        self.assertEqual(phonEx.refText, "EGAN03.37")
        self.assertEqual(phonEx.gloss, "five")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertEqual(phonEx.phonemic, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "JPDN37.6")

    def testTbx2(self):
        self.userVars.set("SFMarker_Gloss", "gl123")    # doesn't exist
        self.config.filepath = os.path.join(TESTDATA_FOLDER,
                                            "TbxPhonCorpus.xml")
        self.config.phoneticWS = ""
        xmlReader = PhonReader(
                    self.config, self.unoObjs, self.userVars)

        exampleDict = xmlReader.read()
        self.assert_(str.lower("JPDN21.5") in exampleDict)
        phonEx = exampleDict[str.lower("JPDN21.5")]
        self.assertEqual(phonEx.refText, "JPDN21.5")
        self.assertEqual(phonEx.gloss, "")
        self.assertNotEqual(phonEx.phonetic, "")
        self.assertNotEqual(phonEx.phonemic, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "JPDN37.6")

        self.userVars.set("SFMarker_Gloss", "") # reset

class XML_Readers_GramTestCase(unittest.TestCase):

    def setUp(self):
        self.unoObjs    = unoObjsForCurrentDoc()
        self.logger     = logging.getLogger("lingt.TestGrammar")
        USERVAR_PREFIX  = "LTg_"  # Grammar
        self.userVars   = UserVars(
                          USERVAR_PREFIX, self.unoObjs.document, self.logger)
        self.config     = ConfigOptions()

    def testTbx(self):
        filepath = os.path.join(TESTDATA_FOLDER, "TbxIntHunt06.xml")
        fileItem             = LingExFileItem()
        fileItem.filepath    = filepath
        self.config.fileList = [fileItem]
        self.config.SeparateMorphColumns = True
        self.config.ShowMorphemeBreaks   = True

        xmlReader = InterlinReader(
                    self.config, self.unoObjs, self.userVars)
        exampleDict = xmlReader.read()
        self.assertEqual(xmlReader.get_filetype(filepath, xmlReader.dom),
                         "toolbox")

        self.assert_(str.lower("Hunt06") in exampleDict)
        gramEx = exampleDict[str.lower("Hunt06")]
        self.assertEqual(gramEx.refText, "Hunt06")
        self.assertEqual(gramEx.freeTrans,
            '"Not so.  Tell him, "We should take along the sister\'s ' +
            'husband and go to the hill for hunting.\'" Only when he hunts ' +
            'they will go.')
        self.assertEqual(len(gramEx.wordList), 13)

        word1 = gramEx.wordList[0]
        self.assertNotEqual(word1.text, "")
        self.assertEqual(word1.orth, "")
        self.assertEqual(len(word1.morphList), 1)
        morph1 = word1.morphList[0]
        self.assertEqual(morph1.gloss, "like.that")
        self.assertEqual(morph1.pos, "adv")
        self.assertNotEqual(morph1.text, "")
        self.assertEqual(morph1.orth, "")

        word4 = gramEx.wordList[3]
        self.assertEqual(len(word4.morphList), 2)
        morph1 = word4.morphList[0]
        self.assertEqual(morph1.gloss, "sister")
        self.assertEqual(morph1.pos, "n")
        self.assertNotEqual(morph1.text, "")
        self.assertEqual(morph1.orth, "")

        suggestions = xmlReader.getSuggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0], "Hunt01")

    def testTbxOrth(self):
        filepath = os.path.join(TESTDATA_FOLDER, "TbxIntHunt06.xml")
        fileItem             = LingExFileItem()
        fileItem.filepath    = filepath
        self.config.fileList = [fileItem]
        self.config.SeparateMorphColumns = True
        self.config.ShowMorphemeBreaks   = True
        self.userVars.set("SFMarker_Orthographic", "or")
        self.userVars.set("SFMarker_OrthographicMorph", "mbtam")

        xmlReader = InterlinReader(
                    self.config, self.unoObjs, self.userVars)
        exampleDict = xmlReader.read()
        gramEx = exampleDict[str.lower("Hunt06")]
        word1 = gramEx.wordList[0]
        self.assertNotEqual(word1.orth, "")
        morph1 = word1.morphList[0]
        self.assertNotEqual(morph1.orth, "")

        word4 = gramEx.wordList[3]
        self.assertNotEqual(word4.orth, "")
        morph1 = word4.morphList[0]
        self.assertNotEqual(morph1.orth, "")

        self.userVars.set("SFMarker_Orthographic", "")          # reset
        self.userVars.set("SFMarker_OrthographicMorph", "")     # reset

    def testFw(self):
        filepath = os.path.join(TESTDATA_FOLDER, "FWtextPigFox.xml")
        fileItem             = LingExFileItem()
        fileItem.filepath    = filepath
        fileItem.prefix      = "Prefix-"
        self.config.fileList = [fileItem]
        self.config.SeparateMorphColumns = True
        self.config.ShowMorphemeBreaks   = True

        xmlReader = InterlinReader(
                    self.config, self.unoObjs, self.userVars)
        exampleDict = xmlReader.read()
        self.assertEqual(xmlReader.get_filetype(filepath, xmlReader.dom),
                         "fieldworks")

        self.assert_(str.lower("Prefix-1.1") in exampleDict)
        self.assert_(str.lower("Prefix-1.2") in exampleDict)
        self.assert_(not str.lower("Prefix-1.3") in exampleDict)
        self.assert_(str.lower("Prefix-2.1") in exampleDict)
        self.assert_(not str.lower("Prefix-2.2") in exampleDict)

        gramEx = exampleDict[str.lower("Prefix-1.2")]
        self.assertEqual(gramEx.refText, "Prefix-1.2")
        self.assertEqual(gramEx.freeTrans,
            u" \u200e\u200eIn his house he kept one pig and one fox ")
        self.assertEqual(len(gramEx.wordList), 7)

        word2 = gramEx.wordList[1]
        self.assertNotEqual(word2.text, "")
        self.assertEqual(word2.orth, "")
        self.assertEqual(len(word2.morphList), 2)
        morph2 = word2.morphList[1]
        self.assertEqual(morph2.gloss, "LOC.in")
        self.assertEqual(morph2.pos, "case ")
        self.assertNotEqual(morph2.text, "")
        self.assertEqual(morph2.orth, "")

    def testFlexText(self):
        filepath = os.path.join(TESTDATA_FOLDER, "Sena Int.flextext")
        fileItem             = LingExFileItem()
        fileItem.filepath    = filepath
        fileItem.prefix      = "ABC "
        self.config.fileList = [fileItem]
        self.config.SeparateMorphColumns = True
        self.config.ShowMorphemeBreaks   = True

        xmlReader = InterlinReader(
                    self.config, self.unoObjs, self.userVars)
        exampleDict = xmlReader.read()
        self.assertEqual(xmlReader.get_filetype(filepath, xmlReader.dom),
                         "fieldworks")

        self.assert_(str.lower("ABC 1.1") in exampleDict)
        self.assert_(str.lower("ABC 1.2") in exampleDict)
        self.assert_(not str.lower("ABC 2.1") in exampleDict)

        gramEx = exampleDict[str.lower("ABC 1.2")]
        self.assertEqual(gramEx.refText, "ABC 1.2")
        self.assertEqual(gramEx.freeTrans, "[1.2 ft]")
        self.assertEqual(len(gramEx.wordList), 4)

        word1 = gramEx.wordList[0]
        self.assertEqual(word1.text, "Tonsene")

        word2 = gramEx.wordList[2]
        self.assertEqual(word2.text, "yathu")
        self.assertEqual(word2.orth, "")
        morph2 = word2.morphList[1]
        self.assertEqual(morph2.text, "a-")
        self.assertEqual(morph2.gloss, "assocpx")
        self.assertEqual(morph2.pos, "Poss:assocpx")
        self.assertEqual(morph2.orth, "")

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.unoObjs = UnoObjs(getContext())

    def testPhonFieldHelper(self):
        exDict      = dict()
        suggestions = []
        helper = PhonFieldHelper(exDict, suggestions)
        self.assert_(not helper.hasContents())
        helper.add("ref", "ABC")
        self.assert_(helper.hasContents())
        helper.reset()
        self.assert_(not helper.hasContents())
        helper.add("phonetic", "123")
        self.assert_(helper.hasContents())
        helper.addEx(False)
        self.assertEqual(len(exDict.keys()), 0)
        self.assertEqual(len(suggestions), 0)
        self.assert_(not helper.hasContents())
        helper.add("ref", "ABC")
        helper.add("phonetic", "123")
        helper.addEx(False)
        self.assertEqual(len(exDict.keys()), 1)
        self.assertEqual(len(suggestions), 1)
        phonEx = exDict["abc"]
        self.assertEqual(phonEx.refText, "ABC")
        self.assertEqual(phonEx.phonetic, "123")
        self.assertEqual(phonEx.phonemic, "")
        self.assertEqual(phonEx.gloss, "")
        helper.addEx(False)
        helper.addEx(False)
        helper.add("ref", "BCD")
        helper.add("phonemic", "234")
        helper.addEx(False)
        self.assertEqual(len(exDict.keys()), 2)
        phonEx = exDict["bcd"]
        self.assertEqual(phonEx.phonemic, "234")
        phonEx = exDict["abc"]
        self.assertEqual(phonEx.phonemic, "")
        self.assertEqual(len(suggestions), 1)
        sugg = suggestions[0]
        self.assertEqual(sugg, "ABC")

    def testMergedMorphemes(self):
        mm = MergedMorphemes()
        morph = LingGramMorph()
        morph.gloss = "ham"
        morph.pos   = "n"
        mm.add(morph)
        mm.add(morph)
        morphMerged = mm.getMorph(True)
        self.assertEqual(morphMerged.gloss, "ham-ham")
        self.assertEqual(morphMerged.pos, "n")

        mm = MergedMorphemes()
        morph = LingGramMorph()
        morph.gloss = "ham"
        morph.pos   = "n"
        mm.add(morph)
        morph = LingGramMorph()
        morph.gloss = "PL"
        morph.pos   = "n.suff"
        mm.add(morph)
        morphMerged = mm.getMorph(True)
        self.assertEqual(morphMerged.gloss, "ham-PL")
        self.assertEqual(morphMerged.pos, "n")

        mm = MergedMorphemes()
        morph = LingGramMorph()
        morph.gloss = "the"
        morph.pos   = "DET"
        mm.add(morph)
        morph = LingGramMorph()
        morph.gloss = "cow"
        morph.pos   = "n"
        mm.add(morph)
        morphMerged = mm.getMorph(True)
        self.assertEqual(morphMerged.gloss, "the-cow")
        self.assertEqual(morphMerged.pos, "n")


#-------------------------------------------------------------------------------
# End of XML_Readers_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of LingExamples.py
#-------------------------------------------------------------------------------



class ExGrabber:
    def __init__(self, exType, unoObjs):
        self.exType         = exType
        self.unoObjs        = unoObjs
        self.logger         = logging.getLogger("lingt.App.LingExamples")
        if self.exType == "phonology":
            USERVAR_PREFIX  = "LTp_"  # LinguisticTools Phonology variables
        else:
            USERVAR_PREFIX  = "LTg_"  # LinguisticTools Grammar variables
        self.userVars       = UserVars(
                              USERVAR_PREFIX, unoObjs.document, self.logger)
        self.msgbox         = MessageBox(unoObjs)
        if self.exType == "phonology":
            self.styles        = PhonologyStyles(
                                 self.unoObjs, self.userVars)
            self.outputManager = PhonMgr(unoObjs, self.styles)
        else:
            self.styles        = GrammarStyles(
                                 self.unoObjs, self.userVars)
            self.outputManager = InterlinMgr(unoObjs, self.styles)
        self.exUpdater         = ExUpdater(
                                 unoObjs, self.outputManager, USERVAR_PREFIX)
        self.search            = ExampleSearch(unoObjs)
        self.config            = None
        self.replacingRefs     = True  # replacing #ref no's versus updating
        self.examplesDict      = None
        self.suggestions       = []
        self.foundString       = None
        self.messagesDisplayed = []    # don't keep displaying for updating all
        self.logger.debug("ExGrabber init() finished")

    def setUpdateExamples(self, newVal):
        self.replacingRefs = not newVal

    def isUpdatingExamples(self):
        return not self.replacingRefs

    def addExampleNumbers(self):
        self.outputManager.addExampleNumbers()

    def insertByRefnum(self, refTextRough):
        self.__readSettings()
        if not self.__readData():
            return
        self.logger.debug("do the insertion.")
        unused_success = self.__insertEx(refTextRough, False, False)

    def findNext(self, searchFromBeginning):
        """Returns true if a ref number is found."""
        self.logger.debug("findNext(" + repr(searchFromBeginning) + ")")
        oldFoundString = self.foundString
        if self.replacingRefs:
            self.foundString = self.search.findRefNumber(searchFromBeginning)
        else:
            styleNames = self.styles.getStyleNames()
            self.foundString = self.search.findRefCharStyle(
                               styleNames["ref"], searchFromBeginning)
        if self.foundString is None and oldFoundString is not None:
            self.foundString = oldFoundString
        if self.foundString:
            return True
        return False

    def replace(self, searchFromBeginning):
        """Returns true if another ref number is found after replacing."""
        self.__readSettings()
        if (self.exType == 'grammar' and self.isUpdatingExamples() and
            not self.config.MakeOuterTable
           ):
            self.msgbox.display("To update examples, 'Outer table' must be "
                                "marked in Grammar Settings.")
            return False
        if not self.foundString:
            return self.findNext(searchFromBeginning)
        refnumFound = self.foundString

        if not self.__readData():
            return False
        if self.replacingRefs:
            success = self.__insertEx(refnumFound, True, False)
        else:
            success = self.__updateEx(refnumFound)
        if not success:
            self.foundString = None
            return False
        if self.replacingRefs:
            self.foundString = self.search.findRefNumber(False)
        else:
            self.foundString = self.search.findRefCharStyle(
                               self.config.styleNames["ref"], False)
        return self.foundString

    def replaceAll(self):
        """Replace all #ref no's or update all existing examples."""
        self.__readSettings()
        if (self.exType == 'grammar' and self.isUpdatingExamples() and
            not self.config.MakeOuterTable
           ):
            self.msgbox.display("To update examples, 'Outer table' must be "
                                "marked in Grammar Settings.")
            return
        if not self.__readData():
            return 
        firstTime = True
        prevRefUpdated    = ""
        repeatedCount     = 0
        replacementsCount = 0
        while True:
            if self.replacingRefs:
                self.foundString = self.search.findRefNumber(
                                   firstTime, True)
            else:
                if self.config:
                    charStyleName = self.config.styleNames["ref"]
                else:
                    styleNames = self.styles.getStyleNames()
                    charStyleName = styleNames["ref"]
                self.foundString = self.search.findRefCharStyle(
                                   charStyleName, firstTime, True)
            if not self.foundString:
                break
            refnumFound = self.foundString
            firstTime = False
            try:
                if self.replacingRefs:
                    success = self.__insertEx(
                        refnumFound, True, False, replacingAll=True)
                    if success:
                        replacementsCount += 1
                else:
                    success = self.__updateEx(
                        refnumFound, updatingAll=True)
                    if success:
                        replacementsCount += 1
                    if refnumFound == prevRefUpdated:
                        ## Updated the same number twice. It might be an
                        ## infinite loop.
                        self.logger.debug(
                            "Repeated ex " + str(repeatedCount) + " times.")
                        repeatedCount += 1
                        MAX_REPETITIONS = 5
                        div, mod = divmod(repeatedCount, MAX_REPETITIONS)
                        if repeatedCount > 0 and mod == 0:
                            refnumDisplay = refnumFound.strip()
                            if not self.msgbox.displayOkCancel(
                                "Updated '%s' %d times in a row. Keep going?",
                                (refnumDisplay, repeatedCount)
                               ):
                                raise UserInterrupt()
                    else:
                        prevRefUpdated = refnumFound
                        repeatedCount = 1
            except UserInterrupt:
                break
        plural = "" if replacementsCount == 1 else "s" # add "s" if plural
        if self.replacingRefs:
            self.msgbox.display(
                "Replaced %d example%s." % (replacementsCount, plural))
        else:
            self.msgbox.display(
                "Updated %d example%s." % (replacementsCount, plural))

    def __readSettings(self):
        """Get settings from user vars."""
        if self.config is None:
            self.logger.debug("Getting settings")
            settings    = Settings (
                          self.exType, self.unoObjs, self.logger, self.userVars)
            self.config = settings.getConfig()
            if self.exType == "grammar":
                if not self.config.ShowComparisonDoc:
                    self.exUpdater.doNotMakeCompDoc()

    def __readData(self):
        """
        Read examples from data files.
        Returns True if there is data.
        """
        if self.examplesDict == None:
            self.logger.debug("Getting examples dict")
            if self.exType == "phonology":
                fileReader = PhonReader(
                             self.config, self.unoObjs, self.userVars)
            else:
                fileReader = InterlinReader(
                             self.config, self.unoObjs, self.userVars)
            self.examplesDict = fileReader.read()
            if len(self.examplesDict) == 0:
                return False
            self.suggestions  = fileReader.getSuggestions()
        return True

    def __insertEx(self, refTextRough, deleteRefNum, updatingEx,
                   replacingAll=False):
        """
        Set updatingEx to True if updating the example.
        returns True if successful.
        throws UserInterrupt
        """
        self.logger.debug("insertEx " + refTextRough)
        self.logger.debug("Got " + str(len(self.examplesDict)) + " examples")

        ## Set ref num

        refnum = refTextRough.strip()
        if refnum.startswith("#"):
            refnum = refnum[1:]  # keep all but first character

        ## Select the specified ref number

        refnum_key = refnum.lower() # case insensitive
        if refnum_key in self.examplesDict:
            self.logger.debug(
                "Inserting " + self.examplesDict[refnum_key].refText)

            ## Display the data in the Writer doc

            if updatingEx:
                self.exUpdater.gotoAfterEx()
            self.outputManager.setConfig(self.config)
            try:
                self.outputManager.outputExample(
                    self.examplesDict[refnum_key], deleteRefNum, updatingEx)
                return True
            except LingtError as exc:
                if replacingAll:
                    if exc.msg not in self.messagesDisplayed:
                        self.messagesDisplayed.append(exc.msg)
                        result = self.msgbox.displayOkCancel(
                                 exc.msg, exc.msg_args)
                        if not result:
                            # User pressed Cancel
                            raise UserInterrupt()
                    return False
                else:
                    self.msgbox.display(exc.msg, exc.msg_args)
                    return False

        ## Display a message that the number was not found

        message = "Could not find ref number %s"
        varsDisplay = [refnum]  # to fill in %s value
        suggNum = 0
        MAX_SUGGESTIONS = 3
        if len(self.suggestions) > 0:
            message += "\n\nSuggestions\n%s"
            suggString = ""
            for suggestion in self.suggestions:
                suggNum += 1
                if suggNum > MAX_SUGGESTIONS:
                    break
                suggString += "\t%s\n" % (suggestion)
            varsDisplay.append(suggString)
        if replacingAll:
            if not self.msgbox.displayOkCancel(message, tuple(varsDisplay)):
                # User pressed Cancel
                raise UserInterrupt()
            return False
        else:
            self.msgbox.display(message, tuple(varsDisplay))
            return False

    def __updateEx(self, refTextRough, updatingAll=False):
        """
        This method gets called after a ref number to update has been selected
        in the document. The order of the next few steps is as follows:
        1. Call gotoAfterEx() to move out of the table.
        2. Insert the new example without the example number.
        3. Call moveExNumber().
        Steps 1 and 2 are done in __insertEx().

        returns True if successful.
        throws UserInterrupt
        """
        self.logger.debug("updateEx BEGIN")
        if self.exType == 'grammar':
            if not self.search.refInTable():
                message = "Found a ref number, but it must be in an outer " \
                          "table in order to be updated."
                if updatingAll:
                    if message not in self.messagesDisplayed:
                        self.messagesDisplayed.append(message)
                        if not self.msgbox.displayOkCancel(message):
                            # User pressed Cancel
                            raise UserInterrupt()
                else:
                    self.msgbox.display(message)
                return False

        if not self.__insertEx(refTextRough, False, True, updatingAll):
            return False

        if self.exType == "grammar":
            self.exUpdater.moveExNumber()
            self.exUpdater.moveExamplesToNewDoc()
        else:
            self.exUpdater.deleteOldPhonEx()
        return True

class Settings:
    def __init__(self, dlgType, unoObjs, logger, userVars):
        self.exType   = dlgType
        self.unoObjs  = unoObjs
        self.logger   = logger
        self.userVars = userVars
        self.msgbox   = MessageBox(unoObjs)
        self.config   = ConfigOptions()
        
    def getConfig(self):
        if self.exType == "phonology":
            return self.__getPhonologySettings()
        else:
            return self.__getGrammarSettings()

    def __getPhonologySettings(self):
        """Get file paths, style names, and other options that were
        set in the Phonology Settings dialog.
        """
        ## File settings

        self.config.filepath   = self.userVars.get("XML_filePath")
        self.config.phoneticWS = self.userVars.get("PhoneticWritingSystem")

        ## Style names

        styles = PhonologyStyles(self.unoObjs, self.userVars)
        self.config.styleNames = styles.getStyleNames()

        ## Options

        self.config.showBrackets = False
        if self.userVars.getInt("ShowBrackets") == 1:
            self.config.showBrackets = True

        self.config.PhonemicLeftmost = True
        leftmost = self.userVars.get("Leftmost")
        if leftmost == "phonetic":
            self.config.PhonemicLeftmost = False

        self.logger.debug("Finished getting settings")
        return self.config

    def __getGrammarSettings(self):
        """Get file paths, style names, and other options from user vars."""
        self.logger.debug("getGrammarSettings begin")

        ## File paths

        fileList = FileItemList(LingExFileItem,
                                             self.unoObjs, self.userVars)
        fileList.loadFromUserVars()
        self.config.fileList = fileList.fileItems
        self.logger.debug(
            "Using " + str(len(self.config.fileList)) + " file(s)")

        ## Style names

        styles = GrammarStyles(self.unoObjs, self.userVars)
        self.config.styleNames = styles.getStyleNames()

        ## Checkboxes

        self.config.ShowOrthoTextLine = False
        if self.userVars.getInt("ShowOrthoTextLine") == 1:
            self.config.ShowOrthoTextLine = True
        self.config.ShowText = False
        if self.userVars.getInt("ShowText") == 1:
            self.config.ShowText = True
        self.config.ShowOrthoMorphLine = False
        if self.userVars.getInt("ShowOrthoMorphLine") == 1:
            self.config.ShowOrthoMorphLine = True
        self.config.ShowMorphemeBreaks = False
        if self.userVars.getInt("ShowMorphBreaks") == 1:
            self.config.ShowMorphemeBreaks = True
        self.config.SeparateMorphColumns = False
        if self.userVars.getInt("SeparateMorphColumns") == 1:
            self.config.SeparateMorphColumns = True
        self.config.ShowPartOfSpeech = False
        if self.userVars.getInt("ShowPartOfSpeech") == 1:
            self.config.ShowPartOfSpeech = True
        self.config.FreeTransInQuotes = False
        if self.userVars.getInt("FreeTransInQuotes") == 1:
            self.config.FreeTransInQuotes = True
        self.config.POS_AboveGloss = False
        if self.userVars.getInt("POS_AboveGloss") == 1:
            self.config.POS_AboveGloss = True
        self.config.InsertNumbering = False
        if self.userVars.getInt("InsertNumbering") == 1:
            self.config.InsertNumbering = True
        self.config.MakeOuterTable = False
        if self.userVars.getInt("MakeOuterTable") == 1:
            self.config.MakeOuterTable = True

        if not self.config.ShowMorphemeBreaks:
            self.config.SeparateMorphColumns = False
        if not self.config.ShowPartOfSpeech:
            self.config.POS_AboveGloss = False

        self.config.ShowComparisonDoc = True
        varname = "ComparisonDoc"
        if not self.userVars.isEmpty(varname):
            if self.userVars.getInt(varname) == 0:
                self.config.ShowComparisonDoc = False

        val = 0
        varname = "TableBottomMargin"
        try:
            strVal = self.userVars.get(varname)
            val = float(strVal)
        except ValueError:
            self.userVars.set(varname, "")
        self.config.tableBottomMargin = val

        ## Numbering column width and Row Height

        self.config.numberingColumnWidth = \
            self.userVars.getInt("NumberingColWidth")

        varname = "StartingOuterRowHeight"
        if self.userVars.isEmpty(varname):
            defaultVal = "2"
            self.userVars.set(varname, defaultVal)
            self.config.startingOuterRowHeight = int(defaultVal)
        else:
            self.config.startingOuterRowHeight = self.userVars.getInt(varname)

        ## Option buttons

        self.config.MethodTables = False
        self.config.MethodFrames = False
        method = self.userVars.get("Method")
        if method == "tables":
            self.config.MethodTables = True
        else:
            self.config.MethodFrames = True
        self.logger.debug("Finished getting settings")
        return self.config

#-------------------------------------------------------------------------------
# End of LingExamples.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgGrabEx.py
#-------------------------------------------------------------------------------



def ShowPhonologyDlg(ctx=uno.getComponentContext()):
    ShowDlgForType(ctx, "phonology")

def ShowGrammarDlg(ctx=uno.getComponentContext()):
    ShowDlgForType(ctx, "grammar")

def ShowDlgForType(ctx, dlgType):
    logger = logging.getLogger("lingt.UI.DlgGrabEx")
    logger.debug("----ShowDlg(" + dlgType + ")--------------------------------")
    unoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgGrabExamples(dlgType, unoObjs, logger)
    if not requireInputFile(dlgType, unoObjs, dlg.userVars):
        return
    dlg.showDlg()

def requireInputFile(dlgType, unoObjs, userVars):
    """Make sure the user has specified an input file.
    If no file is specified, displays an error message and returns false.
    """
    varname = "XML_filePath"
    if dlgType == "grammar": varname = "XML_filePath00"
    filepath = userVars.get(varname)
    if filepath == "":
        msgbox = MessageBox(unoObjs)
        if dlgType == "grammar":
            msgbox.display(
                "Please go to Grammar Settings and specify a file.")
        else:
            msgbox.display(
                "Please go to Phonology Settings and specify a file.")
        return False
    return True

class DlgGrabExamples(XActionListener, XItemListener, unohelper.Base):
    """The dialog implementation."""

    def __init__(self, dlgType, unoObjs, logger):
        self.type         = dlgType
        self.unoObjs      = unoObjs
        self.logger       = logger
        self.locale       = Locale(unoObjs)
        if dlgType == "phonology":
            USERVAR_PREFIX = "LTp_"  # LinguisticTools Phonology variables
            self.titleText = self.locale.getText(
                             "Get Phonology Examples")
        else:
            USERVAR_PREFIX = "LTg_"  # LinguisticTools Grammar variables
            self.titleText = self.locale.getText(
                             "Get Interlinear Grammar Examples")
        self.userVars     = UserVars(USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox       = MessageBox(unoObjs)
        self.app          = ExGrabber(dlgType, unoObjs)
        self.dlg          = None
        self.logger.debug("DlgGrabExamples init() finished")

    def showDlg(self):
        self.logger.debug("DlgGrabEx.showDlg BEGIN")
        dlg = None
        try:
            dlg = self.unoObjs.dlgprov.createDialog(
                  "vnd.sun.star.script:LingToolsBasic.DlgExGrab"
                  "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not create dialog.")
            return
        self.dlg = dlg
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.txtRefnum             = getControl(dlg, "TxtRefnum")
            self.chkStartFromBeginning = getControl(dlg,
                                         "ChkStartFromBeginning")
            self.optSearchRefNum       = getControl(dlg,
                                         "optSearchRefNum")
            self.optSearchExisting     = getControl(dlg,
                                         "optSearchExisting")
            self.btnReplace            = getControl(dlg, "BtnReplace")
            self.btnReplaceAll         = getControl(dlg, "BtnReplaceAll")
            btnFindNext                = getControl(dlg, "BtnFindNext")
            btnReplace                 = getControl(dlg, "BtnReplace")
            btnReplaceAll              = getControl(dlg, "BtnReplaceAll")
            btnInsertEx                = getControl(dlg, "BtnInsertEx")
            btnClose                   = getControl(dlg, "BtnClose")
        except LogicError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        dlg.setTitle(self.titleText)
        self.txtRefnum.setText(self.userVars.get("EXREFNUM"))
        self.txtRefnum.setFocus()

        self.optSearchRefNum.addItemListener(self)
        self.optSearchExisting.addItemListener(self)
        varname = "SearchFor"
        if not self.userVars.isEmpty(varname):
            if self.userVars.get(varname) == "RefNum":
                self.optSearchRefNum.setState(1)    # checked
            else:
                self.optSearchExisting.setState(1)    # checked
        self.enableDisable()

        btnFindNext.setActionCommand("FindNext")
        btnFindNext.addActionListener(self)
        btnReplace.setActionCommand("Replace")
        btnReplace.addActionListener(self)
        btnReplaceAll.setActionCommand("ReplaceAll")
        btnReplaceAll.addActionListener(self)
        btnInsertEx.setActionCommand("InsertEx")
        btnInsertEx.addActionListener(self)
        btnClose.setActionCommand("Close")
        btnClose.addActionListener(self)

        self.dlgClose = dlg.endExecute
        dlg.execute()

        if self.type == "grammar":
            self.app.addExampleNumbers()
        dlg.dispose()

    def itemStateChanged(self, unused_itemEvent):
        """XItemListener event handler.
        Could be for the list control or for enabling and disabling.
        """
        self.logger.debug("itemStateChanged BEGIN")
        self.enableDisable()

    def enableDisable(self):
        """Enable or disable controls as appropriate."""
        if self.optSearchRefNum.getState() == 1:
            self.btnReplace.Label    = self.locale.getText(
                                       "Replace with Example")
            self.btnReplaceAll.Label = self.locale.getText(
                                       "Replace All")
            self.app.setUpdateExamples(False)
            self.userVars.set("SearchFor", "RefNum")
            self.chkStartFromBeginning.setState(1) # checked
        else:
            self.btnReplace.Label    = self.locale.getText(
                                       "Update Example")
            self.btnReplaceAll.Label = self.locale.getText(
                                       "Update All")
            self.app.setUpdateExamples(True)
            self.userVars.set("SearchFor", "Existing")
            self.chkStartFromBeginning.setState(0) # unchecked

    def actionPerformed(self, event):
        self.logger.debug("An action happened: " + event.ActionCommand)

        if event.ActionCommand == "InsertEx":
            self.logger.debug("Inserting example...")
            refText = self.txtRefnum.getText()
            if refText == "":
                self.msgbox.display("Please enter a ref number.")
                return
            self.userVars.set("EXREFNUM", refText)
            self.app.insertByRefnum(refText)

        elif event.ActionCommand == "FindNext":
            self.logger.debug("Searching...")
            startFromBeginning = (self.chkStartFromBeginning.getState() == 1)
            found = self.app.findNext(startFromBeginning)
            if found:
                self.chkStartFromBeginning.setState(0)  # unchecked
            
        elif event.ActionCommand == "Replace":
            self.logger.debug("Replacing...")
            startFromBeginning = (self.chkStartFromBeginning.getState() == 1)
            found = self.app.replace(startFromBeginning)
            if found:
                self.chkStartFromBeginning.setState(0)  # unchecked

        elif event.ActionCommand == "ReplaceAll":
            self.logger.debug("Replacing all...")
            if self.app.isUpdatingExamples():
                result = self.msgbox.displayOkCancel(
                    "Update all examples now?  " +
                    "It is recommended to save a copy of your document " +
                    "first.")
                if not result:
                    return
                ## Refresh the window
                oContainerWindow = self.unoObjs.frame.getContainerWindow()
                oContainerWindow.setVisible(False)
                oContainerWindow.setVisible(True)

            self.chkStartFromBeginning.setState(1)  # checked
            self.app.replaceAll()

        elif event.ActionCommand == "Close":
            self.logger.debug("Action command was Close")
            self.dlgClose()

#-------------------------------------------------------------------------------
# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of DlgGrabEx.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of WritingSysReader.py
#-------------------------------------------------------------------------------



class WritingSysReader(FileReader):
    def __init__(self, filepath, unoObjs):
        FileReader.__init__(self, unoObjs)
        self.filepath = filepath

    def read(self):
        self.writingSystems = []  # list of WritingSystem objects
        filefolder = os.path.dirname(self.filepath)
        filelist   = os.listdir(filefolder)
        for filename in filelist:
            self.__getWritingSystemFromFile(filefolder, filename)
        subdir = os.path.join(filefolder, "WritingSystems")
        if os.path.exists(subdir):
            filelist = os.listdir(subdir)
            for filename in filelist:
                self.__getWritingSystemFromFile(subdir, filename)
        return self.writingSystems

    def __getWritingSystemFromFile(self, folder, filename):
        """Read an .ldml LIFT file. Add its info to writingSystems list."""
        self.logger.debug("getWritingSystem BEGIN")
        ws = WritingSystem()

        ## Get the internal code from the filename

        m = re.match(r"(.+)\.ldml$", filename)
        if m == None: return  # Ignore this file
        #ws.internalCode = m.group(1)    # doesn't work for LIFT format???

        ## Parse the XML to get writing system information

        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            self.msgbox.display("Cannot find file %s", (filepath,))
            return
        try:
            self.dom = xml.dom.minidom.parse(filepath)
        except xml.parsers.expat.ExpatError as exc:
            self.msgbox.display("Error reading file %s\n\n%s",
                                (filepath, str(exc).capitalize()))
            return

        ## Get the code (seems to be different from FW Internal Code)

        elems = self.dom.getElementsByTagName("identity")
        if len(elems) > 0:
            elem = elems[0]
            languages = elem.getElementsByTagName("language")
            if len(languages) > 0:
                language = languages[0]
                if language.attributes is not None:
                    ws.internalCode = language.getAttribute("type")
            variants = elem.getElementsByTagName("variant")
            if len(variants) > 0:
                variant = variants[0]
                if variant.attributes is not None:
                    variantVal = variant.getAttribute("type")
                    ws.internalCode += "-x-" + variantVal

        ## Get the language name

        elems = self.dom.getElementsByTagName("palaso:languageName")
        if len(elems) > 0:
            elem = elems[0]
            if elem.attributes is not None:
                ws.name = elem.getAttribute("value")

        ## Add results to the list

        if ws.internalCode != "":
            if ws.name == "": ws.name = ws.internalCode
            self.writingSystems.append(ws)
            self.logger.debug("Got " + ws.name + ", " + ws.internalCode)

class WritingSystem:
    """Information about a writing system."""
    def __init__(self):
        self.name         = ""
        self.internalCode = ""

#-------------------------------------------------------------------------------
# End of WritingSysReader.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgWritingSystem.py
#-------------------------------------------------------------------------------



class DlgWritingSystem(XActionListener, unohelper.Base):

    def __init__(self, defaultCode, unoObjs):
        self.writingSystems = []
        self.def_ws_code    = defaultCode
        self.unoObjs        = unoObjs
        self.logger         = logging.getLogger("lingt.UI.DlgWritingSystem")
        self.msgbox         = MessageBox(unoObjs)
        self.locale         = Locale(unoObjs)
        self.selectedWS     = WritingSystem()

    def readFile(self, filepath):
        fileReader          = WritingSysReader(
                              filepath, self.unoObjs)
        self.writingSystems = fileReader.read()

    def getResult(self):
        return self.selectedWS
        
    def showDlg(self):
        self.logger.debug("DlgWritingSystem.showDlg BEGIN")
        dlg = None
        try:
            dlg = self.unoObjs.dlgprov.createDialog(
                  "vnd.sun.star.script:LingToolsBasic.DlgWritingSystem"
                  "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not create dialog.")
            return
        self.logger.debug("Created dialog.")

        try:
            self.listbox = dlg.getControl("WSListBox")
            btnOK        = dlg.getControl("BtnOK")
        except LogicError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        def_ws_display = self.locale.getText("(none)")
        self.listbox.addItem(def_ws_display, 0)
        for ws in self.writingSystems:
            listCount = self.listbox.getItemCount()
            ws_display = "%s (%s)" % (ws.name, ws.internalCode)
            self.listbox.addItem(ws_display, listCount)  # add at end of list
            if ws.internalCode == self.def_ws_code:
                def_ws_display = ws_display
        self.listbox.selectItem(def_ws_display, True)
        self.logger.debug(
            "Added " + str(len(self.writingSystems)) + " to list.")

        btnOK.setActionCommand("OK")
        btnOK.addActionListener(self)

        self.dlgClose   = dlg.endExecute
        self.dlgDispose = dlg.dispose
        dlg.execute()

    def actionPerformed(self, event):
        self.logger.debug("An action happened: " + event.ActionCommand)
        if event.ActionCommand == "OK":
            itemPos = self.listbox.getSelectedItemPos()
            self.logger.debug("Item " + str(itemPos) + " selected.")
            if itemPos > 0:
                wsIndex = itemPos - 1   # excluding the first entry "(none)"
                self.selectedWS = self.writingSystems[wsIndex]
            self.dlgClose()
            self.logger.debug("OK finished")

    def call_dispose(self):
        self.logger.debug("disposing")
        self.dlgDispose()

#-------------------------------------------------------------------------------
# End of DlgWritingSystem.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgPhonSettings.py
#-------------------------------------------------------------------------------



def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.DlgPhonSettings")
    logger.debug("----ShowDlg()----------------------------------------------")
    unoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgPhonSettings(unoObjs, logger)
    dlg.showDlg()

class DlgPhonSettings(XActionListener, unohelper.Base):
    """The dialog implementation."""

    def __init__(self, unoObjs, logger):
        self.unoObjs   = unoObjs
        self.logger    = logger
        USERVAR_PREFIX = "LTp_"  # LinguisticTools Phonology variables
        self.userVars  = UserVars(USERVAR_PREFIX, unoObjs.document, logger)
        self.msgbox    = MessageBox(unoObjs)

    def showDlg(self):
        self.logger.debug("DlgPhonSettings.showDlg BEGIN")
        dlg = None
        try:
            dlg = self.unoObjs.dlgprov.createDialog(
                  "vnd.sun.star.script:LingToolsBasic.DlgPhnlgySettings"
                  "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not create dialog.")
            return
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.fileControl         = getControl(dlg, "FileControl1")
            self.checkboxBrackets    = getControl(dlg, "CheckboxBrackets")
            self.txtWritingSys       = getControl(dlg, "TxtWritingSystem")
            self.optionPhonemicFirst = getControl(dlg, "OptPhonemicFirst")
            self.optionPhoneticFirst = getControl(dlg, "OptPhoneticFirst")
            btnSelectWS              = getControl(dlg, "BtnSelectWS")
            buttonOK                 = getControl(dlg, "ButtonOK")
            buttonCancel             = getControl(dlg, "ButtonCancel")
        except LogicError as exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        ## Set default values of controls

        self.fileControl.setText(self.userVars.get("XML_filePath"))

        varname = "ShowBrackets"
        if not self.userVars.isEmpty(varname):
            self.checkboxBrackets.setState(self.userVars.getInt(varname))

        self.txtWritingSys.setText(self.userVars.get("PhoneticWritingSystem"))

        leftmost = self.userVars.get("Leftmost")
        if leftmost == "phonetic":
            self.optionPhoneticFirst.setState(1)   # set to selected

        ## Buttons

        btnSelectWS.setActionCommand("SelectWritingSys")
        btnSelectWS.addActionListener(self)
        buttonOK.setActionCommand("UpdateSettings")
        buttonOK.addActionListener(self)
        buttonCancel.setActionCommand("Cancel")
        buttonCancel.addActionListener(self)

        self.dlgClose = dlg.endExecute
        dlg.execute()
        dlg.dispose()

    def actionPerformed(self, event):
        self.logger.debug("An action happened: " + event.ActionCommand)
        if event.ActionCommand == "SelectWritingSys":
            self.logger.debug("Selecting Writing System...")

            filepath = self.fileControl.getText()
            if not re.search(r"\.lift$", filepath):
                self.msgbox.display(
                    "If you want to use LIFT data, then first specify a "
                    "LIFT file exported from FieldWorks.")
                return
            defaultCode = self.txtWritingSys.getText()
            dlgWS = DlgWritingSystem(defaultCode, self.unoObjs)
            dlgWS.readFile(filepath)
            if len(dlgWS.writingSystems) == 0:
                self.msgbox.display("No writing systems found.")
                return
            dlgWS.showDlg()
            writingSystem = dlgWS.getResult()
            dlgWS.call_dispose()
            self.txtWritingSys.setText(writingSystem.internalCode)

        elif event.ActionCommand == "UpdateSettings":
            self.logger.debug("Updating Settings...")

            ## Save new variable settings

            filePath = self.fileControl.getText()
            self.userVars.set("XML_filePath", filePath)

            wsCode = self.txtWritingSys.getText()
            self.userVars.set("PhoneticWritingSystem", wsCode)

            state = self.checkboxBrackets.getState() # 0 not checked, 1 checked
            self.userVars.set("ShowBrackets", str(state))

            state = self.optionPhonemicFirst.getState()
            if state == 1:  # selected
                self.userVars.set("Leftmost", "phonemic")
            else:
                self.userVars.set("Leftmost", "phonetic")

            ## Create the styles and finish

            styles = PhonologyStyles(self.unoObjs, self.userVars)
            styles.createStyles()

            unused = PhonologyTags(self.userVars)  # set tag names
            varname = "ExperTrans_Phonemic"
            if self.userVars.isEmpty(varname):
                self.userVars.set(varname, "0") # default is False

            self.dlgClose()

        elif event.ActionCommand == "Cancel":
            self.logger.debug("Action command was Cancel")
            self.dlgClose()


#-------------------------------------------------------------------------------
# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of DlgPhonSettings.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Phonology_test.py
#-------------------------------------------------------------------------------




class PhonologyTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.logger  = logging.getLogger("lingt.TestPhonSettings")
        for klass in DlgPhonSettings, DlgWritingSystem, DlgGrabExamples:
            modifyClass_showDlg(klass)
        modifyMsgboxDisplay()
        self.surroundNum = 0    # number for surroundings
        try:
            self.assertRegex
            self.assertNotRegex
        except AttributeError:
            try:
                self.assertRegexpMatches
                self.assertNotRegexpMatches
            except AttributeError:
                def matches(s, pat):
                    self.assertTrue(re.search(pat, s),
                                    "'%s' did not match /%s/" % (s, pat))
                def notMatches(s, pat):
                    self.assertFalse(re.search(pat, s),
                                     "'%s' matched /%s/" % (s, pat))
                self.assertRegex    = matches
                self.assertNotRegex = notMatches

    def setUp(self):
        self.unoObjs = unoObjsForCurrentDoc()
        self.locale  = Locale(self.unoObjs)
        blankWriterDoc(self.unoObjs)
        self.dlgSettings = None
        self.dlgGrabEx   = None

    def runDlgSettings(self, dispose):
        self.dlgSettings = DlgPhonSettings(self.unoObjs, self.logger)
        self.dlgSettings.showDlg()
        if dispose:
            self.dlgSettings.dlgDispose()
            self.dlgSettings = None

    def runDlgGrabEx(self, dispose):
        self.dlgGrabEx   = DlgGrabExamples(
                           "phonology", self.unoObjs, self.logger)
        self.dlgGrabEx.showDlg()
        if dispose:
            self.dlgGrabEx.dlgDispose()
            self.dlgGrabEx = None

    def verifyString(self, whichString, textExpected):
        """
        After phon example is created, verify string not including brackets.

        whichString=1 gives first  string, phonemic by default
        whichString=2 gives second string, phonetic by default
        whichString=3 gives gloss
        whichString=4 gives ref num

        These numbers will be offset if for example gloss has multiple words.
        """
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        oVC.goUp(1, False)
        oVC.gotoStartOfLine(False)
        wordCursor = oVC.getText().createTextCursorByRange(oVC)
        for unused in range(whichString):
            wordCursor.gotoNextWord(False)  # move before string, after bracket
        oVC.gotoRange(wordCursor, False)
        oVC.goRight(len(textExpected), True)
        self.assertEqual(oVC.getString(), textExpected)
        oVC.goDown(1, False)

    def test1_writingSystems(self):
        """
        Verify that selecting a writing system from the WS dialog works
        correctly, and that it correctly changes the example produced.
        """
        def useDialog(selfNew):
            filepath = os.path.join(TESTDATA_FOLDER, "FWlexicon.lift")
            selfNew.fileControl.setText(filepath)
            selfNew.actionPerformed(MyActionEvent("SelectWritingSys"))
            selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
        DlgPhonSettings.useDialog = useDialog
        def useDialog(selfNew):
            selfNew.txtRefnum.setText("JPDN21.4")
            selfNew.actionPerformed(MyActionEvent("InsertEx"))
        DlgGrabExamples.useDialog = useDialog

        # Here is a quick line to get hex code points of unicode string s:
        # for c in s: print hex(ord(c))
        dataSets = [
            ("Irula (Phonetic) (iru-x-X_ETIC)", 2, "iru-x-X_ETIC",  # IPA
             u"amman",
             u"ammɛ"),
            ("Vette Kada Irula (iru)", 3, "iru", # Tamil script
             u"\u0b85\u0bae\u0bcd\u0bae\u0bc6", # Tamil /amman/
             u"ammɛ"),
            ("(none)", 0, "",
             u"\u0b85\u0bae\u0bcd\u0bae\u0bc6", # Tamil /amman/
             u"ammɛ")]

        for wsDisplay, wsIndex, wsCode, phm, pht in dataSets:
            def useDialog(selfNew):
                selfNew.listbox.selectItem(wsDisplay, True)
                self.assertEqual(selfNew.listbox.getSelectedItemPos(), wsIndex)
                selfNew.actionPerformed(MyActionEvent("OK"))
            DlgWritingSystem.useDialog = useDialog
            self.runDlgSettings(False)
            self.assertEqual(self.dlgSettings.txtWritingSys.getText(), wsCode)
            self.dlgSettings.dlgDispose()
            self.runDlgGrabEx(True)
            self.verifyString(1, phm)
            self.verifyString(2, pht)
            self.verifyString(3, "father")
            self.verifyString(4, "JPDN21.4")

    def test2_nonLIFT(self):
        """
        Verify that toolbox and paxml files are read correctly.
        Make sure that non-lift files do not show the WS dialog.
        """
        liftErrorMsg = self.locale.getText(
                       "If you want to use LIFT data, then first specify a "
                       "LIFT file exported from FieldWorks.")
        dataSets = [
            ("TbxPhonCorpus.xml", "JPDN37.6",  u"aɖupa",   u"aɖɨpa",
             "kitchen.stove"),
            ("TbxPhonCorpus.xml", "JPDN37.4",  u"pane",    u"pæne",
             "vessel.to.store.rice"),
            ("PAdata.paxml",       "JPDN23.1",  u"matʃtʃæ", u"mətʃɛ",
             "unmarried cousin"),
            ("PAdata.paxml",       "JPDN58.02", u"bod̪e",    u"boðe",
             "bush")]
        for filename, refNum, phm, pht, ge in dataSets:
            def useDialog(selfNew):
                filepath = os.path.join(TESTDATA_FOLDER, filename)
                selfNew.fileControl.setText(filepath)
                try:
                    selfNew.actionPerformed(MyActionEvent("SelectWritingSys"))
                except MsgSentException as exc:
                    self.assertEqual(exc.msg, liftErrorMsg)
                else:
                    self.fail("Expected error message.")
                selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
            DlgPhonSettings.useDialog = useDialog
            def useDialog(selfNew):
                selfNew.txtRefnum.setText(refNum)
                selfNew.actionPerformed(MyActionEvent("InsertEx"))
            DlgGrabExamples.useDialog = useDialog
            self.runDlgSettings(False)
            wsCode = self.dlgSettings.txtWritingSys.getText()
            self.assertEqual(wsCode, "")
            self.dlgSettings.dlgDispose()
            self.runDlgGrabEx(True)
            self.verifyString(1, phm)
            self.verifyString(2, pht)
            self.verifyString(3, ge)

    def grabExInSurroundings(self, action, blankLine, refNum, firstStr):
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        self.surroundNum += 1
        numStr = str(self.surroundNum)
        oVC.getText().insertString(oVC, "begin" + numStr, False)
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        if action == 'replacing':
            oVC.getText().insertString(oVC, "#" + refNum, False)
            if not blankLine:
                oVC.getText().insertString(oVC, " ", False)
        if blankLine:
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        oVC.getText().insertString(oVC, "end" + numStr, False)
        if blankLine:
            oVC.goUp(1, False)
        else:
            oVC.gotoStartOfLine(False)
        self.runDlgGrabEx(True)
        self.verifyString(1, firstStr)

        ## Verify that beginning and ending strings were not changed.

        oVC.goUp(2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.assertEqual(oVC.getString(), "begin" + numStr)
        oVC.goDown(2, False)
        if blankLine and action == 'inserting':
            oVC.goDown(1, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        self.assertEqual(oVC.getString(), "end" + numStr)
        if blankLine and action == 'inserting':
            oVC.goUp(1, False)

    def test3_surroundings(self):
        """
        Test inserting and replacing examples, verifying that the
        examples are outputted where expected, checking the preceeding and
        following spacing, formatting and text.
        """
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        def useDialog(selfNew):
            filepath = os.path.join(TESTDATA_FOLDER, "TbxPhonCorpus.xml")
            selfNew.fileControl.setText(filepath)
            selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
        DlgPhonSettings.useDialog = useDialog
        self.runDlgSettings(True)
        for action in 'inserting', 'replacing':
            refNum   = "JPDN37.4"
            firstStr = u"pane"
            def useDialog(selfNew):
                if action == 'inserting':
                    selfNew.txtRefnum.setText(refNum)
                    selfNew.actionPerformed(MyActionEvent("InsertEx"))
                elif action == 'replacing':
                    try:
                        selfNew.actionPerformed(MyActionEvent("ReplaceAll"))
                    except MsgSentException as exc:
                        self.assertTrue(exc.msg.startswith("Replaced"))
                    else:
                        self.fail("Expected error message.")
            DlgGrabExamples.useDialog = useDialog
            for blankLine in True, False:
                for attrName, attrVal in [
                    ('Default', ""),
                    ('ParaStyleName', "Caption"),
                    ('CharStyleName', "Caption characters"),
                    ('CharFontName',  "Arial Black")
                   ]:
                    if attrName != 'Default':
                        oVC.setPropertyValue(attrName, attrVal)
                    self.grabExInSurroundings(
                        action, blankLine, refNum, firstStr)
                    if attrName == 'Default':
                        self.assertEqual(
                            oVC.getPropertyValue('ParaStyleName'), "Standard")
                        self.assertEqual(
                            oVC.getPropertyValue('CharStyleName'), "")
                        self.assertEqual(
                            oVC.getPropertyValue('CharFontName'),
                            "Times New Roman")
                    else:
                        self.assertEqual(
                            oVC.getPropertyValue(attrName), attrVal)
                    if blankLine:
                        oVC.goDown(1, False)
                    oVC.gotoEndOfLine(False)
                    oVC.getText().insertControlCharacter(
                        oVC, PARAGRAPH_BREAK, False)
                    oVC.setPropertyValue('ParaStyleName', "Standard")
                    oVC.setPropertyToDefault('CharStyleName')
                    oVC.setPropertyToDefault('CharFontName')

    def test4_settingsOptions(self):
        """
        Test phonology checkboxes and radio buttons.
        """
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        pht = u"age"    # phonetic
        phm = u"agge"   # phonemic
        for phonemicFirst in True, False:
            for brackets in True, False:
                def useDialog(selfNew):
                    filepath = os.path.join(
                               TESTDATA_FOLDER, "TbxPhonCorpus.xml")
                    selfNew.fileControl.setText(filepath)
                    if phonemicFirst:
                        selfNew.optionPhonemicFirst.setState(1)
                    else:
                        selfNew.optionPhoneticFirst.setState(1)
                    if brackets:
                        selfNew.checkboxBrackets.setState(1)
                    else:
                        selfNew.checkboxBrackets.setState(0)
                    selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
                DlgPhonSettings.useDialog = useDialog
                def useDialog(selfNew):
                    selfNew.txtRefnum.setText("JPDN21.3")
                    selfNew.actionPerformed(MyActionEvent("InsertEx"))
                DlgGrabExamples.useDialog = useDialog
                self.runDlgSettings(True)
                self.runDlgGrabEx(True)
                oVC.goUp(1, False)
                oVC.gotoStartOfLine(False)
                oVC.gotoEndOfLine(True)
                sVC = oVC.getString()
                oVC.goDown(1, False)
                if brackets:
                    if phonemicFirst:
                        self.assertRegex(sVC, "^.+/.+/.+\[.+\].+'.+'.+$")
                        self.verifyString(1, phm)
                        self.verifyString(2, pht)
                    else:
                        self.assertRegex(sVC, "^.+\[.+\].+/.+/.+'.+'.+$")
                        self.verifyString(1, pht)
                        self.verifyString(2, phm)
                else:
                    self.assertNotRegex(sVC, "/|\[|\]|'")
                    if phonemicFirst:
                        self.assertRegex(sVC, phm + ".+" + pht)
                    else:
                        self.assertRegex(sVC, pht + ".+" + phm)

    def test5_updating(self):
        """
        Test updating examples. Verify that:
        - the example is actually updated
        - the correct example number is updated
        - the old example isn't still there
        - surrounding spacing, formatting and text doesn't get messed up
        """
        blankWriterDoc(self.unoObjs)
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        examples = [
            (u"aɖɨpa", u"aɖupa", "JPDN37.6", 'Default', ''),
            (u"age",   u"agge",  "JPDN21.3", 'ParaStyleName', "Caption"),
            (u"akʰe",  u"akke",  "JPDN21.5", 'CharStyleName',
                                                   "Caption characters"),
            (u"pæne",  u"pane",  "JPDN37.4", 'CharFontName', "Arial Black")]

        ## Insert original examples

        self.surroundNum = 0
        for pht, phm, refNum, attrName, attrVal in examples:
            def useDialog(selfNew):
                filepath = os.path.join(
                           TESTDATA_FOLDER, "TbxPhonCorpus.xml")
                selfNew.fileControl.setText(filepath)
                selfNew.optionPhonemicFirst.setState(1)
                selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
            DlgPhonSettings.useDialog = useDialog
            def useDialog(selfNew):
                selfNew.txtRefnum.setText(refNum)
                selfNew.actionPerformed(MyActionEvent("InsertEx"))
            DlgGrabExamples.useDialog = useDialog
            self.runDlgSettings(True)

            self.surroundNum += 1
            numStr = str(self.surroundNum)
            if attrName != 'Default':
                oVC.setPropertyValue(attrName, attrVal)
            oVC.getText().insertString(oVC, "begin" + numStr, False)
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
            oVC.getText().insertString(oVC, "end" + numStr, False)
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
            oVC.goUp(1, False)
            oVC.gotoStartOfLine(False)
            self.runDlgGrabEx(True)
            self.verifyString(1, phm)
            self.verifyString(2, pht)
            oVC.goDown(1, False)
            oVC.setPropertyValue("ParaStyleName", "Standard")
            oVC.setPropertyToDefault("CharStyleName")
            oVC.setPropertyToDefault("CharFontName")
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)

        ## Update examples

        def useDialog(selfNew):
            filepath = os.path.join(
                       TESTDATA_FOLDER, "TbxPhonCorpus.xml")
            selfNew.fileControl.setText(filepath)
            selfNew.optionPhoneticFirst.setState(1)
            selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
        DlgPhonSettings.useDialog = useDialog
        def useDialog(selfNew):
            selfNew.optSearchExisting.setState(1)
            selfNew.enableDisable()
            try:
                modifyMsgboxOkCancel(True) # as if user clicked OK
                selfNew.actionPerformed(MyActionEvent("ReplaceAll"))
            except MsgSentException as exc:
                self.assertTrue(exc.msg.startswith("Updated"))
            else:
                self.fail("Expected error message.")
        DlgGrabExamples.useDialog = useDialog
        self.runDlgSettings(True)
        self.runDlgGrabEx(True)

        ## Check examples

        self.surroundNum = 0
        oVC.gotoStart(False)
        for pht, phm, unused, attrName, attrVal in examples:
            self.surroundNum += 1
            numStr = str(self.surroundNum)
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            self.assertEqual(oVC.getString(), "begin" + numStr)
            oVC.goDown(2, False) # to "end" line
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            self.assertEqual(oVC.getString(), "end" + numStr)
            oVC.collapseToEnd()
            oVC.gotoStartOfLine(False)
            self.verifyString(1, pht)
            self.verifyString(2, phm)
            if attrName == 'Default':
                self.assertEqual(
                    oVC.getPropertyValue('ParaStyleName'), "Standard")
                self.assertEqual(
                    oVC.getPropertyValue('CharStyleName'), "")
                self.assertEqual(
                    oVC.getPropertyValue('CharFontName'), "Times New Roman")
            else:
                self.assertEqual(oVC.getPropertyValue(attrName), attrVal)
            oVC.goDown(1, False) # to next "begin" line
        self.tearDownClass()

    @classmethod
    def tearDownClass(cls):
        unoObjs = unoObjsForCurrentDoc()
        blankWriterDoc(unoObjs)


#-------------------------------------------------------------------------------
# End of Phonology_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of Grammar_test.py
#-------------------------------------------------------------------------------




class GrammarTestCase(unittest.TestCase):
    def __init__(self, testCaseName):
        unittest.TestCase.__init__(self, testCaseName)
        self.logger  = logging.getLogger("lingt.TestPhonSettings")
        for klass in [DlgGramSettings, DlgGrabExamples]:
            modifyClass_showDlg(klass)
        modifyMsgboxDisplay()
        self.surroundNum    = 0    # number for surroundings
        self.prevFrameCount = 0
        self.prevTableCount = 0

    def setUp(self):
        self.unoObjs = unoObjsForCurrentDoc()
        self.locale  = Locale(self.unoObjs)
        self.dlgSettings = None
        self.dlgGrabEx   = None

    def runDlgSettings(self, dispose):
        self.dlgSettings = DlgGramSettings(self.unoObjs, self.logger)
        self.dlgSettings.showDlg()
        if dispose:
            self.dlgSettings.dlgDispose()
            self.dlgSettings = None

    def runDlgGrabEx(self, dispose):
        self.dlgGrabEx   = DlgGrabExamples(
                           "grammar", self.unoObjs, self.logger)
        self.dlgGrabEx.showDlg()
        if dispose:
            self.dlgGrabEx.dlgDispose()
            self.dlgGrabEx = None

    def verifyFrame(self, whichFrame, textExpected):
        """
        After gram ex is created, verify text content of frame.
        whichFrame starts at 1 for the first frame created for an example.
        """
        exStartIndex = self.prevFrameCount - 1  # make it 0-based
        exIndex      = exStartIndex + whichFrame
        frames       = self.unoObjs.document.getTextFrames()
        frameWanted  = frames.getByIndex(exIndex)
        framecursor  = frameWanted.createTextCursor()
        framecursor.gotoEnd(True)
        frametext = framecursor.getString().strip()
        self.assertEqual(frametext, textExpected)

    def verifyTable(self, whichTable, col, row, textExpected):
        """
        After gram ex is created, verify text content of table.
        Will check the first row of the specified column.
        whichTable starts at 1 for the first table created for an example.
        """
        exStartIndex = self.prevTableCount - 1  # make it 0-based
        exIndex      = exStartIndex + whichTable
        tables       = self.unoObjs.document.getTextTables()
        tableWanted  = tables.getByIndex(exIndex)
        cellWanted   = tableWanted.getCellByPosition(col, row)
        cellCursor   = cellWanted.createTextCursor()
        cellCursor.gotoEnd(True)
        celltext = cellCursor.getString().strip()
        self.assertEqual(celltext, textExpected)

    def verifyTableHasCell(self, whichTable, whichCell, isExpected):
        """
        After gram ex is created, verify that a table does or does not have
        a specific column such as A1.
        whichTable starts at 1 for the first table created for an example.
        """
        exStartIndex = self.prevTableCount - 1  # make it 0-based
        exIndex      = exStartIndex + whichTable
        tables       = self.unoObjs.document.getTextTables()
        tableWanted  = tables.getByIndex(exIndex)
        cellNames    = tableWanted.getCellNames()
        if isExpected:
            self.assertTrue(whichCell in cellNames, whichCell)
        else:
            self.assertFalse(whichCell in cellNames, whichCell)

    def verifyFreeTrans(self, ftExpected, quoted):
        """
        After gram ex is created, verify free translation.
        """
        oVC = self.unoObjs.viewcursor
        oVC.goLeft(2, False)                # move up to end of FT line
        oVC.goLeft(len(ftExpected), False)  # prepare for gotoStartOfLine
        oVC.gotoStartOfLine(False)
        if quoted:
            oVC.goRight(1, False)               # pass over single quote
        oTextCurs = oVC.getText().createTextCursorByRange(oVC)
        oTextCurs.goRight(len(ftExpected), True)
        self.assertEqual(oTextCurs.getString(), ftExpected)
        oVC.gotoStartOfLine(False)
        spaceLen = 4
        oVC.goRight(len(ftExpected) + spaceLen, False)
        if quoted:
            oVC.goRight(2, False)
        oVC.gotoEndOfLine(False)
        oVC.goDown(2, False)

    #@unittest.skip("")
    def test1_filetypes(self):
        """
        Verify that toolbox and flextext files are read correctly.
        """
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        dataSets = [
            ("TbxIntJPDN60.xml", "JPDN60.01", 9,  u"ceʋuɾu",
             "The wall is white."),
            ("TbxIntJPDN60.xml", "JPDN61.08", 11, u"ceɾɾune",
             "Bring the chair."),
            ("Sena Int.flextext", "1.2",      13, u"Tonsene",
             u"[1.2 ft]"),
            ("Sena Int.flextext", "1.1",      20, u"Pisapha,",
             u"Estas coisas doem mas o que é necessário é ter coragem. Pois "
             u"nós todos vamos morrer.")]
        frames = self.unoObjs.document.getTextFrames()
        self.prevFrameCount = frames.getCount()
        for filename, refNum, numFrames, firstWord, ft in dataSets:
            def useDialog(selfNew):
                filepath = os.path.join(TESTDATA_FOLDER, filename)
                modifyFilePicker(filepath)
                if selfNew.listboxFiles.getItemCount() > 0:
                    selfNew.actionPerformed(MyActionEvent("FileRemove"))
                selfNew.actionPerformed(MyActionEvent("FileAdd"))
                selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
            DlgGramSettings.useDialog = useDialog
            def useDialog(selfNew):
                selfNew.txtRefnum.setText(refNum)
                selfNew.actionPerformed(MyActionEvent("InsertEx"))
            DlgGrabExamples.useDialog = useDialog
            self.runDlgSettings(True)
            self.runDlgGrabEx(True)

            frames = self.unoObjs.document.getTextFrames()
            newFrameCount = frames.getCount()
            self.assertEqual(newFrameCount - self.prevFrameCount, numFrames)
            self.verifyFrame(1, firstWord)
            self.verifyFreeTrans(ft, True)
            self.prevFrameCount = newFrameCount

    def grabExInSurroundings(self, action, blankLine, refNum,
                             outerTable, useFrames, numbering, ftQuoted):
        firstWord = u"oɾu"
        ft        = u" \u200e\u200eIn a village there was a headman."
        numFrames = 11
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        self.surroundNum += 1
        numStr = str(self.surroundNum)
        oVC.getText().insertString(oVC, "begin" + numStr, False)
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        if action == 'replacing':
            oVC.getText().insertString(oVC, "#" + refNum, False)
            if not blankLine:
                oVC.getText().insertString(oVC, " ", False)
        if blankLine:
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        oVC.getText().insertString(oVC, "end" + numStr, False)
        if blankLine:
            oVC.goUp(1, False)
        else:
            oVC.gotoStartOfLine(False)
        self.runDlgGrabEx(True)

        tables = self.unoObjs.document.getTextTables()
        newTableCount = tables.getCount()
        if useFrames:
            numTables = 1 if outerTable else 0
            self.assertEqual(newTableCount - self.prevTableCount, numTables)
            frames = self.unoObjs.document.getTextFrames()
            newFrameCount = frames.getCount()
            self.assertEqual(newFrameCount - self.prevFrameCount, numFrames)
            self.verifyFrame(1, firstWord)
            self.prevFrameCount = newFrameCount
        else:
            numTables = 2 if outerTable else 1
            self.assertEqual(newTableCount - self.prevTableCount, numTables)
            column = 0
            if not outerTable and not useFrames and numbering:
                column = 1
            row = 0
            self.verifyTable(numTables, column, row, firstWord)
        self.verifyFreeTrans(ft, ftQuoted)
        self.prevTableCount = newTableCount

        ## Verify that beginning and ending strings were not changed.

        exLines = 1  # number of lines used by example according to viewcursor
        if not outerTable:
            exLines += 1
            if not useFrames:
                exLines += 2
        oVC.goUp(exLines + 2, False)
        oVC.gotoStartOfLine(False)
        oVC.gotoEndOfLine(True)
        curs = oVC.getText().createTextCursorByRange(oVC)
        self.assertEqual(curs.getString(), "begin" + numStr)
        oVC.gotoStartOfLine(False)
        oVC.goDown(exLines + 2, False)
        if blankLine and action == 'inserting':
            oVC.goDown(1, False)
        oVC.gotoEndOfLine(True)
        curs = oVC.getText().createTextCursorByRange(oVC)
        self.assertEqual(curs.getString(), "end" + numStr)
        if blankLine and action == 'inserting':
            oVC.goUp(1, False)

    #@unittest.skip("")
    def test2_surroundings(self):
        """
        Test inserting and replacing examples, verifying that the
        examples are outputted where expected, checking the preceeding and
        following spacing, formatting and text.
        """
        blankWriterDoc(self.unoObjs)
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        # Only test certain combinations in order to save time.
        gramSettings = [
            # outerTable  frames      numbering   ftQuoted
            (True,        True,       True,       True),
            (True,        False,      False,      False),
            (False,       True,       True,       True),
            (False,       True,       False,      False),
            (False,       False,      True,       True),
            (False,       False,      True,       False)]
        changedAttrs = [
            ('ParaStyleName', "Caption"),
            ('CharStyleName', "Caption characters"),
            ('CharFontName',  "Arial Black"),
            ('CharHeight',    9)]
        frames = self.unoObjs.document.getTextFrames()
        self.prevFrameCount = frames.getCount()
        tables = self.unoObjs.document.getTextTables()
        self.prevTableCount = tables.getCount()
        for outerTable, useFrames, numbering, ftQuoted in gramSettings:
            def useDialog(selfNew):
                filepath = os.path.join(TESTDATA_FOLDER,
                                        "FWtextPigFox.xml")
                modifyFilePicker(filepath)
                if selfNew.listboxFiles.getItemCount() > 0:
                    selfNew.actionPerformed(MyActionEvent("FileRemove"))
                selfNew.actionPerformed(MyActionEvent("FileAdd"))
                selfNew.chkOuterTable.setState( 1 if outerTable else 0)
                selfNew.chkNumbering.setState(  1 if numbering  else 0)
                selfNew.chkFT_inQuotes.setState(1 if ftQuoted   else 0)
                if useFrames:
                    selfNew.optionFrames.setState(1)
                else:
                    selfNew.optionTables.setState(1)
                selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
            DlgGramSettings.useDialog = useDialog
            self.runDlgSettings(True)
            for action in 'inserting', 'replacing':
                refNum   = "1.1"
                def useDialog(selfNew):
                    if action == 'inserting':
                        selfNew.txtRefnum.setText(refNum)
                        selfNew.actionPerformed(MyActionEvent("InsertEx"))
                    elif action == 'replacing':
                        try:
                            selfNew.actionPerformed(MyActionEvent("ReplaceAll"))
                        except MsgSentException as exc:
                            self.assertTrue(exc.msg.startswith("Replaced"))
                        else:
                            self.fail("Expected error message.")
                DlgGrabExamples.useDialog = useDialog
                for blankLine in True, False:
                    for formatting in 'default', 'change':
                        if formatting == 'change':
                            for attrName, attrVal in changedAttrs:
                                oVC.setPropertyValue(attrName, attrVal)
                        self.grabExInSurroundings(
                            action, blankLine, refNum, 
                            outerTable, useFrames, numbering, ftQuoted)
                        if formatting == 'default':
                            self.assertEqual(
                                oVC.getPropertyValue('ParaStyleName'),
                                "Standard")
                            self.assertEqual(
                                oVC.getPropertyValue('CharStyleName'), "")
                            self.assertEqual(
                                oVC.getPropertyValue('CharFontName'),
                                "Times New Roman")
                        else:
                            for attrName, attrVal in changedAttrs:
                                self.assertEqual(
                                    oVC.getPropertyValue(attrName), attrVal)
                        if blankLine:
                            oVC.goDown(1, False)
                        oVC.gotoEndOfLine(False)
                        oVC.getText().insertControlCharacter(
                            oVC, PARAGRAPH_BREAK, False)
                        oVC.setPropertyValue('ParaStyleName', "Standard")
                        oVC.setPropertyToDefault('CharStyleName')
                        oVC.setPropertyToDefault('CharFontName')

    def test3_checkboxes(self):
        """
        Test most checkboxes in Grammar Settings.
        This may ignore some controls that have already been sufficiently
        tested in test2_surroundings() or other places.
        """
        blankWriterDoc(self.unoObjs)
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        frames = self.unoObjs.document.getTextFrames()
        self.prevFrameCount = frames.getCount()
        tables = self.unoObjs.document.getTextTables()
        self.prevTableCount = tables.getCount()
        for setting in ['orth', 'text', 'mbOrth', 'mb', 'ps', 'sepCols',
                        'psAbove', 'numbering'
           ]:
            for setVal in True, False:
                def useDialog(selfNew):
                    filepath = os.path.join(TESTDATA_FOLDER,
                                            "TbxIntHunt06.xml")
                    modifyFilePicker(filepath)
                    if selfNew.listboxFiles.getItemCount() > 0:
                        selfNew.actionPerformed(MyActionEvent("FileRemove"))
                    selfNew.actionPerformed(MyActionEvent("FileAdd"))
                    tagVars = dict(GrammarTags.tagVars)
                    selfNew.userVars.set(tagVars['orth'],  'or')
                    selfNew.userVars.set(tagVars['orthm'], 'mbor')
                    selfNew.chkOrthoTextLine.setState( 0)
                    selfNew.chkTextLine.setState(      1)
                    selfNew.chkOrthoMorphLine.setState(0)
                    selfNew.chkMorphLine.setState(     1)
                    selfNew.chkPOS_Line.setState(      0)
                    selfNew.chkMorphsSeparate.setState(1)
                    selfNew.chkPOS_aboveGloss.setState(0)
                    selfNew.chkNumbering.setState(     1)
                    if setting == 'orth':
                        selfNew.chkOrthoTextLine.setState( 1 if setVal else 0)
                    elif setting == 'text':
                        selfNew.chkTextLine.setState(      1 if setVal else 0)
                    elif setting == 'mbOrth':
                        selfNew.chkOrthoMorphLine.setState(1 if setVal else 0)
                    elif setting == 'mb':
                        selfNew.chkMorphLine.setState(     1 if setVal else 0)
                    elif setting == 'ps':
                        selfNew.chkPOS_Line.setState(      1 if setVal else 0)
                    elif setting == 'sepCols':
                        selfNew.chkMorphsSeparate.setState(1 if setVal else 0)
                    elif setting == 'psAbove':
                        selfNew.chkPOS_Line.setState(1)
                        selfNew.chkPOS_aboveGloss.setState(1 if setVal else 0)
                    elif setting == 'numbering':
                        selfNew.chkNumbering.setState(     1 if setVal else 0)
                    selfNew.optionTables.setState(1)
                    selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
                DlgGramSettings.useDialog = useDialog
                self.runDlgSettings(True)
                refNum   = "Hunt01"
                def useDialog(selfNew):
                    selfNew.txtRefnum.setText(refNum)
                    selfNew.actionPerformed(MyActionEvent("InsertEx"))
                DlgGrabExamples.useDialog = useDialog
                self.runDlgGrabEx(True)

                tables = self.unoObjs.document.getTextTables()
                newTableCount = tables.getCount()
                numTables = 2
                tablesAdded = newTableCount - self.prevTableCount
                # varying font sizes can cause wrapping
                self.assertTrue(tablesAdded >= numTables)
                self.assertTrue(tablesAdded <= numTables + 1)
                ipaOru = u"oɾu"  # used in text and mb lines
                if setting == 'orth':
                    self.verifyTableHasCell(numTables, "A4", setVal)
                    if setVal:
                        tamOru = u"\u0b92\u0bb0\u0bc1"    # Tamil /oru/
                        self.verifyTable(numTables, 0, 0, tamOru) # orth
                        self.verifyTable(numTables, 0, 1, ipaOru) # text
                    else:
                        self.verifyTableHasCell(numTables, "A4", False)
                        self.verifyTable(numTables, 0, 0, ipaOru) # text
                elif setting == 'text':
                    self.verifyTableHasCell(numTables, "A3", setVal)
                    if setVal:
                        self.verifyTable(numTables, 0, 0, ipaOru) # text
                        self.verifyTable(numTables, 0, 1, ipaOru) # mb
                    else:
                        self.verifyTable(numTables, 0, 0, ipaOru) # mb
                        self.verifyTable(numTables, 0, 1, "a")    # gloss
                elif setting == 'mbOrth':
                    self.verifyTableHasCell(numTables, "A4", setVal)
                    if setVal:
                        tamTi = u"-\u0ba4\u0bbf"  # Tamil /-ti/
                        self.verifyTable(numTables, 2, 1, tamTi)  # mb orth
                    else:
                        self.verifyTable(numTables, 2, 1, u"-d̪i") # mb
                elif setting == 'mb':
                    self.verifyTableHasCell(numTables, "A3", setVal)
                    if setVal:
                        self.verifyTable(numTables, 0, 1, ipaOru) # mb
                    else:
                        self.verifyTable(numTables, 0, 1, "a")    # gloss
                elif setting == 'ps':
                    self.verifyTableHasCell(numTables, "A4", setVal)
                    if setVal:
                        self.verifyTable(numTables, 0, 3, "det") # ps
                elif setting == 'sepCols':
                    self.verifyTableHasCell(numTables, "F1", True)
                    self.verifyTableHasCell(numTables, "G1", False)
                    self.verifyTableHasCell(numTables, "F2", True)
                    self.verifyTableHasCell(numTables, "I2", setVal)
                    if setVal:
                        self.verifyTable(numTables, 1, 1, u"uːɾu")    # mb
                    else:
                        self.verifyTable(numTables, 1, 1, u"uːɾu-d̪i") # mb
                elif setting == 'psAbove':
                    self.verifyTableHasCell(numTables, "A4", True)
                    if setVal:
                        self.verifyTable(numTables, 0, 2, "det") # ps
                        self.verifyTable(numTables, 0, 3, "a")   # gloss
                    else:
                        self.verifyTable(numTables, 0, 2, "a")   # gloss
                        self.verifyTable(numTables, 0, 3, "det") # ps
                elif setting == 'numbering':
                    self.verifyTableHasCell(1, "A1", True)
                    if setVal:
                        tableWanted = tables.getByIndex(self.prevTableCount)
                        cellWanted  = tableWanted.getCellByPosition(0, 0)
                        cellCursor  = cellWanted.createTextCursor()
                        cellCursor.gotoEnd(True)
                        celltext = cellCursor.getString().strip()
                        self.assertTrue(re.search("^\(\d+\)$", celltext),
                                        celltext)
                    else:
                        self.verifyTable(1, 0, 0, "()") # number
                self.prevTableCount = newTableCount

    #@unittest.skip("")
    def test4_prefixAndColWidth(self):
        """
        Test prefix and column width in Grammar Settings.
        """
        blankWriterDoc(self.unoObjs)
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        dataSets = [
            ("A1.1", 20,  u"Pisapha,",
             u"Estas coisas doem mas o que é necessário é ter coragem. Pois "
             u"nós todos vamos morrer."),
            ("B1.1", 11,  u"oɾu",
             u" \u200e\u200eIn a village there was a headman.")]
        def useDialog(selfNew):
            filepath = os.path.join(TESTDATA_FOLDER,
                                    "Sena Int.flextext")
            modifyFilePicker(filepath)
            selfNew.actionPerformed(MyActionEvent("FileAdd"))
            selfNew.txtPrefix.setText("A")
            selfNew.actionPerformed(MyActionEvent("FileUpdate"))
            filepath = os.path.join(TESTDATA_FOLDER,
                                    "FWtextPigFox.xml")
            modifyFilePicker(filepath)
            selfNew.actionPerformed(MyActionEvent("FileAdd"))
            selfNew.txtPrefix.setText("B")
            selfNew.actionPerformed(MyActionEvent("FileUpdate"))
            selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
        DlgGramSettings.useDialog = useDialog
        self.runDlgSettings(True)
        frames = self.unoObjs.document.getTextFrames()
        self.prevFrameCount = frames.getCount()
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        for refNum, numFrames, firstWord, ft in dataSets:
            def useDialog(selfNew):
                selfNew.txtRefnum.setText(refNum)
                selfNew.actionPerformed(MyActionEvent("InsertEx"))
            DlgGrabExamples.useDialog = useDialog
            self.runDlgGrabEx(True)

            frames = self.unoObjs.document.getTextFrames()
            newFrameCount = frames.getCount()
            self.assertEqual(newFrameCount - self.prevFrameCount, numFrames)
            self.verifyFrame(1, firstWord)
            self.verifyFreeTrans(ft, True)
            self.prevFrameCount = newFrameCount

        oVC.goUp(2, False)   # move into second table
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:SelectTable", "", 0, ())
        self.unoObjs.dispatcher.executeDispatch(
            self.unoObjs.frame, ".uno:DeleteTable", "", 0, ())
        for resize in False, True:
            if resize:
                def useDialog(selfNew):
                    selfNew.txtNumberingColWidth.setText("30")
                    selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
                DlgGramSettings.useDialog = useDialog
                self.runDlgSettings(True)
            oVC.goLeft(2, False)  # move into first table after ref num
            ft = dataSets[1][3]
            oVC.goLeft(len(ft), False)
            oVC.gotoStartOfLine(False)
            tableName = "Table1"
            oVC.goUp(2, False)
            self.assertTrue(oVC.TextTable is not None)
            self.assertEqual(oVC.TextTable.getName(), tableName)
            oVC.goUp(1, False)
            if resize:
                self.assertTrue(oVC.TextTable is not None)
                self.assertEqual(oVC.TextTable.getName(), tableName)
            else:
                self.assertTrue(oVC.TextTable is None)
            oVC.goDown(3, False)
 
    #@unittest.skip("")
    def test5_updating(self):
        """
        Test updating examples. Verify that:
        - the example is actually updated
        - the correct example number is updated
        - the old example isn't still there
        - surrounding spacing, formatting and text doesn't get messed up
        """
        blankWriterDoc(self.unoObjs)
        oVC = self.unoObjs.viewcursor   # shorthand variable name
        examples = [
            ("AJPDN60.01", 9,  u"ceʋuɾu", 'Default', ''),
            ("AJPDN61.08", 11, u"ceɾɾune",'ParaStyleName', "Caption"),
            ("B1.1",       11, u"oɾu",    'CharStyleName',
                                                         "Caption characters"),
            ("B1.2",       21, u"aʋant̪u", 'CharFontName', "Arial Black")]

        ## Insert original examples

        def useDialog(selfNew):
            if selfNew.fileItems.getCount() == 0:
                filepath = os.path.join(TESTDATA_FOLDER,
                                        "TbxIntJPDN60.xml")
                modifyFilePicker(filepath)
                selfNew.actionPerformed(MyActionEvent("FileAdd"))
                selfNew.txtPrefix.setText("A")
                selfNew.actionPerformed(MyActionEvent("FileUpdate"))
                filepath = os.path.join(TESTDATA_FOLDER,
                                        "FWtextPigFox.xml")
                modifyFilePicker(filepath)
                selfNew.actionPerformed(MyActionEvent("FileAdd"))
                selfNew.txtPrefix.setText("B")
                selfNew.actionPerformed(MyActionEvent("FileUpdate"))
            selfNew.optionFrames.setState(1)
            selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
        DlgGramSettings.useDialog = useDialog
        self.surroundNum = 0
        frames = self.unoObjs.document.getTextFrames()
        self.prevFrameCount = frames.getCount()
        for refNum, numFrames, firstWord, attrName, attrVal in examples:
            def useDialog(selfNew):
                selfNew.txtRefnum.setText(refNum)
                selfNew.actionPerformed(MyActionEvent("InsertEx"))
            DlgGrabExamples.useDialog = useDialog
            self.runDlgSettings(True)

            self.surroundNum += 1
            numStr = str(self.surroundNum)
            if attrName != 'Default':
                oVC.setPropertyValue(attrName, attrVal)
            oVC.getText().insertString(oVC, "begin" + numStr, False)
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
            oVC.getText().insertString(oVC, "end" + numStr, False)
            oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
            oVC.goUp(1, False)
            oVC.gotoStartOfLine(False)
            self.runDlgGrabEx(True)
            frames = self.unoObjs.document.getTextFrames()
            newFrameCount = frames.getCount()
            self.assertEqual(newFrameCount - self.prevFrameCount, numFrames)
            self.verifyFrame(1, firstWord)
            self.prevFrameCount = newFrameCount
            oVC.goDown(1, False)
            oVC.setPropertyValue("ParaStyleName", "Standard")
            oVC.setPropertyToDefault("CharStyleName")
            oVC.setPropertyToDefault("CharFontName")
        oVC.getText().insertControlCharacter(oVC, PARAGRAPH_BREAK, False)
        tables = self.unoObjs.document.getTextTables()
        self.assertEqual(tables.getCount(), len(examples))

        ## Update examples

        def useDialog(selfNew):
            selfNew.optionTables.setState(1)
            selfNew.actionPerformed(MyActionEvent("UpdateSettings"))
        DlgGramSettings.useDialog = useDialog
        def useDialog(selfNew):
            selfNew.optSearchExisting.setState(1)
            selfNew.enableDisable()
            try:
                modifyMsgboxOkCancel(True) # as if user clicked OK
                selfNew.actionPerformed(MyActionEvent("ReplaceAll"))
            except MsgSentException as exc:
                self.assertTrue(exc.msg.startswith("Updated"))
            else:
                self.fail("Expected error message.")
        DlgGrabExamples.useDialog = useDialog
        self.runDlgSettings(True)
        self.runDlgGrabEx(False)

        # check comparison doc

        compDoc = self.dlgGrabEx.app.exUpdater.compDoc
        self.assertTrue(compDoc is not None)
        self.assertTrue(compDoc.document is not None)
        numCompDocTables = compDoc.document.getTextTables().getCount()
        multiLineExs = 1     # number of examples that have another line
        self.assertEqual(numCompDocTables, 3 * len(examples) + multiLineExs)
        compDoc.document.close(True)
        self.dlgGrabEx.dlgDispose()
        self.dlgGrabEx = None
        #self.unoObjs = unoObjsForCurrentDoc()
        #oVC = self.unoObjs.viewcursor   # shorthand variable name

        ## Check examples

        tables = self.unoObjs.document.getTextTables()
        self.assertEqual(tables.getCount(), 2 * len(examples) + multiLineExs)

        oVC.gotoStart(False)
        self.surroundNum = 0
        tableNum         = 1
        for refNum, unused, firstWord, attrName, attrVal in examples:
            self.verifyTable(tableNum + 1, 0, 0, firstWord)
            self.surroundNum += 1
            numStr = str(self.surroundNum)
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            curs = oVC.getText().createTextCursorByRange(oVC)
            self.assertEqual(curs.getString(), "begin" + numStr)
            oVC.gotoStartOfLine(False)
            oVC.goDown(3, False) # to "end" line
            oVC.gotoStartOfLine(False)
            oVC.gotoEndOfLine(True)
            curs = oVC.getText().createTextCursorByRange(oVC)
            self.assertEqual(curs.getString(), "end" + numStr)
            oVC.collapseToEnd()
            oVC.gotoStartOfLine(False)
            if attrName == 'Default':
                self.assertEqual(
                    oVC.getPropertyValue('ParaStyleName'), "Standard")
                self.assertEqual(
                    oVC.getPropertyValue('CharStyleName'), "")
                self.assertEqual(
                    oVC.getPropertyValue('CharFontName'), "Times New Roman")
            else:
                self.assertEqual(oVC.getPropertyValue(attrName), attrVal)
            oVC.goDown(1, False) # to next "begin" line
            tableNum += 2
        self.tearDownClass()

    @classmethod
    def tearDownClass(cls):
        unoObjs = unoObjsForCurrentDoc()
        blankWriterDoc(unoObjs)

#-------------------------------------------------------------------------------
# End of Grammar_test.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of runTestSuite.py
#-------------------------------------------------------------------------------




def runTests(outputToFile=False):

    ## Make sure a writer document is open

    ctx     = getContext()
    unoObjs = UnoObjs(ctx, loadDocObjs=False)
    if len(unoObjs.getOpenDocs()) == 0:
        unoObjs.desktop.loadComponentFromURL(
            "private:factory/swriter", "_blank", 0, ())

    ## Load and run the test suite

    masterSuite = unittest.TestSuite()
    for testClass in [
            ExUpdaterTestCase,
            TablesTestCase,
            SearchTestCase,
            TextChangesTestCase,
            UserVarsTestCase,

            XML_Readers_PhonTestCase,
            XML_Readers_GramTestCase,

            SpellingChecksTestCase,

            DlgGramSettingsTestCase,
            DlgDataConvTestCase,

            PhonologyTestCase,
            GrammarTestCase,
       ]:
        suite = unittest.TestLoader().loadTestsFromTestCase(testClass)
        masterSuite.addTest(suite)

    if outputToFile:
        outfilepath = os.path.join(BASE_FOLDER, "testResults.txt")
        outfile = open(outfilepath, 'w')
        outfile.write("Calling TextTestRunner...\n")
        outfile.flush()
        unittest.TextTestRunner(stream=outfile, verbosity=2).run(masterSuite)
        outfile.close()
    else:
        unittest.TextTestRunner(verbosity=2).run(masterSuite)

    unoObjs = unoObjsForCurrentDoc()
    oVC = unoObjs.viewcursor
    oVC.gotoEnd(False)
    oVC.getText().insertString(oVC, "Testing finished.\n", False)

if __name__ == '__main__':
    getContext()   # get from socket
    runTests()

def runTests_myMacros():
    setContext(uno.getComponentContext())
    runTests(outputToFile=True)

# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of runTestSuite.py
#-------------------------------------------------------------------------------


# Exported Scripts:
g_exportedScripts = runTests_myMacros,
