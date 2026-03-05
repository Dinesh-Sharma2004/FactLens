translator_hi_en = None
_translator_initialized = False


def _get_translator():
    global translator_hi_en, _translator_initialized

    if _translator_initialized:
        return translator_hi_en

    _translator_initialized = True

    try:
        from transformers import pipeline
    except Exception:
        translator_hi_en = None
        return translator_hi_en

    try:
        translator_hi_en = pipeline(
            "translation",
            model="Helsinki-NLP/opus-mt-hi-en"
        )
    except Exception as e:
        print("⚠️ Translation model failed:", e)
        translator_hi_en = None

    return translator_hi_en


def translate_to_english(text, lang="en"):
    if lang == "hi":
        translator = _get_translator()
        if translator:
            return translator(text)[0]["translation_text"]

    return text
