#!/usr/bin/env python
# encoding: utf-8

import struct


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
