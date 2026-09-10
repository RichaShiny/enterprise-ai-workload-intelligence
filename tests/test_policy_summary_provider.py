import json

from src.policy_assistant.provider import PolicySummaryProvider


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return json.dumps(self.body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_provider_is_inert_until_explicitly_enabled():
    provider = PolicySummaryProvider(api_key="secret", enabled=False)

    result = provider.summarize("What is the retention rule?", [])

    assert result["status"] == "disabled"


def test_provider_sends_only_selected_evidence_and_requests_non_stored_response():
    captured = {}

    def opener(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse({"output_text": "Keep records for seven years [finance-expense-retention v2026.1]."})

    provider = PolicySummaryProvider(api_key="secret", enabled=True, model="test-model", opener=opener)
    result = provider.summarize(
        "How long are receipts retained?",
        [{
            "document_id": "finance-expense-retention",
            "title": "Expense record retention",
            "department": "finance",
            "version": "2026.1",
            "excerpt": "Receipts must be retained for seven years.",
            "relevance_score": 0.8,
        }],
    )

    assert result["status"] == "generated"
    assert result["model"] == "test-model"
    assert result["citations"] == [{"document_id": "finance-expense-retention", "version": "2026.1"}]
    assert captured["payload"]["store"] is False
    assert "Receipts must be retained" in captured["payload"]["input"]
    assert captured["timeout"] == 20


def test_provider_rejects_summary_that_cites_an_unretrieved_policy():
    def opener(_request, timeout):
        assert timeout == 20
        return FakeResponse({"output_text": "Escalate it [security-access-review v2026.2]."})

    provider = PolicySummaryProvider(api_key="secret", enabled=True, opener=opener)
    result = provider.summarize(
        "How long are receipts retained?",
        [{
            "document_id": "finance-expense-retention",
            "title": "Expense record retention",
            "department": "finance",
            "version": "2026.1",
            "excerpt": "Receipts must be retained for seven years.",
            "relevance_score": 0.8,
        }],
    )

    assert result["status"] == "fallback"
    assert "selected approved evidence" in result["reason"]


def test_provider_rejects_summary_without_a_source_citation():
    def opener(_request, timeout):
        assert timeout == 20
        return FakeResponse({"output_text": "Keep records for seven years."})

    provider = PolicySummaryProvider(api_key="secret", enabled=True, opener=opener)
    result = provider.summarize(
        "How long are receipts retained?",
        [{
            "document_id": "finance-expense-retention",
            "title": "Expense record retention",
            "department": "finance",
            "version": "2026.1",
            "excerpt": "Receipts must be retained for seven years.",
            "relevance_score": 0.8,
        }],
    )

    assert result["status"] == "fallback"
