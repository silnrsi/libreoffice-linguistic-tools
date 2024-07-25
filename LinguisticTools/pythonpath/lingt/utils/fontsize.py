"""
Operations related to font size defaults and form input.
"""
import functools
import logging

DEFAULT_VAL = 12.0
LOWER_LIMIT = 1
UPPER_LIMIT = 99

logger = logging.getLogger("lingt.utils.fontsize")

@functools.total_ordering
class FontSize:
    def __init__(self, default=DEFAULT_VAL, propSuffix="", spec=False):
        """
        :param default: may be used when loading new values
        :param propSuffix: empty, Complex or Asian
        :param spec: To specify the size on initialization, pass the size as
                     the first parameter and set spec to True.
        """
        self.defaultVal = default
        self.size = float(default)
        self.propSuffix = propSuffix
        self.specified = spec

    def setPropSuffix(self, newVal):
        self.propSuffix = newVal

    def setSize(self, newVal):
        self.size = newVal

    def isSpecified(self):
        """Has a size been specified or is it empty?
        For example, empty means that no change is needed for Data Conversion.
        """
        return self.specified

    def changeCtrlProp(self, ctrl, always_change=False):
        """For dialog controls including labels.
        Sets the control's font size.
        :param always_change: true to change even if size is unspecified
        """
        if self.specified or always_change:
            logger.debug(
                "set %s.FontHeight %1.1f", ctrl.getModel().Name, self.size)
            ctrl.getModel().FontHeight = self.size

    def loadCtrl(self, textctrl):
        """Load from text control input.
        Modifies text of control.
        """
        self.loadVal(textctrl.getText())
        if self.specified:
            self.changeCtrlVal(textctrl)

    def changeCtrlVal(self, textctrl):
        """
        Set value of text control.  Useful even if value is unspecified.
        """
        newVal = self.getString()
        if textctrl.getText() != newVal:
            logger.debug("ctrl from %r to %r", textctrl.getText(), newVal)
            textctrl.setText(newVal)

    def changeElemProp(self, styleObj):
        """For document elements such as styles and cursors.
        Sets the element's font size.
        """
        if self.specified:
            propName = 'CharHeight%s' % self.propSuffix
            logger.debug("set %s %1.1f", propName, self.size)
            styleObj.setPropertyValue(propName, self.size)

    def loadElemProp(self, styleObj):
        """For document elements such as styles and cursors."""
        propName = 'CharHeight%s' % self.propSuffix
        self.loadVal(
            styleObj.getPropertyValue(propName))

    def loadUserVar(self, userVars, varName):
        self.loadVal(userVars.get(varName))

    def loadVal(self, newVal):
        """Set size based on the specified value."""
        if not newVal:
            self.size = self.defaultVal
            self.specified = False
            return
        try:
            self.size = float(newVal)
        except ValueError:
            self.size = self.defaultVal
        if self.size < LOWER_LIMIT or self.size > UPPER_LIMIT:
            self.size = self.defaultVal
        self.specified = True

    def getFloat(self):
        return self.size

    def getString(self):
        if not self.specified:
            return ""
        strval = "%1.1f" % self.size
        if strval.endswith(".0"):
            strval = strval[:-2]  # remove trailing ".0"
        return strval

    def attrs(self):
        """Used for several magic methods below."""
        return self.size, self.propSuffix, self.specified

    def __lt__(self, other):
        return self.attrs() < other.attrs()

    def __eq__(self, other):
        return self.attrs() == other.attrs()

    def __hash__(self):
        return hash(self.attrs())
