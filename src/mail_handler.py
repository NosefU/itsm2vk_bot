import logging
from abc import abstractmethod, ABC
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    import exchangelib

from dto import Notification, Monitoring, Incident


logger = logging.getLogger(__name__)


class MailHandler(ABC):
    """
    Абстрактный обработчик писем.
    Напрямую не используется, используются дочерние классы - конкретные реализации
    """

    type: str
    Dto: Notification

    def __init__(self, mail_dir: 'exchangelib.folders.known_folders.Messages'):
        """
        Принимает exchange папку с письмами, с которой в дальнейшем и будет работать.

        :param mail_dir: exchange папка с письмами
        """
        self.mail_dir = mail_dir

    @abstractmethod
    def is_notification(self, item: 'exchangelib.items.message.Message') -> bool:
        """
        Метод, который проверяет, соответствует ли переданное письмо фильтру.
        То есть является ли тем, что мы ищем

        :param item: exchange-письмо
        :return: True - письмо соответствует фильтру, False - не соответствует
        """
        pass

    def new_messages(self) -> Generator[Notification, None, None]:
        """
        Генератор, который обрабатывает письма из папки, переданной в __init__.
        Если письмо соответствует фильтру из метода is_notification(),
        то формирует соответствующий DTO, отмечает письмо прочитанным и возвращает этот DTO

        :return: Notification DTO
        """

        # вычитываем из папки непрочитанные письма
        unread_emails = list(self.mail_dir.filter(is_read=False))
        if not unread_emails:
            logger.info(f'No new {self.type} emails')
            return

        # проходимся по каждому письму
        for item in unread_emails[::-1]:
            logger.info(f"Processing {self.type} message from " + item.sender.email_address + ": " + item.subject)

            # если письмо не соответствует фильтру, то пропускаем его
            if not self.is_notification(item):
                logger.info(f'\t\tis not {self.type} notification')
                # item.is_read = True  # Помечаем письмо как прочитанное
                continue

            # из текста письма формируем DTO
            dto_obj = self.Dto.from_notification(item.text_body)

            # если не получилось - ругаемся пропускаем
            if not dto_obj:
                logger.error(f'Incorrect {self.type} message format')
                item.is_read = True  # Помечаем письмо как прочитанное
                item.save()
                continue

            logger.info(dto_obj)
            item.is_read = True  # Помечаем письмо как прочитанное
            item.save()
            yield dto_obj


class MonitoringHandler(MailHandler):
    """
    Обработчик для писем мониторинга
    """

    type = 'monitoring'  # тип письма, чисто для логов
    Dto = Monitoring  # класс DTO, в который будет преобразовываться письмо

    def is_notification(self, item) -> bool:
        return item.sender.email_address == 'no-reply.monitoring@lukoil.com' \
               and '.srv.lukoil.com' in item.subject


class IncidentHandler(MailHandler):
    type = 'incident'
    Dto = Incident

    def is_notification(self, item):
        return item.sender.email_address == 'prd.support@lukoil.com' \
               and '] назначено на вашу группу [' in item.subject
