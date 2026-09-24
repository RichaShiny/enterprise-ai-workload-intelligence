import pytest

from src.execution.delegation_policy import evaluate_delegation_policy


def test_large_low_risk_bulk_context_is_delegable():
    decision = evaluate_delegation_policy(
        operation="bulk_context", context_units=12_000,
        sensitivity="medium", risk_level="low",
    )

    assert decision.allowed is True
    assert decision.execution_path == "efficient_worker"
    assert decision.worker_profile == "bulk_context_worker"


@pytest.mark.parametrize("operation", ["debugging", "architecture", "targeted_edit"])
def test_reasoning_and_exact_context_operations_remain_primary(operation):
    decision = evaluate_delegation_policy(
        operation=operation, context_units=50_000,
        sensitivity="low", risk_level="low",
    )

    assert decision.allowed is False
    assert decision.execution_path == "primary_route"


def test_high_sensitivity_cannot_be_delegated_even_when_large():
    decision = evaluate_delegation_policy(
        operation="bulk_context", context_units=50_000,
        sensitivity="high", risk_level="low",
    )

    assert decision.allowed is False
    assert "High-risk" in decision.reason


def test_boilerplate_delegation_requires_reference_artifact():
    decision = evaluate_delegation_policy(
        operation="boilerplate_generation", context_units=12_000,
        sensitivity="low", risk_level="low", reference_available=False,
    )

    assert decision.allowed is False
    assert "reference artifact" in decision.reason
