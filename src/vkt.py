import logging

import requests


logger = logging.getLogger(__name__)


class Bot:
    base_url = 'https://api.internal.myteam.mail.ru/bot/v1/'

    def __init__(self, token: str, base_url: str = ''):
        self.token = token
        if base_url:
            self.base_url = base_url

    def send_message(self, text: str, chat_id: str, inline_kb: str = ''):
        """
        Отправляет сообщение в vk teams
        :param text: текст сообщения
        :param chat_id: адресат
        :param inline_kb: клавиатура (см. api vk teams)
        """

        logger.info(f"Sending message to: {chat_id}")
        params = {
            "token": self.token,
            "chatId": chat_id,
            "parseMode": "MarkdownV2",
            "text": text
        }
        if inline_kb:
            params.update(inlineKeyboardMarkup=inline_kb)

        resp = requests.get(
            url=self.base_url + "messages/sendText",
            params=params
        )
        logger.info(f"Server answer: {resp.text}")
