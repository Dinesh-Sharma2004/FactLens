from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.llms import HuggingFaceHub

embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def load_vectorstore():
    return FAISS.load_local("data/vector_store", embedding)

def generate_answer(query, docs):
    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"""
    Verify the claim: {query}

    Context:
    {context}

    Give:
    - Verdict
    - Explanation
    """

    llm = HuggingFaceHub(repo_id="google/flan-t5-base")
    return llm(prompt)
