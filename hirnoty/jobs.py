#!/usr/bin/env python3
import asyncio
import logging
import subprocess
import threading
from os import X_OK, access, path

log = logging.getLogger(__name__)


class ScriptNotFound(Exception):
    pass


class Runner(object):

    def __init__(self, script_dir, template, args):
        self.script_dir = script_dir
        self.template = template
        self.process = None
        self.command = self._get_script_path(self.template)
        if isinstance(args, list):
            self.args = args
        else:
            self.args = [args]
        self._started = False

    def _get_script_path(self, template):
        safe_template = self._sanitize_template(template)
        for ext in ("", ".sh", ".py"):
            script_path = path.join(self.script_dir, "{}{}"
                                    .format(safe_template, ext))
            if access(script_path, X_OK):
                return script_path

        raise ScriptNotFound()

    @staticmethod
    def _sanitize_template(template):
        ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
                        "abcdefghijklmnopqrstuvwxyz" \
                        "0123456789-"
        return "".join([char for char in template if char in ALLOWED_CHARS])

    async def work(self):
        if self._started:
            log.error("trying to rerun a job")
            return
        self.process = await asyncio.create_subprocess_exec(
            self.command, *self.args, stdout=asyncio.subprocess.PIPE)

        pid = self.process.pid

        def format_output(text):
            text = text.decode("utf-8")
            return f"{pid}: {text}"

        while True:
            data = await self.process.stdout.readline()
            if not data:
                break
            yield format_output(data)

        rc = await self.process.wait()
        yield f"{pid}: Finished with rc {rc}"
        self._started = True
