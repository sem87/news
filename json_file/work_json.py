# json_file/work_json.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from logi import logis


# from news_config import INPUT_FILE, OUTPUT_FILE

# from pydant.pydantics import *  # ParsText


# В начале файла:
BASE_DIR = Path(__file__).parent.parent  # news/
INPUT_FILE = BASE_DIR / "json_file" / "predvaritelno_news.json"
OUTPUT_FILE = BASE_DIR / "json_file" / "news_by_ticker.json"


# ============================================================
# 💾 ФУНКЦИИ СОХРАНЕНИЯ С ПРОВЕРКОЙ ДУБЛИКАТОВ
# ============================================================
def load_existing_posts(filename: Path) -> list[dict]:
    """ЗАГРУЖАЕТ ПОСТЫ ИЗ JSON"""
    try:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logis.err.info(f"load_existing_posts() в json_file/work_json.py {filename} не загруз, Exception as e : {e}")
        return []


def save_file(output_file, filtered_posts):
    """СОХРАНЯЕТ ПОСТЫ В JSON (АТОМАРНО, через временный файл)"""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(filtered_posts, f, ensure_ascii=False, indent=2)
        return filtered_posts
    except Exception as e:
        logis.err.info(f"save_file() в json_file/work_json.py не записали в файл, Exception as e : {e}")


def get_text_signature(text: str, length: int = 15) -> str:
    """ПОЛУЧАЕТ ПЕРВЫЕ length СИМВОЛОВ для сравнения"""
    try:
        if not text:
            return ""
        return text[:length].strip().lower()
    except Exception as e:
        logis.err.info(f"get_text_signature() в json_file/work_json.py ошибка текста, Exception as e : {e}")
        return ""


def is_duplicate(new_post: dict, existing_signatures: set, signature_length: int = 10) -> bool:
    """ПРОВЕРЯЕТ, ЕСТЬ ЛИ ТАКОЙ ТЕКСТ"""
    try:
        signature = get_text_signature(new_post.get("text", ""), signature_length)
        if not signature:
            return False
        return signature in existing_signatures
    except Exception as e:
        logis.err.info(f"is_duplicate() в json_file/work_json.py ошибка в проверке есть ли текст, Exception as e : {e}")
        return False


def save_posts_with_check(new_posts: list[dict], filename, signature_length: int = 15) -> dict[str, int]:
    """СОХРАНЯЕТ ПОСТЫ С ПРОВЕРКОЙ НА ДУБЛИКАТЫ"""
    # Создаём директорию если нет
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # Загружаем существующие посты и их сигнатуры
    existing_posts = load_existing_posts(filename)
    existing_signatures = {
        get_text_signature(post.get("text", ""), signature_length) for post in existing_posts if post.get("text")
    }
    # Фильтруем новые посты
    stats = {"added": 0, "skipped": 0, "total": len(new_posts)}
    posts_to_save = []
    for post in new_posts:
        if is_duplicate(post, existing_signatures, signature_length):
            stats["skipped"] += 1
        else:
            posts_to_save.append(post)
            # Добавляем сигнатуру в множество, чтобы не допустить дубли внутри новой пачки
            sig = get_text_signature(post.get("text", ""), signature_length)
            if sig:
                existing_signatures.add(sig)
            stats["added"] += 1
    # Сохраняем только новые
    if posts_to_save:
        all_posts = existing_posts + posts_to_save
        # Сохраняем обратно в файл
        save_file(output_file=filename, filtered_posts=all_posts)
        # with open(filename, "w", encoding="utf-8") as f:
        #     json.dump(all_posts, f, ensure_ascii=False, indent=2, default=str)
        logis.inf.info(f"💾 Сохранено {stats['added']} новых постов в {filename}")
    else:
        pass
        # logi.inf.info(f"ℹ️ Нет новых постов для сохранения")
    return stats


# ============================================================
# 💾 ФУНКЦИИ СОХРАНЕНИЯ С ПРОВЕРКОЙ ДУБЛИКАТОВ
# ============================================================


# -------------НАЧАЛО СОРТИРОВКА JSON ПО ВРЕМЕНИ ---------------
# predvaritelno_news.json
def sort_posts_by_date(input_file, output_file) -> list:  # : str = OUTPUT_FILE  ,: str = OUTPUT_FILE
    """СОРТИРУЕТ ПОСТЫ ПО ДАТЕ (сначало новые) УДАЛЯЕТ ЕСЛИ БОЛЬШЕ 14 ДНЕЙ"""
    try:
        # Загружаем посты из файла
        posts = load_existing_posts(filename=input_file)
        # Сортируем по дате (убывание: новые сначала)
        sorted_posts = sorted(posts, key=lambda x: x.get("date", ""), reverse=True)
        # ФИЛЬТРУЕМ: удаляем посты старше 14 дней
        now = datetime.now()
        cutoff_date = now - timedelta(days=14)  # Граница: 14 дней назад
        filtered_posts = []
        for post in sorted_posts:
            try:
                # Узнаем дату поста в формате "YYYY-MM-DD HH:MM:SS"
                post_date = datetime.strptime(post.get("date", ""), "%Y-%m-%d %H:%M:%S")
                # Оставляем только посты новее границы
                if post_date >= cutoff_date:
                    filtered_posts.append(post)
            except (ValueError, TypeError):
                # Если дата некорректная — пропускаем пост
                continue
        # Сохраняем обратно в файл
        save_file(output_file=output_file, filtered_posts=filtered_posts)
        return filtered_posts
    except Exception as e:
        logis.err.info(f"sort_posts_by_date в json_file/work_json.py сорт удаление json: Exception as e : {e}")


# сортирует и удаляет news_by_ticker.json
def sort_news_by_ticker(input_file, output_file) -> dict:
    """СОРТИРУЕТ ПОСТЫ ПО ДАТЕ (сначала новые) ДЛЯ КАЖДОГО ТИКЕРА,УДАЛЯЕТ ПОСТЫ СТАРШЕ 14 ДНЕЙ"""
    try:
        # Загружаем данные: структура {ticker: [posts]}
        data = load_existing_posts(filename=input_file)
        now = datetime.now()
        cutoff_date = now - timedelta(days=14)  # Граница: 14 дней назад
        filtered_data = {}
        for ticker, posts in data.items():
            # Сортируем посты тикера по дате (убывание: новые сначала)
            sorted_posts = sorted(posts, key=lambda x: x.get("date", ""), reverse=True)
            # Фильтруем: оставляем только посты новее 14 дней
            filtered_posts = []
            for post in sorted_posts:
                try:
                    # Парсим дату поста в формате "YYYY-MM-DD HH:MM:SS"
                    post_date = datetime.strptime(post.get("date", ""), "%Y-%m-%d %H:%M:%S")
                    # Оставляем пост, если он новее границы
                    if post_date >= cutoff_date:
                        filtered_posts.append(post)
                except (ValueError, TypeError):
                    # Если дата некорректная — пропускаем пост
                    continue

            # Сохраняем отфильтрованный список для тикера
            filtered_data[ticker] = filtered_posts
        # Сохраняем результат обратно в файл
        save_file(output_file=output_file, filtered_posts=filtered_data)
        return filtered_data
    except Exception as e:
        logis.err.info(f"sort_news_by_ticker() в json_file/work_json.py: ошибка при сортировке/фильтрации: {e}")
        return {}


# -------------КОНЕЦ СОРТИРОВКА JSON ПО ВРЕМЕНИ ----------------
if __name__ == "__main__":
    pass
