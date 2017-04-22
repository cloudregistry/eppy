# pylint: disable=C0111

import copy
from eppy.xmldict import XmlDictObject
from eppy.xmldict import _BASE_NSMAP
from past.builtins import unicode, basestring # Python 2 backwards compatibility
from six import iteritems, PY2, PY3
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
    'smd': 'urn:ietf:params:xml:ns:signedMark-1.0',
    'mark': 'urn:ietf:params:xml:ns:mark-1.0',
})


class EppDoc(XmlDictObject):

    def __init__(self, dct=None, nsmap=None, extra_nsmap=None):
        # NOTE: setting attributes in __init__ will require special handling, see
        # XmlDictObject
        if not nsmap:
            nsmap = getattr(self.__class__, '_nsmap', EPP_NSMAP).copy()
        if not dct:
            dct = self.cmddef()
        super(EppDoc, self).__init__(dct, nsmap=nsmap, extra_nsmap=extra_nsmap)

    def to_xml(self, force_prefix):
        # build a dictionary containing the definition of the order that child elements
        # should be serialized
        # NOTE: this does not contain the root element
        # ``self._childorder`` is defined relative to self._path, so we do some tree grafting here
        qualified_childorder = dpath_make(self._path[1:])
        if self._path[1:]:
            dpath_get(qualified_childorder, self._path[
                1:-1])[self._path[-1]] = self._childorder
        else:
            qualified_childorder = self._childorder
        return super(EppDoc, self).to_xml(
            qualified_childorder, force_prefix=force_prefix)

    def __unicode__(self):
        return self.to_xml(force_prefix=False)

    if PY2:
        def __str__(self):
            return unicode(self).encode('utf-8')
    elif PY3:
        def __str__(self):
            return str(self.__unicode__(), 'utf-8')

    # pylint: disable=w0212, e1101
    @classmethod
    def cmddef(cls):
        """
        Create an `XmlDictObject` based on the `_path` defined, and goes through each
        super class to wire up the _childorder
        """
        dct = dpath_make(cls._path)

        # we need to search mro because if we just did `cls._childorder` it could come from any
        # superclass, which may not correspond to the same level where `cls._path` is defined.
        # Also, we want to be able to have each level define its own
        # childorder.
        for aclass in cls.__mro__:
            if aclass == EppDoc:
                # done searching
                break

            if '_childorder' in aclass.__dict__:
                dpath_get(
                    dct, aclass._path)['_order'] = aclass._childorder.get('__order', tuple())
            if '_nsmap' in aclass.__dict__:
                dpath_get(dct, aclass._path)['_nsmap'] = aclass._nsmap
        return dct

    # pylint: disable=w0212, e1101
    @classmethod
    def annotate(cls, dct=None):
        """
        annotate the given `dct` (or create an empty one) by wiring up the _childorder
        and _nsmap fields
        """
        dct = dct or dpath_make(cls._path)

        # we need to search mro because if we just did `cls._childorder` it could come from any
        # superclass, which may not correspond to the same level where `cls._path` is defined.
        # Also, we want to be able to have each level define its own
        # childorder.
        for aclass in cls.__mro__:
            if aclass == EppDoc:
                # done searching
                break

            if '_childorder' in aclass.__dict__:
                # recursively annotate the dict items
                cls._annotate_order_recurse(
                    dpath_get(dct, aclass._path), aclass._childorder)
                # dpath_get(dct, aclass._path)['_order'] = aclass._childorder['__order']

            if '_nsmap' in aclass.__dict__:
                dpath_get(dct, aclass._path)['_nsmap'] = aclass._nsmap
        return dct

    def freeze(self):
        return self.__class__.annotate(self)

    @classmethod
    def _annotate_order_recurse(cls, dct, childorder_):
        if childorder_.get('__order'):
            dct['_order'] = childorder_['__order']
        for k in (k for k in childorder_.keys() if k != '__order'):
            child = dct.get(k)
            if isinstance(child, dict):
                cls._annotate_order_recurse(child, childorder_[k])
            if isinstance(child, (list, tuple)):
                # if there are multiple elements, we need to put the `_order` key in each
                # element
                for elem in child:
                    if isinstance(elem, dict):
                        cls._annotate_order_recurse(elem, childorder_[k])

    @classmethod
    def from_xml(cls, buf, default_prefix='epp', extra_nsmap=None):
        return super(EppDoc, cls).from_xml(
            buf, default_prefix=default_prefix, extra_nsmap=extra_nsmap)

    def normalize_response(self, respdoc):
        """
        perform any cleanup of a response document resulting from this command
        """


class EppHello(EppDoc):
    _path = ('epp', 'hello')


class EppCommand(EppDoc):
    _path = ('epp', 'command')
    _childorder = {'__order': childorder.CMD_BASE}

    def to_xml(self, force_prefix):
        if hasattr(self, 'namestore_product') and self.namestore_product:
            self['epp']['command'].setdefault(
                'extension', {})['namestoreExt:namestoreExt'] = {
                    'namestoreExt:subProduct': self.namestore_product}
            del self.namestore_product
        if hasattr(self, 'phases') and self.phases:
            self.add_command_extension(self.phases)
            del self.phases
        return super(EppCommand, self).to_xml(force_prefix)

    def add_command_extension(self, ext_dict):
        self['epp']['command'].setdefault(
            'extension', {}).update(
                ext_dict.freeze() if isinstance(
                    ext_dict, EppDoc) else ext_dict)
    # pylint: disable=c0103
    def add_clTRID(self, clTRID=None):
        self['epp']['command']['clTRID'] = clTRID or gen_trid()


class EppLoginCommand(EppCommand):
    _path = ('epp', 'command', 'login')
    _childorder = {'__order': childorder.CMD_LOGIN,
                   'svcs': {'__order': ['objURI', 'svcExtension']}}
    # pylint: disable=r0913
    # pylint: disable=w0613
    def __init__(self, dct=None, nsmap=None, extra_nsmap=None, obj_uris=None,
                 extra_obj_uris=None, extra_ext_uris=None, **kwargs):
        super(
            EppLoginCommand,
            self).__init__(
                dct=None,
                nsmap=nsmap,
                extra_nsmap=extra_nsmap)
        dpath_get(self, self._path)
        if not hasattr(self, 'options'):
            self.options = {'version': '1.0', 'lang': 'en'}
        # pylint: disable=w0212
        self.options._order = ['version', 'lang']

        if not hasattr(self, 'svcs'):
            extra_obj_uris = extra_obj_uris or []
            obj_uris = copy.copy(
                obj_uris or list(
                    EPP_STD_OBJECTS_MAP.values()))
            for uri in extra_obj_uris:
                if ':' not in uri:
                    # if no colon, treat it as a well-known namespace prefix
                    uri = EPP_NSMAP[uri]
                if uri not in obj_uris:
                    obj_uris.append(uri)

            self.svcs = dict(objURI=obj_uris)

            ext_uris = []
            extra_ext_uris = extra_ext_uris or []
            for uri in extra_ext_uris:
                if ':' not in uri:
                    # if no colon, treat it as a well-known namespace prefix
                    uri = EPP_NSMAP[uri]
                if uri not in obj_uris:
                    ext_uris.append(uri)
            if ext_uris:
                self.svcs.svcExtension = dict(extURI=ext_uris)

        #self.svcs._order = ['objURI', 'svcExtension']


class EppLogoutCommand(EppCommand):
    _path = ('epp', 'command', 'logout')


class EppCheckCommand(EppCommand):
    _path = ('epp', 'command', 'check')


class EppCheckDomainCommand(EppCheckCommand):
    _path = ('epp', 'command', 'check', 'domain:check')


class EppCheckHostCommand(EppCommand):
    _path = ('epp', 'command', 'check', 'host:check')


class EppCheckContactCommand(EppCheckCommand):
    _path = EppCheckCommand._path + ('contact:check',)


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
        for action, value in iteritems(data):
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
                record_data = dict(
                    ('secDNS:%s' %
                     k, v) for k, v in iteritems(
                         item['data']))
                record_data['_order'] = order
                update_data.append({record_key: record_data})
            for item in update_data:
                for key, val in iteritems(item):
                    if key in tmp_dict:
                        tmp_dict[key].append(val)
                    else:
                        tmp_dict[key] = [val, ]
            update_data = [{k: v[0] if len(v) == 1 else v}
                           for k, v in iteritems(tmp_dict)]
            secdns_data[update_data_key] = update_data
        self['epp']['command'].setdefault(
            'extension', {})['secDNS:update'] = secdns_data


class EppUpdateContactCommand(EppUpdateCommand):
    _path = EppUpdateCommand._path + ('contact:update',)
    _childorder = {
        '__order': childorder.CMD_UPDATE_CONTACT,
        'chg': {
            '__order': childorder.CMD_UPDATE_CONTACT_CHG,
            'postalInfo': {
                '__order': childorder.POSTAL_INFO,
                'addr': {
                    '__order': childorder.ADDR
                },
            },
        },
    }


class EppUpdateHostCommand(EppUpdateCommand):
    _path = EppUpdateCommand._path + ('host:update',)
    _childorder = {'__order': childorder.CMD_UPDATE_DOMAIN}


class EppDeleteCommand(EppCommand):
    _path = ('epp', 'command', 'delete')


class EppDeleteContactCommand(EppDeleteCommand):
    _path = EppDeleteCommand._path + ('contact:delete',)


class EppDeleteDomainCommand(EppDeleteCommand):
    _path = EppDeleteCommand._path + ('domain:delete',)


class EppDeleteHostCommand(EppDeleteCommand):
    _path = EppDeleteCommand._path + ('host:delete',)


class EppPollCommand(EppCommand):
    _path = ('epp', 'command', 'poll')

    def __init__(self, op, msgID=None, extra_nsmap=None):
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

        super(EppPollCommand, self).__init__(dct, extra_nsmap=extra_nsmap)


class EppTransferCommand(EppCommand):
    _path = EppCommand._path + ('transfer',)

    def __init__(self, op, extra_nsmap=None):
        dct = self.cmddef()
        dct['epp']['command']['transfer']['@op'] = op
        super(EppTransferCommand, self).__init__(dct, extra_nsmap=extra_nsmap)


class EppTransferDomainCommand(EppTransferCommand):
    _path = EppTransferCommand._path + ('domain:transfer',)
    _childorder = {'__order': childorder.CMD_TRANSFER_DOMAON}

    @classmethod
    def cmddef(cls):
        dct = EppTransferCommand.cmddef()
        dpath = dpath_get(dct, EppTransferCommand._path)
        dpath['domain:transfer'] = {}
        dpath = dpath_get(dct, cls._path)
        dpath['_order'] = ['name', 'period', 'authInfo']
        return dct


class EppTransferContactCommand(EppTransferCommand):
    _path = EppTransferCommand._path + ('contact:transfer',)
    _childorder = {'__order': childorder.CMD_TRANSFER_CONTACT}

    @classmethod
    def cmddef(cls):
        dct = EppTransferCommand.cmddef()
        dpath = dpath_get(dct, EppTransferCommand._path)
        dpath['contact:transfer'] = {}
        dpath = dpath_get(dct, cls._path)
        dpath['_order'] = ['id', 'period', 'authInfo']
        return dct


class EppResponse(EppDoc):
    _path = ('epp', 'response')
    _childorder = {
        '__order': (
            'result',
            'msgQ',
            'resData',
            'extension',
            'trID')}
    _multi_nodes = set([
        # If the command was processed successfully, only one <result>
        # element MUST be returned. If the command was not processed
        # successfully, multiple <result> elements MAY be returned to
        # document failure conditions.
        ('epp', 'response', 'result'),
        ('epp', 'response', 'result', 'value'),
        ('epp', 'response', 'result', 'extValue'),
        ('epp', 'response', 'resData', 'domain:infData', 'status'),
        ('epp', 'response', 'resData', 'domain:infData', 'contact'),
        ('epp', 'response', 'resData', 'domain:infData', 'ns', 'hostObj'),
        ('epp', 'response', 'resData', 'domain:infData', 'ns', 'hostAttr'),
        ('epp', 'response', 'resData', 'domain:infData', 'ns', 'hostAttr', 'hostAddr'),
        ('epp', 'response', 'resData', 'domain:infData', 'host'),
        ('epp', 'response', 'resData', 'domain:chkData', 'cd'),
        ('epp', 'response', 'resData', 'host:infData', 'status'),
        ('epp', 'response', 'resData', 'host:infData', 'addr'),
        ('epp', 'response', 'resData', 'host:chkData', 'cd'),
        ('epp', 'response', 'resData', 'contact:infData', 'status'),
        ('epp', 'response', 'resData', 'contact:infData', 'postalInfo'),
        ('epp',
         'response',
         'resData',
         'contact:infData',
         'postalInfo',
         'addr',
         'street'),
        ('epp', 'response', 'resData', 'contact:chkData', 'cd'),
        ('epp', 'response', 'extension', 'launch:chkData', 'cd'),
        ('epp', 'response', 'extension', 'rgp:infData', 'rgpStatus'),
        ('epp', 'response', 'extension', 'secDNS:infData', 'dsData'),
        ('epp', 'response', 'extension', 'secDNS:infData', 'keyData'),
    ])

    def __init__(self, dct=None, extra_nsmap=None):
        if dct is None:
            dct = {'epp': {'response': {}}}
        super(EppResponse, self).__init__(dct, extra_nsmap=extra_nsmap)

    @property
    def code(self):
        res = self.first_result
        if res:
            return res['@code']
        else:
            return '0000'

    # pylint: disable=C0103
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
        res = self.first_result
        if res:
            msg = res['msg']
            if isinstance(msg, dict):
                msg = msg.get('_text', u'')

            value = res.get('value', [{}])[0]
            if value:
                if isinstance(value, basestring):
                    msg = u'{}; {}'.format(msg, value)
                if isinstance(value, dict):
                    # afilias message looks like
                    # {'{urn:afilias:params:xml:ns:oxrs-1.1}xcp': 'detailed message'}
                    valuemsg = u', '.join(value.values())
                    if valuemsg:
                        msg = u'{}; {}'.format(msg, valuemsg)

            ext_value = res.get('extValue', [{}])[0]  # take the first one
            reason = ext_value.get(
                'reason',
                {}) if isinstance(
                    ext_value,
                    dict) else ''
            if reason:
                if isinstance('reason', dict):
                    reason = reason.get('_text', '')
                if reason:
                    msg = u'{}; {}'.format(msg, reason)
            return msg
        else:
            return ''

    @property
    def first_result(self):
        if hasattr(self, 'result') and len(self.result):
            return self.result[0]
        else:
            return None

    def get_response_extension(self, key, default=None):
        return getattr(self, 'extension', {}).get(key, default)


def dpath_get(dct, path, default=None):
    default = {} if default is None else default
    cur = dct
    for pat in path:
        cur = cur.get(pat, default)
    return cur


def dpath_make(path):
    out = {}
    cur = out
    for pat in path:
        cur[pat] = {}
        cur = cur[pat]
    return out
