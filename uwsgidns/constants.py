#!/usr/bin/env python
# encoding: utf-8

LOCALHOST_ZONE = ". 60 IN A 127.0.0.1"

UWSGI_SUBSCRIPTIONS = "subscriptions"
UWSGI_SUBSCRIPTIONS_KEY = 'key'

LISTENER_HOST, LISTENER_PORT = "localhost", 9696
DNS_HOST, DNS_PORT = "localhost", 53

UWSGI_TIMEOUT_CHECKER = 30  # seconds
