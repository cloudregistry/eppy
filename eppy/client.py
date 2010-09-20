try:
    # use gevent if available
    import gevent.socket as socket
    print "YAY!"
except ImportError:
    import socket

import struct
import logging
from .doc import EppResponse, EppLoginCommand


LOGIN_XML = """<epp xmlns="urn:ietf:params:xml:ns:epp-1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:ietf:params:xml:ns:epp-1.0 epp-1.0.xsd">
  <command>
    <login>
      <clID>root</clID> 
      <pw>hahawebo</pw> 
       <options>
         <version>1.0</version>
         <lang>en</lang>
       </options>
       <svcs>
         <objURI>urn:ietf:params:xml:ns:domain-1.0</objURI>
         <objURI>urn:ietf:params:xml:ns:host-1.0</objURI>
         <objURI>urn:ietf:params:xml:ns:contact-1.0</objURI>
       </svcs>
     </login>
     <clTRID>6Idjqb5LpfTleoFYnwrN</clTRID> 
  </command>
</epp>
"""


class EppClient():
    def __init__(self, host=None, port=700, ssl_enable=True, ssl_keyfile=None, ssl_certfile=None):
        self.host = host
        self.port = port
        self.ssl_enable = ssl_enable
        self.keyfile = ssl_keyfile
        self.certfile = ssl_certfile
        self.log = logging.getLogger(__name__)
        self.sock = None


    def connect(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self._sock = self.sock
        if self.ssl_enable:
            self.sock = socket.ssl(self.sock, self.keyfile, self.certfile)


    def login(self, clID, pw):
        if not self.sock:
            self.connect(self.host, self.port)
            # XXX: ignore greeting
            r = self.read()

        cmd = EppLoginCommand()
        cmd.clID = clID
        cmd.pw = pw
        return self.send(cmd)

    def read(self):
        #self.log.debug("reading...")
        recvmeth = self.sock.read if self.ssl_enable else self.sock.recv
        siz = recvmeth(4)
        siz = struct.unpack(">I", siz)[0] - 4
        #self.log.debug("reading %d bytes\n" % (siz,))
        data = recvmeth(siz)
        return data
        #self.log.debug("read total %d bytes:\n%s\n" % (siz+4, data))


    def write(self, data):
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4+len(data))
        writemeth(siz + data)


    def send(self, doc):
        self.write(doc.to_xml())
        r = self.read()
        return EppResponse.from_xml(r)


    def write_pipeline(self, data1, data2):
        """
        For testing only.
        Writes two commands at once
        """
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        siz1 = struct.pack(">I", 4+len(data1))
        siz2 = struct.pack(">I", 4+len(data2))
        writemeth(siz1 + data1 + siz2 + data2)


    def write_split(self, data):
        """
        For testing only.
        Writes the size header and first 4 bytes of the payload in one call,
        then the rest of the payload in another call.
        """
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
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
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
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
        writemeth = self.sock.write if self.ssl_enable else self.sock.sendall
        siz = struct.pack(">I", 4+len(data))
        self.log.debug("siz=%d" % (4+len(data)))
        writemeth(siz[:2])
        writemeth(siz[2:])
        writemeth(data[:4])
        writemeth(data[4:])

    def close(self):
        self._sock.close()




if __name__ == '__main__':
    import sys
    import time
    import logging
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    epp = EppClient(logging.getLogger('root'), True, '/opt/cr/doc/certs/client.key', '/opt/cr/doc/certs/client.pem')
    epp.connect('localhost', 7700)
    epp.read()
    epp.write_split(LOGIN_XML)
    epp.read()
    epp.close()
    time.sleep(2)

    logging.debug("splitsize")
    epp = EppClient(logging.getLogger('root'), True, '/opt/cr/doc/certs/client.key', '/opt/cr/doc/certs/client.pem')
    epp.connect('localhost', 7700)
    epp.read()
    epp.write_splitsize(LOGIN_XML)
    epp.close()
    time.sleep(1)

    logging.debug("splitsize")
    epp = EppClient(logging.getLogger('root'), True, '/opt/cr/doc/certs/client.key', '/opt/cr/doc/certs/client.pem')
    epp.connect('localhost', 7700)
    epp.read()
    epp.write_splitall(LOGIN_XML)
    epp.close()

    logging.debug("two at one go")
    epp = EppClient(logging.getLogger('root'), True, '/opt/cr/doc/certs/client.key', '/opt/cr/doc/certs/client.pem')
    epp.connect('localhost', 7700)
    epp.read()
    epp.write_pipeline(LOGIN_XML, LOGIN_XML)
    epp.read()
    epp.read()
    epp.close()
