
import SEC_wrapper

class mymsgbox:
    def display(self, msg):
        print msg

msgbox = mymsgbox()
secWrapper = SEC_wrapper.SEC_wrapper(None, msgbox)
result = secWrapper.PickConverter()
print secWrapper.converterName
print result

