#-------------------------------------------------------------------------------
#
# add_numbers.py
#
# Automatically fill in Ref No's for Flex by using an SIL Converter.
# This is useful for phonology writeups with the OpenOffice Linguistic Tools.
#
# This code uses Python 2 string syntax.
#
# History:
#   Created by Jim Kornelsen on October 4, 2014
#
#-------------------------------------------------------------------------------

DIGITS    = 4    # change to 3 or 5 as needed
RUN_TWICE = True # increment more slowly so it can be run twice for each entry

def Convert(sInput):

    #sInput = unicode(sInput).strip()
    #if sInput:
    #    # input is not empty
    #    return sInput

    #try:
    #    currentVal = int(sInput)
    #except ValueError:
    #    pass
    #else:
    #    # If there's already a legitimate number, then we won't change it.
    #    return unicode(currentVal)

    try:
        with open("counter.txt") as f:
            counter = float(f.read())
            if RUN_TWICE:
                counter += 0.5
            else:
                counter += 1
    except IOError:
        counter = 1
    with open("counter.txt", "w") as f:
        f.write(str(counter))
    padded_number = ("%0" + str(DIGITS) + "d") % (counter)
    return unicode(padded_number)

if __name__ == '__main__':
    # Run multiple times to produce 0001, then 0002 etc.
    # Warning: The following testing code will not work on Python 3.
    print Convert("")

