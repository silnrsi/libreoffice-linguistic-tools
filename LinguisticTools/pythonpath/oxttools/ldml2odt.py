#!/usr/bin/python

import sys, os, re
import argparse
import xml.etree.ElementTree as et
from sldr.langtags_full import LangTag

assert sys.version_info.major >= 3, "Requires Python 3"

try:
    from oxttools.xmltemplate import Templater
    import oxttools.modified_etree as metree
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..','lib'))
    from oxttools.xmltemplate import Templater
    import oxttools.modified_etree as metree

parser = argparse.ArgumentParser()
parser.add_argument('infile',help='xml file to process')
parser.add_argument('outfile',help='Ouptut file to generate')
parser.add_argument('-t','--template',help='Template file to generate from')
parser.add_argument('-l','--langtag',help='Maximal Langtag for this data')
args = parser.parse_args()
t = Templater()
datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib/oxttools/data"))
if args.template is None:
    args.template = os.path.join(datadir, 'simple_ldml.fodt')
t.define('resdir', datadir)
t.define('repdir', os.path.abspath(os.path.dirname(args.template)))

lt = args.langtag
if lt == None:
    lt = re.sub(r"^([a-zA-Z_\-]+).xml", r"\1", os.path.basename(args.infile))
    if "." in lt:
        lt = None
if lt != None:
    ltag = LangTag(lt)
    ltag = ltag.analyse()
    t.define('lang', ltag.lang)
    t.define('script', ltag.script)
    if ltag.script:
        t.define('lscript', ltag.script.lower())
    t.define('region', ltag.region)
    # print t.vars

t.parse(args.template)
oldd = metree.parse(args.infile).getroot()
nsmap = oldd.ns_map
nsmap['sil'] = 'urn://www.sil.org/ldml/0.1'
d = et.Element(oldd.tag)
d.ns_map = nsmap
d[:] = oldd[:]
if args.template.endswith('.fodt'):
    t.processodt(context=d)
else:
    t.process(context = d)
with open(args.outfile, "w", encoding="utf-8") as of :
    of.write("<?xml version='1.0'?>\n")
    of.write(str(t))


