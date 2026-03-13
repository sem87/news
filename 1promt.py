import os

from dotenv import load_dotenv
from openai import OpenAI


# Загружаем переменные из .env
load_dotenv(".env.news")
# Создаём клиента с настройками BotHub
client = OpenAI(
    api_key=os.getenv("BOTHUB_API_KEY"),
    base_url=os.getenv("BOTHUB_BASE_URL"),  # <-- Это направляет запросы в BotHub
)

try:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "расскажи про gpt-4o-mini что он делает "}], model="gpt-4o-mini"
    )
    print("✅ Успех!")
    print(response.choices[0].message.content)
except Exception as e:
    print("❌ Ошибка:")
    print(e)
