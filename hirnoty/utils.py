#!/usr/bin/env python3
from os import path


def get_source(filename=""):
    return path.join(path.dirname(path.abspath(__file__)), filename)
