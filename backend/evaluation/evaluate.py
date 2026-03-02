import requests
import json

URL = "http://localhost:8000/fact-check-stream"

def test_mode(claim, mode):
    res = requests.post(URL, json={
        "query": claim,
        "mode": mode
    })

    return res.text.lower()


def evaluate():
    with open("evaluation/test_data.json") as f:
        data = json.load(f)

    rag_correct = 0
    no_rag_correct = 0

    for item in data:
        claim = item["claim"]
        label = item["label"].lower()

        rag_output = test_mode(claim, "rag")
        no_rag_output = test_mode(claim, "no_rag")

        if label in rag_output:
            rag_correct += 1

        if label in no_rag_output:
            no_rag_correct += 1

    total = len(data)

    print(f"\nRAG Accuracy: {rag_correct/total:.2f}")
    print(f"No-RAG Accuracy: {no_rag_correct/total:.2f}")


if __name__ == "__main__":
    evaluate()
