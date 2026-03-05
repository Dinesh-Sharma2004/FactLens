import os
import shutil
import uuid

from fastapi import APIRouter, File, UploadFile
import requests

from models.whisper_model import transcribe_audio

router = APIRouter()


@router.post("/voice-transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    temp_name = f"temp_audio_{uuid.uuid4().hex}_{file.filename}"

    try:
        with open(temp_name, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_key:
            transcribed = _transcribe_with_groq(temp_name, groq_key)
            if transcribed:
                english_text = _translate_to_english_with_groq(transcribed["text"], groq_key)
                return {
                    "transcript": transcribed["text"],
                    "transcript_english": english_text or transcribed["text"],
                    "language": transcribed.get("language", "unknown"),
                    "provider": "groq",
                }

        # Fallback local lightweight path when Groq is unavailable
        result = transcribe_audio(temp_name)
        transcript = (result or {}).get("text", "").strip()
        return {
            "transcript": transcript,
            "transcript_english": transcript,
            "language": "unknown",
            "provider": "local",
        }
    except Exception as exc:
        return {"error": f"Voice transcription failed: {exc}"}
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def _transcribe_with_groq(audio_path: str, api_key: str):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": os.getenv("GROQ_ASR_MODEL", "whisper-large-v3-turbo"),
        "response_format": "verbose_json",
        "temperature": "0",
    }

    try:
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/webm")}
            res = requests.post(url, headers=headers, data=data, files=files, timeout=40)
        res.raise_for_status()
        payload = res.json()
        text = (payload.get("text") or "").strip()
        if not text:
            return None
        return {"text": text, "language": payload.get("language", "unknown")}
    except Exception:
        return None


def _translate_to_english_with_groq(text: str, api_key: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "temperature": 0,
        "max_tokens": 220,
        "messages": [
            {
                "role": "system",
                "content": "Translate user speech to concise English. Return only the translated text.",
            },
            {"role": "user", "content": text},
        ],
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        data = res.json()
        out = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return out or text
    except Exception:
        return text
