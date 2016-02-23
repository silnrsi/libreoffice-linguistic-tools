# -*- coding: Latin-1 -*-
#
# This file created February 22 2016 by Jim Kornelsen
#

"""
A fake UNO file needed to make PyLint happy.
docs.libreoffice.org/pyuno/html/uno_8py.html
"""

def getComponentContext():

    class ServiceManager:
        def createInstanceWithContext(self, dummy_str, dummy_ComponentContext):
            return None
        def createInstanceWithArgumentsAndContext(
                self, dummy_str, dummy_arguments, dummy_ComponentContext):
            return None
        def getAvailableServiceNames(self):
            return []

    class ComponentContext:
        def __init__(self):
            self.ServiceManager = ServiceManager()
        def getServiceManager(self):
            return self.ServiceManager

    return ComponentContext()

def getConstantByName():
    return 0

def getTypeByName():
    pass


def createUnoStruct(dummy_structname):

    class ArbitraryUnoStruct:
        pass

    return ArbitraryUnoStruct()


def getClass():
    pass

def isInterface():
    pass

def generateUuid():
    pass

def systemPathToFileUrl(dummy_path):
    return ""

def fileUrlToSystemPath(dummy_url):
    return ""

def absolutize():
    pass

def getCurrentContext():
    return None

def setCurrentContext():
    pass

def invoke():
    pass

