#!/usr/bin/env python
# encoding: utf-8

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from uwsgidns.utils import uwsgi_packet_to_dict


class SubscriptionHandler(socketserver.BaseRequestHandler):

    """Handle UDP subscription requests from uWSGI."""

    """
        trigger is called, if set, after handling a new uWSGI subscription.
        It MUST be a callable accepting a uWSGI dictionary as an argument.
    """
    trigger = None

    def handle(self):
        data = self.request[0]
        d = uwsgi_packet_to_dict(data)

        if callable(SubscriptionHandler.trigger):
            SubscriptionHandler.trigger(d)
