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
from .exceptions import EppLoginError, EppConnectionError
from .doc import (EppResponse, EppHello, EppLoginCommand, EppLogoutCommand,
                  EppCreateCommand, EppUpdateCommand, EppRenewCommand, EppTransferCommand, EppDeleteCommand)
from .utils import gen_trid
from backports.ssl_match_hostname import match_hostname, CertificateError


class EppClient(object):
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
        # `ssl_ciphers`, if given, should be a string (https://www.openssl.org/docs/apps/ciphers.html)
        self.ssl_ciphers = ssl_ciphers  # if not given, use the default in Python version (`ssl._DEFAULT_CIPHERS`)
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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.socket_connect_timeout)  # connect timeout
        self.sock.connect((host, port or self.port))
        self.sock.settimeout(self.socket_timeout)  # regular timeout
        if self.ssl_enable:
            self.sock = ssl.wrap_socket(self.sock, self.keyfile, self.certfile,
                                        ssl_version=self.ssl_version,
                                        ciphers=self.ssl_ciphers,
                                        server_side=False,
                                        cert_reqs=self.cert_required,
                                        ca_certs=self.cacerts)
            if self.validate_hostname:
                try:
                    match_hostname(self.sock.getpeercert(), host)
                except CertificateError, e:
                    self.log.exception("SSL hostname mismatch")
                    raise EppConnectionError(str(e))


    def remote_info(self):
        return '{}:{}'.format(*self.sock.getpeername())


    def hello(self, log_send_recv=False):
        return self.send(EppHello(), log_send_recv=log_send_recv)

    def login(self, clID, pw, newPW=None, raise_on_fail=True, obj_uris=None, extra_obj_uris=None, extra_ext_uris=None,
              clTRID=None):
        if not self.sock:
            self.connect(self.host, self.port)
            self.greeting = EppResponse.from_xml(self.read())

        cmd = EppLoginCommand(obj_uris=obj_uris, extra_obj_uris=extra_obj_uris, extra_ext_uris=extra_ext_uris)
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


    def read(self):
        recvmeth = self.sock.read if self.ssl_enable else self.sock.recv
        siz = ''
        while len(siz) < 4:
            siz += recvmeth(4 - len(siz))
            if not siz:
                # empty string after read means EOF
                self.close()
                raise IOError("No size header read")

        size_remaining = siz = struct.unpack(">I", siz)[0] - 4
        data = ''
        while size_remaining:
            buf = recvmeth(size_remaining)
            if not buf:
                self.close()
                raise IOError("Short / no data read (expected %d bytes, got %d)" % (siz, len(data)))
            size_remaining -= len(buf)
            data += buf

        return data
        #self.log.debug("read total %d bytes:\n%s\n" % (siz+4, data))


    def write(self, data):
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4+len(data))
        writemeth(siz + data)


    def write_many(self, docs):
        """
        For testing only.
        Writes multiple documents at once
        """
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        buf = []
        for doc in docs:
            buf.append(struct.pack(">I", 4+len(doc)))
            buf.append(doc)
        writemeth(''.join(buf))


    def send(self, doc, log_send_recv=True, extra_nsmap=None, strip_hints=True):
        self._gen_cltrid(doc)
        buf = doc.to_xml(force_prefix=True).encode('utf-8')
        if log_send_recv:
            self.log.debug("SEND %s: %s", self.remote_info(), buf)
        self.write(buf)
        r = self.read()
        if log_send_recv:
            self.log.debug("RECV %s: %s", self.remote_info(), r)
        resp = EppResponse.from_xml(r, extra_nsmap=extra_nsmap)
        if strip_hints:
            self.strip_hints(resp)
        doc.normalize_response(resp)
        return resp

    def strip_hints(self, data):
        """
        Remove various cruft from the given EppDoc (useful for responses where we don't care about _order etc.
        """
        stack = deque([data])
        while len(stack):
            current = stack.pop()
            for k in list(current.keys()):
                if k in ('@xsi:schemaLocation', '_order'):
                    del current[k]
                else:
                    v = current[k]
                    if isinstance(v, dict):
                        # visit later
                        stack.append(v)
                    elif isinstance(v, list):
                        # visit each dict in the list
                        for elem in v:
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
        except:
            self.log.error("Failed to send all commands (sent %d/%d)" % (sent, ndocs))
            if failfast:
                raise

        if not readresponse:
            return sent

        try:
            out = []
            for _ in xrange(sent):
                r = self.read()
                out.append(EppResponse.from_xml(r))
                recved += 1
        except:
            self.log.error("Failed to receive all responses (recv'ed %d/%d)" % (recved, sent))
            # pad the rest with None
            for _ in xrange(sent-len(out)):
                out.append(None)

        return out


    def write_split(self, data):
        """
        For testing only.
        Writes the size header and first 4 bytes of the payload in one call,
        then the rest of the payload in another call.
        """
        writemeth = self.sock.sendall if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4+len(data))
        self.log.debug("siz=%d" % (4+len(data)))
        writemeth(siz + data[:4])
        writemeth(data[4:])


    def write_splitsize(self, data):
        """
        For testing only.
        Writes 2 bytes of the header, then another two bytes,
        then the payload in another call.
        """
        writemeth = self.sock.sendall if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4+len(data))
        self.log.debug("siz=%d" % (4+len(data)))
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
        siz = struct.pack(">I", 4+len(data))
        self.log.debug("siz=%d" % (4+len(data)))
        writemeth(siz[:2])
        writemeth(siz[2:])
        writemeth(data[:4])
        writemeth(data[4:])

    def close(self):
        self.sock.close()
        self.sock = None

    def _gen_cltrid(self, doc):
        if isinstance(doc, (EppLoginCommand, EppCreateCommand, EppUpdateCommand, EppDeleteCommand, EppTransferCommand, EppRenewCommand)):
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

        size_pyobject_head = ctypes.sizeof(ctypes.c_long) + ctypes.sizeof(ctypes.c_voidp)
        real_ssl_offset = size_pyobject_head + ctypes.sizeof(ctypes.c_voidp) * 2 # skip PySocketSockObject* and SSL_CTX*
        ssl_p = ctypes.c_voidp.from_address(id(self.sock._sslobj) + real_ssl_offset)
        # libssl = ctypes.cdll.LoadLibrary('/usr/local/opt/openssl/lib/libssl.1.0.0.dylib')
        libssl = ctypes.cdll.LoadLibrary(ctypes.util.find_library('ssl'))
        if not libssl:
            return None
        libssl.SSL_get_version.restype = ctypes.c_char_p
        libssl.SSL_get_version.argtypes = [ctypes.c_void_p]
        ver = libssl.SSL_get_version(ssl_p)
        return ver
