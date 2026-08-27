from src.retrieval.index import LexicalRetriever
from src.retrieval.ranker import SemanticReranker
from src.evaluation.retrieval_eval import (
    aggregate_metrics,
    evaluate_query,
)


DOCUMENTS = [
    {
        "document_id": "doc_1",
        "text": (
            "High-sensitivity compliance requests containing regulated "
            "or confidential information must not be routed to external "
            "AI providers."
        ),
        "metadata": {
            "department": "compliance",
            "topic": "sensitivity",
        },
    },
    {
        "document_id": "doc_2",
        "text": (
            "Compliance teams may use external AI providers for low-risk "
            "administrative summarization when no confidential information "
            "is included."
        ),
        "metadata": {
            "department": "compliance",
            "topic": "external_models",
        },
    },
    {
        "document_id": "doc_3",
        "text": (
            "Smaller local models may handle low-complexity summarization "
            "when quality requirements are moderate and latency matters."
        ),
        "metadata": {
            "department": "support",
            "topic": "routing",
        },
    },
    {
        "document_id": "doc_4",
        "text": (
            "Frontier models may be preferred for summarization when "
            "documents require complex reasoning or high factual accuracy."
        ),
        "metadata": {
            "department": "support",
            "topic": "routing",
        },
    },
    {
        "document_id": "doc_5",
        "text": (
            "Coding tasks with strict latency requirements should only use "
            "specialized coding models when expected response time remains "
            "within the workload latency budget."
        ),
        "metadata": {
            "department": "engineering",
            "topic": "latency",
        },
    },
    {
        "document_id": "doc_6",
        "text": (
            "Coding workloads with high reasoning complexity may benefit "
            "from specialized coding models even when they have higher cost."
        ),
        "metadata": {
            "department": "engineering",
            "topic": "coding",
        },
    },
    {
        "document_id": "doc_7",
        "text": (
            "Retrieval systems should prioritize supporting evidence recall "
            "and ranking quality before evaluating downstream generation."
        ),
        "metadata": {
            "department": "research",
            "topic": "retrieval",
        },
    },
    {
        "document_id": "doc_8",
        "text": (
            "Generation systems should be evaluated for groundedness, "
            "faithfulness, completeness, and task success."
        ),
        "metadata": {
            "department": "research",
            "topic": "generation",
        },
    },
    {
        "document_id": "doc_9",
        "text": (
            "Frontier models generally provide stronger reasoning ability "
            "but introduce higher inference cost and latency."
        ),
        "metadata": {
            "department": "finance",
            "topic": "cost",
        },
    },
    {
        "document_id": "doc_10",
        "text": (
            "Small local models reduce inference cost and data exposure "
            "but may provide weaker performance on complex reasoning tasks."
        ),
        "metadata": {
            "department": "finance",
            "topic": "cost",
        },
    },
]


QUERIES = [
    {
        "query": (
            "Can confidential compliance workloads be sent "
            "to external AI providers?"
        ),
        "relevant_ids": ["doc_1"],
    },
    {
        "query": (
            "When should a small local model be used "
            "for summarization?"
        ),
        "relevant_ids": ["doc_3"],
    },
    {
        "query": (
            "Should a coding model be used when latency "
            "requirements are strict?"
        ),
        "relevant_ids": ["doc_5"],
    },
    {
        "query": (
            "What should be measured first when evaluating "
            "an information retrieval system?"
        ),
        "relevant_ids": ["doc_7"],
    },
    {
        "query": (
            "What trade-off comes with using a frontier model "
            "for reasoning?"
        ),
        "relevant_ids": ["doc_9"],
    },
]

def run_benchmark():
    retriever = LexicalRetriever()
    retriever.fit(DOCUMENTS)

    reranker = SemanticReranker()

    retrieval_metrics = []
    reranked_metrics = []

    for item in QUERIES:
        query = item["query"]
        relevant_ids = item["relevant_ids"]

        retrieved = retriever.search(
            query=query,
            top_k=5,
        )

        retrieved_ids = [
            result.document_id
            for result in retrieved
        ]

        reranked = reranker.rerank(
            query=query,
            results=retrieved,
        )

        reranked_ids = [
            result.document_id
            for result in reranked
        ]

        retrieval_metrics.append(
            evaluate_query(
                retrieved_ids=retrieved_ids,
                relevant_ids=relevant_ids,
                k=3,
            )
        )

        reranked_metrics.append(
            evaluate_query(
                retrieved_ids=reranked_ids,
                relevant_ids=relevant_ids,
                k=3,
            )
        )

        print(f"\nQuery: {query}")
        print(f"Relevant: {relevant_ids}")
        print(f"Retrieved: {retrieved_ids[:3]}")
        print(f"Reranked: {reranked_ids[:3]}")

    baseline_summary = aggregate_metrics(
        retrieval_metrics
    )

    reranked_summary = aggregate_metrics(
        reranked_metrics
    )

    print("\nBaseline retrieval metrics")
    for metric, value in baseline_summary.items():
        print(f"{metric}: {value:.3f}")

    print("\nReranked retrieval metrics")
    for metric, value in reranked_summary.items():
        print(f"{metric}: {value:.3f}")


if __name__ == "__main__":
    run_benchmark()