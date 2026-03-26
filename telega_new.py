# import json
# import os
# from datetime import datetime, timedelta
# from urllib.parse import unquote, urlparse
#
# from dotenv import load_dotenv
# from pyrogram import Client as TelegramClient
# from pyrogram.enums import ParseMode
#
#
# CHANNEL_USERNAME = "rbc_news"  # или "rbc_news" без @
# LIMIT = 50  # Сколько последних сообщений забрать
# JSON_FILE = "telega_new.json"  # Имя файла для сохранения
#
# """ДЛЯ ЧТЕНИЯ ТОКЕНА"""
# load_dotenv(".env.news")
# token = os.getenv("TOKSELL")
# accid = os.getenv("AOCID")
# telegtok = os.getenv("TELEGTOKENG")
# groupt = os.getenv("GROUPT")
# api_iddd = os.getenv("API_IDDD")
# # 📦 Прокси настройки
# proxy_url = os.getenv("PROXY_URL")
#
#
# # ✅ Функция для преобразования строки прокси в формат Pyrogram
# def get_proxy_dict(proxy_url: str | None):
#     """Конвертирует proxy-строку в dict для Pyrogram"""
#     if not proxy_url:
#         return None
#     p = urlparse(proxy_url)
#     return {
#         "scheme": p.scheme.lower(),
#         "hostname": p.hostname,
#         "port": p.port,
#         "username": unquote(p.username) if p.username else None,
#         "password": unquote(p.password) if p.password else None,
#     }
#
#
# def message_to_dict(msg):
#     """Конвертируем Message в dict с обработкой всех типов контента"""
#     # 1. Текст или подпись (для медиа)
#     text = msg.text or msg.caption or ""
#     # 2. Извлекаем реальные URL из entities (важно для ссылок!)
#     links = []
#     if msg.entities:
#         for entity in msg.entities:
#             url = getattr(entity, "url", None)
#             if url and text:  # извлекаем текст ссылки по смещению
#                 link_text = text[entity.offset : entity.offset + entity.length]
#                 links.append({"text": link_text, "url": url})
#
#     # 3. Медиа-контент
#     media_info = None
#     if msg.media:
#         media_info = {"type": msg.media.value, "file_id": None, "file_unique_id": None}
#         # Получаем file_id в зависимости от типа медиа
#         try:
#             if msg.photo:
#                 media_info["file_id"] = msg.photo[-1].file_id  # лучшее качество
#                 media_info["file_unique_id"] = msg.photo[-1].file_unique_id
#             elif msg.video:
#                 media_info["file_id"] = msg.video.file_id
#             elif msg.document:
#                 media_info["file_id"] = msg.document.file_id
#             # ... добавьте другие типы при необходимости
#         except:
#             pass
#
#     # 4. Опросы
#     poll_info = None
#     if msg.poll:
#         poll_info = {
#             "question": msg.poll.question,
#             "options": [opt.text for opt in msg.poll.options],
#             "is_closed": msg.poll.closed,
#         }
#
#     # 5. Стикер/голосовое/аудио (кратко)
#     special_media = None
#     if msg.sticker:
#         special_media = {"type": "sticker", "emoji": msg.sticker.emoji}
#     elif msg.voice:
#         special_media = {"type": "voice", "duration": msg.voice.duration}
#
#     # 6. Ссылка на сообщение (исправил пробелы в URL!)
#     message_link = f"https://t.me/{CHANNEL_USERNAME}/{msg.id}"
#
#     return {
#         "id": msg.id,
#         "date": msg.date.isoformat() if msg.date else None,
#         "text": text,  # может быть пустым — это нормально для медиа
#         "links": links,  # ✅ отдельно вынесенные ссылки с URL!
#         # "views": getattr(msg, "views", None),
#         # "forwards": getattr(msg, "forwards", None),
#         # "media": media_info,  # ✅ полная информация о медиа
#         # "poll": poll_info,  # ✅ опросы
#         # "special_media": special_media,  # ✅ стикеры/голосовые
#         # "is_service": msg.service,  # ✅ флаг сервисного сообщения
#         # "message_link": message_link,  # ✅ исправленная ссылка
#         # entities оставляем для отладки, но основные данные уже извлечены выше
#         # "raw_entities": [
#         #     {"type": e.__class__.__name__, "offset": e.offset, "length": e.length}
#         #     for e in (msg.entities or [])
#         # ]
#     }
#
#
# def load_existing_data(filename):
#     """Загружает данные из JSON, если файл существует."""
#     if os.path.exists(filename):
#         try:
#             with open(filename, encoding="utf-8") as f:
#                 return json.load(f)
#         except json.JSONDecodeError:
#             print("⚠️ Ошибка чтения JSON, начинаем с нуля.")
#             return []
#     return []
#
#
# def save_data(filename, data):
#     """Сохраняет данные в JSON."""
#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)
#
#
# def parse_channel(telegram_cl):
#     # Получаем информацию о канале
#     chat = telegram_cl.get_chat(CHANNEL_USERNAME)
#     channel_id = chat.id
#     # # Получаем сообщения (сортировка: от новых к старым)
#     # messages = []
#
#     # 2. Загружаем уже сохраненные данные
#     existing_data = load_existing_data(filename=JSON_FILE)
#
#     # Создаем множество ID для быстрой проверки (O(1))
#     existing_ids = {item["id"] for item in existing_data}
#
#     new_messages = []
#     skipped_duplicates = 0
#     skipped_empty = 0
#
#     print("📥 Получение истории сообщений...")
#
#     # 3. Проходим по истории
#     for msg in telegram_cl.get_chat_history(chat_id=channel_id, limit=LIMIT):
#         # --- ПРОВЕРКА 1: Пустое сообщение ---
#         # Пропускаем, если нет текста И нет медиа (картинок, файлов и т.д.)
#         if not msg.text or msg.text == "":
#             skipped_empty += 1
#             continue
#         # if not msg.media:
#         #     skipped_empty += 1
#         #     continue
#         # --- ПРОВЕРКА 2: Дубликат ---
#         if msg.id in existing_ids:
#             skipped_duplicates += 1
#             continue
#
#         # Если всё ок, конвертируем и добавляем
#         msg_dict = message_to_dict(msg)
#         new_messages.append(msg_dict)
#
#         # Добавляем ID в множество, чтобы не дублировать внутри текущего запуска
#         existing_ids.add(msg.id)
#
#     # 4. Объединяем старые и новые данные
#     # (Старые + Новые)
#     updated_data = existing_data + new_messages
#
#     # 5. Сохраняем в файл
#     if new_messages:
#         save_data(filename=JSON_FILE, data=updated_data)
#         print(f"✅ Сохранено {len(new_messages)} новых записей в {JSON_FILE}")
#     else:
#         print("ℹ️ Новых сообщений нет.")
#     print(f"🚫 Пропущено дубликатов: {skipped_duplicates}")
#     print(f"🚫 Пропущено пустых: {skipped_empty}")
#     return new_messages
#
#
# def clean_old_records(filename=JSON_FILE, days_to_keep=10):
#     """
#     Удаляет записи старше указанного количества дней из JSON файла.
#
#     Args:
#         filename: Имя файла с данными
#         days_to_keep: Сколько дней хранить записи (по умолчанию 10)
#     """
#     # Загружаем данные
#     try:
#         with open(filename, encoding="utf-8") as f:
#             data = json.load(f)
#     except FileNotFoundError:
#         print(f"❌ Файл {filename} не найден")
#         return
#     except json.JSONDecodeError:
#         print(f"❌ Ошибка чтения JSON в файле {filename}")
#         return
#
#     if not isinstance(data, list):
#         print("❌ Данные должны быть списком")
#         return
#
#     # Вычисляем дату отсечения (10 дней назад от текущего момента)
#     cutoff_date = datetime.now() - timedelta(days=days_to_keep)
#
#     # Фильтруем записи
#     filtered_data = []
#     removed_count = 0
#
#     for record in data:
#         try:
#             # Парсим дату из записи (формат: "2026-03-22T01:03:53")
#             # Убираем возможные пробелы в ключах (в вашем файле есть "date " с пробелом)
#             date_str = record.get("date", record.get("date ", "")).strip()
#
#             if not date_str:
#                 removed_count += 1
#                 continue
#
#             # Парсим дату
#             record_date = datetime.fromisoformat(date_str)
#
#             # Оставляем только свежие записи
#             if record_date >= cutoff_date:
#                 filtered_data.append(record)
#             else:
#                 removed_count += 1
#
#         except (ValueError, TypeError) as e:
#             print(f"⚠️ Ошибка парсинга даты в записи {record.get('id', 'unknown')}: {e}")
#             removed_count += 1
#             continue
#
#     # Сохраняем отфильтрованные данные
#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump(filtered_data, f, ensure_ascii=False, indent=4)
#
#
# if __name__ == "__main__":
#     telegram_cl = TelegramClient(
#         name="SEM",
#         api_id=int(api_iddd) if api_iddd else None,  # 🔧 int!
#         api_hash=telegtok,
#         parse_mode=ParseMode.HTML,
#         proxy=get_proxy_dict(proxy_url),
#     )
#
#     # 🔌 Подключаемся ОДИН раз перед циклом
#     telegram_cl.start()
#     parse_channel(telegram_cl=telegram_cl)
#     telegram_cl.stop()
#     print("🔌 Отключено")
#     clean_old_records()
