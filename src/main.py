import os
import logging
import time

from dotenv import load_dotenv
from exchangelib import Credentials, Account, DELEGATE, Configuration
from exchangelib.errors import ErrorFolderNotFound

from dto import Incident
from mail_handler import MonitoringHandler, IncidentHandler
import vkt
import vkt_logger
from safe_scheduler import SafeScheduler

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


def handle_notifications(bot, inc_handler, mon_handler):
    try:
        logger.info('Checking new emails...')
        for message in inc_handler.new_messages():
            message.editor = bot.nickname
            vkt_message = message.prep_vkt_message()
            bot.send_message(
                text=vkt_message['text'],
                chat_id=os.environ['VKT_CHAT_ID'],
                inline_kb=vkt_message.get('inlineKB', '')
            )

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


def handle_callbacks(bot):
    events = bot.get_events(['callbackQuery', ])
    for event in events:
        message = event['payload']['message']
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

        inc = Incident.from_vkt_message(message['text'], link)
        inc.editor = event['payload']['from']['userId']
        if event['payload']['callbackData'] == 'close':
            inc.status = 'CLOSED'
        if event['payload']['callbackData'] == 'open':
            inc.status = 'OPEN'

        message_id = message['msgId']
        vkt_message = inc.prep_vkt_message()
        bot.edit_message(
            msg_id=message_id,
            text=vkt_message['text'],
            chat_id=os.environ['VKT_CHAT_ID'],
            inline_kb=vkt_message.get('inlineKB', '')
        )


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

    inc_handler = IncidentHandler(acct.inbox / 'prd.support')
    mon_handler = MonitoringHandler(acct.inbox / 'Мониторинг')

    bot = vkt.Bot(
        token=os.environ['VKT_BOT_TOKEN'],
        base_url=os.environ.get('VKT_BASE_URL', '')
    )
    bot.get_events()

    scheduler = SafeScheduler(reschedule_on_failure=True, seconds_after_failure=5)
    scheduler.every(60).seconds.do(
        handle_notifications, bot=bot, inc_handler=inc_handler, mon_handler=mon_handler
    )
    scheduler.every(2).seconds.do(handle_callbacks, bot=bot)

    bot.send_message(r'Бот itsm2vk\_bot запущен', os.environ['VKT_ADMIN_ID'])

    while True:
        scheduler.run_pending()
        time.sleep(1)

