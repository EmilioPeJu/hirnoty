#!/usr/bin/env python3
import logging
import zmq


def strlevel2level(strlevel):
    return {'info': logging.INFO,
            'error': logging.ERROR,
            'debug': logging.DEBUG}.get(strlevel, logging.INFO)


def setup_logging(strlevel, addr, topic):
    """ Setup logging

    Args:
        strlevel: logging level in string format
        addr: IP and port where to push logs using format IP:PORT
        topic: queue topic where the logs will be pushed
    """
    level = strlevel2level(strlevel)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level)
    logging.getLogger().addHandler(
        ZmqPushHandler(addr, topic)
    )


class ZmqPushHandler(logging.Handler):
    """
    A handler class which sends logs to the specified topic
    """
    def __init__(self, addr, topic):
        """ Initilise handler

        Args:
            addr: IP and port where to push logs using format IP:PORT
            topic: queue topic where the logs will be pushed
        """
        logging.Handler.__init__(self)
        self.topic = topic
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.connect(f"tcp://{addr}")

    def emit(self, record):
        msg = self.format(record)
        self.socket.send_multipart([self.topic.encode('utf-8'),
                                    msg.encode('utf-8')])
