import asyncio
import os
import json

import requests


def _mock_fact_check_text(prompt: str) -> str:
    lower = prompt.lower()
    if "trust_check_mode" in lower:
        return (
            "Trust Assessment: likely trusted. "
            "Reason: At least one top corroborating source appears from established news domains."
        )

    if "summarize_verify_mode" in lower:
        match = "found" if "news_exists:true" in lower else "not found"
        return (
            f"NewsAPI Cross-check: {match}. "
            "The summarized story appears to align with available trusted-source reporting."
            if match == "found"
            else "NewsAPI Cross-check: not found. This summarized story could not be confirmed from trusted-source results."
        )

    if "summarize_mode" in lower:
        return (
            "Summary: This article discusses a recent event with key actors, timeline, and impact. "
            "Key Points: It highlights the central claim, supporting context, and public response. "
            "Caution: Validate with at least two independent trusted outlets for full confidence."
        )

    if "verify_mode" in lower:
        if any(token in lower for token in ["hoax", "fake", "rumor", "forwards", "forwards message"]):
            verdict = "Likely False"
        elif any(token in lower for token in ["breaking", "unconfirmed", "viral"]):
            verdict = "Partly True"
        else:
            verdict = "Likely True"

        return (
            f"Verdict: {verdict}. "
            "What seems wrong: The claim may overstate certainty, omit timeline context, or lack corroboration. "
            "Correct news direction: Use trusted source coverage and date-aligned reporting for corrections."
        )

    return "Unable to determine mode."


def _call_groq_stream(prompt: str):
    """Stream tokens from Groq API"""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        # Fallback to mock
        text = _mock_fact_check_text(prompt)
        for word in text.split():
            yield word + " "
        return

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Fact Lens.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 50,
        "top_p": 1.0,
        "stream": True,  # Enable streaming
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=7, stream=True)
        res.raise_for_status()
        
        for line in res.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8') if isinstance(line, bytes) else line
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    pass
    except Exception:
        # Fallback to non-streaming mock
        text = _mock_fact_check_text(prompt)
        for word in text.split():
            yield word + " "


def _call_groq(prompt: str) -> tuple[str, str]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return _mock_fact_check_text(prompt), "mock"

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Fact Lens.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,  # Zero randomness for speed
        "max_tokens": 50,    # Ultra-minimal tokens
        "top_p": 1.0,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=7)  # Aggressive timeout
        res.raise_for_status()
        data = res.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if text:
            return text, "groq"
        return _mock_fact_check_text(prompt), "mock"
    except Exception:
        return _mock_fact_check_text(prompt), "mock"


async def generate_text_async(prompt: str) -> tuple[str, str]:
    return await asyncio.to_thread(_call_groq, prompt)


async def stream_generate_async(prompt):
    """Stream tokens from LLM asynchronously"""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def producer():
        try:
            for token in _call_groq_stream(prompt):
                asyncio.run_coroutine_threadsafe(queue.put(token), loop).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

    producer_task = asyncio.create_task(asyncio.to_thread(producer))

    try:
        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
    finally:
        await producer_task
