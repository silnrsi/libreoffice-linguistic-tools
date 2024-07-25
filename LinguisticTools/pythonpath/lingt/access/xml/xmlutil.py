"""
Functions to help read XML files.
"""
import itertools
import logging

logger = logging.getLogger("lingt.access.xmlutil")

def getTextByTagName(parent, tagname):
    """XML helper function.  Gets text of the first and probably only tag.
    :param parent: DOM object to search under
    :param tagname: tag to search for
    """
    elems = parent.getElementsByTagName(tagname)
    if not elems:
        return ""
    elem = elems[0]
    return getElemText(elem)

def getElemText(elem):
    return "".join(getElemTextList(elem))

def getElemTextList(elem):
    nodelist = elem.childNodes
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return rc

def getTextByWS(parent, preferredWS):
    """Returns the text content for the specified writing system.
    Expected structure <form lang="en"><text></text></form>
    This is handled too: <text></text>

    If more than one form is found, and none match the requested writing system,
    then the first form found is returned.
    """
    if not preferredWS:
        preferredWS = "en"  # default to English
    forms = parent.getElementsByTagName("form")
    if not forms:
        return getTextByTagName(parent, "text")
    if forms == 1:
        return getTextByTagName(forms[0], "text")
    for form in forms:
        if form.attributes:
            lang = form.getAttribute("lang")
            if lang == preferredWS:
                logger.debug("got lang %s", preferredWS)
                return getTextByTagName(form, "text")
    logger.debug("could not get lang %s", preferredWS)
    return getTextByTagName(forms[0], "text")

def getElementsByTagNames(parent, tag_names):
    """For example, get all elements that have tag name 'x' and all elements
    that have tag name 'y'.

    :param parent: a DOM element
    :param tag_names: list of strings ['x', 'y']
    """
    iterables = []
    for tag_name in tag_names:
        iterables.append(parent.getElementsByTagName(tag_name))
    return itertools.chain.from_iterable(iterables)
