from fastapi import APIRouter, UploadFile, File
import shutil
import os

from services.image_verifier import verify_image

router = APIRouter()


@router.post("/image-verify")
async def image_verify(file: UploadFile = File(...), query: str = ""):

    file_path = f"temp_{file.filename}"

    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run verification
        score = verify_image(file_path, query)

        return {
            "image_score": score,
            "message": "Higher score = more relevant/likely true"
        }

    except Exception as e:
        print("❌ Image verify error:", e)
        return {"error": "Image verification failed"}

    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
