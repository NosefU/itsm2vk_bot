import logging
import re
from dataclasses import dataclass


logger = logging.getLogger(__name__)

PRIORITY_EMOJI = {
    'Critical': '🟥',
    'Warning': '🟨',
}


@dataclass
class Monitoring:
    server: str = ""
    priority: str = ""
    priority_emoji: str = ""
    registration_date: str = ""
    notification_date: str = ""
    description: str = ""

    @classmethod
    def from_notification(cls, notification_text: str):
        notf_pattern = re.compile(
            r"событие на объекте:\s+(?P<server>.+)(?:\([\d\.]+\)*).+"
            r"Критичность:\s+(?P<priority>\S+).+"
            r"Сообщение:\s+(?P<description>.*?\S)(?: [\d.]+)?\s+"
            r"Время регистрации:\s+(?P<reg_time>[\d\. :]+[A-Z]*)\s+"
            r"Время нотификации:\s+(?P<notf_time>[\d\. :]+[A-Z]*)",
            re.DOTALL
        )
        match = re.search(notf_pattern, notification_text)
        if not match:
            logger.error(f'I dont recognize that mail: {notification_text}')
            return None

        return cls(
            server=match.group('server'),
            priority=match.group('priority'),
            priority_emoji=PRIORITY_EMOJI.get(match.group('priority'), '‼️'),
            registration_date=match.group('reg_time'),
            notification_date=match.group('notf_time'),
            description=match.group('description').removesuffix('\r'),
        )
