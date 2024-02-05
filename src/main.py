import os
from dataclasses import asdict
import logging
import time

from dotenv import load_dotenv
from exchangelib import Credentials, Account, DELEGATE, Configuration, FaultTolerance
from exchangelib.errors import ErrorFolderNotFound
import requests

from incident import Incident
import templates


load_dotenv()
logging.basicConfig(level=logging.INFO)
print(os.environ.get('EXC_USER', 'No EXC_USER environ'))


def prep_message(inc: Incident) -> str:
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


def process_new_emails():
    unread_emails = list(inbox.filter(is_read=False))
    if not unread_emails:
        logging.info('No new emails')
        return

    for item in unread_emails[::-1]:
        logging.info(item.sender.email_address + ": " + item.subject)
        if item.sender.email_address != 'prd.support@lukoil.com' \
                or '] назначено на вашу группу [' not in item.subject:
            item.is_read = True  # Помечаем письмо как прочитанное
            continue

        inc = Incident.from_notification(item.text_body)
        logging.info(inc)
        msg = prep_message(inc)
        send_message_to_vkt(msg, os.environ['VKT_CHAT_ID'])
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

    inbox = acct.inbox / 'prd.support'

    while True:
        try:
            logging.info('Checking new emails...')
            process_new_emails()
            logging.info('Waiting 60 sec for next email check...')
            time.sleep(60)  # Пауза в 60 секунд между проверками
        except ErrorFolderNotFound as e:
            print(f'Ошибка: {e}')
            send_message_to_vkt(f'Ошибка: {e}', os.environ['VKT_ADMIN_ID'])
            break
        except KeyboardInterrupt:
            print('Прервано пользователем')
            break
        except Exception as e:
            print(f'Ошибка: {e}')
            send_message_to_vkt(f'Ошибка: {e}', os.environ['VKT_ADMIN_ID'])

