import asyncio

try:
    from langchain_community.vectorstores import FAISS
except Exception:
    FAISS = None

from models.embeddings import get_embeddings

vectorstore = None
_vectorstore_initialized = False


def _ensure_vectorstore():
    global vectorstore, _vectorstore_initialized

    if _vectorstore_initialized:
        return vectorstore

    _vectorstore_initialized = True

    if FAISS is None:
        vectorstore = None
        return vectorstore

    embedding = get_embeddings()
    if embedding is None:
        vectorstore = None
        return vectorstore

    try:
        vectorstore = FAISS.load_local(
            "data/vector_store",
            embedding,
            allow_dangerous_deserialization=True,
        )
    except Exception:
        vectorstore = None

    return vectorstore

async def retrieve_docs_async(query):
    store = _ensure_vectorstore()
    if store is None:
        return []

    return await asyncio.to_thread(
        store.similarity_search, query, 5
    )
