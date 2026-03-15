from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI

from config import TICKERS
from news_collector import collect_news_for_tickers


MOEX_CANDLES_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json"


class MoexError(RuntimeError):
    pass


class TickerNotFoundError(MoexError):
    pass


@dataclass(frozen=True)
class Candle:
    begin: str
    end: str
    open: float
    close: float
    high: float
    low: float
    value: float
    volume: float


def _iso(d: date) -> str:
    """Конвертирует дату в ISO формат"""
    return d.isoformat()


def get_candles(ticker: str, days: int = 7, timeout_s: float = 10.0) -> list[Candle]:
    """
    Получает ежедневные свечи с MOEX ISS за последние `days` дней (включительно).
    Использует:
      - from: сегодня - days
      - to: сегодня
      - interval: 24 (ежедневный)
    """
    if days <= 0:
        raise ValueError("days должно быть положительным")

    today = date.today()
    start = today - timedelta(days=days)

    url = MOEX_CANDLES_URL.format(ticker=ticker)
    params = {"from": _iso(start), "to": _iso(today), "interval": 24}

    try:
        resp = requests.get(url, params=params, timeout=timeout_s)
    except requests.Timeout as e:
        raise MoexError(f"Timeout для {ticker}") from e
    except requests.RequestException as e:
        raise MoexError(f"Ошибка запроса для {ticker}: {e}") from e

    if resp.status_code == 404:
        raise TickerNotFoundError(f"Тикер {ticker} не найден (HTTP 404)")

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise MoexError(f"Ошибка HTTP для {ticker}: {resp.status_code}") from e

    try:
        payload = resp.json()
    except ValueError as e:
        raise MoexError(f"MOEX вернул не JSON для {ticker}") from e

    candles = payload.get("candles", {})
    columns: list[str] = candles.get("columns") or []
    data: list[list[Any]] = candles.get("data") or []

    if not columns:
        raise MoexError(f"Неожиданная форма ответа от MOEX для {ticker}: отсутствуют candles.columns")

    if not data:
        raise TickerNotFoundError(f"Нет свечей для {ticker} в {_iso(start)}..{_iso(today)}")

    idx = {name: i for i, name in enumerate(columns)}
    required = ["begin", "end", "open", "close", "high", "low", "value", "volume"]
    missing = [c for c in required if c not in idx]
    if missing:
        raise MoexError(f"Неожиданные столбцы от MOEX для {ticker}, отсутствуют: {missing}")

    out: list[Candle] = []
    for row in data:
        try:
            out.append(
                Candle(
                    begin=str(row[idx["begin"]]),
                    end=str(row[idx["end"]]),
                    open=float(row[idx["open"]]),
                    close=float(row[idx["close"]]),
                    high=float(row[idx["high"]]),
                    low=float(row[idx["low"]]),
                    value=float(row[idx["value"]]),
                    volume=float(row[idx["volume"]]),
                )
            )
        except (TypeError, ValueError) as e:
            raise MoexError(f"Неправильная строка свечи для {ticker}: {row}") from e

    return out


def prepare_llm_payload(
    candles_by_ticker: dict[str, list[Candle]],
    news_by_ticker: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """
    Подготавливает данные для LLM: свечи Мосбиржи + новости РБК по каждому тикеру.
    """
    series: dict[str, dict[str, Any]] = {}
    for ticker, candles in candles_by_ticker.items():
        entry: dict[str, Any] = {
            "candles": [{"date": c.begin[:10], "close": c.close, "volume": c.volume} for c in candles],
        }
        if news_by_ticker and ticker in news_by_ticker:
            # Для LLM оставляем date, title, summary, impact
            entry["news"] = [
                {"date": n["date"], "title": n["title"], "summary": n["summary"], "impact": n["impact"]}
                for n in news_by_ticker[ticker]
            ]
        else:
            entry["news"] = []
        series[ticker] = entry
    return {"source": "MOEX ISS + RBC", "interval": "1d", "series": series}


def analyze_with_llm(prepared_data: dict[str, Any]) -> str:
    """
    Отправляет подготовленные данные MOEX в OpenAI и получает анализ.
    Требует BOTHUB_API_KEY и BOTHUB_BASE_URL в .env.news
    """
    load_dotenv(".env.news")
    client = OpenAI(
        api_key=os.getenv("BOTHUB_API_KEY"),
        base_url=os.getenv("BOTHUB_BASE_URL"),  # <-- Это направляет запросы в BotHub
    )

    system = (
        "Ты профессиональный финансовый аналитик с опытом работы на Мосбирже.\n"
        "Твоя задача — дать заключение на основе котировок И новостей, если они есть.\n"
        "Правила работы с новостями:\n"
        "- ЕСЛИ в данных есть поле 'news' — проанализируй его суть (макс. 10 слов).\n"
        "- ЕСЛИ новостей нет — работай только с котировками, не выдумывай события.\n"
        "- ЗАПРЕЩЕНО: придумывать новости, если их нет в исходных данных.\n"
        "Формат ответа: маркированный список, затем общий итог."
    )

    user = (
        "Проанализируй данные по акциям Мосбиржи за последнюю неделю.\n"
        "Для каждого тикера:\n"
        "- динамика цены (рост/падение/флэт)\n"
        "- оценка активности по объему\n"
        "- наблюдения (волатильность, аномалии)\n"
        "- [Если есть новость]: краткая суть (до 10 слов) + влияние на цену (позитив/негатив)\n"
        "- общий итог: лидер/аутсайдер недели\n"
        "Данные (JSON):\n"
        f"{json.dumps(prepared_data, ensure_ascii=False)}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.6,
    )

    return resp.choices[0].message.content or ""


def main() -> None:
    candles_by_ticker: dict[str, list[Candle]] = {}
    errors: list[tuple[str, str]] = []

    for t in TICKERS:
        try:
            candles_by_ticker[t] = get_candles(t, days=7)
        except TickerNotFoundError as e:
            errors.append((t, str(e)))
        except MoexError as e:
            errors.append((t, str(e)))

    if errors:
        print("Some tickers failed:")
        for t, err in errors:
            print(f" - {t}: {err}")

    if not candles_by_ticker:
        raise SystemExit("Нет данных для анализа.")

    # Сбор новостей РБК за те же 7 дней
    try:
        news_by_ticker = collect_news_for_tickers(days=7)
    except Exception as e:
        print(f"Новости не загружены (анализ только по свечам): {e}")
        news_by_ticker = None

    prepared = prepare_llm_payload(candles_by_ticker, news_by_ticker=news_by_ticker)

    try:
        # analysis = analyze_with_llm(prepared)
        # print(analysis)
        # =================анализ ИИ  =====================================
        print(prepared)

    except RuntimeError as e:
        print(f"\nАнализ с помощью LLM пропущен: {e}\n")
        print("Подготовленные данные (JSON) для отправки в OpenAI вручную:\n")
        print(json.dumps(prepared, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
    # привет
