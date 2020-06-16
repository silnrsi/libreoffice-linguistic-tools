#!/usr/bin/python

import sys, os, re
try:
    from oxttools.xmltemplate import Templater
    import oxttools.modified_etree as metree
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))
    from oxttools.xmltemplate import Templater
    import oxttools.modified_etree as metree
import argparse, codecs
import xml.etree.ElementTree as et
from palaso.langtags import LangTag

try:
    unicode
except NameError:
    unicode = str
    unichr = chr

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

if args.langtag is None:
    lt = re.sub(r"^([a-zA-Z_\-]+).xml", r"\1", os.path.basename(args.infile))
    if "." not in lt:
        ltag = LangTag(lt)
        args.langtag = ltag.analyse()
else:
    ltag = LangTag(args.langtag)
    args.langtag = ltag.analyse()

if args.langtag is not None:
    ltag = LangTag(args.langtag)
    args.langtag = ltag.analyse()
    t.define('lang', args.langtag.lang)
    t.define('script', args.langtag.script)
    if args.langtag.script:
        t.define('lscript', args.langtag.script.lower())
    t.define('region', args.langtag.region)
    # print(t.vars)

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
with codecs.open(args.outfile, "w", encoding="utf-8") as of :
    of.write("<?xml version='1.0'?>\n")
    of.write(unicode(t))


