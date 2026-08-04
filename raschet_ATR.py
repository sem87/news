from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
import pandas as pd
import requests

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


def get_candles(ticker: str, days: int = 1, timeout_s: float = 5.0, interval=60):  # -> list[Candle]:
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
    params = {"from": _iso(start), "to": _iso(today), "interval": interval}

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


def get_atr_for_ticker(ticker="SBER"):
    # 1. Получаем данные
    candles = get_candles(ticker=ticker, days=3, interval=60)  # 3 дня, чтобы набрать минимум для ATR 14
    # 2. Преобразуем список dataclass в DataFrame (Pandas умеет делать это напрямую)
    df = pd.DataFrame(candles)
    # 3. ФОРМУЛЫ ATR
    period = 14
    h = df['high']
    l = df['low']
    c = df['close']
    c_prev = c.shift(1)  # Сдвигаем close на 1 строку вниз, чтобы получить предыдущее закрытие
    # Истинный диапазон (True Range)
    tr1 = h - l
    tr2 = (h - c_prev).abs()
    tr3 = (l - c_prev).abs()
    df['tr'] = np.maximum.reduce([tr1, tr2, tr3])
    # ATR (сглаживание Уайлдера через экспоненциальную скользящую среднюю)
    df['atr'] = df['tr'].ewm(alpha=1 / period, adjust=False).mean()
    # 5. Практическое применение: расчет стопа для последней свечи
    last = df.iloc[-1]
    # current_price = last['close']
    # print(current_price)
    current_atr = last['atr']
    return current_atr


if __name__ == "__main__":
    print(get_atr_for_ticker(ticker="NVTK"))

    # multiplier = 2  # Коэффициент защиты от шума (1.5 - 2.0)
    # stop_loss_price = current_price - (current_atr * multiplier)
    # print("\n--- Расчет позиции (Лонг) ---")
    # print(f"Текущая цена (Close): {current_price:.2f}")
    # print(f"Значение ATR (14):    {current_atr:.2f} руб.")
    # print(f"Безопасный Stop-Loss: {stop_loss_price:.2f} руб. (ниже цены на {current_atr * multiplier:.2f})")
    # print(f"% ATR от цены {(current_atr*100/current_price):.2f}")
