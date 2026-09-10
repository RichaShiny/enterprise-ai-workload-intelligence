"""Versioned, local policy-catalog adapter for the demonstration service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "policies" / "approved_policies.json"
REQUIRED_FIELDS = {"document_id", "title", "department", "version", "text"}


class PolicyCatalogError(ValueError):
    """Raised when the configured approved-policy catalog is unusable."""


def load_policy_catalog(path: Path = CATALOG_PATH) -> tuple[dict[str, str], ...]:
    """Load one reviewed policy release, rejecting malformed or duplicate documents."""
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyCatalogError(f"Unable to load approved policy catalog: {error}") from error

    policies = payload.get("policies")
    if not isinstance(policies, list) or not policies:
        raise PolicyCatalogError("Approved policy catalog must contain a non-empty policies list.")
    if not isinstance(payload.get("catalog_version"), str) or not payload["catalog_version"]:
        raise PolicyCatalogError("Approved policy catalog must include catalog_version.")

    documents: list[dict[str, str]] = []
    ids: set[str] = set()
    for policy in policies:
        if not isinstance(policy, dict) or set(policy) != REQUIRED_FIELDS:
            raise PolicyCatalogError("Each policy must contain only the required document fields.")
        if not all(isinstance(policy[field], str) and policy[field].strip() for field in REQUIRED_FIELDS):
            raise PolicyCatalogError("Every policy field must be a non-empty string.")
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
