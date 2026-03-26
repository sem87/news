# parser/t_pulse_parser
import json
import os
from pathlib import Path

from logi import logis


# from pydant.pydantics import *  # ParsText


# В начале файла:
BASE_DIR = Path(__file__).parent.parent  # news/
OUTPUT_FILE = BASE_DIR / "json_file" / "predvaritelno_news.json"


# ============================================================
# 💾 ФУНКЦИИ СОХРАНЕНИЯ С ПРОВЕРКОЙ ДУБЛИКАТОВ
# ============================================================
def load_existing_posts(filename: str) -> list[dict]:
    """Загружает существующие посты из файла"""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки {filename}: {e}")
        return []


def get_text_signature(text: str, length: int = 10) -> str:
    """Получает сигнатуру текста (первые N символов) для сравнения"""
    if not text:
        return ""
    return text[:length].strip().lower()


def is_duplicate(new_post: dict, existing_signatures: set, signature_length: int = 10) -> bool:
    """Проверяет, есть ли пост с такой же сигнатурой"""
    signature = get_text_signature(new_post.get("text", ""), signature_length)
    if not signature:
        return False
    return signature in existing_signatures


def save_posts_with_check(new_posts: list[dict], filename: str, signature_length: int = 10) -> dict[str, int]:
    """
    Сохраняет посты с проверкой на дубликаты.
    Returns:
        dict со статистикой: {'added': int, 'skipped': int, 'total': int}
    """
    # 1. Создаём директорию если нет
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # 2. Загружаем существующие посты и их сигнатуры
    existing_posts = load_existing_posts(filename)
    existing_signatures = {
        get_text_signature(post.get("text", ""), signature_length) for post in existing_posts if post.get("text")
    }
    # 3. Фильтруем новые посты
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
    # 4. Сохраняем только новые
    if posts_to_save:
        all_posts = existing_posts + posts_to_save
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2, default=str)
        logis.inf.info(f"💾 Сохранено {stats['added']} новых постов в {filename}")
    else:
        pass
        # logi.inf.info(f"ℹ️ Нет новых постов для сохранения")
    return stats


# ============================================================
# 💾 ФУНКЦИИ СОХРАНЕНИЯ С ПРОВЕРКОЙ ДУБЛИКАТОВ
# ============================================================
# -------------НАЧАЛО СОРТИРОВКА JSON ПО ВРЕМЕНИ ---------------
def sort_posts_by_date(input_file: str = OUTPUT_FILE, output_file: str = OUTPUT_FILE) -> list:
    """
    Загружает посты из файла, сортирует по дате (сначала новые) и сохраняет.

    Args:
        input_file: Путь к исходному файлу с постами
        output_file: Путь к файлу для сохранения отсортированных постов

    Returns:
        Отсортированный список постов
    """
    # 1. Загружаем посты из файла
    with open(input_file, encoding="utf-8") as f:
        posts = json.load(f)
    # 2. Сортируем по дате (убывание: новые сначала)
    sorted_posts = sorted(posts, key=lambda x: x.get("date", ""), reverse=True)
    # 3. Сохраняем обратно в файл
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sorted_posts, f, ensure_ascii=False, indent=2)
    return sorted_posts


# -------------КОНЕЦ СОРТИРОВКА JSON ПО ВРЕМЕНИ ----------------
