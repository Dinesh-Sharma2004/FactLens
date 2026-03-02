try:
    from transformers import CLIPModel, CLIPProcessor
except Exception:
    CLIPModel = None
    CLIPProcessor = None

_clip_model = None
_clip_processor = None


def get_clip():
    global _clip_model, _clip_processor

    if CLIPModel is None or CLIPProcessor is None:
        raise RuntimeError("transformers is not available")

    if _clip_model is None or _clip_processor is None:
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    return _clip_model, _clip_processor
