import json
import time
from datetime import datetime, timedelta

import feedparser
import requests


class FinamRSSParser:
    # Рабочие ссылки на RSS каналы ФИНАМ [[34]]
    RSS_URLS = {
        "companies": "https://www.finam.ru/analysis/conews/rsspoint/",  # Новости компаний
        "bonds": "https://bonds.finam.ru/news/today/rss.asp",  # Новости облигаций
        "markets": "https://www.finam.ru/analysis/markets/rsspoint/",  # Новости рынков (может потребовать проверки)
    }

    def __init__(self, channel: str = "companies"):
        """
        Инициализация парсера.
        :param channel: Ключ канала из RSS_URLS ('companies', 'bonds', 'markets')
        """
        self.rss_url = self.RSS_URLS.get(channel, self.RSS_URLS["companies"])
        self.session = requests.Session()

        # Настройка заголовков для имитации реального браузера (обход 403)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.finam.ru/",
                "Connection": "keep-alive",
            }
        )

    def fetch_feed(self, retries: int = 3) -> feedparser.FeedParserDict | None:
        """Получение и парсинг RSS ленты с повторными попытками."""
        for attempt in range(retries):
            try:
                print(f"Загрузка ленты: {self.rss_url} (попытка {attempt + 1})...")
                response = self.session.get(self.rss_url, timeout=15)

                # Явная проверка на успешный статус
                if response.status_code == 403:
                    print("⚠️ Доступ запрещен (403). Проверьте заголовки или IP.")
                    return None
                elif response.status_code != 200:
                    print(f"⚠️ Ошибка HTTP {response.status_code}")
                    return None

                # Принудительная кодировка, если она не определилась автоматически
                if response.encoding == "ISO-8859-1":
                    response.encoding = "utf-8"

                return feedparser.parse(response.content)

            except requests.RequestException as e:
                print(f"Ошибка сети: {e}")
                time.sleep(2)  # Пауза перед повторной попыткой

        return None

    def parse_entries(
        self, feed: feedparser.FeedParserDict, limit: int = 10, keywords: list[str] | None = None, hours_back: int = 24
    ) -> list[dict]:
        """Фильтрация и форматирование новостей."""
        news_list = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        for entry in feed.entries[:limit]:
            try:
                # Обработка даты публикации
                published = entry.get("published_parsed")
                if not published:
                    continue
                pub_datetime = datetime(*published[:6])

                # Фильтр по времени
                if pub_datetime < cutoff_time:
                    continue

                title = entry.get("title", "Без заголовка")

                # Фильтр по ключевым словам
                if keywords and not any(kw.lower() in title.lower() for kw in keywords):
                    continue

                # Очистка описания от HTML-тегов (простая версия)
                import re

                summary = entry.get("summary", "")
                clean_summary = re.sub(r"<[^>]+>", "", summary)

                news_item = {
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": pub_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": clean_summary.strip()[:300],  # Обрезаем длинное описание
                    "source": "ФИНАМ",
                }
                news_list.append(news_item)

            except Exception as e:
                print(f"Ошибка при разборе записи: {e}")
                continue

        return news_list

    def save_to_json(self, data: list[dict], filename: str = "finam_news.json"):
        """Сохранение результата в файл."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Данные сохранены в {filename}")
        except OSError as e:
            print(f"❌ Ошибка записи файла: {e}")

    def print_news(self, news_list: list[dict]):
        """Красивый вывод новостей в консоль."""
        if not news_list:
            print("📭 Новостей не найдено.")
            return

        print(f"\n📰 Найдено новостей: {len(news_list)}")
        print("=" * 70)
        for i, news in enumerate(news_list, 1):
            print(f"{i}. [{news['published']}] {news['title']}")
            print(f"   🔗 {news['link']}")
            print(f"   📝 {news['summary']}")
            print("-" * 70)


def main():
    # Выбираем канал: 'companies' (новости компаний), 'bonds' (облигации)
    parser = FinamRSSParser(channel="companies")

    feed = parser.fetch_feed()

    if feed and feed.entries:
        print(f"✅ Лента загружена. Всего записей в фиде: {len(feed.entries)}")

        # Получаем новости: лимит 10, за последние 48 часов, с ключевыми словами
        news = parser.parse_entries(
            feed,
            limit=99,
            hours_back=100,
            keywords=[],  # Можно добавить: ['акции', 'дивиденды', 'отчет']
        )

        parser.print_news(news)
        parser.save_to_json(news)
    else:
        print("❌ Не удалось загрузить ленту новостей.")


if __name__ == "__main__":
    main()
