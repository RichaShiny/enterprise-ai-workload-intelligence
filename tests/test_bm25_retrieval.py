import pytest

from src.retrieval.index import BM25Retriever


def test_bm25_prefers_rare_exact_identifiers():
    retriever = BM25Retriever()
    retriever.fit([
        {"document_id": "generic", "text": "expense records retention policy", "metadata": {}},
        {"document_id": "fin-742", "text": "expense records policy FIN-742", "metadata": {}},
    ])

    results = retriever.search("What does FIN-742 require?")

    assert results[0].document_id == "fin-742"
    assert results[0].score > results[1].score


def test_bm25_applies_metadata_filters_before_ranking():
    retriever = BM25Retriever()
    retriever.fit([
        {"document_id": "finance", "text": "retention", "metadata": {"department": "finance"}},
        {"document_id": "security", "text": "retention", "metadata": {"department": "security"}},
    ])

    results = retriever.search("retention", metadata_filters={"department": "security"})

    assert [result.document_id for result in results] == ["security"]


def test_bm25_requires_a_fitted_index():
    with pytest.raises(RuntimeError, match="fit"):
        BM25Retriever().search("policy")
