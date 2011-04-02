import gevent.pool
import time
from .connector import Connector


class Session(object):
    def __init__(self, ctx, behavior=None):
        self.num_connectors = 1
        self.concurrency = 1
        self.spawn_interval = 0.1
        if not behavior:
            behavior = BehaviorComposer(ctx, NoopBehavior(ctx))
        self.connector = Connector(ctx, behavior)

    def start(self):
        pool = gevent.pool.Pool(size=self.concurrency)
        try:
            for i in xrange(1, self.num_connectors + 1):
                pool.spawn(self.connector)
                time.sleep(self.spawn_interval)

            pool.join()
        except KeyboardInterrupt:
            pass


