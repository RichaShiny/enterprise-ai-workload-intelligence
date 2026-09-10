"""Regression gate for proposed policy-corpus revisions."""

import hashlib
import json
from dataclasses import asdict

from src.evaluation.regression import RegressionEvaluator
from src.policy_assistant.evaluation import evaluate_policy_assistant
from src.policy_assistant.service import APPROVED_POLICIES, ApprovedPolicyAssistant, PolicyDocument


QUALITY_METRICS = {
    "retrieval_accuracy": True,
    "safe_abstention_rate": True,
}


def policy_snapshot(policies: tuple[PolicyDocument, ...]) -> list[dict]:
    """Return reviewable, content-light metadata for a policy revision."""
    return [
        {
            "document_id": policy.document_id,
            "department": policy.department,
            "version": policy.version,
        }
        for policy in policies
    ]


def policy_release_fingerprint(policies: tuple[PolicyDocument, ...]) -> str:
    """Create a stable content digest without retaining the policy body in audit data."""
    canonical = [
        asdict(policy)
        for policy in sorted(policies, key=lambda policy: policy.document_id)
    ]
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def evaluate_policy_change(
    candidate_policies: tuple[PolicyDocument, ...],
    baseline_policies: tuple[PolicyDocument, ...] = APPROVED_POLICIES,
) -> dict:
    """Block a revision when it regresses retrieval or safe abstention."""
    baseline = evaluate_policy_assistant(ApprovedPolicyAssistant(baseline_policies))
    candidate = evaluate_policy_assistant(ApprovedPolicyAssistant(candidate_policies))
    baseline_metrics = {name: baseline[name] for name in QUALITY_METRICS}
    candidate_metrics = {name: candidate[name] for name in QUALITY_METRICS}
    gate = RegressionEvaluator(default_tolerance=0.0).compare(
        baseline_metrics,
        candidate_metrics,
        QUALITY_METRICS,
    )

    return {
        "passed": gate.passed,
        "regressions": gate.regressions,
        "improvements": gate.improvements,
        "unchanged": gate.unchanged,
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "baseline_snapshot": policy_snapshot(baseline_policies),
        "candidate_snapshot": policy_snapshot(candidate_policies),
        "baseline_fingerprint": policy_release_fingerprint(baseline_policies),
        "candidate_fingerprint": policy_release_fingerprint(candidate_policies),
        "scope": (
            "Demonstration-only release gate. A production implementation must "
            "authenticate policy authors and evaluate an access-controlled policy source."
        ),
    }
