"""
Module that implements the EppClient class
"""

try:
    # use gevent if available
    import gevent.socket as socket
    import gevent.ssl as ssl
except ImportError:
    import socket
    import ssl

import struct
from collections import deque
import logging
from six import PY2, PY3
from past.builtins import xrange # Python 2 backwards compatibility
from .exceptions import EppLoginError, EppConnectionError
from .doc import (EppResponse, EppHello, EppLoginCommand, EppLogoutCommand,
                  EppCreateCommand, EppUpdateCommand, EppRenewCommand,
                  EppTransferCommand, EppDeleteCommand)
from .utils import gen_trid
try:
    from ssl import match_hostname, CertificateError
except ImportError:
    from backports.ssl_match_hostname import match_hostname, CertificateError


class EppClient(object):
    """
    EPP client class
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments

    def __init__(self, host=None, port=700,
                 ssl_enable=True, ssl_keyfile=None, ssl_certfile=None, ssl_cacerts=None,
                 ssl_version=None, ssl_ciphers=None,
                 ssl_validate_hostname=True, socket_timeout=60, socket_connect_timeout=15,
                 ssl_validate_cert=True):
        self.host = host
        self.port = port
        self.ssl_enable = ssl_enable
        # PROTOCOL_SSLv23 gives the best proto version available (including TLSv1 and above)
        # SSLv2 should be disabled by most OpenSSL build
        self.ssl_version = ssl_version or ssl.PROTOCOL_SSLv23
        # `ssl_ciphers`, if given, should be a string
        # (https://www.openssl.org/docs/apps/ciphers.html)
        # if not given, use the default in Python version (`ssl._DEFAULT_CIPHERS`)
        self.ssl_ciphers = ssl_ciphers
        self.keyfile = ssl_keyfile
        self.certfile = ssl_certfile
        self.cacerts = ssl_cacerts
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.validate_hostname = ssl_validate_hostname
        self.log = logging.getLogger(__name__)
        self.sock = None
        self.greeting = None

        if ssl_validate_cert:
            self.cert_required = ssl.CERT_REQUIRED
        else:
            self.cert_required = ssl.CERT_NONE

    def connect(self, host, port=None):
        """
        Method that initiates a connection to an EPP host
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.socket_connect_timeout)  # connect timeout
        self.sock.connect((host, port or self.port))
        local_sock_addr = self.sock.getsockname()
        local_addr, local_port = local_sock_addr[:2]
        self.log.debug('connected local=%s:%s remote=%s:%s',
                       local_addr, local_port, self.sock.getpeername()[0], port)
        self.sock.settimeout(self.socket_timeout)  # regular timeout
        if self.ssl_enable:
            self.sock = ssl.wrap_socket(self.sock, self.keyfile, self.certfile,
                                        ssl_version=self.ssl_version,
                                        ciphers=self.ssl_ciphers,
                                        server_side=False,
                                        cert_reqs=self.cert_required,
                                        ca_certs=self.cacerts)
            self.log.debug('%s negotiated with local=%s:%s remote=%s:%s', self.sock.version(),
                           local_addr, local_port, self.sock.getpeername()[0], port)
            if self.validate_hostname:
                try:
                    match_hostname(self.sock.getpeercert(), host)
                except CertificateError as exp:
                    self.log.exception("SSL hostname mismatch")
                    raise EppConnectionError(str(exp))
        self.greeting = EppResponse.from_xml(self.read().decode('utf-8'))

    def remote_info(self):
        """
        Method that returns the remote peer name
        """
        return '{}:{}'.format(*self.sock.getpeername())

    def hello(self, log_send_recv=False):
        """
        Method to send EppHello()
        """
        return self.send(EppHello(), log_send_recv=log_send_recv)

    # pylint: disable=c0103

    def login(self, clID, pw, newPW=None, raise_on_fail=True,
              obj_uris=None, extra_obj_uris=None, extra_ext_uris=None, clTRID=None):
        if not self.sock:
            self.connect(self.host, self.port)

        cmd = EppLoginCommand(
            obj_uris=obj_uris,
            extra_obj_uris=extra_obj_uris,
            extra_ext_uris=extra_ext_uris)
        cmd.clID = clID
        cmd.pw = pw
        if clTRID:
            cmd['epp']['command']['clTRID'] = clTRID
        if newPW:
            cmd.newPW = newPW
        r = self.send(cmd)
        if not r.success and raise_on_fail:
            raise EppLoginError(r)
        return r

    def logout(self, clTRID=None):
        cmd = EppLogoutCommand()
        if clTRID:
            cmd['epp']['command']['clTRID'] = clTRID
        return self.send(cmd)

    # pylint: enable=c0103

    def read(self):
        recvmeth = self.sock.read if self.ssl_enable else self.sock.recv
        siz = b''
        while len(siz) < 4:
            siz += recvmeth(4 - len(siz))
            if not siz:
                # empty string after read means EOF
                self.close()
                raise IOError("No size header read")

        size_remaining = siz = struct.unpack(">I", siz)[0] - 4
        data = b''
        while size_remaining:
            buf = recvmeth(size_remaining)
            if not buf:
                self.close()
                raise IOError(
                    "Short / no data read (expected %d bytes, got %d)" %
                    (siz, len(data)))
            size_remaining -= len(buf)
            data += buf

        return data
        #self.log.debug("read total %d bytes:\n%s\n" % (siz+4, data))

    def write(self, data):
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4 + len(data))

        if PY3:
            datad = str.encode(data) if type(data) is str else data
            writemeth(siz + datad)
        else:
            writemeth(siz + data)

    def write_many(self, docs):
        """
        For testing only.
        Writes multiple documents at once
        """
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        buf = []
        for doc in docs:
            buf.append(struct.pack(">I", 4 + len(doc)))
            buf.append(doc)
        writemeth(b''.join(buf))

    def send(self, doc, log_send_recv=True, extra_nsmap=None, strip_hints=True):
        self._gen_cltrid(doc)
        buf = doc.to_xml(force_prefix=True)
        if log_send_recv:
            self.log.debug("SEND %s: %s", self.remote_info(), buf.decode('utf-8'))
        self.write(buf)
        r_buf = self.read().decode('utf-8')
        if log_send_recv:
            self.log.debug("RECV %s: %s", self.remote_info(), r_buf)
        resp = EppResponse.from_xml(r_buf, extra_nsmap=extra_nsmap)
        if strip_hints:
            self.strip_hints(resp)
        doc.normalize_response(resp)
        return resp

    @staticmethod
    def strip_hints(data):
        """
        Remove various cruft from the given EppDoc
        (useful for responses where we don't care about _order etc.)
        """
        stack = deque([data])
        while len(stack):
            current = stack.pop()
            for key in list(current.keys()):
                if key in ('@xsi:schemaLocation', '_order'):
                    del current[key]
                else:
                    val = current[key]
                    if isinstance(val, dict):
                        # visit later
                        stack.append(val)
                    elif isinstance(val, list):
                        # visit each dict in the list
                        for elem in val:
                            if isinstance(elem, dict):
                                stack.append(elem)
        return data

    def batchsend(self, docs, readresponse=True, failfast=True, pipeline=False):
        """ Send multiple documents. If ``pipeline`` is True, it will
        send it in a single ``write`` call (which may have the effect
        of having more than one doc packed into a single TCP packet
        if they fits) """
        sent = 0
        recved = 0
        ndocs = len(docs)
        try:
            if pipeline:
                self.write_many(docs)
                sent = ndocs
            else:
                for doc in docs:
                    self.write(str(doc))
                    sent += 1
        # pylint: disable=w0702
        except:
            self.log.error(
                "Failed to send all commands (sent %d/%d)", sent, ndocs)
            if failfast:
                raise

        if not readresponse:
            return sent

        try:
            out = []
            for _ in xrange(sent):
                r_buf = self.read()
                out.append(EppResponse.from_xml(r_buf))
                recved += 1
        # pylint: disable=w0702
        except Exception as exp:
            self.log.error(
                "Failed to receive all responses (recv'ed %d/%d)", recved, sent)
            # pad the rest with None
            for _ in xrange(sent - len(out)):
                out.append(None)
        # pylint: enable=w0702
        return out

    def write_split(self, data):
        """
        For testing only.
        Writes the size header and first 4 bytes of the payload in one call,
        then the rest of the payload in another call.
        """
        writemeth = self.sock.sendall if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4 + len(data))
        self.log.debug("siz=%d", (4 + len(data)))
        writemeth(siz + data[:4])
        writemeth(data[4:])

    def write_splitsize(self, data):
        """
        For testing only.
        Writes 2 bytes of the header, then another two bytes,
        then the payload in another call.
        """
        writemeth = self.sock.sendall if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4 + len(data))
        self.log.debug("siz=%d", (4 + len(data)))
        writemeth(siz[:2])
        writemeth(siz[2:])
        writemeth(data)

    def write_splitall(self, data):
        """
        For testing only.
        Writes 2 bytes of the header, then another two bytes,
        then 4 bytes of the payload, then the rest of the payload.
        """
        writemeth = self.sock.sendall if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4 + len(data))
        self.log.debug("siz=%d", (4 + len(data)))
        writemeth(siz[:2])
        writemeth(siz[2:])
        writemeth(data[:4])
        writemeth(data[4:])

    def close(self):
        self.sock.close()
        self.sock = None

    @staticmethod
    def _gen_cltrid(doc):
        if isinstance(doc, (EppLoginCommand, EppCreateCommand, EppUpdateCommand,
                            EppDeleteCommand, EppTransferCommand, EppRenewCommand)):
            cmd_node = doc['epp']['command']
            if not cmd_node.get('clTRID'):
                cmd_node['clTRID'] = gen_trid()

    def _get_ssl_protocol_version(self):
        """
        This is a hack to get the negotiated protocol version of an SSL connection.

        WARNING: Do not use this on anything other than Python 2.7
        WARNING: Do not use on non-CPython.
        WARNING: only use it for debugging.
        WARNING: this will probably crash because we may be loading the wrong version of libssl

        From https://github.com/python-git/python/blob/master/Modules/_ssl.c
        the PySSLObject struct looks like this:

        typedef struct {
            PyObject_HEAD
            PySocketSockObject *Socket;	/* Socket on which we're layered */
            SSL_CTX*	ctx;
            SSL*		ssl;
            X509*		peer_cert;
            char		server[X509_NAME_MAXLEN];
            char		issuer[X509_NAME_MAXLEN];

        } PySSLObject;

        and this is stored as self.sock._sslobj so we pry open the mem location
        and call OpenSSL's SSL_get_version C API

        This technique is inspired by http://pyevolve.sourceforge.net/wordpress/?p=2171
        """
        assert self.ssl_enable, "don't use it on non-SSL sockets"
        assert self.sock._sslobj, "don't use it on non-SSL sockets"

        import ctypes
        import ctypes.util

        size_pyobject_head = ctypes.sizeof(
            ctypes.c_long) + ctypes.sizeof(ctypes.c_voidp)
        # skip PySocketSockObject* and SSL_CTX*
        real_ssl_offset = size_pyobject_head + ctypes.sizeof(ctypes.c_voidp) * 2
        ssl_p = ctypes.c_voidp.from_address(id(self.sock._sslobj) + real_ssl_offset)
        # libssl = ctypes.cdll.LoadLibrary('/usr/local/opt/openssl/lib/libssl.1.0.0.dylib')
        libssl = ctypes.cdll.LoadLibrary(ctypes.util.find_library('ssl'))
        if not libssl:
            return None
        libssl.SSL_get_version.restype = ctypes.c_char_p
        libssl.SSL_get_version.argtypes = [ctypes.c_void_p]
        ver = libssl.SSL_get_version(ssl_p)
        return ver
