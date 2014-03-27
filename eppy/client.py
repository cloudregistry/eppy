try:
    # use gevent if available
    import gevent.socket as socket
    import gevent.ssl as ssl
except ImportError:
    import socket
    import ssl

import struct
import logging
from .doc import EppResponse, EppHello, EppLoginCommand, EppLogoutCommand


class EppClient():
    def __init__(self, host=None, port=700, ssl_enable=True, ssl_keyfile=None, ssl_certfile=None, ssl_cacerts=None):
        self.host = host
        self.port = port
        self.ssl_enable = ssl_enable
        self.keyfile = ssl_keyfile
        self.certfile = ssl_certfile
        self.cacerts = ssl_cacerts
        self.log = logging.getLogger(__name__)
        self.sock = None
        self.greeting = None


    def connect(self, host, port=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port or self.port))
        self._sock = self.sock
        if self.ssl_enable:
            self.sock = ssl.wrap_socket(self.sock, self.keyfile, self.certfile, server_side=False, cert_reqs=ssl.CERT_REQUIRED, ca_certs=self.cacerts)


    def hello(self):
        return self.send(EppHello())

    def login(self, clID, pw):
        if not self.sock:
            self.connect(self.host, self.port)
            self.greeting = EppResponse.from_xml(self.read())

        cmd = EppLoginCommand()
        cmd.clID = clID
        cmd.pw = pw
        return self.send(cmd)


    def logout(self):
        cmd = EppLogoutCommand()
        return self.send(cmd)


    def read(self):
        #self.log.debug("reading...")
        recvmeth = self.sock.read if self.ssl_enable else self.sock.recv
        siz = recvmeth(4)
        if not siz:
            self.close()
            raise IOError("No size header read")

        siz = struct.unpack(">I", siz)[0] - 4
        #self.log.debug("reading %d bytes\n" % (siz,))
        data = recvmeth(siz)
        if not data:
            self.close()
            raise IOError("No data read (expected %d bytes)" % siz)

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



    def send(self, doc):
        self.write(str(doc))
        r = self.read()
        return EppResponse.from_xml(r)


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
        self._sock.close()

