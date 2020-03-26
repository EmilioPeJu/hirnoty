import asyncio
import logging

from hirnoty.settings import config

log = logging.getLogger(__name__)


def check_otp(message):
    OTP = config["OTP"]
    text = message["text"]
    if OTP is None:
        return True

    with open(OTP, "r") as fhandler:
        data = fhandler.read().split("\n")

    if not data:
        return False

    if text.endswith(data[-1]):
        with open(OTP, "w") as fhandler:
            fhandler.write("\n".join(data[:-1]))
        message["text"] = text[:-len(data[-1])]
        return True

    return False


def check_acl(user_id):
    return config['ACL'] is None or user_id in config['ACL']


async def temporal_ban(user_id):
    ACL = config["ACL"]
    if ACL is None:
        return
    log.info('Temporary banning %d', user_id)
    ACL.remove(user_id)
    await asyncio.sleep(30)
    ACL.add(user_id)


def run_handler_if_allowed(func):
    OTP = config["OTP"]

    async def new_func(message):
        user_id = message['from']['id']
        if not check_acl(user_id):
            log.info(f'ACL: Unallowed access attempted: {str(message)}')
            return
        if not check_otp(message):
            log.info(f'OTP: Unallowed access attempted: {str(message)}')
            await temporal_ban(user_id)
            return
        await func(message)
    return new_func
