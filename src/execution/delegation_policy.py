"""Deterministic guardrails for delegating bounded, lower-risk AI work."""

from dataclasses import asdict, dataclass


DELEGABLE_OPERATIONS = frozenset({"bulk_context", "boilerplate_generation"})
PRIMARY_ONLY_OPERATIONS = frozenset({"debugging", "architecture", "targeted_edit"})


@dataclass(frozen=True)
class DelegationDecision:
    allowed: bool
    execution_path: str
    worker_profile: str | None
    reason: str
    policy: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_delegation_policy(
    *,
    operation: str,
    context_units: int,
    sensitivity: str,
    risk_level: str,
    reference_available: bool = False,
    minimum_context_units: int = 10_000,
) -> DelegationDecision:
    """Allow only bounded I/O work to use an efficient worker profile.

    ``context_units`` is an application-defined estimate (for example, input
    characters or tokens) and must be measured consistently by the caller.
    This function makes no provider-performance claim.
    """
    if context_units < 0:
        raise ValueError("context_units must be non-negative.")
    if minimum_context_units < 0:
        raise ValueError("minimum_context_units must be non-negative.")

    normalized_operation = operation.strip().lower()
    normalized_sensitivity = sensitivity.strip().lower()
    normalized_risk = risk_level.strip().lower()
    policy = "delegation-guardrail-v1"

    if normalized_sensitivity == "high" or normalized_risk == "high":
        return DelegationDecision(
            allowed=False,
            execution_path="primary_route",
            worker_profile=None,
            reason="High-risk or high-sensitivity work is retained on the guarded primary route.",
            policy=policy,
        )
    if normalized_operation in PRIMARY_ONLY_OPERATIONS:
        return DelegationDecision(
            allowed=False,
            execution_path="primary_route",
            worker_profile=None,
            reason="This operation requires primary-route reasoning or exact local context.",
            policy=policy,
        )
    if normalized_operation not in DELEGABLE_OPERATIONS:
        return DelegationDecision(
            allowed=False,
            execution_path="primary_route",
            worker_profile=None,
            reason="The operation is not in the approved delegation allowlist.",
            policy=policy,
        )
    if context_units < minimum_context_units:
        return DelegationDecision(
            allowed=False,
            execution_path="primary_route",
            worker_profile=None,
            reason="The task is below the configured delegation threshold, so handoff overhead is not justified.",
            policy=policy,
        )
    if normalized_operation == "boilerplate_generation" and not reference_available:
        return DelegationDecision(
            allowed=False,
            execution_path="primary_route",
            worker_profile=None,
            reason="Boilerplate delegation requires a reference artifact to constrain the generated pattern.",
            policy=policy,
        )
    return DelegationDecision(
        allowed=True,
        execution_path="efficient_worker",
        worker_profile=(
            "bulk_context_worker"
            if normalized_operation == "bulk_context"
            else "pattern_constrained_writer"
        ),
        reason="The operation is allowlisted, low-risk, and large enough to justify a bounded worker handoff.",
        policy=policy,
    )
