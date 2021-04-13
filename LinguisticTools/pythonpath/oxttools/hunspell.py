
import sys
import unicodedata
import itertools

assert sys.version_info.major >= 3, "Requires Python 3"

def decompose(s) :
    return "".join([chr(int(x, 16)) for x in unicodedata.decomposition(s).split()])
    

class Hunspell(object) :

    def __init__(self, name, normalize, puncs="") :
        self.name = name
        self.words = set()
        self.affix = ""
        self.chars = set()
        self.ignore = set()
        self.puncs = puncs
        self.normalize = normalize

    def addword(self, word) :
        if len(word) :
            if self.normalize in ('NFC','NFD'):
                line = unicodedata.normalize('NFC', word)
            else:
                line = word
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
            with open(fname, encoding='utf-8') as fd :
                self.affix = "\n".join(fd.readlines()).replace("\uFEFF", "")

    def getaff(self) :
        res = """
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
                            t = ("".join(p), r)
                            if t not in uconv :
                                uconv.append(t)
                    else :
                        break

        if len(specialchars) :
            res += "\nWORDCHARS {}\n".format("".join(specialchars))

        if len(self.ignore) :
            res += "\nIGNORE {}\n".format("".join(sorted(self.ignore)))

        if len(uconv) :
            res += "\nICONV {}\n".format(len(uconv))
            for u in uconv :
                res += "ICONV {} {}\n".format(u[0], u[1])
        return res


    def getdic(self) :
        res = "{}\n".format(len(self.words))
        res += "\n".join(sorted(self.words))
        return res

