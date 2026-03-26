# pydant/pydantics.py

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, computed_field, field_validator

from logi import logi


SPACE_LIKE_CHARS = [
    "\u00a0",  # неразрывный пробел
    "\u2000",
    "\u2001",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",  # разные ширины пробелов
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u202f",  # узкий неразрывный пробел
    "\u205f",  # среднее математическое пространство
    "\u3000",  # идеографический пробел
]


INVISIBLE_CHARS = [
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\ufeff",  # BOM
]

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff"
    "\U00002702-\U000027b0"
    "\U000024c2-\U0001f251"
    "]+",
    flags=re.UNICODE,
)


class ParsTextT(BaseModel):
    """ОЧИСТКА ТЕКСТА ДЛЯ ПОСТА ИЗ ПУЛЬСА"""

    text_after: str

    @field_validator("text_after", mode="before")
    @classmethod
    def clean_text(cls, v: Any) -> str:
        if not v:
            return ""
        text = str(v)
        # 1. Невидимые символы
        for char in INVISIBLE_CHARS:
            text = text.replace(char, "")
        # 2. Эмодзи
        text = EMOJI_PATTERN.sub("", text)
        # 3. Тикеры {$TICKER} → TICKER
        text = re.sub(r"\{\$([A-Z0-9@_]+)\}", r"\1", text)
        # 4. Хэштэги #слово → пробел
        text = re.sub(r"#\w+", " ", text)
        # 5. Стоп-фразы (дисклеймеры)
        stop_phrases = [
            "не иир",
            "не является иир",
            "иир",
            "пост носит исключительно информативный характер",
            "подпишись",
            "информация носит аналитический характер",
            "узнать подробнее и подключиться",
            "не индивидуальная инвестиционная рекомендация",
            "Подключайтесь к стратегии",
            "Дата следующего поста",
            "для меня честь",
            "уважением",
            "следующего поста",
            "Новые идеи доступны",
        ]
        text_lower = text.lower()
        for phrase in stop_phrases:
            idx = text_lower.find(phrase)
            if idx != -1:
                text = text[:idx].strip()
                break
        # 6. Ссылки
        text = re.sub(r"https?://[^\s]+", "", text)
        # 7. Пробелы
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\s*\n", " ", text)
        text = text.replace("\n", "")
        text = text.replace("\r", "")
        # 8. Финал
        text = text.strip()
        # 9. 900 символов
        if len(text) > 900:
            text = text[:897] + "..."
        elif len(text) < 100:
            text = ""
        return text

    @property
    def text(self) -> str:
        return self.text_after

    def __str__(self) -> str:
        return self.text_after


class ParsTextTnews(BaseModel):
    """Модель для очистки текста новости Т-Инвестиций"""

    text_after: str

    @field_validator("text_after", mode="before")
    @classmethod
    def clean_text(cls, v: Any) -> str:
        if not v:
            return ""

        text = str(v)

        # 🔹 1. ЗАМЕНЯЕМ пробелоподобные символы на обычный пробел (НЕ удаляем!)
        for char in SPACE_LIKE_CHARS:
            text = text.replace(char, " ")

        # 🔹 2. Удаляем только реально невидимые символы
        for char in INVISIBLE_CHARS:
            text = text.replace(char, "")

        # 🔹 3. Нормализуем Юникод (разбираем составные символы)
        text = unicodedata.normalize("NFKC", text)

        # 🔹 4. Удаляем эмодзи
        text = EMOJI_PATTERN.sub("", text)

        # 🔹 5. Тикеры: {$SBER} → SBER
        text = re.sub(r"\{\$([A-Z0-9@_./-]+)\}", r"\1", text)

        # 🔹 6. Хэштэги: #слово → удаляем
        text = re.sub(r"#\w+", "", text)

        # 🔹 7. Стоп-фразы (дисклеймеры)
        stop_phrases = ["не иир", "не является иир", "иир", "не инвестиционная рекомендация"]
        text_lower = text.lower()
        for phrase in stop_phrases:
            idx = text_lower.find(phrase)
            if idx != -1:
                text = text[:idx].strip()
                break

        # 🔹 8. Markdown-ссылки: [текст](url) → текст
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Обычные URL
        text = re.sub(r"https?://[^\s]+", "", text)

        # 🔹 9. Нормализуем пробелы и переносы
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")

        # 🔹 10. Убираем множественные пробелы → один
        text = re.sub(r" {2,}", " ", text)

        # 🔹 11. Пробелы ПЕРЕД пунктуацией убираем, ПОСЛЕ — оставляем
        # "текст ." → "текст." но "текст. Далее" → остаётся как есть
        text = re.sub(r"\s+([.,:;!?])", r"\1", text)  # перед знаками
        text = re.sub(r"([.,:;!?])([^\s])", r"\1 \2", text)  # после знаков, если нет пробела

        # 🔹 12. Финальная очистка
        text = text.strip()

        return text

    @property
    def text(self) -> str:
        return self.text_after

    def __str__(self) -> str:
        return self.text_after


class UfaDate(BaseModel):
    """МОДЕЛЬ КОНВЕРТАЦИИ UTC В УФИМСКОЕ ВРЕМЯ"""

    raw_date: str

    @computed_field
    # @property
    def date(self) -> str | None:
        """UTC В УФИМСКОЕ ВРЕМЯ"""
        if not self.raw_date:
            return None
        try:
            # Заменяем Z на +00:00 для корректного парсинга
            dt = datetime.fromisoformat(self.raw_date.replace("Z", "+00:00"))
            # Создаём часовую зону (UTC+5)
            ufa_tz = timezone(timedelta(hours=5))
            # Конвертируем время
            dt_ufa = dt.astimezone(ufa_tz)
            # Форматируем в читаемый вид
            return dt_ufa.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, AttributeError) as e:
            logi.err.info(f"date() в pydant/pydantics.py utc в уфимское время, e : {e}")
            return None

    @property
    def datetime_obj(self) -> datetime | None:
        """Возвращает как datetime объект"""
        if self.date:
            try:
                return datetime.strptime(self.date, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError, AttributeError) as e:
                logi.err.info(f"datetime() в pydant/pydantics.py возвращает как datetime объект, e : {e}")
        return None

    def __str__(self) -> str:
        """Позволяет использовать объект как строку"""
        return self.date or ""
