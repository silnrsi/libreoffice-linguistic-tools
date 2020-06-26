#!/usr/bin/python

import xml.etree.ElementTree as et
try:
    from io import StringIO
except ImportError:
    # python 2
    from StringIO import StringIO

namespaces_read = dict()  # definitions that were read from the input file

class CommentedTreeBuilder(et.TreeBuilder):
    def comment(self, data):
        self.start(et.Comment, {})
        self.data(data)
        self.end(et.Comment)

def get_namespaces(sourcefile):
    return dict([node for _, node in et.iterparse(sourcefile, events=['start-ns'])])

def get_namespaces_from_string(sourcestring):
    sourcefile = StringIO(sourcestring)
    return get_namespaces(sourcefile)

def register_namespaces(source):
    et._namespace_map = dict()
    namespaces_read.clear()
    namespaces = get_namespaces(source)
    for prefix, uri in namespaces.items():
        et.register_namespace(prefix, uri)
        namespaces_read[prefix] = uri
    if ('' in namespaces):
        # in case one of the namespace definitions overrode the default
        et.register_namespace('', namespaces[''])
        namespaces_read[''] = namespaces['']

def add_namespaces_not_found(root):
    # First get the normal result generated by etree, which includes
    # namespace definitions that are used according to etree.
    result_with_namespaces_found = et.tostring(root).decode()
    namespaces_found = get_namespaces_from_string(result_with_namespaces_found)
    # Now add namespace definitions that were not found by etree.
    for prefix, uri in namespaces_read.items():
        if prefix not in namespaces_found:
            if prefix:
                tag = 'xmlns:' + prefix
            else:
                tag = 'xmlns'
            root.set(tag, uri)

def parse(source):
    register_namespaces(source)
    parser = et.XMLParser(target=CommentedTreeBuilder())
    return et.parse(source, parser)

