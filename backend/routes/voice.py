import os
import shutil
import uuid

from fastapi import APIRouter, File, UploadFile

from models.whisper_model import transcribe_audio

router = APIRouter()


@router.post("/voice-transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    temp_name = f"temp_audio_{uuid.uuid4().hex}_{file.filename}"

    try:
        with open(temp_name, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = transcribe_audio(temp_name)
        transcript = (result or {}).get("text", "").strip()
        return {"transcript": transcript}
    except Exception as exc:
        return {"error": f"Voice transcription failed: {exc}"}
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)
