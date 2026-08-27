from dataclasses import dataclass

import numpy as np


@dataclass
class ExperimentResult:
    control_mean: float
    treatment_mean: float
    absolute_lift: float
    relative_lift: float
    standard_error: float
    ci_lower: float
    ci_upper: float


def analyze_binary_experiment(
    control,
    treatment,
    confidence_z=1.96,
):
    control = np.asarray(control, dtype=float)
    treatment = np.asarray(treatment, dtype=float)

    control_mean = control.mean()
    treatment_mean = treatment.mean()

    absolute_lift = (
        treatment_mean - control_mean
    )

    relative_lift = (
        absolute_lift / control_mean
        if control_mean != 0
        else np.nan
    )

    control_variance = (
        control_mean
        * (1 - control_mean)
        / len(control)
    )

    treatment_variance = (
        treatment_mean
        * (1 - treatment_mean)
        / len(treatment)
    )

    standard_error = np.sqrt(
        control_variance
        + treatment_variance
    )

    margin = confidence_z * standard_error

    return ExperimentResult(
        control_mean=control_mean,
        treatment_mean=treatment_mean,
        absolute_lift=absolute_lift,
        relative_lift=relative_lift,
        standard_error=standard_error,
        ci_lower=absolute_lift - margin,
        ci_upper=absolute_lift + margin,
    )