#-------------------------------------------------------------------------------
#
# count_numbers.py
#
# Read existing Ref No's in Flex to see what the highest number is.
# After running this code as an SIL Converter, run add_numbers.py.
# This is not required unless the counter needs to be reset.
#
# History:
#   Created by Jim Kornelsen on October 4, 2014
#
#-------------------------------------------------------------------------------

def Convert(sInput):
    try:
        nextVal = int(sInput)
    except ValueError:
        return sInput
    try:
        with open("counter.txt") as f:
            counter = float(f.read())
    except IOError:
        counter = 1.0
    if nextVal > counter:
        with open("counter.txt", "w") as f:
            f.write(str(nextVal))
    return sInput

