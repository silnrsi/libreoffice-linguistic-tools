import uno
import unohelper
from com.doobiecompany.examples.DoobieDoo import XDoobieDoo

# DoobieDoo OOo Calc Add-in implementation.
# Created by jan@biochemfusion.com April 2009.

class DoobieDooImpl( unohelper.Base, XDoobieDoo ):
	def __init__( self, ctx ):
		self.ctx = ctx

	def doobieMult( self, a, b ):
		return a * b

	def doobieRev( self, a ):
        return "doobieRev"
        #return a[::-1]

def createInstance( ctx ):
	return DoobieDooImpl( ctx )

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation( \
	createInstance,"com.doobiecompany.examples.DoobieDoo.python.DoobieDooImpl",
		("com.sun.star.sheet.AddIn",),)
