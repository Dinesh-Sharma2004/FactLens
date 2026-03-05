import asyncio
import json
import logging
import re
import time
import uuid
from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from models.llm import generate_text_async
from services.cache import get_cache, set_cache
from services.confidence import compute_confidence_explain
from services.multilingual import translate_to_english
from services.article_fetcher import extract_domain, fetch_article
from services.rag_cache import get_rag
from services.reference_manager import create_request_reference_manager
from services.serp_news import search_related_news_from_url

router = APIRouter()
logger = logging.getLogger(__name__)

_SUMMARY_STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "are", "was", "were",
    "has", "have", "had", "will", "would", "can", "could", "should", "about",
    "into", "after", "before", "over", "under", "between", "during", "said",
    "says", "say", "their", "there", "they", "them", "than", "then", "also",
    "because", "while", "where", "when", "which", "who", "whom", "whose",
    "what", "how", "why", "you", "your", "our", "its", "his", "her",
}


class QueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    language: str = "en"
    mode: str = "verify"  # "verify" or "summarize"


def _safe_send(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _normalize_query(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:220]


def _extract_url(text: str) -> str:
    match = re.search(r"https?://\S+", text or "")
    return match.group(0).rstrip(".,);") if match else ""


def _compress_text(text: str, limit_chars: int = 900) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""

    # Remove noisy boilerplate phrases that add tokens but little signal.
    text = re.sub(
        r"(subscribe now|read more|click here|all rights reserved|cookies policy)",
        " ",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit_chars]


def _build_compact_context(docs: list, per_doc_limit: int = 260, max_docs: int = 3) -> str:
    compact_chunks = []
    for doc in docs[:max_docs]:
        compact = _compress_text(getattr(doc, "page_content", ""), per_doc_limit)
        if compact:
            compact_chunks.append(f"- {compact}")
    return "\n".join(compact_chunks)


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9]{3,}", text.lower())}


def _source_alignment(query: str, news: list[dict[str, str]]) -> dict[str, float]:
    query_tokens = _tokenize(query)
    if not query_tokens or not news:
        return {
            "support_ratio": 0.0,
            "contradiction_ratio": 0.0,
            "evidence_signal": 0.0,
        }

    negation_terms = {"fake", "hoax", "false", "deny", "denied", "debunked"}
    support_hits = 0
    contradiction_hits = 0

    for item in news:
        title_tokens = _tokenize(item.get("title", ""))
        overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
        if overlap >= 0.2:
            support_hits += 1
        if title_tokens & negation_terms:
            contradiction_hits += 1

    total = len(news)
    support_ratio = round(support_hits / total, 2)
    contradiction_ratio = round(contradiction_hits / total, 2)
    evidence_signal = round(max(0.0, support_ratio - (0.5 * contradiction_ratio)), 2)

    return {
        "support_ratio": support_ratio,
        "contradiction_ratio": contradiction_ratio,
        "evidence_signal": evidence_signal,
    }


def _extract_verdict(generated: str) -> str:
    text = generated.lower()
    if any(term in text for term in ["false", "misleading", "not true", "incorrect"]):
        return "Likely False"
    if any(term in text for term in ["partly true", "partially true", "mixed"]):
        return "Partly True"
    return "Likely True"


def _decide_verdict(generated: str, evidence_signal: float, contradiction_ratio: float, docs: list, news: list) -> str:
    # Be conservative: avoid "Likely False" unless multiple sources corroborate contradiction.
    if contradiction_ratio >= 0.6 and len(news) >= 2:
        return "Likely False"
    if evidence_signal < 0.2 and (not docs or len(news) <= 1):
        return "Unverified"

    llm_guess = _extract_verdict(generated)
    if llm_guess == "Likely False" and (len(news) < 2 or evidence_signal < 0.25):
        return "Unverified"
    if llm_guess == "Likely True" and evidence_signal < 0.3:
        return "Partly True"
    return llm_guess


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
    if not re.search(r"\b(19|20)\d{2}\b", query):
        errors.append(
            {
                "error_type": "Missing Time Context",
                "details": "The claim has no clear date/time anchor, which weakens verification quality.",
                "correction": "Add an exact date or date range to make evidence matching reliable.",
            }
        )
    return errors


def _build_corrected_news(verdict: str, news: list[dict[str, str]]) -> list[dict[str, str]]:
    if not news:
        return []

    prefix = "Supporting update" if verdict in {"Likely True", "Exists in corroborating sources"} else "Corrective update"
    corrected = []
    for item in news[:3]:
        compact_description = _compress_text(item.get("description", ""), 140)
        corrected.append(
            {
                "headline": item.get("title", "Untitled"),
                "summary": f"{prefix}: {compact_description or 'Read full coverage in source link.'}",
                "url": item.get("url", ""),
                "published_at": item.get("published_at", ""),
                "source": item.get("source", "unknown"),
            }
        )
    return corrected


def _dedupe_news(items: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for item in items:
        url = item.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        output.append(item)
    return output


def _parse_summary_struct(text: str) -> dict:
    # Try JSON first for deterministic structure.
    json_match = re.search(r"\{[\s\S]*\}", text or "")
    if json_match:
        try:
            obj = json.loads(json_match.group(0))
            return {
                "summary": str(obj.get("summary", "")).strip(),
                "key_event": str(obj.get("key_event", "")).strip(),
                "timeline": str(obj.get("timeline", "")).strip(),
            }
        except Exception:
            pass

    # Fallback: simple label extraction
    def pick(label: str) -> str:
        m = re.search(rf"{label}\s*:\s*(.+)", text or "", flags=re.I)
        return m.group(1).strip() if m else ""

    return {
        "summary": pick("summary"),
        "key_event": pick("key event"),
        "timeline": pick("timeline"),
    }


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.strip()) >= 40]


def _extract_keywords(text: str, max_terms: int = 16) -> set[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", (text or "").lower())
    filtered = [t for t in tokens if t not in _SUMMARY_STOPWORDS and not t.isdigit()]
    counts = Counter(filtered)
    return {term for term, _ in counts.most_common(max_terms)}


def _sentence_similarity(a: str, b: str) -> float:
    a_tokens = _tokenize(a)
    b_tokens = _tokenize(b)
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)


def _extract_focus_keywords_from_url(url: str, max_terms: int = 10) -> set[str]:
    if not url:
        return set()
    parts = re.findall(r"[a-zA-Z]{4,}", url.lower())
    stop = {"https", "http", "www", "news", "world", "india", "report", "claiming", "using", "ports"}
    cleaned = [p for p in parts if p not in stop]
    return set(cleaned[:max_terms])


def _build_summary_source(
    title: str,
    article_text: str,
    max_chars: int = 1400,
    focus_keywords: set[str] | None = None,
) -> str:
    title = _compress_text(title or "", 180)
    text = _compress_text(article_text or "", 12000)
    if len(text) < 120:
        return ""
    sentences = _split_sentences(text)
    if not sentences:
        return f"Title: {title}\nKey Sentences:\n{text[:max_chars]}"

    keyword_set = _extract_keywords(f"{title} {text}")
    scored: list[tuple[float, str]] = []
    total = len(sentences)

    for idx, sent in enumerate(sentences):
        lower = sent.lower()
        sent_tokens = _tokenize(sent)
        overlap = len(sent_tokens & keyword_set) / max(len(keyword_set), 1)
        focus_overlap = 0.0
        if focus_keywords:
            focus_overlap = len(sent_tokens & focus_keywords) / max(len(focus_keywords), 1)
        pos_score = 0.0
        if idx <= 2:
            pos_score += 0.25
        if idx >= max(0, total - 3):
            pos_score += 0.1
        factual_signal = 0.0
        if re.search(r"\b(19|20)\d{2}\b", sent):
            factual_signal += 0.2
        if re.search(r"\b\d+(?:\.\d+)?%?\b", sent):
            factual_signal += 0.15
        if any(k in lower for k in ["according to", "reported", "announced", "confirmed", "official"]):
            factual_signal += 0.2
        if any(k in lower for k in ["but", "however", "meanwhile", "although"]):
            factual_signal += 0.05

        length_penalty = 0.0 if len(sent) <= 260 else 0.1
        score = (1.6 * overlap) + (2.2 * focus_overlap) + pos_score + factual_signal - length_penalty
        scored.append((score, sent))

    ranked = [s for _, s in sorted(scored, key=lambda x: x[0], reverse=True)]
    if focus_keywords:
        focused_ranked = [s for s in ranked if len(_tokenize(s) & focus_keywords) > 0]
        if focused_ranked:
            ranked = focused_ranked
    selected: list[str] = []
    for sent in ranked:
        if any(_sentence_similarity(sent, kept) >= 0.72 for kept in selected):
            continue
        selected.append(sent)
        if len(selected) >= 9:
            break

    # Preserve article flow for readability after ranking
    order_map = {s: i for i, s in enumerate(sentences)}
    selected.sort(key=lambda s: order_map.get(s, 10_000))

    packed = ""
    for sent in selected:
        candidate = f"{packed} {sent}".strip()
        if len(candidate) > max_chars:
            break
        packed = candidate

    packed = packed or text[:max_chars]
    return f"Title: {title}\nKey Sentences:\n{packed}"


def _build_summary_prompt(summary_source: str) -> str:
    return f"""You are a precise news summarizer.
Use only the provided context. If a date is unclear, say "date not specified".

Context:
{summary_source}

Return strict JSON:
{{"summary":"3-4 concise factual sentences","key_event":"one-sentence core event","timeline":"primary date/time context"}}"""


def _build_fallback_summary_source_from_url(url: str, focus_keywords: set[str] | None = None, max_results: int = 4) -> str:
    snippets = search_related_news_from_url(url, max_results=max_results)
    if not snippets:
        return ""
    filtered = []
    for item in snippets:
        text = f"{item.get('title', '')} {item.get('description', '')}".strip()
        if not text:
            continue
        if focus_keywords:
            overlap = len(_tokenize(text) & focus_keywords)
            if overlap == 0:
                continue
        filtered.append(item)
    if filtered:
        snippets = filtered
    joined = " ".join(
        f"{item.get('title', '')}. {item.get('description', '')}".strip()
        for item in snippets
    )
    return _build_summary_source("Related coverage", joined, max_chars=1200, focus_keywords=focus_keywords)


def _is_valid_summary_struct(summary_struct: dict) -> bool:
    if not summary_struct:
        return False
    summary = (summary_struct.get("summary") or "").strip().lower()
    key_event = (summary_struct.get("key_event") or "").strip().lower()
    if len(summary) < 30 or len(key_event) < 12:
        return False
    bad_markers = {"n/a", "none", "not available", "please provide", "no context"}
    return not any(marker in summary or marker in key_event for marker in bad_markers)


def _fallback_summary_struct_from_context(summary_source: str) -> dict:
    context = (summary_source or "").split("Key Sentences:\n", 1)
    text = context[1] if len(context) > 1 else summary_source
    sentences = _split_sentences(text)
    if not sentences:
        return {"summary": "", "key_event": "", "timeline": "date not specified"}
    chosen = sentences[:4]
    summary = " ".join(chosen[:3]).strip()
    key_event = chosen[0].strip()
    timeline_match = re.search(
        r"\b(?:\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s*\d{4}|(19|20)\d{2})\b",
        text,
    )
    timeline = timeline_match.group(0) if timeline_match else "date not specified"
    return {
        "summary": summary[:700],
        "key_event": key_event[:240],
        "timeline": timeline,
    }


async def _collect_llm_output(prompt: str) -> tuple[str, list[str], str]:
    text, provider = await generate_text_async(prompt)
    tokens = [(word + " ") for word in text.split()]
    return text.strip(), tokens, provider


async def _run_fact_check(request: QueryRequest):
    request_id = uuid.uuid4().hex[:10]
    req_start = time.perf_counter()
    timing: dict[str, float] = {}

    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    mode_alias = {"rag": "summarize", "no_rag": "verify"}
    mode_raw = request.mode.strip().lower()
    mode = mode_alias.get(mode_raw, mode_raw)
    if mode not in {"summarize", "verify"}:
        mode = "verify"

    t = time.perf_counter()
    # Skip translation for English, only translate if needed
    if request.language.lower() != "en":
        query_en = await asyncio.to_thread(translate_to_english, query, request.language)
    else:
        query_en = query
    timing["translation_ms"] = _elapsed_ms(t)

    url_in_query = _extract_url(query_en)
    if mode == "summarize" and url_in_query:
        query_norm = url_in_query.lower()[:220]
    else:
        query_norm = _normalize_query(query_en)

    cache_key = f"fact:{query_norm}:{mode}"
    t = time.perf_counter()
    cached = await get_cache(cache_key)
    timing["cache_read_ms"] = _elapsed_ms(t)

    if cached:
        timing["total_ms"] = _elapsed_ms(req_start)
        logger.info(
            "fact_check request_id=%s mode=%s cache_hit=true timings=%s",
            request_id,
            mode,
            timing,
        )
        return {
            "tokens": cached.get("tokens", []),
            "meta": {
                **cached.get("meta", {}),
                "cache_hit": True,
                "request_id": request_id,
                "timing_breakdown": timing,
            },
        }

    start_time = time.time()

    docs = []

    context = _build_compact_context(docs)
    article_context = ""
    article_title = ""
    summarize_error = ""
    source_check = {"original_domain": "", "mode": mode}
    
    # Initialize variables for both modes
    ref_manager = None
    evidence_source = None
    cache_stats = {}
    
    if mode == "summarize" and url_in_query:
        focus_keywords = _extract_focus_keywords_from_url(url_in_query)
        t = time.perf_counter()
        article = await asyncio.to_thread(fetch_article, url_in_query)
        timing["article_fetch_ms"] = _elapsed_ms(t)
        article_title = article.get("title", "")
        source_check = {
            "original_domain": article.get("domain", ""),
            "mode": mode,
            "trusted": True,
            "trust_score": 1.0,
            "corroborating_domains": 0,
        }
        article_context = _build_summary_source(
            article.get("title", ""),
            article.get("text", ""),
            focus_keywords=focus_keywords,
        )
        if not article_context:
            t = time.perf_counter()
            article_context = await asyncio.to_thread(
                _build_fallback_summary_source_from_url,
                url_in_query,
                focus_keywords,
            )
            timing["summary_fallback_ms"] = _elapsed_ms(t)
        if not article_context:
            summarize_error = "Unable to extract article text from URL."
    elif mode == "summarize":
        summarize_error = "Please paste a news URL in summarize mode."

    full_response = ""
    streamed_tokens = []

    if mode == "summarize":
        summary_source = article_context
        summary_prompt = _build_summary_prompt(summary_source)
        t = time.perf_counter()
        summary_text, summary_tokens, provider_1 = await _collect_llm_output(summary_prompt)
        timing["llm_generation_ms"] = _elapsed_ms(t)
        summary_struct = _parse_summary_struct(summary_text)
        if not _is_valid_summary_struct(summary_struct):
            summary_struct = _fallback_summary_struct_from_context(summary_source)
        summary_render = (
            f"Summary: {summary_struct.get('summary','')}\n"
            f"Key Event: {summary_struct.get('key_event','')}\n"
            f"Timeline: {summary_struct.get('timeline','')}"
        ).strip()
        full_response = summary_render or summary_text.strip()
        streamed_tokens = summary_tokens
        llm_provider = provider_1
        news_query = url_in_query
        news = [
            {
                "title": article_title or "Source article",
                "description": "Original submitted URL used for summarization.",
                "url": url_in_query,
                "published_at": "",
                "source": extract_domain(url_in_query),
            }
        ] if url_in_query else []
        news_exists = bool(news)
    else:
        # VERIFY MODE: Use cached+corrective RAG
        summary_struct = None
        
        # Get RAG instance and reference manager for this request
        rag = get_rag()
        ref_manager = create_request_reference_manager()
        
        # OPTIMIZATION: Retrieve only top 2 results for faster processing
        t = time.perf_counter()
        rag_result = await rag.retrieve_evidence(query_en, max_results=2)
        timing["evidence_retrieval_ms"] = _elapsed_ms(t)
        news = rag_result["evidence"]
        news_exists = len(news) > 0
        evidence_source = rag_result["source"]  # "cache" or "search"
        cache_stats = rag_result.get("cache_stats", {})
        
        # Track references for this request
        for news_item in news:
            ref_id = news_item.get("ref_id")
            if not ref_id:
                ref_id = ref_manager.add_reference(
                    title=news_item.get("title", ""),
                    url=news_item.get("url", ""),
                    source=news_item.get("source", ""),
                    accessed_from=evidence_source
                )
                news_item["ref_id"] = ref_id

        # OPTIMIZATION: Minimal evidence blocks for speed
        evidence_blocks = []
        for i, item in enumerate(news[:2]):
            ref_id = item.get("ref_id", f"REF_{i+1:03d}")
            title = (item.get('title', '') or '')[:60]
            snippet = (item.get('description', '') or '')[:300]
            evidence_blocks.append(f"[{ref_id}] {title}: {snippet}")
        
        evidence_text = "\n".join(evidence_blocks) if evidence_blocks else "No sources found."

        # ULTRA-OPTIMIZED: Minimal prompt for maximum speed
        prompt = f"""Verify claim: {query_en[:120]}
Evidence: {evidence_text[:800]}
Verdict (Likely True/Partly True/Likely False/Unverified):"""
        
        if not news:
            verify_text = (
                "Verdict: Unverified. No relevant corroborating sources were found quickly. "
                "Try adding date, location, and names for better evidence matching."
            )
            verify_tokens = [(word + " ") for word in verify_text.split()]
            llm_provider = "rule"
        else:
            t = time.perf_counter()
            verify_text, verify_tokens, llm_provider = await _collect_llm_output(prompt)
            timing["llm_generation_ms"] = _elapsed_ms(t)
        full_response = verify_text
        streamed_tokens = verify_tokens
        news_query = query_norm

    source_alignment = _source_alignment(query_norm, news)
    latency = round(time.time() - start_time, 2)
    
    # OPTIMIZATION: Lightweight confidence for verify mode
    if mode == "verify":
        # Fast confidence for verify mode
        confidence_data = {
            "final_confidence": min(1.0, 0.5 + (0.1 * len(news))),
            "breakdown": {"evidence_count": len(news)},
            "metrics": {"news_sources": len(news), "evidence_signal": source_alignment["evidence_signal"]}
        }
    else:
        # Full confidence computation for summarize
        confidence_data = compute_confidence_explain(
            docs=docs,
            query=query_norm,
            news=news,
            evidence_signal=source_alignment["evidence_signal"],
        )
    
    if mode == "summarize":
        verdict = "Summary Completed"
        fake_news_errors = []
    else:
        verdict = _decide_verdict(
            generated=full_response,
            evidence_signal=source_alignment["evidence_signal"],
            contradiction_ratio=source_alignment["contradiction_ratio"],
            docs=docs,
            news=news,
        )
        # OPTIMIZATION: Skip fake_news_errors for verify mode (not critical for speed)
        fake_news_errors = []

    # OPTIMIZATION: Skip corrected_news for speed
    corrected_news = []

    metrics = {
        **confidence_data["metrics"],
        "support_ratio": source_alignment["support_ratio"],
        "contradiction_ratio": source_alignment["contradiction_ratio"],
    }

    # Build references section
    references_section = ""
    references_data = []
    if mode == "verify" and ref_manager:
        references_data = ref_manager.get_all_references()
        references_section = ref_manager.format_references(style="harvard")
    
    meta = {
        "query": query,
        "query_en": query_en,
        "mode": mode,
        "latency": latency,
        "confidence": confidence_data["final_confidence"],
        "confidence_breakdown": confidence_data["breakdown"],
        "metrics": metrics,
        "verdict": verdict,
        "fake_news_errors": fake_news_errors,
        "corrected_news": corrected_news,
        "news": news,
        "cache_hit": False,
        "generated_answer": full_response.strip(),
        "summarize_error": summarize_error,
        "llm_provider": llm_provider,
        "news_existence": {
            "exists": news_exists,
            "match_count": len(news),
            "checked_query": news_query,
        },
        "source_trust_check": source_check,
        "summary_struct": summary_struct,
        # NEW: References and cache info
        "references": references_data,
        "references_formatted": references_section,
        "evidence_source": evidence_source if mode == "verify" else None,
        "cache_stats": cache_stats if mode == "verify" else None,
    }

    t = time.perf_counter()
    await set_cache(cache_key, {"tokens": streamed_tokens, "meta": meta})
    timing["cache_write_ms"] = _elapsed_ms(t)
    timing["total_ms"] = _elapsed_ms(req_start)
    meta["timing_breakdown"] = timing
    meta["request_id"] = request_id
    logger.info(
        "fact_check request_id=%s mode=%s cache_hit=false evidence_source=%s timings=%s",
        request_id,
        mode,
        evidence_source,
        timing,
    )
    return {"tokens": streamed_tokens, "meta": meta}


@router.post("/fact-check")
async def fact_check(request: QueryRequest):
    result = await _run_fact_check(request)
    return {
        "response": "".join(result["tokens"]).strip(),
        "meta": result["meta"],
    }


@router.post("/fact-check-stream")
async def fact_check_stream(request: QueryRequest):
    """Stream fact-check results with real-time LLM token generation (ChatGPT-style)"""
    request_id = uuid.uuid4().hex[:10]
    req_start = time.perf_counter()

    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    mode_alias = {"rag": "summarize", "no_rag": "verify"}
    mode_raw = request.mode.strip().lower()
    mode = mode_alias.get(mode_raw, mode_raw)
    if mode not in {"summarize", "verify"}:
        mode = "verify"

    # Skip translation for English
    if request.language.lower() != "en":
        query_en = await asyncio.to_thread(translate_to_english, query, request.language)
    else:
        query_en = query

    url_in_query = _extract_url(query_en)
    if mode == "summarize" and url_in_query:
        query_norm = url_in_query.lower()[:220]
    else:
        query_norm = _normalize_query(query_en)

    cache_key = f"fact:{query_norm}:{mode}"

    start_time = time.time()

    async def stream():
        timing: dict[str, float] = {}
        # Send start signal
        yield _safe_send({"type": "start", "data": "Generating verdict..."})
        yield _safe_send({"type": "status", "data": "Checking cache..."})

        t = time.perf_counter()
        cached = await get_cache(cache_key)
        timing["cache_read_ms"] = _elapsed_ms(t)
        if cached:
            timing["total_ms"] = _elapsed_ms(req_start)
            for token in cached.get("tokens", []):
                yield _safe_send({"type": "text", "data": token})
            logger.info(
                "fact_check_stream request_id=%s mode=%s cache_hit=true timings=%s",
                request_id,
                mode,
                timing,
            )
            yield _safe_send({
                "type": "meta",
                "data": {
                    **cached.get("meta", {}),
                    "cache_hit": True,
                    "request_id": request_id,
                    "timing_breakdown": timing,
                },
            })
            return

        from models.llm import stream_generate_async
        ref_manager = create_request_reference_manager()
        streamed_tokens = []
        news = []
        evidence_source = None
        summarize_error = ""

        if mode == "summarize":
            article_context = ""
            article_title = ""
            if url_in_query:
                focus_keywords = _extract_focus_keywords_from_url(url_in_query)
                t = time.perf_counter()
                article = await asyncio.to_thread(fetch_article, url_in_query)
                timing["article_fetch_ms"] = _elapsed_ms(t)
                article_title = article.get("title", "")
                article_context = _build_summary_source(
                    article.get("title", ""),
                    article.get("text", ""),
                    focus_keywords=focus_keywords,
                )
                if not article_context:
                    t = time.perf_counter()
                    article_context = await asyncio.to_thread(
                        _build_fallback_summary_source_from_url,
                        url_in_query,
                        focus_keywords,
                    )
                    timing["summary_fallback_ms"] = _elapsed_ms(t)
                if not article_context:
                    summarize_error = "Unable to extract article text from URL."
            else:
                summarize_error = "Please paste a news URL in summarize mode."

            if summarize_error:
                streamed_tokens = [summarize_error]
                yield _safe_send({"type": "text", "data": summarize_error})
            else:
                t = time.perf_counter()
                summary_prompt = _build_summary_prompt(article_context)
                async for token in stream_generate_async(summary_prompt):
                    streamed_tokens.append(token)
                    yield _safe_send({"type": "text", "data": token})
                timing["llm_generation_ms"] = _elapsed_ms(t)

            generated_text = "".join(streamed_tokens).strip()
            summary_struct = _parse_summary_struct(generated_text) if generated_text else {
                "summary": "",
                "key_event": "",
                "timeline": "",
            }
            if not _is_valid_summary_struct(summary_struct):
                summary_struct = _fallback_summary_struct_from_context(article_context)
            verdict = "Summary Completed"
            confidence = 0.75 if generated_text and not summarize_error else 0.2
            llm_provider = "groq"
            source_check = {
                "original_domain": extract_domain(url_in_query) if url_in_query else "",
                "mode": mode,
                "trusted": bool(url_in_query),
                "trust_score": 1.0 if url_in_query else 0.0,
                "corroborating_domains": 0,
            }
            if url_in_query:
                news = [
                    {
                        "title": article_title or "Source article",
                        "description": "Original submitted URL used for summarization.",
                        "url": url_in_query,
                        "published_at": "",
                        "source": extract_domain(url_in_query),
                    }
                ]
            metrics = {
                "news_sources": len(news),
                "evidence_signal": 0.0,
                "support_ratio": 0.0,
                "contradiction_ratio": 0.0,
            }
            meta = {
                "query": query,
                "query_en": query_en,
                "mode": mode,
                "latency": round(time.time() - start_time, 2),
                "confidence": confidence,
                "confidence_breakdown": {"summary_completion": 1.0 if generated_text else 0.0},
                "metrics": metrics,
                "verdict": verdict,
                "fake_news_errors": [],
                "corrected_news": [],
                "news": news,
                "cache_hit": False,
                "generated_answer": generated_text,
                "summarize_error": summarize_error,
                "llm_provider": llm_provider,
                "news_existence": {
                    "exists": bool(news),
                    "match_count": len(news),
                    "checked_query": url_in_query,
                },
                "source_trust_check": source_check,
                "summary_struct": summary_struct,
                "references": [],
                "references_formatted": "",
                "evidence_source": None,
                "cache_stats": None,
            }
            t = time.perf_counter()
            await set_cache(cache_key, {"tokens": streamed_tokens, "meta": meta})
            timing["cache_write_ms"] = _elapsed_ms(t)
            timing["total_ms"] = _elapsed_ms(req_start)
            meta["timing_breakdown"] = timing
            meta["request_id"] = request_id
            logger.info(
                "fact_check_stream request_id=%s mode=%s cache_hit=false timings=%s",
                request_id,
                mode,
                timing,
            )
            yield _safe_send({"type": "meta", "data": meta})
            return

        yield _safe_send({"type": "status", "data": "Retrieving evidence..."})
        rag = get_rag()
        t = time.perf_counter()
        rag_result = await rag.retrieve_evidence(query_en, max_results=2)
        timing["evidence_retrieval_ms"] = _elapsed_ms(t)
        news = rag_result["evidence"]
        evidence_source = rag_result["source"]

        for news_item in news:
            ref_id = news_item.get("ref_id")
            if not ref_id:
                ref_id = ref_manager.add_reference(
                    title=news_item.get("title", ""),
                    url=news_item.get("url", ""),
                    source=news_item.get("source", ""),
                    accessed_from=evidence_source,
                )
                news_item["ref_id"] = ref_id

        evidence_blocks = []
        for item in news[:2]:
            title = (item.get("title", "") or "")[:50]
            snippet = (item.get("description", "") or "")[:200]
            if title and snippet:
                evidence_blocks.append(f"{title}: {snippet}")
        evidence_text = "\n".join(evidence_blocks) if evidence_blocks else "No sources found."
        prompt = f"Verify: {query_en[:100]}\nEvidence: {evidence_text[:500]}\nVERDICT:"

        if not news:
            generated_text = (
                "Verdict: Unverified. No relevant corroborating sources were found quickly. "
                "Try adding date, location, and names for better evidence matching."
            )
            for token in generated_text.split():
                piece = token + " "
                streamed_tokens.append(piece)
                yield _safe_send({"type": "text", "data": piece})
        else:
            yield _safe_send({"type": "status", "data": "Generating verdict..."})
            t = time.perf_counter()
            async for token in stream_generate_async(prompt):
                streamed_tokens.append(token)
                yield _safe_send({"type": "text", "data": token})
            timing["llm_generation_ms"] = _elapsed_ms(t)

        generated_text = "".join(streamed_tokens).strip()
        source_alignment = _source_alignment(query_norm, news)
        verdict = _decide_verdict(
            generated=generated_text,
            evidence_signal=source_alignment["evidence_signal"],
            contradiction_ratio=source_alignment["contradiction_ratio"],
            docs=[],
            news=news,
        )
        confidence_data = {
            "final_confidence": min(1.0, 0.5 + (0.1 * len(news))),
            "breakdown": {"evidence_count": len(news)},
            "metrics": {
                "news_sources": len(news),
                "evidence_signal": source_alignment["evidence_signal"],
            },
        }
        metrics = {
            **confidence_data["metrics"],
            "support_ratio": source_alignment["support_ratio"],
            "contradiction_ratio": source_alignment["contradiction_ratio"],
        }
        references_data = ref_manager.get_all_references()
        references_section = ref_manager.format_references(style="harvard")

        latency = round(time.time() - start_time, 2)
        meta = {
            "query": query,
            "query_en": query_en,
            "mode": mode,
            "latency": latency,
            "confidence": confidence_data["final_confidence"],
            "confidence_breakdown": confidence_data["breakdown"],
            "metrics": metrics,
            "verdict": verdict,
            "fake_news_errors": [],
            "corrected_news": [],
            "evidence_source": evidence_source,
            "news": news,
            "cache_hit": False,
            "generated_answer": generated_text,
            "summarize_error": "",
            "llm_provider": "groq",
            "news_existence": {
                "exists": len(news) > 0,
                "match_count": len(news),
                "checked_query": query_norm,
            },
            "source_trust_check": {"original_domain": "", "mode": mode},
            "summary_struct": None,
            "references": references_data,
            "references_formatted": references_section,
            "cache_stats": rag_result.get("cache_stats", {}),
        }

        t = time.perf_counter()
        await set_cache(cache_key, {"tokens": streamed_tokens, "meta": meta})
        timing["cache_write_ms"] = _elapsed_ms(t)
        timing["total_ms"] = _elapsed_ms(req_start)
        meta["timing_breakdown"] = timing
        meta["request_id"] = request_id
        logger.info(
            "fact_check_stream request_id=%s mode=%s cache_hit=false evidence_source=%s timings=%s",
            request_id,
            mode,
            evidence_source,
            timing,
        )
        yield _safe_send({"type": "meta", "data": meta})

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics and usage"""
    from services.cache_manager import get_cache_manager
    cache_manager = get_cache_manager()
    return cache_manager.get_cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cached data"""
    from services.cache_manager import get_cache_manager
    cache_manager = get_cache_manager()
    stats_before = cache_manager.get_cache_stats()
    cache_manager.clear()
    return {
        "status": "Cache cleared",
        "stats_before": stats_before,
        "stats_after": cache_manager.get_cache_stats()
    }


@router.get("/cache/status")
async def cache_status():
    """Get detailed cache status and info"""
    from services.cache_manager import get_cache_manager
    cache_manager = get_cache_manager()
    stats = cache_manager.get_cache_stats()
    return {
        "status": "ok",
        "cache_enabled": True,
        "caching_strategy": "LRU with frequency weighting",
        "stats": stats,
        "info": {
            "max_size_mb": int(stats.get("max_size_mb", 100)),
            "current_usage_mb": stats.get("total_size_mb", 0),
            "entries_cached": stats.get("total_entries", 0),
            "total_accesses": stats.get("total_accesses", 0),
            "cache_hit_potential": f"{stats.get('usage_percent', 0)}% of capacity used"
        }
    }
