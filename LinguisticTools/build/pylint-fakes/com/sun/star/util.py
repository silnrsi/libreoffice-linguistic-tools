# -*- coding: Latin-1 -*-
#
# This file created February 22 2016 by Jim Kornelsen
#

"""
A fake UNO file needed to make PyLint happy.
http://www.openoffice.org/api/docs/common/ref/com/sun/star/util/module-ix.html
"""

class CloseVetoException(Exception):
    pass

class InvalidStateException(Exception):
    pass

class MalformedNumberFormatException(Exception):
    pass

class NotLockedException(Exception):
    pass

class NotNumericException(Exception):
    pass

class VetoException(Exception):
    pass

