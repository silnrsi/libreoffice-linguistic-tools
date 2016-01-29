## Cre 25-Oct-10 by Jim

"""This file is intended to help find problems in XML files."""

import xml.dom.minidom

infile = r'D:\Jim\study\Irula\Toolbox\exported data\WrittenTamilTexts.xml'

print "Parsing..."
dom = xml.dom.minidom.parse(infile)
print "Finished."

