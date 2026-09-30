import pytest

from src.retrieval.index import BM25Retriever, normalize_retrieval_text


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


def test_bm25_breaks_equal_score_ties_by_document_id():
    retriever = BM25Retriever()
    retriever.fit([
        {"document_id": "z-policy", "text": "retention policy", "metadata": {}},
        {"document_id": "a-policy", "text": "retention policy", "metadata": {}},
    ])

    results = retriever.search("retention")

    assert [result.document_id for result in results] == ["a-policy", "z-policy"]


def test_bm25_rejects_duplicate_document_ids():
    retriever = BM25Retriever()

    with pytest.raises(ValueError, match=r"duplicates: shared-policy"):
        retriever.fit([
            {"document_id": "shared-policy", "text": "finance policy", "metadata": {}},
            {"document_id": "shared-policy", "text": "security policy", "metadata": {}},
        ])


def test_bm25_requires_a_fitted_index():
    with pytest.raises(RuntimeError, match="fit"):
        BM25Retriever().search("policy")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("spend above $25,000", "spend above $25000"),
        ("spend above 25k", "spend above 25000"),
        ("budget is 1.5m", "budget is 1500000"),
    ],
)
def test_retrieval_text_normalizes_equivalent_amounts(query, expected):
    assert normalize_retrieval_text(query) == expected


def test_bm25_matches_numeric_shorthand_to_catalog_amounts():
    retriever = BM25Retriever()
    retriever.fit([
        {"document_id": "low", "text": "approval above 5,000 dollars", "metadata": {}},
        {"document_id": "high", "text": "approval above 25,000 dollars", "metadata": {}},
    ])

    results = retriever.search("Who approves 25k?")

    assert results[0].document_id == "high"
