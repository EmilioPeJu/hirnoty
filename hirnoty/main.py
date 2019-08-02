#!/usr/bin/env python3
import asyncio
import logging

from hirnoty.bot import BotManager
from hirnoty.bot_commands import (execute_command, subscribe_command,
                                  register_message_queue)
from hirnoty.jobs import Runner
from hirnoty.logconfig import setup_logging
from hirnoty.mq import MessageQueue
from hirnoty.settings import config

log = logging.getLogger(__name__)


async def on_startup(dispatcher):
    mq = MessageQueue(config["BIND_ADDRESS"])
    register_message_queue(mq)
    asyncio.create_task(mq.receive_loop())


def main():
    setup_logging(config["LOGLEVEL"])
    bot = BotManager(config["TOKEN"])
    bot.register_command('exec', execute_command)
    bot.register_command('subs', subscribe_command)
    # this starts the event loop
    bot.run(on_startup)


if __name__ == "__main__":
    main()
