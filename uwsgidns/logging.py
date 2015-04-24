#!/usr/bin/env python
# encoding: utf-8

"""Logging module."""

from __future__ import absolute_import

import logging


def setup_logging(level=logging.DEBUG):
    """Configure the module logging engine."""
    package_logger = logging.getLogger('uwsgidns')
    package_logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    package_logger.addHandler(handler)
    return package_logger
logger = setup_logging()
