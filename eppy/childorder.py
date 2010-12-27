

CMD_LOGIN = ('clID',
             'pw',
             'newPW',
             'options',
             'svcs')

CMD_CREATE_DOMAIN = ('name', 'period', 'ns', 'registrant', 'contact', 'authInfo')

CMD_CREATE_CONTACT = ('id', 'postalInfo', 'voice', 'fax', 'email', 'authInfo', 'disclose')

CMD_UPDATE_DOMAIN = ('name', 'add', 'rem', 'chg')

CMD_TRANSFER_DOMAON = ('name', 'period', 'authInfo')

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
