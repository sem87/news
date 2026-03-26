# import asyncio
# import os
#
# from dotenv import load_dotenv
# from tinkoff import InvestClient
#
#
# """ДЛЯ ЧТЕНИЯ ТОКЕНА"""
# load_dotenv(".env.news")  # Если файл в той же папке, что и скрипт
# token = os.getenv("TOKSELL")  # Обратите внимание на имя переменной
# accid = os.getenv("AOCID")  # Обратите внимание на имя переменной
#
# # instruments = [
# #     NewsInstrument(figi="BBG004730N88"),  # Сбербанк
# #     NewsInstrument(figi="BBG004730ZXS8"),  # Газпром
# # ]
#
# # def candl(cl, day: int, interval, figi: str, tiker: str):
# #     """ИЗВЛЕКАЕТ ДАННЫЕ ИЗ СВЕЧЕК ЗА ОПРЕДЕЛЕННЫЙ ПЕРИОД"""
# #     try:
# #         # Получаем данные о свечах указываем интервал
# #         candle_data = cl.market_data.get_candles(
# #             figi=figi,
# #             from_=now() - timedelta(days=day),  # было day=1 (неверно)
# #             to=now(),  # было datetime.UTC() (неверно)
# #             interval=interval,
# #         )  # '''CandleInterval.CANDLE_INTERVAL_15_MIN  # нужно указать конкретный интервал'''
# #         # Преобразуем в удобный формат
# #         candles = []
# #         for candle in candle_data.candles:
#
#
# async def get_news():
#     async with InvestClient(token) as client:
#         # Получаем новости через REST эндпоинт
#         news = await client.news.get(
#             from_date="2026-03-19",
#             to_date="2026-03-22",
#             instruments=[],  # пустой список = общие новости
#         )
#         for item in news:
#             print(f"{item.title} — {item.url}")
#
#
# asyncio.run(get_news())
