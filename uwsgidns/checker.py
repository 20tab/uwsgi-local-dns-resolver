#!/usr/bin/env python
# encoding: utf-8

import socket
import threading
import contextlib
import json

from uwsgidns.logging import logger
from uwsgidns.constants import UWSGI_SUBSCRIPTIONS, \
    UWSGI_SUBSCRIPTIONS_KEY, \
    UWSGI_TIMEOUT_CHECKER


class SubscritionChecker(object):

    """Periodically ask the uWSGI subscription server for subscribed domains."""

    """
        trigger is called, if set, after checking for new uWSGI subscriptions.
        It MUST be a callable accepting an iterable as an argument.
    """
    trigger = None

    def __init__(self, subscription_server):
        try:
            remote, port = subscription_server.split(":")
            port = int(port)
        except ValueError:  # port was not specified, fallback to 80
            remote, port = subscription_server, 80
        finally:
            self.remote, self.port = remote, port

        self._create_socket()

    def _start_timer(self):
        timer = threading.Timer(
            UWSGI_TIMEOUT_CHECKER,
            self._create_socket
        )
        timer.daemon = True
        timer.start()

    def _create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.connect((self.remote, self.port))
            self._poll()
        except socket.error:  # Basically a connection denied error
            # uWSGI is not running or we specified the wrong address:port
            logger.debug(
                "Error while connecting to uWSGI subscription server. "
                "We'll try again later..."
            )
            self.socket.close()

            # we'll try again later...
            self._start_timer()

    def _poll(self):
        with contextlib.closing(self.socket.makefile()) as f:
            f = self.socket.makefile()
            stats = json.load(f)

            domains = {
                subscription_info[UWSGI_SUBSCRIPTIONS_KEY]
                for subscription_info in stats[UWSGI_SUBSCRIPTIONS]
            }

            if domains:
                SubscritionChecker.trigger(domains)

        # ... and poll again later
        self._start_timer()
