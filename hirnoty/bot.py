#!/usr/bin/env python3
import logging
import shlex

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_polling

from hirnoty.security import run_handler_if_allowed
from hirnoty.settings import config

log = logging.getLogger(__name__)


class BotManager(object):
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.dispatcher = Dispatcher(self.bot)

    def register_command(self, command, handler):
        self.dispatcher.register_message_handler(
            run_handler_if_allowed(handler), commands=[command])

    def run(self, on_startup=None):
        start_polling(self.dispatcher, on_startup=on_startup)
