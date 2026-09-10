from src.policy_assistant.service import ApprovedPolicyAssistant, PolicyDocument


class FakeSemanticReranker:
    def rerank(self, _question, results):
        class Ranked:
            def __init__(self, document_id, ranking_score):
                self.document_id = document_id
                self.ranking_score = ranking_score

        return [
            Ranked(result.document_id, 1.0 if result.document_id == "second" else 0.5)
            for result in results
        ]


def test_semantic_reranking_reorders_lexical_candidates_without_changing_evidence():
    policies = (
        PolicyDocument("first", "Budget process", "finance", "1", "Budget approval requires an owner review."),
        PolicyDocument("second", "Spend process", "finance", "1", "Spend approval requires finance owner review."),
    )
    assistant = ApprovedPolicyAssistant(policies, semantic_reranker=FakeSemanticReranker())

    result = assistant.answer("What approval owner review is required?")

    assert result["grounded"] is True
    assert result["retrieval"]["ranking_method"] == "semantic"
    assert result["evidence"][0]["document_id"] == "second"
    assert result["evidence"][0]["ranking_method"] == "semantic"
