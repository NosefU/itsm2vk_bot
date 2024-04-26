import logging
import re
import string
from dataclasses import dataclass, asdict
from typing import Union

from .notification import Notification

logger = logging.getLogger(__name__)


# шаблон VK Teams сообщения,
# из которого собираются уведомления об инцидентах
inc_notification_template = string.Template(
    "<b>#$idx   #$status</b> <i>by <a href=\"https://u.internal.myteam.mail.ru/profile/$editor\">$editor</a></i>\n\n"
    "⭐ $priority\n"
    "👤 $family_name $name $parent_name\n"
    "🏭 $org_unit\n"
    "📆 $creation_date\n\n"
    # "🔗 [Инцидент в ITSM]($link)\n\n"
    "🪧 <b>Описание</b>\n"
    "<blockquote>$subject</blockquote>\n\n"
    "📖 <b>Подробно</b>\n"
    "<blockquote>$description</blockquote>"
)

# легаси шаблон. В январе-феврале инциденты по ОПЭ
# прилетали как пересылка в описании другого инцидента.
# Таких инцидентов уже не осталось, но пусть будет
inc_description_template = string.Template(
    "👤 $family_name $name $parent_name\n"
    "🏭 $org_unit\n"
    "📆 $creation_date\n"
    "⚙ `$device`\n\n"
    "✏️ $description"
)


@dataclass
class Incident(Notification):
    """
    DTO инцидента.
    Все поля опциональны.
    Реализует интерфейс dto.notification.Notification
    """

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
    status: str = "OPEN"
    editor: str = ""

    @classmethod
    def from_notification(cls, notification_text: str) -> Union['Incident', None]:
        """
        Разбирает текст письма и возвращает готовый объект DTO

        :param notification_text: текст письма об инциденте
        :return: DTO Incident
        """
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
    def from_description(cls, descr_text: str) -> Union['Incident', None]:
        """
        Разбирает текст описания вложенного инцидента и возвращает готовый объект DTO

        :param descr_text: текст описания инцидента
        :return: DTO Incident
        """
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

    @classmethod
    def from_vkt_message(cls, notification_text: str, link: str = '') -> Union['Incident', None]:
        """
        Разбирает текст сообщения в VK Teams из этого бота и возвращает готовый объект DTO.
        Метод нужен для того, чтобы правильно обрабатывать нажатие кнопок
        "отметить открытым" и "отметить закрытым"

        :param notification_text: текст сообщения об инциденте из этого бота
        :param link: ссылка на инцидент в ITSM.
                    В тексте сообщения из бота она явно не указывается - нужно вытаскивать из клавиатуры (см. bot api)
        :return: DTO Incident
        """
        # TODO Разбить регэксп на мелкие, отдельно для каждого поля.
        #  Возможно, реализовать что-то типа мапы поле: регэксп
        vkt_msg_pattern = re.compile(
            r"#(?P<inc_id>INC\d+)   #(?P<status>\S+).+\n\n"
            r"⭐ (?P<priority>\S+)\n"
            r"👤 (?:(?P<family_name>\S+) (?P<name>\S+) (?P<parent_name>\S*)|(?P<job_title>.+))\n"
            r"🏭 (?P<org_unit>.+)\n"
            r"📆 (?P<date>[\d\sPAM:\.\/]+)\n\n"
            r"🪧 Описание\n(?P<subject>.*)\n\n"
            r"📖 Подробно\n(?P<description>.*)",
            re.DOTALL
        )
        match = re.search(vkt_msg_pattern, notification_text)
        if not match:
            # print(f'I dont recognize that mail: {notification_text}')
            logger.error(f'I dont recognize that vkt message: {notification_text}')
            return None

        return cls(
            idx=match.group('inc_id'),
            priority=match.group('priority'),
            creation_date=match.group('date'),
            family_name=match.group('family_name') or match.group('job_title'),
            name=match.group('name') or "",
            parent_name=match.group('parent_name') or "",
            org_unit=match.group('org_unit'),
            subject=match.group('subject'),
            description=match.group('description'),
            status=match.group('status'),
            link=link
        )

    def prep_vkt_message(self) -> dict:
        """
        Формирует сообщение об инциденте для VK Teams из шаблона inc_notification_template (см. выше)

        :return: словарь вида {'text': 'текст сообщения об инциденте',
                               'inlineKB': 'json клавиатуры сообщения (см. bot api)'}
        """
        fields = asdict(self)

        # вычищаем пустые строки в теме инцидента
        # fields['subject'] = fields['subject'].replace('_', r'\_')
        fields['subject'] = fields['subject'].replace('\r', '')
        fields['subject'] = '\n'.join([s for s in fields['subject'].split('\n') if s])

        # вычищаем пустые строки в описании инцидента
        # fields['description'] = fields['description'].replace('_', r'\_')
        fields['description'] = fields['description'].replace('\r', '')
        fields['description'] = '\n'.join([s for s in fields['description'].split('\n') if s])

        # если описание - пересылка другого инцидента, то парсим его,
        # формируем часть сообщения и склеиваем с основным сообщением.
        if fields['description'].startswith('Для группы 2-ая линия ВК мессенджер (VK Teams)'):
            descr_inc = Incident.from_description(fields['description'])
            descr_fields = asdict(descr_inc)
            fields['description'] = inc_description_template.substitute(descr_fields)
        fields['description'] = '\n'.join([s for s in fields['description'].split('\n') if s])

        # в теме и описании инцидента экранируем символы '<', '>' и '&',
        # чтобы не поломалась HTML-разметка сообщения (см. bot api)
        fields['subject'] = fields['subject'].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        fields['description'] = fields['description'].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')

        # в json клавиатуры кладём кнопку со ссылкой на itsm и кнопку дл изменения хэштега (#OPEN/#CLOSED)
        inline_kb = '[[{"text": "🔗 Инцидент в ITSM", "url": "' + fields['link'] + '", "style": "primary"}]'
        if self.status == 'OPEN':
            inline_kb += ',[{"text": "Отметить закрытой", "callbackData": "close", "style": "attention"}]]'
        elif self.status == 'CLOSED':
            inline_kb += ',[{"text": "Отметить открытой", "callbackData": "open", "style": "base"}]]'
        else:
            inline_kb += ']'

        return {
            'text': inc_notification_template.substitute(fields),
            'inlineKB': inline_kb
        }
