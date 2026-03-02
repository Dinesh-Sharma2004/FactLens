import os
from urllib.parse import quote_plus

import requests


def fetch_news(query: str) -> list[dict[str, str]]:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return []

    url = (
        "https://newsapi.org/v2/everything"
        f"?q={quote_plus(query)}&language=en&pageSize=5&sortBy=publishedAt&apiKey={api_key}"
    )

    try:
        res = requests.get(url, timeout=8)
        res.raise_for_status()
        payload = res.json()
    except Exception:
        return []

    articles = []
    for article in payload.get("articles", [])[:5]:
        source = article.get("source") or {}
        articles.append(
            {
                "title": article.get("title", "Untitled"),
                "description": article.get("description", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "source": source.get("name", "unknown"),
            }
        )

    return articles
