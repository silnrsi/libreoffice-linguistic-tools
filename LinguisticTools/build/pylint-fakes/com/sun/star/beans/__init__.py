#
# A fake package needed to make PyLint happy.
#
# 03-May-16 JDK  Add classes.

class PropertyValue:
    def __init__(self):
        self.Name = ""
        self.Handle = 0
        self.Value = None
        #self.State = PropertyState.DIRECT_VALUE
        self.State = 0
