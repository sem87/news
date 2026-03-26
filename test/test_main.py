# import os
# import sys
# from datetime import date
# from types import SimpleNamespace
#
# import pytest
#
#
# PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if PROJECT_ROOT not in sys.path:
#     sys.path.insert(0, PROJECT_ROOT)
#
# import main  # noqa: E402
# from main import (  # noqa: E402
#     Candle,
#     MoexError,
#     TickerNotFoundError,
#     _iso,
#     analyze_with_llm,
#     get_candles,
#     prepare_llm_payload,
#     send_telegram,
# )
#
#
# def test__iso_returns_isoformat():
#     d = date(2024, 1, 2)
#     assert _iso(d) == "2024-01-02"
#
#
# def test_get_candles_builds_url_and_parses_response(monkeypatch):
#     today = date(2024, 1, 10)
#
#     class DummyResp:
#         status_code = 200
#
#         def __init__(self, payload):
#             self._payload = payload
#
#         def raise_for_status(self):
#             pass
#
#         def json(self):
#             return self._payload
#
#     def fake_today():
#         return today
#
#     payload = {
#         "candles": {
#             "columns": ["begin", "end", "open", "close", "high", "low", "value", "volume"],
#             "data": [
#                 ["2024-01-09 10:00:00", "2024-01-09 23:50:00", 100, 110, 120, 90, 1000, 10],
#             ],
#         }
#     }
#
#     called = {}
#
#     def fake_get(url, params=None, timeout=None):
#         called["url"] = url
#         called["params"] = params
#         called["timeout"] = timeout
#         return DummyResp(payload)
#
#     monkeypatch.setattr(main, "date", SimpleNamespace(today=fake_today))
#     monkeypatch.setattr(main.requests, "get", fake_get)
#
#     candles = get_candles("SBER", days=7, timeout_s=5.0)
#
#     assert called["url"].endswith("/SBER/candles.json")
#     assert called["params"]["interval"] == 24
#     assert isinstance(candles[0], Candle)
#     assert candles[0].close == 110
#
#
# def test_get_candles_invalid_days():
#     with pytest.raises(ValueError):
#         get_candles("SBER", days=0)
#
#
# def test_get_candles_404_raises_ticker_not_found(monkeypatch):
#     class DummyResp:
#         status_code = 404
#
#         def raise_for_status(self):
#             pass
#
#         def json(self):
#             return {}
#
#     def fake_get(_url, **_kwargs):
#         return DummyResp()
#
#     monkeypatch.setattr(main.requests, "get", fake_get)
#
#     with pytest.raises(TickerNotFoundError):
#         get_candles("UNKNOWN", days=7)
#
#
# def test_get_candles_http_error_raises_moexerror(monkeypatch):
#     class DummyResp:
#         status_code = 500
#
#         def raise_for_status(self):
#             raise main.requests.HTTPError("boom")
#
#         def json(self):
#             return {}
#
#     def fake_get(_url, **_kwargs):
#         return DummyResp()
#
#     monkeypatch.setattr(main.requests, "get", fake_get)
#
#     with pytest.raises(MoexError):
#         get_candles("SBER", days=7)
#
#
# def test_prepare_llm_payload_with_and_without_news():
#     candles_by_ticker = {
#         "SBER": [
#             Candle(
#                 begin="2024-01-01T00:00:00",
#                 end="2024-01-01T23:50:00",
#                 open=100,
#                 close=110,
#                 high=120,
#                 low=90,
#                 value=1000,
#                 volume=10,
#             )
#         ]
#     }
#     news_by_ticker = {
#         "SBER": [
#             {"date": "2024-01-01", "title": "News", "summary": "Summary", "impact": "direct"},
#         ]
#     }
#
#     prepared = prepare_llm_payload(candles_by_ticker, news_by_ticker)
#     assert prepared["source"] == "MOEX ISS + RBC"
#     assert "SBER" in prepared["series"]
#     assert prepared["series"]["SBER"]["candles"][0]["close"] == 110
#     assert prepared["series"]["SBER"]["news"][0]["title"] == "News"
#
#     prepared_without_news = prepare_llm_payload(candles_by_ticker, news_by_ticker=None)
#     assert prepared_without_news["series"]["SBER"]["news"] == []
#
#
# def test_analyze_with_llm_builds_request_and_returns_content(monkeypatch):
#     captured = {}
#
#     class DummyChoice:
#         def __init__(self, content):
#             self.message = SimpleNamespace(content=content)
#
#     class DummyResp:
#         def __init__(self, content):
#             self.choices = [DummyChoice(content)]
#
#     class DummyChat:
#         def __init__(self):
#             self.completions = SimpleNamespace(create=lambda **_kwargs: captured.setdefault("resp", DummyResp("ok")))
#
#     class DummyClient:
#         def __init__(self, *args, **kwargs):
#             captured["init"] = {"args": args, "kwargs": kwargs}
#             self.chat = DummyChat()
#
#     monkeypatch.setattr(main, "OpenAI", DummyClient)
#
#     data = {"test": True}
#     result = analyze_with_llm(data)
#
#     assert result == "ok"
#     assert "init" in captured
#     assert "resp" in captured
#
#
# def test_send_telegram_uses_client_and_swallows_exceptions(capsys):
#     class DummyClient:
#         def __enter__(self):
#             return self
#
#         def __exit__(self, exc_type, exc, tb):
#             return False
#
#         def send_message(self, _group, _msg):
#             raise RuntimeError("boom")
#
#     send_telegram("hello", telegram_cl=DummyClient(), group="grp")
#     out = capsys.readouterr().out
#     assert "send_telegram() ошибка в телеграмм" in out
