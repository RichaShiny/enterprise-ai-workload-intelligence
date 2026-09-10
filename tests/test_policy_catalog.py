import json

import pytest

from src.policy_assistant.catalog import PolicyCatalogError, catalog_metadata, load_policy_catalog


def test_versioned_policy_catalog_loads_the_reviewed_release():
    policies = load_policy_catalog()
    metadata = catalog_metadata()

    assert len(policies) == 5
    assert metadata == {
        "catalog_version": "2026.2",
        "source": "approved-policy-catalog",
        "documents": 5,
    }
    assert policies[0]["document_id"] == "finance-expense-retention"


def test_catalog_rejects_duplicate_document_ids(tmp_path):
    path = tmp_path / "policies.json"
    policy = {
        "document_id": "finance-policy", "title": "Finance policy", "department": "finance",
        "version": "1", "text": "A reviewed policy body with enough text to be valid.",
    }
    path.write_text(json.dumps({"catalog_version": "1", "policies": [policy, policy]}))

    with pytest.raises(PolicyCatalogError, match="unique"):
        load_policy_catalog(path)
