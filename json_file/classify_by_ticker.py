# json_file/classify_by_ticker.py
"""
МОДУЛЬ КЛАССИФИКАЦИИ НОВОСТЕЙ ПО ТИКЕРАМ
Распределяет новости из общего файла по конкретным акциям (SBER, LKOH...)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# 🔹 Импорт функций работы с JSON
from json_file.work_json import load_existing_posts  # , save_posts_to_json

# 🔹 Импорт конфигурации и моделей
from news_config import MACRO_KEYWORDS, SECTOR_KEYWORDS, TICKER_KEYWORDS, TICKERS, NewsImpact


# 🔹 Пути к файлам
BASE_DIR = Path(__file__).parent.parent  # news/
INPUT_FILE = BASE_DIR / "json_file" / "predvaritelno_news.json"
OUTPUT_FILE = BASE_DIR / "json_file" / "news_by_ticker.json"


def classify_news(text: str) -> tuple[NewsImpact, list[str]]:
    """
    Классифицирует новость по тексту.
    Порядок приоритета: 1) прямые тикеры → 2) отрасль → 3) макро → 4) general.

    Возвращает:
        tuple[NewsImpact, list[str]]: (тип влияния, список затронутых тикеров)
    """
    if not text:
        return NewsImpact.GENERAL, []

    lower = text.lower()

    # 1️⃣ Прямые упоминания тикеров (наивысший приоритет)
    for ticker, keywords in TICKER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower:
                return NewsImpact.DIRECT, [ticker]

    # 2️⃣ Отраслевые новости (средний приоритет)
    for sector_data in SECTOR_KEYWORDS.values():
        tickers = sector_data["tickers"]
        if not tickers:
            continue
        for kw in sector_data["keywords"]:
            if kw.lower() in lower:
                return NewsImpact.SECTOR, list(tickers)

    # 3️⃣ Макроэкономика (низкий приоритет, но влияет на все)
    for kw in MACRO_KEYWORDS["keywords"]:
        if kw.lower() in lower:
            return NewsImpact.MACRO, list(TICKERS)

    # 4️⃣ Общая новость (не влияет на акции напрямую)
    return NewsImpact.GENERAL, []


def collect_news_for_tickers(
    input_file: Path = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    include_general: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """
    Собирает и классифицирует новости для списка тикеров.

    Аргументы:
        input_file: Путь к файлу с сырыми новостями
        output_file: Путь для сохранения классифицированных новостей
        include_general: Включать ли новости типа GENERAL (по умолчанию нет)

    Возвращает:
        dict[str, list[dict]]: Словарь {тикер: [список новостей]}
    """
    # 🔹 Загружаем новости из файла
    raw_news = load_existing_posts(filename=input_file)

    if not raw_news:
        print("⚠️ Новости не найдены в файле")
        return {t: [] for t in TICKERS}

    # 🔹 Инициализируем пустые списки для всех тикеров
    result: dict[str, list[dict[str, Any]]] = {t: [] for t in TICKERS}

    # 🔹 Для дедупликации (date + text)
    seen: set[tuple[str, str]] = set()

    # 🔹 Счётчики статистики
    stats = {"DIRECT": 0, "SECTOR": 0, "MACRO": 0, "GENERAL": 0, "SKIPPED": 0}

    for msg in raw_news:
        text = msg.get("text", "")
        date_str = msg.get("date", "")

        # Пропускаем пустые
        if not text or not date_str:
            continue

        # Дедупликация
        key = (date_str, text[:100])  # Первые 100 символов для ключа
        if key in seen:
            continue
        seen.add(key)

        # 🔹 Классифицируем
        impact, tickers = classify_news(text=text)
        stats[impact.name] += 1

        # Пропускаем GENERAL, если не включены
        if impact == NewsImpact.GENERAL and not include_general:
            stats["SKIPPED"] += 1
            continue

        # Если GENERAL включены — привязываем ко всем тикерам
        if impact == NewsImpact.GENERAL and include_general:
            tickers = list(TICKERS)

        # 🔹 Формируем запись
        record = {
            "date": date_str,
            "text": text,
            "impact": impact.value,  # "direct", "sector", "macro", "general"
            "tickers": tickers,  # ["SBER"], ["LKOH", "ROSN"], ...
            "source": "RBC",
            "classified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 🔹 Раскладываем по тикерам
        for t in tickers:
            if t in result:
                result[t].append(record)

    # 🔹 Сортируем по дате (новые сверху) внутри каждого тикера
    for t in result:
        result[t].sort(key=lambda x: x["date"], reverse=True)

    # # 🔹 Сохраняем результат в файл
    # save_posts_to_json(filename=output_file, posts=result)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 🔹 Вывод статистики
    print(f"\n{'=' * 50}")
    print("📊 СТАТИСТИКА КЛАССИФИКАЦИИ")
    print(f"{'=' * 50}")
    print(f"✅ DIRECT:  {stats['DIRECT']}")
    print(f"🏭 SECTOR:  {stats['SECTOR']}")
    print(f"📈 MACRO:   {stats['MACRO']}")
    print(f"📰 GENERAL: {stats['GENERAL']}")
    print(f"⏭️ SKIPPED: {stats['SKIPPED']}")
    print(f"{'=' * 50}")
    print(f"💾 Сохранено в: {output_file}")
    print(f"{'=' * 50}\n")

    return result


def main_classify_by_ticker():
    """ТОЧКА ВХОДА: Классификация новостей по тикерам"""
    print("🚀 Запуск классификации новостей по тикерам...")

    try:
        # 🔹 Запускаем классификацию
        result = collect_news_for_tickers(
            input_file=INPUT_FILE,
            output_file=OUTPUT_FILE,
            include_general=False,  # GENERAL новости не привязываем к тикерам
        )

        # 🔹 Выводим пример для первого тикера
        for ticker, news_list in result.items():
            if news_list:
                print(f"\n📌 {ticker}: {len(news_list)} новостей")
                for n in news_list[:2]:  # Первые 2 новости
                    print(f"   • [{n['impact']}] {n['date']} — {n['text'][:80]}...")
                break  # Показываем только один тикер для примера

    except FileNotFoundError as e:
        print(f"❌ Ошибка: Файл не найден — {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка: Неверный формат JSON — {e}")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main_classify_by_ticker()
