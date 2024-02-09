import logging
from logging import StreamHandler
from time import time, sleep
from typing import List

import requests

logger = logging.getLogger(__name__)


class VKTLoggerHandler(StreamHandler):

    def __init__(self, api_url: str, token: str, chats: List[str], timeout: int = 10):
        """
        Setup VKTLoggerHandler class

        :param api_url: server api url. Ask @metabot
        :param token: vk teams bot token to log form
        :param chats: list of chat_id to log to
        :param timeout: seconds for retrying to send log if error occupied
        """

        super().__init__()
        self.base_url = api_url
        self.token = token
        self.chats = chats
        self.timeout = timeout

    def emit(self, record):
        msg = self.format(record)
        for chat_id in self.chats:
            t0 = time()
            while time() - t0 < self.timeout:
                try:
                    requests.get(
                        url=self.base_url + "messages/sendText",
                        params={
                            "token": self.token,
                            "chatId": chat_id,
                            "parseMode": "HTML",
                            "text": msg
                        }
                    )
                    break
                except Exception as ex:
                    logger.exception("Exception while sending %s to %s:", msg, chat_id)
                    sleep(1)