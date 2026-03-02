try:
    from transformers import pipeline
except Exception:
    pipeline = None

if pipeline is None:
    translator_hi_en = None
else:
    try:
        translator_hi_en = pipeline(
            "translation",
            model="Helsinki-NLP/opus-mt-hi-en"
        )
    except Exception as e:
        print("⚠️ Translation model failed:", e)
        translator_hi_en = None


def translate_to_english(text, lang="en"):
    if lang == "hi" and translator_hi_en:
        return translator_hi_en(text)[0]["translation_text"]

    return text
