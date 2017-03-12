# -*- coding: Latin-1 -*-
#
# This file created February 22 2016 by Jim Kornelsen
#
# 11-Mar-17 JDK  Added XJobExecutor.

"""
A fake UNO file needed to make PyLint happy.
http://www.openoffice.org/api/docs/common/ref/com/sun/star/task/module-ix.html
"""

class ErrorCodeIOException(Exception):
    """long ErrCode"""
    pass

class XJobExecutor:
    def trigger(self, sEvent):
        pass
