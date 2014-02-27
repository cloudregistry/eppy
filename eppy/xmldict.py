# @purpose converts an XML file into a python dict, back and forth
# @author http://code.activestate.com/recipes/573463
#         slightly adapted to follow PEP8 conventions
# based on http://alxr.usatlas.bnl.gov/lxr/source/atlas/Tools/PyUtils/python/xmldict.py
# @author "Sebastien Binet <binet@cern.ch>"
#         modified to handle attributes, namespaces..

__doc__ = """\
functions to convert an XML file into a python dict, back and forth
"""
__author__ = "Wil Tan <http://cloudregistry.net/people/wil>"

from StringIO import StringIO

# hack: LCGCMT had the py-2.5 xml.etree module hidden by mistake.
#       this is to import it, by hook or by crook
def import_etree():
    import xml
    # first try the usual way
    try:
        import xml.etree
        return xml.etree
    except ImportError:
        pass
    # do it by hook or by crook...
    import sys, os, imp
    xml_site_package = os.path.join(os.path.dirname(os.__file__), 'xml')
    m = imp.find_module('etree', [xml_site_package])

    etree = imp.load_module('xml.etree', *m)
    setattr(xml, 'etree', etree)
    return etree

etree = import_etree()
from xml.etree import ElementTree

## module data ----------------------------------------------------------------
__all__ = [
    'xml2dict',
    'dict2xml',
    ]

_BASE_NSMAP = {
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

## module implementation ------------------------------------------------------
class XmlDictObject(dict):
    _nsmap = _BASE_NSMAP
    _nsmap_r = {}
    _path = ()
    _childorder = {} # relative to _path; only useful if defined at the same level at which _path is defined/overridden

    def __init__(self, initdict=None, nsmap=None):
        # NOTE: setting attributes in __init__ will require special handling, see XmlDictObject
        if initdict is None:
            initdict = {}
        dict.__init__(self, initdict)

        if nsmap is not None:
            self._nsmap = nsmap
            nsmap_r = {}
            # build reverse map
            for prefix, uri in nsmap.iteritems():
                if uri in nsmap_r and not prefix: # default prefix should not override anything already in the rmap
                    continue
                nsmap_r[uri] = prefix
            self._nsmap_r = nsmap_r

        self.__initialized = True


    def __getattr__(self, item):
        it = self
        for p in self._path:
            it = it[p]
        return it[item]


    def __setattr__(self, item, value):
        if not self.__dict__.has_key('_XmlDictObject__initialized'):
            # this test allows attributes to be set in the __init__ method
            return super(XmlDictObject, self).__setattr__(item, value)

        if item.startswith("__"):
            super(XmlDictObject, self).__setattr__(item, value)
            return

        it = self
        for p in self._path:
            it = it.__getitem__(p)

        if type(value) is dict:
            value = XmlDictObject(value)
        return it.__setitem__(item, value)


    def __delattr__(self, item):
        if item.startswith("__"):
            super(XmlDictObject, self).__delattr__(item)
            return

        it = self
        for p in self._path:
            it = it.__getitem__(p)
        return it.__delitem__(item)


    def __str__(self):
        if '_text' in self:
            return self['_text']
        else:
            return dict.__str__(self)

    @staticmethod
    def wrap(x):
        if isinstance(x, dict):
            return XmlDictObject ((k, XmlDictObject.wrap(v))
                                  for (k, v) in x.iteritems())
        elif isinstance(x, list):
            return [XmlDictObject.wrap(v) for v in x]
        else:
            return x

    @staticmethod
    def _unwrap(x):
        if isinstance(x, dict):
            return dict ((k, XmlDictObject._unwrap(v))
                         for (k, v) in x.iteritems())
        elif isinstance(x, list):
            return [XmlDictObject._unwrap(v) for v in x]
        else:
            return x


    def to_xml(self, childorder):
        el = dict2xml(self, childorder)
        indent(el)
        return ElementTree.tostring(el)


    @classmethod
    def from_xml(cls, buf, default_prefix=None):
        root = ElementTree.parse(StringIO(buf)).getroot()
        rv = xml2dict(root, initialclass=cls, default_prefix=default_prefix)
        return rv

        
    def unwrap(self):
        return XmlDictObject._unwrap(self)


def _dict2xml_recurse(parent, dictitem, nsmap, current_prefixes, childorder):
    """
    :param nsmap: is a dict, can be `{}`
    :param current_prefixes: is a set
    :param childorder: is a dict, can be `{}`
    """
    assert type(dictitem) is not type(list) # XXX: this looks wrong, should it be just `list`?

    #print "_dict2xml_recurse(%r)" % (dictitem,)
    #print "nsmap=%r" % (nsmap,)
    #import ipdb; ipdb.set_trace()
    if isinstance(dictitem, dict):
        if '_order' in dictitem or '__order' in childorder:
            ordr = dictitem.get('_order') or childorder['__order']
            nodeorder = dict((name, i) for i,name in enumerate(ordr))
            items = sorted(list(dictitem.iteritems()), key=lambda x: nodeorder.get(x[0].split(":")[-1], 0))
        else:
            items = list(dictitem.iteritems())
        for (tag, child) in items:
            #print "tag=%r" % tag
            if str(tag) in ('_order', '_nsmap'):
                continue
            if str(tag) == '_text':
                parent.text = str(child)
            elif str(tag).startswith("@"):
                _do_xmlns(parent, str(tag)[1:], current_prefixes, nsmap, set_default_ns=False)
                parent.set(str(tag)[1:], str(child))
            elif type(child) in (list, tuple):
                for listchild in child:
                    elem = ElementTree.Element(tag)
                    nsmap_recurs = nsmap
                    prefixes_recurs = current_prefixes
                    if ":" in tag:
                        prefix, uri = _do_xmlns(elem, tag, current_prefixes, nsmap)
                        if uri: # we will change the default namespace for children with no prefix
                            # so we need to make copies of nsmap and current_prefixes instead of updating in-place
                            nsmap_recurs = nsmap.copy()
                            nsmap_recurs[''] = uri
                            prefixes_recurs = current_prefixes.union([prefix])
                    parent.append(elem)
                    _dict2xml_recurse(elem,
                                      listchild,
                                      nsmap=nsmap_recurs,
                                      current_prefixes=prefixes_recurs,
                                      childorder=childorder.get(tag, {}))
            else:                
                elem = ElementTree.Element(tag)
                parent.append(elem)
                nsmap_recurs = nsmap
                prefixes_recurs = current_prefixes
                if ":" in tag:
                    prefix, uri = _do_xmlns(elem, tag, current_prefixes, nsmap)
                    if uri: # we will change the default namespace for children with no prefix
                        nsmap_recurs = nsmap.copy()
                        nsmap_recurs[''] = uri
                        prefixes_recurs = current_prefixes.union([prefix])
                _dict2xml_recurse(elem,
                                  child,
                                  nsmap=nsmap_recurs,
                                  current_prefixes=prefixes_recurs,
                                  childorder=childorder.get(tag, {}))
    else:
        parent.text = unicode(dictitem)


def _do_xmlns(elem, tag, prefixes, nsmap, set_default_ns=True):
    if tag.startswith("{"):
        # tag is in the form of "{NSURI}tagname", which means NSURI is not
        # known in ``nsmap``
        uri = tag[1:tag.rindex('}')]
        return '', uri

    prefix, name = tag.split(":") if ":" in tag else ('', tag)
    if prefix in prefixes:
        return prefix, None
    uri = nsmap.get(prefix)
    if uri:
        if prefix:
            elem.set('xmlns:%s' % prefix, uri)
            if set_default_ns:
                elem.set('xmlns', uri)
        else:
            if set_default_ns:
                elem.set('xmlns', uri)
    return prefix, uri


def dict2xml(xmldict, childorder):
    """convert a python dictionary into an XML tree"""
    roottag = filter(lambda x: not x.startswith("_"), xmldict.keys())[0]
    root = ElementTree.Element(roottag)

    prefixes = set()
    nsmap = getattr(xmldict, '_nsmap', {})
    if nsmap:
        prefix, uri = _do_xmlns(root, roottag, prefixes, nsmap)
        if uri:
            prefixes.add(prefix)
    #print "dict2xml(%r, roottag=%r)" % (xmldict, roottag)
    _dict2xml_recurse(root, xmldict[roottag], current_prefixes=prefixes, nsmap=nsmap, childorder=childorder)
    return root


def _compute_prefix(tag, nsmap_r={}, default_prefix=None):
    if tag.startswith("{"):
        enduri = tag.index("}")
        prefix = nsmap_r.get(tag[1:enduri])
        if prefix is not None:
            tag = tag[enduri+1:]
            if prefix != default_prefix: # namespace changed
                tag = "%s:%s" % (prefix, tag)
                default_prefix = prefix
    return tag, default_prefix


def get_prefix_and_name(nsmap_r, name):
    if name.startswith('{'):
        enduri = name.index("}")
        prefix = nsmap_r.get(name[1:enduri])
        return prefix, name[enduri+1:]
    else:
        return None, name


def get_prefixed_name(nsmap_r, name):
    """meant for attributes"""
    prefix, name = get_prefix_and_name(nsmap_r, name)
    if prefix is not None:
        return "%s:%s" % (prefix, name)
    else:
        return name


def _xml2dict_recurse(node, nodedict, dictclass, nsmap, nsmap_r, default_prefix=None):
    #print "nodedict = %r" % (nodedict,)
    if len(node.items()) > 0:
        # if we have attributes, set them
        ## wil/rem nodedict.update(dict(node.items()))
        nodedict.update(dict(("@%s" % get_prefixed_name(nsmap_r, k), v) for k,v in node.items()))

    for child in node:
        childtag, childprefix = _compute_prefix(child.tag, nsmap_r, default_prefix)

        #print "recursing with", childtag, "[", childprefix, "] default=", default_prefix
        # recursively add the element's children
        newitem = _xml2dict_recurse(child, dictclass(), dictclass, nsmap, nsmap_r, default_prefix=childprefix)

        nodeval = nodedict.get(childtag)
        if nodeval is not None:
            # found duplicate tag, force a list
            if type(nodeval) is list:
                # append to existing list
                nodeval.append(newitem)
            else:
                # convert to list
                nodedict[childtag] = [nodeval, newitem]
        else:
            nodedict.setdefault('_order', []).append(childtag)
            # only one, directly set the dictionary
            nodedict[childtag] = newitem

    if node.text is None:
        text = ''
    else:
        text = node.text.strip()

    if len(nodedict) > 0:
        # if we have a dictionary add the text as a dictionary value
        # (if there is any)
        if len(text) > 0:
            nodedict['_text'] = text
    else:
        # if we don't have child nodes or attributes, just set the text
        nodedict = node.text.strip() if node.text else ""

    #print "end nodedict = %r" % (nodedict,)
    return nodedict


def xml2dict(root, dictclass=XmlDictObject, initialclass=XmlDictObject, default_prefix=None, nsmap={}, nsmap_r={}):
    """convert an xml tree into a python dictionary
    """
    rootnode = dictclass()

    # we cheat a bit, instantiate it to get the nsmap and nsmap_r
    if not nsmap:
        tmp = initialclass()
        nsmap = tmp._nsmap
        nsmap_r = tmp._nsmap_r

    if not nsmap_r:
        # build reverse map
        for prefix, uri in nsmap.iteritems():
            if uri in nsmap_r and not prefix: # default prefix should not override anything already in the rmap
                continue
            nsmap_r[uri] = prefix

    tag, default_prefix = _compute_prefix(root.tag, nsmap_r, default_prefix)
    return initialclass({tag: _xml2dict_recurse(root, rootnode, dictclass, nsmap=nsmap, nsmap_r=nsmap_r, default_prefix=default_prefix)})


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i



if __name__ == '__main__':
    from simplejson import dumps as json_encode

    def from_xml(filename):
        root = ElementTree.parse(filename).getroot()
        epp = xml2dict(root)
        return epp

    """
    epp = from_xml('/dev/stdin')
    print ElementTree.tostring(dict2xml(epp))
    print json_encode([epp, xml2dict(dict2xml(epp))])
    """

    EPP_NSMAP = {
            '': 'urn:ietf:params:xml:ns:epp-1.0',
            'epp': 'urn:ietf:params:xml:ns:epp-1.0',
            'domain': 'urn:ietf:params:xml:ns:domain-1.0',
            'contact': 'urn:ietf:params:xml:ns:contact-1.0',
            'host': 'urn:ietf:params:xml:ns:host-1.0',
            }

    eppdict = XmlDictObject(dict(epp={
        'command': {
            'epp:create': {
                #'{urn:ietf:params:xml:ns:domain-1.0}create': {
                'domain:create': {
                    '_order': ['name', 'period', 'ns', 'registrant', 'contact', 'authInfo'],
                    #'@xmlns:domain': 'urn:ietf:params:xml:ns:domain-1.0',
                    'name': 'hello.com',
                    'domain:registrant': 'wil001',
                    'contact': [
                        {'@type': 'admin', '_text': 'wil001a'},
                        {'@type': 'billing', '_text': 'wil001b'},
                        ],
                    'ns': {
                        'hostObj': [
                            'ns1.example.com',
                            'ns2.example.com',
                            ]
                        },
                    'authInfo': {
                        'pw': 'fooBar'
                        }
                    }
                }
            }
            }), EPP_NSMAP)
    print ElementTree.tostring(dict2xml(eppdict))
    import sys
    sys.exit(0)

    eppdict = XmlDictObject.wrap(dict(epp={
        'command': {
            'create': {
                #'{urn:ietf:params:xml:ns:domain-1.0}create': {
                'domain:create': {
                    #'@xmlns:domain': 'urn:ietf:params:xml:ns:domain-1.0',
                    'name': 'hello.com',
                    'registrant': 'wil001',
                    'contact': [
                        {'@type': 'admin', '_text': 'wil001a'},
                        {'@type': 'billing', '_text': 'wil001b'},
                        ],
                    'ns': {
                        'hostObj': [
                            'ns1.example.com',
                            'ns2.example.com',
                            ]
                        }
                    }
                }
            }
            }))
    eppdict._nsmap = EPP_NSMAP

    print eppdict.epp.command.create['domain:create'].name
    #eppdict = XmlDictObject()
    #eppdict.epp.command.create['domain:create'].name = 'kitty.net'
    print ElementTree.tostring(dict2xml(eppdict))
