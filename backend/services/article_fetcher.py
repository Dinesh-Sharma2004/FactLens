import re
import os
from urllib.parse import urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


def extract_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return host
    except Exception:
        return ""


def _strip_html_fallback(html: str) -> str:
    text = re.sub(r"<(script|style).*?>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_article(url: str) -> dict:
    timeout_sec = float(os.getenv("ARTICLE_FETCH_TIMEOUT_SEC", "4.0"))
    try:
        res = requests.get(url, timeout=timeout_sec, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
        html = res.text
    except Exception:
        return {"url": url, "title": "", "text": "", "domain": extract_domain(url)}

    title = ""
    text = ""

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join([p for p in paragraphs if len(p) > 50]).strip()
    else:
        text = _strip_html_fallback(html)

    if not title:
        title = extract_domain(url)

    return {
        "url": url,
        "title": title[:300],
        "text": text[:6000],
        "domain": extract_domain(url),
    }
