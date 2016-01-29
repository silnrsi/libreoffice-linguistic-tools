
def Convert(s):
    #print "testcnv.py: got " + s
    if s is None or s == "":
        s = "(none)"
    return "<" + s.lower() + ">"

#-------------------------------------------------------------------------------
# idea:
#
# Two python converters.
# 1. Find max num.
# 2. Add new nums.
#
# Run both each time, including for previewing.
# Put file in same dir where scripts are located, which will be current dir.
#
# Problem: How to implement script 1?
# Because how will it know to start at 0?
# User may have to delete the file, which would add a 3rd step.
#
# Somehow allow user to specify how many 0's.
# Also user may just want to rewrite all numbers starting cleanly at 0001.
# Perhaps these options can be allowed in a way that makes it not any extra
# effort to specify when to delete the file.
#
# Perhaps there can be one main script plus a generated or modified called
# script. (That makes 3 scripts all together in this process).
#
# try:
#   import called_script
# except:
#    write_my_new_script()
#    import called_script
#    reload(called_script)
# called_script.main()
#
# Instead of script 1 and 2, could the preview be used as script 1?
# Maybe not; how would we know it's the preview?
#
# Ok, I think these ideas will fit together.
# Two scripts plus a file that just contains a number.
# To change the number of 0 padding, modify a constant in the 2nd script.
# To clear everything and start from 0001, use the bulk edit Delete feature
# and also delete the number file.
# To clear everything but keep numbering from where we left off,
# do the same but no need to delete the file.
#
# In the best case scenario, the user would never have to delete
# the number file or use script 1.
# Just run script 2 as needed.
#
# Using the preview will make it so script 1 and deleting the file are needed
# if the user doesn't want larger numbers.
# Also if some numbers are already filled in then script 1 will be needed.
#
# Use the pickle module to read and write the file?
# No, it doesn't make the file i/o easier.
# try:
#     with open("counter.txt") as f:
#         counter = int(f.read()) + 1
# except IOError:
#     counter = 1
# with open("counter.txt", "w") as f:
#     f.write(str(counter))
#
# DIGITS = 4    # change to 3 or 5 as needed
#
# Zip these two files into a subfolder, then deploy zip file to OOLT website.
# Also include a PDF file with instructions?
# Include a note in the main OOLT help file but not all the instructions.
# "counter.txt"
# "add_numbers.py"
# "count_numbers.py"
# "Ref Numbers for Flex.zip"
# "Help.odt"
#
#-------------------------------------------------------------------------------

