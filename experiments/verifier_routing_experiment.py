from dataclasses import dataclass


@dataclass
class VerifierResult:
    sensitivity: float
    specificity: float
    accepted_bad_rate: float
    escalation_rate: float
    final_success_probability: float
    expected_inference_cost: float
    expected_verification_cost: float
    expected_failure_cost: float
    expected_total_cost: float
    expected_escalation_cost: float


def evaluate_verified_cascade(
    small_success: float,
    frontier_success: float,
    small_cost: float,
    frontier_cost: float,
    failure_cost: float,
    escalation_cost: float,
    verifier_sensitivity: float,
    verifier_specificity: float,
    verifier_cost: float,
):
    """
    sensitivity:
        P(verifier flags response | small model actually failed)

    specificity:
        P(verifier accepts response | small model actually succeeded)
    """

    small_failure = 1.0 - small_success

    true_positive = (
        small_failure * verifier_sensitivity
    )

    false_negative = (
        small_failure * (1.0 - verifier_sensitivity)
    )

    false_positive = (
        small_success * (1.0 - verifier_specificity)
    )

    escalation_rate = true_positive + false_positive

    # A false negative means a bad small-model response is accepted.
    # If escalation happens, the frontier model gets another chance.
    final_failure_probability = (
        false_negative
        + escalation_rate * (1.0 - frontier_success)
    )

    final_success_probability = (
        1.0 - final_failure_probability
    )

    expected_escalation_cost = (
        escalation_rate * escalation_cost
    )

    expected_inference_cost = (
    small_cost
    + escalation_rate * frontier_cost
    )

    expected_failure_cost = (
        final_failure_probability * failure_cost
    )

    expected_total_cost = (
        expected_inference_cost
        + expected_escalation_cost
        + verifier_cost
        + expected_failure_cost
    )

    return VerifierResult(
        sensitivity=verifier_sensitivity,
        specificity=verifier_specificity,
        accepted_bad_rate=false_negative,
        escalation_rate=escalation_rate,
        final_success_probability=final_success_probability,
        expected_inference_cost=expected_inference_cost,
        expected_verification_cost=verifier_cost,
        expected_failure_cost=expected_failure_cost,
        expected_total_cost=expected_total_cost,
        expected_escalation_cost=expected_escalation_cost,
    )


def main():
    workloads = [
        {
            "name": "summarization",
            "small_success": 0.90,
            "frontier_success": 0.97,
            "failure_cost": 0.01,
            "escalation_cost": 0.002,
        },
        {
            "name": "technical_reasoning",
            "small_success": 0.68,
            "frontier_success": 0.95,
            "failure_cost": 0.10,
            "escalation_cost": 0.02,
        },
        {
            "name": "compliance",
            "small_success": 0.55,
            "frontier_success": 0.96,
            "failure_cost": 1.00,
            "escalation_cost": 0.20,
        },
    ]

    verifier_profiles = [
        ("weak", 0.70, 0.90),
        ("moderate", 0.85, 0.95),
        ("strong", 0.95, 0.98),
    ]

    small_cost = 0.004
    frontier_cost = 0.018
    verifier_cost = 0.002

    for workload in workloads:
        print("\n" + "=" * 72)
        print(f"Workload: {workload['name']}")

        for name, sensitivity, specificity in verifier_profiles:
            result = evaluate_verified_cascade(
                small_success=workload["small_success"],
                frontier_success=workload["frontier_success"],
                small_cost=small_cost,
                frontier_cost=frontier_cost,
                failure_cost=workload["failure_cost"],
                escalation_cost=workload["escalation_cost"],
                verifier_sensitivity=sensitivity,
                verifier_specificity=specificity,
                verifier_cost=verifier_cost,
            )

            print(f"\nVerifier: {name}")
            print(
                f"Sensitivity / specificity: "
                f"{sensitivity:.2f} / {specificity:.2f}"
            )
            print(
                f"Accepted bad-response rate: "
                f"{result.accepted_bad_rate:.3f}"
            )
            print(
                f"Escalation rate: "
                f"{result.escalation_rate:.3f}"
            )
            print(
                f"Final success probability: "
                f"{result.final_success_probability:.3f}"
            )
            print(
                f"Expected inference cost: "
                f"${result.expected_inference_cost:.4f}"
            )
            print(
                f"Expected escalation cost: "
                f"${result.expected_escalation_cost:.4f}"
            )
            print(
                f"Expected verification cost: "
                f"${result.expected_verification_cost:.4f}"
            )
            print(
                f"Expected failure cost: "
                f"${result.expected_failure_cost:.4f}"
            )
            print(
                f"Expected total cost: "
                f"${result.expected_total_cost:.4f}"
            )


if __name__ == "__main__":
    main()