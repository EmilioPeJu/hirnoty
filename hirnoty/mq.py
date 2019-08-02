#!/usr/bin/env python3
import logging

import zmq
import zmq.asyncio
from hirnoty.settings import config

log = logging.getLogger(__name__)


class MessageQueue(object):

    def __init__(self, addr):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.PULL)
        log.info("Binding in address: %s", addr)
        self.socket.bind(f"tcp://{addr}")
        self._subscribers = {}

    def subscribe(self, topic, callback):
        log.info("Added callback to topic: %s", topic)
        self._subscribers.setdefault(topic, []).append(callback)
        self._subscribers.setdefault('all', []).append(callback)

    def unsubscribe(self, topic, callback):
        try:
            self._subscribers.get('all', []).remove(callback)
            self._subscribers.get(topic, []).remove(callback)
        except ValueError:
            pass

    async def notify(self, topic, data):

        for cb in self._subscribers.get(topic, []):
            await cb(f"{topic}: {data}")

    async def receive_loop(self):
        while True:
            topic, data = await self.socket.recv_multipart()
            log.debug("Receive %s from topic %s", data, topic)
            topic = topic.decode("utf-8")
            data = data.decode("utf-8")
            await self.notify(topic, data)
