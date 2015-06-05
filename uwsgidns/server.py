#!/usr/bin/env python
# encoding: utf-8

"""A custom DNS server resolving uWSGI subscribed domains to localhost."""

import copy
import binascii
import threading

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from dnslib import RR, QTYPE
from dnslib.server import BaseResolver, DNSRecord, UDPServer, DNSError

from uwsgidns.logging import logger
from uwsgidns.constants import LOCALHOST_ZONE, UWSGI_SUBSCRIPTIONS_KEY


class LocalDNSLogger(object):

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

    def __init__(self, proxy=False, upstream=None):
        # Prepare the RRs
        self.rrs = RR.fromZone(LOCALHOST_ZONE)

        # Set which domain to serve
        self.domains = set()

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

        self.lock = threading.Lock()

    def add_domain_from_uwsgi(self, uwsgi_dict):
        """
        If the uwsgi_dict is a valid subscription info dictionary,
        add its domain to the local domain list.
        """
        try:
            # Unicode sandwich
            domain = uwsgi_dict[UWSGI_SUBSCRIPTIONS_KEY.encode()]
            domain = domain.decode()

            if not domain.endswith("."):
                domain += "."

            if domain not in self.domains:
                with self.lock:
                    self.domains.add(domain)
                logger.debug("add_domain_from_uwsgi added {}".format(domain))
        except KeyError:
            logger.error("add_domain_from_uwsgi received a malformed dictionary.")

    def add_domains(self, domains):
        """
        Add each domain in domains to localhost.
        """
        domains = {
            d + "." if not d.endswith(".") else d
            for d in domains
        }

        if domains != self.domains:
            with self.lock:
                self.domains = domains
            logger.debug("add_domains added {}".format(domains))

    def resolve(self, request, handler):
        """
        If the requested domain is local, resolve it to localhost.
        Otherwise, proxy or drop the request.
        """

        reply = request.reply()
        qname = request.q.qname

        with self.lock:
            local_domain = str(qname) in self.domains

        if local_domain:  # If we have to handle this domain:
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
