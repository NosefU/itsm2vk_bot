import logging

import requests


logger = logging.getLogger(__name__)


class Bot:
    """
    VK Teams бот
    """

    base_url = 'https://api.internal.myteam.mail.ru/bot/v1/'
    last_event_id = 0

    def __init__(self, token: str, base_url: str = ''):
        """
        :param token: VK Teams bot token, получать у @metabot
        :param base_url: url для bot api, получать у @metabot
        """
        self.token = token
        if base_url:
            self.base_url = base_url
        self.nickname = self.get_self_nick()

    def get_self_nick(self):
        """
        Бот получает собственный никнейм и сохраняет его в соответствующем поле
        """
        params = {
            "token": self.token,
        }
        resp = requests.get(
            url=self.base_url + "/self/get",
            params=params
        )
        return resp.json()['nick']

    def send_message(self, text: str, chat_id: str, inline_kb: str = ''):
        """
        Отправляет сообщение в VK Teams

        :param text: текст сообщения
        :param chat_id: адресат
        :param inline_kb: клавиатура (см. api vk teams)
        """

        logger.info(f"Sending message to: {chat_id}")
        params = {
            "token": self.token,
            "chatId": chat_id,
            "parseMode": "HTML",
            "text": text
        }
        if inline_kb:
            params.update(inlineKeyboardMarkup=inline_kb)

        resp = requests.get(
            url=self.base_url + "messages/sendText",
            params=params
        )
        logger.info(f"Server answer: {resp.text}")

    def get_events(self, event_types: list[str] = None) -> list[dict]:
        """
        Вычитывает новые события для бота и возвращает отфильтрованные по типу

        :param event_types: список типов желаемых событий (см. bot api).
                            Если не передать ничего, то вернёт все доступные события
        :return: отфильтрованный список новых событий
        """
        if not event_types:
            logger.debug(f"Checking all events")
        else:
            logger.debug(f"Checking event types: " + ", ".join(event_types))

        params = {
            "token": self.token,
            "lastEventId": self.last_event_id,
            "pollTime": "2"
        }

        resp = requests.get(
            url=self.base_url + "/events/get",
            params=params
        )
        logger.debug(f"Server answer: {resp.text}")

        try:
            events = resp.json()['events']
        except requests.exceptions.JSONDecodeError:
            logger.error(f'Error decoding json "{resp.text}"')
            raise

        if not events:
            return []
        self.last_event_id = events[-1]['eventId']

        if not event_types:
            return events

        return list(filter(lambda e: e["type"] in event_types, events))

    def edit_message(self, msg_id: str, text: str, chat_id: str, inline_kb: str = ''):
        """
        Редактирует сообщение в VK Teams

        :param msg_id: id сообщения
        :param text: текст сообщения
        :param chat_id: адресат
        :param inline_kb: клавиатура (см. bot api)
        """

        logger.info(f"Editing message {msg_id} on {chat_id}")
        params = {
            "token": self.token,
            "msgId": msg_id,
            "chatId": chat_id,
            "parseMode": "HTML",
            "text": text
        }
        if inline_kb:
            params.update(inlineKeyboardMarkup=inline_kb)

        resp = requests.get(
            url=self.base_url + "/messages/editText",
            params=params
        )
        logger.info(f"Server answer: {resp.text}")
