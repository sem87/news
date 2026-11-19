from crewai import Agent, Task, Crew, Process, LLM
import re

# 1. ТВОЙ ИСХОДНЫЙ КОД (Вставь сюда свой код, который нужно улучшить)
EXISTING_CODE = """
import json


"""

# 2. Настройка LLM
llm = LLM(
    model="ollama/qwen2.5-coder:1.5b",
    base_url="http://localhost:11434",
    temperature=0.2  # Низкая температура для точного рефакторинга
)

# 3. Агенты
refactorer = Agent(
    role="Senior Python Refactorer",
    goal="Написать новый код калькулятор для вводишь первое число потом операцию потом второе число в ООП стиль, добавить обработку ошибок и новую функцию",
    backstory="Ты эксперт по чистому коду (Clean Code). Ты пишешь супер-код в красивые классы с type hints и docstrings.",
    llm=llm,
    verbose=True
)

reviewer = Agent(
    role="Strict Code Reviewer",
    goal="Проверить, что новый код работает, не содержит ошибок и соответствует задаче",
    backstory="Ты ищешь любые пропущенные исключения, отсутствие type hints и логические ошибки. Ты не пропустишь плохой код.",
    llm=llm,
    verbose=True
)

# 4. Задачи
task_refactor = Task(
    description=f"""
    Вот исходный код, который нужно улучшить:
    ```python
    {EXISTING_CODE}
    ```

    Твоя задача:
    1. Переписать новый код, создав ООП-класс `DataProcessor`.
    2. Добавить надежную обработку ошибок (например, если в словаре нет ключа 'age', использовать значение по умолчанию 0 или пропускать, не роняя программу).
    3. Добавить новый метод `save_to_json(self, filename: str)`, который сохраняет обработанный результат в JSON-файл.
    4. Добавить блок `if __name__ == '__main__':` для демонстрации работы.
    5. Верни ТОЛЬКО готовый Python-код в блоке ```python ... ```.
    """,
    expected_output="Полный, готовый к запуску Python-код в блоке markdown",
    agent=refactorer
)

task_review = Task(
    description="""
    Проверь код, написанный предыдущим агентом.
    1. Убедись, что все импорты на месте (json, typing и т.д.).
    2. Убедись, что обработка ошибок (try/except или .get()) реализована корректно.
    3. Если есть ошибки, исправь их.
    4. Верни ТОЛЬКО финальный, исправленный Python-код в блоке ```python ... ```.
    """,
    expected_output="Финальный, безупречный Python-код в блоке markdown",
    agent=reviewer,
    context=[task_refactor]
)

# 5. Создаём команду
crew = Crew(
    agents=[refactorer, reviewer],
    tasks=[task_refactor, task_review],
    process=Process.sequential,
    verbose=True
)

# 6. Запуск и СОХРАНЕНИЕ ФАЙЛА
print("🚀 Агенты анализируют и улучшают твой код...")
result = crew.kickoff()

# === ИЗВЛЕЧЕНИЕ И СОХРАНЕНИЕ КОДА ===
match = re.search(r'```python\s*(.*?)\s*```', result.raw, re.DOTALL | re.IGNORECASE)
if match:
    clean_code = match.group(1).strip()
else:
    clean_code = result.raw.strip()

filename = "refactored_app.py"
with open(filename, "w", encoding="utf-8") as file:
    file.write(clean_code)

print("\n" + "=" * 60)
print("🎉 РЕФАКТОРИНГ ЗАВЕРШЕН!")
print(f"📁 Улучшенный код сохранен в: {filename}")
print(f"▶️  Запусти его, чтобы проверить: python {filename}")
print("=" * 60)