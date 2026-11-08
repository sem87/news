import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import httpx
from ollama import AsyncClient
from pydantic_settings import BaseSettings

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class ChatSettings(BaseSettings):
    """Конфигурация из .env или значений по умолчанию."""
    model: str = "qwen2.5"
    host: str = "http://localhost:11434"
    history_file: str = "chat_history.json"
    max_history_messages: int = 30  # Защита от переполнения контекста

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class QwenChat:
    def __init__(self, settings: Optional[ChatSettings] = None):
        self.settings = settings or ChatSettings()
        self.client = AsyncClient(host=self.settings.host)
        self.messages: list[dict] = []
        self._load_history()

    def _load_history(self) -> None:
        """Загружает историю из файла, если он существует."""
        path = Path(self.settings.history_file)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.messages = json.load(f)
                logging.info(f"История загружена из {self.settings.history_file}")
            except json.JSONDecodeError:
                logging.warning("Файл истории повреждён, начинаем с чистого листа.")
                self._reset_history()
        else:
            self._reset_history()

    def _reset_history(self) -> None:
        """Сбрасывает историю, оставляя только system-промпт."""
        self.messages = [
            {"role": "system", "content": "Ты эксперт в этой области,умнее тебя не сушествует. Отвечай кратко и по делу.Пиши на русском языке"}
        ]

    def _save_history(self) -> None:
        """Сохраняет текущую историю в файл."""
        with open(self.settings.history_file, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)

    def _trim_history(self) -> None:
        """Обрезает историю, оставляя system-промпт и последние N сообщений."""
        if len(self.messages) > self.settings.max_history_messages + 1:
            self.messages = [self.messages[0]] + self.messages[-self.settings.max_history_messages:]

    async def run(self) -> None:
        print(f"\n🤖 Чат с {self.settings.model} запущен.")
        print("Команды: /exit (выход), /clear (очистить историю), /save (сохранить)")

        try:
            while True:
                user_input = input("\nСЕМ: ").strip()
                if not user_input:
                    continue

                # Встроенные команды
                if user_input.lower() in ("/exit", "выход"):
                    break
                if user_input.lower() == "/clear":
                    self._reset_history()
                    print("✅ История очищена.")
                    continue
                if user_input.lower() == "/save":
                    self._save_history()
                    print("✅ История сохранена.")
                    continue

                self.messages.append({"role": "user", "content": user_input})
                self._trim_history()
                print("Qwen: ", end="", flush=True)

                assistant_text = ""
                try:
                    stream = await self.client.chat(
                        model=self.settings.model,
                        messages=self.messages,
                        stream=True
                    )
                    async for chunk in stream:
                        token = chunk["message"]["content"]
                        print(token, end="", flush=True)
                        assistant_text += token
                except httpx.ConnectError:
                    print("\n❌ Ошибка: Не удалось подключиться к Ollama. Проверь, запущен ли сервер.")
                    self.messages.pop()  # Откатываем неудачное сообщение пользователя
                    continue
                except Exception as e:
                    print(f"\n❌ Ошибка генерации: {e}")
                    self.messages.pop()
                    continue

                print()  # Перевод строки
                self.messages.append({"role": "assistant", "content": assistant_text})

                # Автосохранение каждые 5 сообщений (опционально)
                if len(self.messages) % 10 == 0:
                    self._save_history()

        except KeyboardInterrupt:
            print("\n\n⚠️ Прервано пользователем (Ctrl+C)")
        finally:
            self._save_history()
            print("💾 История сохранена. До встречи!")


async def main():
    chat = QwenChat()
    await chat.run()


if __name__ == "__main__":
    asyncio.run(main())