from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union


@dataclass
class Notification(ABC):
    """
    Интерфейс для DTO уведомлений (инцидента и мониторинга).
    Напрямую не используется, используются дочерние классы - конкретные реализации
    """

    @classmethod
    @abstractmethod
    def from_notification(cls, notification_text: str) -> Union['Notification', None]:
        """
        Разбирает текст письма и возвращает готовый объект DTO.

        :param notification_text: текст письма
        :return: Notification DTO
        """
        pass

    @abstractmethod
    def prep_vkt_message(self):
        """
        Формирует сообщение для VK Teams

        :return: словарь вида {'text': 'текст сообщения',
                               'inlineKB': 'json клавиатуры сообщения (см. bot api)'}
        """
        pass
