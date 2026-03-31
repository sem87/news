# json_file/classify_by_ticker.py
"""МОДУЛЬ КЛАССИФИКАЦИИ НОВОСТЕЙ ПО ТИКЕРАМ
Распределяет новости из общего файла по конкретным акциям (SBER, LKOH...)"""

import json
from pathlib import Path
from typing import Any

from json_file.work_json import load_existing_posts, save_file  # , save_posts_to_json
from logi import logis
from news_config import (  # , INPUT_FILE, OUTPUT_FILE
    MACRO_KEYWORDS,
    SECTOR_KEYWORDS,
    TICKER_KEYWORDS,
    TICKERS,
    NewsImpact,
)


# # В начале файла:
BASE_DIR = Path(__file__).parent.parent  # news/
INPUT_FILE = BASE_DIR / "json_file" / "predvaritelno_news.json"
OUTPUT_FILE = BASE_DIR / "json_file" / "news_by_ticker.json"


def classify_news(text: str) -> tuple[NewsImpact, list[str]]:
    """Классифицирует новость по тексту.Порядок приоритета: 1) прямые тикеры → 2) отрасль → 3) макро → 4) general."""
    if not text:
        return NewsImpact.GENERAL, []
    lower = text.lower()
    # Прямые упоминания тикеров (наивысший приоритет)
    for ticker, keywords in TICKER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower:
                return NewsImpact.DIRECT, [ticker]
    # Отраслевые новости (средний приоритет)
    for sector_data in SECTOR_KEYWORDS.values():
        tickers = sector_data["tickers"]
        if not tickers:
            continue
        for kw in sector_data["keywords"]:
            if kw.lower() in lower:
                return NewsImpact.SECTOR, list(tickers)
    # Макроэкономика (низкий приоритет, но влияет на все)
    for kw in MACRO_KEYWORDS["keywords"]:
        if kw.lower() in lower:
            return NewsImpact.MACRO, list(TICKERS)
    # Общая новость (не влияет на акции напрямую)
    return NewsImpact.GENERAL, []


def collect_news_for_tickers(
    input_file: Path = INPUT_FILE, output_file: Path = OUTPUT_FILE, include_general: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """КЛАССИФИЦИРУЕТ НОВОСТИ ДЛЯ СПИСКА ТИКЕРОВ.Словарь {тикер: [список новостей]}"""
    # Загружаем новости из файла
    raw_news = load_existing_posts(filename=input_file)
    if not raw_news:
        logis.inf.info("⚠️ Новости не найдены в файле")
        return {t: [] for t in TICKERS}
    # Инициализируем пустые списки для всех тикеров
    result: dict[str, list[dict[str, Any]]] = {t: [] for t in TICKERS}
    # Для дедупликации (date + text)
    seen: set[tuple[str, str]] = set()
    # Счётчики статистики
    stats = {"DIRECT": 0, "SECTOR": 0, "MACRO": 0, "GENERAL": 0, "SKIPPED": 0}
    for msg in raw_news:
        text = msg.get("text", "")
        date_str = msg.get("date", "")
        ticker = msg.get("ticker", [])
        hashtags = msg.get("hashtags", [])
        # Пропускаем пустые
        if not text or not date_str:
            continue
        # Дедупликация
        key = (date_str, text[:100])  # Первые 100 символов для ключа
        if key in seen:
            continue
        seen.add(key)
        # Классифицируем
        impact, tickers = classify_news(text=text)
        stats[impact.name] += 1
        # Пропускаем GENERAL, если не включены
        if impact == NewsImpact.GENERAL and not include_general:
            stats["SKIPPED"] += 1
            continue
        # Если GENERAL включены — привязываем ко всем тикерам
        if impact == NewsImpact.GENERAL and include_general:
            tickers = list(TICKERS)
        # Формируем запись
        record = {
            "date": date_str,
            "text": text,
            "impact": impact.value,  # "direct", "sector", "macro", "general"
            "tickers": tickers,  # ["SBER"], ["LKOH", "ROSN"], ...
            "ticker_recomend_t": ticker,
            "hashtags": hashtags,
        }
        # Раскладываем по тикерам
        for t in tickers:
            if t in result:
                result[t].append(record)
    # Сортируем по дате (новые сверху) внутри каждого тикера
    for t in result:
        result[t].sort(key=lambda x: x["date"], reverse=True)
    # Сохраняем результат в файл
    save_file(output_file=output_file, filtered_posts=result)
    # Вывод статистики
    logis.inf.info(
        f"✅ DIRECT:{stats['DIRECT']},🏭 SECTOR:{stats['SECTOR']},📈 MACRO:{stats['MACRO']},📰 GENERAL:{stats['GENERAL']},⏭️ SKIPPED:{stats['SKIPPED']}"
    )
    return result


def main_classify_by_ticker():
    """ТОЧКА ВХОДА: Классификация новостей по тикерам"""
    try:
        # Запускаем классификацию
        collect_news_for_tickers(
            input_file=INPUT_FILE, output_file=OUTPUT_FILE, include_general=False
        )  # GENERAL новости не привязываем к тикерам
    except FileNotFoundError as e:
        logis.err.info(f"main_classify_by_ticker() в json_file/classify_by_ticker.py Файл не найден , e : {e}")
    except json.JSONDecodeError as e:
        logis.err.info(f"main_classify_by_ticker() в json_file/classify_by_ticker.py Неверный формат JSON , e : {e}")
    except Exception as e:
        logis.err.info(f"main_classify_by_ticker() в json_file/classify_by_ticker.py Критическая ошибка , e : {e}")


if __name__ == "__main__":
    main_classify_by_ticker()
