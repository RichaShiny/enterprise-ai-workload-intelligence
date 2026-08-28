import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error


SEED = 42
rng = np.random.default_rng(SEED)


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def generate_observational_data(n=5000):
    complexity = rng.uniform(0, 1, n)
    sensitivity = rng.binomial(1, 0.35, n)
    business_priority = rng.uniform(0, 1, n)

    baseline_success_prob = (
        0.88
        - 0.30 * complexity
        - 0.08 * sensitivity
        + 0.05 * business_priority
    )

    treatment_effect = (
        0.03
        + 0.18 * complexity
        + 0.08 * sensitivity
    )

    treatment_effect = np.clip(treatment_effect, 0, 0.30)

    propensity_logit = (
        -1.5
        + 3.0 * complexity
        + 1.5 * sensitivity
        + 0.5 * business_priority
    )

    true_propensity = sigmoid(propensity_logit)
    treatment = rng.binomial(1, true_propensity)

    control_prob = np.clip(baseline_success_prob, 0.05, 0.95)
    treatment_prob = np.clip(
        baseline_success_prob + treatment_effect,
        0.05,
        0.98,
    )

    observed_prob = np.where(
        treatment == 1,
        treatment_prob,
        control_prob,
    )

    outcome = rng.binomial(1, observed_prob)

    df = pd.DataFrame(
        {
            "complexity": complexity,
            "sensitivity": sensitivity,
            "business_priority": business_priority,
            "treatment": treatment,
            "outcome": outcome,
            "true_propensity": true_propensity,
            "true_treatment_effect": treatment_effect,
            "control_prob": control_prob,
            "treatment_prob": treatment_prob,
        }
    )

    return df


def naive_difference(df):
    treated = df.loc[df["treatment"] == 1, "outcome"].mean()
    control = df.loc[df["treatment"] == 0, "outcome"].mean()
    return treated - control


def estimate_propensity(df, features):
    model = LogisticRegression(max_iter=1000)

    model.fit(df[features], df["treatment"])

    propensity = model.predict_proba(df[features])[:, 1]

    return np.clip(propensity, 0.02, 0.98)


def ipw_ate(df, propensity):
    t = df["treatment"].to_numpy()
    y = df["outcome"].to_numpy()

    treated_term = t * y / propensity
    control_term = (1 - t) * y / (1 - propensity)

    return np.mean(treated_term - control_term)


def doubly_robust_ate(df, propensity, features):
    treated_df = df[df["treatment"] == 1]
    control_df = df[df["treatment"] == 0]

    model_treated = RandomForestRegressor(
        n_estimators=200,
        random_state=SEED,
        min_samples_leaf=20,
    )

    model_control = RandomForestRegressor(
        n_estimators=200,
        random_state=SEED,
        min_samples_leaf=20,
    )

    model_treated.fit(
        treated_df[features],
        treated_df["outcome"],
    )

    model_control.fit(
        control_df[features],
        control_df["outcome"],
    )

    mu1 = model_treated.predict(df[features])
    mu0 = model_control.predict(df[features])

    t = df["treatment"].to_numpy()
    y = df["outcome"].to_numpy()

    dr_score = (
        mu1
        - mu0
        + t * (y - mu1) / propensity
        - (1 - t) * (y - mu0) / (1 - propensity)
    )

    return dr_score.mean()


def double_ml_ate(df, features, n_splits=5):
    kf = KFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=SEED,
    )

    residual_y = np.zeros(len(df))
    residual_t = np.zeros(len(df))

    for train_idx, test_idx in kf.split(df):
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]

        outcome_model = RandomForestRegressor(
            n_estimators=200,
            random_state=SEED,
            min_samples_leaf=20,
        )

        treatment_model = LogisticRegression(
            max_iter=1000,
        )

        outcome_model.fit(
            train[features],
            train["outcome"],
        )

        treatment_model.fit(
            train[features],
            train["treatment"],
        )

        y_hat = outcome_model.predict(test[features])
        t_hat = treatment_model.predict_proba(
            test[features]
        )[:, 1]

        residual_y[test_idx] = (
            test["outcome"].to_numpy() - y_hat
        )

        residual_t[test_idx] = (
            test["treatment"].to_numpy() - t_hat
        )

    final_model = LinearRegression(
        fit_intercept=False
    )

    final_model.fit(
        residual_t.reshape(-1, 1),
        residual_y,
    )

    return final_model.coef_[0]


def heterogeneous_effects(df):
    df = df.copy()

    df["complexity_group"] = pd.cut(
        df["complexity"],
        bins=[0, 0.33, 0.66, 1.0],
        labels=["low", "medium", "high"],
        include_lowest=True,
    )

    grouped = (
        df.groupby(
            "complexity_group",
            observed=False,
        )["true_treatment_effect"]
        .mean()
        .reset_index()
    )

    return grouped


def main():
    df = generate_observational_data()

    features = [
        "complexity",
        "sensitivity",
        "business_priority",
    ]

    true_ate = df["true_treatment_effect"].mean()

    naive = naive_difference(df)

    propensity = estimate_propensity(
        df,
        features,
    )

    ipw = ipw_ate(
        df,
        propensity,
    )

    dr = doubly_robust_ate(
        df,
        propensity,
        features,
    )

    dml = double_ml_ate(
        df,
        features,
    )

    print("Observational Routing Causal Experiment")
    print()

    print(f"Sample size: {len(df)}")
    print(
        f"Treatment rate: "
        f"{df['treatment'].mean():.3f}"
    )

    print()

    print(
        f"Known simulated ATE: "
        f"{true_ate:.4f}"
    )

    print(
        f"Naive observational difference: "
        f"{naive:.4f}"
    )

    print(
        f"IPW estimate: "
        f"{ipw:.4f}"
    )

    print(
        f"Doubly robust estimate: "
        f"{dr:.4f}"
    )

    print(
        f"Double ML estimate: "
        f"{dml:.4f}"
    )

    print()

    print("Absolute estimation error")

    estimates = {
        "naive": naive,
        "ipw": ipw,
        "doubly_robust": dr,
        "double_ml": dml,
    }

    for name, estimate in estimates.items():
        error = abs(
            estimate - true_ate
        )

        print(
            f"{name}: "
            f"{error:.4f}"
        )

    print()

    print(
        "True treatment effect by "
        "complexity group"
    )

    print(
        heterogeneous_effects(df).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()