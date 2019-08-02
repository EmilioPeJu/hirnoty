#!/usr/bin/env python3
import shlex

from hirnoty.jobs import Runner, ScriptNotFound
from hirnoty.utils import split_args
_mq = None


def register_message_queue(mq):
    global _mq
    _mq = mq


async def execute_command(message):
    command, args = split_args(message["text"])
    runner = Runner(command, args)
    async for line in runner.work():
        await message.reply(line)


async def subscribe_command(message):
    global _mq
    topic, args = split_args(message["text"])
    _mq.subscribe(topic, message.reply)
    await message.reply(f"{topic}: Subscribed")
