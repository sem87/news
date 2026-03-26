# def classify_news(text: str) -> tuple[NewsImpact, list[str]]:
#     """
#     Классифицирует новость по тексту.
#     Порядок: 1) прямые тикеры 2) отрасль 3) макро 4) general.
#     Возвращает (тип влияния, список тикеров).
#     """
#     lower = text.lower()
#
#     # 1. Прямые упоминания тикеров
#     for ticker, keywords in TICKER_KEYWORDS.items():
#         for kw in keywords:
#             if kw.lower() in lower:
#                 return NewsImpact.DIRECT, [ticker]
#
#     # 2. Отраслевые новости
#     for sector_data in SECTOR_KEYWORDS.values():
#         tickers = sector_data["tickers"]
#         if not tickers:
#             continue
#         for kw in sector_data["keywords"]:
#             if kw.lower() in lower:
#                 return NewsImpact.SECTOR, list(tickers)
#
#     # 3. Макро
#     for kw in MACRO_KEYWORDS["keywords"]:
#         if kw.lower() in lower:
#             return NewsImpact.MACRO, list(TICKERS)
#
#     # 4. Общая новость — привязываем ко всем тикерам (или пустой список — не привязывать)
#     return NewsImpact.GENERAL, []
#
#
# def collect_news_for_tickers(
#     days: int = NEWS_DAYS,
#     include_general: bool = False,
# ) -> dict[str, list[dict[str, Any]]]:
#     """
#     Собирает и классифицирует новости для списка тикеров (config.TICKERS).
#
#     - Берёт новости с РБК за последние `days` дней.
#     - Классифицирует: direct → sector → macro → general.
#     - Раскладывает по тикерам.
#
#     Возвращает:
#     {
#         "SBER": [
#             {
#                 "date": "2026-03-14",
#                 "title": "...",
#                 "summary": "...",
#                 "impact": "direct",
#                 "tickers": ["SBER"],
#                 "source": "RBC"
#             },
#             ...
#         ],
#         "LKOH": [...],
#         ...
#     }
#
#     Если include_general=False, новости с impact "general" не привязываются ни к одному тикеру.
#     """
#     raw_news = fetch_rbk_rss(days=days)
#
#     # Инициализируем пустые списки для всех тикеров
#     result: dict[str, list[dict[str, Any]]] = {t: [] for t in TICKERS}
#
#     seen: set[tuple[str, str]] = set()  # (date, title) — дедупликация
#
#     for item in raw_news:
#         title = item["title"]
#         date_str = item["date"]
#         key = (date_str, title)
#         if key in seen:
#             continue
#         seen.add(key)
#
#         text = _get_text(item["raw_entry"])
#         impact, tickers = classify_news(text)
#
#         if impact == NewsImpact.GENERAL and not include_general:
#             continue
#         if impact == NewsImpact.GENERAL and include_general:
#             tickers = list(TICKERS)
#
#         record = {
#             "date": date_str,
#             "title": title,
#             "summary": item["summary"],
#             "impact": impact.value,
#             "tickers": tickers,
#             "source": "RBC",
#         }
#
#         for t in tickers:
#             if t in result:
#                 result[t].append(record)
#
#     # Сортируем по дате (новые сверху) внутри каждого тикера
#     for t in result:
#         result[t].sort(key=lambda x: x["date"], reverse=True)
#
#     return result
#
#
# def get_series_with_news(
#     candles_by_ticker: dict[str, Any] | None = None,
#     days: int = NEWS_DAYS,
# ) -> dict[str, Any]:
#     """
#     Формирует структуру для объединения с данными свечей (main.py).
#
#     Если передан candles_by_ticker (словарь тикер -> list of candle-like dicts),
#     возвращает:
#       series[ticker] = { "candles": [...], "news": [...] }
#
#     Если не передан — только новости:
#       series[ticker] = { "news": [...] }
#     """
#     news_by_ticker = collect_news_for_tickers(days=days)
#
#     series: dict[str, Any] = {}
#     for ticker in TICKERS:
#         entry: dict[str, Any] = {}
#         if candles_by_ticker and ticker in candles_by_ticker:
#             candles = candles_by_ticker[ticker]
#             if candles and hasattr(candles[0], "begin"):
#                 entry["candles"] = [{"date": c.begin[:10], "close": c.close, "volume": c.volume} for c in candles]
#             else:
#                 entry["candles"] = list(candles) if candles else []
#         entry["news"] = news_by_ticker.get(ticker, [])
#         series[ticker] = entry
#
#     return {"series": series}
