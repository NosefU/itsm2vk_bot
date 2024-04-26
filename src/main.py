import os
import logging
import time
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from exchangelib import Credentials, Account, DELEGATE, Configuration
from exchangelib.errors import ErrorFolderNotFound

import mail_handler

if TYPE_CHECKING:
    import exchangelib

from dto import Incident
from mail_handler import MonitoringHandler, IncidentHandler
import vkt
import vkt_logger
from safe_scheduler import SafeScheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s"
)

vkt_logger.setup(
    logging.getLogger(),
    api_url=os.environ['VKT_BASE_URL'],
    token=os.environ['VKT_BOT_TOKEN'],
    chats=[os.environ['VKT_ADMIN_ID'], ]
)
logger = logging.getLogger('bot')


def walk_mail(
        mail_dir: 'exchangelib.folders.known_folders.Messages', path: str = ''
) -> 'exchangelib.folders.known_folders.Messages':
    """
    Проходит по переданному пути и возвращает соответствующую Exchange-папку.
    Например, если mail_dir=acct.inbox (Входящие), а path='Уведомления/Мониторинг',
    то вернётся exchange-папка, соответствующая пути Входящие/Уведомления/Мониторинг

    :param mail_dir: exchange-папка, от которой идёт отсчёт
    :param path: относительный путь, например 'Уведомления/Мониторинг'
    :return: exchange-папка, соответствующая пути относительно mail_dir
    """
    result_folder = mail_dir
    if not path or path == '.':
        return mail_dir

    for folder in path.split('/'):
        result_folder = result_folder / folder
    return result_folder


def handle_notifications(
        bot: vkt.Bot, inc_handler: mail_handler.IncidentHandler, mon_handler: mail_handler.MonitoringHandler
        ):
    """
    Собирает DTO уведомлений из обработчиков писем,
    рассылает соответствующие сообщения в VK Teams

    :param bot: объект VK Teams бота
    :param inc_handler: обработчик писем инцидентов
    :param mon_handler: обработчик писем мониторинга
    """
    try:
        logger.info('Checking new emails...')
        # проходимся по письмам-инцидентам
        for message in inc_handler.new_messages():
            message.editor = bot.nickname
            vkt_message = message.prep_vkt_message()
            bot.send_message(
                text=vkt_message['text'],
                chat_id=os.environ['VKT_CHAT_ID'],
                inline_kb=vkt_message.get('inlineKB', '')
            )

        # проходимся по письмам мониторинга
        for message in mon_handler.new_messages():
            vkt_message = message.prep_vkt_message()
            bot.send_message(
                text=vkt_message['text'],
                chat_id=os.environ['VKT_MONITORING_CHAT_ID'],
                inline_kb=vkt_message.get('inlineKB', '')
            )

        logger.info('Waiting for next email check...')
    except ErrorFolderNotFound as e:
        print(f'Ошибка: {e}')
        logger.exception(e)
        return
    except KeyboardInterrupt:
        print('Прервано пользователем')
        logger.info('Прервано пользователем')
        return
    except Exception as e:
        print(f'Ошибка: {e}')
        logger.exception(e)


def handle_callbacks(bot: vkt.Bot):
    """
    Обрабатывает коллбэки - нажатия на кнопки "пометить закрытым" и "пометить открытым"

    :param bot: объект VK Teams бота
    """
    # вычитываем события нажатий на callback-кнопки (см. bot api)
    events = bot.get_events(['callbackQuery', ])
    for event in events:
        # получаем текст сообщения, на котором нажата кнопка
        message = event['payload']['message']

        # ищем в прикреплённой к сообщению клавиатуре кнопку "Инцидент в ITSM".
        # Если такая есть, то дёргаем ссылку на инцидент из этой кнопки
        link = ''
        for part in message['parts']:
            if part['type'] != 'inlineKeyboardMarkup':
                continue
            buttons = [btn for row in part['payload'] for btn in row]
            for button in buttons:
                if 'Инцидент в ITSM' not in button['text']:
                    continue
                link = button["url"]
                break
            if link:
                break

        # получаем DTO инцидента из текста сообщения и ссылки на инцидент,
        # отмечаем как редактора пользователя, нажавшего кнопку,
        # изменяем статус инцидента на соответствующий нажатой кнопке
        inc = Incident.from_vkt_message(message['text'], link)
        inc.editor = event['payload']['from']['userId']
        if event['payload']['callbackData'] == 'close':
            inc.status = 'CLOSED'
        if event['payload']['callbackData'] == 'open':
            inc.status = 'OPEN'

        # подменяем сообщение, на котором нажата кнопка, но вновь сформированное
        message_id = message['msgId']
        vkt_message = inc.prep_vkt_message()
        bot.edit_message(
            msg_id=message_id,
            text=vkt_message['text'],
            chat_id=os.environ['VKT_CHAT_ID'],
            inline_kb=vkt_message.get('inlineKB', '')
        )


if __name__ == '__main__':

    # подключаемся к exchange
    creds = Credentials(username=os.environ['EXC_USER'], password=os.environ['EXC_PASSWORD'])
    config = Configuration(
        server=os.environ['EXC_SERVER'],
        # retry_policy=FaultTolerance(max_wait=3600),
        credentials=creds
    )
    acct = Account(
        primary_smtp_address=os.environ['EXC_EMAIL'],
        config=config,
        autodiscover=True,
        access_type=DELEGATE
    )

    # получаем exchange-папки для писем инцидентов и мониторинга,
    # затем создаём соответствующие обработчики этих папок
    incident_folder = walk_mail(acct.inbox, os.environ.get('EXC_INC_FOLDER', ''))
    monitoring_folder = walk_mail(acct.inbox, os.environ.get('EXC_MON_FOLDER', ''))
    inc_handler = IncidentHandler(incident_folder)
    mon_handler = MonitoringHandler(monitoring_folder)

    # инициализируем бота VK Teams и очищаем накопившиеся на сервере события
    bot = vkt.Bot(
        token=os.environ['VKT_BOT_TOKEN'],
        base_url=os.environ.get('VKT_BASE_URL', '')
    )
    bot.get_events()

    # создаём планировщик, который будет запускать обработчики по таймеру
    scheduler = SafeScheduler(reschedule_on_failure=True, seconds_after_failure=5)

    # запланируем раз в минуту проверять новые письма
    # и раз в 2 секунды проверять новые события нажатия кнопок
    scheduler.every(60).seconds.do(
        handle_notifications, bot=bot, inc_handler=inc_handler, mon_handler=mon_handler
    )
    scheduler.every(2).seconds.do(handle_callbacks, bot=bot)

    bot.send_message(r'Бот itsm2vk\_bot запущен', os.environ['VKT_ADMIN_ID'])

    # запускаем работу бота
    while True:
        scheduler.run_pending()
        time.sleep(1)
