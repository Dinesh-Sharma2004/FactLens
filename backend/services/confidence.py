def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def compute_confidence_explain(docs, query, news, evidence_signal=0.0):
    doc_count = len(docs)
    news_count = len(news)
    query_len = len(query.split())
    evidence_signal = _clamp(evidence_signal)

    retrieval_score = _clamp(doc_count / 5)
    source_agreement = _clamp(0.45 + (0.1 * min(news_count, 5)))
    recency_score = _clamp(0.3 if news_count == 0 else 0.65 + (0.05 * min(news_count, 3)))
    consistency_score = _clamp(0.4 + min(query_len, 25) / 100 + (0.25 * evidence_signal))

    final_score = round(
        (retrieval_score + source_agreement + recency_score + consistency_score) / 4,
        2,
    )

    return {
        "final_confidence": final_score,
        "breakdown": {
            "retrieval_score": round(retrieval_score, 2),
            "source_agreement": round(source_agreement, 2),
            "recency_score": round(recency_score, 2),
            "consistency_score": round(consistency_score, 2),
        },
        "metrics": {
            "retrieved_documents": doc_count,
            "news_sources": news_count,
            "query_terms": query_len,
            "evidence_signal": round(evidence_signal, 2),
            "confidence_formula": "mean(retrieval, source_agreement, recency, consistency)",
        },
    }
