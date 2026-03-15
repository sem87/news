import os
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import news_collector  # noqa: E402
from news_collector import (  # noqa: E402
    MACRO_KEYWORDS,
    NEWS_DAYS,
    RBK_RSS_URL,
    SECTOR_KEYWORDS,
    TICKER_KEYWORDS,
    classify_news,
    collect_news_for_tickers,
    fetch_rbk_rss,
    get_series_with_news,
)


def test_classify_news_prefers_direct_over_sector_and_macro():
    text = "Сбербанк опубликовал отчет по Сберу"
    TICKER_KEYWORDS["SBER"] = ["Сбер"]
    impact, tickers = classify_news(text)
    assert impact.name.lower() == "direct"
    assert tickers == ["SBER"]


def test_classify_news_sector_when_sector_keyword_present():
    SECTOR_KEYWORDS["banking"] = {
        "tickers": ["SBER", "VTBR"],
        "keywords": ["банковский сектор"],
    }
    text = "Весь банковский сектор показал рост"
    impact, tickers = classify_news(text)
    assert impact.name.lower() == "sector"
    assert set(tickers) == {"SBER", "VTBR"}


def test_classify_news_macro_when_macro_keyword_present():
    MACRO_KEYWORDS["keywords"] = ["макроключ"]
    text = "Эта новость про макроключ и экономику"
    impact, tickers = classify_news(text)
    assert impact.name.lower() == "macro"
    from config import TICKERS

    assert set(tickers) == set(TICKERS)


def test_classify_news_general_when_nothing_matches():
    impact, tickers = classify_news("обычная новость без ключевых слов")
    assert impact.name.lower() == "general"
    assert tickers == []


def _make_fake_entry(title, description, published_dt):
    return SimpleNamespace(
        title=title,
        description=description,
        summary="",
        link="http://example.com",
        published=published_dt.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        published_parsed=None,
    )


def test_fetch_rbk_rss_filters_by_days_and_parses(monkeypatch):
    now = datetime.now(UTC)
    recent_dt = now - timedelta(days=1)
    old_dt = now - timedelta(days=NEWS_DAYS + 5)

    class DummyResp:
        status_code = 200

        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    def fake_get(url, timeout=None):
        assert url == RBK_RSS_URL
        assert timeout is not None
        item_recent = _make_fake_entry("Recent", "desc", recent_dt)
        item_old = _make_fake_entry("Old", "desc", old_dt)

        feed = SimpleNamespace(
            bozo=False,
            entries=[item_recent, item_old],
        )

        def fake_parse(_content):
            return feed

        monkeypatch.setattr(news_collector, "feedparser", SimpleNamespace(parse=fake_parse))
        return DummyResp(b"<xml></xml>")

    monkeypatch.setattr(news_collector.requests, "get", fake_get)

    items = fetch_rbk_rss(days=NEWS_DAYS, timeout=5)
    assert len(items) == 1
    assert items[0]["title"] == "Recent"


def test_fetch_rbk_rss_raises_on_request_error(monkeypatch):
    def fake_get(_url, **_kwargs):
        raise news_collector.requests.RequestException("boom")

    monkeypatch.setattr(news_collector.requests, "get", fake_get)

    with pytest.raises(RuntimeError):
        fetch_rbk_rss()


def test_collect_news_for_tickers_builds_result(monkeypatch):
    now = datetime.now(UTC)
    dt = now - timedelta(days=1)
    entry = _make_fake_entry("Title", "description about Сбер", dt)

    def fake_fetch_rbk_rss(**_kwargs):
        return [
            {
                "date": dt.strftime("%Y-%m-%d"),
                "title": "Title",
                "summary": "summary",
                "link": "http://example.com",
                "raw_entry": entry,
            }
        ]

    monkeypatch.setattr(news_collector, "fetch_rbk_rss", fake_fetch_rbk_rss)
    TICKER_KEYWORDS["SBER"] = ["Сбер"]

    data = collect_news_for_tickers(days=NEWS_DAYS)

    from config import TICKERS

    assert set(data.keys()) == set(TICKERS)
    assert any(item["title"] == "Title" for item in data["SBER"])


def test_get_series_with_news_only_news(monkeypatch):
    def fake_collect_news_for_tickers(**_kwargs):
        return {
            "SBER": [
                {
                    "date": "2024-01-01",
                    "title": "t",
                    "summary": "s",
                    "impact": "direct",
                    "tickers": ["SBER"],
                    "source": "RBC",
                }
            ]
        }

    monkeypatch.setattr(news_collector, "collect_news_for_tickers", fake_collect_news_for_tickers)

    from config import TICKERS

    result = get_series_with_news(candles_by_ticker=None, days=NEWS_DAYS)
    for t in TICKERS:
        assert "news" in result["series"][t]


def test_get_series_with_news_with_candles_like_objects(monkeypatch):
    class DummyCandle:
        def __init__(self):
            self.begin = "2024-01-01T00:00:00"
            self.close = 110
            self.volume = 10

    def fake_collect_news_for_tickers(**_kwargs):
        return {"SBER": []}

    monkeypatch.setattr(news_collector, "collect_news_for_tickers", fake_collect_news_for_tickers)

    candles_by_ticker = {"SBER": [DummyCandle()]}

    result = get_series_with_news(candles_by_ticker=candles_by_ticker, days=NEWS_DAYS)
    assert result["series"]["SBER"]["candles"][0]["close"] == 110
