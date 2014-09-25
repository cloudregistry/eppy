from eppy.xmldict import XmlDictObject, _BASE_NSMAP, dict2xml, ElementTree
from . import childorder
from .utils import gen_trid


EPP_NSMAP = dict(_BASE_NSMAP)
EPP_STD_OBJECTS_MAP = {
    'domain': 'urn:ietf:params:xml:ns:domain-1.0',
    'host': 'urn:ietf:params:xml:ns:host-1.0',
    'contact': 'urn:ietf:params:xml:ns:contact-1.0',
}
EPP_STD_EXT_MAP = {
    'rgp': 'urn:ietf:params:xml:ns:rgp-1.0',
}
EPP_NSMAP.update(EPP_STD_OBJECTS_MAP)
EPP_NSMAP.update(EPP_STD_EXT_MAP)
EPP_NSMAP.update({
    '': 'urn:ietf:params:xml:ns:epp-1.0',
    'epp': 'urn:ietf:params:xml:ns:epp-1.0',
    'secDNS10': 'urn:ietf:params:xml:ns:secDNS-1.0',
    'secDNS': 'urn:ietf:params:xml:ns:secDNS-1.1',
    'namestoreExt': 'http://www.verisign-grs.com/epp/namestoreExt-1.1',
    'launch': 'urn:ietf:params:xml:ns:launch-1.0',
})


class EppDoc(XmlDictObject):
    def __init__(self, dct=None, nsmap=None, extra_nsmap=None):
        # NOTE: setting attributes in __init__ will require special handling, see XmlDictObject
        if not nsmap:
            nsmap = EPP_NSMAP.copy()
        if not dct:
            dct = self.cmddef()
        super(EppDoc, self).__init__(dct, nsmap=nsmap, extra_nsmap=extra_nsmap)

    def to_xml(self, force_prefix):
        # build a dictionary containing the definition of the order that child elements should be serialized
        # NOTE: this does not contain the root element
        # ``self._childorder`` is defined relative to self._path, so we do some tree grafting here
        qualified_childorder = dpath_make(self._path[1:])
        dpath_get(qualified_childorder, self._path[1:-1])[self._path[-1]] = self._childorder
        return super(EppDoc, self).to_xml(qualified_childorder, force_prefix=force_prefix)

    def __unicode__(self):
        return self.to_xml(force_prefix=False)

    def __str__(self):
        return unicode(self).encode('utf-8')

    @classmethod
    def cmddef(cls):
        """
        Create an `XmlDictObject` based on the `_path` defined, and goes through each super class to wire up
        the _childorder
        """
        dct = dpath_make(cls._path)

        # we need to search mro because if we just did `cls._childorder` it could come from any superclass,
        # which may not correspond to the same level where `cls._path` is defined.
        # Also, we want to be able to have each level define its own childorder.
        for aclass in cls.__mro__[1:]:
            if aclass == EppDoc:
                # done searching
                break

            if '_childorder' in aclass.__dict__:
                dpath_get(dct, aclass._path)['_order'] = aclass._childorder['__order']
        return dct

    @classmethod
    def from_xml(cls, buf, default_prefix='epp', extra_nsmap=None):
        return super(EppDoc, cls).from_xml(buf, default_prefix=default_prefix, extra_nsmap=extra_nsmap)

    def normalize_response(self, respdoc):
        """
        perform any cleanup of a response document resulting from this command
        """
        pass


class EppHello(EppDoc):
    _path = ('epp', 'hello')


class EppCommand(EppDoc):
    _path = ('epp', 'command')
    _childorder = {'__order': childorder.CMD_BASE}

    def to_xml(self, force_prefix):
        if hasattr(self, 'namestore_product') and self.namestore_product:
            self['epp']['command'].setdefault(
                'extension', {})['namestoreExt:namestoreExt'] = {'namestoreExt:subProduct': self.namestore_product}
            del self.namestore_product
        return super(EppCommand, self).to_xml(force_prefix)

    def add_command_extension(self, ext_dict):
        self['epp']['command'].setdefault('extension', {}).update(ext_dict)

    def add_clTRID(self, clTRID=None):
        self['epp']['command']['clTRID'] = clTRID or gen_trid()



class EppLoginCommand(EppCommand):
    _path = ('epp', 'command', 'login')
    _childorder = {'__order': childorder.CMD_LOGIN}

    def __init__(self, dct=None):
        if dct is None:
            dct = {
                    'epp': {
                        'command': {
                            'login': {},
                            },
                        },
                    }

        login = dpath_get(dct, self._path)
        login.setdefault('_order', childorder.CMD_LOGIN)
        login.setdefault('options', {'version': '1.0', 'lang': 'en'})
        login['options']['_order'] = ['version', 'lang']
        super(EppLoginCommand, self).__init__(dct)

    def to_xml(self, force_prefix):
        if not hasattr(self, 'svcs'):
            self.svcs = dict(objURI=EPP_STD_OBJECTS_MAP.values())
        return super(EppLoginCommand, self).to_xml(force_prefix=force_prefix)


class EppLogoutCommand(EppCommand):
    _path = ('epp', 'command', 'logout')


class EppCheckCommand(EppCommand):
    _path = ('epp', 'command', 'check')


class EppCheckDomainCommand(EppCheckCommand):
    _path = ('epp', 'command', 'check', 'domain:check')


class EppCheckHostCommand(EppCommand):
    _path = ('epp', 'command', 'check', 'host:check')

    def __init__(self, dct=None, hosts=None):
        if dct is None:
            if hosts is None:
                hosts = []
            elif not isinstance(hosts, (list, tuple)):
                hosts = [hosts]

            dct = {
                    'epp': {
                        'command': {
                            'check': {
                                'host:check': {'name': list(hosts)}
                                },
                            },
                        },
                    }

        super(EppCheckHostCommand, self).__init__(dct)


class EppInfoCommand(EppCommand):
    _path = ('epp', 'command', 'info')


class EppInfoDomainCommand(EppInfoCommand):
    _path = EppInfoCommand._path + ('domain:info',)
    _childorder = {'__order': childorder.CMD_INFO_DOMAIN}


class EppInfoContactCommand(EppInfoCommand):
    _path = EppInfoCommand._path + ('contact:info',)
    _childorder = {'__order': childorder.CMD_INFO_CONTACT}

    def normalize_response(self, respdoc):
        """
        clean up voice and fax
        """
        super(EppInfoContactCommand, self).normalize_response(respdoc)
        try:
            voice = respdoc.resData['contact:infData']['voice']
        except (AttributeError, KeyError):
            pass
        else:
            if not isinstance(voice, dict):
                respdoc.resData['contact:infData']['voice'] = {'_text': voice}

        try:
            fax = respdoc.resData['contact:infData']['fax']
        except (AttributeError, KeyError):
            pass
        else:
            if not isinstance(fax, dict):
                respdoc.resData['contact:infData']['fax'] = {'_text': fax}


class EppInfoHostCommand(EppInfoCommand):
    _path = EppInfoCommand._path + ('host:info',)

    def normalize_response(self, respdoc):
        """
        clean up addr
        """
        super(EppInfoHostCommand, self).normalize_response(respdoc)
        try:
            addrs = respdoc.resData['host:infData']['addr']
        except (AttributeError, KeyError):
            return

        if addrs:
            for i, addr in enumerate(addrs):
                if not isinstance(addr, dict):
                    # it should be a text
                    addrs[i] = dict(_text=addr)



class EppCreateCommand(EppCommand):
    _path = ('epp', 'command', 'create')

    @classmethod
    def cmddef(cls):
        return {
            'epp': {
                'command': {
                    '_order': ['create', 'extension', 'clTRID'],
                    'create': {},
                    },
                },
            }


class EppCreateDomainCommand(EppCreateCommand):
    _path = EppCreateCommand._path + ('domain:create',)
    _childorder = {'__order': childorder.CMD_CREATE_DOMAIN}


class EppCreateContactCommand(EppCreateCommand):
    _path = EppCreateCommand._path + ('contact:create',)
    _childorder = {
        '__order': childorder.CMD_CREATE_CONTACT,
        'postalInfo': {
            '__order': childorder.POSTAL_INFO,
            'addr': {
               '__order': childorder.ADDR
            },
        },
        'disclose': {
            '__order': childorder.DISCLOSE
        }
    }


class EppCreateHostCommand(EppCreateCommand):
    _path = EppCreateCommand._path + ('host:create',)
    _childorder = {'__order': childorder.CMD_CREATE_HOST}



class EppRenewCommand(EppCommand):
    _path = ('epp', 'command', 'renew')


class EppRenewDomainCommand(EppRenewCommand):
    _path = EppRenewCommand._path + ('domain:renew',)
    _childorder = {'__order': childorder.CMD_RENEW_DOMAIN}



class EppUpdateCommand(EppCommand):
    _path = ('epp', 'command', 'update')


class EppUpdateDomainCommand(EppUpdateCommand):
    _path = EppUpdateCommand._path + ('domain:update',)
    _childorder = {'__order': childorder.CMD_UPDATE_DOMAIN}

    def add_secdns_data(self, data):
        secdns_data = dict()
        for action, value in data.iteritems():
            update_data_key = 'secDNS:%s' % action
            update_data = list()
            tmp_dict = dict()
            for item in value:
                record_type = item['type']
                record_key = 'secDNS:%sData' % record_type
                if record_type == 'maxSigLife':
                    update_data.append({record_key: [item['value'], ]})
                    continue
                if record_type == 'ds':
                    order = ['keyTag', 'alg', 'digestType', 'digest']
                else:
                    order = ['flags', 'protocol', 'alg', 'pubKey']
                record_data = dict(('secDNS:%s' % k, v) for k, v in item['data'].iteritems())
                record_data['_order'] = order
                update_data.append({record_key: record_data})
            for item in update_data:
                for key, val in item.iteritems():
                    if key in tmp_dict:
                        tmp_dict[key].append(val)
                    else:
                        tmp_dict[key] = [val, ]
            update_data = [{k: v[0] if len(v) == 1 else v} for k, v in tmp_dict.iteritems()]
            secdns_data[update_data_key] = update_data
        self['epp']['command'].setdefault('extension', {})['secDNS:update'] = secdns_data


class EppUpdateContactCommand(EppUpdateCommand):
    _path = EppUpdateCommand._path + ('contact:update',)
    _childorder = {
        '__order': childorder.CMD_UPDATE_CONTACT,
        'chg': {
            '__order': childorder.CMD_UPDATE_CONTACT_CHG,
        },
    }



class EppUpdateHostCommand(EppUpdateCommand):
    _path = EppUpdateCommand._path + ('host:update',)
    _childorder = {'__order': childorder.CMD_UPDATE_DOMAIN}



class EppCheckContactCommand(EppCheckCommand):
    _path = EppCheckCommand._path + ('contact:check',)

    def __init__(self, dct=None, contacts=None):
        if dct is None:
            if contacts is None:
                contacts = []
            elif isinstance(contacts, basestring):
                contacts = [contacts]
            dct = {
                'epp': {
                    'command': {
                        'check': {
                            'contact:check': {'id': list(contacts)}
                        },
                    },
                },
            }

        super(EppCheckContactCommand, self).__init__(dct)



class EppDeleteCommand(EppCommand):
    _path = ('epp', 'command', 'delete')

    @classmethod
    def cmddef(cls):
        return {
            'epp': {
                'command': {
                    '_order': ['delete', 'extension'],
                    'delete': {},
                    },
                },
            }


class EppDeleteContactCommand(EppDeleteCommand):
    _path = EppDeleteCommand._path + ('contact:delete',)


class EppDeleteDomainCommand(EppDeleteCommand):
    _path = EppDeleteCommand._path + ('domain:delete',)


class EppDeleteHostCommand(EppDeleteCommand):
    _path = EppDeleteCommand._path + ('host:delete',)



class EppPollCommand(EppCommand):
    _path = ('epp', 'command', 'poll')

    def __init__(self, op, msgID=None):
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

        super(EppPollCommand, self).__init__(dct)



class EppTransferCommand(EppCommand):
    _path = EppCommand._path + ('transfer',)

    def __init__(self, op):
        dct = self.cmddef()
        dct['epp']['command']['transfer']['@op'] = op
        super(EppTransferCommand, self).__init__(dct)

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
    _path = EppTransferCommand._path + ('domain:transfer',)
    _childorder = {'__order': childorder.CMD_TRANSFER_DOMAON}

    def __init__(self, dct=None):
        if dct is None:
            dct = self.cmddef()
        super(EppTransferDomainCommand, self).__init__(dct)

    @classmethod
    def cmddef(cls):
        dct = EppTransferCommand.cmddef()
        dpath = dpath_get(dct, EppTransferCommand._path)
        dpath['domain:transfer'] = {}
        dpath = dpath_get(dct, cls._path)
        dpath['_order'] = ['name', 'period', 'authInfo']
        return dct


class EppResponse(EppDoc):
    _path = ('epp', 'response')
    _childorder = {'__order': ('result', 'msgQ', 'resData', 'extension', 'trID')}
    _multi_nodes = set([
        # If the command was processed successfully, only one <result>
        # element MUST be returned. If the command was not processed
        # successfully, multiple <result> elements MAY be returned to
        # document failure conditions.
        ('epp', 'response', 'result'),
        ('epp', 'response', 'resData', 'domain:infData', 'status'),
        ('epp', 'response', 'resData', 'domain:infData', 'ns', 'hostObj'),
        ('epp', 'response', 'resData', 'domain:infData', 'host'),
        ('epp', 'response', 'resData', 'domain:chkData', 'cd'),
        ('epp', 'response', 'resData', 'host:infData', 'status'),
        ('epp', 'response', 'resData', 'host:infData', 'addr'),
        ('epp', 'response', 'resData', 'host:chkData', 'cd'),
        ('epp', 'response', 'resData', 'contact:infData', 'status'),
        ('epp', 'response', 'resData', 'contact:infData', 'postalInfo'),
        ('epp', 'response', 'resData', 'contact:infData', 'postalInfo', 'addr', 'street'),
        ('epp', 'response', 'resData', 'contact:chkData', 'cd'),
        ('epp', 'response', 'extension', 'launch:chkData', 'cd'),
    ])

    def __init__(self, dct=None, extra_nsmap=None):
        if dct is None:
            dct = {'epp': {'response': {}}}
        super(EppResponse, self).__init__(dct, extra_nsmap=extra_nsmap)

    @property
    def code(self):
        return self.result[0]['@code']

    @property
    def ok(self):
        return self.code == '1000'

    @property
    def pending(self):
        return self.code == '1001'

    @property
    def success(self):
        return self.code in ('1000', '1001')

    @property
    def msg(self):
        return self.result[0].msg

    @property
    def first_result(self):
        return self.result[0].msg

    @property
    def response_extension(self):
        return self['epp']['response']['extension']

    def get_response_extension(self, key):
        return self.response_extension[key]


def dpath_get(dct, path, default=None):
    default = {} if default is None else default
    it = dct
    for p in path:
        it = it.get(p, default)
    return it

def dpath_make(path):
    out = {}
    it = out
    for p in path:
        it[p] = {}
        it = it[p]
    return out

if __name__ == '__main__':
    import sys
    from eppy.xmldict import xml2dict
    from StringIO import StringIO
    try:
        from simplejson import dumps as json_encode
    except ImportError:
        from json import dumps as json_encode

    cmd = EppCreateDomainCommand()
    cmd.name = 'hello.me'
    cmd.ns = dict(hostObj=['ns1.acme.com', 'ns2.acme.com'])
    cmd.contact = [{'@type': 'admin', '_text': 'wil001a'}]
    cmd.authInfo=dict(pw='fooBAR')

    #print "handcrafted = ", json_encode(cmd)
    xml = cmd.to_xml()
    print xml

    root = ElementTree.parse(StringIO(xml)).getroot()
    cmd2 = xml2dict(root, outerclass=EppCreateDomainCommand, default_prefix="epp")
    print repr(cmd2)
    print json_encode(cmd2)

    print "domain = ", cmd2.name

    print "again back to XML="
    print cmd2.to_xml()

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
