#!/usr/bin/env python3
import asyncio


# Convenient decorator to test asyncio code, see:
def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper
