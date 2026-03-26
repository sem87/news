# # parser/t_pulse_parser
# import time
# from pathlib import Path
#
# import httpx
#
# from json_file.work_json import *
# from news_config import TICKERS
# from pydant.pydantics import *  # ParsText
#
#
# # В начале файла:
# BASE_DIR = Path(__file__).parent.parent  # news/
# OUTPUT_FILE = BASE_DIR / "json_file" / "predvaritelno_news.json"
#
#
# class TinkoffPulseDirect:
#     def __init__(self):
#         self.base_url = "https://www.tinkoff.ru/api/invest-gw/social/v1/"
#         self.headers = {
#             "Content-Type": "application/json",
#             "Accept": "application/json",
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
#             "Origin": "https://www.tinkoff.ru",
#             "Referer": "https://www.tinkoff.ru/invest/stocks/SBER/pulse/",
#         }
#         self.params = {"appName": "invest", "origin": "web", "platform": "web"}
#         self.session = httpx.Client(headers=self.headers, params=self.params, timeout=30)
#         self.posts = []
#
#     def get_posts_by_ticker(self, ticker: str, limit: int = 30, cursor=None):
#         """Запрос к API с разными вариантами курсора"""
#         url = f"{self.base_url}post/instrument/{ticker}"
#         # 🔧 Пробуем разные варианты курсора
#         params = {"limit": limit}
#         if cursor is not None:
#             params["cursor"] = cursor
#         try:
#             response = self.session.get(url, params=params)
#             response.raise_for_status()
#             data = response.json()
#             # Проверяем структуру ответа
#             if "payload" in data:
#                 return data["payload"]
#             return data
#         except Exception as e:
#             print(f"❌ Ошибка запроса: {e}")
#             return {}
#
#     def parse_all_posts(self, ticker: str, max_pages: int = 50):
#         """Парсинг постов по тикуру с пагинацией"""
#         self.posts = []
#         cursor = None  # Начинаем с самых новых постов
#         page = 0
#         while page < max_pages:
#             try:
#                 data = self.get_posts_by_ticker(ticker, limit=30, cursor=cursor)
#                 posts = data.get("items", [])
#                 if not posts:
#                     print("⚠️ Посты закончились")
#                     break
#                 self.posts.extend(posts)
#                 cursor = data.get("nextCursor")
#                 if not cursor:
#                     break
#                 page += 1
#                 time.sleep(0.5)  # Вежливая задержка
#             except KeyboardInterrupt:
#                 print("\n⚠️ Прервано пользователем")
#                 break
#             except Exception as e:
#                 print(f"❌ Ошибка: {e}")
#                 break
#         print(f"\n✅ Всего: {len(self.posts)} постов")
#         return self.posts
#
#     def close(self):
#         self.session.close()
#
#
# def message_to_dict(msg: dict) -> dict:
#     """
#     Превращает словарь из API Пульса в нужный мне простой словарь.
#     """
#     # 📅 1. Обработка даты
#     raw_date = msg.get("inserted", "")
#     date = MoscowDate(raw_date=raw_date).date
#     # 📝 2. Обработка текста
#     content = msg.get("content", {})
#     text_after = content.get("text", "")
#     text = ParsTextT(text_after=text_after).text  # ← Готовая строка!
#     # 3. Обработка тикеров
#     tickers = []
#     instruments = content.get("instruments", [])
#     for inst in instruments:
#         ticker = inst.get("ticker")
#         if ticker:
#             tickers.append(ticker)
#     # 4. Обработка хэштэгов
#     hashtags = []
#     hashs = content.get("hashtags", [])  # Список хэштэгов
#     if isinstance(hashs, list):
#         for h in hashs:
#             if isinstance(h, dict):
#                 hashtag = h.get("title")
#                 if hashtag and isinstance(hashtag, str):
#                     hashtags.append(hashtag)
#
#     # 🎁 Возвращаем готовый словарь
#     return {"date": date, "text": text, "ticker": tickers, "hashtags": hashtags}
#
#
# def main_t_pulse_parser():
#     api = TinkoffPulseDirect()
#     try:
#         for tik in TICKERS:
#             time.sleep(10)
#             clean_posts = []
#             for msg in api.parse_all_posts(ticker=tik, max_pages=2):
#                 if message_to_dict(msg)["text"] == "" or message_to_dict(msg)["text"] == " ":
#                     pass
#                 else:
#                     clean_posts.append(message_to_dict(msg))  # добавляем в уже обработанные посты
#             stats = save_posts_with_check(
#                 clean_posts, filename=str(OUTPUT_FILE), signature_length=10
#             )  # сверяем по первые 10 символов и добавляем в JSON
#     finally:
#         api.close()
#
#
# if __name__ == "__main__":
#     main_t_pulse_parser()
