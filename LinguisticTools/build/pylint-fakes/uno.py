"""
A fake UNO file needed to make PyLint happy.
docs.libreoffice.org/pyuno/html/uno_8py.html
"""
class BaseFakeInstance:
    """Complains if None is unexpectedly returned,
    so create one of these instead.
    """
    pass

class FakeInstance(BaseFakeInstance):
    """General purpose fake instance"""
    pass

class UnoUrlResolver(BaseFakeInstance):
    def resolve(self, uno_url):
        return getComponentContext()

class ConfigurationAccess(BaseFakeInstance):
    def getByName(self, name):
        return FakeInstance()

class ConfigurationProvider(BaseFakeInstance):
    def createInstanceWithArguments(self, service_name, arguments):
        if service_name == "com.sun.star.configuration.ConfigurationAccess":
            return ConfigurationAccess()
        return FakeInstance()

def getComponentContext():

    class ServiceManager:
        def createInstanceWithContext(self, service_name, context):
            if service_name == "com.sun.star.bridge.UnoUrlResolver":
                return UnoUrlResolver()
            if service_name == "com.sun.star.configuration.ConfigurationProvider":
                return ConfigurationProvider()
            return FakeInstance()

        def createInstanceWithArgumentsAndContext(
                self, service_name, arguments, context):
            if service_name == "com.sun.star.bridge.UnoUrlResolver":
                return UnoUrlResolver()
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

