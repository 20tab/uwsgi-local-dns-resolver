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

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from dnslib import RR
from dnslib.server import BaseResolver, DNSServer, DNSRecord, UDPServer

LOCALHOST_ZONE = ". 60 IN A 127.0.0.1"

UWSGI_SUBSCRIPTIONS_STATS = "127.0.0.1:5004"
UWSGI_SUBSCRIPTIONS = "subscriptions"
UWSGI_SUBSCRIPTIONS_KEY = "key"

UPSTREAM_SERVER = "8.8.8.8"
UPSTREAM_SERVER_PORT = 53

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

logger = setup_logging()


class LocalResolver(BaseResolver):

    """Respond with fixed localhost responses to specified domains requests.
    Proxy to the upstream server the other.
    """

    def __init__(self, domains, upstream, upstream_port):
        # Prepare the RRs
        self.rrs = RR.fromZone(LOCALHOST_ZONE)

        # Set which domain to serve
        self.domains = domains

        # Set the upstream DNS server
        self.upstream, self.upstream_port = upstream, upstream_port

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
            if handler.protocol == 'udp':
                proxy_r = request.send(self.upstream, self.upstream_port)
            else:
                proxy_r = request.send(
                    self.upstream, self.upstream_port, tcp=True)
            reply = DNSRecord.parse(proxy_r)

        return reply

        # Signal to the handler that this request has to be ignored.
        # raise DNSError("DNS not in local domain list.")


class ThreadedUDPServer(socketserver.ThreadingMixIn, UDPServer):

    """Threads, yeah, better use them!"""
    pass


def get_uwsgi_subscriptions(fastrouter_stats_address):
    """Ask the uWSGI subscription server for currently subscripted domains.

    :fastrouter_stats_address: Remote address:port of the uWSGI fastrouter stat server.
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


def serve_dns_forever(event, upstream, upstream_port=53):
    """Start handling DNS requests. """
    while True:
        domains = get_uwsgi_subscriptions(UWSGI_SUBSCRIPTIONS_STATS)

        logger.info("Starting local DNS resolver...")
        resolver = LocalResolver(domains, upstream, upstream_port)
        server = DNSServer(
            resolver,
            address="localhost",
            server=ThreadedUDPServer,
        )
        server.start_thread()

        while server.isAlive():
            if event.is_set():
                event.clear()
                domains = get_uwsgi_subscriptions(UWSGI_SUBSCRIPTIONS_STATS)
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


def main():
    """The main, what else? """
    set_signal_handler()
    serve_dns_forever(event, UPSTREAM_SERVER, UPSTREAM_SERVER_PORT)


if __name__ == '__main__':
    main()
