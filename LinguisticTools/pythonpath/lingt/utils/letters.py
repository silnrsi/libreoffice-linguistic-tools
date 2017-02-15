# -*- coding: Latin-1 -*-
#
# This file created June 28 2011 by Jim Kornelsen
#
# 12-Aug-11 JDK  Added OTHER_KNOWN_CHARS.  LetterIndex only has one value.
# 07-Aug-15 JDK  Rename constants to all caps.
# 13-Aug-15 JDK  Alphabetize and update font lists.
# 18-Feb-16 JDK  Add getFontType().
# 22-Feb-16 JDK  Add Blocks class.  Move SCRIPT_LETTERS to its own module.
# 23-Feb-16 JDK  Fixed bug: Constants list did not compile when assimilated.

"""
Information about Unicode characters, scripts and fonts.
"""
import string
from lingt.utils import unicode_data

try:
    # verify that it is defined
    unichr
except NameError:
    # define it for Python 3
    unichr = chr


# Useful to look up the type of a letter.
# Types are "WI_Vowels", "DepVowels", "AnyVowels", "WI_Consonants",
# "WF_Consonants", "AnyConsonants",
LetterIndex = dict()
for script in unicode_data.SCRIPT_LETTERS:
    for lettertype in unicode_data.SCRIPT_LETTERS[script]:
        for code in unicode_data.SCRIPT_LETTERS[script][lettertype]:
            LetterIndex[code] = lettertype
for lettertype in unicode_data.OTHER_KNOWN_LETTERS:
    for code in unicode_data.OTHER_KNOWN_LETTERS[lettertype]:
        LetterIndex[code] = lettertype


# These values are used to strip punctuation and numbers from words.
PUNCTUATION = (
    [chr(i) for i in range(33, 47+1)] +
    [chr(i) for i in range(48, 57+1)] +               # digits
    [chr(i) for i in range(58, 64+1)] +
    [chr(i) for i in range(91, 96+1)] +
    [unichr(i) for i in range(0x2018, 0x201F)]) # smart quotes

VIRAMA = {
    "BENGALI": u"\u09CD",    # Halant
    "DEVANAGARI": u"\u094D",
    "GUJARATI": u"\u0ACD",
    "GURMUKHI": u"\u0A4D",
    "HEBREW": u"\u05B0",    # Sheva
    "KANNADA": u"\u0CCD",
    "MALAYALAM": u"\u0D4D",
    "ORIYA": u"\u0B4D",
    "TAMIL": u"\u0BCD",
    "TELUGU": u"\u0C4D",
    }


# The font lists below are compiled from several online lists.
# See for example:
#   https://en.wikipedia.org/wiki/
#       List_of_typefaces_included_with_Microsoft_Windows
#

LATIN_FONTS = [
    "Arial", "Arial Nova", "Calibri", "Calisto MT", "Cambria", "Candara",
    "Century Gothic", "Chicago", "Comic Sans MS", "Consolas", "Constantia",
    "Corbel", "Courier New", "Georgia", "Georgia Pro", "Gill Sans Nova",
    "Helvetica", "Impact", "Lucida Sans Unicode", "Microsoft Sans Serif",
    "Palatino", "Palatino Linotype", "Rockwell Nova", "Sitka Text",
    "Tahoma", "Times New Roman", "Trebuchet MS" "Verdana", "Westminster"]

SCRIPT_FONTS = {
    "ARABIC": [
        "AlBayan", "Andalus", "Arabic Transparent", "Arabic Typesettings",
        "Arial", "Baghdad", "Courier New", "DecoTypeNaskh",
        "Droid Arabic Naskh",
        "Estrangelo Edessa", "Geeza", "Geeza Pro",
        "KacstOne", "Kalimati", "Kalyani",
        "KufiStandard GK", "Microsoft Sans Serif", "Microsoft Uighur",
        "Nadeem", "Sakkal Majalla", "Scheherazade", "Simplified Arabic",
        "TAMu_Kadambri", "TAMu_Kalyani", "TAMu_Maduram", "TLArabic",
        "Tahoma", "Times New Roman", "Traditional Arabic",
        "Urdu Typesetting"],
    "ARMENIAN": [
        "Droid Sans Armenian", "JF Armenian Serif", "Mshtakan", "Sylfaen",
        "Times New Roman"],
    "BALINESE": [],
    "BAMUM": [],
    "BATAK": [],
    "BENGALI": [
        "Ani", "Jamrul", "Likhan", "Lohit Bengali",
        "Mitra Mono", "Mukti Narrow", "Shonar Bangla", "Vrinda"],
    "BOPOMOFO": [],
    "BUGINESE": [],
    "BUHID": [],
    "CHAM": [],
    "CHEROKEE": ["Gadugi", "Plantagenet Cherokee"],
    "COPTIC": ["Sinaiticus"],
    "CYRILLIC": LATIN_FONTS,
    "DEVANAGARI": [
        "Annapurna", "Aparajita", "CDAC-GIST Surekh", "Chandas",
        "Devanagari", "DevanagariMT", "Jana Hindi", "Kalimati", "Kokila",
        "Lohit Hindi", "Mangal", "Raavi", "Raghu8", "Samanata",
        "Sanskrit Text", "Saraswati5", "Ultsaah", "Xdvng", "Yogesh",
        "gargi"],
    "GEORGIAN": ["JF Georgian Contrast", "Sylfaen"],
    "GLAGOLITIC": [],
    "GREEK": LATIN_FONTS,
    "GUJARATI": [
        "Gujarati", "GujaratiMT", "Lohit Gujarati", "Rekha", "Saab",
        "Shruti", "aakar", "padmaa"],
    "GURMUKHI": ["Gurmukhi", "Lohit Punjabi", "Raavi"],
    "HANGUL": [
        "#Gungseouche", "#Pilgiche", "Apple Gothic", "AppleGothic",
        "Baekmuk Batang", "Baekmuk Dotum", "Baekmuk Gulim", "Batang",
        "BatangChe", "Dotum", "DotumChe", "Gulim", "GulimChe", "Gungsuh",
        "GungsuhChe", "GungSeo", "Hangangche", "Jung Gothic",
        "Malgun Gothic", "PCMyungjo", "PilGi", "Seoul", "Tae Graphic"],
    "HANUNOO": [],
    "HEBREW": [
        "Aharoni", "Arial", "Arial Hebrew", "ArialHB", "Corsiva",
        "Corsiva Hebrew", "Courier New", "David",
        "Droid Sans Hebrew", "Ezra SIL",
        "FrankRuehl", "Gisha", "Hebrew", "Levenim MT",
        "Lucida Sans Unicode", "Microsoft Sans Serif", "Miriam",
        "Narkisim", "New Peninim", "NewPeninimMT", "Raanana", "Rod",
        "Tahoma", "Times New Roman"],
    "HIRAGANA": [
        "AquaKanaRegular", "Droid Sans Japanese",
        "Hiragino Kaku Gothic Pro", "Kochi Mincho",
        "MS Gothic", "MS Mincho", "Meiryo", "Osaka", "Yu Gothic",
        "Yu Mincho"],
    "JAVANESE": [],
    "KANNADA": ["Kedage", "Mallig", "Tunga"],
    "KATAKANA": [
        "AquaKanaRegular", "Droid Sans Japanese",
        "Hiragino Kaku Gothic Pro", "Kochi Mincho",
        "MS Gothic", "MS Mincho", "Meiryo", "Osaka", "Yu Gothic",
        "Yu Mincho"],
    "KHMER": ["DaunPenh", "Khmer OS", "Khmer UI", "MoolBoran"],
    "LAO": ["DokChampa", "Lao UI", "Phetsarath OT"],
    "LATIN": LATIN_FONTS,
    "LEPCHA": [],
    "LIMBU": [],
    "LISU": [],
    "MALAYALAM": ["Kartika", "Lohit Malayalam", "Meera", "Rachana"],
    "MANDAIC": [],
    "MONGOLIAN": ["Mongolian Baiti"],
    "MYANMAR": ["Myanmar Text", "Padauk"],
    "NKO": ["Ebrima"],
    "OGHAM": [],
    "ORIYA": [
        "Kalinga", "Khondi", "Lohit Oriya", "Oriya", "Santali", "oriUni",
        "utkal"],
    "REJANG": [],
    "RUNIC": [],
    "SAMARITAN": [],
    "SAURASHTRA": [],
    "SINHALA": ["Iskoola Pota", "LKLUG"],
    "SUNDANESE": [],
    "SYRIAC": ["Extrangelo Edessa"],
    "TAGALOG": [],
    "TAGBANWA": [],
    "TAMIL": [
        "Inai Mathi", "InaiMathi", "JanaTamil", "Latha", "Lohit Tamil",
        "Tau Elango Barathi", "ThendraUni", "TheneeUni", "VaigaiUni",
        "Vijaya", "aAvarangal"],
    "TELUGU": [
        "Gautami", "Lohit Telugu", "Pothana2000", "Vani", "Vemana2000"],
    "THAANA": ["MV Boli"],
    "THAI": [
        "Angsana New", "AngsanaUPC", "Ayuthaya", "Browallia",
        "BrowalliaUPC", "Cordia New", "Dillenia", "DilleniaUPC",
        "Droid Sans Thai",
        "Eucrosia", "EucrosiaUPC", "Freesia", "FreesiaUPC", "Garuda",
        "IrisUPC", "JasmineUPC", "Jumpa", "Kinnari",
        "KodchiangUPC", "Krungthep",
        "Leelawadee", "Leelawadee UI", "LilyUPC", "Loma",
        "Microsoft Sans Serif", "Norasi", "Purisa", "Sathu",
        "Sawasdee", "Silom",
        "Tahoma", "Thonburi", "Tlwg Typist", "Umpush", "Waree"],
    "TIBETAN": ["Microsoft Himalaya"],
    "TIFINAGH": ["Ebrima"],
}

# For fonts that support a number of different scripts
FONT_SCRIPTS = {
    "Akshar Unicode" : [
        "DEVANAGARI", "KANNADA", "MALAYALAM", "TAMIL", "TELUGU"],
    "Arial Unicode MS" : [
        "ARABIC", "ARMENIAN", "CYRILLIC", "DEVANAGARI", "GEORGIAN",
        "GREEK", "GURMUKHI", "HEBREW", "HIRAGANA", "KANNADA", "HANGUL",
        "TAMIL", "THAI"],
    "DejaVu Serif" : [
        "ARABIC", "ARMENIAN", "CYRILLIC", "GREEK", "HEBREW", "LAO"],
    "Gentium" : ["CYRILLIC", "GREEK"],
    "FreeSerif" : [
        "BENGALI", "CYRILLIC", "GREEK", "DEVANAGARI", "GURMUKHI",
        "HEBREW", "HIRAGANA", "KATAKANA", "MALAYALAM", "TAMIL", "TELUGU",
        "THAANA", "THAI"],
    "Nirmala UI" : [
        "DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "ORIYA",
        "TAMIL", "TELEGU", "KANNADA", "MALAYALAM", "SINHALA"],
    "Segoe UI" : [
        "ARABIC", "ARMENIAN", "CYRILLIC", "GEORGIAN", "GREEK",
        "HEBREW", "LATIN", "LISU"],
    }


# CASE_CAPITALS and CASE_LOWER are generated by grab_case_pairs.pl,
# after grab_unicode_letters.py is run.
#
# They are in the same order, so for example the lowercase equivalent of
# CASE_CAPITALS[0] is CASE_LOWER[0].

CASE_CAPITALS = [
    u"\u0041", u"\u0042", u"\u0043", u"\u0044", u"\u0045", u"\u0046",
    u"\u0047", u"\u0048", u"\u0049", u"\u004A", u"\u004B", u"\u004C",
    u"\u004D", u"\u004E", u"\u004F", u"\u0050", u"\u0051", u"\u0052",
    u"\u0053", u"\u0054", u"\u0055", u"\u0056", u"\u0057", u"\u0058",
    u"\u0059", u"\u005A", u"\u00C6", u"\u00D0", u"\u00DE", u"\u014A",
    u"\u018F", u"\u0194", u"\u0196", u"\u01A2", u"\u01A9", u"\u01B1",
    u"\u01B7", u"\u01F6", u"\u01F7", u"\u021C", u"\u0222", u"\u0370",
    u"\u0391", u"\u0392", u"\u0393", u"\u0394", u"\u0395", u"\u0396",
    u"\u0397", u"\u0398", u"\u0399", u"\u039A", u"\u039B", u"\u039C",
    u"\u039D", u"\u039E", u"\u039F", u"\u03A0", u"\u03A1", u"\u03A3",
    u"\u03A4", u"\u03A5", u"\u03A6", u"\u03A7", u"\u03A8", u"\u03A9",
    u"\u03E2", u"\u03E4", u"\u03E6", u"\u03E8", u"\u03EA", u"\u03EC",
    u"\u03EE", u"\u03F7", u"\u03FA", u"\u0401", u"\u0402", u"\u0403",
    u"\u0405", u"\u0407", u"\u0408", u"\u0409", u"\u040A", u"\u040B",
    u"\u040C", u"\u040F", u"\u0410", u"\u0411", u"\u0412", u"\u0413",
    u"\u0414", u"\u0415", u"\u0416", u"\u0417", u"\u0418", u"\u041A",
    u"\u041B", u"\u041C", u"\u041D", u"\u041E", u"\u041F", u"\u0420",
    u"\u0421", u"\u0422", u"\u0423", u"\u0424", u"\u0425", u"\u0426",
    u"\u0427", u"\u0428", u"\u0429", u"\u042B", u"\u042D", u"\u042E",
    u"\u042F", u"\u0460", u"\u0462", u"\u046E", u"\u0470", u"\u0472",
    u"\u0474", u"\u0478", u"\u047E", u"\u0480", u"\u04BA", u"\u04D8",
    u"\u0514", u"\u0516", u"\u0518", u"\u051A", u"\u051C", u"\u0531",
    u"\u0532", u"\u0533", u"\u0534", u"\u0535", u"\u0536", u"\u0537",
    u"\u0538", u"\u0539", u"\u053A", u"\u053B", u"\u053C", u"\u053D",
    u"\u053E", u"\u053F", u"\u0540", u"\u0541", u"\u0542", u"\u0543",
    u"\u0544", u"\u0545", u"\u0546", u"\u0547", u"\u0548", u"\u0549",
    u"\u054A", u"\u054B", u"\u054C", u"\u054D", u"\u054E", u"\u054F",
    u"\u0550", u"\u0551", u"\u0552", u"\u0553", u"\u0554", u"\u0555",
    u"\u0556", u"\u10A0", u"\u10A1", u"\u10A2", u"\u10A3", u"\u10A4",
    u"\u10A5", u"\u10A6", u"\u10A7", u"\u10A8", u"\u10A9", u"\u10AA",
    u"\u10AB", u"\u10AC", u"\u10AD", u"\u10AE", u"\u10AF", u"\u10B0",
    u"\u10B1", u"\u10B2", u"\u10B3", u"\u10B4", u"\u10B5", u"\u10B6",
    u"\u10B7", u"\u10B8", u"\u10B9", u"\u10BA", u"\u10BB", u"\u10BC",
    u"\u10BD", u"\u10BE", u"\u10BF", u"\u10C0", u"\u10C1", u"\u10C2",
    u"\u10C3", u"\u10C4", u"\u10C5", u"\u2C00", u"\u2C01", u"\u2C02",
    u"\u2C03", u"\u2C04", u"\u2C05", u"\u2C06", u"\u2C07", u"\u2C08",
    u"\u2C09", u"\u2C0B", u"\u2C0C", u"\u2C0D", u"\u2C0E", u"\u2C0F",
    u"\u2C10", u"\u2C11", u"\u2C12", u"\u2C13", u"\u2C14", u"\u2C15",
    u"\u2C16", u"\u2C17", u"\u2C18", u"\u2C19", u"\u2C1A", u"\u2C1B",
    u"\u2C1C", u"\u2C1D", u"\u2C1E", u"\u2C1F", u"\u2C20", u"\u2C21",
    u"\u2C23", u"\u2C26", u"\u2C2A", u"\u2C2B", u"\u2C2C", u"\u2C6D",
    u"\u2C80", u"\u2C82", u"\u2C84", u"\u2C86", u"\u2C88", u"\u2C8A",
    u"\u2C8C", u"\u2C8E", u"\u2C90", u"\u2C92", u"\u2C94", u"\u2C96",
    u"\u2C98", u"\u2C9A", u"\u2C9C", u"\u2C9E", u"\u2CA0", u"\u2CA2",
    u"\u2CA4", u"\u2CA6", u"\u2CA8", u"\u2CAA", u"\u2CAC", u"\u2CAE",
    u"\u2CB0", u"\u2CC0", u"\uA640", u"\uA642", u"\uA646", u"\uA648",
    u"\uA65E", u"\uA680", u"\uA682", u"\uA684", u"\uA686", u"\uA688",
    u"\uA68C", u"\uA68E", u"\uA690", u"\uA692", u"\uA694", u"\uA696",
    u"\uA726", u"\uA728", u"\uA72A", u"\uA72C", u"\uA732", u"\uA734",
    u"\uA736", u"\uA738", u"\uA73C", u"\uA74E", u"\uA760", u"\uA768",
    u"\uA76A", u"\uA76C", u"\uA76E", u"\uA78B"]


CASE_LOWER = [
    u"\u0061", u"\u0062", u"\u0063", u"\u0064", u"\u0065", u"\u0066",
    u"\u0067", u"\u0068", u"\u0069", u"\u006A", u"\u006B", u"\u006C",
    u"\u006D", u"\u006E", u"\u006F", u"\u0070", u"\u0071", u"\u0072",
    u"\u0073", u"\u0074", u"\u0075", u"\u0076", u"\u0077", u"\u0078",
    u"\u0079", u"\u007A", u"\u00E6", u"\u00F0", u"\u00FE", u"\u014B",
    u"\u0259", u"\u0263", u"\u0269", u"\u01A3", u"\u0283", u"\u028A",
    u"\u0292", u"\u0195", u"\u01BF", u"\u021D", u"\u0223", u"\u0371",
    u"\u03B1", u"\u03B2", u"\u03B3", u"\u03B4", u"\u03B5", u"\u03B6",
    u"\u03B7", u"\u03B8", u"\u03B9", u"\u03BA", u"\u03BB", u"\u03BC",
    u"\u03BD", u"\u03BE", u"\u03BF", u"\u03C0", u"\u03C1", u"\u03C3",
    u"\u03C4", u"\u03C5", u"\u03C6", u"\u03C7", u"\u03C8", u"\u03C9",
    u"\u03E3", u"\u03E5", u"\u03E7", u"\u03E9", u"\u03EB", u"\u03ED",
    u"\u03EF", u"\u03F8", u"\u03FB", u"\u0451", u"\u0452", u"\u0453",
    u"\u0455", u"\u0457", u"\u0458", u"\u0459", u"\u045A", u"\u045B",
    u"\u045C", u"\u045F", u"\u0430", u"\u0431", u"\u0432", u"\u0433",
    u"\u0434", u"\u0435", u"\u0436", u"\u0437", u"\u0438", u"\u043A",
    u"\u043B", u"\u043C", u"\u043D", u"\u043E", u"\u043F", u"\u0440",
    u"\u0441", u"\u0442", u"\u0443", u"\u0444", u"\u0445", u"\u0446",
    u"\u0447", u"\u0448", u"\u0449", u"\u044B", u"\u044D", u"\u044E",
    u"\u044F", u"\u0461", u"\u0463", u"\u046F", u"\u0471", u"\u0473",
    u"\u0475", u"\u0479", u"\u047F", u"\u0481", u"\u04BB", u"\u04D9",
    u"\u0515", u"\u0517", u"\u0519", u"\u051B", u"\u051D", u"\u0561",
    u"\u0562", u"\u0563", u"\u0564", u"\u0565", u"\u0566", u"\u0567",
    u"\u0568", u"\u0569", u"\u056A", u"\u056B", u"\u056C", u"\u056D",
    u"\u056E", u"\u056F", u"\u0570", u"\u0571", u"\u0572", u"\u0573",
    u"\u0574", u"\u0575", u"\u0576", u"\u0577", u"\u0578", u"\u0579",
    u"\u057A", u"\u057B", u"\u057C", u"\u057D", u"\u057E", u"\u057F",
    u"\u0580", u"\u0581", u"\u0582", u"\u0583", u"\u0584", u"\u0585",
    u"\u0586", u"\u2D00", u"\u2D01", u"\u2D02", u"\u2D03", u"\u2D04",
    u"\u2D05", u"\u2D06", u"\u2D07", u"\u2D08", u"\u2D09", u"\u2D0A",
    u"\u2D0B", u"\u2D0C", u"\u2D0D", u"\u2D0E", u"\u2D0F", u"\u2D10",
    u"\u2D11", u"\u2D12", u"\u2D13", u"\u2D14", u"\u2D15", u"\u2D16",
    u"\u2D17", u"\u2D18", u"\u2D19", u"\u2D1A", u"\u2D1B", u"\u2D1C",
    u"\u2D1D", u"\u2D1E", u"\u2D1F", u"\u2D20", u"\u2D21", u"\u2D22",
    u"\u2D23", u"\u2D24", u"\u2D25", u"\u2C30", u"\u2C31", u"\u2C32",
    u"\u2C33", u"\u2C34", u"\u2C35", u"\u2C36", u"\u2C37", u"\u2C38",
    u"\u2C39", u"\u2C3B", u"\u2C3C", u"\u2C3D", u"\u2C3E", u"\u2C3F",
    u"\u2C40", u"\u2C41", u"\u2C42", u"\u2C43", u"\u2C44", u"\u2C45",
    u"\u2C46", u"\u2C47", u"\u2C48", u"\u2C49", u"\u2C4A", u"\u2C4B",
    u"\u2C4C", u"\u2C4D", u"\u2C4E", u"\u2C4F", u"\u2C50", u"\u2C51",
    u"\u2C53", u"\u2C56", u"\u2C5A", u"\u2C5B", u"\u2C5C", u"\u0251",
    u"\u2C81", u"\u2C83", u"\u2C85", u"\u2C87", u"\u2C89", u"\u2C8B",
    u"\u2C8D", u"\u2C8F", u"\u2C91", u"\u2C93", u"\u2C95", u"\u2C97",
    u"\u2C99", u"\u2C9B", u"\u2C9D", u"\u2C9F", u"\u2CA1", u"\u2CA3",
    u"\u2CA5", u"\u2CA7", u"\u2CA9", u"\u2CAB", u"\u2CAD", u"\u2CAF",
    u"\u2CB1", u"\u2CC1", u"\uA641", u"\uA643", u"\uA647", u"\uA649",
    u"\uA65F", u"\uA681", u"\uA683", u"\uA685", u"\uA687", u"\uA689",
    u"\uA68D", u"\uA68F", u"\uA691", u"\uA693", u"\uA695", u"\uA697",
    u"\uA727", u"\uA729", u"\uA72B", u"\uA72D", u"\uA733", u"\uA735",
    u"\uA737", u"\uA739", u"\uA73D", u"\uA74F", u"\uA761", u"\uA769",
    u"\uA76B", u"\uA76D", u"\uA76F", u"\uA78C"]


# Blocks are either Standard ("Western"), Complex Text Layout (CTL),
# or Chinese/Japanese/Korean (CJK also known as "Asian").
# Punctuation can be used for all types so it does not determine the type,
# but it can be considered Standard if it is the only type in a string.
TYPE_INDETERMINATE = 0
TYPE_STANDARD = 1
TYPE_COMPLEX = 2
TYPE_CJK = 3

def getFontType(c, adjacentCharType=None):
    """Get the font type of the given character.
    :param c: the character to check
    :param adjacentCharType: type of surrounding characters

    Note: Looking up all strings in a document might be slow,
    but it is O(n) running time, so hopefully it shouldn't take too long.
    """
    if c.isspace() or c.isdigit() or c in string.punctuation:
        if adjacentCharType:
            return adjacentCharType
        else:
            return TYPE_INDETERMINATE
    for startChar, endChar, fontType in FONT_TYPE_BLOCKS:
        if startChar < c < endChar:
            return fontType
    return TYPE_STANDARD

# These code points are manually derived from the Unicode database file
# Blocks.txt, and the types are a best guess.
FONT_TYPE_BLOCKS = [
    (u"\u0000", u"\u007F", TYPE_STANDARD), # Basic Latin
    (u"\u0080", u"\u00FF", TYPE_STANDARD), # Latin-1 Supplement
    (u"\u0100", u"\u017F", TYPE_STANDARD), # Latin Extended-A
    (u"\u0180", u"\u024F", TYPE_STANDARD), # Latin Extended-B
    (u"\u0250", u"\u02AF", TYPE_STANDARD), # IPA Extensions
    (u"\u02B0", u"\u02FF", TYPE_STANDARD), # Spacing Modifier Letters
    (u"\u0300", u"\u036F", TYPE_STANDARD), # Combining Diacritical Marks
    (u"\u0370", u"\u03FF", TYPE_STANDARD), # Greek and Coptic
    (u"\u0400", u"\u04FF", TYPE_STANDARD), # Cyrillic
    (u"\u0500", u"\u052F", TYPE_STANDARD), # Cyrillic Supplement
    (u"\u0530", u"\u058F", TYPE_STANDARD), # Armenian
    (u"\u0590", u"\u05FF", TYPE_COMPLEX), # Hebrew
    (u"\u0600", u"\u06FF", TYPE_COMPLEX), # Arabic
    (u"\u0700", u"\u074F", TYPE_STANDARD), # Syriac
    (u"\u0750", u"\u077F", TYPE_COMPLEX), # Arabic Supplement
    (u"\u0780", u"\u07BF", TYPE_STANDARD), # Thaana
    (u"\u07C0", u"\u07FF", TYPE_STANDARD), # NKo
    (u"\u0800", u"\u083F", TYPE_STANDARD), # Samaritan
    (u"\u0840", u"\u085F", TYPE_STANDARD), # Mandaic
    (u"\u08A0", u"\u08FF", TYPE_COMPLEX), # Arabic Extended-A
    (u"\u0900", u"\u097F", TYPE_COMPLEX), # Devanagari
    (u"\u0980", u"\u09FF", TYPE_COMPLEX), # Bengali
    (u"\u0A00", u"\u0A7F", TYPE_COMPLEX), # Gurmukhi
    (u"\u0A80", u"\u0AFF", TYPE_COMPLEX), # Gujarati
    (u"\u0B00", u"\u0B7F", TYPE_COMPLEX), # Oriya
    (u"\u0B80", u"\u0BFF", TYPE_COMPLEX), # Tamil
    (u"\u0C00", u"\u0C7F", TYPE_COMPLEX), # Telugu
    (u"\u0C80", u"\u0CFF", TYPE_COMPLEX), # Kannada
    (u"\u0D00", u"\u0D7F", TYPE_COMPLEX), # Malayalam
    (u"\u0D80", u"\u0DFF", TYPE_COMPLEX), # Sinhala
    (u"\u0E00", u"\u0E7F", TYPE_COMPLEX), # Thai
    (u"\u0E80", u"\u0EFF", TYPE_COMPLEX), # Lao
    (u"\u0F00", u"\u0FFF", TYPE_COMPLEX), # Tibetan
    (u"\u1000", u"\u109F", TYPE_COMPLEX), # Myanmar
    (u"\u10A0", u"\u10FF", TYPE_STANDARD), # Georgian
    (u"\u1100", u"\u11FF", TYPE_STANDARD), # Hangul Jamo
    (u"\u1200", u"\u137F", TYPE_STANDARD), # Ethiopic
    (u"\u1380", u"\u139F", TYPE_STANDARD), # Ethiopic Supplement
    (u"\u13A0", u"\u13FF", TYPE_STANDARD), # Cherokee
    (u"\u1400", u"\u167F", TYPE_STANDARD), # Canadian Aboriginal Syllabics
    (u"\u1680", u"\u169F", TYPE_STANDARD), # Ogham
    (u"\u16A0", u"\u16FF", TYPE_STANDARD), # Runic
    (u"\u1700", u"\u171F", TYPE_STANDARD), # Tagalog
    (u"\u1720", u"\u173F", TYPE_STANDARD), # Hanunoo
    (u"\u1740", u"\u175F", TYPE_STANDARD), # Buhid
    (u"\u1760", u"\u177F", TYPE_STANDARD), # Tagbanwa
    (u"\u1780", u"\u17FF", TYPE_COMPLEX), # Khmer
    (u"\u1800", u"\u18AF", TYPE_COMPLEX), # Mongolian
    (u"\u18B0", u"\u18FF", TYPE_STANDARD), # Canadian Aboriginal Syll. Ext.
    (u"\u1900", u"\u194F", TYPE_STANDARD), # Limbu
    (u"\u1950", u"\u197F", TYPE_STANDARD), # Tai Le
    (u"\u1980", u"\u19DF", TYPE_STANDARD), # New Tai Lue
    (u"\u19E0", u"\u19FF", TYPE_COMPLEX), # Khmer Symbols
    (u"\u1A00", u"\u1A1F", TYPE_STANDARD), # Buginese
    (u"\u1A20", u"\u1AAF", TYPE_STANDARD), # Tai Tham
    (u"\u1AB0", u"\u1AFF", TYPE_STANDARD), # Combining Diacritic Marks Ext.
    (u"\u1B00", u"\u1B7F", TYPE_STANDARD), # Balinese
    (u"\u1B80", u"\u1BBF", TYPE_STANDARD), # Sundanese
    (u"\u1BC0", u"\u1BFF", TYPE_STANDARD), # Batak
    (u"\u1C00", u"\u1C4F", TYPE_STANDARD), # Lepcha
    (u"\u1C50", u"\u1C7F", TYPE_STANDARD), # Ol Chiki
    (u"\u1CC0", u"\u1CCF", TYPE_STANDARD), # Sundanese Supplement
    (u"\u1CD0", u"\u1CFF", TYPE_STANDARD), # Vedic Extensions
    (u"\u1D00", u"\u1D7F", TYPE_STANDARD), # Phonetic Extensions
    (u"\u1D80", u"\u1DBF", TYPE_STANDARD), # Phonetic Extensions Supplement
    (u"\u1DC0", u"\u1DFF", TYPE_STANDARD), # Combining Diacritic Marks Supp
    (u"\u1E00", u"\u1EFF", TYPE_STANDARD), # Latin Extended Additional
    (u"\u1F00", u"\u1FFF", TYPE_STANDARD), # Greek Extended
    (u"\u2000", u"\u206F", TYPE_STANDARD), # General Punctuation
    (u"\u2070", u"\u209F", TYPE_STANDARD), # Superscripts and Subscripts
    (u"\u20A0", u"\u20CF", TYPE_STANDARD), # Currency Symbols
    (u"\u20D0", u"\u20FF", TYPE_STANDARD), # Combining Marks for Symbols
    (u"\u2100", u"\u214F", TYPE_STANDARD), # Letterlike Symbols
    (u"\u2150", u"\u218F", TYPE_STANDARD), # Number Forms
    (u"\u2190", u"\u21FF", TYPE_STANDARD), # Arrows
    (u"\u2200", u"\u22FF", TYPE_STANDARD), # Mathematical Operators
    (u"\u2300", u"\u23FF", TYPE_STANDARD), # Miscellaneous Technical
    (u"\u2400", u"\u243F", TYPE_STANDARD), # Control Pictures
    (u"\u2440", u"\u245F", TYPE_STANDARD), # Optical Character Recognition
    (u"\u2460", u"\u24FF", TYPE_STANDARD), # Enclosed Alphanumerics
    (u"\u2500", u"\u257F", TYPE_STANDARD), # Box Drawing
    (u"\u2580", u"\u259F", TYPE_STANDARD), # Block Elements
    (u"\u25A0", u"\u25FF", TYPE_STANDARD), # Geometric Shapes
    (u"\u2600", u"\u26FF", TYPE_STANDARD), # Miscellaneous Symbols
    (u"\u2700", u"\u27BF", TYPE_STANDARD), # Dingbats
    (u"\u27C0", u"\u27EF", TYPE_STANDARD), # Miscellaneous Math Symbols-A
    (u"\u27F0", u"\u27FF", TYPE_STANDARD), # Supplemental Arrows-A
    (u"\u2800", u"\u28FF", TYPE_STANDARD), # Braille Patterns
    (u"\u2900", u"\u297F", TYPE_STANDARD), # Supplemental Arrows-B
    (u"\u2980", u"\u29FF", TYPE_STANDARD), # Miscellaneous Math Symbols-B
    (u"\u2A00", u"\u2AFF", TYPE_STANDARD), # Supplemental Math Operators
    (u"\u2B00", u"\u2BFF", TYPE_STANDARD), # Misc Symbols and Arrows
    (u"\u2C00", u"\u2C5F", TYPE_STANDARD), # Glagolitic
    (u"\u2C60", u"\u2C7F", TYPE_STANDARD), # Latin Extended-C
    (u"\u2C80", u"\u2CFF", TYPE_STANDARD), # Coptic
    (u"\u2D00", u"\u2D2F", TYPE_STANDARD), # Georgian Supplement
    (u"\u2D30", u"\u2D7F", TYPE_STANDARD), # Tifinagh
    (u"\u2D80", u"\u2DDF", TYPE_STANDARD), # Ethiopic Extended
    (u"\u2DE0", u"\u2DFF", TYPE_STANDARD), # Cyrillic Extended-A
    (u"\u2E00", u"\u2E7F", TYPE_STANDARD), # Supplemental Punctuation
    (u"\u2E80", u"\u2EFF", TYPE_CJK), # CJK Radicals Supplement
    (u"\u2F00", u"\u2FDF", TYPE_STANDARD), # Kangxi Radicals
    (u"\u2FF0", u"\u2FFF", TYPE_STANDARD), # Ideographic Description Chars
    (u"\u3000", u"\u303F", TYPE_CJK), # CJK Symbols and Punctuation
    (u"\u3040", u"\u309F", TYPE_CJK), # Hiragana
    (u"\u30A0", u"\u30FF", TYPE_CJK), # Katakana
    (u"\u3100", u"\u312F", TYPE_STANDARD), # Bopomofo
    (u"\u3130", u"\u318F", TYPE_CJK), # Hangul Compatibility Jamo
    (u"\u3190", u"\u319F", TYPE_STANDARD), # Kanbun
    (u"\u31A0", u"\u31BF", TYPE_STANDARD), # Bopomofo Extended
    (u"\u31C0", u"\u31EF", TYPE_CJK), # CJK Strokes
    (u"\u31F0", u"\u31FF", TYPE_STANDARD), # Katakana Phonetic Extensions
    (u"\u3200", u"\u32FF", TYPE_CJK), # Enclosed CJK Letters & Months
    (u"\u3300", u"\u33FF", TYPE_CJK), # CJK Compatibility
    (u"\u3400", u"\u4DBF", TYPE_CJK), # CJK Unified Ideographs Ext A
    (u"\u4DC0", u"\u4DFF", TYPE_CJK), # Yijing Hexagram Symbols
    (u"\u4E00", u"\u9FFF", TYPE_CJK), # CJK Unified Ideographs
    (u"\uA000", u"\uA48F", TYPE_CJK), # Yi Syllables
    (u"\uA490", u"\uA4CF", TYPE_CJK), # Yi Radicals
    (u"\uA4D0", u"\uA4FF", TYPE_STANDARD), # Lisu
    (u"\uA500", u"\uA63F", TYPE_STANDARD), # Vai
    (u"\uA640", u"\uA69F", TYPE_STANDARD), # Cyrillic Extended-B
    (u"\uA6A0", u"\uA6FF", TYPE_STANDARD), # Bamum
    (u"\uA700", u"\uA71F", TYPE_STANDARD), # Modifier Tone Letters
    (u"\uA720", u"\uA7FF", TYPE_STANDARD), # Latin Extended-D
    (u"\uA800", u"\uA82F", TYPE_STANDARD), # Syloti Nagri
    (u"\uA830", u"\uA83F", TYPE_COMPLEX), # Common Indic Number Forms
    (u"\uA840", u"\uA87F", TYPE_STANDARD), # Phags-pa
    (u"\uA880", u"\uA8DF", TYPE_STANDARD), # Saurashtra
    (u"\uA8E0", u"\uA8FF", TYPE_COMPLEX), # Devanagari Extended
    (u"\uA900", u"\uA92F", TYPE_STANDARD), # Kayah Li
    (u"\uA930", u"\uA95F", TYPE_STANDARD), # Rejang
    (u"\uA960", u"\uA97F", TYPE_CJK), # Hangul Jamo Extended-A
    (u"\uA980", u"\uA9DF", TYPE_STANDARD), # Javanese
    (u"\uA9E0", u"\uA9FF", TYPE_COMPLEX), # Myanmar Extended-B
    (u"\uAA00", u"\uAA5F", TYPE_STANDARD), # Cham
    (u"\uAA60", u"\uAA7F", TYPE_COMPLEX), # Myanmar Extended-A
    (u"\uAA80", u"\uAADF", TYPE_STANDARD), # Tai Viet
    (u"\uAAE0", u"\uAAFF", TYPE_STANDARD), # Meetei Mayek Extensions
    (u"\uAB00", u"\uAB2F", TYPE_STANDARD), # Ethiopic Extended-A
    (u"\uAB30", u"\uAB6F", TYPE_STANDARD), # Latin Extended-E
    (u"\uAB70", u"\uABBF", TYPE_STANDARD), # Cherokee Supplement
    (u"\uABC0", u"\uABFF", TYPE_STANDARD), # Meetei Mayek
    (u"\uAC00", u"\uD7AF", TYPE_CJK), # Hangul Syllables
    (u"\uD7B0", u"\uD7FF", TYPE_CJK), # Hangul Jamo Extended-B
    (u"\uD800", u"\uDB7F", TYPE_STANDARD), # High Surrogates
    (u"\uDB80", u"\uDBFF", TYPE_STANDARD), # High Private Use Surrogates
    (u"\uDC00", u"\uDFFF", TYPE_STANDARD), # Low Surrogates
    (u"\uE000", u"\uF8FF", TYPE_STANDARD), # Private Use Area
    (u"\uF900", u"\uFAFF", TYPE_CJK), # CJK Compatibility Ideographs
    (u"\uFB00", u"\uFB4F", TYPE_STANDARD), # Alphabetic Presentation Forms
    (u"\uFB50", u"\uFDFF", TYPE_COMPLEX), # Arabic Presentation Forms-A
    (u"\uFE00", u"\uFE0F", TYPE_STANDARD), # Variation Selectors
    (u"\uFE10", u"\uFE1F", TYPE_STANDARD), # Vertical Forms
    (u"\uFE20", u"\uFE2F", TYPE_STANDARD), # Combining Half Marks
    (u"\uFE30", u"\uFE4F", TYPE_CJK), # CJK Compatibility Forms
    (u"\uFE50", u"\uFE6F", TYPE_STANDARD), # Small Form Variants
    (u"\uFE70", u"\uFEFF", TYPE_COMPLEX), # Arabic Presentation Forms-B
    (u"\uFF00", u"\uFFEF", TYPE_STANDARD), # Halfwidth and Fullwidth Forms
    (u"\uFFF0", u"\uFFFF", TYPE_STANDARD), # Specials
    ]
