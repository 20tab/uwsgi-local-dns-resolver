#!/usr/bin/env python
# encoding: utf-8


def application(env, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b"What are you looking at?!"]
