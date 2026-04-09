# ГЛАВНЫЙ ФАЙЛ
import os
import time
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from pyrogram import Client as TelegramClient
from pyrogram.enums import ParseMode

from json_file.classify_by_ticker import main_classify_by_ticker
from json_file.work_json import INPUT_FILE, OUTPUT_FILE, filter_read_json, sort_news_by_ticker, sort_posts_by_date
from logi import logis
from parser.news_collector_RBK import main_news_collector_rbk
from parser.t_news_parser import main_t_news_parser


CHANNEL_USERNAME = "rbc_news"  # или "rbc_news" без @
LIMIT = 50  # Сколько последних сообщений забрать
JSON_FILE = "telega_new.json"  # Имя файла для сохранения

# from parser.t_pulse_parser import sort_posts_by_date
"""ДЛЯ ЧТЕНИЯ ТОКЕНА"""
load_dotenv(".env.news")
token = os.getenv("TOKSELL")
accid = os.getenv("AOCID")
telegtok = os.getenv("TELEGTOKENG")
newgroupt = os.getenv("NEWSGROUPT")
api_iddd = os.getenv("API_IDDD")
# 📦 Прокси настройки
proxy_url = os.getenv("PROXY_URL")


# ✅ Функция для преобразования строки прокси в формат Pyrogram
def get_proxy_dict(proxy_url: str | None):
    """Конвертирует proxy-строку в dict для Pyrogram"""
    if not proxy_url:
        return None
    p = urlparse(proxy_url)
    return {
        "scheme": p.scheme.lower(),
        "hostname": p.hostname,
        "port": p.port,
        "username": unquote(p.username) if p.username else None,
        "password": unquote(p.password) if p.password else None,
    }


if __name__ == "__main__":
    # =====НАЧАЛО ТЕЛЕГРАММ ДАННЫЕ========
    telegram_cl = TelegramClient(
        name="SEM",
        api_id=int(api_iddd) if api_iddd else None,  # 🔧 int!
        api_hash=telegtok,
        parse_mode=ParseMode.HTML,
        proxy=get_proxy_dict(proxy_url),
    )
    # =====КОНЕЦ ТЕЛЕГРАММ ДАННЫЕ=========
    logis.inf.info("'''***=====НАЧАЛО ПАРСИНГА=====***'''")
    # # main_t_pulse_parser()  # парсим переделываем и сохраняем в json - пульс
    # # ------------------------------------
    main_t_news_parser()  # парсим переделываем и сохраняем в json - Т НОВОСТИ
    main_news_collector_rbk()  # парсим переделываем и сохраняем в json - РБК RSS
    # # ------------------------------------
    sort_posts_by_date(input_file=INPUT_FILE, output_file=INPUT_FILE)  # сортируем пост по дате
    main_classify_by_ticker()  # сортировка новости по тикеру
    sort_news_by_ticker(input_file=OUTPUT_FILE, output_file=OUTPUT_FILE)  # сорт по тикерам новости удаляет старше 14 дн
    logis.inf.info("'''***=====КОНЕЦ ПАРСИНГА=====***'''")
    # =========НАЧАЛО отправка сообщения=========
    # 🔌 Подключаемся ОДИН раз перед циклом
    telegram_cl.start()
    # Получаем словарь {ticker: message}
    messages = filter_read_json()
    # Отправляем по одному сообщению на каждый тикер
    telegram_cl.send_message(newgroupt, "✅✅✅✅✅")
    for ticker, message in messages.items():
        try:
            telegram_cl.send_message(newgroupt, ticker)
            # Проверяем, что список не пустой
            if not message:
                # logis.err.info(f"⚠️ Для {ticker} нет новостей, пропускаем")
                continue
            for mess in message:  # у телеграмм проверка если длинна не больше 4000
                telegram_cl.send_message(newgroupt, mess)
                time.sleep(1)
            time.sleep(5)
        except Exception as e:
            logis.err.info(f"play.py ошибка отправки в телегу e : {e}")
    telegram_cl.stop()
    # =========КОНЕЦ отправка сообщения=========
