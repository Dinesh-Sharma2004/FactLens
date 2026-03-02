from langchain_community.vectorstores import FAISS
from models.embeddings import get_embeddings

def build_faiss_index(chunks):
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("data/vector_store")
