from gevent import monkey; monkey.patch_all()
import gevent
import gevent.pool
from eppy.load_test import *
import sys
from optparse import OptionParser



def main():
    parser = OptionParser(usage="%prog <userid> <passwd>")
    parser.add_option('-c', type=int, dest='concurrency', default=1, help='number of concurrent connections')
    parser.add_option('-n', type=int, dest='num_connectors', default=1, help='number of connections to make')
    parser.add_option('--behavior', default='info_loop')
    parser.add_option('--no-wait', action='store_true', default=True)
    parser.add_option('--host', default='localhost', help='EPP host to connect to')
    parser.add_option('--port', '-p', default=700, type=int, help='EPP port to connect to')
    parser.add_option('--ssl-key', default='certs/client-key.pem')
    parser.add_option('--ssl-cert', default='certs/client-cert.pem')
    parser.add_option('--zone')
    (options, args) = parser.parse_args()

    if len(args) < 2:
        print >> sys.stderr, "No userid/passwd specified"
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    logger = logging.getLogger()


    ctx = ExecutionContext(host=options.host,
                           port=options.port,
                           ssl_key=options.ssl_key,
                           ssl_cert=options.ssl_cert,
                           userid=args[0],
                           passwd=args[1])


    behavior = parse_behavior(ctx, options)
    session = Session(ctx, behavior)
    session.concurrency = options.concurrency
    session.num_connectors = options.num_connectors

    try:
        session.start()
    finally:
        ctx.print_stats()

if __name__ == '__main__':
    main()

#chaos
#swarm
#swamp, flood
#bezerk
#ballistic
#session has a connector, looper, bezerk modifier, 


