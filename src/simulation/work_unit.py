from dataclasses import dataclass


@dataclass
class WorkUnit:
    workload_id: str
    task_type: str
    complexity: float
    sensitivity: str
    business_value: float
    failure_cost: float
    escalation_cost: float = 0.0


@dataclass
class ModelProfile:
    name: str
    cost_per_attempt: float
    success_probability: float
    latency_ms: float
    quality: float


@dataclass
class CompletionEstimate:
    strategy: str
    expected_cost: float
    expected_latency_ms: float
    success_probability: float
    expected_failure_cost: float
    expected_total_cost: float


def direct_route(
    work_unit: WorkUnit,
    model: ModelProfile,
) -> CompletionEstimate:
    failure_probability = 1.0 - model.success_probability

    expected_failure_cost = (
        failure_probability * work_unit.failure_cost
    )

    return CompletionEstimate(
        strategy=f"direct:{model.name}",
        expected_cost=model.cost_per_attempt,
        expected_latency_ms=model.latency_ms,
        success_probability=model.success_probability,
        expected_failure_cost=expected_failure_cost,
        expected_total_cost=(
            model.cost_per_attempt + expected_failure_cost
        ),
    )


def cascade_route(
    work_unit: WorkUnit,
    first_model: ModelProfile,
    fallback_model: ModelProfile,
) -> CompletionEstimate:
    first_failure_probability = (
        1.0 - first_model.success_probability
    )

    cascade_success_probability = (
        first_model.success_probability
        + first_failure_probability
        * fallback_model.success_probability
    )

    expected_escalation_cost = (
        first_failure_probability
        * work_unit.escalation_cost
    )

    expected_cost = (
        first_model.cost_per_attempt
        + first_failure_probability
        * fallback_model.cost_per_attempt
        + expected_escalation_cost
    )

    expected_latency_ms = (
        first_model.latency_ms
        + first_failure_probability
        * fallback_model.latency_ms
    )

    final_failure_probability = (
        first_failure_probability
        * (1.0 - fallback_model.success_probability)
    )

    expected_failure_cost = (
        final_failure_probability * work_unit.failure_cost
    )

    expected_total_cost = (
        expected_cost + expected_failure_cost
    )

    return CompletionEstimate(
        strategy=(
            f"cascade:{first_model.name}"
            f"->{fallback_model.name}"
        ),
        expected_cost=expected_cost,
        expected_latency_ms=expected_latency_ms,
        success_probability=cascade_success_probability,
        expected_failure_cost=expected_failure_cost,
        expected_total_cost=expected_total_cost,
    )