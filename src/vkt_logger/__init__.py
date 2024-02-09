from .handler import *

import logging
from typing import List


def setup(base_logger: logging.Logger = logging.getLogger(),
          api_url: str = '',
          token: str = '',
          chats: List[str] = [],
          timeout: int = 10,
          vkt_format: str = '<b>%(name)s:%(levelname)s</b> - <code>%(message)s</code>'):
    """
    Setup TgLogger

    :param api_url: server api url. Ask @metabot
    :param base_logger: base logging.Logger obj
    :param token: vk teams bot token to log form
    :param chats: list of chat_id to log to
    :param timeout: seconds for retrying to send log if error occupied
    :param vkt_format: logging format for tg messages (html parse mode)

    :return: logging.StreamHandler
    """
    # Logging format
    formatter = logging.Formatter(vkt_format)

    # Setup TgLoggerHandler
    vkt_handler = VKTLoggerHandler(
        api_url=api_url,
        token=token,
        chats=chats,
        timeout=timeout  # default value is 10 seconds
    )
    vkt_handler.setFormatter(formatter)
    base_logger.addHandler(vkt_handler)

    return vkt_handler
