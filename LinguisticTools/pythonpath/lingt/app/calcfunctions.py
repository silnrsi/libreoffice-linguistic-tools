# -*- coding: Latin-1 -*-
#
# This file created Dec 5 2012 by Jim Kornelsen
#
# 09-Apr-13 JDK  Handle unicode strings in Python 2.
# 10-May-13 JDK  Make it work for Python 3.
# 13-Jul-15 JDK  Change reverseString to module-level function rather than
#                class method.

"""
Define Calc add-ins that can be used as functions.
"""

try:
    # verify that it is defined
    unicode
except NameError:
    # define it for Python 3
    unicode = str

def reverseString(inString):
    s = unicode(inString)
    # This is extended slice syntax [begin:end:step].  With a step of -1,
    # it will traverse the string elements in descending order.
    return s[::-1]

