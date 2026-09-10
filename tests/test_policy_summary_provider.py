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
    assert captured["payload"]["store"] is False
    assert "Receipts must be retained" in captured["payload"]["input"]
    assert captured["timeout"] == 20
