# parser/t_news_parser.py
import time
from pathlib import Path

import httpx

from json_file.work_json import save_posts_with_check
from logi import logi
from news_config import TICKERS
from pydant.pydantics import ParsTextTnews, UfaDate


BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "json_file" / "predvaritelno_news.json"


class TinkoffOfficialNewsParser:
    """ПАРСИТ НОВОСТИ ИЗ ФИДА"""

    def __init__(self):
        # Рабочий эндпоинт
        self.base_url = "https://www.tbank.ru/mybank/api/social-api-gateway/social/post/feed/v1/feed/instrument"
        # Параметры строки запроса
        self.query_params = {
            "sessionId": "",  # можно оставить пустым или генерировать
            "limit": 30,
            "appName": "invest",
            "appVersion": "1.600.0",
            "origin": "web",
            "platform": "web",
        }
        # Заголовки
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
            "Origin": "https://www.tbank.ru",
            "Referer": "https://www.tbank.ru/invest/stocks/SBER/news/",
            "x-app-name": "invest",
            "x-app-version": "1.600.0",
            "x-platform": "web",
        }
        self.session = httpx.Client(headers=self.headers, timeout=30)

    def get_feed(self, ticker: str, limit: int = 10, cursor=None):  # limit-кол-во новостей
        """POST-ЗАПРОС"""
        json_payload = {"ticker": ticker}
        params = self.query_params.copy()
        params["limit"] = limit
        if cursor:
            params["nextCursor"] = cursor  # или "cursor" — проверь по ответу
        try:
            response = self.session.post(self.base_url, params=params, json=json_payload)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "Ok" and "payload" in data:
                return data["payload"]
            return {}
        except Exception as e:
            logi.err.info(f"get_feed() в parser/t_news_parser.py Ошибка: {type(e).__name__}, Exception as e : {e}")
            return {}

    def parse_all_posts(self, ticker: str, max_pages: int = 5):
        """СБОР НОВОСТЕЙ С ПАГИНАЦИЕЙ"""
        all_news = []
        cursor = None
        page = 0
        while page < max_pages:
            try:
                payload = self.get_feed(ticker, limit=5, cursor=cursor)  # по limit шт новостей
                items = payload.get("items", [])
                if not items:
                    break
                all_news.extend(items)
                # Пагинация
                cursor = payload.get("nextCursor") or payload.get("cursor")
                if not cursor:
                    break
                page += 1
                time.sleep(1)  # Вежливая задержка
            except Exception as e:
                logi.err.info(f"parse_all_posts() в parser/t_news_parser.py ошибка сбора новости: Exception as e : {e}")
        logi.inf.info(f"✅ {ticker}: найдено {len(all_news)} новостей")
        return all_news

    def close(self):
        self.session.close()


def message_to_dict(msg: dict) -> dict:
    """КОНВЕРТИРУЕТ ЗАПИСЬ В НУЖНЫЙ МНЕ СЛОВАРЬ"""
    try:
        # 1. Обработка даты
        raw_date = msg.get("inserted", "")
        date = UfaDate(raw_date=raw_date).date
        # 2. Обработка текста
        content = msg.get("content", {})
        title = content.get("title", "")
        announce = content.get("announce", "")
        text_after = f"{title} {announce}".strip() if announce else title
        text = ParsTextTnews(text_after=text_after).text  # ← Готовая строка!
        # Тикеры из instruments
        tickers = []
        for inst in content.get("instruments", []):
            if isinstance(inst, dict) and inst.get("ticker"):
                tickers.append(inst["ticker"])
        # Возвращаем готовый словарь
        return {"date": date, "text": text, "ticker": tickers, "hashtags": []}
    except Exception as e:
        logi.err.info(f"message_to_dict() в parser/t_news_parser.py ошибка конвертации в словарь: Exception as e : {e}")


def main_t_news_parser():
    """ТОЧКА ВХОДА"""
    logi.inf.info("=====НАЧАЛО ПАРСИНГА НОВОСТИ Т-ИНВЕСТИЦИИ ======")
    api = TinkoffOfficialNewsParser()
    try:
        for tik in TICKERS:
            time.sleep(1)  # Пауза между тикерами
            clean_posts = []
            for msg in api.parse_all_posts(ticker=tik, max_pages=1):
                clean_posts.append(message_to_dict(msg=msg))  # добавляем в уже обработанные посты
            save_posts_with_check(
                clean_posts, filename=str(OUTPUT_FILE), signature_length=10
            )  # сверяем по первые 10 символов и добавляем в JSON
    except Exception as e:
        logi.err.info(f"main_t_news_parser() в parser/t_news_parser.py ошибка точки входа: Exception as e : {e}")
    finally:
        api.close()


if __name__ == "__main__":
    main_t_news_parser()
