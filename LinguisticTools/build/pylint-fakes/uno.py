# -*- coding: Latin-1 -*-
#
# This file created February 22 2016 by Jim Kornelsen
#

"""
A fake UNO file needed to make PyLint happy.
docs.libreoffice.org/pyuno/html/uno_8py.html
"""

class BaseFakeInstance:
    """Complains if None is unexpectedly returned,
    so create one of these instead.
    """
    pass

class FakeUnoUrlResolver(BaseFakeInstance):
    def resolve(self, uno_url):
        return "dummy_ctx"

class FakeInstance(BaseFakeInstance):
    """General purpose fake instance"""
    pass

def getComponentContext():

    class ServiceManager:
        def createInstanceWithContext(self, service_name, context):
            if service_name == "com.sun.star.bridge.UnoUrlResolver":
                return FakeUnoUrlResolver()
            return FakeInstance()

        def createInstanceWithArgumentsAndContext(
                self, service_name, arguments, context):
            if service_name == "com.sun.star.bridge.UnoUrlResolver":
                return FakeUnoUrlResolver()
            return FakeInstance()

        def getAvailableServiceNames(self):
            return ["com.sun.star.bridge.UnoUrlResolver",]

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
    return FakeInstance()

def setCurrentContext():
    pass

def invoke():
    pass

