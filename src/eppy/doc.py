from eppy.xmldict import XmlDictObject, dict2xml, ElementTree


EPP_NSMAP = {
        '': 'urn:ietf:params:xml:ns:epp-1.0',
        'epp': 'urn:ietf:params:xml:ns:epp-1.0',
        'domain': 'urn:ietf:params:xml:ns:domain-1.0',
        'contact': 'urn:ietf:params:xml:ns:contact-1.0',
        'host': 'urn:ietf:params:xml:ns:host-1.0',
}

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


class EppDoc(XmlDictObject):
    def __init__(self, dct=None, path=['epp'], extra_nsmap={}):
        nsmap = EPP_NSMAP.copy()
        nsmap.update(extra_nsmap)
        super(EppDoc, self).__init__(dct, nsmap=nsmap)
        if path is not None:
            self._path = path

    def __getattr__(self, item, default=None):
        it = super(EppDoc, self)
        if not item.startswith("_"):
            for p in self._path:
                #print "eppdoc.get %s - getting %s" % (item, p)
                it = it.__getitem__(p)
        return it.get(item, default)

    def __setattr__(self, item, value):
        it = super(EppDoc, self)
        if not item.startswith("_"):
            for p in self._path:
                it = it.__getitem__(p)
        return it.__setitem__(item, value)

    def toxml(self):
        el = dict2xml(self)
        indent(el)
        return ElementTree.tostring(el)


class EppCommand(EppDoc):
    def __init__(self, dct=None, path=['epp', 'command'], extra_nsmap={}):
        #print "comand init", dct
        if dct is None:
            dct = {'epp': {'command': {}}}
        super(EppCommand, self).__init__(dct, path=path, extra_nsmap=extra_nsmap)


class EppLoginCommand(EppCommand):
    def __init__(self, dct=None, path=['epp', 'command', 'login']):
        #print "comand init", dct
        childorder = ['clID', 'pw', 'options', 'svcs']
        if dct is None:
            dct = {
                    'epp': {
                        'command': {
                            'login': {},
                            },
                        },
                    }

        login = dpath_get(dct, path)
        login.setdefault('_order', childorder)
        login.setdefault('options', {'version': '1.0', 'lang': 'en'})
        login['options']['_order'] = ['version', 'lang']
        super(EppLoginCommand, self).__init__(dct, path=path)
        if 'svcs' not in self:
            self.svcs = dict(objURI=self._nsmap_r.keys())


class EppCheckCommand(EppCommand):
    def __init__(self, dct=None, path=['epp', 'command', 'check']):
        if dct is None:
            dct = {
                    'epp': {
                        'command': {
                            'check': {},
                            },
                        },
                    }

        super(EppCheckCommand, self).__init__(dct, path=path)


class EppCheckDomainCommand(EppCommand):
    def __init__(self, dct=None, path=['epp', 'command', 'check', 'domain:check']):
        if dct is None:
            dct = {
                    'epp': {
                        'command': {
                            'check': {
                                'domain:check': {}
                                },
                            },
                        },
                    }

        super(EppCheckDomainCommand, self).__init__(dct, path=path)


class EppInfoCommand(EppCommand):
    _path = ['epp', 'command', 'info']
    def __init__(self, dct=None, path=_path):
        if dct is None:
            dct = self.cmddef()
        super(EppInfoCommand, self).__init__(dct, path=path)

    @classmethod
    def cmddef(cls):
        return {
            'epp': {
                'command': {
                    'info': {},
                },
            },
        }


class EppInfoDomainCommand(EppInfoCommand):
    _path = ['epp', 'command', 'info', 'domain:info']
    def __init__(self, dct=None, path=_path):
        if dct is None:
            dct = self.cmddef()
        super(EppInfoDomainCommand, self).__init__(dct, path=path)

    @classmethod
    def cmddef(cls):
        dct = EppInfoCommand.cmddef()
        dpath = dpath_get(dct, EppInfoCommand._path)
        dpath['domain:info'] = {}
        dpath = dpath_get(dct, cls._path)
        dpath['_order'] = ['name', 'authInfo']
        return dct




class EppCreateDomainCommand(EppCommand):
    def __init__(self, dct=None, path=['epp', 'command', 'create', 'domain:create']):
        #print "comand init", dct
        childorder = ['name', 'period', 'ns', 'registrant', 'contact', 'authInfo']
        if dct is None:
            dct = {
                    'epp': {
                        'command': {
                            'create': {
                                "domain:create": {},
                                },
                            },
                        },
                    }

        #dct['epp']['command']['create']['domain:create']['_order'] = childorder
        dpath_get(dct, path)['_order'] = childorder

        super(EppCreateDomainCommand, self).__init__(dct, path=path)


class EppUpdateCommand(EppCommand):
    _path = ['epp', 'command', 'update']
    def __init__(self, dct=None, path=_path, extra_nsmap={}):
        if dct is None:
            dct = self.cmddef()
        super(EppUpdateCommand, self).__init__(dct, path=path, extra_nsmap=extra_nsmap)

    @classmethod
    def cmddef(cls):
        return {
            'epp': {
                'command': {
                    'update': {},
                },
            },
        }


class EppUpdateDomainCommand(EppUpdateCommand):
    _path = EppUpdateCommand._path + ['domain:update']

    def __init__(self, dct=None, extra_nsmap={}):
        childorder = ['name', 'add', 'rem', 'chg']
        if dct is None:
            dct = {
                    'epp': {
                        'command': {
                            'update': {
                                "domain:update": {},
                                },
                            },
                        },
                    }
        dpath_get(dct, self._path)['_order'] = childorder
        super(EppUpdateDomainCommand, self).__init__(dct, path=self._path, extra_nsmap=extra_nsmap)



class EppPollCommand(EppCommand):
    def __init__(self, op, msgID=None, path=['epp', 'command', 'poll']):
        pollattr = {"@op": op}
        if msgID is not None:
            pollattr['@msgID'] = str(msgID)

        dct = {
            'epp': {
                'command': {
                    'poll': pollattr,
                },
            },
        }

        super(EppPollCommand, self).__init__(dct, path=path)



class EppTransferCommand(EppCommand):
    _path = ['epp', 'command', 'transfer']
    def __init__(self, op, path=_path):
        dct = self.cmddef()
        dct['epp']['command']['transfer']['@op'] = op
        super(EppTransferCommand, self).__init__(dct, path=path)

    @classmethod
    def cmddef(cls):
        return {
            'epp': {
                'command': {
                    'transfer': {},
                },
            },
        }



class EppTransferDomainCommand(EppTransferCommand):
    _path = ['epp', 'command', 'transfer', 'domain:transfer']
    def __init__(self, dct=None, path=_path):
        if dct is None:
            dct = self.cmddef()
        super(EppTransferDomainCommand, self).__init__(dct, path=path)

    @classmethod
    def cmddef(cls):
        dct = EppTransferCommand.cmddef()
        dpath = dpath_get(dct, EppTransferCommand._path)
        dpath['domain:transfer'] = {}
        dpath = dpath_get(dct, cls._path)
        dpath['_order'] = ['name', 'period', 'authInfo']
        return dct



def dpath_get(dct, path, default=None):
    it = dct
    for p in path:
        it = it[p]
    return it


if __name__ == '__main__':
    import sys
    from eppy.xmldict import xml2dict
    from StringIO import StringIO
    from simplejson import dumps as json_encode

    cmd = EppCreateDomainCommand()
    cmd.name = 'hello.me'
    cmd.ns = dict(hostObj=['ns1.acme.com', 'ns2.acme.com'])
    cmd.contact = [{'@type': 'admin', '_text': 'wil001a'}]
    cmd.authInfo=dict(pw='fooBAR')

    #print "handcrafted = ", json_encode(cmd)
    xml = cmd.toxml()
    print xml

    root = ElementTree.parse(StringIO(xml)).getroot()
    cmd2 = xml2dict(root, initialclass=EppCreateDomainCommand, default_prefix="epp")
    print repr(cmd2)
    print json_encode(cmd2)

    print "domain = ", cmd2.name

    print "again back to XML="
    print cmd2.toxml()

    sys.exit(0)
    cmd = {
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

    eppdoc = EppCommand(cmd)
    from xml.etree import ElementTree
    from eppy.xmldict import dict2xml
    print ElementTree.tostring(dict2xml(eppdoc))
