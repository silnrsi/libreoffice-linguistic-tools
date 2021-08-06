# -*- coding: Latin-1 -*-
# pylint: disable=too-many-lines

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
            "Volver a la configuraci�n",
            'fr' :
            "Atteindre la configuration",
        },
        "Bulk Conversion" : {
            'es' :
            "Conversi�n masiva",
            'fr' :
            "Conversion en bloc",
        },
        "Column" : {
            'es' :
            "Columna",
            'fr' :
            "Colonne",
        },
        "Draw" : {
            'es' :
            "Draw",
            'fr' :
            "Draw",
        },
        "Get Phonology Examples" : {
            'es' :
            "Obtener ejemplos de fonolog�a",
            'fr' :
            "Obtenir des exemples de phonologie",
        },
        "Get Interlinear Examples" : {
            'es' :
            "Obtener ejemplos interlineales",
            'fr' :
            "Obtenir des exemples interlin�aires",
        },
        "Get words" : {
            'es' :
            "Obtener palabras",
            'fr' :
            "Obtenir mots",
        },
        "Go to Practice" : {
            'es' :
            "Ir a la pr�ctica",
            'fr' :
            "Atteindre exercices",
        },
        "Insert Examples" : {
            'es' :
            "Insertar ejemplos",
            'fr' :
            "Ins�rer exemples",
        },
        "Insert this Example" : {
            'es' :
            "Insertar este ejemplo",
            'fr' :
            "Ins�rer cet exemple",
        },
        "Make Empty List" : {
            'es' :
            "Hacer una lista vac�a",
            'fr' :
            "Cr�er liste vide",
        },
        "Make List" : {
            'es' :
            "Hacer una lista",
            'fr' :
            "Cr�er liste",
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
            "Exercices d'�criture",
        },
        "Script Practice - Settings" : {
            'es' :
            "Practica de script - Configuraci�n",
            'fr' :
            "Exercices d'�criture - Configuration",
        },
        "Searched by %s but did not find anything." : {
            'es' :
            "Se ha buscado por %s pero no ha encontrado nada.",
            'fr' :
            "Recherche selon %s n'a trouv� aucun r�sultat.",
        },
        "Spelling" : {
            'es' :
            "Ortograf�a",
            'fr' :
            "V�rification d'orthographe",
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
            "Mettre l'exemple � jour",
        },
        "Update All" : {
            'es' :
            "Actualizar todos",
            'fr' :
            "Tout mettre � jour",
        },
        "Word Lists and Spelling" : {
            'es' :
            "Listas de palabras y ortograf�a",
            'fr' :
            "Listes de mots et orthographe",
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
            "(impossible de cr�er mot)",
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
            "(aucun mot trouv�)",
        },
        "(No data)" : {
            'es' :
            "(No hay datos)",
            'fr' :
            "(Aucune donn�e)",
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
            "Cr�ation de liste...",
        },
        "Getting data..." : {
            'es' :
            "Obteniendo datos...",
            'fr' :
            "L�obtention des donn�es...",
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
            "Chargement des donn�es...",
        },

        ## Error messages

        "%s finished." : {
            'es' :
            "%s terminado.",
            'fr' :
            "%s termin�.",
        },
        "%s is already in the list." : {
            'es' :
            "%s ya est� en la lista.",
            'fr' :
            "%s est d�j� dans la liste.",
        },
        "Add '%s' as a new abbreviation?" : {
            'es' :
            "Agregar '%s' como una abreviatura de nuevo?",
            'fr' :
            "Ajouter '%s' comme nouvelle abr�viation?",
        },
        "Cannot be in a header or footer." : {
            'es' :
            "No puede ser en un encabezado o un pie de p�gina.",
            'fr' :
            "Interdit dans un en-t�te ou pied de page.",
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
            "No se puede insertar texto aqu�.",
            'fr' :
            "Impossible d'ins�rer texte ici.",
        },
        "Character style '%s' is missing" : {
            'es' :
            "No se encuentra el estilo de car�cter '%s'",
            'fr' :
            "Style de caract�re '%s' introuvable",
        },
        "Column width is not a number." : {
            'es' :
            "El ancho de columna no es un n�mero.",
            'fr' :
            "La largeur de colonne n'est pas un nombre.",
        },
        "Could not create style '%s'." : {
            'es' :
            "No se pudo crear el estilo '%s'.",
            'fr' :
            "Impossible de cr�er le style '%s'.",
        },
        "Could not create temporary folder %s" : {
            'es' :
            "No se pudo crear la carpeta temporal %s.",
            'fr' :
            "Impossible de cr�er le dossier temporaire %s.",
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
            "No se encuentra el n�mero de referencia %s",
            'fr' :
            "Num�ro de r�f�rence %s introuvable.",
        },
        "Could not get AddConverter function.  Automatically adding a "
        "converter requires SEC4.0 or higher." : {
            'es' :
            "No se pudo obtener la funci�n AddConverter. La "
            "adici�n autom�tica de un convertidor requiere "
            "SEC4.0 o superior.",
            'fr' :
            "Impossible d'obtenir la fonction AddConverter. L'ajout "
            "automatique d'un convertisseur n�cessite SEC4.0 ou sup�rieur.",
        },
        "Could not get column %d, row %d of table %s." : {
            'es' :
            "No se pudo obtener la columna %d, fila %d de la tabla%s.",
            'fr' :
            "Impossible d�obtenir colonne %d, ligne %d de table %s.",
        },
        "Could not get selection string." : {
            'es' :
            "No se pudo obtener la cadena de selecci�n.",
            'fr' :
            "Impossible d�obtenir la cha�ne de s�lection",
        },
        "Did not find any data in file %s" : {
            'es' :
            "No ha encontrado ning�n dato en el archivo %s",
            'fr' :
            "Aucune donn�e n'a �t� trouv�e dans le fichier %s",
        },
        "Did not find any similar words." : {
            'es' :
            "No encontr� algunas palabras similares.",
            'fr' :
            "On n'a trouv� aucun mot similaire.",
        },
        "Did not find any words for the list." : {
            'es' :
            "No encontr� algunas palabras para la lista.",
            'fr' :
            "On n'a trouv� aucun mot pour la liste.",
        },
        "Did not find anything in column %s." : {
            'es' :
            "No encontr� nada en la columna %s.",
            'fr' :
            "On n'a rien trouv� dans colonne %s.",
        },
        "Did not find scope of change." : {
            'es' :
            "No ha encontrado el �mbito del cambio.",
            'fr' :
            "L'�tendue de changement n'a pas �t� trouv�e.",
        },
        "\n\nEither change the numbers or, if they are in "
        "different texts, add a prefix for each text.\n"
        "Press OK to use these settings anyway." : {
            'es' :
            "\n\nCambia los n�meros o, si est�n en"
            "diferentes textos, agregue un prefijo para cada texto.\n"
            "Presione OK para usar estas configuraciones de todos modos",
            'fr' :
            "\n\nSoit modifiez les nombres ou, s'ils sont"
            "textes diff�rents, ajoutez un pr�fixe pour chaque texte.\n"
            "Appuyez sur OK pour utiliser ces param�tres quand m�me.",
        },
        "EncConverters does not seem to be installed properly." : {
            'es' :
            "EncConverters no parece que se haya instalado correctamente.",
            'fr' :
            "EncConverters semble �tre mal install�",
        },
        "Error parsing %s user variable.  Please go to Insert -> Field -> "
        "More Fields and fix the problem." : {
            'es' :
            "Error al analizar %s variable de usuario.  Por favor, vaya a "
            "Insertar -> Campos y solucionar el problema.",
            'fr' :
            "Erreur en analysant la variable utilisateur %s.  Veuillez "
            "atteindre Insertion -> Champs pour r�soudre le probl�me.",
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
            "Erreur d�enregistrement de %s",
        },
        "Error showing dialog: No %s control." : {
            'es' :
            "Error al mostrar el di�logo: No %s control.",
            'fr' :
            "Erreur d�affichage du dialogue: Aucun contr�le %s",
        },
        "Error with file: %s" : {
            'es' :
            "Error con el archivo: %s",
            'fr' :
            "Erreur de fichier : %s",
        },
        "Error reading spreadsheet." : {
            'es' :
            "Error al leer la hoja de c�lculo",
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
            "Error al escribir al hoja de c�lculo.",
            'fr' :
            "Erreur d'�criture de classeur.",
        },
        "Error: Could not create dialog." : {
            'es' :
            "Error: No se pudo crear el di�logo.",
            'fr' :
            "Erreur : Impossible de cr�er dialogue.",
        },
        "Error: EncConverters returned %d%s." : {
            'es' :
            "Error: EncConverters devolvi� %d%s.",
            'fr' :
            "Erreur: EncConverters a r�pondu %d%s.",
        },
        "Expected frame margin parameter." : {
            'es' :
            "Par�metro de margen de marco esperado.",
            'fr' :
            "Param�tre de marge de cadre attendu.",
        },
        "Expected styleFonts to be set." : {
            'es' :
            "Se espera que se establezcan styleFonts.",
            'fr' :
            "Param�tre de styleFonts attendu.",
        },
        "Failed to encode string properly." : {
            'es' :
            "No pudo codificar correctamente la cadena.",
            'fr' :
            "Impossible d'encoder correctement la cha�ne.",
        },
        "Failed to go to text range." : {
            'es' :
            "No pudo ir al rango de texto.",
            'fr' :
            "Impossible d�atteindre la plage de texte.",
        },
        "File does not seem to be from Toolbox or FieldWorks: %s" : {
            'es' :
            "El archivo no parece ser del Toolbox o Fieldworks: %s",
            'fr' :
            "Il semble que ce fichier n'a pas �t� cr�� par Toolbox ou "
            "FieldWorks: %s",
        },
        "File is already in the list." : {
            'es' :
            "El archivo ya est� en la lista.",
            'fr' :
            "Le fichier est d�j� dans la liste.",
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
            "%d mots similaires trouv�s.",
        },
        "Found %d words." : {
            'es' :
            "Encontrado %d palabras.",
            'fr' :
            "%d mots trouv�s.",
        },
        "Found %d paragraphs and made %d change%s." : {
            'es' :
            "Ha encontrado %d p�rrafos y hizo %d cambio%s.",
            'fr' :
            "%d paragraphes trouv�s et %d changement%s faits.",
        },
        "Found a ref number, but it must be in an outer table in order to "
        "be updated." : {
            'es' :
            "Ha encontrado un n�mero de referencia, pero debe estar en una "
            "tabla de exterior para ser actualizados.",
            'fr' :
            "N� de r�f.  trouv�, mais pour l'actualier il doit �tre dans un "
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
            "Pour utiliser des donn�es LIFT il faut sp�cifier un fichier "
            "LIFT export� de FieldWorks.",
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
            "On a cr�� une liste de %d mots.",
        },
        "Make OXT" : {
            'es' :
            "Hacer OXT",
            'fr' :
            "Cr�er OXT",
        },
        "Make this change?" : {
            'es' :
            "�Hacer este cambio?",
            'fr' :
            "Modifier ceci?",
        },
        "Make this change?  (%s -> %s)" : {
            'es' :
            "�Hacer este cambio?  (%s -> %s)",
            'fr' :
            "Modifier ceci?  (%s -> %s)",
        },
        "Missed word '%s'.  Keep going?" : {
            'es' :
            "Hubo un problema con la palabra '%s'.  �Seguir adelante?",
            'fr' :
            "Un probl�me en le mot '%s'.  Continuer?",
        },
        "No conversion result." : {
            'es' :
            "No hay resultado de conversi�n.",
            'fr' :
            "Aucun r�sultat de conversion.",
        },
        "No changes, but modified style of %d paragraph%s." : {
            'es' :
            "No hubo cambios, pero el estilo de %d p�rrafo%s se ha "
            "modificado.",
            'fr' :
            "Pas de changements, mais le style de %d paragraphe%s a �t� "
            "chang�.",
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
            "Aucun convertisseur sp�cifi�.",
        },
        "No data found." : {
            'es' :
            "No se encontraron datos",
            'fr' :
            "Aucune donn�e trouv�e.",
        },
        "No locale was specified." : {
            'es' :
            "Un locale no se ha especificado",
            'fr' :
            "Aucuns param�tres r�gionaux sp�cifi�s.",
        },
        "No more existing examples found." : {
            'es' :
            "No se ha encontrado m�s ejemplos existentes",
            'fr' :
            "Il n'y a plus d'exemples trouv�s.",
        },
        "No more possible abbreviations found." : {
            'es' :
            "No se ha encontrado m�s abreviaturas posibles",
            'fr' :
            "On ne trouve plus des abr�viations possibles.",
        },
        "No more reference numbers found." : {
            'es' :
            "No se ha encontrado m�s n�meros de referencia",
            'fr' :
            "On ne trouve plus des num�ros de r�f�rence.",
        },
        "No more reference numbers found.\n Make sure to type # in front." : {
            'es' :
            "No se encontraron m�s n�meros de referencia. \n Aseg�rese de "
            "escribir # delante.",
            'fr' :
            "On ne trouve plus des num�ros de r�f�rence. Il faut v�rifier "
            "le # devant des num�ros.",
        },
        "No scope was specified." : {
            'es' :
            "No se especific� ning�n �mbito.",
            'fr' :
            "Aucune �tendue n��tait sp�cifi�e",
        },
        "No SF markers were specified.  Continue anyway?" : {
            'es' :
            "Ning�n marcadores SFM fueron especificados.  �Desea continuar?",
            'fr' :
            "Aucune balise SFM sp�cifi�e.  Continuer quand m�me?",
        },
        "No spreadsheet is open." : {
            'es' :
            "No hay ninguna hoja de c�lculo abierto.",
            'fr' :
            "Aucun classeur est ouvert.",
        },
        "No task was specified." : {
            'es' :
            "No se especific� ninguna tarea.",
            'fr' :
            "Aucune t�che n��tait sp�cifi�e",
        },
        "No writing systems found." : {
            'es' :
            "No se encontraron sistemas de escritura.",
            'fr' :
            "Aucune syst�mes d'�criture trouv�e.",
        },
        "No Xpath expressions were specified.  Continue anyway?" : {
            'es' :
            "Ning�n expresiones XPath fueron especificadas.  "
            "�Desea continuar?",
            'fr' :
            "Aucune expression Xpath sp�cifi�e.  Continuer quand m�me?",
        },
        "No text is selected." : {
            'es' :
            "No hay texto seleccionado.",
            'fr' :
            "Aucun texte s�lectionn�.",
        },
        "Paragraph style '%s' is missing" : {
            'es' :
            "No se encuentra el estilo de p�rrafo '%s'",
            'fr' :
            "Style de paragraphe '%s' introuvable",
        },
        "Please add a file to get words." : {
            'es' :
            "Por favor, a�ada un archivo para obtener las palabras.",
            'fr' :
            "Veuillez ajouter un fichier duquel on peut obtenir des mots.",
        },
        "Please add files to scan." : {
            'es' :
            "Por favor, agregue archivos para escanear.",
            'fr' :
            "Veuillez ajouter des fichiers � analyser.",
        },
        "Please do not select individual table cells." : {
            'es' :
            "Por favor, no seleccione las celdas individuales de la tabla.",
            'fr' :
            "Veuillez ne pas choisir des cellules individuelles.",
        },
        "Please enter a number for max length." : {
            'es' :
            "Por favor, introduzca un n�mero para la longitud m�xima.",
            'fr' :
            "Veuillez entrer la longueur maximum.",
        },
        "Please enter a ref number." : {
            'es' :
            "Por favor, introduzca un n�mero de referencia.",
            'fr' :
            "Veuillez entrer un num�ro de r�f�rence.",
        },
        "Please enter a value for column width." : {
            'es' :
            "Por favor, introduzca un valor para el ancho de la columna.",
            'fr' :
            "Veuillez entrer la largeur de colonne.",
        },
        "Please go to Interlinear Settings and specify a file." : {
            'es' :
            "Por favor, vaya a la Configuraci�n interlineal y especifique "
            "un archivo.",
            'fr' :
            "Veuillez choisir un fichier dans Configuration interlin�aire.",
        },
        "Please go to Phonology Settings and specify a file." : {
            'es' :
            "Por favor, vaya a la Configuraci�n de fonolog�a y especifique "
            "un archivo.",
            'fr' :
            "Veuillez sp�cifier un fichier dans Configuration de phonologie.",
        },
        "Please load a word list by clicking on the Files... button.  When "
        "file settings are finished, click Get words." : {
            'es' :
            "Por favor, cargue una lista de palabras haciendo clic en el "
            "bot�n Archivos.  Cuando la configuraci�n de archivo se haya "
            "terminado, haga clic en Obtener palabras.",
            'fr' :
            "Veuillez charger une liste de mots en cliquant sur Fichiers...  "
            "Apr�s avoir fait la configuration de fichier",
        },
        "Please save the current document first." : {
            'es' :
            "Por favor, primero guarde el documento actual.",
            'fr' :
            "Veuillez enregistrer d'abord le document actuel.",
        },
        "Please save the spreadsheet first." : {
            'es' :
            "Por favor, primero guarde la hoja de c�lculo.",
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
            "Veuillez s�lectionner un nom de langue.",
        },
        "Please select a scope character style." : {
            'es' :
            "Por favor, seleccione un estilo de car�cter �mbito.",
            'fr' :
            "Veuillez choisir un style de caract�re pour l'�tendue.",
        },
        "Please select a scope font." : {
            'es' :
            "Por favor, seleccione una fuente �mbito.",
            'fr' :
            "Veuillez choisir une police pour l'�tendue.",
        },
        "Please select a paragraph style." : {
            'es' :
            "Por favor, seleccione un estilo de p�rrafo.",
            'fr' :
            "Veuillez choisir un style de paragraphe.",
        },
        "Please select a scope paragraph style." : {
            'es' :
            "Por favor, seleccione un estilo de p�rrafo �mbito.",
            'fr' :
            "Veuillez choisir un style de paragraphe pour l'�tendue.",
        },
        "Please select a script." : {
            'es' :
            "Por favor, seleccione un script.",
            'fr' :
            "Veuillez choisir un �criture.",
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
            "Veuillez choisir une abr�viation dans la liste.",
        },
        "Please select an item in the list." : {
            'es' :
            "Por favor, seleccione un elemento de la lista.",
            'fr' :
            "Veuillez choisir un �l�ment dans la liste.",
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
            "Veuillez s�lectionner ou saisir quelque chose � rechercher.",
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
            "Veuillez sp�cifier les balises (SFMs).",
        },
        "Please specify a file to export." : {
            'es' :
            "Por favor, especifique un archivo para exportar.",
            'fr' :
            "Veuillez sp�cifier un fichier � exporter.",
        },
        "Please specify a scope." : {
            'es' :
            "Por favor, especifique un �mbito.",
            'fr' :
            "Veuillez sp�cifier l'�tendue.",
        },
        "Please specify a target." : {
            'es' :
            "Por favor, especifique un destino.",
            'fr' :
            "Veuillez sp�cifier un cible.",
        },
        "Please specify a word list file.  To make a new empty list, go to "
        "Word List and Spelling and then save the spreadsheet file." : {
            'es' :
            "Por favor, especifique un archivo de una lista de palabras.  "
            "Para crear una nueva lista vac�a, vaya a Lista de palabras y "
            "ortograf�a y guarde el archivo de hoja de c�lculo.",
            'fr' :
            "Veuillez sp�cifier un fichier de liste de mots.  Pour cr�er une "
            "nouvelle liste vide, atteindre Liste de mots et orthographe, "
            "puis enregistrer le classeur.",
        },
        "Replaced %d example%s." : {
            'es' :
            "reemplazado %d ejemplo%s.",
            'fr' :
            "%d exemple%s a �t� remplas�.",
        },
        "Spell check finished." : {
            'es' :
            "Spell check finished.",
            'fr' :
            "V�rification d'orthographe termin�e.",
        },
        "Successfully finished conversion." : {
            'es' :
            "Terminado con �xito la conversi�n.",
            'fr' :
            "Conversion termin�e avec succ�s.",
        },
        "\n\nSuggestions\n%s" : {
            'es' :
            "\n\nSugerencias\n%s",
            'fr' :
            "\n\nSuggestions\n%s",
        },
        "The cursor cannot be in a header or footer." : {
            'es' :
            "El cursor no puede estar en un encabezado o en un pie de "
            "p�gina.",
            'fr' :
            "Le curseur ne peut pas se trouver dans un en-t�te ou dans un "
            "pied de page.",
        },
        "The cursor cannot be inside a table or frame." : {
            'es' :
            "El cursor no puede estar dentro de una tabla o un marco.",
            'fr' :
            "Le curseur ne peut pas se trouver dans un tableau ou dans un "
            "cadre.",
        },
        "The following Ref Numbers have duplicates: %s" : {
            'es' :
            "Los siguientes n�meros de referencia tienen duplicados: %s",
            'fr' :
            "Les num�ros de r�f�rence suivants ont des doublons: %s",
        },
        "There was a problem while writing the list.\n\n%s" : {
            'es' :
            "Hubo un problema al escribir la lista.\n\n%s",
            'fr' :
            "Un probl�me est survenu en �crivant la liste.\n\n%s",
        },
        "This document stores settings for %s.  "
        "Please leave it open while using %s.  "
        "If you want to keep the settings to use again later, "
        "then save this document." : {
            'es' :
            "Este documento guarda la configuraci�n de %s.  "
            "Por favor, dejarlo abierto durante el uso de %s.  "
            "Si desea mantener la configuraci�n para utilizarlo m�s "
            "adelante, guarde este documento.",
            'fr' :
            "Ce document contient la configuration de la fonction %s.  "
            "Veuillez le laisser ouvert en utilisant %s.  "
            "Pour garder la configuration afin de la r�utiliser plus tard, "
            "enregistrer ce document.",
        },
        "This expression is already in the list." : {
            'es' :
            "Esta expresi�n est� ya en la lista.",
            'fr' :
            "Cette expression est d�j� dans la liste.",
        },
        "This will change the case of the entire list from '%s' to '%s.' "
        "Continue?" : {
            'es' :
            "Esto cambiar� el caso de la lista completa de '%s' a '%s'.  "
            "�Desea continuar?",
            'fr' :
            "Ceci changera la casse de toute la liste de '%s' � '%s'.  "
            "Continuer?",
        },
        "This word was already set to correct.  Change anyway?" : {
            'es' :
            "Esta palabra ya estaba configurada para corregir. "
            "�Cambiar de todos modos?",
            'fr' :
            "Ce mot est d�j� r�gl� pour corriger. Modifier quand m�me?",
        },
        "To update examples, 'Outer table' must be marked in Interlinear "
        "Settings." : {
            'es' :
            "'Tabla de exterior' debe estar en la Configuraci�n "
            "interlineal.",
            'fr' :
            "'Cadre exterieur' doit �tre dans Configuration interlin�aire.",
        },
        "To use oxttools, the lxml python library must be installed." : {
            'es' :
            "Para usar oxttools, python lxml debe ser instalado.",
            'fr' :
            "Pour utiliser oxttools, python lxml doit �tre install�e.",
        },
        "Too many files named like %s." : {
            'es' :
            "Demasiados archivos con el nombre %s.",
            'fr' :
            "Trop de fichiers nomm�s comme %s.",
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
            "Comando de acci�n desconocido '%s'",
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
            "�Actualizar todos los ejemplos ahora?  Se recomienda que "
            "primero guarde una copia de su documento.",
            'fr' :
            "Actualiser tous les exemples maintenant?  Il est conseill� "
            "d'enregistrer le document d'abord.",
        },
        "Updated '%s' %d times in a row.  Keep going?" : {
            'es' :
            "Actualizado '%s' %d veces seguidas.  �Seguir adelante?",
            'fr' :
            "'%s' a �t� actualis� %d fois de suite.  Continuer?",
        },
        "Updated %d example%s." : {
            'es' :
            "Actualizado %d ejemplo%s.",
            'fr' :
            "%d exemple%s a �t� actualis�.",
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
            "La largeur de colonne doit �tre sup�rieure � z�ro.",
        },
        "'Whole Document' must be the only thing to find." : {
            'es' :
            "'Documento Completo' debe ser la �nica cosa para buscar.",
            'fr' :
            "'Document entier' doit �tre la seule chose � rechercher",
        },
        "Word failed to fit properly." : {
            'es' :
            "La palabra no se ajust� correctamente.",
            'fr' :
            "Le mot ne rentre pas correctement.",
        },
        "You did not make any changes to the word." : {
            'es' :
            "No hiciste ning�n cambio en la palabra.",
            'fr' :
            "Vous n'avez apport� aucun changement au mot.",
        },
        "You did not specify anything to find.  Continue anyway?" : {
            'es' :
            "No ha especificado nada que encontrar.  �Desea continuar?",
            'fr' :
            "Vous n'avez sp�cifier aucune chose � rechercher.  Continuer "
            "quand m�me?",
        },
    }

theLocale = Locale()
