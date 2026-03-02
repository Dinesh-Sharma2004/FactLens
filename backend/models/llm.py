import asyncio


def _mock_fact_check_text(prompt: str) -> str:
    lower = prompt.lower()
    if any(token in lower for token in ["hoax", "fake", "rumor", "forwards"]):
        verdict = "Likely False"
    elif any(token in lower for token in ["breaking", "unconfirmed", "viral"]):
        verdict = "Partly True"
    else:
        verdict = "Likely True"

    return (
        f"Verdict: {verdict}. "
        "The current result is an initial automated analysis. "
        "Cross-check dates, primary sources, and official statements before final decisions. "
        "Uncertainty remains where independent corroboration is limited."
    )


async def stream_generate_async(prompt):
    text = _mock_fact_check_text(prompt)
    for word in text.split():
        yield word + " "
        await asyncio.sleep(0.01)
