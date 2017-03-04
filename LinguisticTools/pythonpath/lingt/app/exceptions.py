# -*- coding: Latin-1 -*-
#
# This file created Oct 2 2010 by Jim Kornelsen
#
# 28-Feb-13 JDK  Added DocAccessError.
# 18-Apr-13 JDK  Added FileAccessError.
# 13-Jul-15 JDK  Call base class constructors during init.
# 01-Aug-15 JDK  Use tuple unpacking for message arguments list.
# 19-Oct-15 JDK  Interpolate messages.
# 04-Nov-15 JDK  A nested empty tuple should not be used for interpolation.
# 22-Mar-16 JDK  Added DialogError.
# 01-Mar-17 JDK  Added ContentError.

"""
Define custom exceptions that can be raised.

This module exports all of the exception classes defined below.
"""
import logging

from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.app.exceptions")


class LingtError(Exception):
    """Abstract base class for custom exceptions."""
    def __init__(self):
        if self.__class__ is LingtError:
            # The base class should not be instantiated.
            raise NotImplementedError
        Exception.__init__(self)


def interpolate_message(message, msg_args):
    """
    For example, given ("Hello %s", "John"), returns "Hello John".

    :arg message: string optionally containing values like %s to interpolate
    :arg msg_args: any arguments needed for interpolating the message string
    """
    message = theLocale.getText(message)
    if msg_args and msg_args != ((),):
        try:
            # for example "%d%d" % (a, b)
            message = message % msg_args
        except (TypeError, UnicodeDecodeError):
            # Calling logger.exception() here gets the stack trace.
            # However it also causes a crash during automated testing,
            # perhaps caused by lingttest.utils.testutil.MsgSentException
            # and lingt.ui.common.evt_handler.log_exceptions.
            raise LogicError(
                "Message '%s' failed to interpolate arguments %r",
                message, msg_args)
    return message

class MessageError(LingtError):
    """
    Abstract base class for exceptions that can be used to display messages.
    For example:
        raise DataNotFoundError("Didn't find %s or %s (%d)", a, b, len(c))
    Or just:
        raise DataNotFoundError("Didn't find data.")
    """
    def __init__(self, msg, *msg_args):
        if self.__class__ is MessageError:
            # The base class should not be instantiated.
            raise NotImplementedError
        LingtError.__init__(self)
        self.msg = msg
        self.msg_args = msg_args

    def __str__(self):
        return interpolate_message(self.msg, self.msg_args)


class UserInterrupt(LingtError):
    """When the user presses Cancel to interrupt something."""
    pass


class DocAccessError(LingtError):
    """The current document could not be accessed, perhaps because it was
    closed.
    """
    pass


class DataNotFoundError(MessageError):
    """The requested item was not found or the requested operation could not
    be performed.
    """
    pass


class FileAccessError(MessageError):
    """Error reading or writing files."""
    pass


class StyleError(MessageError):
    """Exception raised when there is a problem with styles."""
    pass


class RangeError(MessageError):
    """A problem with the selection or cursor location."""
    pass


class ChoiceProblem(MessageError):
    """There is some problem with the options the user chose."""
    pass


class LogicError(MessageError):
    """Something wrong with program flow; for example, none of several elsif
    conditions were matched.
    """
    pass

class DialogError(MessageError):
    """Dialog controls were in an unexpected state."""
    pass


class ContentError(MessageError):
    """There is something unexpected about what the document or file
    contains."""
    pass
