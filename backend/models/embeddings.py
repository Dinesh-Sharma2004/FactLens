try:
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    HuggingFaceEmbeddings = None

_embedding_model = None

def get_embeddings():
    global _embedding_model

    if HuggingFaceEmbeddings is None:
        return None

    if _embedding_model is None:
        try:
            _embedding_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        except Exception:
            _embedding_model = None

    return _embedding_model
