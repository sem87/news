"""Генератор шаблона family.xlsx — стейджинг для векторной БД семьи."""
from __future__ import annotations
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

MAX_ROW = 2000                      # глубина валидации/подсветки
OUT = Path("family.xlsx")

REQ = PatternFill("solid", fgColor="C00000")   # обязательная колонка
OPT = PatternFill("solid", fgColor="1F4E79")   # необязательная
RED = PatternFill("solid", fgColor="FFC7CE")
GREY = PatternFill("solid", fgColor="E8E8E8")
ORANGE = PatternFill("solid", fgColor="FFE0B2")

# name, width, required, подсказка (всплывает при наведении на шапку)
COLUMNS = [
    ("id", 14, True, "Уникальный ключ, напр. med-0007. НИКОГДА не менять и не переиспользовать."),
    ("category", 14, True, "Тип записи. Список из листа dicts."),
    ("person", 18, True, "person_id из листа people. Несколько — через ; . Общее — family."),
    ("title", 32, True, "Заголовок 3-8 слов."),
    ("text", 80, True, "ЕДИНСТВЕННОЕ поле, которое векторизуется. 200-1500 символов, полные имена, даты внутри текста."),
    ("event_date", 13, False, "Дата факта, текстом YYYY-MM-DD."),
    ("valid_until", 13, False, "Срок действия документа, YYYY-MM-DD."),
    ("tags", 24, False, "Теги через ; в нижнем регистре."),
    ("doc_id", 16, False, "Общий id для длинного документа, разбитого на части."),
    ("part_no", 9, False, "Номер части внутри doc_id (1,2,3...)."),
    ("source", 24, True, "Откуда данные: скан, договор, со слов мамы."),
    ("file_path", 30, False, "Относительный путь к скану: archive/2024/polis.pdf"),
    ("access", 12, True, "public / family / private. private — только локальные модели!"),
    ("status", 12, True, "draft не попадает в индекс, verified попадает."),
    ("updated_at", 13, True, "Дата правки YYYY-MM-DD — для переиндексации."),
    ("author", 12, False, "Кто внёс запись."),
    ("notes", 30, False, "Служебное. НЕ векторизуется."),
]

PEOPLE_COLS = [
    ("person_id", 18, True, "Латиница, snake_case. На него ссылается records.person."),
    ("full_name", 28, True, "Полное ФИО."),
    ("aliases", 34, True, "Как называют в жизни, через ; — нужно для поиска 'у бабули'."),
    ("birth_date", 13, False, "YYYY-MM-DD"),
    ("relation", 16, False, "Роль в семье, список из dicts."),
    ("notes", 30, False, "Служебное."),
]

DICTS = {
    "category": ["person", "document", "medical", "finance", "education", "event",
                 "recipe", "story", "instruction", "property", "contact", "travel", "pet", "other"],
    "access": ["public", "family", "private"],
    "status": ["draft", "verified"],
    "relation": ["self", "wife", "husband", "mother", "father", "son", "daughter",
                 "grandmother", "grandfather", "brother", "sister", "family", "other"],
}

PEOPLE_ROWS = [
    ("family", "Вся семья", "семья;все;мы;дом", "", "family", "Общие записи"),
    ("sem_smirnov", "Семён Смирнов", "Сем;Сёма;я", "1993-07-12", "self", "ПРИМЕР — замени"),
    ("anna_smirnova", "Анна Смирнова", "мама;Аня;Аннушка", "1975-06-03", "mother", "ПРИМЕР — замени"),
    ("nina_petrova", "Нина Петровна Смирнова", "бабушка Нина;бабуля;Нина Петровна", "1948-02-09", "grandmother", "ПРИМЕР — замени"),
]

RECORD_ROWS = [
    dict(id="med-0001", category="medical", person="nina_petrova",
         title="Лечение зубов бабушки Нины в клинике Дента",
         text="Нина Петровна Смирнова (бабушка, 1948 г.р.) прошла лечение зубов в клинике «Дента», "
              "Воронеж, ул. Ленина, 12, с 11.03.2024 по 25.03.2024. Стоимость 84 000 руб., оплатил Сем. "
              "Полис ДМС №4417-А действует до 01.05.2029. Следующий осмотр — сентябрь 2026.",
         event_date="2024-03-11", valid_until="2029-05-01", tags="стоматология;дмс;расходы",
         source="скан договора и чеки", file_path="archive/2024/denta_nina.pdf",
         access="private", status="verified", updated_at="2026-11-14", author="sem"),
    dict(id="fin-0001", category="finance", person="family",
         title="Ипотека Сбербанка по квартире на Мира",
         text="Ипотечный договор Сбербанка №2021-06-778 на квартиру по ул. Мира, 45, кв. 12, оформлен "
              "15.06.2021 на Анну Смирнову. Платёж 32 400 руб. до 10 числа каждого месяца, ставка 9,1%, "
              "срок до 15.06.2031. Досрочное погашение без комиссии через приложение.",
         event_date="2021-06-15", valid_until="2031-06-15", tags="ипотека;платежи;жильё",
         source="кредитный договор", file_path="archive/2021/ipoteka.pdf",
         access="private", status="verified", updated_at="2026-11-14", author="sem"),
    dict(id="story-0001", category="story", person="nina_petrova",
         title="Как бабушка Нина познакомилась с дедом Петром",
         text="Нина Петровна познакомилась с Петром Смирновым в августе 1969 года на танцах в ДК «Заря» "
              "в Воронеже. Пётр пригласил её на медленный танец, через год они поженились. "
              "Бабушка до сих пор хранит тот билетик на танцы в шкатулке.",
         event_date="1969-08-01", tags="история семьи;дедушка;бабушка",
         source="со слов бабушки Нины", access="family", status="verified",
         updated_at="2026-11-14", author="sem"),
    dict(id="instr-0001", category="instruction", person="family",
         title="Как перезапустить домашний роутер",
         text="Роутер Keenetic стоит в прихожей над электрощитком. Для перезапуска выключить питание "
              "на 10 секунд и включить обратно, загрузка около 2 минут. Сеть Wi-Fi называется "
              "SmirnovHome, пароль лежит в менеджере паролей. Если интернет не появился — "
              "звонить провайдеру Ростелеком 8-800-100-08-00.",
         tags="интернет;дом;техника", source="личный опыт",
         access="family", status="verified", updated_at="2026-11-14", author="sem"),
    dict(id="event-0001", category="event", person="anna_smirnova",
         title="День рождения мамы Ани",
         text="Анна Смирнова (мама) родилась 3 июня 1975 года. Отмечаем дома узким кругом. "
              "Любит пионы и чай улун, не любит шумные вечеринки и сюрпризы с гостями.",
         event_date="1975-06-03", tags="день рождения;подарки", source="со слов мамы",
         access="family", status="draft", updated_at="2026-11-14", author="sem",
         notes="Черновик — пример серой подсветки"),
]


class FamilyTemplate:
    def __init__(self, path: Path = OUT):
        if path.exists():
            raise SystemExit(f"{path} уже есть — переименуй, чтобы не потерять данные.")
        self.path = path
        self.wb = Workbook()
        self.wb.remove(self.wb.active)

    # ---------- helpers ----------
    def _header(self, ws, spec):
        for i, (name, width, required, tip) in enumerate(spec, 1):
            c = ws.cell(1, i, name)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = REQ if required else OPT
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.comment = Comment(("ОБЯЗАТЕЛЬНО. " if required else "") + tip, "template")
            c.comment.width, c.comment.height = 340, 110
            ws.column_dimensions[get_column_letter(i)].width = width
        ws.row_dimensions[1].height = 30
        ws.sheet_view.zoomScale = 90

    def _body(self, ws, spec, rows):
        for r, row in enumerate(rows, 2):
            for c, (name, *_ ) in enumerate(spec, 1):
                cell = ws.cell(r, c, row.get(name, "") if isinstance(row, dict) else row[c - 1])
                cell.number_format = "@"                      # всё текстом: даты не «плывут»
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        # заготовка форматирования на будущие строки
        for r in range(len(rows) + 2, min(MAX_ROW, 300) + 1):
            for c in range(1, len(spec) + 1):
                cell = ws.cell(r, c)
                cell.number_format = "@"
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    def _table(self, ws, name, ncols, nrows):
        ref = f"A1:{get_column_letter(ncols)}{max(nrows + 1, 2)}"
        t = Table(displayName=name, ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(t)

    def _dv_list(self, ws, col, named, prompt, warn=False):
        dv = DataValidation(type="list", formula1=f"={named}", allow_blank=True, showDropDown=False)
        dv.promptTitle, dv.prompt, dv.showInputMessage = "Подсказка", prompt, True
        dv.errorTitle, dv.error = "Значение не из списка", "Выбери из выпадающего списка (лист dicts)."
        dv.errorStyle = "warning" if warn else "stop"          # warning = можно ввести своё
        dv.showErrorMessage = True
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{MAX_ROW}")

    def _dv_date(self, ws, cols):
        f = ('=OR({c}2="",AND(LEN({c}2)=10,MID({c}2,5,1)="-",MID({c}2,8,1)="-",'
             'ISNUMBER(--LEFT({c}2,4))))')
        for col in cols:
            dv = DataValidation(type="custom", formula1=f.format(c=col), allow_blank=True)
            dv.errorTitle, dv.error = "Формат даты", "Нужно текстом YYYY-MM-DD, напр. 2024-03-11."
            dv.errorStyle, dv.showErrorMessage = "warning", True
            ws.add_data_validation(dv)
            dv.add(f"{col}2:{col}{MAX_ROW}")

    # ---------- sheets ----------
    def _records(self):
        ws = self.wb.create_sheet("records")
        self._header(ws, COLUMNS)
        self._body(ws, COLUMNS, RECORD_ROWS)
        self._table(ws, "tblRecords", len(COLUMNS), len(RECORD_ROWS))
        ws.freeze_panes = "D2"

        self._dv_list(ws, "B", "cat_list", "Тип записи.")
        self._dv_list(ws, "C", "person_list", "person_id из people. Несколько — через ;", warn=True)
        self._dv_list(ws, "M", "access_list", "private = не отдавать в облачные API.")
        self._dv_list(ws, "N", "status_list", "draft в индекс не попадает.")
        self._dv_date(ws, ["F", "G", "O"])

        dv = DataValidation(type="whole", operator="between", formula1=1, formula2=999, allow_blank=True)
        dv.errorStyle, dv.showErrorMessage = "warning", True
        dv.error = "Целое число 1..999"
        ws.add_data_validation(dv); dv.add(f"J2:J{MAX_ROW}")

        rng = f"A2:Q{MAX_ROW}"
        ws.conditional_formatting.add(rng, FormulaRule(
            formula=['AND($A2<>"",OR($B2="",$C2="",$D2="",$E2="",$K2="",$M2="",$N2="",$O2=""))'],
            fill=RED, stopIfTrue=True))
        ws.conditional_formatting.add(rng, FormulaRule(formula=['$N2="draft"'], fill=GREY))
        ws.conditional_formatting.add(f"A2:A{MAX_ROW}", FormulaRule(
            formula=[f'AND($A2<>"",COUNTIF($A$2:$A${MAX_ROW},$A2)>1)'],
            fill=RED, font=Font(bold=True, color="9C0006")))
        ws.conditional_formatting.add(f"M2:M{MAX_ROW}", FormulaRule(formula=['$M2="private"'], fill=ORANGE))

    def _people(self):
        ws = self.wb.create_sheet("people")
        self._header(ws, PEOPLE_COLS)
        self._body(ws, PEOPLE_COLS, PEOPLE_ROWS)
        self._table(ws, "tblPeople", len(PEOPLE_COLS), len(PEOPLE_ROWS))
        ws.freeze_panes = "B2"
        self._dv_list(ws, "E", "relation_list", "Роль в семье.")
        self._dv_date(ws, ["D"])
        ws.conditional_formatting.add(f"A2:A{MAX_ROW}", FormulaRule(
            formula=[f'AND($A2<>"",COUNTIF($A$2:$A${MAX_ROW},$A2)>1)'], fill=RED))

    def _dicts(self):
        ws = self.wb.create_sheet("dicts")
        for i, (key, values) in enumerate(DICTS.items(), 1):
            c = ws.cell(1, i, key)
            c.font = Font(bold=True, color="FFFFFF"); c.fill = OPT
            ws.column_dimensions[get_column_letter(i)].width = 18
            for r, v in enumerate(values, 2):
                ws.cell(r, i, v)
        ws.cell(1, 6, "Списки можно пополнять вниз — диапазоны динамические (OFFSET/COUNTA).")
        ws.freeze_panes = "A2"

    def _names(self):
        for name, ref in [
            ("cat_list", "dicts!$A$2:$A$500"),
            ("access_list", "dicts!$B$2:$B$500"),
            ("status_list", "dicts!$C$2:$C$500"),
            ("relation_list", "dicts!$D$2:$D$500"),
            ("person_list", "people!$A$2:$A$500"),
        ]:
            col = ref.split("$")[1]
            sheet, rng = ref.split("!")
            dyn = f"OFFSET({sheet}!${col}$2,0,0,MAX(1,COUNTA({rng})),1)"
            self.wb.defined_names.add(DefinedName(name, attr_text=dyn))

    def _readme(self):
        ws = self.wb.create_sheet("README")
        ws.column_dimensions["A"].width = 46
        ws.column_dimensions["B"].width = 60
        lines = [
            ("СЕМЕЙНАЯ БАЗА ЗНАНИЙ → векторная БД", ""),
            ("Принцип", "1 строка = 1 законченный факт. В вектор идёт только text, остальное — фильтры."),
            ("", ""),
            ("ЛИСТЫ", ""),
            ("records", "Основные данные. Заполняешь тут."),
            ("people", "Члены семьи + aliases (бабуля, мама) — для нормализации запросов."),
            ("dicts", "Списки для выпадашек. Пополняй вниз, диапазоны расширятся сами."),
            ("", ""),
            ("ПРАВИЛА", ""),
            ("text", "200-1500 символов, полные имена вместо «он/она», даты и суммы внутри текста."),
            ("Даты", "Текстом YYYY-MM-DD. Ячейки уже в текстовом формате."),
            ("Нельзя", "Объединённые ячейки, формулы в данных, цвета вместо смысла, пароли и коды 2FA."),
            ("id", "Придумал — не меняешь никогда. По нему идёт upsert без дублей."),
            ("Длинные документы", "Режь на части: общий doc_id + part_no 1,2,3..."),
            ("private", "Медицина, паспорта, финансы → только локальные эмбеддинги, без облака."),
            ("Имена листов/колонок", "Не переименовывать — Python читает по ним."),
            ("", ""),
            ("ЦВЕТА", ""),
            ("Красная шапка", "Обязательное поле."),
            ("Красная строка", "Не заполнено что-то обязательное."),
            ("Серая строка", "status=draft — в индекс не попадёт."),
            ("Красный id", "Дубликат id."),
            ("Оранжевый access", "private — чувствительные данные."),
            ("", ""),
            ("ЧЕК-ЛИСТ ПЕРЕД ЭКСПОРТОМ", ""),
            ("[ ] id уникальны", ""),
            ("[ ] обязательные поля заполнены", ""),
            ("[ ] person есть в people", ""),
            ("[ ] даты в ISO", ""),
            ("[ ] text понятен без соседних строк", ""),
            ("[ ] file_path существуют", ""),
            ("[ ] секретов нет", ""),
            ("[ ] бэкап сделан", ""),
            ("", ""),
            ("АВТОПРОВЕРКИ", ""),
            ("Всего записей", f"=COUNTA(records!A2:A{MAX_ROW})"),
            ("verified", f'=COUNTIF(records!N2:N{MAX_ROW},"verified")'),
            ("draft", f'=COUNTIF(records!N2:N{MAX_ROW},"draft")'),
            ("Строк с дублем id", f'=SUMPRODUCT((records!A2:A{MAX_ROW}<>"")*(COUNTIF(records!A2:A{MAX_ROW},records!A2:A{MAX_ROW}&"")>1))'),
            ("Строк без text", f'=SUMPRODUCT((records!A2:A{MAX_ROW}<>"")*(records!E2:E{MAX_ROW}=""))'),
            ("private-записей", f'=COUNTIF(records!M2:M{MAX_ROW},"private")'),
        ]
        for r, (a, b) in enumerate(lines, 1):
            ws.cell(r, 1, a).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(r, 2, b).alignment = Alignment(wrap_text=True, vertical="top")
            if a and not b:
                ws.cell(r, 1).font = Font(bold=True, size=12, color="1F4E79")
        ws.freeze_panes = "A2"

    def build(self) -> Path:
        self._records(); self._people(); self._dicts(); self._names(); self._readme()
        self.wb.active = 0
        self.wb.save(self.path)
        return self.path


if __name__ == "__main__":
    p = FamilyTemplate().build()
    print(f"Готово: {p.resolve()}")