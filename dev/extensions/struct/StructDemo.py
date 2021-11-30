import uno
import unohelper
from com.sun.star.container import XMap
 
class FlexibleStruct:
    pass

class StructDemo(unohelper.Base, XMap):
    def __init__(self, ctx):
        self.ctx = ctx
        self.values = FlexibleStruct()
        self.KeyType = str
        self.ValueType = str
 
    def clear(self):
        self.values = FlexibleStruct()

    def get(self, Key):
        return getattr(self.values, Key)

    def put(self, Key, Value):
        setattr(self.values, Key, Value)

    def remove(self, Key):
        delattr(self.values, Key)

    def containsKey(self, Key):
        return hasattr(self.values, Key)

    def containsValue(self, Value):
        return False

def testdemo(ctx=None):
    if ctx is None:
        ctx = XSCRIPTCONTEXT.getComponentContext()
    demo = StructDemo(ctx)
    demo.put("a", 3)
    display_quick_message(demo.get("a"))

def display_quick_message(message):
    raise Exception("[message={}]".format(message))

g_exportedScripts = (
    testdemo,
    )

IMPLE_NAME = "name.JimK.StructDemo"
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
        StructDemo, IMPLE_NAME, (IMPLE_NAME,),)
