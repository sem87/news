from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup


# URL = "https://www.rbc.ru/quote/"
# URL = "https://www.rbc.ru/rubric/finances?utm_source=topline"
URL = "https://www.rbc.ru/tags/?tag=%D1%84%D0%B8%D0%BD%D0%B0%D0%BD%D1%81%D0%BE%D0%B2%D1%8B%D0%B9%20%D1%80%D1%8B%D0%BD%D0%BE%D0%BA"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def clean_text(text):
    """Очистка текста от лишних символов"""
    if not text:
        return None
    # Удаляем лишние пробелы и символы
    text = re.sub(r"\s+·\s*\d+", "", text)  # Удаляем "·0"
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def extract_time(text):
    """Извлечение времени из текста (формат ЧЧ:ММ)"""
    if not text:
        return None
    match = re.search(r"(\d{2}:\d{2})", text)
    return match.group(1) if match else None


def parse_rbc_quote_html():
    """Парсинг HTML-страницы РБК Инвестиции"""
    all_news = []

    try:
        response = httpx.get(URL.strip(), headers=HEADERS, timeout=10.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем все ссылки на новости
        news_links = soup.find_all("a", href=lambda x: x and "/quote/news/article/" in x)
        print(f"🔍 Найдено ссылок на новости: {len(news_links)}")

        seen_links = set()

        for link_tag in news_links[:20]:
            # Получаем полный текст
            full_text = link_tag.get_text(strip=True)

            # Извлекаем время из текста
            time_text = extract_time(full_text)

            # Очищаем заголовок от времени и лишних символов
            title = clean_text(full_text)

            # Пропускаем если заголовок слишком короткий или пустой
            if not title or len(title) < 10:
                continue

            # Убираем время из заголовка если оно там осталось
            if time_text:
                title = title.replace(time_text, "").strip()
                title = re.sub(r"\s+", " ", title).strip()

            href = link_tag.get("href", "")

            # Пропускаем дубликаты
            if href in seen_links:
                continue
            seen_links.add(href)

            # Относительные ссылки превращаем в абсолютные
            if href.startswith("/"):
                href = "https://www.rbc.ru" + href

            # Ищем категорию в родительском элементе
            parent = link_tag.find_parent(["div", "article", "section"])
            category = None

            if parent:
                cat_tag = parent.find("a", href=lambda x: x and "/quote/category/" in x)
                if cat_tag:
                    category = cat_tag.get_text(strip=True)

            all_news.append(
                {
                    "title": title[:150],  # Обрезаем длинные заголовки
                    "link": href,
                    "published": time_text,
                    "category": category,
                    "source": "RBC Quote HTML",
                }
            )

        return all_news

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP ошибка: {e.response.status_code}")
        return []
    except httpx.ConnectError as e:
        print(f"❌ Ошибка подключения: {e}")
        return []
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("📰 Парсер РБК Инвестиции (HTML)")
    print("=" * 60)

    news = parse_rbc_quote_html()

    print(f"\n📊 Найдено новостей: {len(news)}\n")

    for i, item in enumerate(news[:10], 1):
        print(f"{i}. {item['title']}")
        print(f"   🔗 {item['link'][:60]}...")
        print(f"   ⏰ {item['published']}")
        if item["category"]:
            print(f"   📁 {item['category']}")
        print()
