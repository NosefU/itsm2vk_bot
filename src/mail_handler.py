import logging
from abc import abstractmethod, ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import exchangelib

from dto import Notification, Monitoring, Incident


logger = logging.getLogger(__name__)


class MailHandler(ABC):
    type: str
    Dto: Notification

    def __init__(self, mail_dir: 'exchangelib.folders.known_folders.Messages'):
        self.mail_dir = mail_dir

    @abstractmethod
    def is_notification(self, item) -> bool:
        pass

    def new_messages(self):
        unread_emails = list(self.mail_dir.filter(is_read=False))
        if not unread_emails:
            logger.info(f'No new {self.type} emails')
            return

        for item in unread_emails[::-1]:
            logger.info(f"Processing {self.type} message from " + item.sender.email_address + ": " + item.subject)
            if self.is_notification(item):
                logger.info(f'\t\tis not {self.type} notification')
                item.is_read = True  # Помечаем письмо как прочитанное
                continue

            dto_obj = self.Dto.from_notification(item.text_body)

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
    type = 'monitoring'
    Dto = Monitoring

    def is_notification(self, item):
        return item.sender.email_address != 'no-reply.monitoring@lukoil.com' \
               or '.srv.lukoil.com' not in item.subject


class IncidentHandler(MailHandler):
    type = 'incident'
    Dto = Incident

    def is_notification(self, item):
        return item.sender.email_address != 'prd.support@lukoil.com' \
               or '] назначено на вашу группу [' not in item.subject
