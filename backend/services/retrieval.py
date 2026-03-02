import asyncio

try:
    from langchain_community.vectorstores import FAISS
except Exception:
    FAISS = None

from models.embeddings import get_embeddings

embedding = get_embeddings()

if FAISS is None or embedding is None:
    vectorstore = None
else:
    try:
        vectorstore = FAISS.load_local(
            "data/vector_store",
            embedding,
            allow_dangerous_deserialization=True,
        )
    except Exception:
        vectorstore = None

async def retrieve_docs_async(query):
    if vectorstore is None:
        return []

    return await asyncio.to_thread(
        vectorstore.similarity_search, query, 5
    )
