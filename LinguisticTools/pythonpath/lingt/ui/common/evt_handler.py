# -*- coding: Latin-1 -*-
#
# This file created March 23 2016 by Jim Kornelsen
#
# 24-Mar-16 JDK  Base class methods to load values and add listeners.
# 25-Mar-16 JDK  Make handling_event static across all listeners.
# 28-Apr-16 JDK  Added DataControls.
# 09-Jun-16 JDK  Fixed bug: Method must be named textChanged().

"""
Abstract base classes to handle UNO dialog events.

This module exports:
    DataControls
    ActionEventHandler
    ItemEventHandler
    TextEventHandler
    log_exceptions()
    do_not_enter_if_handling_event()
    remember_handling_event()
"""
import logging
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener
from com.sun.star.awt import XTextListener

from lingt.app import exceptions
from lingt.utils import util

logger = logging.getLogger("lingt.ui.evt_handler")


class DataControls:
    """Abstract base class for form controls that have data.
    It should not be a problem for other controls such as buttons to
    inherit this class, because implementing these methods is optional.
    This is somewhat similar to uservars.Syncable, but it is for
    the user interface layer.
    """
    def __init__(self):
        if (self.__class__ is DataControls or
                self.__class__ is EventHandler or
                self.__class__ is ActionEventHandler or
                self.__class__ is ItemEventHandler or
                self.__class__ is TextEventHandler):
            # The base classes should not be instantiated.
            raise NotImplementedError

    def load_values(self):
        """Load initial values.  Implement if needed."""
        pass

    def store_results(self):
        """Store form data.  Implement if needed."""
        pass

    def fill(self, *args):
        """Set values of controls to the specified values."""
        pass

    def read(self):
        """Get values of controls and return them."""
        pass


def warn_unexpected_source(src):
    logger.warning("unexpected source %s", src.Model.Name)

class EventHandler(DataControls, unohelper.Base):
    """Abstract base class for handling events."""

    handling_event = False

    def __init__(self):
        DataControls.__init__(self)
        unohelper.Base.__init__(self)
        self.last_source = None  # control of last event

    def start_working(self):
        """Add listeners last because they could cause side effects during
        load_values().
        """
        self.load_values()
        self.add_listeners()

    def add_listeners(self):
        """Add listeners.  Implement if needed."""
        pass


def raise_unknown_action(action_command):
    raise exceptions.LogicError(
        "Unknown action command '%s'", action_command)

class ActionEventHandler(XActionListener, EventHandler):
    """Abstract base class for handling action events such as button
    presses."""

    def actionPerformed(self, event):
        """XActionListener event handler.  Handle which button was pressed."""
        logger.debug("%s %s", util.funcName(), event.ActionCommand)
        EventHandler.handling_event = True
        try:
            self.last_source = event.Source
            self.handle_action_event(event.ActionCommand)
        except Exception as exc:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise
        finally:
            EventHandler.handling_event = False

    def handle_action_event(self, action_command):
        pass


class ItemEventHandler(XItemListener, EventHandler):
    """Abstract base class for handling item events including as list control,
    check box and radio button changes.
    """

    def itemStateChanged(self, event):
        """XItemListener event handler.
        For list controls or enabling and disabling.
        """
        logger.debug(util.funcName())
        if EventHandler.handling_event:
            logger.debug("An event is already being handled.")
            return
        EventHandler.handling_event = True
        try:
            self.last_source = event.Source
            self.handle_item_event(event.Source)
        except Exception as exc:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise
        finally:
            EventHandler.handling_event = False

    def handle_item_event(self, src):
        pass


class TextEventHandler(XTextListener, EventHandler):
    """Abstract base class for handling text events such as list control
    or radio button changes.
    """

    def textChanged(self, event):
        """XTextListener event handler.  For text controls."""
        logger.debug(util.funcName())
        if EventHandler.handling_event:
            logger.debug("An event is already being handled.")
            return
        EventHandler.handling_event = True
        try:
            self.last_source = event.Source
            self.handle_text_event(event.Source)
        except Exception as exc:
            logger.exception(exc)
            # Re-raising is proper coding practice, although it will
            # probably have no effect, at least during runtime.
            raise
        finally:
            EventHandler.handling_event = False

    def handle_text_event(self, src):
        pass


def sameName(control1, control2):
    """Returns True if the UNO controls have the same name.
    This is the control name that is in the dialog designer,
    and also used with dlg.getControl().
    """
    if control1 is None or control2 is None:
        return False
    return control1.getModel().Name == control2.getModel().Name


def log_exceptions(func):
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
