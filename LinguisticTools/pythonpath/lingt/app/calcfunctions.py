"""
Define Calc add-ins that can be used as functions.
"""
def reverseString(inString):
    s = str(inString)
    # This is extended slice syntax [begin:end:step].  With a step of -1,
    # it will traverse the string elements in descending order.
    return s[::-1]
