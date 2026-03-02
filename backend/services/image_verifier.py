from PIL import Image

try:
    import torch
except Exception:
    torch = None


def verify_image(image_path, query):
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
