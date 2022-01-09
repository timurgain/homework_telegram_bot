import logging
import os
import time
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (HomeworkIsNotDict, HomeworkNameKeyNotFound,
                        HomeworksIsNotList, HomeworksKeyNotFound,
                        HomeworkStatusKeyNotFound, ResponseTextIsNotDict,
                        VerdictNotFound)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
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
    logger.debug('Обратился к Яндекс.Практикум')
    if response.status_code != requests.codes.ok:
        message = 'Недоступность эндпоинта: practicum.yandex.ru'
        raise requests.HTTPError(message)
    try:
        response = response.json()
    except ValueError as e:
        message = f'Ошибка преобразования response в формат json: {e}'
        raise ValueError(message)
    return response


def check_response(response_text: dict) -> list:
    """Returns list of homeworks."""
    if type(response_text) != dict:
        message = 'response_text ждем в формате dict, пришел другой формат'
        raise ResponseTextIsNotDict(message)

    homeworks = response_text.get('homeworks')
    if homeworks is None:
        message = 'Отсутствие ожидаемого ключа homeworks в ответе API'
        raise HomeworksKeyNotFound(message)
    if type(homeworks) != list:
        message = 'homeworks ждем в формате list, пришел другой формат'
        raise HomeworksIsNotList(message)

    return homeworks


def parse_status(homework: dict) -> str:
    """Returns name and rewiever's verdict of a sertain homework."""
    if type(homework) != dict:
        message = 'homework ждем в формате dict, пришел другой формат'
        raise HomeworkIsNotDict(message)

    homework_name = homework.get('homework_name')
    if homework_name is None:
        message = 'Отсутствие ожидаемого ключа homework_name в ответе API'
        raise HomeworkNameKeyNotFound(message)

    homework_status = homework.get('status')
    if homework_status is None:
        message = 'Отсутствие ожидаемого ключа status в ответе API'
        raise HomeworkStatusKeyNotFound(message)

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        message = ('Недокументированный статус домашней работы, '
                   'обнаруженный в ответе API.')
        raise VerdictNotFound(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checks the availability of environment variables."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logger.critical('Отсутствуют обязательные переменные окружения.')
    return False


def main():
    """Основная логика работы бота."""
    logger.info('Запуск приложения')
    if not check_tokens():
        quit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # current_timestamp = 0  # для дебага, все домашки с основания веков
    cache_error_messages = []
    cache_homework_statuses = {}

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                homework_id = homework['id']
                homework_st = homework['status']
                if cache_homework_statuses.get(homework_id) != homework_st:
                    message = parse_status(homework)
                    send_message(bot, message)
                    cache_homework_statuses.update(
                        homework_id=homework_st
                    )
                    logger.info('Есть обновления')
                else:
                    logger.info('Ничего нового')

        except Exception as e:
            message = f'Сбой в работе программы: {e}'
            logger.error(message)
            if message not in cache_error_messages:
                cache_error_messages.append(message)
                send_message(bot, message)

        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
