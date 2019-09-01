#!/usr/bin/env python3
import logging
import shlex

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentType
from aiogram.utils.executor import start_polling

from hirnoty.security import run_handler_if_allowed
from hirnoty.settings import config

log = logging.getLogger(__name__)

ANY = ContentType.ANY
DOCUMENT = ContentType.DOCUMENT


def log_message(func):
    async def new_func(message):
        log.info('Got message: %s', message)
        await func(message)
    return new_func


class BotManager(object):
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.dispatcher = Dispatcher(self.bot)

    def register_handler(self, handler, commands=None, regexp=None,
            content_types=None):
        if content_types == None:
            content_types = ANY
        self.dispatcher.register_message_handler(
            log_message(run_handler_if_allowed(handler)),
            commands=commands, regexp=regexp,
            content_types=content_types)

    def run(self, on_startup=None):
        start_polling(self.dispatcher, on_startup=on_startup)
