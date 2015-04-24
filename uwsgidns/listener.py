#!/usr/bin/env python
# encoding: utf-8

import struct
import socket
import contextlib
import json

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from uwsgidns.logging import logger
from uwsgidns.constants import UWSGI_SUBSCRIPTIONS, UWSGI_SUBSCRIPTIONS_KEY


def uwsgi_packet_to_dict(blob):
    """Convert a uWSGI binary packet to a dictionary."""
    d = dict()
    _, packet_len, _ = struct.unpack("<BHB", blob[0:4])

    i = 4
    while i < packet_len:
        size, = struct.unpack("<H", blob[i:i + 2])
        i += 2
        key = blob[i:i + size]
        i += size

        size, = struct.unpack("<H", blob[i:i + 2])
        i += 2
        value = blob[i:i + size]
        i += size

        d[key] = value

    return d


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

            logger.debug("Got the following uWSGI subscriptions: %s.", domains)
    except socket.error:  # Basically a connection denied error
        # uWSGI is not running or we specified the wrong address:port
        logger.error(
            "Got connection denied error while trying to get subscription list.")
    finally:
        s.close()

    return domains


class SubscriptionHandler(socketserver.BaseRequestHandler):
    """Handle UDP subscription requests from uWSGI."""

    """
        This class property is called, if set, after handling a new uWSGI subscription.
        It has to be a callable accepting a uWSGI dictionary as argument.
    """
    trigger = None

    def handle(self):
        data = self.request[0]
        d = uwsgi_packet_to_dict(data)

        if callable(SubscriptionHandler.trigger):
            SubscriptionHandler.trigger(d)
