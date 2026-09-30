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


def test_bm25_requires_a_fitted_index():
    with pytest.raises(RuntimeError, match="fit"):
        BM25Retriever().search("policy")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("spend above $25,000", "spend above 25000 dollars"),
        ("spend above 25k", "spend above 25000"),
        ("budget is 1.5m", "budget is 1500000"),
        ("margin is 12.5%", "margin is 12.5 percent"),
        ("fees of €2k", "fees of 2000 euros"),
        ("limit is £500", "limit is 500 pounds"),
        ("price is ¥300", "price is 300 yen"),
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


@pytest.mark.parametrize(
    ("query", "catalog_text"),
    [
        ("Does the 20% threshold apply?", "A 20 percent threshold applies"),
        ("Who approves $25k?", "Approval above 25000 dollars"),
        ("What is the €2k limit?", "The limit is 2000 euros"),
    ],
)
def test_bm25_matches_symbolic_numeric_forms_to_words(query, catalog_text):
    retriever = BM25Retriever()
    retriever.fit([
        {"document_id": "match", "text": catalog_text, "metadata": {}},
        {"document_id": "other", "text": "unrelated operating guidance", "metadata": {}},
    ])

    results = retriever.search(query)

    assert results[0].document_id == "match"
    assert results[0].score > results[1].score
