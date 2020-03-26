#!/usr/bin/env python3
import asyncio
import logging

from hirnoty.bot import BotManager
from hirnoty.bot_commands import Commands
from hirnoty.jobs import Runner
from hirnoty.logconfig import setup_logging
from hirnoty.mq import MessageQueue
from hirnoty.settings import config

log = logging.getLogger(__name__)

LOG_TOPIC = "log"


def main():
    setup_logging(config["LOGLEVEL"], config["CONNECT_ADDRESS"], LOG_TOPIC)
    bot_manager = BotManager(config["TOKEN"])
    mq = MessageQueue(config["BIND_ADDRESS"])
    commands = Commands(config, bot_manager, mq)

    async def on_startup(dispatcher):
        asyncio.create_task(mq.receive_loop())

    bot_manager.run(on_startup)


if __name__ == "__main__":
    main()
