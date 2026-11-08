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
    prompt = f"""
    Ты аналитик новостей. Проанализируй следующие данные и верни СТРОГО валидный JSON 
    с полями: "summary" (краткая суть), "sentiment" (позитив/негатив/нейтрально), "key_topics" (список тем).

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
            model="qwen2.5",  # или "llama3.2"
            prompt=prompt,
            format="json",  # Ключевой параметр для твоей задачи!
            stream=False  # Ждём весь ответ сразу, а не по словам
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