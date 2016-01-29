#!/usr/bin/python
# -*- coding: Latin-1 -*-

# Exceptions.py
#
# Change History:
#   Created Oct 2 2010 by Jim Kornelsen

"""
Define custom exceptions that can be raised.
"""

#from lingt.App import Hammy

class LingtError(Exception):
    """Base class for custom exceptions."""
    def __init__(self):
        if self.__class__ is LingtError:   # if base class is instantiated
            raise NotImplementedError

class MessageError(LingtError):
    """Base class for exceptions that can be used to display messages."""
    def __init__(self, msg, msg_args=None):
        if self.__class__ is MessageError:   # if base class is instantiated
            raise NotImplementedError
        self.msg      = msg
        self.msg_args = msg_args

class UserInterrupt(LingtError):
    """When the user presses Cancel to interrupt something."""
    pass

class StyleError(MessageError):
    """Exception raised when there is a problem with styles."""
    pass

class ScopeError(MessageError):
    """A problem with the selection or cursor location."""
    pass

class ChoiceProblem(MessageError):
    """There is some problem with the options the user chose."""
    pass

class LogicError(MessageError):
    """Something wrong with program flow."""
    pass

