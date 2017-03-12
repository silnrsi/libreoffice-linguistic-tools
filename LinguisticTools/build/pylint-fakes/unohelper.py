# -*- coding: Latin-1 -*-
#
# This file created February 22 2016 by Jim Kornelsen
#

"""
A fake UNO file needed to make PyLint happy.
docs.libreoffice.org/pyuno/html/unohelper_8py.html
"""

class ImplementationHelper:
    def addImplementation(self, ctor, implementationName, serviceNames):
        pass

class ImplementationEntry:
    pass

class Base:
    pass

class CurrentContext:
    pass

def inspect():
    pass
 
def createSingleServiceFactory():
    pass
 
def writeRegistryInfoHelper():
    pass
 
def systemPathToFileUrl(dummy_path):
    return ""
 
def fileUrlToSystemPath(dummy_url):
    return ""
 
def absolutize():
    pass
 
def getComponentFactoryHelper():
    pass
 
def addComponentsToContext():
    pass

