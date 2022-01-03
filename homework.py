import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ForeignServerError

load_dotenv()
logging.basicConfig()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# RETRY_TIME = 600
RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Sends a message to user with TELEGRAM_CHAT_ID."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp: int) -> dict:
    """Makes a request to ya.practicum,  takes unix time."""
    timestamp = current_timestamp  # or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise ForeignServerError('Что-то пошло не так на внешнем сервере')
    return json.loads(response.text)


def check_response(response_text: dict) -> list:
    """Checks response status code, reterns list of homeworks."""
    homeworks = response_text.get('homeworks')
    return homeworks


def parse_status(homework: dict) -> str:
    """Returns name and rewiever's verdict of a sertain homework."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        return 'Домашняя работа не найдена.'
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checks the availability of environment variables."""
    variables = (
        'PRACTICUM_TOKEN',
        'TELEGRAM_TOKEN',
        'TELEGRAM_CHAT_ID',
    )
    for v in variables:
        if v in globals():
            continue
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        quit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # current_timestamp = 0  # для дебага, все работы с основания веков
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) < 1:
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
                continue

            last_homework = homeworks[0]
            message = parse_status(last_homework)

            send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
            continue
        else:
            continue
    quit()


if __name__ == '__main__':
    main()
