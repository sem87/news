import asyncio
import json
from pathlib import Path
from ollama import AsyncClient


async def analyze_news_file(input_file: str, output_file: str):
    # 1. Читаем твой спарсенный JSON
    path = Path(input_file)
    if not path.exists():
        print(f"❌ Файл {input_file} не найден!")
        return

    with open(path, "r", encoding="utf-8") as f:
        news_data = json.load(f)

    # 2. Формируем промпт (это аналог поля "prompt" или "messages" в payload)
    #  Роль → Задача → Формат вывода → Данные.
    prompt = f"""
    Ты строгий финансовый аналитик. Проанализируй предоставленные новости.
    Твоя задача: вернуть СТРОГО валидный JSON. Никакого текста до или после JSON, никаких markdown-обёрток (```json).

    Если новость не относится ни к одному из целевых тикеров, НЕ добавляй её в вывод.
    НЕ выдумывай тикеры. Если тикер не очевиден, не включай его.

    Ожидаемая структура JSON (пример):
    {{
      "analyzed_news": [
        {{
          "ticker": "SBER", 
          "date": "2026-11-08 14:35:29",
          "summary": "Краткая суть новости в 1 предложении",
          "sentiment": "positive", 
          "key_topics": ["дивиденды", "отчетность"]
        }}
      ]
    }}

    Данные для анализа:
    {json.dumps(news_data, ensure_ascii=False, indent=2)}
    """
    # 3. Инициализируем клиент (он сам знает, что стучаться на localhost:11434)
    client = AsyncClient(host="http://localhost:11434")

    print("⏳ Анализирую новости через Ollama... (это может занять 10-30 сек)")

    try:
        # 4. Делаем запрос.
        # Внимание: используем .generate(), а не .chat(), так как у нас нет истории диалога!
        # format="json" заставит модель выдать валидный JSON (работает в новых моделях типа qwen2.5, llama3.2)
        response = await client.generate(
            model="qwen2.5",
            prompt=prompt,
            format="json",
            stream=False,
            options={
                "temperature": 0.1,  # Жёстко гасим креативность, чтобы не было тикера "T"
                "top_p": 0.9,
                "num_predict": 2000,
                "seed": 42  # Для стабильности при отладке
            }
        )
        # 5. Получаем текст ответа
        result_text = response["response"]

        # 6. Проверяем, что это действительно JSON, и сохраняем
        result_json = json.loads(result_text)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_json, f, ensure_ascii=False, indent=2)

        print(f"✅ Анализ завершён! Результат сохранён в {output_file}")
        print("Содержимое:", json.dumps(result_json, ensure_ascii=False, indent=2))

    except json.JSONDecodeError:
        print("❌ Модель вернула не JSON, а обычный текст. Проверь промпт или смени модель.")
        print("Сырой ответ:", result_text)
    except Exception as e:
        print(f"❌ Ошибка при запросе к Ollama: {e}")


if __name__ == "__main__":
    # Запуск: читаем news.json, пишем результат в analysis_result.json
    asyncio.run(analyze_news_file("json_file/news_by_ticker.json", "analysis_udali.json"))