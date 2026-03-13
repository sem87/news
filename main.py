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
    return d.isoformat()


def get_candles(ticker: str, days: int = 7, timeout_s: float = 10.0) -> list[Candle]:
    """
    Fetch daily candles from MOEX ISS for the last `days` days (inclusive).
    Uses:
      - from: today - days
      - to: today
      - interval: 24 (daily)
    """
    if days <= 0:
        raise ValueError("days must be positive")

    today = date.today()
    start = today - timedelta(days=days)

    url = MOEX_CANDLES_URL.format(ticker=ticker)
    params = {"from": _iso(start), "to": _iso(today), "interval": 24}

    try:
        resp = requests.get(url, params=params, timeout=timeout_s)
    except requests.Timeout as e:
        raise MoexError(f"MOEX timeout for {ticker}") from e
    except requests.RequestException as e:
        raise MoexError(f"MOEX request error for {ticker}: {e}") from e

    if resp.status_code == 404:
        raise TickerNotFoundError(f"Ticker {ticker} not found (HTTP 404)")

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise MoexError(f"MOEX HTTP error for {ticker}: {resp.status_code}") from e

    try:
        payload = resp.json()
    except ValueError as e:
        raise MoexError(f"MOEX returned non-JSON for {ticker}") from e

    candles = payload.get("candles", {})
    columns: list[str] = candles.get("columns") or []
    data: list[list[Any]] = candles.get("data") or []

    if not columns:
        raise MoexError(f"Unexpected MOEX response shape for {ticker}: missing candles.columns")

    if not data:
        raise TickerNotFoundError(f"No candles returned for {ticker} in {_iso(start)}..{_iso(today)}")

    idx = {name: i for i, name in enumerate(columns)}
    required = ["begin", "end", "open", "close", "high", "low", "value", "volume"]
    missing = [c for c in required if c not in idx]
    if missing:
        raise MoexError(f"Unexpected MOEX columns for {ticker}, missing: {missing}")

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
            raise MoexError(f"Bad candle row for {ticker}: {row}") from e

    return out


def prepare_llm_payload(
    candles_by_ticker: dict[str, list[Candle]],
) -> dict[str, Any]:
    """
    Prepare compact data for LLM: close prices and volumes per day.
    """
    series: dict[str, list[dict[str, Any]]] = {}
    for ticker, candles in candles_by_ticker.items():
        series[ticker] = [{"date": c.begin[:10], "close": c.close, "volume": c.volume} for c in candles]
    return {"source": "MOEX ISS", "interval": "1d", "series": series}


def analyze_with_llm(
    prepared_data: dict[str, Any],
    *,
    model: str | None = None,
) -> str:
    """
    Send prepared MOEX data to OpenAI and get analysis.
    Requires OPENAI_API_KEY in .env.
    Optional: OPENAI_MODEL in .env (or pass model=...).
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Create .env based on .env.example")

    final_model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)

    system = (
        "You are a financial analyst. Provide a concise Russian analysis based only on the "
        "provided OHLC-derived series (close) and volumes. Avoid hallucinating news."
    )
    user = (
        "Проанализируй акции Мосбиржи по дневным данным за последнюю неделю.\n"
        "Для каждого тикера дай:\n"
        "- краткий вывод по динамике цены (рост/падение/флэт)\n"
        "- оценку активности по объему\n"
        "- простые наблюдения (волатильность по закрытиям, аномальные дни)\n"
        "- общий итог по списку (лидеры/аутсайдеры недели)\n\n"
        "Данные (JSON):\n"
        f"{json.dumps(prepared_data, ensure_ascii=False)}"
    )

    resp = client.chat.completions.create(
        model=final_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
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
        raise SystemExit("No data to analyze.")

    prepared = prepare_llm_payload(candles_by_ticker)
    try:
        analysis = analyze_with_llm(prepared)
    except RuntimeError as e:
        print(f"\nLLM analysis skipped: {e}\n")
        print("Prepared data (JSON) to send to OpenAI manually:\n")
        print(json.dumps(prepared, ensure_ascii=False, indent=2))
        return

    print("\n=== LLM analysis ===\n")
    print(analysis)


if __name__ == "__main__":
    main()
