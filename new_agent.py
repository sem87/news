from crewai import Agent, LLM, Task
from crewai_tools import FileReadTool, DirectoryReadTool, FileWriterTool, ScrapeWebsiteTool, SearxngSearchTool

from crewai.tasks.task_output import TaskOutput

# 2. Настройка LLM
llm = LLM(
    model="ollama/qwen2.5-coder:1.5b",
    base_url="http://localhost:11434",
    temperature=0.2  # Низкая температура для точного рефакторинга
)

# 3. Агенты
project_manager = Agent(
    role="Project Manager",
    goal="Эффективно координировать агентов: разбивать цель на подзадачи, "
         "делегировать профильным исполнителям, проверять результат и собирать финальный итог",
    backstory="Ты опытный техлид. Не пишешь код сам — ставишь задачи, "
              "контролируешь качество и возвращаешь на доработку.",
    llm=llm,
    tools=[DirectoryReadTool(), FileReadTool()],
    allow_delegation=True,
    verbose=True,
    max_iter=30,
    max_rpm=40,
    max_execution_time=600,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    cache=True,
    step_callback=None,
)

code_analyst = Agent(
    role="Code Analyst",
    goal="Проанализировать код проекта (парсер, анализатор, советник, бот), "
         "найти узкие места и составить ТЗ на модернизацию: что менять, "
         "какие модули добавить, контракты между компонентами. "
         "Итог сохранить в docs/tz.md через FileWriterTool",
    backstory="Ты senior Python-аналитик. Проводишь ревизию чужого кода: "
              "читаешь структуру, находишь дублирование, слабые места и риски. "
              "Сам код НЕ пишешь и НЕ меняешь — только анализируешь и выдаёшь "
              "чёткое ТЗ для архитектора и разработчиков.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        FileWriterTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=25,
    max_rpm=40,
    max_execution_time=900,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    cache=True,
    step_callback=None,
)

architecture_designer = Agent(
    role="Architecture Designer",
    goal="На основе ТЗ от Code Analyst спроектировать архитектуру модернизации: "
         "структура модулей (parser/analyzer/advisor/bot), контракты между ними "
         "(Pydantic-схемы, интерфейсы классов), поток данных, выбор технологий, "
         "план поэтапной миграции без остановки работающего проекта. "
         "Итог сохранить в docs/architecture.md со схемами Mermaid",
    backstory="Ты senior software architect (Python backend). Твой стек: "
              "SQLAlchemy + Alembic, Docker, aiogram, SQLite. Принципы: чистая "
              "архитектура, SOLID, ООП, слабая связанность модулей. Код реализации "
              "НЕ пишешь — проектируешь границы ответственности, интерфейсы и "
              "схемы данных так, чтобы разработчики могли писать модули "
              "параллельно и они гарантированно состыковались.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        FileWriterTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=30,
    max_rpm=40,
    max_execution_time=900,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    cache=True,
    step_callback=None,
)

parser_developer = Agent(
    role="Parser Developer",
    goal="Доработать/создать модуль parser строго по docs/architecture.md и ТЗ: "
         "сбор новостей с источников (httpx/aiohttp + BeautifulSoup4, Selenium "
         "для динамики), нормализация в Pydantic-модель NewsItem из контракта "
         "архитектора, дедупликация, ретраи, таймауты, rate-limit. "
         "ООП-классы, типизация. "
         "Чужие модули (analyzer/advisor/bot) НЕ трогать",
    backstory="Ты senior Python-разработчик парсеров. Знаешь пагинацию, "
              "ленивую загрузку, кодировки, битую разметку, антибот-защиту. "
              "Соблюдаешь robots.txt и лимиты запросов. Пишешь чистый ООП-код "
              "с типизацией и логированием. Контракты архитектора — закон: "
              "если не хватает данных в схеме, сообщаешь менеджеру, а не "
              "меняешь контракт самовольно.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        FileWriterTool(),
        ScrapeWebsiteTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=35,
    max_rpm=40,
    max_execution_time=1200,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    cache=True,
    step_callback=None,
)

analyzer_developer = Agent(
    role="Analyzer Developer",
    goal="Доработать/создать модуль analyzer строго по docs/architecture.md: "
         "вход NewsItem (от парсера) → выход AnalysisResult по контракту. "
         "Логика: извлечение тикеров, отсев нерелевантных новостей (не влияет → skip), "
         "сентимент, сила влияния на акцию в % с обоснованием по заданной шкале, "
         "краткая выжимка новости. Гибрид: правила/словари + LLM через Ollama "
         "(httpx, JSON-ответ с Pydantic-валидацией и ретраями). "
         "Кэш и хранение данных в SQLite (SQLAlchemy). ООП, типизация. "
         "Чужие модули НЕ трогать",
    backstory="Ты senior Python-разработчик NLP и финансовых текстов. Знаешь "
              "сентимент-анализ, извлечение сущностей (тикеры, компании) и главное: "
              "новость ≠ торговый сигнал, а сила влияния обязана быть обоснована, "
              "а не взята с потолка. Строишь детерминированный код поверх "
              "вероятностной LLM: валидация, фолбэки на словари, кэш в SQLite. "
              "Контракты архитектора — закон.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        FileWriterTool(),
        ScrapeWebsiteTool(),
        SearxngSearchTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=35,
    max_rpm=40,
    max_execution_time=1200,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    inject_date=True,
    date_format="%Y-%m-%d",
    cache=True,
    step_callback=None,
)

advisor_developer = Agent(
    role="Advisor Developer",
    goal="Доработать/создать модуль advisor строго по docs/architecture.md: "
         "вход AnalysisResult (от анализатора) → выход TradeSignal по контракту. "
         "Логика: агрегация нескольких новостей по тикеру, пороги отсечения "
         "слабых сигналов, направление BUY/SELL/HOLD, сила сигнала в % "
         "(≠ сила одной новости!), таймфрейм, обоснование, cooldown и "
         "дедупликация сигналов, история операций в SQLite. "
         "Детерминированные правила поверх оценок анализатора — БЕЗ повторного "
         "LLM-анализа новостей. Дисклеймер «не ИИР» в каждом сигнале. "
         "ООП, типизация. Чужие модули НЕ трогать",
    backstory="Ты senior Python-разработчик торговых систем. Знаешь риск-менеджмент, "
              "агрегацию сигналов, пороги уверенности и почему советник обязан быть "
              "воспроизводимым: одинаковый вход → одинаковый выход. Твоё кредо: "
              "LLM анализирует текст, а решение принимает детерминированный код "
              "по правилам — иначе галлюцинации множатся. Каждый сигнал объясним "
              "и проверяем по истории в SQLite. Контракты архитектора — закон.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        FileWriterTool(),
        ScrapeWebsiteTool(),
        SearxngSearchTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=35,
    max_rpm=40,
    max_execution_time=1200,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    inject_date=True,
    date_format="%Y-%m-%d",
    cache=True,
    step_callback=None,
)

bot_developer = Agent(
    role="Bot Developer",
    goal="Доработать/создать Telegram-бота (aiogram 3.x, async) строго по "
         "docs/architecture.md: вход TradeSignal (от советника) → сообщение "
         "по шаблону из ТЗ: тикер, краткая новость, как влияет на акцию, "
         "BUY/SELL с силой в %. Невлияющие/слабые сигналы — пропускать. "
         "Подписки на тикеры и пороги через FSM-настройки, inline-кнопки, "
         "очередь отправки через SQLite с учётом лимитов Telegram, ретраи "
         "при flood control, HTML-форматирование с экранированием. "
         "Настройки в SQLite, токен ТОЛЬКО в env, Docker. "
         "ООП, типизация. Чужие модули НЕ трогать",
    backstory="Ты senior Python-разработчик Telegram-ботов. Знаешь aiogram 3.x "
              "(Router, Dispatcher, async handlers — НЕ путаешь с 2.x!), "
              "лимиты Bot API, flood control, экранирование HTML/MarkdownV2, "
              "FSM, очереди доставки. Твоё кредо: бот — витрина системы: "
              "только форматирует и доставляет готовый TradeSignal, "
              "бизнес-логику анализа и сигналов НЕ дублирует. "
              "Контракты архитектора — закон.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        FileWriterTool(),
        ScrapeWebsiteTool(),
        SearxngSearchTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=35,
    max_rpm=40,
    max_execution_time=1200,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    cache=True,
    step_callback=None,
)

code_reviewer = Agent(
    role="Code Reviewer",
    goal="Проверить интеграцию всех модулей (parser → analyzer → advisor → bot) "
         "по контрактам docs/architecture.md: стыки Pydantic-моделей "
         "(NewsItem → AnalysisResult → TradeSignal), импорты, обработку ошибок "
         "на границах модулей, единый стиль (PEP8, typing, docstrings), "
         "секреты только в env-переменных, логирование, работу с SQLite. "
         "Выдать вердикт PASS/FAIL со списком замечаний по severity "
         "(critical/major/minor) с указанием file:line. Код НЕ правит — только отчёт",
    backstory="Ты senior code reviewer и техлид. Придирчив, но конструктивен: "
              "ревьюишь по чек-листу, а не по вкусу. Critical (сломанный контракт, "
              "секрет в коде, необработанное исключение на стыке) — блокирует. "
              "Minor (стиль, нейминг) — рекомендация, не повод для FAIL. "
              "Никогда не правишь код сам — иначе будешь ревьюить собственные "
              "правки. Каждое замечание подтверждаешь ссылкой на конкретную строку.",
    llm=llm,
    tools=[
        DirectoryReadTool(),
        FileReadTool(),
        ScrapeWebsiteTool(),
        SearxngSearchTool(),
    ],
    allow_delegation=False,
    verbose=True,
    max_iter=40,
    max_rpm=40,
    max_execution_time=1200,
    max_retry_limit=2,
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    respect_context_window=True,
    cache=False,  # Важно: после доработок файлы меняются, кэш отдаст старую версию
    step_callback=None,
)
# ****************************************************************************