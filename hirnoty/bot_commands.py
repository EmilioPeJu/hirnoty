#!/usr/bin/env python3
import hashlib
import inspect
import logging
import re
import shlex
from io import BytesIO
from os import path

from hirnoty.bot import DOCUMENT, ANY, VIDEO
from hirnoty.index import SimpleIndex
from hirnoty.jobs import Runner, ScriptNotFound

log = logging.getLogger(__name__)


class Commands(object):
    def __init__(self, config, bot_manager, mq):
        self._bot = bot_manager
        self._mq = mq
        self._config = config
        self._index = SimpleIndex(self._config["INDEX_DIR"],
                                  self._config["INVERTED_INDEX"])
        # we use this to know if a file was already sent to telegram
        # and also it maps from our index's file id to telegram's file id
        self._doc_cache = {}
        if getattr(self, 'doc_command', False):
            self._bot.register_handler(self.doc_command,
                                       content_types=[DOCUMENT])
        if getattr(self, 'video_command', False):
            self._bot.register_handler(self.video_command,
                                       content_types=[VIDEO])
        for (method_name, method) in inspect.getmembers(self):
            if method_name.endswith('_command'):
                command_name = method_name[0:-8]
                if command_name in ['default', 'doc', 'video']:
                    continue
                commands = [command_name]
                log.info("Registering command %s", commands)
                self._bot.register_handler(method, commands)
        if getattr(self, 'default_command', False):
            # make sure this is last to not override others
            self._bot.register_handler(self.default_command, content_types=ANY)

    def close(self):
        self._index.close()

    async def exec_command(self, message):
        parts = shlex.split(message["text"])
        command, args = parts[1], parts[2:]
        log.info("Executing command %s", command)
        runner = Runner(self._config["SCRIPT_DIR"], command, args)
        async for line in runner.work():
            await message.answer(line)

    async def join_command(self, message):
        topics = shlex.split(message["text"])[1:]
        for topic in topics:
            log.info("Subscribing to %s", topic)
            self._mq.subscribe(topic, message.answer)
            await message.answer(f"{topic}: Subscribed")

    @staticmethod
    def _sanitize_file_name(name):
        ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
                        "abcdefghijklmnñopqrstuvwxyz" \
                        "0123456789-_.áéíóúÁÉÍÓÚüÜçÇ ()"
        res = "".join([char for char in name if char in ALLOWED_CHARS])
        # protect against folder scalation
        while '..' in res:
            res = res.replace('..', '.')
        return res

    async def doc_command(self, message):
        if message.document:
            await self._download_and_index(message.document.file_id,
                                           message.document.file_name,
                                           message.caption,
                                           message.reply,
                                           DOCUMENT)

    async def video_command(self, message):
        if message.video:
            await self._download_and_index(message.video.file_id,
                                           message.video.file_id,
                                           message.caption,
                                           message.reply,
                                           VIDEO)

    async def _download_and_index(self, file_id, file_name, caption, callback,
                                  content_type=None):
        if content_type is None:
            content_type = DOCUMENT
        file_io = BytesIO()
        dst = await self._bot.bot.download_file_by_id(file_id, file_io)
        try:
            entry = self._index.add_entry(file_name, caption,
                                          file_io.getvalue())
            await callback(f"File indexed: {entry.fileid}")
        except FileExistsError as e:
            await callback(f"{e}")

    async def search_command(self, message):
        args = message['text'].split()[1:]
        text = " ".join(args)
        found = False
        for entry in self._index.search(text):
            found = True
            cached_id = self._doc_cache.get(entry.fileid)
            if cached_id:
                log.info("Found cached entry (%s, %s)", entry.fileid,
                         cached_id)
                sent = await self._bot.bot.send_document(message.chat.id,
                                                         cached_id)
                continue
            log.info("Sending %s", entry.fileid)
            sent = await self._bot.bot.send_document(message.chat.id,
                                                     (entry.filename,
                                                      self._index.get_file(
                                                          entry.fileid)))
            if sent:
                self._doc_cache[entry.fileid] = sent.document.file_id
            else:
                msg = 'Error while sending %s', file_path
                log.error(msg)
                await message.reply(msg)
        if not found:
            await message.reply("No file found")

    async def test_command(self, message):
        await message.reply(f"Hello world")

    async def default_command(self, message):
        # for logging purposes
        pass
