import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
import os

# 🔐 Use environment variable (IMPORTANT)
API_KEY = os.getenv("NEWS_API_KEY")


# 📰 1. NEWS API LOADER
def load_news(query="finance OR stock OR economy"):
    url = "https://newsapi.org/v2/everything"

    params = {
        "q": query,
        "language": "en",
        "pageSize": 20,
        "apiKey": API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except Exception as e:
        print("❌ News API error:", e)
        return []

    docs = []

    for article in data.get("articles", []):
        title = article.get("title", "")
        desc = article.get("description", "")
        content = article.get("content", "")

        # Skip empty
        if not title:
            continue

        full_text = f"{title}\n{desc}\n{content}"

        docs.append(Document(
            page_content=full_text,
            metadata={
                "source": article.get("source", {}).get("name"),
                "url": article.get("url"),
                "published": article.get("publishedAt")
            }
        ))

    print(f"✅ Loaded {len(docs)} news articles")
    return docs


# 🌐 2. ET SCRAPER (IMPROVED)
def scrape_et_news():
    url = "https://economictimes.indiatimes.com/markets"

    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print("❌ ET scrape error:", e)
        return []

    docs = []

    # Better selectors (headlines)
    for item in soup.select("h2 a, h3 a"):
        text = item.get_text(strip=True)
        link = item.get("href")

        if len(text) > 40:
            docs.append(Document(
                page_content=text,
                metadata={
                    "source": "Economic Times",
                    "url": f"https://economictimes.indiatimes.com{link}" if link else None
                }
            ))

    print(f"✅ Scraped {len(docs)} ET articles")
    return docs


# 🔥 3. COMBINED LOADER (BEST PRACTICE)
def load_all_data():
    news_docs = load_news()
    et_docs = scrape_et_news()

    all_docs = news_docs + et_docs

    print(f"🚀 Total documents: {len(all_docs)}")
    return all_docs

