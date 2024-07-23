# -*- coding: Latin-1 -*-

"""
Functions for iterating over UNO collections.
See "https://wiki.openoffice.org/wiki/Documentation/DevGuide" +
    "/ProUNO/Collections_and_Containers"

Function names are based on the UNO interface they use.

This module exports:
    byIndex() - Gets a python iterator for an UNO collection.
    byName() - Gets a python iterator for an UNO collection.
    byEnum() - Gets a python iterator for an UNO collection.
    fromEnum() - Gets a python iterator from an UNO enumeration.
"""

def byIndex(unoObj):
    """
    The returned iterator is order preserving, unlike byEnum().

    :param unoObj: an UNO collection object that implements interface
                   com.sun.star.container.XIndexAccess.
    :returns: a python generator that iterates over all items
    """
    for iterIndex in range(0, unoObj.getCount()):
        yield unoObj.getByIndex(iterIndex)

def byEnum(unoObj):
    """
    :param unoObj: an UNO collection object that implements interface
                   com.sun.star.container.XEnumerationAccess.
    :returns: a python generator that iterates over all items
    """
    return fromEnum(unoObj.createEnumeration())

def fromEnum(unoObj):
    """
    :param unoObj: an UNO collection object that implements interface
                   com.sun.star.container.XEnumeration.
    :returns: a python generator that iterates over all items
    """
    while unoObj.hasMoreElements():
        yield unoObj.nextElement()

def byName(unoObj):
    """
    :param unoObj: an UNO collection object that implements interface
                   com.sun.star.container.XNameAccess.
    :returns: a python generator that iterates over all items
    """
    for elemName in unoObj.getElementNames():
        yield unoObj.getByName(elemName)
