# -*- coding: Latin-1 -*-
#
# This file created February 22 2016 by Jim Kornelsen
#
# 23-Feb-2016 JDK  Add classes.
# 03-May-2016 JDK  Add classes.
# 15-Dec-2017 JDK  Classes for APSO add-on.

"""
A fake UNO file needed to make PyLint happy.
https://www.openoffice.org/api/docs/common/ref/com/sun/star/awt/module-ix.html
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

