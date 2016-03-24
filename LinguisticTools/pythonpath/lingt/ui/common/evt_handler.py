# -*- coding: Latin-1 -*-
#
# This file created March 23 2016 by Jim Kornelsen
#
# 24-Mar-16 JDK  Base class methods to load values and add listeners.

"""
Abstract base classes to handle UNO dialog events.

This module exports:
    ActionEventHandler
    ItemEventHandler
    TextEventHandler
    log_event_handler_exceptions()
    do_not_enter_if_handling_event()
    remember_handling_event()
"""
import logging

from lingt.app import exceptions
from lingt.utils import util

logger = logging.getLogger("lingt.ui.evt_handler")


class EventHandler(unohelper.Base):
    """Abstract base class for handling events."""

    def __init__(self):
        if (self.__class__ is EventHandler or
                self.__class__ is ActionEventHandler or
                self.__class__ is ItemEventHandler or:
                self.__class__ is TextEventHandler):
            # The base classes should not be instantiated.
            raise NotImplementedError
        super(EventHandler, self).__init__()
        self.handling_event = False

    def start_working(self):
        """This method was not designed to be overridden."""
        self.load_values()
        self.add_listeners()

    def load_values(self):
        """Load initial values.  Implement if needed."""
        pass

    def add_listeners(self):
        """Add listeners.  Implement if needed."""
        pass


class ActionEventHandler(XActionListener, EventHandler):
    """Abstract base class for handling action events such as button
    presses."""

    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        self.handling_event = True
        try:
            self.handle_action_event(event.ActionCommand)
        except:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise
        finally:
            self.handling_event = False

    def handle_action_event(self, action_command):
        raise NotImplementedError()

    def raise_unknown_command(self, action_command):
        raise exceptions.LogicError(
            "Unknown action command '%s'", action_command)


class ItemEventHandler(XItemListener, EventHandler):
    """Abstract base class for handling item events including as list control,
    check box and radio button changes.
    """

    def itemStateChanged(self, itemEvent):
        """XItemListener event handler.
        For list controls or enabling and disabling.
        """
        logger.debug(util.funcName())
        if self.handling_event:
            logger.debug("An event is already being handled.")
            return
        try:
            self.handle_item_event(itemEvent.Source)
        except:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise

    def handle_item_event(self, src):
        raise NotImplementedError()


class TextEventHandler(XTextListener, EventHandler):
    """Abstract base class for handling text events such as list control
    or radio button changes.
    """

    def textStateChanged(self, textEvent):
        """XTextListener event handler.  For text controls."""
        logger.debug(util.funcName())
        if self.handling_event:
            logger.debug("An event is already being handled.")
            return
        try:
            self.handle_text_event(textEvent.Source)
        except:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise

    def handle_text_event(self, src):
        raise NotImplementedError()


def sameName(control1, control2):
    """Returns True if the UNO controls have the same name.
    This is the control name that is in the dialog designer,
    and also used with dlg.getControl().
    """
    if control1 is None or control2 is None:
        return False
    return control1.getModel().Name == control2.getModel().Name


def log_event_handler_exceptions(func):
    """Event handlers may swallow exceptions, so we log the exception.

    Wraps event handler methods by decorating them.
    To use, add @this_function_name before the start of a method definition.
    If there is more than one decorator, then this should normally be
    listed first in order to catch exceptions in other decorators.
    """
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as exc:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise

    return wrapper


def do_not_enter_if_handling_event(func):
    """Do not enter this method if an event is already being handled.
    See docstring for remember_handling_event() for further information.

    Wraps event handler methods by decorating them.
    To use, add @this_function_name before the start of a method definition.
    """
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.handling_event:
            logger.debug("An event is already being handled.")
            return
        wrapped_func = remember_handling_event(func)
        wrapped_func(*args, **kwargs)

    return wrapper

def remember_handling_event(func):
    """Set the instance variable self.handling_event.

    An event handler that modifies a control value may cause another
    event handler to be called, which can get out of control.
    So we use an instance variable self.handling_event to check this.
    The variable should be initialized in __init__().

    Wraps event handler methods by decorating them.
    To use, add @this_function_name before the start of a method definition.
    """
    def wrapper(*args, **kwargs):
        self = args[0]
        self.handling_event = True
        try:
            func(*args, **kwargs)
        except:
            raise
        finally:
            self.handling_event = False

    return wrapper

