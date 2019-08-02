#!/usr/bin/env python3
import shlex


def split_args(text):
    splitted_text = shlex.split(text)
    command = splitted_text[1]
    args = splitted_text[2:]
    return (command, args)
