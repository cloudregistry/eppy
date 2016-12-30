"""\
functions to convert an XML file into a python dict, back and forth
"""
# @purpose converts an XML file into a python dict, back and forth
# @author http://code.activestate.com/recipes/573463
#         slightly adapted to follow PEP8 conventions
# based on http://alxr.usatlas.bnl.gov/lxr/source/atlas/Tools/PyUtils/python/xmldict.py
# @author "Sebastien Binet <binet@cern.ch>"
#         modified to handle attributes, namespaces..

__author__ = "Wil Tan <wil@cloudregistry.net>"
from xml.etree import ElementTree
from six import StringIO, iteritems, text_type, PY2, PY3

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
    import os
    import imp
    xml_site_package = os.path.join(os.path.dirname(os.__file__), 'xml')
    m = imp.find_module('etree', [xml_site_package])

    etree = imp.load_module('xml.etree', *m)
    setattr(xml, 'etree', etree)
    return etree

etree = import_etree()


# module data ----------------------------------------------------------------
__all__ = [
    'xml2dict',
    'dict2xml',
]

_BASE_NSMAP = {
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

# module implementation ------------------------------------------------------


class XmlDictObject(dict):
    _path = ()
    _childorder = {}  # relative to _path; only useful if defined at the same
                      # level at which _path is defined/overridden
    _multi_nodes = set()

    def __init__(self, initdict=None, nsmap=None, extra_nsmap=None):
        # NOTE: setting attributes in __init__ will require special handling, see
        # XmlDictObject
        if initdict is None:
            initdict = {}
        dict.__init__(self, initdict)

        if nsmap is None:
            nsmap = self._nsmap = _BASE_NSMAP.copy()
        nsmap.update(extra_nsmap or {})
        self._nsmap = nsmap

        nsmap_r = {}
        # build reverse map
        for prefix, uri in iteritems(nsmap):
            if uri in nsmap_r and not prefix:  # default prefix should not override anything
                continue                # already in the rmap override anything already in the rmap
            nsmap_r[uri] = prefix
        self._nsmap_r = nsmap_r

        self.__initialized = True

    def __getattr__(self, item):
        items = self
        for path in self._path:
            items = items[path]
        if item in items:
            return items[item]
        else:
            # we are calling the `dict` version of __str__ in case the regular
            # __str__ implementation got overridden
            # by a subclass that somehow calls this method again causing an unterminated recursion
            raise AttributeError("no such node (%s/%s) in: %r (self=%s)" % ('/'.join(self._path),
                                                                            item,
                                                                            items,
                                                                            dict.__str__(self)))

    def __setattr__(self, item, value):
        if '_XmlDictObject__initialized' not in self.__dict__:
            # this test allows attributes to be set in the __init__ method
            return super(XmlDictObject, self).__setattr__(item, value)

        if item.startswith("__"):
            super(XmlDictObject, self).__setattr__(item, value)
            return

        items = self
        for path in self._path:
            items = items.__getitem__(path)

        if isinstance(value, dict):
            value = XmlDictObject(value)
        return items.__setitem__(item, value)

    def __delattr__(self, item):
        if item.startswith("__"):
            super(XmlDictObject, self).__delattr__(item)
            return

        items = self
        for path in self._path:
            items = items.__getitem__(path)
        return items.__delitem__(item)

    def __str__(self):
        if '_text' in self:
            return self['_text']
        else:
            return dict.__str__(self)

    @staticmethod
    def wrap(x):
        if isinstance(x, dict):
            return XmlDictObject((k, XmlDictObject.wrap(v))
                                 for (k, v) in iteritems(x))
        elif isinstance(x, list):
            return [XmlDictObject.wrap(v) for v in x]
        else:
            return x

    @staticmethod
    def _unwrap(x):
        if isinstance(x, dict):
            return dict((k, XmlDictObject._unwrap(v))
                        for (k, v) in iteritems(x))
        elif isinstance(x, list):
            return [XmlDictObject._unwrap(v) for v in x]
        else:
            return x

    def to_xml(self, childorder, force_prefix=False):
        el = dict2xml(self, childorder, force_prefix=force_prefix)
        indent(el)
        return ElementTree.tostring(el)

    @classmethod
    def from_xml(cls, buf, default_prefix=None, extra_nsmap=None):
        if PY2:
            root = ElementTree.parse(StringIO(buf)).getroot()
        else: 
            root = ElementTree.fromstring(buf)
        
        rv = xml2dict(
            root,
            outerclass=cls,
            default_prefix=default_prefix,
            multi_nodes=cls._multi_nodes,
            extra_nsmap=extra_nsmap)
        return rv

    def unwrap(self):
        return XmlDictObject._unwrap(self)


def _dict2xml_recurse(parent, dictitem, nsmap, current_prefixes,
                      childorder, force_prefix=False):
    """
    :param nsmap: is a dict, can be `{}`
    :param current_prefixes: is a set
    :param childorder: is a dict, can be `{}`
    """
    if '_order' in dictitem or '__order' in childorder:
        ordr = dictitem.get('_order') or childorder.get('__order', [])
        nodeorder = dict((name, i) for i, name in enumerate(ordr))
        items = sorted(iteritems(dictitem),
                       key=lambda x: nodeorder.get(x[0].split(":")[-1], 0))
    else:
        items = iteritems(dictitem)

    parent_prefix = parent.tag.partition(':')[0] if ':' in parent.tag else ''
    for (tag, child) in items:
        if tag in ('_order', '_nsmap'):
            continue
        if child is None:
            # None means we should not output this element
            continue

        if tag == '_text':
            parent.text = text_type(child)
        elif tag.startswith("@"):
            attrname = tag[1:]
            _do_xmlns(
                parent,
                attrname,
                current_prefixes,
                nsmap,
                set_default_ns=False)
            parent.set(attrname, text_type(child))
        elif type(child) in (list, tuple):
            for listchild in child:
                nsmap_recurs = nsmap
                prefixes_recurs = current_prefixes.copy()
                if ":" in tag:
                    elem = ElementTree.Element(tag)
                    prefix, uri = _do_xmlns(
                        elem, tag, current_prefixes, nsmap, set_default_ns=not force_prefix)
                    if uri:  # we will change the default namespace for children with no prefix
                        # so we need to make copies of nsmap and current_prefixes instead
                        # of updating in-place
                        nsmap_recurs = nsmap.copy()
                        if not force_prefix:
                            nsmap_recurs[''] = uri
                        prefixes_recurs = current_prefixes.union([prefix])
                else:
                    # tag has no prefix
                    if force_prefix:
                        # take parent's prefix
                        if parent_prefix:
                            tag = '%s:%s' % (parent_prefix, tag)
                    elem = ElementTree.Element(tag)

                parent.append(elem)
                if isinstance(listchild, dict):
                    tag_prefix = tag.partition(':')[0] if ':' in tag else ''
                    reltag = tag.rpartition(
                        ':')[2] if not tag_prefix or tag_prefix == parent_prefix else tag
                    _dict2xml_recurse(elem,
                                      listchild,
                                      nsmap=nsmap_recurs,
                                      current_prefixes=prefixes_recurs,
                                      childorder=childorder.get(reltag, {}),
                                      force_prefix=force_prefix)
                else:
                    elem.text = text_type(listchild)
        else:
            nsmap_recurs = nsmap.copy()
            prefixes_recurs = current_prefixes.copy()
            if ":" in tag:
                elem = ElementTree.Element(tag)
                if isinstance(child, dict) and '_nsmap' in child:
                    nsmap_recurs.update(child['_nsmap'])
                prefix, uri = _do_xmlns(
                    elem, tag, current_prefixes, nsmap_recurs, set_default_ns=not force_prefix)
                if uri:  # we will change the default namespace for children with no prefix
                    if not force_prefix:
                        nsmap_recurs[''] = uri
                    prefixes_recurs = current_prefixes.union([prefix])
            else:
                # tag has no prefix
                if force_prefix:
                    # take parent's prefix
                    if parent_prefix:
                        tag = '%s:%s' % (parent_prefix, tag)
                elem = ElementTree.Element(tag)

            parent.append(elem)
            if isinstance(child, dict):
                tag_prefix = tag.partition(':')[0] if ':' in tag else ''
                reltag = tag.rpartition(
                    ':')[2] if not tag_prefix or tag_prefix == parent_prefix else tag
                _dict2xml_recurse(elem,
                                  child,
                                  nsmap=nsmap_recurs,
                                  current_prefixes=prefixes_recurs,
                                  childorder=childorder.get(reltag, {}),
                                  force_prefix=force_prefix)
            else:
                elem.text = text_type(child)


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


def dict2xml(xmldict, childorder, force_prefix=False):
    """convert a python dictionary into an XML tree"""
    roottag = list(filter(lambda x: not x.startswith("_"), xmldict.keys()))[0]
    root = ElementTree.Element(roottag)

    prefixes = set()
    nsmap = getattr(xmldict, '_nsmap', {})
    if nsmap:
        prefix, uri = _do_xmlns(root, roottag, prefixes, nsmap)
        if uri:
            prefixes.add(prefix)
    _dict2xml_recurse(root, xmldict[roottag],
                      current_prefixes=prefixes,
                      nsmap=nsmap,
                      childorder=childorder,
                      force_prefix=force_prefix)
    return root


def _compute_prefix(tag, nsmap_r={}, default_prefix=None):
    if tag.startswith("{"):
        enduri = tag.index("}")
        prefix = nsmap_r.get(tag[1:enduri])
        if prefix is not None:
            tag = tag[enduri + 1:]
            if prefix != default_prefix:  # namespace changed
                tag = "%s:%s" % (prefix, tag)
                default_prefix = prefix
    return tag, default_prefix


def get_prefix_and_name(nsmap_r, name):
    if name.startswith('{'):
        enduri = name.index("}")
        prefix = nsmap_r.get(name[1:enduri])
        return prefix, name[enduri + 1:]
    else:
        return None, name


def get_prefixed_name(nsmap_r, name):
    """meant for attributes"""
    prefix, name = get_prefix_and_name(nsmap_r, name)
    if prefix is not None:
        return "%s:%s" % (prefix, name)
    else:
        return name


def _xml2dict_recurse(node, nodedict, dictclass, nsmap, nsmap_r,
                      default_prefix=None, parent_path=None, multi_nodes=None):
    parent_path = parent_path or tuple()
    if len(node.items()) > 0:
        # if we have attributes, set them
        # wil/rem nodedict.update(dict(node.items()))
        nodedict.update(dict(("@%s" % get_prefixed_name(nsmap_r, k), v)
                             for k, v in node.items()))

    for child in node:
        childtag, childprefix = _compute_prefix(child.tag, nsmap_r, default_prefix)

        # print "recursing with", childtag, "[", childprefix, "] default=", default_prefix
        # recursively add the element's children
        newitem = _xml2dict_recurse(child, dictclass(), dictclass, nsmap, nsmap_r,
                                    default_prefix=childprefix,
                                    multi_nodes=multi_nodes,
                                    parent_path=parent_path + (childtag,))

        nodeval = nodedict.get(childtag)
        if nodeval is not None:
            # found duplicate tag, force a list
            if isinstance(nodeval, list):
                # append to existing list
                nodeval.append(newitem)
            else:
                # convert to list
                nodedict[childtag] = [nodeval, newitem]
        else:
            nodedict.setdefault('_order', []).append(childtag)
            nodepath = parent_path + (childtag,)
            if multi_nodes and nodepath in multi_nodes:
                # if this node is configured to appear multiple times, put it in a
                # list
                nodedict[childtag] = [newitem]
            else:
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

    # print "end nodedict = %r" % (nodedict,)
    return nodedict


def xml2dict(root, dictclass=XmlDictObject, outerclass=XmlDictObject,
             default_prefix=None, multi_nodes=None, extra_nsmap=None):
    """convert an xml tree into a python dictionary
    """
    rootnode = dictclass()
    # we cheat a bit, instantiate it to get the nsmap and nsmap_r

    outer = outerclass(extra_nsmap=extra_nsmap)
    nsmap = outer._nsmap
    nsmap_r = outer._nsmap_r

    tag, default_prefix = _compute_prefix(root.tag, nsmap_r, default_prefix)
    outer[tag] = _xml2dict_recurse(root, rootnode, dictclass, nsmap=nsmap, nsmap_r=nsmap_r,
                                   default_prefix=default_prefix, parent_path=(tag,),
                                   multi_nodes=multi_nodes)
    return outer


def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
