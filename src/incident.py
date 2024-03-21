import logging
import re
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class Incident:
    idx: str = ""
    priority: str = ""
    sla: str = ""
    creation_date: str = ""
    family_name: str = ""
    name: str = ""
    parent_name: str = ""
    org_unit: str = ""
    subject: str = ""
    description: str = ""
    link: str = ""
    device: str = ""

    @classmethod
    def from_notification(cls, notification_text: str):
        # TODO Разбить регэксп на мелкие, отдельно для каждого поля.
        #  Возможно, реализовать что-то типа мапы поле: регэксп
        notf_pattern = re.compile(
            r"Исполнение \[(?P<inc_id>INC\d+)\], \[(?P<priority>\S+)\].+"
            r"Дата регистрации:\s+\[(?P<date>[\d\sPAM:\.\/]+)\].+"
            r"Статус SLA:\s+\[(?P<sla>.*)\].+"
            r"Пользователь:\s+\[(?:(?P<family_name>\S+) (?P<name>\S+) (?P<parent_name>\S*)|(?P<job_title>.+))\].+"
            r"Организация:\s+\[(?P<org_unit>.+)\].+"
            r"Описание:\s+\[(?P<subject>.*)\].+"
            r"Подробное описание:.+\[(?P<description>.*)\].+"
            r"Ссылка: Заявка *<(?P<link>\S+)>",
            re.DOTALL
        )
        match = re.search(notf_pattern, notification_text)
        if not match:
            # print(f'I dont recognize that mail: {notification_text}')
            logger.error(f'I dont recognize that mail: {notification_text}')
            return None

        return cls(
            idx=match.group('inc_id'),
            priority=match.group('priority'),
            sla=match.group('sla'),
            creation_date=match.group('date'),
            family_name=match.group('family_name') or match.group('job_title'),
            name=match.group('name') or "",
            parent_name=match.group('parent_name') or "",
            org_unit=match.group('org_unit'),
            subject=match.group('subject'),
            description=match.group('description'),
            link=match.group('link')
        )

    @classmethod
    def from_description(cls, descr_text: str):
        descr_pattern = re.compile(
            r"Заказчик: +(?P<org_unit>.+) +"
            r"(?P<family_name>\S+) +(?P<name>\S+) +(?P<parent_name>\S+) *\n*"
            r"Дата обращения: (?P<date>[\d\s]+),.+"
            r"тип клиента и ОС: (?P<device>.+),.+"
            r"Описание проблемы:\s*(?P<description>[\s|\S|\n]+)"
            r"(?:С уважением,[\s|\n]+Никулина Валентина Александровна[\s|\S|\n]+)"
        )
        match = re.search(descr_pattern, descr_text)
        if not match:
            # print(f'I dont recognize that message: {descr_text}')
            logger.error(f'I dont recognize that message: {descr_text}')
            return None

        return cls(
            creation_date=match.group('date'),
            family_name=match.group('family_name'),
            name=match.group('name'),
            parent_name=match.group('parent_name'),
            org_unit=match.group('org_unit'),
            description=match.group('description'),
            device=match.group('device'),
        )
