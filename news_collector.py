"""
Сбор и классификация новостей РБК за последние 7 дней.
Алгоритм: 1) прямые упоминания тикеров 2) отраслевые 3) макро 4) общая новость.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import feedparser
import requests

from config import TICKERS
from news_config import (
    MACRO_KEYWORDS,
    SECTOR_KEYWORDS,
    TICKER_KEYWORDS,
    NewsImpact,
)


# RSS РБК (главные новости, полный текст)
RBK_RSS_URL = "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"

# Таймаут запроса к РБК (сек)
RBK_TIMEOUT = 15

# Количество дней новостей
NEWS_DAYS = 7


def _strip_html(text: str) -> str:
    """Убирает HTML/CDATA и лишние пробелы для поиска ключевых слов."""
    if not text:
        return ""
    # Убираем CDATA
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    # Убираем теги
    text = re.sub(r"<[^>]+>", " ", text)
    # Нормализуем пробелы
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_pubdate(entry: Any) -> datetime | None:
    """Парсит дату публикации из элемента RSS."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            from time import mktime

            return datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)
        except (TypeError, OSError):
            pass
    if getattr(entry, "published", None):
        try:
            # "Sun, 15 Mar 2026 06:36:59 +0300"
            return datetime.strptime(
                entry.published.replace(" +0300", "").replace(" +0000", ""),
                "%a, %d %b %Y %H:%M:%S",
            ).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def _get_text(entry: Any) -> str:
    """Собирает единый текст из title + description для классификации."""
    parts = []
    if getattr(entry, "title", None):
        parts.append(_strip_html(entry.title))
    if getattr(entry, "description", None):
        parts.append(_strip_html(entry.description))
    if getattr(entry, "summary", None):
        parts.append(_strip_html(entry.summary))
    return " ".join(parts).lower()


def _get_summary(entry: Any, max_len: int = 200) -> str:
    """Краткое описание новости (до max_len символов)."""
    raw = ""
    if getattr(entry, "description", None):
        raw = _strip_html(entry.description)
    elif getattr(entry, "summary", None):
        raw = _strip_html(entry.summary)
    if not raw and getattr(entry, "title", None):
        raw = _strip_html(entry.title)
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 3].rsplit(" ", 1)[0] + "..."


def classify_news(text: str) -> tuple[NewsImpact, list[str]]:
    """
    Классифицирует новость по тексту.
    Порядок: 1) прямые тикеры 2) отрасль 3) макро 4) general.
    Возвращает (тип влияния, список тикеров).
    """
    lower = text.lower()

    # 1. Прямые упоминания тикеров
    for ticker, keywords in TICKER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower:
                return NewsImpact.DIRECT, [ticker]

    # 2. Отраслевые новости
    for sector_data in SECTOR_KEYWORDS.values():
        tickers = sector_data["tickers"]
        if not tickers:
            continue
        for kw in sector_data["keywords"]:
            if kw.lower() in lower:
                return NewsImpact.SECTOR, list(tickers)

    # 3. Макро
    for kw in MACRO_KEYWORDS["keywords"]:
        if kw.lower() in lower:
            return NewsImpact.MACRO, list(TICKERS)

    # 4. Общая новость — привязываем ко всем тикерам (или пустой список — не привязывать)
    return NewsImpact.GENERAL, []


def fetch_rbk_rss(days: int = NEWS_DAYS, timeout: float = RBK_TIMEOUT) -> list[dict[str, Any]]:
    """
    Загружает RSS РБК и возвращает список новостей за последние `days` дней.
    Каждый элемент: {"date": "YYYY-MM-DD", "title", "summary", "link", "raw_entry"}.
    """
    try:
        resp = requests.get(RBK_RSS_URL, timeout=timeout)
        resp.raise_for_status()
        content = resp.content
    except requests.RequestException as e:
        raise RuntimeError(f"Ошибка загрузки RSS РБК: {e}") from e

    feed = feedparser.parse(content)
    if feed.bozo and not getattr(feed, "entries", None):
        raise RuntimeError("Не удалось разобрать RSS РБК")

    cutoff = datetime.now(UTC) - timedelta(days=days)
    items = []

    for entry in getattr(feed, "entries", []) or []:
        pub_dt = _parse_pubdate(entry)
        if not pub_dt:
            continue
        if pub_dt.replace(tzinfo=UTC) < cutoff:
            continue

        date_str = pub_dt.strftime("%Y-%m-%d")
        title = _strip_html(getattr(entry, "title", "") or "")
        summary = _get_summary(entry)
        link = getattr(entry, "link", "") or ""

        items.append(
            {
                "date": date_str,
                "title": title,
                "summary": summary,
                "link": link,
                "raw_entry": entry,
            }
        )

    return items


def collect_news_for_tickers(
    days: int = NEWS_DAYS,
    include_general: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """
    Собирает и классифицирует новости для списка тикеров (config.TICKERS).

    - Берёт новости с РБК за последние `days` дней.
    - Классифицирует: direct → sector → macro → general.
    - Раскладывает по тикерам.

    Возвращает:
    {
        "SBER": [
            {
                "date": "2026-03-14",
                "title": "...",
                "summary": "...",
                "impact": "direct",
                "tickers": ["SBER"],
                "source": "RBC"
            },
            ...
        ],
        "LKOH": [...],
        ...
    }

    Если include_general=False, новости с impact "general" не привязываются ни к одному тикеру.
    """
    raw_news = fetch_rbk_rss(days=days)

    # Инициализируем пустые списки для всех тикеров
    result: dict[str, list[dict[str, Any]]] = {t: [] for t in TICKERS}

    seen: set[tuple[str, str]] = set()  # (date, title) — дедупликация

    for item in raw_news:
        title = item["title"]
        date_str = item["date"]
        key = (date_str, title)
        if key in seen:
            continue
        seen.add(key)

        text = _get_text(item["raw_entry"])
        impact, tickers = classify_news(text)

        if impact == NewsImpact.GENERAL and not include_general:
            continue
        if impact == NewsImpact.GENERAL and include_general:
            tickers = list(TICKERS)

        record = {
            "date": date_str,
            "title": title,
            "summary": item["summary"],
            "impact": impact.value,
            "tickers": tickers,
            "source": "RBC",
        }

        for t in tickers:
            if t in result:
                result[t].append(record)

    # Сортируем по дате (новые сверху) внутри каждого тикера
    for t in result:
        result[t].sort(key=lambda x: x["date"], reverse=True)

    return result


def get_series_with_news(
    candles_by_ticker: dict[str, Any] | None = None,
    days: int = NEWS_DAYS,
) -> dict[str, Any]:
    """
    Формирует структуру для объединения с данными свечей (main.py).

    Если передан candles_by_ticker (словарь тикер -> list of candle-like dicts),
    возвращает:
      series[ticker] = { "candles": [...], "news": [...] }

    Если не передан — только новости:
      series[ticker] = { "news": [...] }
    """
    news_by_ticker = collect_news_for_tickers(days=days)

    series: dict[str, Any] = {}
    for ticker in TICKERS:
        entry: dict[str, Any] = {}
        if candles_by_ticker and ticker in candles_by_ticker:
            candles = candles_by_ticker[ticker]
            if candles and hasattr(candles[0], "begin"):
                entry["candles"] = [{"date": c.begin[:10], "close": c.close, "volume": c.volume} for c in candles]
            else:
                entry["candles"] = list(candles) if candles else []
        entry["news"] = news_by_ticker.get(ticker, [])
        series[ticker] = entry

    return {"series": series}


def main() -> None:
    """Точка входа при запуске: python news_collector.py"""
    import json

    print("Сбор новостей РБК за последние 7 дней...")
    try:
        data = collect_news_for_tickers(days=NEWS_DAYS)
        total = sum(len(v) for v in data.values())
        print(f"Всего привязок новостей по тикерам: {total}")
        for ticker in TICKERS:
            n = len(data[ticker])
            if n > 0:
                print(f"  {ticker}: {n} новостей")
        print("\nРезультат (JSON):")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Ошибка: {e}")
        raise


if __name__ == "__main__":
    main()
