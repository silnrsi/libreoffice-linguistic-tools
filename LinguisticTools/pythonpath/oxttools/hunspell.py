
import codecs
import unicodedata
import itertools

def decompose(s) :
    return "".join([unichr(int(x, 16)) for x in unicodedata.decomposition(s).split()])
    

class Hunspell(object) :

    def __init__(self, name, puncs="") :
        self.name = name
        self.words = set()
        self.affix = ""
        self.chars = set()
        self.ignore = set()
        self.puncs = puncs

    def addword(self, word) :
        if len(word) :
            line = unicodedata.normalize('NFC', word)
            for dat in line.split() :  # no phrases, just words
                self.words.add(dat)
                i = 0
                while i < len(dat) :
                    c = dat[i]
                    while i+1 < len(dat) and unicodedata.combining(dat[i+1]) :
                        i += 1
                        c += dat[i]
                    if ord(c[0]) > 128 or unicodedata.category(c[0])[0] not in "SP" or c[0] in self.puncs :
                        self.chars.add(c)
                    else :
                        self.ignore.add(c[0])
                    i += 1

    def mergeaffix(self, fname) :
        if fname is not None :
            with codecs.open(fname, encoding='utf-8') as fd :
                self.affix = "\n".join(fd.readlines()).replace(u"\uFEFF", "")

    def getaff(self) :
        res = u"""
SET UTF-8
""" + self.affix

        # calculate uconvs
        uconv = []
        specialchars = []
        for c in self.chars :
            r = c[0]
            if unicodedata.category(r)[0] in 'SP' :
                specialchars.append(r)
            d = decompose(r)
            if len(d) :
                uconv.append((d, r))
                i = 0
                for i in range(1, len(c)) :
                    if unicodedata.combining(c[i]) :
                        d += c[i]
                        r += c[i]
                        for p in itertools.permutations(d[1:]) :
                            t = (u"".join(p), r)
                            if t not in uconv :
                                uconv.append(t)
                    else :
                        break

        if len(specialchars) :
            res += u"\nWORDCHARS {}\n".format(u"".join(specialchars))

        if len(self.ignore) :
            res += u"\nIGNORE {}\n".format(u"".join(sorted(self.ignore)))

        if len(uconv) :
            res += u"\nICONV {}\n".format(len(uconv))
            for u in uconv :
                res += u"ICONV {} {}\n".format(u[0], u[1])
        return res


    def getdic(self) :
        res = "{}\n".format(len(self.words))
        res += "\n".join(sorted(self.words))
        return res

