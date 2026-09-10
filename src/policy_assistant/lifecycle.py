"""Reviewable accept, fallback, and escalation decisions for policy answers."""

from __future__ import annotations


def decide_policy_response(policy_result: dict, model_summary: dict, routing: dict) -> dict:
    """Describe the executed answer path without retaining question or policy content.

    A generated provider answer is accepted only after citation validation in the
    provider adapter. Deterministic evidence remains an acceptable response when
    the provider is disabled or unavailable. Weak retrieval always escalates.
    """
    route = {
        "recommended_strategy": routing["recommended_strategy"],
        "routing_source": routing["routing_source"],
    }
    if policy_result["abstained"]:
        return {
            "status": "escalated",
            "next_action": "Send to policy owner",
            "reason": "The retriever found insufficient approved evidence; no model call was made.",
            "response_source": "safe_abstention",
            "verification": {"status": "not_applicable", "reason": "No answer was generated."},
            "route": route,
        }

    if model_summary.get("status") == "generated":
        return {
            "status": "accepted",
            "next_action": "Use cited model summary",
            "reason": "The provider returned a summary whose citations match the selected approved evidence.",
            "response_source": "provider_summary",
            "verification": {
                "status": "passed",
                "reason": "Every displayed citation refers to selected approved policy evidence.",
                "citations": model_summary["citations"],
            },
            "route": route,
        }

    return {
        "status": "accepted_with_fallback",
        "next_action": "Use cited evidence extract",
        "reason": "A provider summary was not accepted, so the system returned the deterministic approved-evidence extract.",
        "response_source": "deterministic_evidence",
        "verification": {
            "status": "passed",
            "reason": "The response is an extract of selected approved policy evidence.",
        },
        "route": route,
    }
