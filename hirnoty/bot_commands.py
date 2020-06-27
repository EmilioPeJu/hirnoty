#!/usr/bin/env python3
import hashlib
import inspect
import json
import logging
import re
import shlex
from io import BytesIO
from os import path

from hirnoty.bot import DOCUMENT, ANY, VIDEO
from hirnoty.file_manager import CompressingFileManager
from hirnoty.index import CompressingFileManager, SimpleIndex, FILE_PRESENT
from hirnoty.jobs import Runner, ScriptNotFound

log = logging.getLogger(__name__)


class Commands(object):
    CACHE_FILE = ".hirnoty.cache"

    def __init__(self, config, bot_manager, mq):
        self._bot = bot_manager
        self._mq = mq
        self._config = config
        self._fm = CompressingFileManager(self._config["INDEX_DIR"])
        self._index = SimpleIndex(self._config["INDEX_DIR"], self._fm,
                                  self._config["INVERTED_INDEX"])
        # we use this to know if a file was already sent to telegram
        # and also it maps from our index's entry id to telegram's file id
        self._file_id_cache = {}
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
        self._all_unsubscribers = {}
        self._load_cache()

    def _load_cache(self):
        if self._fm.contains(self.CACHE_FILE):
            log.info("Loading cache data")
            self._file_id_cache = json.load(self._fm.get_file(self.CACHE_FILE))

    def _save_cache(self):
        log.info("Saving cache data")
        self._fm.write_content(self.CACHE_FILE,
                               json.dumps(self._file_id_cache).encode())

    def close(self):
        self._index.close()
        self._save_cache()

    async def exec_command(self, message):
        parts = shlex.split(message["text"])
        command, args = parts[1], parts[2:]
        log.info("Executing command %s", command)
        runner = Runner(self._config["SCRIPT_DIR"], command, args)
        async for line in runner.work():
            await message.answer(line)

    async def join_command(self, message):
        args = message['text'].split()[1:]
        topic = " ".join(args)
        if self._all_unsubscribers.get(
                message["chat"]["id"], {}).get(topic):
            await message.answer(f"{topic}: Already subscribed")
            return
        log.info("Subscribing to %s", topic)
        self._mq.subscribe(topic, message.answer)
        self._all_unsubscribers. \
            setdefault(message["chat"]["id"], {})[topic] = \
            lambda: self._mq.unsubscribe(topic, message.answer)
        await message.answer(f"{topic}: Subscribed")

    async def leave_command(self, message):
        args = message['text'].split()[1:]
        topic = " ".join(args)
        unsubscribers = self._all_unsubscribers.get(message["chat"]["id"], {})
        unsubscribe = unsubscribers.get(topic)
        if unsubscribe:
            unsubscribe()
            del unsubscribers[topic]
            await message.answer(f"{topic}: Unsubscribed")

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
        try:
            dst = await self._bot.bot.download_file_by_id(file_id, file_io)
        except Exception as e:
            # we can still index without the content
            msg = f"Error downloading file: {e}"
            log.info(msg)
            await callback(msg)
        try:
            entry = self._index.add_entry(file_name, caption,
                                          file_io.getvalue(), file_id)
            await callback(f"File indexed: {entry.entry_id}")
        except FileExistsError as e:
            await callback(f"{e}")

    async def search_command(self, message):
        args = message['text'].split()[1:]
        text = " ".join(args)
        found = False
        for entry in self._index.search(text):
            found = True
            file_id = self._file_id_cache.get(entry.entry_id)
            if file_id:
                log.info("Found cached entry (%s, %s)", entry.entry_id,
                         file_id)
                sent = await self._bot.bot.send_document(message.chat.id,
                                                         file_id)
            elif entry.extra:  # extra field is used for file_id
                log.info("Found file id %s", entry.entry_id)
                sent = await self._bot.bot.send_document(message.chat.id,
                                                         entry.extra)
            elif entry.entry_type == FILE_PRESENT:
                log.info("Sending %s", entry.entry_id)
                sent = await self._bot.bot.send_document(message.chat.id,
                                                         (entry.filename,
                                                          self._index.get_file(
                                                              entry.entry_id)))
            else:
                sent = False

            if sent:
                self._file_id_cache[entry.entry_id] = sent.document.file_id
            else:
                msg = 'Error while sending %s' % entry.entry_id
                log.error(msg)
                await message.reply(msg)
        if not found:
            await message.reply("No file found")

    async def ping_command(self, message):
        await message.answer("pong")

    async def default_command(self, message):
        # for logging purposes
        pass
