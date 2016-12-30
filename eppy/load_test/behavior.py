import random
import time
import eppy.doc
from past.builtins import xrange # Python 2 backwards compatibility
from .util import randid


class Behavior(object):

    def __init__(self, ctx, logger=None):
        self.ctx = ctx
        self.logger = logger or self.ctx.getLogger(self)

    def __call__(self, client):
        raise NotImplementedError


class LoginBehavior(Behavior):

    def __init__(self, ctx, userid=None, passwd=None):
        super(LoginBehavior, self).__init__(ctx)
        self.userid = userid or ctx.userid
        self.passwd = passwd or ctx.passwd

    def __call__(self, client):
        r = client.login(self.userid, self.passwd)
        if not r.success:
            return False
        self.ctx.authenticated()


class LoginNoWaitBehavior(Behavior):

    def __init__(self, ctx, userid=None, passwd=None):
        super(LoginNoWaitBehavior, self).__init__(ctx)
        self.userid = userid or ctx.userid
        self.passwd = passwd or ctx.passwd

    def __call__(self, client):
        cmd = eppy.doc.EppLoginCommand()
        cmd.clID = self.userid
        cmd.pw = self.passwd
        client.write(str(cmd))
        # not reading response!


class LoopBehavior(Behavior):

    def __init__(self, ctx, behavior, loop=1, sleep=None, sleep_min=0, sleep_max=5):
        super(LoopBehavior, self).__init__(ctx)
        self.behavior = behavior
        self.loop = int(loop)
        if sleep:
            if sleep is None:
                self.sleep = lambda: time.sleep(
                    sleep_min + random.random() * sleep_max)
            else:
                self.sleep = lambda: time.sleep(sleep)
        else:
            self.sleep = lambda: None

    def __call__(self, client):
        for i in xrange(self.loop):
            self.behavior(client)
            if i < self.loop - 1:  # don't sleep at the last one
                self.sleep()


class BatchSendBehavior(Behavior):

    def __init__(self, ctx, cmdgens, pipeline=False):
        super(BatchSendBehavior, self).__init__(ctx)
        self.cmdgens = cmdgens
        self.pipeline = pipeline

    def __call__(self, client):
        r = client.batchsend([cmdgen() for cmdgen in self.cmdgens],
                             readresponse=False,
                             failfast=False,
                             pipeline=self.pipeline)
        self.ctx.sent_commands(r)
        #self.ctx.recved_responses(len(filter(None, r)))


class SingleCommand(Behavior):

    def __init__(self, ctx, cmdgen):
        super(SingleCommand, self).__init__(ctx)
        self.cmdgen = cmdgen

    def __call__(self, client):
        cmd = self.cmdgen()
        r = client.send(cmd)
        self.ctx.sent_commands()
        self.ctx.recved_responses()
        self.logger.debug(r)
        return r


class NoopBehavior(Behavior):

    def __call__(self, client):
        pass


class LogoutBehavior(Behavior):

    def __call__(self, client):
        r = client.logout()
        return r


class BehaviorComposer(Behavior):

    def __init__(self, ctx, middle_behavior, userid=None,
                 passwd=None, wait_login=True):
        super(BehaviorComposer, self).__init__(ctx)

        login_behavior = (LoginBehavior(ctx, userid, passwd)
                          if wait_login else LoginNoWaitBehavior(ctx, userid, passwd))
        self.behaviors = [login_behavior,
                          middle_behavior,
                          LogoutBehavior(ctx)]

    def __call__(self, client):
        for b in self.behaviors:
            b(client)


def info_domain_factory(zone):
    def f():
        infocmd = eppy.doc.EppInfoDomainCommand()
        infocmd.name = "%s.%s" % (randid(), zone)
        return infocmd
    return f


def check_domain_factory(zone, num_domains=5):
    def f():
        cmd = eppy.doc.EppCheckDomainCommand()
        cmd.name = ["%s.%s" % (randid(), zone) for i in xrange(int(num_domains))]
        return cmd
    return f


def strbool(v):
    return str(v).strip().lower() in ('1', 'true')


BEHAVIORS = {
    'info_batch': lambda ctx, options, repeat=100:
    BatchSendBehavior(ctx, [info_domain_factory(options.zone)] * int(repeat)),
    'info_loop': lambda ctx, options, loop=20, sleep=1: LoopBehavior(ctx,
                                                                     SingleCommand(
                                                                         ctx, info_domain_factory(options.zone)),
                                                                     loop=loop, sleep=int(sleep)),
    'fatso': lambda ctx, options, num_domains=10: SingleCommand(ctx, check_domain_factory(options.zone, num_domains)),
}


def parse_behavior(ctx, options):
    behavior_type, _, opts = options.behavior.partition(':')
    opts = opts.split(',') if opts else []
    behavior = BehaviorComposer(ctx, BEHAVIORS[behavior_type](
        ctx, options, *opts), wait_login=(not options.no_wait))
    return behavior
