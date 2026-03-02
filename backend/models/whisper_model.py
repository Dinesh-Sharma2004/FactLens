try:
    import whisper
except Exception:
    whisper = None

if whisper is None:
    whisper_model = None
else:
    try:
        whisper_model = whisper.load_model("base")
    except Exception:
        whisper_model = None

def transcribe_audio(path):
    if whisper_model is None:
        return {"text": ""}

    result = whisper_model.transcribe(path)
    return result
