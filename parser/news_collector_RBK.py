# parser\news_collector_RBK
"""СБОР НОВОСТЕЙ ИЗ ЛЕНТЫ RSS РБК"""

from __future__ import annotations

import time
from typing import Any

import feedparser
import requests

from logi import logis
from news_config import (
    RBK_TIMEOUT,
)
from pydant.pydantics import ParsTextRbk, UfaRbkRss


# ссылки на источник
RBK_RSS_URL = ["https://rssexport.rbc.ru/rbcnews/news/30/full.rss"]


def fetch_rbk_rss(timeout: float = RBK_TIMEOUT, rbc_rss_url: str = []) -> list[dict[str, Any]]:
    """ЗАГРУЖАЕТ RSS РБК"""
    try:
        resp = requests.get(rbc_rss_url, timeout=timeout)
        resp.raise_for_status()
        content = resp.content
    except requests.RequestException as e:
        raise RuntimeError(f"Ошибка загрузки RSS РБК: {e}") from e
    feed = feedparser.parse(content)
    if feed.bozo and not getattr(feed, "entries", None):
        raise RuntimeError("Не удалось разобрать RSS РБК")
    # cutoff = datetime.now(UTC) - timedelta(days=days)
    items = []
    for entry in getattr(feed, "entries", []) or []:
        items.append(entry)
    return items


# -------------НАЧАЛО ПЕРЕРАБОТКИ В НУЖНЫЙ СЛОВАРЬ-----------


def message_to_dict(msg: dict) -> dict:
    """КОНВЕРТИРУЕТ ЗАПИСЬ В НУЖНЫЙ МНЕ СЛОВАРЬ"""
    try:
        # Обработка даты
        raw_date = f"{msg.get('rbc_news_date', '')} {msg.get('rbc_news_time', '')}".strip()
        date = UfaRbkRss(raw_date=raw_date).date
        # Обработка текста
        title = msg.get("title", "") or ""
        rbc_news_full_text = msg.get("rbc_news_full-text", "") or ""
        text_after = f"{title} {rbc_news_full_text}".strip() if rbc_news_full_text else title
        text = ParsTextRbk(text=text_after).text
        # hashtags
        tags_list = msg.get("tags")
        if isinstance(tags_list, list) and tags_list and isinstance(tags_list[0], dict):
            tags = tags_list[0].get("term", "")
        else:
            tags = ""
        # Возвращаем готовый словарь
        return {"date": date, "text": text, "hashtags": tags, "ticker": []}
    except Exception as e:
        logis.err.info(f"message_to_dict() в parser/news_collector_RBK конверт в словарь: Exception as e : {e}")


# -------------НАЧАЛО ПЕРЕРАБОТКИ В НУЖНЫЙ СЛОВАРЬ-----------


def main_news_collector_rbk() -> None:
    """Точка входа при запуске: news_collector_RBK.py"""
    for rbc_rss_url in RBK_RSS_URL:
        time.sleep(1)  # Пауза между тикерами
        clean_posts = []
        for msg in fetch_rbk_rss(rbc_rss_url=rbc_rss_url):
            print("===============")
            clean_posts.append(message_to_dict(msg=msg))  # добавляем в уже обработанные посты
            print(message_to_dict(msg=msg))
            time.sleep(1)


if __name__ == "__main__":
    main_news_collector_rbk()
