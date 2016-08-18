"""
Module that implements EPP exceptions
"""
from .doc import EppResponse


class EppException(Exception):
    """Base EPP exception"""
    def __init__(self, resp):
        if isinstance(resp, EppResponse):
            msg = "{%s} %s" % (resp.code, resp.msg)
        else:
            msg = resp
        self.resp = resp
        super(EppException, self).__init__(msg)


class EppConnectionError(EppException):
    """EPP Connection Error. Extends EppException"""
    pass


class EppLoginError(EppException):
    """EPP Loging Error. Extends EppException"""
    pass
