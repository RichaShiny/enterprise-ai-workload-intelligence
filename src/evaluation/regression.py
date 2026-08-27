from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RegressionResult:
    passed: bool
    regressions: List[str]
    improvements: List[str]
    unchanged: List[str]


class RegressionEvaluator:
    def __init__(
        self,
        default_tolerance: float = 0.02,
        metric_tolerances: Optional[
            Dict[str, float]
        ] = None,
    ):
        self.default_tolerance = (
            default_tolerance
        )

        self.metric_tolerances = (
            metric_tolerances or {}
        )

    def compare(
        self,
        baseline: Dict[str, float],
        candidate: Dict[str, float],
        higher_is_better: Dict[str, bool],
    ) -> RegressionResult:
        regressions = []
        improvements = []
        unchanged = []

        for metric, baseline_value in baseline.items():
            if metric not in candidate:
                raise ValueError(
                    f"Candidate is missing metric: {metric}"
                )

            candidate_value = candidate[metric]

            tolerance = self.metric_tolerances.get(
                metric,
                self.default_tolerance,
            )

            difference = (
                candidate_value
                - baseline_value
            )

            if not higher_is_better.get(
                metric,
                True,
            ):
                difference = -difference

            if difference < -tolerance:
                regressions.append(metric)

            elif difference > tolerance:
                improvements.append(metric)

            else:
                unchanged.append(metric)

        return RegressionResult(
            passed=len(regressions) == 0,
            regressions=regressions,
            improvements=improvements,
            unchanged=unchanged,
        )