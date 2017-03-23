# -*- coding: Latin-1 -*-
# pylint: disable=too-many-lines
#
# This file created Sept 14 2010 by Jim Kornelsen
#
# 13-Nov-10 JDK  Updated French translations for 1.0 release.
# 01-Apr-11 JDK  Added Spanish.  Localize dynamic labels and status messages.
# 22-Apr-11 JDK  Strings need to be unicode to handle accents correctly.
# 28-Oct-11 JDK  Finished Spanish and French for 1.2 release.
# 27-Feb-13 JDK  Can't modify dict in loop in python 3.3
# 11-Mar-13 JDK  Remove "Default" (use underlying name "Standard" instead).
# 08-Mar-17 JDK  Spanish and French for 3.0 release.

"""
Handle localization of messages into French and Spanish.
Also gets the system locale and list of locales.

To maintain the translations dictionary, here is one approach:
1. Using Vim, change each entry in the dictionary into "eng" | "fr"
   Save as type .csv
2. Open in OOo Calc with | as delimiter.
   Sort by English, and delete duplicates.
3. Use Vim to change back into dictionary entries.

To verify the strings that should go in this file, see
build/generating_code/read_error_messages.pl.

This module exports:
    theLocale
"""
from __future__ import unicode_literals
import logging

from lingt.utils import util

logger = logging.getLogger("lingt.utils.locale")

# The system locale (instantiated after class definition).
theLocale = None

class Locale:
    """Call loadUnoObjs() before using getText()."""

    def __init__(self):
        self.unoObjs = None
        self.code = None  # two-letter ISO language code

    def loadUnoObjs(self, genericUnoObjs):
        """Initialize and get current OpenOffice locale."""
        if self.unoObjs:
            # Already loaded.
            return theLocale
        self.unoObjs = genericUnoObjs

        ## Get locale setting

        configProvider = self.unoObjs.smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider",
            self.unoObjs.ctx)
        args = (
            # trailing comma is required to make a tuple
            util.createProp("nodepath", "/org.openoffice.Setup/L10N"),
        )
        settings = configProvider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess", args)
        OOLang = settings.getByName("ooLocale")
        self.code = OOLang[:2]  # grab first two characters
        logger.debug("locale = %s", self.code)

        ## Make the English key values case insensitive

        translationsLower = dict()
        for en in self.translations:
            translationsLower[en.lower()] = self.translations[en]
        self.translations.update(translationsLower)
        return theLocale

    def getText(self, message_en):
        """Return L10N value.  If no translation is found for the current
        locale, returns the English message.
        """
        if message_en is None:
            return ""
        message_en = str(message_en)
        if self.code == "en":
            return message_en
        key = message_en.lower()
        if key in self.translations:
            phrase_translations = self.translations.get(key)
            message_other = phrase_translations.get(self.code)
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
        """Returns a list of tuples with locale description and locale obj.
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
            desc = "%s (%s)" % (
                Locale.LANG_CODES[localeObj.Language], localeObj.Country)
            descList.append((desc, localeObj))
        return descList

    translations = {

        ## Dynamic labels in dialogs

        "Back to Settings" : {
            'es' :
            "Volver a la configuración",
            'fr' :
            "Atteindre la configuration",
        },
        "Column" : {
            'es' :
            "Columna",
            'fr' :
            "Colonne",
        },
        "Bulk Conversion" : {
            'es' :
            "Conversión masiva",
            'fr' :
            "Conversion en bloc",
        },
        "Get Phonology Examples" : {
            'es' :
            "Obtener ejemplos de fonología",
            'fr' :
            "Obtenir des exemples de phonologie",
        },
        "Get Interlinear Grammar Examples" : {
            'es' :
            "Obtener ejemplos de gramática",
            'fr' :
            "Obtenir des exemples de grammaire",
        },
        "Get words" : {
            'es' :
            "Obtener palabras",
            'fr' :
            "Obtenir mots",
        },
        "Go to Practice" : {
            'es' :
            "Ir a la práctica",
            'fr' :
            "Atteindre exercices",
        },
        "Make Empty List" : {
            'es' :
            "Hacer una lista vacía",
            'fr' :
            "Créer liste vide",
        },
        "Make List" : {
            'es' :
            "Hacer una lista",
            'fr' :
            "Créer liste",
        },
        "Replace with Example" : {
            'es' :
            "Reemplazar con ejemplo",
            'fr' :
            "Remplacer par exemple",
        },
        "Replace All" : {
            'es' :
            "Reemplazar todo",
            'fr' :
            "Remplacer tout",
        },
        "Script Practice" : {
            'es' :
            "Practica de script",
            'fr' :
            "Exercices d'écriture",
        },
        "Script Practice - Settings" : {
            'es' :
            "Practica de script - Configuración",
            'fr' :
            "Exercices d'écriture - Configuration",
        },
        "Searched by %s but did not find anything." : {
            'es' :
            "Se ha buscado por %s pero no ha encontrado nada.",
            'fr' :
            "Recherche selon %s n'a trouvé aucun résultat.",
        },
        "Spelling" : {
            'es' :
            "Ortografía",
            'fr' :
            "Vérification d'orthographe",
        },
        "Testing" : {
            'es' :
            "Probando",
            'fr' :
            "Test",
        },
        "Update Example" : {
            'es' :
            "Actualizar el ejemplo",
            'fr' :
            "Mettre l'exemple à jour",
        },
        "Update All" : {
            'es' :
            "Actualizar todos",
            'fr' :
            "Tout mettre à jour",
        },
        "Word List and Spelling" : {
            'es' :
            "Lista de palabras y ortografía",
            'fr' :
            "Liste de mots et orthographe",
        },

        ## Localized text values

        "(none)" : {
            'es' :
            "(ninguno)",
            'fr' :
            "(aucun)",
        },
        "(cannot make word)" : {
            'es' :
            "(no puede hacer la palabra)",
            'fr' :
            "(impossible de créer mot)",
        },
        "(Fallback Font)" : {
            'es' :
            "(Fuente de Reserva)",
            'fr' :
            "(Police de Remplacement)",
        },
        "(no words found)" : {
            'es' :
            "(no hay palabras encontradas)",
            'fr' :
            "(aucun mot trouvé)",
        },
        "(No data)" : {
            'es' :
            "(No hay datos)",
            'fr' :
            "(Aucune donnée)",
        },
        "Whole Document" : {
            'es' :
            "Documento completo",
            'fr' :
            "Document entier",
        },

        ## Status messages for ProgressBar

        "Converting..." : {
            'es' :
            "Convirtiendo...",
            'fr' :
            "Conversion en cours...",
        },
        "Finding text..." : {
            'es' :
            "Buscando texto...",
            'fr' :
            "Recherche de texte...",
        },
        "Generating List..." : {
            'es' :
            "Generando lista...",
            'fr' :
            "Création de liste...",
        },
        "Getting data..." : {
            'es' :
            "Obteniendo datos...",
            'fr' :
            "L’obtention des données...",
        },
        "Reading..." : {
            'es' :
            "Leyendo...",
            'fr' :
            "",
        },
        "Reading files..." : {
            'es' :
            "Leyendo los archivos...",
            'fr' :
            "Lecture des fichiers...",
        },
        "Saving file..." : {
            'es' :
            "Guardando archivo...",
            'fr' :
            "Enregistrement de fichier...",
        },
        "Searching for occurrences..." : {
            'es' :
            "Buscando ocurrencias...",
            'fr' :
            "Recherche des occurrences...",
        },
        "Sorting..." : {
            'es' :
            "Ordenando...",
            'fr' :
            "Triage...",
        },
        "Loading data..." : {
            'es' :
            "Cargando datos...",
            'fr' :
            "Chargement des données...",
        },

        ## Error messages

        "%s is already in the list." : {
            'es' :
            "%s ya está en la lista.",
            'fr' :
            "%s est déjà dans la liste.",
        },
        "Add '%s' as a new abbreviation?" : {
            'es' :
            "Agregar '%s' como una abreviatura de nuevo?",
            'fr' :
            "Ajouter '%s' comme nouvelle abréviation?",
        },
        "Cannot be in a header or footer." : {
            'es' :
            "No puede ser en un encabezado o un pie de página.",
            'fr' :
            "Interdit dans un en-tête ou pied de page.",
        },
        "Cannot be inside a table or frame." : {
            'es' :
            "No se puede estar dentro de una tabla o un marco.",
            'fr' :
            "Interdit dans un tableau ou cadre",
        },
        "Cannot find file %s" : {
            'es' :
            "No se puede encontrar el archivo %s",
            'fr' :
            "Impossible de trouver le fichier %s",
        },
        "Cannot insert text here." : {
            'es' :
            "No se puede insertar texto aquí.",
            'fr' :
            "Impossible d'insérer texte ici.",
        },
        "Character style '%s' is missing" : {
            'es' :
            "No se encuentra el estilo de carácter '%s'",
            'fr' :
            "Style de caractère '%s' introuvable",
        },
        "Column width is not a number." : {
            'es' :
            "El ancho de columna no es un número.",
            'fr' :
            "La largeur de colonne n'est pas un nombre.",
        },
        "Could not create style '%s'." : {
            'es' :
            "No se pudo crear el estilo '%s'.",
            'fr' :
            "Impossible de créer le style '%s'.",
        },
        "Could not create temporary folder %s" : {
            'es' :
            "No se pudo crear la carpeta temporal %s.",
            'fr' :
            "Impossible de créer le dossier temporaire %s.",
        },
        "Could not find any words in '%s'.  Try changing %s%d to use a "
        "different marker, or change %s to 'WordLine%d'." : {
            'es' :
            "No se encontraron palabras en '%s'. Intente cambiar %s%d para "
            "usar un marcador diferente, o cambie %s a 'WordLine%d'.",
            'fr' :
            "Impossible de trouver des mots dans '%s'. Essayer une autre "
            "balise pour %s%d, ou modifier %s en 'WordLine%d'.",
        },
        "Could not find ref number %s" : {
            'es' :
            "No se encuentra el número de referencia %s",
            'fr' :
            "Numéro de référence %s introuvable.",
        },
        "Could not find ref number %s\n\nSuggestions\n%s" : {
            'es' :
            "No se encuentra el número de referencia %s\n\nSugerencias\n%s",
            'fr' :
            "Numéro de référence %s introuvable.\n\nSuggestions\n%s",
        },
        "Could not get AddConverter function.  Automatically adding a "
        "converter requires SEC4.0 or higher." : {
            'es' :
            "No se pudo obtener la función AddConverter. La "
            "adición automática de un convertidor requiere "
            "SEC4.0 o superior.",
            'fr' :
            "Impossible d'obtenir la fonction AddConverter. L'ajout "
            "automatique d'un convertisseur nécessite SEC4.0 ou supérieur.",
        },
        "Could not get column %d, row %d of table %s." : {
            'es' :
            "No se pudo obtener la columna %d, fila %d de la tabla%s.",
            'fr' :
            "Impossible d’obtenir colonne %d, ligne %d de table %s.",
        },
        "Could not get selection string." : {
            'es' :
            "No se pudo obtener la cadena de selección.",
            'fr' :
            "Impossible d’obtenir la chaîne de sélection",
        },
        "Did not find any data in file %s" : {
            'es' :
            "No ha encontrado ningún dato en el archivo %s",
            'fr' :
            "Aucune donnée n'a été trouvée dans le fichier %s",
        },
        "Did not find any similar words." : {
            'es' :
            "No encontró algunas palabras similares.",
            'fr' :
            "On n'a trouvé aucun mot similaire.",
        },
        "Did not find any words for the list." : {
            'es' :
            "No encontró algunas palabras para la lista.",
            'fr' :
            "On n'a trouvé aucun mot pour la liste.",
        },
        "Did not find anything in column %s." : {
            'es' :
            "No encontró nada en la columna %s.",
            'fr' :
            "On n'a rien trouvé dans colonne %s.",
        },
        "Did not find scope of change." : {
            'es' :
            "No ha encontrado el ámbito del cambio.",
            'fr' :
            "L'étendue de changement n'a pas été trouvée.",
        },
        "EncConverters does not seem to be installed properly." : {
            'es' :
            "EncConverters no parece que se haya instalado correctamente.",
            'fr' :
            "EncConverters semble être mal installé",
        },
        "Error parsing %s user variable.  Please go to Insert -> Field -> "
        "More Fields and fix the problem." : {
            'es' :
            "Error al analizar %s variable de usuario.  Por favor, vaya a "
            "Insertar -> Campos y solucionar el problema.",
            'fr' :
            "Erreur en analysant la variable utilisateur %s.  Veuillez "
            "atteindre Insertion -> Champs pour résoudre le problème.",
        },
        "Error reading file %s" : {
            'es' :
            "Error al leer el archivo %s",
            'fr' :
            "Erreur en lisant le fichier %s",
        },
        "Error reading file %s\n\n%s" : {
            'es' :
            "Error al leer el archivo %s\n\n%s",
            'fr' :
            "Erreur en lisant le fichier %s\n\n%s",
        },
        "Error saving %s" : {
            'es' :
            "Error al guardar %s",
            'fr' :
            "Erreur d’enregistrement de %s",
        },
        "Error showing dialog: No %s control." : {
            'es' :
            "Error al mostrar el diálogo: No %s control.",
            'fr' :
            "Erreur d’affichage du dialogue: Aucun contrôle %s",
        },
        "Error with file: %s" : {
            'es' :
            "Error con el archivo: %s",
            'fr' :
            "Erreur de fichier : %s",
        },
        "Error reading spreadsheet." : {
            'es' :
            "Error al leer la hoja de cálculo",
            'fr' :
            "Erreur de lecture de classeur",
        },
        "Error reading the list." : {
            'es' :
            "Error al leer la lista.",
            'fr' :
            "Erreur de lecture de liste.",
        },
        "Error reading the list.\n\n%s" : {
            'es' :
            "Error al leer la lista.\n\n%s",
            'fr' :
            "Erreur de lecture de liste.\n\n%s",
        },
        "Error writing to spreadsheet." : {
            'es' :
            "Error al escribir al hoja de cálculo.",
            'fr' :
            "Erreur d'écriture de classeur.",
        },
        "Error: Could not create dialog." : {
            'es' :
            "Error: No se pudo crear el diálogo.",
            'fr' :
            "Erreur : Impossible de créer dialogue.",
        },
        "Error: EncConverters returned %d%s." : {
            'es' :
            "Error: EncConverters devolvió %d%s.",
            'fr' :
            "Erreur: EncConverters a répondu %d%s.",
        },
        "Expected frame margin parameter." : {
            'es' :
            "Parámetro de margen de marco esperado.",
            'fr' :
            "Paramètre de marge de cadre attendu.",
        },
        "Expected styleFonts to be set." : {
            'es' :
            "Se espera que se establezcan styleFonts.",
            'fr' :
            "Paramètre de styleFonts attendu.",
        },
        "Failed to encode string properly." : {
            'es' :
            "No pudo codificar correctamente la cadena.",
            'fr' :
            "Impossible d'encoder correctement la chaîne.",
        },
        "Failed to go to text range." : {
            'es' :
            "No pudo ir al rango de texto.",
            'fr' :
            "Impossible d’atteindre la plage de texte.",
        },
        "File does not seem to be from Toolbox or FieldWorks: %s" : {
            'es' :
            "El archivo no parece ser del Toolbox o Fieldworks: %s",
            'fr' :
            "Il semble que ce fichier n'a pas été créé par Toolbox ou "
            "FieldWorks: %s",
        },
        "File is already in the list." : {
            'es' :
            "El archivo ya está en la lista.",
            'fr' :
            "Le fichier est déjà dans la liste.",
        },
        "First press Copy." : {
            'es' :
            "Primero presione Copiar.",
            'fr' :
            "Appuyer d'abord sur Copier.",
        },
        "Found %d similar words." : {
            'es' :
            "Encontrado %d palabras similares.",
            'fr' :
            "%d mots similaires trouvés.",
        },
        "Found %d words." : {
            'es' :
            "Encontrado %d palabras.",
            'fr' :
            "%d mots trouvés.",
        },
        "Found %d paragraphs and made %d change%s." : {
            'es' :
            "Ha encontrado %d párrafos y hizo %d cambio%s.",
            'fr' :
            "%d paragraphes trouvés et %d changement%s faits.",
        },
        "Found a ref number, but it must be in an outer table in order to "
        "be updated." : {
            'es' :
            "Ha encontrado un número de referencia, pero debe estar en una "
            "tabla de exterior para ser actualizados.",
            'fr' :
            "N° de réf.  trouvé, mais pour l'actualier il doit être dans un "
            "cadre exterieur",
        },
        "Frame style '%s' is missing" : {
            'es' :
            "No se encuentra el estilo del marco '%s'",
            'fr' :
            "Style de cadre '%s' introuvable",
        },
        "If you want to use LIFT data, then first specify a LIFT file "
        "exported from FieldWorks." : {
            'es' :
            "Si desea utilizar los datos LIFT, en primer lugar especificar "
            "un archivo LIFT exportados de Fieldworks.",
            'fr' :
            "Pour utiliser des données LIFT il faut spécifier un fichier "
            "LIFT exporté de FieldWorks.",
        },
        "Library error: %s." : {
            'es' :
            "Error de rutinas: %s.",
            'fr' :
            "Erreur de logiciel: %s.",
        },
        "Made %d change%s to %d file%s." : {
            'es' :
            "Hecho %d cambio%s a %d archivo %s.",
            'fr' :
            "%d changement%s faits dans %d fichier%s.",
        },
        "Made %d change%s." : {
            'es' :
            "Hizo %d cambio%s.",
            'fr' :
            "%d changement%s faits.",
        },
        "Made %d correction%s." : {
            'es' :
            "Hizo %d correccione%s.",
            'fr' :
            "On a fait %d correction%s.",
        },
        "Made list of %d words." : {
            'es' :
            "Hizo una lista de %d palabras.",
            'fr' :
            "On a créé une liste de %d mots.",
        },
        "Make this change?" : {
            'es' :
            "¿Hacer este cambio?",
            'fr' :
            "Modifier ceci?",
        },
        "Make this change?  (%s -> %s)" : {
            'es' :
            "¿Hacer este cambio?  (%s -> %s)",
            'fr' :
            "Modifier ceci?  (%s -> %s)",
        },
        "Missed word '%s'.  Keep going?" : {
            'es' :
            "Hubo un problema con la palabra '%s'.  ¿Seguir adelante?",
            'fr' :
            "Un problème en le mot '%s'.  Continuer?",
        },
        "No conversion result." : {
            'es' :
            "No hay resultado de conversión.",
            'fr' :
            "Aucun résultat de conversion.",
        },
        "No changes, but modified style of %d paragraph%s." : {
            'es' :
            "No hubo cambios, pero el estilo de %d párrafo%s se ha "
            "modificado.",
            'fr' :
            "Pas de changements, mais le style de %d paragraphe%s a été "
            "changé.",
        },
        "No changes." : {
            'es' :
            "No hubo cambios.",
            'fr' :
            "Pas de changements.",
        },
        "No converter was specified." : {
            'es' :
            "No convertidor se ha especificado.",
            'fr' :
            "Aucun convertisseur spécifié.",
        },
        "No data found." : {
            'es' :
            "No se encontraron datos",
            'fr' :
            "Aucune donnée trouvée.",
        },
        "No locale was specified." : {
            'es' :
            "Un locale no se ha especificado",
            'fr' :
            "Aucuns paramètres régionaux spécifiés.",
        },
        "No more existing examples found." : {
            'es' :
            "No se ha encontrado más ejemplos existentes",
            'fr' :
            "Il n'y a plus d'exemples trouvés.",
        },
        "No more possible abbreviations found." : {
            'es' :
            "No se ha encontrado más abreviaturas posibles",
            'fr' :
            "On ne trouve plus des abréviations possibles.",
        },
        "No more reference numbers found." : {
            'es' :
            "No se ha encontrado más números de referencia",
            'fr' :
            "On ne trouve plus des numéros de référence.",
        },
        "No more reference numbers found.\n Make sure to type # in front." : {
            'es' :
            "No se encontraron más números de referencia. \n Asegúrese de "
            "escribir # delante.",
            'fr' :
            "On ne trouve plus des numéros de référence. Il faut vérifier "
            "le # devant des numéros.",
        },
        "No scope was specified." : {
            'es' :
            "No se especificó ningún ámbito.",
            'fr' :
            "Aucune étendue n’était spécifiée",
        },
        "No SF markers were specified.  Continue anyway?" : {
            'es' :
            "Ningún marcadores SFM fueron especificados.  ¿Desea continuar?",
            'fr' :
            "Aucune balise SFM spécifiée.  Continuer quand même?",
        },
        "No spreadsheet is open." : {
            'es' :
            "No hay ninguna hoja de cálculo abierto.",
            'fr' :
            "Aucun classeur est ouvert.",
        },
        "No task was specified." : {
            'es' :
            "No se especificó ninguna tarea.",
            'fr' :
            "Aucune tâche n’était spécifiée",
        },
        "No writing systems found." : {
            'es' :
            "No se encontraron sistemas de escritura.",
            'fr' :
            "Aucune systèmes d'écriture trouvée.",
        },
        "No Xpath expressions were specified.  Continue anyway?" : {
            'es' :
            "Ningún expresiones XPath fueron especificadas.  "
            "¿Desea continuar?",
            'fr' :
            "Aucune expression Xpath spécifiée.  Continuer quand même?",
        },
        "No text is selected." : {
            'es' :
            "No hay texto seleccionado.",
            'fr' :
            "Aucun texte sélectionné.",
        },
        "Paragraph style '%s' is missing" : {
            'es' :
            "No se encuentra el estilo de párrafo '%s'",
            'fr' :
            "Style de paragraphe '%s' introuvable",
        },
        "Please add a file to get words." : {
            'es' :
            "Por favor, añada un archivo para obtener las palabras.",
            'fr' :
            "Veuillez ajouter un fichier duquel on peut obtenir des mots.",
        },
        "Please add files to scan." : {
            'es' :
            "Por favor, agregue archivos para escanear.",
            'fr' :
            "Veuillez ajouter des fichiers à analyser.",
        },
        "Please do not select individual table cells." : {
            'es' :
            "Por favor, no seleccione las celdas individuales de la tabla.",
            'fr' :
            "Veuillez ne pas choisir des cellules individuelles.",
        },
        "Please enter a number for max length." : {
            'es' :
            "Por favor, introduzca un número para la longitud máxima.",
            'fr' :
            "Veuillez entrer la longueur maximum.",
        },
        "Please enter a ref number." : {
            'es' :
            "Por favor, introduzca un número de referencia.",
            'fr' :
            "Veuillez entrer un numéro de référence.",
        },
        "Please enter a ref number.\n\nSuggestions\n%s" : {
            'es' :
            "Por favor, introduzca un número de referencia."
            "\n\nSugerencias\n%s",
            'fr' :
            "Veuillez entrer un numéro de référence.\n\nSuggestions\n%s",
        },
        "Please enter a value for column width." : {
            'es' :
            "Por favor, introduzca un valor para el ancho de la columna.",
            'fr' :
            "Veuillez entrer la largeur de colonne.",
        },
        "Please go to Grammar Settings and specify a file." : {
            'es' :
            "Por favor, vaya a la Configuración de gramática y especifique "
            "un archivo.",
            'fr' :
            "Veuillez choisir un fichier dans Configuration de grammaire.",
        },
        "Please go to Phonology Settings and specify a file." : {
            'es' :
            "Por favor, vaya a la Configuración de fonología y especifique "
            "un archivo.",
            'fr' :
            "Veuillez spécifier un fichier dans Configuration de phonologie.",
        },
        "Please load a word list by clicking on the Files... button.  When "
        "file settings are finished, click Get words." : {
            'es' :
            "Por favor, cargue una lista de palabras haciendo clic en el "
            "botón Archivos.  Cuando la configuración de archivo se haya "
            "terminado, haga clic en Obtener palabras.",
            'fr' :
            "Veuillez charger une liste de mots en cliquant sur Fichiers...  "
            "Après avoir fait la configuration de fichier",
        },
        "Please save the current document first." : {
            'es' :
            "Por favor, primero guarde el documento actual.",
            'fr' :
            "Veuillez enregistrer d'abord le document actuel.",
        },
        "Please save the spreadsheet first." : {
            'es' :
            "Por favor, primero guarde la hoja de cálculo.",
            'fr' :
            "Veuillez d'abord enregistrer le classeur",
        },
        "Please select %s in the list." : {
            'es' :
            "Por favor, seleccione %s en la lista.",
            'fr' :
            "Veuillez choisir %s dans la liste.",
        },
        "Please select a converter." : {
            'es' :
            "Por favor, seleccione un convertidor.",
            'fr' :
            "Veuillez choisir un convertisseur.",
        },
        "Please select a file in the list." : {
            'es' :
            "Por favor, seleccione un archivo en la lista.",
            'fr' :
            "Veuillez choisir un fichier dans la liste.",
        },
        "Please select a language name." : {
            'es' :
            "Por favor, seleccione un nombre de idioma.",
            'fr' :
            "Veuillez sélectionner un nom de langue.",
        },
        "Please select a scope character style." : {
            'es' :
            "Por favor, seleccione un estilo de carácter ámbito.",
            'fr' :
            "Veuillez choisir un style de caractère pour l'étendue.",
        },
        "Please select a scope font." : {
            'es' :
            "Por favor, seleccione una fuente ámbito.",
            'fr' :
            "Veuillez choisir une police pour l'étendue.",
        },
        "Please select a paragraph style." : {
            'es' :
            "Por favor, seleccione un estilo de párrafo.",
            'fr' :
            "Veuillez choisir un style de paragraphe.",
        },
        "Please select a scope paragraph style." : {
            'es' :
            "Por favor, seleccione un estilo de párrafo ámbito.",
            'fr' :
            "Veuillez choisir un style de paragraphe pour l'étendue.",
        },
        "Please select a script." : {
            'es' :
            "Por favor, seleccione un script.",
            'fr' :
            "Veuillez choisir un écriture.",
        },
        "Please select a target font." : {
            'es' :
            "Por favor, seleccione una fuente destino.",
            'fr' :
            "Veuillez choisir une police cible.",
        },
        "Please select a target style." : {
            'es' :
            "Por favor, seleccione un estilo destino.",
            'fr' :
            "Veuillez choisir un style cible.",
        },
        "Please select an abbreviation in the list." : {
            'es' :
            "Por favor, seleccione una abreviatura de la lista.",
            'fr' :
            "Veuillez choisir une abréviation dans la liste.",
        },
        "Please select an item in the list." : {
            'es' :
            "Por favor, seleccione un elemento de la lista.",
            'fr' :
            "Veuillez choisir un élément dans la liste.",
        },
        "Please select an output folder." : {
            'es' :
            "Por favor, seleccione una carpeta de salida.",
            'fr' :
            "Veuillez choisir un dossier cible.",
        },
        "Please select or enter something to find." : {
            'es' :
            "Por favor seleccione o escriba algo para buscar.",
            'fr' :
            "Veuillez sélectionner ou saisir quelque chose à rechercher.",
        },
        "Please select the converter again." : {
            'es' :
            "Por favor, seleccione el convertidor de nuevo.",
            'fr' :
            "Veuillez choisir encore le convertisseur.",
        },
        "Please specify SFMs." : {
            'es' :
            "Por favor, especifique los SFMs.",
            'fr' :
            "Veuillez spécifier les balises (SFMs).",
        },
        "Please specify a file to export." : {
            'es' :
            "Por favor, especifique un archivo para exportar.",
            'fr' :
            "Veuillez spécifier un fichier à exporter.",
        },
        "Please specify a scope." : {
            'es' :
            "Por favor, especifique un ámbito.",
            'fr' :
            "Veuillez spécifier l'étendue.",
        },
        "Please specify a target." : {
            'es' :
            "Por favor, especifique un destino.",
            'fr' :
            "Veuillez spécifier un cible.",
        },
        "Please specify a word list file.  To make a new empty list, go to "
        "Word List and Spelling and then save the spreadsheet file." : {
            'es' :
            "Por favor, especifique un archivo de una lista de palabras.  "
            "Para crear una nueva lista vacía, vaya a Lista de palabras y "
            "ortografía y guarde el archivo de hoja de cálculo.",
            'fr' :
            "Veuillez spécifier un fichier de liste de mots.  Pour créer une "
            "nouvelle liste vide, atteindre Liste de mots et orthographe, "
            "puis enregistrer le classeur.",
        },
        "Replaced %d example%s." : {
            'es' :
            "reemplazado %d ejemplo%s.",
            'fr' :
            "%d exemple%s a été remplasé.",
        },
        "Spell check finished." : {
            'es' :
            "Spell check finished.",
            'fr' :
            "Vérification d'orthographe terminée.",
        },
        "Successfully finished conversion." : {
            'es' :
            "Terminado con éxito la conversión.",
            'fr' :
            "Conversion terminée avec succès.",
        },
        "The cursor cannot be in a header or footer." : {
            'es' :
            "El cursor no puede estar en un encabezado o en un pie de "
            "página.",
            'fr' :
            "Le curseur ne peut pas se trouver dans un en-tête ou dans un "
            "pied de page.",
        },
        "The cursor cannot be inside a table or frame." : {
            'es' :
            "El cursor no puede estar dentro de una tabla o un marco.",
            'fr' :
            "Le curseur ne peut pas se trouver dans un tableau ou dans un "
            "cadre.",
        },
        "There was a problem while writing the list.\n\n%s" : {
            'es' :
            "Hubo un problema al escribir la lista.\n\n%s",
            'fr' :
            "Un problème est survenu en écrivant la liste.\n\n%s",
        },
        "This document stores %s settings.  "
        "Please leave it open while using %s.  "
        "If you want to keep the settings to use again later, "
        "then save this document." : {
            'es' :
            "Este documento guarda la configuración de %s.  "
            "Por favor, dejarlo abierto durante el uso de %s.  "
            "Si desea mantener la configuración para utilizarlo más "
            "adelante, guarde este documento.",
            'fr' :
            "Ce document contient la configuration de la fonction %s.  "
            "Veuillez le laisser ouvert en utilisant %s.  "
            "Pour garder la configuration afin de la réutiliser plus tard, "
            "enregistrer ce document.",
        },
        "This expression is already in the list." : {
            'es' :
            "Esta expresión está ya en la lista.",
            'fr' :
            "Cette expression est déjà dans la liste.",
        },
        "This will change the case of the entire list from '%s' to '%s.' "
        "Continue?" : {
            'es' :
            "Esto cambiará el caso de la lista completa de '%s' a '%s'.  "
            "¿Desea continuar?",
            'fr' :
            "Ceci changera la casse de toute la liste de '%s' à '%s'.  "
            "Continuer?",
        },
        "This word was already set to correct.  Change anyway?" : {
            'es' :
            "Esta palabra ya estaba configurada para corregir. "
            "¿Cambiar de todos modos?",
            'fr' :
            "Ce mot est déjà réglé pour corriger. Modifier quand même?",
        },
        "To update examples, 'Outer table' must be marked in Grammar "
        "Settings." : {
            'es' :
            "'Tabla de exterior' debe estar en la Configuración de "
            "gramática.",
            'fr' :
            "'Cadre exterieur' doit être dans Configuration de grammaire.",
        },
        "Too many files named like %s." : {
            'es' :
            "Demasiados archivos con el nombre %s.",
            'fr' :
            "Trop de fichiers nommés comme %s.",
        },
        "Too many temporary folders in %s." : {
            'es' :
            "Demasiadas carpetas temporales en %s.",
            'fr' :
            "Trop de dossiers temporaires dans %s.",
        },
        "Unexpected file type %s" : {
            'es' :
            "Tipo de archivo inesperado %s",
            'fr' :
            "Type de fichier %s inattendu",
        },
        "Unexpected font type %s." : {
            'es' :
            "Tipo de fuente inesperada %s.",
            'fr' :
            "Police de type %s inattendue.",
        },
        "Unexpected new value %s." : {
            'es' :
            "Nuevo valor inesperado %s.",
            'fr' :
            "Nouvelle valeur inattendue %s.",
        },
        "Unexpected value %r" : {
            'es' :
            "Valor inesperado %r.",
            'fr' :
            "Valeur inattendue %r",
        },
        "Unexpected value %s" : {
            'es' :
            "Valor inesperado %s.",
            'fr' :
            "Valeur inattendue %s",
        },
        "Unknown action command '%s'" : {
            'es' :
            "Comando de acción desconocido '%s'",
            'fr' :
            "Commande d'action inconnue '%s'",
        },
        "Unknown file type for %s" : {
            'es' :
            "Tipo de archivo desconocido para %s",
            'fr' :
            "Type de fichier inconnu pour %s",
        },
        "Unknown grabKey '%s'" : {
            'es' :
            "grabKey '%s' desconocido",
            'fr' :
            "grabKey '%s' inconnu",
        },
        "Update all examples now?  It is recommended to save a copy of your "
        "document first." : {
            'es' :
            "¿Actualizar todos los ejemplos ahora?  Se recomienda que "
            "primero guarde una copia de su documento.",
            'fr' :
            "Actualiser tous les exemples maintenant?  Il est conseillé "
            "d'enregistrer le document d'abord.",
        },
        "Updated '%s' %d times in a row.  Keep going?" : {
            'es' :
            "Actualizado '%s' %d veces seguidas.  ¿Seguir adelante?",
            'fr' :
            "'%s' a été actualisé %d fois de suite.  Continuer?",
        },
        "Updated %d example%s." : {
            'es' :
            "Actualizado %d ejemplo%s.",
            'fr' :
            "%d exemple%s a été actualisé.",
        },
        "Value %d for column width is too high." : {
            'es' :
            "El valor de %d para el ancho de columna es demasiado alta.",
            'fr' :
            "%d est trop grande comme largeur de colonne.",
        },
        "Value for column width must be more than zero." : {
            'es' :
            "El valor para el ancho de columna debe ser mayor de cero.",
            'fr' :
            "La largeur de colonne doit être supérieure à zéro.",
        },
        "'Whole Document' must be the only thing to find." : {
            'es' :
            "'Documento Completo' debe ser la única cosa para buscar.",
            'fr' :
            "'Document entier' doit être la seule chose à rechercher",
        },
        "Word failed to fit properly." : {
            'es' :
            "La palabra no se ajustó correctamente.",
            'fr' :
            "Le mot ne rentre pas correctement.",
        },
        "You did not made any changes to the word." : {
            'es' :
            "No hiciste ningún cambio en la palabra.",
            'fr' :
            "Vous n'avez apporté aucun changement au mot.",
        },
        "You did not specify anything to find.  Continue anyway?" : {
            'es' :
            "No ha especificado nada que encontrar.  ¿Desea continuar?",
            'fr' :
            "Vous n'avez spécifier aucune chose à rechercher.  Continuer "
            "quand même?",
        },
    }

theLocale = Locale()
