import logging


class ExecutionContext(object):

    def __init__(self, host=None, port=None, ssl_key=None, ssl_cert=None,
                 ssl_cacerts=None, userid=None, passwd=None):
        self.host = host
        self.port = port
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert
        self.ssl_cacerts = ssl_cacerts
        self.userid = userid
        self.passwd = passwd
        self.max_ident = 0
        self.total_connected = 0  # ever connected
        self.num_connected = 0
        self.num_authenticated = 0
        self.failed_connections = 0  # ever connected
        self.num_commands_sent = 0
        self.num_responses_recved = 0

    def getLogger(self, obj):
        # is this atomic enough for threads? (fine if we're running in coroutine)
        i, self.max_ident = self.max_ident + 1, self.max_ident + 1
        adapter = logging.LoggerAdapter(logging.getLogger(__name__),
                                        dict(label=("%s%d" % (obj, i))))
        return adapter

    def connected(self):
        self.num_connected += 1
        self.total_connected += 1

    def disconnected(self):
        self.num_connected -= 1

    def failed_to_connect(self):
        self.failed_connections += 1

    def authenticated(self):
        self.num_authenticated += 1

    def sent_commands(self, count=1):
        self.num_commands_sent += count

    def recved_responses(self, count=1):
        self.num_responses_recved += count

    def print_stats(self):
        print "%5d Total connections" % self.total_connected
        print "%5d Failed" % self.failed_connections
        print "%5d Connected" % self.num_connected
        print "%5d Authenticated" % self.num_authenticated
        print "%5d Commands sent" % self.num_commands_sent
        print "%5d Responses received" % self.num_responses_recved
