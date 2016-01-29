#!/usr/bin/python
# -*- coding: Latin-1 -*-

## Import standard modules
import uno
from  com.sun.star.awt import XActionListener
from com.sun.star.uno import RuntimeException
import logging
import os
import platform
import unohelper

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

# Change this value depending on operating system and location
if platform.system() == "Windows" :
    BASE_FOLDER = r"D:\Jim\computing\Office\OOo Linguistic Tools" + "\\"
else:
    BASE_FOLDER = r"/media/winD/Jim/computing/Office/OOo Linguistic Tools/"

SOURCE_FOLDER    = BASE_FOLDER + "LinguisticTools" + os.sep # OOoLT zipped from
LOGGING_FILEPATH = BASE_FOLDER + "debug.txt"

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
    def __init__(self, ctx, doctype='writer', loadFromContext=True):
        self.ctx      = ctx
        self.document = None
        if loadFromContext:
            # Calling uno.getComponentContext() here causes a bad crash.
            # Apparently in components, it is necessary to use the provided
            # context.
            self.smgr       = ctx.ServiceManager
            self.desktop    = self.smgr.createInstanceWithContext(
                              "com.sun.star.frame.Desktop", ctx)
            self.dispatcher = self.smgr.createInstanceWithContext (
                              "com.sun.star.frame.DispatchHelper", ctx)
            self.getDocObjs(None, doctype)

    def serviceObjs(self):
        """
        Factory method to make an UnoObjs containing only context and service
        objects, not document-specific objects.
        """
        newObjs = UnoObjs(self.ctx, loadFromContext=False)
            # this is probably the only case where loadFromContext=False
        newObjs.smgr       = self.smgr
        newObjs.desktop    = self.desktop
        newObjs.dispatcher = self.dispatcher
        return newObjs

    def getDocObjs(self, document=None, doctype='writer'):
        if document:
            self.document = document
        else:
            self.document = self.desktop.getCurrentComponent()
        self.controller = self.document.getCurrentController()
        self.frame      = self.controller.getFrame()
        self.window     = self.frame.getContainerWindow()
        if doctype == 'writer':
            try:
                self.text = self.document.getText()
            except AttributeError:
                raise AttributeError, 'Could not get Writer document.'
            self.viewcursor = self.controller.getViewCursor()
        elif doctype == 'calc':
            try:
                self.sheets = self.document.getSheets()
                self.sheet  = self.sheets.getByIndex(0)
            except AttributeError:
                raise AttributeError, 'Could not get Calc spreadsheet.'
        else:
            raise AttributeError, 'Unexpected doc type ' + doctype

def getUnoObjsFromSocket():
    """Use when connecting from outside OOo. For testing."""
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext)
    ctx = resolver.resolve(
        "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    return UnoObjs(ctx)

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
    try:
        mspf = unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.script.provider.MasterScriptProviderFactory",
            unoObjs.ctx)
        scriptPro = mspf.createScriptProvider("")
        xScript = scriptPro.getScript(
            "vnd.sun.star.script:XrayTool._Main.Xray?" +
            "language=Basic&location=application")
        xScript.invoke((myObject,), (), ())
        return
    except:
        raise RuntimeException(
            "\nBasic library Xray is not installed", unoObjs.ctx)

class ConfigOptions:
    """
    A flexible structure to hold configuration options,
    typically settings that the user has selected or entered.
    Attributes can be created and used as needed.
    """
    pass

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
# Start of Locale.py
#-------------------------------------------------------------------------------


class Locale:
    def __init__(self, unoObjs):
        """Initialize and get current OOo locale."""
        self.logger = logging.getLogger("lingt.Locale")

        ## Get locale setting

        configProvider = unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", unoObjs.ctx)
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

        for en in self.translations.keys():
            self.translations[en.lower()] = self.translations[en]

    def getText(self, message_en):
        """Return L10N value.  If no translation is found for the current
        locale, returns the English message.
        """
        if message_en is None:
            return ""
        if self.locale == "en":
            return message_en
        key = message_en.lower()
        if self.translations.has_key(key):
            phrase_translations = self.translations.get(key)
            message_other = phrase_translations.get(self.locale)
            if message_other is not None and message_other != "":
                return message_other
        return message_en

    translations = {

        ## Dynamic labels in dialogs

        u"Back to Settings" : {
            'es' :
            u"Volver a la configuración",
            'fr' :
            u"Atteindre la configuration",
        },
        u"Get Phonology Examples" : {
            'es' :
            u"Obtener ejemplos de fonología",
            'fr' :
            u"Obtenir des exemples de phonologie",
        },
        u"Get Interlinear Grammar Examples" : {
            'es' :
            u"Obtener ejemplos de gramática",
            'fr' :
            u"Obtenir des exemples de grammaire",
        },
        u"Go to Practice" : {
            'es' :
            u"Ir a la práctica",
            'fr' :
            u"Atteindre exercices",
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
            "Practica de script",
            'fr' :
            "Exercices d'écriture",
        },
        u"Script Practice - Settings" : {
            'es' :
            "Practica de script - Configuración",
            'fr' :
            "Exercices d'écriture - Configuration",
        },
        u"Update Example" : {
            'es' :
            u"Actualizar el ejemplo",
            'fr' :
            u"Mettre l'exemple à jour",
        },
        u"Update All" : {
            'es' :
            u"Actualizar todos",
            'fr' :
            u"Tout mettre à jour",
        },

        ## Localized text values

        u"(none)" : {
            'es' :
            u"(ninguno)",
            'fr' :
            u"(aucun)",
        },
        u"Default" : {      # the built-in default style name
            'es' :
            u"Predeterminado",
            'fr' :
            u"Standard",
        },
        u"(cannot make word)" : {
            'es' :
            u"(no puede hacer la palabra)",
            'fr' :
            u"(impossible de créer mot)",
        },
        u"(no words found)" : {
            'es' :
            u"(no hay palabras encontradas)",
            'fr' :
            u"(aucun mot trouvé)",
        },

        ## Status messages for ProgressBar

        u"Converting..." : {
            'es' :
            u"Convirtiendo...",
            'fr' :
            u"Conversion en cours...",
        },
        u"Searching for occurrences..." : {
            'es' :
            u"Buscando ocurrencias...",
            'fr' :
            u"Recherche des occurrences...",
        },
        u"Loading data..." : {
            'es' :
            u"Cargando datos...",
            'fr' :
            u"Chargement des données...",
        },

        ## Error messages

        u"Add '%s' as a new abbreviation?" : {
            'es' :
            u"Agregar '%s' como una abreviatura de nuevo?",
            'fr' :
            u"Ajouter '%s' comme nouvelle abréviation ?",
        },
        u"Cannot be in a header or footer." : {
            'es' :
            u"No puede ser en un encabezado o un pie de página.",
            'fr' :
            u"Interdit dans un en-tête ou pied de page.",
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
            u"No se puede insertar texto aquí.",
            'fr' :
            u"Impossible d'insérer texte ici.",
        },
        u"Character style '%s' is missing" : {
            'es' :
            u"No se encuentra el estilo de carácter '%s'",
            'fr' :
            u"Style de caractère '%s' introuvable",
        },
        u"Column width is not a number." : {
            'es' :
            u"El ancho de columna no es un número.",
            'fr' :
            u"La largeur de colonne n'est pas un nombre.",
        },
        u"Converting..." : {
            'es' :
            u"Conversión en proceso...",
            'fr' :
            u"Conversion en cours...",
        },
        u"Could not find ref number %s" : {
            'es' :
            u"No se encuentra el número de referencia %s",
            'fr' :
            u"Numéro de référence %s introuvable.",
        },
        u"Could not find ref number %s\n\nSuggestions\n%s" : {
            'es' :
            u"No se encuentra el número de referencia %s\n\nSugerencias\n%s",
            'fr' :
            u"Numéro de référence %s introuvable. Suggestion(s) : %s",
        },
        u"Did not find any data in file %s" : {
            'es' :
            u"No ha encontrado ningún dato en el archivo %s",
            'fr' :
            u"Aucune donnée n'a été trouvée dans le fichier %s",
        },
        u"Did not find scope of change." : {
            'es' :
            u"No ha encontrado el ámbito del cambio.",
            'fr' :
            u"L'étendue de changement n'a pas été trouvée.",
        },
        u"Error parsing %s user variable. Please go to Insert -> Fields and " +
        u"fix the problem." : {
            'es' :
            u"Error al analizar %s variable de usuario. Por favor, vaya a " +
            u"Insertar -> Campos y solucionar el problema.",
            'fr' :
            u"Erreur en analysant la variable utilisateur %s. Veuillez " +
            u"atteindre Insertion -> Champs pour résoudre le problème.",
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
        u"Error: Could not create dialog." : {
            'es' :
            u"Error: No se pudo crear el diálogo.",
            'fr' :
            u"Erreur : Impossible de créer dialogue.",
        },
        u"Error: Could not show dialog window." : {
            'es' :
            u"Error: No se pudo mostrar el cuadro de diálogo.",
            'fr' :
            u"Erreur : Impossible d'afficher dialogue.",
        },
        u"File does not seem to be from Toolbox or FieldWorks: %s" : {
            'es' :
            u"El archivo no parece ser del Toolbox o Fieldworks: %s",
            'fr' :
            u"Il semble que ce fichier n'a pas été créé par Toolbox ou " +
            u"FieldWorks: %s",
        },
        u"File is already in the list." : {
            'es' :
            u"El archivo ya está en la lista.",
            'fr' :
            u"Le fichier est déjà dans la liste.",
        },
        u"Found %d paragraphs and made %d change(s)." : {
            'es' :
            u"Ha encontrado %d párrafos y hizo %d cambio(s).",
            'fr' :
            u"%d paragraphes trouvés et %d changements faits.",
        },
        u"Found a ref number, but it must be in an outer table in order to " +
        u"be updated." : {
            'es' :
            u"Ha encontrado un número de referencia, pero debe estar en una " +
            u"tabla de exterior para ser actualizados.",
            'fr' :
            u"N° de réf. trouvé, mais pour l'actualier il doit être dans un " +
            u"cadre exterieur",
        },
        u"Frame style '%s' is missing" : {
            'es' :
            u"No se encuentra el estilo del marco '%s'",
            'fr' :
            u"Style de cadre '%s' introuvable",
        },
        u"If you want to use LIFT data, then first specify a LIFT file " +
        u"exported from FieldWorks." : {
            'es' :
            u"Si desea utilizar los datos LIFT, en primer lugar especificar " +
            u"un archivo LIFT exportados de Fieldworks.",
            'fr' :
            u"Pour utiliser des données LIFT il faut spécifier un fichier " +
            u"LIFT exporté de FieldWorks.",
        },
        u"Made %d changes." : {
            'es' :
            u"%d cambios realizados",
            'fr' :
            u"%d changements faits.",
        },
        u"No changes, but modified style of %d paragraph(s)." : {
            'es' :
            u"No hubo cambios, pero el estilo de %d párrafo(s) se ha " +
            u"modificado.",
            'fr' :
            u"Pas de changements, mais le style de %d paragraphes a été " +
            u"changé.",
        },
        u"No changes." : {
            'es' :
            u"No hubo cambios.",
            'fr' :
            u"Pas de changements.",
        },
        u"No more existing examples found." : {
            'es' :
            u"No se ha encontrado más ejemplos existentes",
            'fr' :
            u"Il n'y a plus d'exemples trouvés.",
        },
        u"No more possible abbreviations found." : {
            'es' :
            u"No se ha encontrado más abreviaturas posibles",
            'fr' :
            u"On ne trouve plus des abréviations possibles.",
        },
        u"No more reference numbers found." : {
            'es' :
            u"No se ha encontrado más números de referencia",
            'fr' :
            u"On ne trouve plus des numéros de référence.",
        },
        u"No text is selected." : {
            'es' :
            u"No hay texto seleccionado.",
            'fr' :
            u"Aucun texte sélectionné. ",
        },
        u"Paragraph style '%s' is missing" : {
            'es' :
            u"No se encuentra el estilo de párrafo '%s'",
            'fr' :
            u"Style de paragraphe '%s' introuvable",
        },
        u"Please do not select individual table cells." : {
            'es' :
            u"Por favor, no seleccione las celdas individuales de la tabla.",
            'fr' :
            u"Veuillez ne pas choisir des cellules individuelles.",
        },
        u"Please enter a number for max length." : {
            'es' :
            u"Por favor, introduzca un número para la longitud máxima.",
            'fr' :
            u"Veuillez entrer la longueur maximum.",
        },
        u"Please enter a ref number." : {
            'es' :
            u"Por favor, introduzca un número de referencia.",
            'fr' :
            u"Veuillez entrer un numéro de référence.",
        },
        u"Please enter a value for column width." : {
            'es' :
            u"Por favor, introduzca un valor para el ancho de la columna.",
            'fr' :
            u"Veuillez entrer la largeur de colonne.",
        },
        u"Please go to Grammar Settings and specify a file." : {
            'es' :
            u"Por favor, vaya a la Configuración de gramática y especifique " +
            u"un archivo.",
            'fr' :
            u"Veuillez choisir un fichier dans Configuration de grammaire.",
        },
        u"Please go to Phonology Settings and specify a file." : {
            'es' :
            u"Por favor, vaya a la Configuración de fonología y especifique " +
            u"un archivo.",
            'fr' :
            u"Veuillez spécifier un fichier dans Configuration de phonologie.",
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
        u"Please select a scope character style." : {
            'es' :
            u"Por favor, seleccione un estilo de carácter ámbito.",
            'fr' :
            u"Veuillez choisir un style de caractère pour l'étendue.",
        },
        u"Please select a scope font." : {
            'es' :
            u"Por favor, seleccione una fuente ámbito.",
            'fr' :
            u"Veuillez choisir une police pour l'étendue.",
        },
        u"Please select a scope paragraph style." : {
            'es' :
            u"Por favor, seleccione un estilo de párrafo ámbito.",
            'fr' :
            u"Veuillez choisir un style de paragraphe pour l'étendue.",
        },
        u"Please select a script." : {
            'es' :
            u"Por favor, seleccione un script.",
            'fr' :
            u"Veuillez choisir un écriture.",
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
            u"Veuillez choisir un élément dans la liste.",
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
            u"Veuillez spécifier les balises (SFMs).",
        },
        u"Please specify a scope." : {
            'es' :
            u"Por favor, especifique un ámbito.",
            'fr' :
            u"Veuillez spécifier l'étendue.",
        },
        u"Searching for occurrences..." : {
            'es' :
            u"Buscando ocurrencias...",
            'fr' :
            u"Recherche des occurrences...",
        },
        u"System error: Unable to get UNO object." : {
            'es' :
            u"Error del sistema: No se puede obtener objeto UNO.",
            'fr' :
            u"Erreur de système : Impossible d'accéder à l'objet UNO.",
        },
        u"The cursor cannot be in a header or footer." : {
            'es' :
            u"El cursor no puede estar en un encabezado o en un pie de página.",
            'fr' :
            u"Le curseur ne peut pas se trouver dans un en-tête ou dans un " +
            u"pied de page.",
        },
        u"The cursor cannot be inside a table or frame." : {
            'es' :
            u"El cursor no puede estar dentro de una tabla o un marco.",
            'fr' :
            u"Le curseur ne peut pas se trouver dans un tableau ou dans un " +
            u"cadre.",
        },
        u"There do not seem to be any examples to insert." : {
            'es' :
            u"No parece haber ningún ejemplo para insertar.",
            'fr' :
            u"Il semble qu'il n'existe pas d'exemples à insérer.",
        },
        u"This will change the case of the entire list from '%s' to '%s.' " +
        u"Continue?" : {
            'es' :
            u"Esto cambiará el caso de la lista completa de '%s' a '%s'. " +
            u"¿Desea continuar?",
            'fr' :
            u"Ceci changera la casse de toute la liste de '%s' à '%s'. " +
            u"Continuer ?",
        },
        u"Unexpected file type %s" : {
            'es' :
            u"Tipo de archivo inesperado %s",
            'fr' :
            u"Type de fichier %s inattendu",
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
        u"Update all examples now?  It is recommended to save a copy of your " +
        u"document first." : {
            'es' :
            u"¿Actualizar todos los ejemplos ahora?  Se recomienda que " +
            u"primero guarde una copia de su documento.",
            'fr' :
            u"Actualiser tous les exemples maintenant ? Il est conseillé " +
            u"d'enregistrer le document d'abord.",
        },
        u"Updated '%s' %d times in a row. Keep going?" : {
            'es' :
            u"Actualizado '%s' %d veces seguidas. ¿Seguir adelante?",
            'fr' :
            u"'%s' a été actualisé %d fois de suite. Continuer ?",
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
            u"La largeur de colonne doit être supérieure à zéro.",
        },
    }
#-------------------------------------------------------------------------------
# End of Locale.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of MessageBox.py
#-------------------------------------------------------------------------------



class MessageBox:
    """Message box for python, like OOo Basic MsgBox.
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

    def __init__(self, unoObjs, logger, doc=None):
        """Requires the frame of the higher level window.
        Note: Don't call logging methods from this __init__ routine.
        """
        try:
            if doc:
                self.parent  = doc.frame.getContainerWindow() 
            else:
                self.parent  = unoObjs.frame.getContainerWindow() 
            self.toolkit = self.parent.getToolkit()
        except:
            raise AttributeError, 'Did not get a valid parent window' 
        self.logger = logger
        self.locale = Locale(unoObjs)

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

    def __init__(self, unoObjs, logger):
        self.unoObjs = unoObjs
        self.locale  = Locale(unoObjs)
        self.logger  = logger

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
    unoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = FourButtonDialog(unoObjs, logger)
    dlg.display("Testing")

# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of MessageBox.py
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Start of DlgSimple.py
#-------------------------------------------------------------------------------



def ShowDlg(ctx=uno.getComponentContext()):
    """Main method to show a dialog window.
    You can call this method directly by Tools -> Macros -> Run Macro.
    """
    logger = logging.getLogger("lingt.UI.DlgApplyConv")
    logger.debug("----ShowDlg()----------------------------------------------")
    unoObjs = UnoObjs(ctx)
    logger.debug("got UNO context")

    dlg = DlgSimple(unoObjs, logger)
    dlg.showDlg()

class DlgSimple(XActionListener, unohelper.Base):
    """The dialog implementation."""

    def __init__(self, unoObjs, logger):
        self.unoObjs        = unoObjs
        self.logger         = logger
        self.msgbox         = MessageBox(unoObjs, self.logger)

    def showDlg(self):
        self.logger.debug("DlgSimple.showDlg BEGIN")
        dlgprov = self.unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.awt.DialogProvider", self.unoObjs.ctx )
        dlg = None
        try:
            dlg = dlgprov.createDialog(
                "vnd.sun.star.script:LingToolsBasic.DlgApplyConverter" + \
                "?location=application")
        except:
            pass
        if not dlg:
            self.msgbox.display("Error: Could not show dialog window.")
            return
        self.logger.debug("Created dialog.")

        ## Get dialog controls
        try:
            self.txtConverterName    = getControl(dlg, "txtConvName")
            self.chkDirectionReverse = getControl(dlg, "chkReverse")
            self.txtSourceCol        = getControl(dlg, "txtSourceColumn")
            self.txtTargetCol        = getControl(dlg, "txtTargetColumn")
            btnSelect                = getControl(dlg, "btnSelect")
            btnConvert               = getControl(dlg, "btnConvert")
            btnCancel                = getControl(dlg, "btnCancel")
        except LogicError, exc:
            self.msgbox.display(exc.msg, exc.msg_args)
            dlg.dispose()
            return
        self.logger.debug("Got controls.")

        hamster = Hammy()
        print hamster
        self.logger.debug("Won't get here I bet.")

        ## Command buttons

        btnSelect.setActionCommand("SelectConverter")
        btnSelect.addActionListener(self)
        btnConvert.setActionCommand("Close_and_Convert")
        btnConvert.addActionListener(self)
        btnCancel.setActionCommand("Cancel")
        btnCancel.addActionListener(self)

        ## Display the dialog

        self.dlgClose = dlg.endExecute
        dlg.execute()
        dlg.dispose()

    def actionPerformed(self, event):
        """Handle which button was pressed."""
        self.logger.debug("An action happened: " + event.ActionCommand)
        if event.ActionCommand == "SelectConverter":
            self.logger.debug("Pretending to select a converter...")
        elif event.ActionCommand == "Cancel":
            self.logger.debug("Action command was Cancel")
            self.dlgClose()
            return
        elif event.ActionCommand == "Close_and_Convert":
            self.logger.debug("Closing and Converting...")
            self.dlgClose()

#-------------------------------------------------------------------------------
# Functions that can be called from Tools -> Macros -> Run Macro.
#-------------------------------------------------------------------------------
# End of DlgSimple.py
#-------------------------------------------------------------------------------


# Exported Scripts:
g_exportedScripts = ShowDlg,
