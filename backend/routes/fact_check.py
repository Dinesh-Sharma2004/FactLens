import asyncio
import json
import re
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from models.llm import stream_generate_async
from services.cache import get_cache, set_cache
from services.confidence import compute_confidence_explain
from services.multilingual import translate_to_english
from services.news_fetcher import fetch_news
from services.retrieval import retrieve_docs_async

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    language: str = "en"
    mode: str = "rag"  # "rag" or "no_rag"


def _safe_send(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _extract_verdict(generated: str) -> str:
    text = generated.lower()
    if any(term in text for term in ["false", "misleading", "not true", "incorrect"]):
        return "Likely False"
    if any(term in text for term in ["partly true", "partially true", "mixed"]):
        return "Partly True"
    return "Likely True"


def _derive_fake_news_errors(query: str, docs: list, news: list[dict[str, str]]) -> list[dict[str, str]]:
    errors = []
    if not docs:
        errors.append(
            {
                "error_type": "Missing Evidence",
                "details": "The claim cannot be supported by indexed retrieval documents.",
                "correction": "Use verifiable primary sources and include dates, names, and place references.",
            }
        )
    if not news:
        errors.append(
            {
                "error_type": "No News Corroboration",
                "details": "No matching recent news coverage was found for the claim.",
                "correction": "Treat the claim as unverified until independent outlets report the same facts.",
            }
        )
    if re.search(r"\b(always|never|everyone|nobody|100%)\b", query.lower()):
        errors.append(
            {
                "error_type": "Absolute Language",
                "details": "Absolute wording often overstates the claim.",
                "correction": "Rewrite with measurable qualifiers and source-backed scope.",
            }
        )
    return errors


def _build_corrected_news(verdict: str, news: list[dict[str, str]]) -> list[dict[str, str]]:
    if not news:
        return []

    prefix = "Supporting update" if verdict == "Likely True" else "Corrective update"
    corrected = []
    for item in news[:3]:
        corrected.append(
            {
                "headline": item.get("title", "Untitled"),
                "summary": f"{prefix}: {item.get('description', 'Read full coverage in source link.')[:220]}",
                "url": item.get("url", ""),
                "published_at": item.get("published_at", ""),
                "source": item.get("source", "unknown"),
            }
        )
    return corrected


@router.post("/fact-check-stream")
async def fact_check_stream(request: QueryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    mode = request.mode if request.mode in {"rag", "no_rag"} else "rag"
    query_en = await asyncio.to_thread(translate_to_english, query, request.language)

    cache_key = f"fact:{query_en}:{mode}"
    cached = await get_cache(cache_key)

    if cached:
        async def cached_stream():
            for token in cached.get("tokens", []):
                yield _safe_send({"type": "text", "data": token})
            meta = cached.get("meta", {})
            meta["cache_hit"] = True
            yield _safe_send({"type": "meta", "data": meta})

        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    start_time = time.time()

    docs = []
    if mode == "rag":
        docs = await retrieve_docs_async(query_en)

    context = "\n\n".join([d.page_content[:1000] for d in docs])

    prompt = f"""
You are Fact Lens, a strict fact-checking assistant.

Claim: {query_en}

Use this context when available:
{context}

Return a concise analysis with:
1) Verdict
2) Why this verdict is likely
3) What is still uncertain
"""

    full_response = ""
    streamed_tokens = []

    async def event_stream():
        nonlocal full_response

        async for token in stream_generate_async(prompt):
            full_response += token
            streamed_tokens.append(token)
            yield _safe_send({"type": "text", "data": token})

        news = fetch_news(query_en)
        latency = round(time.time() - start_time, 2)
        confidence_data = compute_confidence_explain(docs=docs, query=query_en, news=news)
        verdict = _extract_verdict(full_response)

        fake_news_errors = _derive_fake_news_errors(query_en, docs, news)
        corrected_news = _build_corrected_news(verdict, news)

        meta = {
            "query": query,
            "query_en": query_en,
            "mode": mode,
            "latency": latency,
            "confidence": confidence_data["final_confidence"],
            "confidence_breakdown": confidence_data["breakdown"],
            "metrics": confidence_data["metrics"],
            "verdict": verdict,
            "fake_news_errors": fake_news_errors,
            "corrected_news": corrected_news,
            "news": news,
            "cache_hit": False,
            "generated_answer": full_response.strip(),
        }

        await set_cache(cache_key, {"tokens": streamed_tokens, "meta": meta})
        yield _safe_send({"type": "meta", "data": meta})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
