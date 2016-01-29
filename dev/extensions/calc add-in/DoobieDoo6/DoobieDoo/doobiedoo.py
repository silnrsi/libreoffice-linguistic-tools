import uno
import unohelper
#from com.doobiecompany.examples.DoobieDoo import XDoobieDoo
from name.JimK.LinguisticTools.CalcFunctions import XCalcFunctions

# DoobieDoo OOo Calc Add-in implementation.
# Created by jan@biochemfusion.com April 2009.

#class DoobieDooImpl( unohelper.Base, XDoobieDoo ):
#    def __init__( self, ctx ):
#        self.ctx = ctx
#
#    def doobieRev( self, s1 ):
#        s = str(s1)
#        return s[::-1]
#
#    def reverseString(self, inString):
#        return u"reverseString"
#        #from lingt.App.CalcFunctions import CalcFunctions
#        #functions = CalcFunctions(self.ctx)
#        #return functions.reverseString(inString)

class StringReverserAddIn(unohelper.Base, XCalcFunctions):
    def __init__( self, ctx ):
        self.ctx = ctx
    @staticmethod
    def factory(ctx):
        return StringReverserAddIn(ctx)
    def reverseString(self, inString):
        return u"reverseString"
        #from lingt.App.CalcFunctions import CalcFunctions
        #functions = CalcFunctions(self.ctx)
        #return functions.reverseString(inString)

#def createInstance(ctx):
def createStringRev(ctx):
    return StringReverserAddIn(ctx)

#def createInstance( ctx ):
#def createStringRev(ctx):
#    return DoobieDooImpl( ctx )

g_ImplementationHelper = unohelper.ImplementationHelper()
#g_ImplementationHelper.addImplementation( \
#    createInstance,"name.JimK.LinguisticTools.ReverseStringImpl",
#        ("com.sun.star.sheet.AddIn",),)
g_ImplementationHelper.addImplementation( \
    StringReverserAddIn.factory,
    "name.JimK.LinguisticTools.ReverseStringImpl",
    ("com.sun.star.sheet.AddIn",),)
