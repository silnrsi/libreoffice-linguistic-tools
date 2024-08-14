"""
A fake UNO interface needed to make PyLint happy.
https://api.libreoffice.org/docs/idl/ref/namespacecom_1_1sun_1_1star_1_1awt.html
"""
class Point:
    def __init__(self, dummy_x, dummy_y):
        pass

class Rectangle:
    pass

class Selection(self):
    def __init__(self, dummy_min, dummy_max):
        self.Min = 0
        self.Max = 0

class Size:
    pass

class WindowDescriptor:
    def __init__(self):
        self.Type = 0
        self.WindowServiceName = 0
        self.Parent = 0
        self.ParentIndex = 0
        self.Bounds = 0
        self.WindowAttributes = 0

class XActionListener():
    pass

class XAdjustmentListener():
    pass

class XContainerWindowEventHandler():
    pass

class XItemListener():
    pass

class XKeyListener():
    pass

class XMouseListener():
    pass

class XTextListener():
    pass

