# Translated by Jim K from
# https://wiki.openoffice.org/wiki/Documentation/DevGuide/WritingUNO/Disable_Commands
import uno

from com.sun.star.beans import PropertyValue
from com.sun.star.container import NoSuchElementException
from com.sun.star.lang import WrappedTargetException
from com.sun.star.util import URL as uno_URL

class DisableCommandsTest:
    """Provides example code how to enable/disable commands."""

    # A list of command names
    aCommandURLTestSet = [
        "Open",
        "About",
        "SelectAll",
        "Quit",
    ]

    def __init__(self):
        self.uno_objs = UnoObjs()

    def run_test(self):

        # First we need a defined starting point. So we have to remove
        # all commands from the disabled set!
        self.enableCommands()

        # Check if the commands are usable
        self.testCommands(False)

        # Disable the commands
        self.disableCommands()

        # Now the commands should not be usable anymore
        self.testCommands(True)

        # Remove disable commands to make Office usable again
        self.enableCommands()

    def testCommands(self, bDisabledCmds):
        """Test the commands that we enabled/disabled."""
        print("testCommands " + ("disabled" if bDisabledCmds else "enabled"))
        for sCommand in self.aCommandURLTestSet:
            # Prepare the URL
            aURL = uno_URL()
            aURL.Complete = ".uno:" + sCommand
            dummy, aURL = self.uno_objs.transformer.parseSmart(aURL, ".uno:")

            # Try to get a dispatch object for our URL
            xDispatch = self.uno_objs.frame.queryDispatch(aURL, "", 0)
            if xDispatch:
                if bDisabledCmds:
                    print("Something is wrong, I got dispatch object for "
                      + aURL.Complete)
                else:
                    print("OK, Got dispatch object for " + aURL.Complete)
            else:
                if not bDisabledCmds:
                    print(
                        "Something is wrong, I cannot get dispatch object for "
                        + aURL.Complete)
                else:
                    print("OK, no dispatch object for " + aURL.Complete)
            self.resetURL(aURL)

    def enableCommands(self):
        """Ensure that there are no disabled commands in the user layer. The
        implementation removes all commands from the disabled set!
        """
        # Set the root path for our configuration access
        xPropertyValue = PropertyValue()
        xPropertyValue.Name = "nodepath"
        xPropertyValue.Value = "/org.openoffice.Office.Commands/Execute/Disabled"
        # Create configuration update access to have write access to the
        # configuration
        xAccess = self.uno_objs.configProvider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationUpdateAccess",
            (xPropertyValue,))
        # Retrieves the names of all Disabled nodes
        aCommandsSeq = xAccess.getElementNames()
        for sCommand in aCommandsSeq:
            try:
                # remove the node
                xAccess.removeByName(sCommand)
            except WrappedTargetException as exc:
                print(str(exc))
            except NoSuchElementException as exc:
                print(str(exc))
        # Commit our changes
        xAccess.commitChanges()

    def disableCommands(self):
        """Disable all commands defined in the aCommandURLTestSet array."""
        # Set the root path for our configuration access
        xPropertyValue = PropertyValue()
        xPropertyValue.Name = "nodepath"
        xPropertyValue.Value = "/org.openoffice.Office.Commands/Execute/Disabled"
        # Create configuration update access to have write access to the
        # configuration
        xAccess = self.uno_objs.configProvider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationUpdateAccess",
            (xPropertyValue,))
        aArgs = ()
        for index, sCommand in enumerate(self.aCommandURLTestSet):
            # Create the nodes with the XSingleServiceFactory of the
            # configuration
            xNewElement = xAccess.createInstanceWithArguments(aArgs)
            # We have a new node.
            if xNewElement:
                # Create a unique node name.
                aCmdNodeName = "Command-"
                aCmdNodeName += str(index)

                # Insert the node into the Disabled set
                xNewElement.setPropertyValue("Command", sCommand)
                xAccess.insertByName(aCmdNodeName, xNewElement)
            else:
                print("Not inserting node for " + sCommand)
            # Commit our changes
            xAccess.commitChanges()

    def resetURL(self, aURL):
        """reset URL so it can be reused
        @param aURL the URL that should be reseted
        """
        aURL.Protocol = ""
        aURL.User = ""
        aURL.Password = ""
        aURL.Server = ""
        aURL.Port = 0
        aURL.Path = ""
        aURL.Name = ""
        aURL.Arguments = ""
        aURL.Mark = ""
        aURL.Main = ""
        aURL.Complete = ""


class UnoObjs:
    def __init__(self):
        localContext = uno.getComponentContext()
        resolver = localContext.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", localContext)
        initialObject = resolver.resolve(
            "uno:socket,host=localhost,port=2002;urp;"
            "StarOffice.ServiceManager")
        self.ctx = initialObject.getPropertyValue("DefaultContext")
        self.smgr = self.ctx.ServiceManager
        self.desktop = self.smgr.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        self.frame = self.desktop.getCurrentFrame()
        if not self.frame:
            raise Exception("Could not get frame")
        self.dispatcher = self.smgr.createInstanceWithContext(
            "com.sun.star.frame.DispatchHelper", self.ctx)
        self.transformer = self.smgr.createInstanceWithContext(
            "com.sun.star.util.URLTransformer", self.ctx)
        self.configProvider = self.smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", self.ctx)


if __name__ == '__main__':
    test = DisableCommandsTest()
    test.run_test()
