import uno
import unohelper
from com.doobiecompany.examples.DoobieDoo import XDoobieDoo

# DoobieDoo OOo Calc Add-in implementation.
# Created by jan@biochemfusion.com April 2009.

class DoobieDooImpl( unohelper.Base, XDoobieDoo ):
    def __init__( self, ctx ):
        self.ctx = ctx

    def doobieRev( self, s1 ):
        s = str(s1)
        return s[::-1]

    def reverseString(self, inString):
        return u"reverseString"
        #from lingt.App.CalcFunctions import CalcFunctions
        #functions = CalcFunctions(self.ctx)
        #return functions.reverseString(inString)

def createInstance( ctx ):
    return DoobieDooImpl( ctx )

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation( \
    createInstance,"com.doobiecompany.examples.DoobieDoo.python.DoobieDooImpl",
        ("com.sun.star.sheet.AddIn",),)
