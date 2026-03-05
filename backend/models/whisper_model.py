try:
    import whisper
except Exception:
    whisper = None

_whisper_model = None


def _get_whisper():
    global _whisper_model
    if whisper is None:
        return None
    if _whisper_model is None:
        try:
            _whisper_model = whisper.load_model("base")
        except Exception:
            _whisper_model = None
    return _whisper_model

def transcribe_audio(path):
    model = _get_whisper()
    if model is None:
        return {"text": ""}

    result = model.transcribe(path)
    return result
