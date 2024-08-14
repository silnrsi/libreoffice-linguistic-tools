"""
A fake UNO file needed to make PyLint happy.
"""
class Locale:
    def __init__(self, lang, country, variant):
        self.Language = ""
        self.Country = ""
        self.Variant = ""

class EventObject:
    pass

class IllegalArgumentException(Exception):
    pass

class IndexOutOfBoundsException(Exception):
    pass
