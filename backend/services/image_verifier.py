import os
import re

import requests
from PIL import Image

try:
    import torch
except Exception:
    torch = None


def verify_image(image_path, query):
    remote_score = _verify_image_remote_vit(image_path, query)
    if remote_score is not None:
        return remote_score

    if torch is None:
        return 0.5

    try:
        from models.clip_model import get_clip
        clip_model, clip_processor = get_clip()
    except Exception:
        return 0.5

    image = Image.open(image_path)

    inputs = clip_processor(
        text=[query],
        images=image,
        return_tensors="pt",
        padding=True
    )

    outputs = clip_model(**inputs)

    logits_per_image = outputs.logits_per_image
    score = torch.softmax(logits_per_image, dim=1)[0][0].item()

    return round(score, 2)


def _verify_image_remote_vit(image_path, query):
    endpoint = os.getenv("HF_VIT_ENDPOINT", "https://api-inference.huggingface.co/models/google/vit-base-patch16-224")
    token = os.getenv("HF_API_TOKEN", "").strip()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with open(image_path, "rb") as f:
            res = requests.post(endpoint, headers=headers, data=f.read(), timeout=20)
        if res.status_code >= 400:
            return None
        payload = res.json()
        if not isinstance(payload, list):
            return None

        query_tokens = set(re.findall(r"[a-zA-Z0-9]{3,}", (query or "").lower()))
        if not query_tokens:
            return round(float(payload[0].get("score", 0.5)), 2) if payload else 0.5

        best = 0.0
        for item in payload[:8]:
            label = str(item.get("label", "")).lower()
            score = float(item.get("score", 0.0))
            if any(t in label for t in query_tokens):
                best = max(best, score)
            else:
                best = max(best, score * 0.25)
        return round(best, 2)
    except Exception:
        return None
