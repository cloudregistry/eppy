from eppy.client import EppClient


class Connector(object):
    def __init__(self, ctx, behavior, host=None, port=None, ssl_key=None, ssl_cert=None,
                 logger=None, read_greeting=True):
        self.ctx = ctx
        self.host = host or ctx.host
        self.port = port or ctx.port
        self.ssl_key = ssl_key or ctx.ssl_key
        self.ssl_cert = ssl_cert or ctx.ssl_cert
        self.logger = logger or ctx.getLogger(self)
        self.read_greeting = read_greeting
        self.behavior = behavior


    def connect(self):
        do_ssl = self.ssl_cert is not None
        client = EppClient(host=self.host, port=self.port,
                           ssl_enable=do_ssl, ssl_keyfile=self.ssl_key, ssl_certfile=self.ssl_cert)
        try:
            client.connect(self.host, self.port)
            if self.read_greeting:
                client.read() # discard greeting
        except:
            self.ctx.failed_to_connect()
            raise
        self.ctx.connected()
        return client


    def __call__(self):
        try:
            client = self.connect()
            self.behavior(client)
        except:
            self.logger.exception("connector failed")

    def __str__(self):
        return self.__class__.__name__


