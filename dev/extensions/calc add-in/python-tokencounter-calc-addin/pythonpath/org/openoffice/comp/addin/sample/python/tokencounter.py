import unohelper
from org.openoffice.addin.sample import XTokenCounter
from com.sun.star.sheet import XAddIn
from com.sun.star.lang import XLocalizable, XServiceName, Locale

class TokenCounter( unohelper.Base, XTokenCounter,  XAddIn, XServiceName ):
    def __init__( self, ctx ):
        self.ctx = ctx
        self.locale = Locale("de","GE", "" )

    def getServiceName( self ):
        return "wordCounter"

    def setLocale( self, locale ):
        self.locale = locale

    def getLocale( self ):
        return self.locale

    def getProgrammaticFuntionName( self, aDisplayName ):
        return aDisplayName

    def getDisplayFunctionName( self, aProgrammaticName ):
        return aProgrammaticName

    def getFunctionDescription( self , aProgrammaticName ):
        return "Counts the number of token separated by whitespace in the target field"

    def getDisplayArgumentName( self, aProgrammaticFunctionName, nArgument ):
        return "Text"

    def getArgumentDescription( self, aProgrammaticFunctionName, nArgument ):
        return "Field, which contains the tokens to count"
    
    def getProgrammaticCategoryName( self, aProgrammaticFunctionName ):
        return "Add-In"

    def getDisplayArgumentName( self, aProgrammaticFunctionName ):
        return "Add-In"

    def tokencount( self, str ):
        # certainly not the most efficient way to implement ...
        return len( str.split() )
    

    
