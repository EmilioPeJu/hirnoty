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
        self._index = SimpleIndex(self._config["INDEX_DIR"])
        if getattr(self, 'doc_command', False):
            self._bot.register_handler(self.doc_command,
                content_types=[DOCUMENT])
        if getattr(self, 'video_command', False):
            self._bot.register_handler(self.video_command,
                content_types=[VIDEO])
        for (method_name, method) in inspect.getmembers(self):
            if method_name.endswith('_command'):
                command_name = method_name[0:-8]
                if command_name == "default" or command_name == 'doc':
                    continue
                commands = [command_name]
                log.info("Registering command %s", commands)
                self._bot.register_handler(method, commands)
        if getattr(self, 'default_command', False):
            # make sure this is last to not override others
            self._bot.register_handler(self.default_command, content_types=ANY)

    async def exec_command(self, message):
        parts = shlex.split(message["text"])
        command, args = parts[1], parts[2:]
        log.info("Executing command %s", command);
        runner = Runner(self._config, command, args)
        async for line in runner.work():
            await message.reply(line)


    async def join_command(self, message):
        topics = shlex.split(message["text"])[1:]
        for topic in topics:
            log.info("Subscribing to %s", topic)
            self._mq.subscribe(topic, message.reply)
            await message.reply(f"{topic}: Subscribed")

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
                message.video.file_id, # wtf there is no name?
                message.caption,
                message.reply,
                VIDEO)

    async def _download_and_index(self, file_id, file_name, caption, callback,
                                  content_type=None):
        if content_type == None:
            content_type = DOCUMENT
        sane_file_name = self._sanitize_file_name(file_name)
        file_path = path.join(self._config['DOWN_DIR'], sane_file_name)
        if not self._index.has_doc(file_id) and not path.exists(file_path):
            file_io = BytesIO()
            dst = await self._bot.bot.download_file_by_id(
                    file_id,
                    file_io)
            hash_o = hashlib.sha1()
            hash_o.update(file_io.getvalue())
            hash_ = hash_o.hexdigest()

            if self._index.has_hash(hash_):
                log.info('Data already downloaded')
                return

            with open(file_path, 'wb') as fhandler:
                fhandler.write(file_io.getvalue())

            base_file_name = path.splitext(sane_file_name)[0]
            terms = [base_file_name]
            for sep in (' ', '-', '_'):
                if sep in base_file_name:
                    terms.extend(base_file_name.split(sep))
            if caption:
                terms.extend(caption.split())
            terms = list(set(terms)) # make it unique
            doc = self._index.index_file(file_id, terms, sane_file_name, hash_,
                                         content_type)
            await callback(f"File indexed: {doc}")
        else:
            log.info('File already there')

    async def search_command(self, message):
        args = message['text'].split()[1:]
        for doc_id in self._index.search_words(args):
            metadata = self._index.get_metadata(doc_id)
            if not metadata:
                log.error('no metadata')
                return
            if self._index.not_uploaded(doc_id):

                file_path = path.join(self._config["DOWN_DIR"],
                                      metadata['filename'])

                if not path.exists(file_path):
                    log.error('File does not exist')
                    return

                log.info('Sending file %s', file_path)
                sent = await self._bot.bot.send_document(message.chat.id,
                                                         open(file_path, 'rb'))
                if sent:
                    self._index.update_docid(doc_id, sent.document.file_id)
                else:
                    log.error('Error while sending %s', file_path)

            else:
                log.info('Sending file with doc_id %s', doc_id)
                content_type = metadata.get('content_type', DOCUMENT)
                if content_type == VIDEO:
                    sent = await self._bot.bot.send_video(message.chat.id,
                                                          doc_id)
                elif content_type == DOCUMENT:
                    sent = await self._bot.bot.send_document(message.chat.id,
                                                             doc_id)

    async def index_command(self, message):
        parts = shlex.split(message['text'])
        sane_file_name = self._sanitize_file_name(parts[1])
        terms = parts[2:]
        base_file_name = path.splitext(sane_file_name)[0]
        terms.append(base_file_name)
        for sep in (' ', '-', '_'):
            if sep in base_file_name:
                terms.extend(base_file_name.split(sep))
        terms = list(set(terms))
        file_path = path.join(self._config["DOWN_DIR"], sane_file_name)
        if not path.exists(file_path):
            log.error('File not found')
            await message.reply(f"File not found")
            return
        with open(file_path, 'rb') as fhandle:
            data = fhandle.read()
        hash_o = hashlib.sha1()
        hash_o.update(data)
        hash_ = hash_o.hexdigest()
        doc = self._index.index_file(None, terms, sane_file_name, hash_,
                                     DOCUMENT)
        await message.reply(f"File indexed: {doc}")

    async def default_command(self, message):
        # for logging purposes
        pass
