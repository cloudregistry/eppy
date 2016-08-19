"""
Module containing the definition of the order that child elements should be serialized
"""

CMD_BASE = (
    'check',
    'create',
    'delete',
    'info',
    'login',
    'logout',
    'poll',
    'renew',
    'transfer',
    'update',
    'extension',
    'clTRID')

CMD_LOGIN = ('clID',
             'pw',
             'newPW',
             'options',
             'svcs')

CMD_CREATE_DOMAIN = (
    'name',
    'period',
    'ns',
    'registrant',
    'contact',
    'authInfo')
CMD_RENEW_DOMAIN = ('name', 'curExpDate', 'period')

CMD_CREATE_CONTACT = (
    'id',
    'postalInfo',
    'voice',
    'fax',
    'email',
    'authInfo',
    'disclose')

CMD_CREATE_HOST = ('name', 'addr')

CMD_INFO_DOMAIN = ('name', 'authInfo')
CMD_INFO_CONTACT = ('id', 'authInfo')

CMD_UPDATE_DOMAIN = ('name', 'add', 'rem', 'chg')

CMD_UPDATE_CONTACT = ('id', 'add', 'rem', 'chg')
CMD_UPDATE_CONTACT_CHG = (
    'postalInfo',
    'voice',
    'fax',
    'email',
    'authInfo',
    'disclose')

CMD_TRANSFER_DOMAON = ('name', 'period', 'authInfo')
CMD_TRANSFER_CONTACT = ('id', 'period', 'authInfo')

POSTAL_INFO = (
    'name',
    'org',
    'addr',
)

ADDR = (
    'street',
    'city',
    'sp',
    'pc',
    'cc'
)

DISCLOSE = (
    'name',
    'org',
    'addr',
    'voice',
    'fax',
    'email'
)
