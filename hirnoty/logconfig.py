#!/usr/bin/env python3
import logging


def strlevel2level(strlevel):
    return {'info': logging.INFO,
            'error': logging.ERROR,
            'debug': logging.DEBUG}.get(strlevel, logging.INFO)


def setup_logging(strlevel):
    level = strlevel2level(strlevel)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level)
