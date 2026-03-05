import os
import time
from urllib.parse import quote_plus

import requests

_NEWS_CACHE = {}


def _normalize_news_query(query: str) -> str:
    import re

    q = (query or "").lower().strip()
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    q = re.sub(r"\s+", " ", q)
    return q[:120]


def fetch_news(query: str) -> list[dict[str, str]]:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return []

    normalized_query = _normalize_news_query(query)
    if not normalized_query:
        return []

    cache_key = normalized_query
    cached = _NEWS_CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"] < 300):
        return cached["data"]

    url = (
        "https://newsapi.org/v2/everything"
        f"?q={quote_plus(normalized_query)}"
        f"&searchIn=title,description"
        f"&language=en&pageSize=10&sortBy=relevancy&apiKey={api_key}"
    )

    try:
        res = requests.get(url, timeout=8)
        res.raise_for_status()
        payload = res.json()
    except Exception:
        return []

    query_tokens = {t for t in normalized_query.split() if len(t) > 2}
    articles = []
    for article in payload.get("articles", []):
        source = article.get("source") or {}
        article_url = article.get("url", "")
        title = article.get("title", "Untitled")
        description = article.get("description", "")
        haystack = f"{title} {description}".lower()
        overlap = sum(1 for t in query_tokens if t in haystack)
        if query_tokens and overlap == 0:
            continue

        articles.append(
            {
                "title": title,
                "description": description,
                "url": article_url,
                "published_at": article.get("publishedAt", ""),
                "source": source.get("name", "unknown"),
            }
        )
        if len(articles) >= 5:
            break

    _NEWS_CACHE[cache_key] = {"ts": time.time(), "data": articles}
    return articles
