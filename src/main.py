import os
import logging
import time

from dotenv import load_dotenv
from exchangelib import Credentials, Account, DELEGATE, Configuration
from exchangelib.errors import ErrorFolderNotFound

from mail_handler import MonitoringHandler, IncidentHandler
import vkt
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
    bot.send_message(r'Бот itsm2vk\_bot запущен', os.environ['VKT_ADMIN_ID'])
    while True:
        try:
            logger.info('Checking new emails...')
            for message in inc_handler.new_messages():
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
