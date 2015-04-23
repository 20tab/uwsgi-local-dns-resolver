#!/usr/bin/env python
# encoding: utf-8

import copy
import time
import json
import socket
import contextlib
import signal
import threading
import logging
import argparse
import binascii

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from dnslib import RR, QTYPE
from dnslib.server import BaseResolver, DNSServer, DNSRecord, UDPServer, DNSError

LOCALHOST_ZONE = ". 60 IN A 127.0.0.1"

UWSGI_SUBSCRIPTIONS = "subscriptions"
UWSGI_SUBSCRIPTIONS_KEY = "key"

event = threading.Event()
event.clear()


def setup_logging(level=logging.DEBUG):
    """Configure the module logging engine."""
    if level == logging.DEBUG:
        # For debugging purposes, log from everyone!
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging

    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
logger = None


class LocalDNSLogger:

    """
        The class provides a default set of logging functions for the various
        stages of the request handled by a DNSServer instance which are
        enabled/disabled by flags in the 'log' class variable.

        To customise logging create an object which implements the LocalDNSLogger
        interface and pass instance to DNSServer.

        The methods which the logger instance must implement are:

            log_recv          - Raw packet received
            log_send          - Raw packet sent
            log_request       - DNS Request
            log_reply         - DNS Response
            log_truncated     - Truncated
            log_error         - Decoding error
            log_data          - Dump full request/response
    """

    def log_recv(self, handler, data):
        logger.debug("Received: [%s:%d] (%s) <%d> : %s",
                     handler.client_address[0],
                     handler.client_address[1],
                     handler.protocol,
                     len(data),
                     binascii.hexlify(data))

    def log_send(self, handler, data):
        logger.debug("Sent: [%s:%d] (%s) <%d> : %s",
                     handler.client_address[0],
                     handler.client_address[1],
                     handler.protocol,
                     len(data),
                     binascii.hexlify(data))

    def log_request(self, handler, request):
        logger.debug("Request: [%s:%d] (%s) / '%s' (%s)",
                     handler.client_address[0],
                     handler.client_address[1],
                     handler.protocol,
                     request.q.qname,
                     QTYPE[request.q.qtype])
        self.log_data(request)

    def log_reply(self, handler, reply):
        logger.debug("Reply: [%s:%d] (%s) / '%s' (%s) / RRs: %s",
                     handler.client_address[0],
                     handler.client_address[1],
                     handler.protocol,
                     reply.q.qname,
                     QTYPE[reply.q.qtype],
                     ",".join([QTYPE[a.rtype] for a in reply.rr]))
        self.log_data(reply)

    def log_truncated(self, handler, reply):
        logger.debug("Truncated Reply: [%s:%d] (%s) / '%s' (%s) / RRs: %s",
                     handler.client_address[0],
                     handler.client_address[1],
                     handler.protocol,
                     reply.q.qname,
                     QTYPE[reply.q.qtype],
                     ",".join([QTYPE[a.rtype] for a in reply.rr]))
        self.log_data(reply)

    def log_error(self, handler, e):
        logger.error("Invalid Request: [%s:%d] (%s) :: %s",
                     handler.client_address[0],
                     handler.client_address[1],
                     handler.protocol,
                     e)

    def log_data(self, dnsobj):
        logger.debug("\n" + dnsobj.toZone("    ") + "\n")


class LocalResolver(BaseResolver):

    """Respond with fixed localhost responses to specified domains requests.
    Proxy to the upstream server the other or drop them (proxy argument).
    """

    def __init__(self, domains, proxy=False, upstream=None):
        # Prepare the RRs
        self.rrs = RR.fromZone(LOCALHOST_ZONE)

        # Set which domain to serve
        self.domains = domains

        # Set the upstream DNS server
        if proxy and upstream:
            try:
                self.upstream, self.upstream_port = upstream.split(":")
                self.upstream_port = int(self.upstream_port)
            except ValueError:
                self.upstream = upstream
                self.upstream_port = 53
            finally:
                self.proxy = True
        else:
            self.proxy = False

    def domains():
        """
        The domains @property.
        While setting it better make sure that each domain ends with a "." as per RFC.
        """

        def fget(self):
            return self._domains

        def fset(self, value):
            if value:
                self._domains = {
                    d if d.endswith(".") else d + "." for d in value}
        return locals()
    domains = property(**domains())

    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname

        if str(qname) in self.domains:  # If we have to handle this domain:
            # Replace labels with request label
            for rr in self.rrs:
                a = copy.copy(rr)
                a.rname = qname
                reply.add_answer(a)
        else:  # Otherwise proxy to upstream
            if not self.proxy:
                # Signal to the handler that this request has to be ignored.
                raise DNSError(
                    "{} not in local domain list and upstream proxy disabled.".format(str(qname))
                )
            else:
                if handler.protocol == 'udp':
                    proxy_r = request.send(self.upstream, self.upstream_port)
                else:
                    proxy_r = request.send(
                        self.upstream, self.upstream_port, tcp=True)
                reply = DNSRecord.parse(proxy_r)

        return reply


class ThreadedUDPServer(socketserver.ThreadingMixIn, UDPServer):

    """Threads, yeah, better use them!"""
    pass


def get_uwsgi_subscriptions(fastrouter_stats_address):
    """Ask the uWSGI subscription server for currently subscripted domains.

    :fastrouter_stats_address: Remote address:port of the uWSGI fastrouter stats server.
    :returns: The set of domains currently subscripted or None if any error.

    """
    domains = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        remote, port = fastrouter_stats_address.split(":")
        port = int(port)
    except ValueError:  # port was not specified, fallback to 80
        remote, port = fastrouter_stats_address, 80

    try:
        s.connect((remote, port))

        with contextlib.closing(s.makefile()) as f:
            stats = json.load(f)

            domains = {
                subscription_info[UWSGI_SUBSCRIPTIONS_KEY]
                for subscription_info in stats[UWSGI_SUBSCRIPTIONS]
            }
            logger.info("Got the following uWSGI subscriptions: %s.", domains)
    except socket.error:  # Basically a connection denied error
        # uWSGI is not running or we specified the wrong address:port
        logger.error(
            "Got connection denied error while trying to get subscription list.")
    finally:
        s.close()

    return domains


def serve_dns_forever(uwsgi_stats, event, proxy, upstream):
    """Start handling DNS requests. """
    while True:
        domains = get_uwsgi_subscriptions(uwsgi_stats)

        logger.info("uWSGI-DNS resolver is starting...")
        server_logger = LocalDNSLogger()
        resolver = LocalResolver(
            domains,
            proxy,
            upstream
        )
        server = DNSServer(
            resolver,
            address="localhost",
            server=ThreadedUDPServer,
            logger=server_logger
        )
        server.start_thread()

        while server.isAlive():
            if event.is_set():
                event.clear()
                domains = get_uwsgi_subscriptions(uwsgi_stats)
                resolver.domains = domains
            time.sleep(1)


def set_signal_handler():
    """Receiving a SIGINT signal will cause the DNS server to update the domain list. """
    signal.signal(signal.SIGINT, signal_handler)


def signal_handler(signal_number, stack_frame):
    """Signal handler.

    :signal_number: Signal number.
    :stack_frame: Stack frame.

    """
    if (signal_number == signal.SIGINT):
        event.set()


def create_parser():
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="DNS server that resolves to localhost uWSGI's HTTP subscripted domains."
    )

    parser.add_argument(
        "stats",
        type=str,
        metavar="uwsgi-HTTP-stats-URI",
        help="the URI (remote:port) to the uWSGI HTTP subscription stats server",
    )

    parser.add_argument(
        "-l",
        "--logging",
        choices=['CRITICAL',
                 'ERROR',
                 'WARNING',
                 'INFO',
                 'DEBUG',
                 'NOTSET'],
        default='ERROR',
        help="set the logging level"
    )

    parser.add_argument(
        "-p",
        "--proxy",
        action="store_true",
        help="proxy other requests to upstream DNS server (--upstream)"
    )

    parser.add_argument(
        "-u",
        "--upstream",
        metavar="upstream DNS server URI",
        default="8.8.8.8:53",
        type=str,
        help="the URI to the upstream DNS server (with --proxy), defaults to 8.8.8.8:53"
    )

    return parser


def main(args=None):
    """The main."""
    parser = create_parser()
    args = vars(parser.parse_args(args))

    log_mapping = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET,
    }

    log_level = log_mapping[args['logging']]
    global logger
    logger = setup_logging(log_level)

    set_signal_handler()
    serve_dns_forever(args['stats'], event, args['proxy'], args['upstream'])


if __name__ == '__main__':
    main()
