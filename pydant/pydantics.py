# pydant/pydantics.py
import html
import re
import unicodedata
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, computed_field, field_validator

from logi import logis


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

# 🔹 Глобальные константы — компилируем один раз
RE_TICKER = re.compile(r"\{\$([A-Z0-9@_./-]+)\}")
RE_HASHTAG = re.compile(r"#\w+")
RE_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
RE_URL = re.compile(r"https?://[^\s]+")
RE_MULTI_SPACE = re.compile(r" {2,}")
RE_PUNCT_BEFORE = re.compile(r"\s+([.,:;!?])")
RE_PUNCT_AFTER = re.compile(r"([.,:;!?])([^\s])")

# Стоп-фразы РБК + дисклеймеры (регистронезависимый поиск)
STOP_PHRASES = [
    "не иир",
    "не является иир",
    "иир",
    "не инвестиционная рекомендация",
    "оставайтесь на связи с рбк",
    "материал дополняется",
]
RE_STOP_PHRASES = re.compile(r"(" + "|".join(map(re.escape, STOP_PHRASES)) + r").*$", flags=re.I)

# Символы для замены/удаления
SPACE_LIKE_CHARS = {
    "\u00a0",
    "\u2000",
    "\u2001",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u202f",
    "\u205f",
    "\u3000",
}
INVISIBLE_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}

# Таблицы для str.translate (создаём один раз)
_DELETE_TABLE = str.maketrans("", "", "".join(INVISIBLE_CHARS))
_REPLACE_TABLE = str.maketrans({char: " " for char in SPACE_LIKE_CHARS})


class ParsTextT(BaseModel):
    """ОЧИСТКА ТЕКСТА ДЛЯ ПОСТА ИЗ ПУЛЬСА"""

    """переделать"""
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

    """переделать"""
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


class ParsTextRbk(BaseModel):
    """Модель для очистки текста новости РБК"""

    text: str  # Простое поле — без лишних проперти

    @field_validator("text", mode="before")
    @classmethod
    def clean_text(cls, v: Any) -> str:
        if not v:
            return ""

        text = str(v)

        # 🔹 0. Декодируем HTML-сущности: &nbsp; → пробел, &laquo; → « и т.д.
        text = html.unescape(text)

        # 🔹 1. Быстрая замена символов через translate
        text = text.translate(_DELETE_TABLE)  # Удаляем невидимые
        text = text.translate(_REPLACE_TABLE)  # Заменяем пробелоподобные на " "

        # 🔹 2. Нормализация Юникод + удаление эмодзи
        text = unicodedata.normalize("NFKC", text)
        text = EMOJI_PATTERN.sub("", text)

        # 🔹 3. Структурная очистка
        text = RE_TICKER.sub(r"\1", text)  # {$SBER} → SBER
        text = RE_HASHTAG.sub("", text)  # #слово → ''
        text = RE_MD_LINK.sub(r"\1", text)  # [text](url) → text
        text = RE_URL.sub("", text)  # http... → ''

        # 🔹 4. Удаляем стоп-фразы (всё, начиная с первой найденной)
        text = RE_STOP_PHRASES.sub("", text)

        # 🔹 5. Финальная нормализация пробелов и пунктуации
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        text = RE_MULTI_SPACE.sub(" ", text)  # Множественные пробелы → один
        text = RE_PUNCT_BEFORE.sub(r"\1", text)  # "текст ." → "текст."
        text = RE_PUNCT_AFTER.sub(r"\1 \2", text)  # "текст.Далее" → "текст. Далее"

        if len(text) > 500:
            text = text[:497] + "..."
        return text.strip()


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
            logis.err.info(f"date() в pydant/pydantics.py utc в уфимское время, e : {e}")
            return None

    @property
    def datetime_obj(self) -> datetime | None:
        """Возвращает как datetime объект"""
        try:
            date_str = self.date()
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, AttributeError) as e:
            logis.err.info(f"datetime() в pydant/pydantics.py возвращает как datetime объект, e : {e}")
            return None

    def __str__(self) -> str:
        """Позволяет использовать объект как строку"""
        return self.date or ""


class UfaRbkRss(BaseModel):
    """МОДЕЛЬ КОНВЕРТАЦИИ ДАТЫ В УФИМСКОЕ ВРЕМЯ (UTC+5)"""

    raw_date: str

    @field_validator("raw_date", mode="before")
    @classmethod
    def normalize_raw_date(cls, v):
        """Приводим входное значение к строке"""
        if not v:
            return ""
        return str(v).strip()

    @computed_field(return_type=str | None)
    @property
    def date(self) -> str | None:
        """Конвертирует дату в формат YYYY-MM-DD HH:MM:SS с учётом часового пояса Уфы (UTC+5)"""
        if not self.raw_date:
            return None

        try:
            # 🔹 1. Парсим дату в формате "ДД.ММ.ГГГГ ЧЧ:ММ:СС"
            # Если формат другой — пробуем ISO
            if re.match(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}", self.raw_date):
                dt = datetime.strptime(self.raw_date, "%d.%m.%Y %H:%M:%S")
                # Считаем, что входная дата уже в местном времени (или UTC — уточните логику)
                # Если это UTC, добавляем timezoneinfo:
                dt = dt.replace(tzinfo=UTC)
            else:
                # Пробуем ISO-формат как запасной вариант
                dt = datetime.fromisoformat(self.raw_date.replace("Z", "+00:00"))

            # 🔹 2. Конвертируем в уфимское время (UTC+5)
            ufa_tz = timezone(timedelta(hours=2))
            dt_ufa = dt.astimezone(ufa_tz)

            # 🔹 3. Форматируем результат
            return dt_ufa.strftime("%Y-%m-%d %H:%M:%S")

        except (ValueError, TypeError, AttributeError) as e:
            logis.err.info(f"date() в UfaDate: ошибка парсинга '{self.raw_date}', e: {e}")
            return None

    @property
    def datetime_obj(self) -> datetime | None:
        """Возвращает как datetime-объект (уже в уфимском времени)"""
        date_str = self.date  # 🔹 computed_field вызывается БЕЗ скобок!
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            logis.err.info(f"datetime_obj в UfaDate: ошибка, e: {e}")
            return None

    def __str__(self) -> str:
        """Позволяет использовать объект как строку"""
        return self.date or ""  # 🔹 self.date — свойство, не метод!
