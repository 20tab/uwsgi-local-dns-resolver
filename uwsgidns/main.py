#!/usr/bin/env python
# encoding: utf-8

from __future__ import absolute_import

import argparse
import logging
import threading

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from dnslib.server import DNSServer

from uwsgidns.logging import logger
from uwsgidns.server import LocalResolver, LocalDNSLogger, ThreadedUDPServer
from uwsgidns.constants import LISTENER_HOST, LISTENER_PORT, DNS_HOST, DNS_PORT
from uwsgidns.listener import SubscriptionHandler
from uwsgidns.checker import SubscritionChecker


def start_subscription_listener(trigger):
    """Start a new thread with the subscription listener.

        :trigger: Check the UDPSubscriptionListener docstring.

    """
    def _start_listener():
        """Start the subscription listener."""
        server = socketserver.UDPServer((LISTENER_HOST, LISTENER_PORT), SubscriptionHandler)
        server.serve_forever()

    SubscriptionHandler.trigger = trigger

    thread = threading.Thread(target=_start_listener)
    thread.daemon = True

    logger.info("uWSGI subscription listener is starting...")
    thread.start()


def start_subscription_checker(subscription_server_uri, trigger):
    """
        Start polling the uWSGI subscription server.

        :subscription_server_uri: The URI (host:port) of the uWSGI subscription server
        :trigger: Check the SubscritionChecker docstring.
    """
    logger.info("uWSGI subscription checker is starting...")
    SubscritionChecker.trigger = trigger
    SubscritionChecker(subscription_server_uri)


def start_dns_server(proxy, upstream, subscription_server_uri=None):
    """Start handling DNS requests. """
    logger.info("uWSGI-DNS resolver is starting...")

    resolver = LocalResolver(
        proxy,
        upstream
    )

    dns_server = DNSServer(
        resolver=resolver,
        address=DNS_HOST,
        port=DNS_PORT,
        server=ThreadedUDPServer,
        logger=LocalDNSLogger()
    )

    # Start the subscription listener BEFORE the server.
    start_subscription_listener(resolver.add_domain_from_uwsgi)

    if subscription_server_uri:
        # Start the subscription checker BEFORE the server.
        start_subscription_checker(subscription_server_uri, resolver.add_domains)

    # And start the DNS server.
    dns_server.start()


def create_parser():
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="DNS server that resolves to localhost uWSGI's HTTP subscribed domains."
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

    parser.add_argument(
        "-s",
        "--stats",
        type=str,
        metavar="uwsgi-HTTP-stats-URI",
        default="127.0.0.1:5004",
        help="the URI (remote:port) to the uWSGI HTTP subscription stats server",
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
    logger.setLevel(log_level)

    start_dns_server(args['proxy'], args['upstream'], args['stats'])


if __name__ == '__main__':
    main()
