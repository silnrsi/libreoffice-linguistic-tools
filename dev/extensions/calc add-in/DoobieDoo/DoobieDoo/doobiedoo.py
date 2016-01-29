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

	def doobieDiv( self, a, b ):
		return a / b

	def doobieConcat( self, s1, s2 ):
		return str(s1) + str(s2)

	def doobieConcatOptional( self, s1, s2, s3 ):
		if s3 == None:
			return str(s1) + str(s2)
		else:
			return str(s1) + str(s2) + str(s3)
 
def createInstance( ctx ):
	return DoobieDooImpl( ctx )

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation( \
	createInstance,"com.doobiecompany.examples.DoobieDoo.python.DoobieDooImpl",
		("com.sun.star.sheet.AddIn",),)
