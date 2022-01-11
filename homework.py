import logging
import os
import time
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ForeignServerError, HomeworkIsNotDict,
                        HomeworksIsNotList)

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
        logger.info('Удачная отправка сообщения в Telegram.')
    except Exception as e:
        logger.error(f'Cбой при отправке сообщения в Telegram: {e}')


def get_api_answer(current_timestamp: int) -> dict:
    """Makes a request to ya.practicum, takes unix time."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        logger.info('Обратился к Яндекс.Практикум')
    except requests.exceptions.RequestException as e:
        raise ForeignServerError(e)

    if response.status_code != requests.codes.ok:
        message = f'Недоступен {ENDPOINT}, код: {response.status_code}'
        raise requests.HTTPError(message)

    try:
        response = response.json()
    except KeyError as e:
        raise KeyError(e)

    # Я не уверен, что правильно понял комментарий:
    # "Ищи в response.json() ключи error или code."
    # в документации requests не смог найти подробностей
    # в режиме дебага тоже не получилось имитировать эти ключи (

    if type(response) is dict:
        is_error = response.get('error')
        is_code = response.get('code')
    else:
        is_error = response[0].get('error')
        is_code = response[0].get('code')

    if is_error or is_code:
        message = f'Ошибка внешнего сервера: {is_error}, {is_code}'
        raise ForeignServerError(message)
    return response


def check_response(response_text: dict) -> list:
    """Returns list of homeworks."""
    if type(response_text) is dict:
        homeworks = response_text.get('homeworks')

    if type(response_text) is list:
        homeworks = response_text[0].get('homeworks')

    if homeworks is None:
        raise KeyError('Отсутствие ожидаемого ключа homeworks в ответе API')
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
        raise KeyError('В ответе API отсутствует ожидаемый ключ homework_name')

    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('В ответе API отсутствует ожидаемый ключ status')

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyError('Недокументированный статус домашней работы, '
                       'обнаруженный в ответе API.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checks the availability of environment variables."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    errors = [key for key, value in tokens.items() if not value]
    if len(errors) == 0:
        return True
    logger.critical(f'Токен недоступен ({", ".join(errors)}), бот выключается')
    return False


def main():
    """Основная логика работы бота."""
    logger.info('Запуск приложения')
    if not check_tokens():
        logger.critical('Токен недоступен, бот покидает нас...')
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
            logger.info('Ухожу на следующий виток цикла программы')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
