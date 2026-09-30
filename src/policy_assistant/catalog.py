"""Versioned, local policy-catalog adapter for the demonstration service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "policies" / "approved_policies.json"
REQUIRED_FIELDS = {"document_id", "title", "department", "version", "text"}
MAX_CATALOG_BYTES = 1_000_000
MAX_POLICIES = 1_000
MAX_FIELD_LENGTHS = {
    "document_id": 128,
    "title": 256,
    "department": 128,
    "version": 64,
    "text": 50_000,
}


class PolicyCatalogError(ValueError):
    """Raised when the configured approved-policy catalog is unusable."""


def load_policy_catalog(path: Path = CATALOG_PATH) -> tuple[dict[str, str], ...]:
    """Load one reviewed policy release, rejecting malformed or duplicate documents."""
    try:
        catalog_text = path.read_text(encoding="utf-8")
        if len(catalog_text.encode("utf-8")) > MAX_CATALOG_BYTES:
            raise PolicyCatalogError("Approved policy catalog exceeds the maximum size.")
        payload: dict[str, Any] = json.loads(catalog_text)
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyCatalogError(f"Unable to load approved policy catalog: {error}") from error

    if not isinstance(payload, dict):
        raise PolicyCatalogError("Approved policy catalog must be a JSON object.")
    policies = payload.get("policies")
    if not isinstance(policies, list) or not policies:
        raise PolicyCatalogError("Approved policy catalog must contain a non-empty policies list.")
    if len(policies) > MAX_POLICIES:
        raise PolicyCatalogError("Approved policy catalog contains too many policies.")
    if not isinstance(payload.get("catalog_version"), str) or not payload["catalog_version"]:
        raise PolicyCatalogError("Approved policy catalog must include catalog_version.")

    documents: list[dict[str, str]] = []
    ids: set[str] = set()
    for policy in policies:
        if not isinstance(policy, dict) or set(policy) != REQUIRED_FIELDS:
            raise PolicyCatalogError("Each policy must contain only the required document fields.")
        if not all(isinstance(policy[field], str) and policy[field].strip() for field in REQUIRED_FIELDS):
            raise PolicyCatalogError("Every policy field must be a non-empty string.")
        for field in REQUIRED_FIELDS:
            value = policy[field]
            if value != " ".join(value.split()):
                raise PolicyCatalogError(f"Policy field {field} must use normalized whitespace.")
            if len(value) > MAX_FIELD_LENGTHS[field]:
                raise PolicyCatalogError(f"Policy field {field} exceeds the maximum length.")
        if policy["document_id"] in ids:
            raise PolicyCatalogError("Policy document IDs must be unique.")
        ids.add(policy["document_id"])
        documents.append({field: policy[field] for field in REQUIRED_FIELDS})
    return tuple(documents)


def catalog_metadata(path: Path = CATALOG_PATH) -> dict[str, str | int]:
    """Return safe release metadata without returning policy body content."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = load_policy_catalog(path)
    return {
        "catalog_version": payload["catalog_version"],
        "source": payload.get("source", "approved-policy-catalog"),
        "documents": len(documents),
    }
