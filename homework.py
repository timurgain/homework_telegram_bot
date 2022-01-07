import logging
import os
import time
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HomeworksKeyNotFound, VerdictNotFound

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
# RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=stdout)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s | %(module)s.%(funcName)s',
    '%d/%m/%Y %H:%M:%S'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Sends a message to user with TELEGRAM_CHAT_ID."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as e:
        logger.error(f'Cбой при отправке сообщения в Telegram: {e}')
    else:
        logger.info('Удачная отправка сообщения в Telegram.')


def get_api_answer(current_timestamp: int) -> dict:
    """Makes a request to ya.practicum, takes unix time."""
    timestamp = current_timestamp  # or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = response.json()
    except ValueError as e:
        logger.error(f'Ошибка преобразования response в формат json: {e}')
        return None
    return response


def check_response(response_text: dict) -> list:
    """Returns list of homeworks."""
    return response_text.get('homeworks')


def parse_status(homework: dict) -> str:
    """Returns name and rewiever's verdict of a sertain homework."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.debug('Обновлений домашних работ пока нет.')
        return None
    homework_status = homework.get('status')
    if homework_status is None:
        logger.debug('Отсутствие в ответе новых статусов.')
        return None
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        return 'verdict_is_none'
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checks the availability of environment variables."""
    variables = (
        'PRACTICUM_TOKEN',
        'TELEGRAM_TOKEN',
        # 'WRONG',
        'TELEGRAM_CHAT_ID',
    )
    for v in variables:
        if v in globals() and v is not None:
            continue
        logger.critical('Отсутствуют обязательные переменные окружения.')
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        quit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # current_timestamp = 0  # для дебага, все домашки с основания веков
    should_notice_api_error = True

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks is None:
                raise HomeworksKeyNotFound

            for homework in homeworks:
                message = parse_status(homework)
                if message == 'verdict_is_none':
                    raise VerdictNotFound
                send_message(bot, message)

        except requests.exceptions.ConnectionError as e:
            message = f'Недоступность эндпоинта: practicum.yandex.ru : {e}'
            logger.error(message)
            if should_notice_api_error:
                send_message(bot, message)
                should_notice_api_error = False

        except ValueError as e:
            logger.error(f'Ошибка преобразования response в формат json: {e}')

        except HomeworksKeyNotFound:
            message = 'Отсутствие ожидаемого ключа "homeworks" в ответе API'
            logger.error(message)
            send_message(bot, message)

        except VerdictNotFound:
            message = ('Недокументированный статус домашней работы, '
                       'обнаруженный в ответе API.')
            logger.error(message)
            send_message(bot, message)

        except Exception as e:
            message = f'Сбой в работе программы: {e}'
            logger.error(message)
            send_message(bot, message)

        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
