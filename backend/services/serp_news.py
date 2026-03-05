import os
import re
import time
from urllib.parse import urlparse

from serpapi import GoogleSearch

from services.article_fetcher import extract_domain, fetch_article

STOPWORDS = {
    "www",
    "http",
    "https",
    "com",
    "org",
    "net",
    "html",
    "liveblog",
    "article",
    "story",
    "update",
}

_SERP_CACHE = {}


def _extract_keywords_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        raw = f"{parsed.netloc} {parsed.path}"
    except Exception:
        raw = url or ""

    tokens = re.findall(r"[a-zA-Z0-9]{3,}", raw.lower())
    filtered = [t for t in tokens if t not in STOPWORDS]

    unique = []
    for token in filtered:
        if token not in unique:
            unique.append(token)
    return " ".join(unique[:10])


def _google_search_cached(query: str, num: int = 10) -> list[dict]:
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key or not query:
        return []

    cache_key = f"{query}:{num}"
    cached = _SERP_CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"] < 600):
        return cached["results"]

    params = {
        "engine": "google",
        "q": query,
        "num": num,
        "api_key": api_key,
    }

    try:
        data = GoogleSearch(params).get_dict()
        results = data.get("organic_results", []) or []
    except Exception:
        results = []

    _SERP_CACHE[cache_key] = {"ts": time.time(), "results": results}
    return results


def assess_source_trust(url: str) -> dict:
    source_domain = extract_domain(url)
    keywords = _extract_keywords_from_url(url)
    results = _google_search_cached(f"{keywords} news", num=10)

    result_domains = []
    for item in results:
        link = item.get("link", "")
        domain = extract_domain(link)
        if domain:
            result_domains.append(domain)

    source_rank = None
    for idx, domain in enumerate(result_domains, start=1):
        if domain == source_domain:
            source_rank = idx
            break

    corroborating = []
    for domain in result_domains:
        if domain != source_domain and domain not in corroborating:
            corroborating.append(domain)

    corroborating_count = len(corroborating[:6])
    rank_score = 0.0
    if source_rank is not None:
        rank_score = 0.5 if source_rank <= 5 else 0.25

    trust_score = min(1.0, rank_score + (0.08 * corroborating_count))
    trusted = trust_score >= 0.45

    return {
        "source_domain": source_domain,
        "keywords": keywords,
        "trusted": trusted,
        "trust_score": round(trust_score, 2),
        "source_rank": source_rank,
        "corroborating_domains": corroborating_count,
    }


def search_related_news_from_url(url: str, max_results: int = 3) -> list[dict]:
    keywords = _extract_keywords_from_url(url)
    results = _google_search_cached(f"{keywords} latest news", num=10)
    return _build_article_results(results, max_results=max_results)


def search_related_news_from_query(query: str, max_results: int = 5) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    # OPTIMIZED: Shorter search query for faster SERP response
    search_query = f"{query[:80]} news"  # Further limit query
    results = _google_search_cached(search_query, num=5)  # OPTIMIZED: Fetch only 5, not 10
    return _build_article_results(results, max_results=max_results)


def _build_article_results(results: list[dict], max_results: int) -> list[dict]:
    """Build article results from SERP. OPTIMIZED: Use snippets only, skip full article fetch."""
    output = []
    seen = set()
    for item in results:
        link = item.get("link", "")
        if not link or link in seen:
            continue
        seen.add(link)

        # OPTIMIZATION: Use snippet from SERP result directly, don't fetch full article
        output.append(
            {
                "title": item.get("title", "Untitled"),
                "description": item.get("snippet", ""),
                "url": link,
                "published_at": item.get("date", ""),
                "source": extract_domain(link),
                # Skip article_text field - it's not needed for verification
                "article_text": "",  # Empty, but field exists for compatibility
            }
        )
        if len(output) >= max_results:
            break

    return output
