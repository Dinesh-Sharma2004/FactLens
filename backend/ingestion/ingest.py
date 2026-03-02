from ingestion.loaders import load_all_data
from ingestion.chunking import split_documents
from ingestion.build_index import build_faiss_index


def run_ingestion():
    docs = load_all_data()

    if not docs:
        print("❌ No data loaded")
        return

    chunks = split_documents(docs)
    build_faiss_index(chunks)

    print("✅ FAISS index built with real data")


if __name__ == "__main__":
    run_ingestion()
