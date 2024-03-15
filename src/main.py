import os
from dataclasses import asdict
import logging
import time

import exchangelib.folders.known_folders
from dotenv import load_dotenv
from exchangelib import Credentials, Account, DELEGATE, Configuration
from exchangelib.errors import ErrorFolderNotFound
import requests

from incident import Incident
from monitoring import Monitoring
import templates
import vkt_logger


load_dotenv()


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s")

vkt_logger.setup(
    logging.getLogger(),
    api_url=os.environ['VKT_BASE_URL'],
    token=os.environ['VKT_BOT_TOKEN'],
    chats=[os.environ['VKT_ADMIN_ID'], ]
)
logger = logging.getLogger('bot')


def prep_inc_message(inc: Incident) -> str:
    fields = asdict(inc)

    # экранируем "_", вычищаем пустые строки и превращаем всё в цитату
    fields['subject'] = fields['subject'].replace('_', r'\_')
    fields['subject'] = fields['subject'].replace('\r', '')
    fields['subject'] = '\n'.join(['>' + s for s in fields['subject'].split('\n') if s])

    # экранируем "_", вычищаем пустые строки
    fields['description'] = fields['description'].replace('_', r'\_')
    fields['description'] = fields['description'].replace('\r', '')
    fields['description'] = '\n'.join([s for s in fields['description'].split('\n') if s])

    # если описание - пересылка другого инцидента, то парсим его,
    # формируем часть сообщения, превращаем в цитату и склеиваем с основным сообщением
    if fields['description'].startswith('Для группы 2-ая линия ВК мессенджер (VK Teams)'):
        descr_inc = Incident.from_description(fields['description'])
        descr_fields = asdict(descr_inc)
        fields['description'] = templates.md_description.substitute(descr_fields)
    fields['description'] = '\n'.join(['>' + s for s in fields['description'].split('\n')])

    return templates.md_notification.substitute(fields)


def prep_mon_message(mon: Monitoring) -> str:
    fields = asdict(mon)

    # экранируем "_", вычищаем пустые строки
    fields['description'] = fields['description'].replace('_', r'\_')
    fields['description'] = fields['description'].replace('\r', '')
    fields['description'] = '\n'.join([s for s in fields['description'].split('\n') if s])

    return templates.md_mon_notification.substitute(fields)


def send_message_to_vkt(msg: str, chat_id: str):
    requests.get(
        url=os.environ['VKT_BASE_URL'] + "messages/sendText",
        params={
            "token": os.environ['VKT_BOT_TOKEN'],
            "chatId": chat_id,
            "parseMode": "MarkdownV2",
            "text": msg
        }
    )


def process_new_inc_emails(mail_dir: exchangelib.folders.known_folders.Messages):
    unread_emails = list(mail_dir.filter(is_read=False))
    if not unread_emails:
        logger.info('No new incident emails')
        return

    for item in unread_emails[::-1]:
        logger.info("Processing incident message from " + item.sender.email_address + ": " + item.subject)
        if item.sender.email_address != 'prd.support@lukoil.com' \
                or '] назначено на вашу группу [' not in item.subject:
            logger.info('\t\tis not incident notification')
            item.is_read = True  # Помечаем письмо как прочитанное
            continue

        inc = Incident.from_notification(item.text_body)

        if not inc:
            logger.error('Incorrect incident message format')
            item.is_read = True  # Помечаем письмо как прочитанное
            item.save()
            continue

        logger.info(inc)
        msg = prep_inc_message(inc)
        send_message_to_vkt(msg, os.environ['VKT_CHAT_ID'])
        item.is_read = True  # Помечаем письмо как прочитанное
        item.save()


def process_new_monitoring_emails(mail_dir: exchangelib.folders.known_folders.Messages):
    unread_emails = list(mail_dir.filter(is_read=False))
    if not unread_emails:
        logger.info('No new monitoring emails')
        return

    for item in unread_emails[::-1]:
        logger.info("Processing monitoring message from " + item.sender.email_address + ": " + item.subject)
        if item.sender.email_address != 'no-reply.monitoring@lukoil.com' \
                or '.srv.lukoil.com' not in item.subject:
            logger.info('\t\tis not monitoring notification')
            item.is_read = True  # Помечаем письмо как прочитанное
            continue

        mon = Monitoring.from_notification(item.text_body)

        if not mon:
            logger.error('Incorrect monitoring message format')
            item.is_read = True  # Помечаем письмо как прочитанное
            item.save()
            continue

        logger.info(mon)
        msg = prep_mon_message(mon)
        send_message_to_vkt(msg, os.environ['VKT_MONITORING_CHAT_ID'])
        item.is_read = True  # Помечаем письмо как прочитанное
        item.save()


if __name__ == '__main__':
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

    inc_dir = acct.inbox / 'prd.support'
    monitoring_dir = acct.inbox / 'Мониторинг'

    send_message_to_vkt(r'Бот itsm2vk\_bot запущен', os.environ['VKT_ADMIN_ID'])
    while True:
        try:
            logger.info('Checking new emails...')
            process_new_inc_emails(inc_dir)
            process_new_monitoring_emails(monitoring_dir)
            logger.info('Waiting 60 sec for next email check...')
            time.sleep(60)  # Пауза в 60 секунд между проверками
        except ErrorFolderNotFound as e:
            print(f'Ошибка: {e}')
            logger.exception(e)
            break
        except KeyboardInterrupt:
            print('Прервано пользователем')
            logger.info('Прервано пользователем')
            break
        except Exception as e:
            print(f'Ошибка: {e}')
            logger.exception(e)

