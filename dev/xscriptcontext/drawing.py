import uno

def create_shape(document, x, y, width, height, shapeType):
    shape = document.createInstance("com.sun.star.drawing.RectangleShape")
    aPoint = uno.createUnoStruct("com.sun.star.awt.Point")
    aPoint.X, aPoint.Y = x, y
    aSize = uno.createUnoStruct("com.sun.star.awt.Size")
    aSize.Width, aSize.Height = width, height
    shape.setPosition(aPoint)
    shape.setSize(aSize)
    return shape

def insert_shape():
    document = XSCRIPTCONTEXT.getDocument()
    drawPage = document.getDrawPages().getByIndex(0)
    shape = create_shape(
        document, 0, 0, 10000, 5000, "com.sun.star.drawing.RectangleShape")
    drawPage.add(shape)
    shape.setString("My new RectangleShape");
    shape.setPropertyValue("CornerRadius", 1000)
    shape.setPropertyValue("Shadow", True)
    shape.setPropertyValue("ShadowXDistance", 250)
    shape.setPropertyValue("ShadowYDistance", 250)
    shape.setPropertyValue("FillColor", int("C0C0C0", 16))  # blue
    shape.setPropertyValue("LineColor", int("000000", 16))  # black
    shape.setPropertyValue("Name", "Rounded Gray Rectangle")

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = insert_shape,
