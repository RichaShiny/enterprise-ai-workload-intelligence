# Enterprise AI Workload Intelligence

A simulation and evaluation framework for workload-aware routing of enterprise AI tasks across heterogeneous tools under cost, quality, reliability, latency, and sensitivity constraints.

Rather than assuming one model or tool should handle every enterprise workload, this project asks:

> **Given a specific workload and its operational requirements, which available AI tool should handle it?**

The framework simulates enterprise workloads, estimates potential outcomes across multiple AI tools, detects inefficient tool allocation, applies constraint-aware routing policies, and evaluates the resulting system under repeated simulation seeds.

## Motivation

Enterprise AI systems increasingly combine multiple execution options:

- frontier language models
- coding-specialized models
- smaller local models
- deterministic automation

These tools have different cost, latency, quality, reliability, and governance characteristics.

Routing every request to the most capable model can be expensive and unnecessary. Routing everything to the cheapest tool can reduce reliability.

This project explores the problem as a **workload allocation and decision-policy problem**.

The objective is not to identify one universally best model. It is to determine which tool is appropriate for each workload given its characteristics and operational constraints.

## System Overview

The framework follows this pipeline:

```text
Synthetic Enterprise Workloads
            |
            v
Observed Tool Allocation
            |
            v
Observability + Inefficiency Detection
            |
            v
Counterfactual Tool Simulation
            |
            v
Expected Outcome Estimation
            |
            v
Constraint-Aware Routing Policy
            |
            v
Baseline vs. Routed Evaluation
            |
            v
Multi-Seed Robustness Analysis
```

## Workload Representation

Each synthetic event represents an enterprise AI workload with characteristics including:

- department
- workflow
- task type
- complexity
- sensitivity
- business priority
- assigned tool
- model
- latency
- estimated cost
- human correction effort
- task success
- quality score

The simulated organization includes workloads from functions such as:

- engineering
- compliance
- finance
- sales
- support
- recruiting
- marketing

Task types include:

- coding
- reasoning
- retrieval
- summarization
- generation
- classification
- extraction

## Tool Portfolio

The simulated execution environment contains five tool classes:

| Tool | Intended role |
|---|---|
| ChatGPT | General-purpose frontier model |
| Claude | General-purpose frontier model |
| Codex | Coding-oriented model |
| Small local model | Lower-cost local inference |
| Deterministic automation | Non-LLM workflow execution |

Each tool has different simulated performance characteristics across task types, complexity levels, and sensitivity requirements.

## Observability

The first stage measures how the organization currently uses AI.

The framework tracks:

- total AI spend
- average task quality
- task success rate
- latency
- human corrections
- frontier-model usage
- tool utilization by department and task type

This creates an organization-level view of where AI resources are being consumed and where inefficient allocation may exist.

## Inefficiency Detection

The framework flags patterns such as:

- frontier models used for simple workloads
- coding-specialized tools used for mismatched tasks
- deterministic automation used where task complexity exceeds its capabilities
- expensive failed executions
- successful executions requiring substantial human correction

These signals are intended as diagnostic indicators rather than definitive judgments about individual tool calls.

## Counterfactual Tool Simulation

A core challenge in routing evaluation is that an observed workload only reveals the outcome of the tool that actually handled it.

To evaluate alternative routing decisions, the framework generates simulated potential outcomes for every workload-tool pair.

For each workload, outcomes are generated for:

```text
ChatGPT
Claude
Codex
Small local model
Deterministic automation
```

With 250 workloads and five tools, each experiment produces:

```text
250 × 5 = 1,250 potential outcomes
```

The simulated outcomes include:

- success probability
- expected quality
- expected latency
- expected human corrections
- estimated cost
- realized success
- realized quality
- realized latency
- realized human corrections

## Avoiding Outcome Leakage

An important evaluation correction was made during development.

A router should not select a tool using the realized outcome of that same decision. Doing so would allow the routing policy to effectively observe the future before choosing an action.

The corrected router therefore makes decisions using only **expected pre-decision quantities**, including:

```text
success_probability
expected_quality
expected_latency_ms
expected_corrections
estimated_cost_usd
```

Realized outcomes are retained only for downstream evaluation.

This separates:

```text
Decision information
        from
Evaluation outcomes
```

and prevents outcome leakage from artificially improving routing performance.

## Constraint-Aware Routing

For every workload, the router evaluates candidate tools against policy-specific constraints.

Constraints can include:

- minimum expected quality
- minimum success probability
- maximum expected latency
- maximum expected human corrections
- sensitivity restrictions
- tool eligibility

If multiple tools satisfy the constraints, the router chooses among the feasible candidates according to the policy objective.

If no tool satisfies all constraints, the system records:

```text
fallback_best_available
```

rather than pretending that the workload was successfully covered.

This makes **constraint coverage** an explicit system metric.

## Routing Policies

Four routing strategies are evaluated.

### Cost Optimized

Prioritizes economical execution while maintaining relatively permissive operational constraints.

### Balanced

Balances cost, reliability, quality, latency, and human correction requirements.

### Reliability First

Uses stronger reliability requirements and favors more capable tools when appropriate.

### Strict

Applies the strongest operational constraints.

The policies are not assumed to have a fixed ranking. Their behavior depends on whether the available tool portfolio can actually satisfy the requested constraints.

## Corrected Policy Trade-offs

A representative simulation produced:

| Policy | Cost reduction | Success rate | Avg. quality | Latency reduction | Correction reduction | Frontier usage | Constraint satisfaction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cost optimized | 42.8% | 92.8% | 0.871 | 21.4% | 24.8% | 26.4% | 77.6% |
| Balanced | 20.2% | 90.8% | 0.860 | 9.0% | 23.3% | 36.8% | 53.2% |
| Reliability first | 2.6% | 90.4% | 0.857 | -1.1% | 27.9% | 44.8% | 36.0% |
| Strict | 0.6% | 90.4% | 0.855 | -2.0% | 26.7% | 46.0% | 23.2% |

![Policy trade-offs](results/figures/policy_tradeoffs.png)

A key result is that **stricter constraints do not automatically produce better realized system outcomes**.

As requirements become harder to satisfy, fewer tools remain feasible. The router therefore falls back more frequently to the best available option.

This creates a coverage trade-off:

> Increasing policy strictness can increase fallback behavior when the available tool portfolio cannot satisfy the requested operating envelope.

## Multi-Seed Robustness

The balanced routing policy was evaluated across 10 independent simulation seeds.

| Metric | Mean | 95% CI | Min | Max |
|---|---:|---:|---:|---:|
| Cost reduction | 20.7% | 18.2% to 23.2% | 15.2% | 26.3% |
| Success improvement | +17.6 pp | +15.7 to +19.6 pp | +13.2 pp | +21.2 pp |
| Quality improvement | +0.084 | +0.075 to +0.093 | +0.059 | +0.096 |
| Latency reduction | 8.4% | 7.3% to 9.6% | 5.0% | 10.4% |
| Human correction reduction | 28.3% | 25.4% to 31.3% | 23.5% | 33.2% |
| Frontier usage change | -6.4 pp | -7.3 to -5.6 pp | -8.8 pp | -5.2 pp |
| Constraint satisfaction | 53.4% | 52.2% to 54.6% | 51.6% | 56.4% |

![Balanced routing impact](results/figures/routing_impact.png)

Across all tested seeds, the balanced router reduced simulated cost while improving realized success and quality relative to the baseline allocation.

The effect therefore does not depend on a single random seed.

## Where Routing Breaks Down

Constraint failures are not evenly distributed across workloads.

For the analyzed balanced-policy run:

| Workload characteristic | Low | Medium | High |
|---|---:|---:|---:|
| Complexity fallback rate | 27.2% | 34.0% | 89.3% |
| Sensitivity fallback rate | 25.0% | 35.6% | 78.3% |

![Constraint failures](results/figures/constraint_failures.png)

High-complexity and high-sensitivity workloads are substantially more difficult for the simulated tool portfolio to cover.

This suggests that routing optimization alone cannot solve every workload allocation problem.

Sometimes the limiting factor is the **capability frontier of the available tools**, not the routing policy.

## Key Findings

### 1. Workload-aware routing can outperform static allocation

Across 10 simulation seeds, the balanced routing policy reduced simulated cost by an average of **20.7%** while increasing task success by **17.6 percentage points**.

### 2. Improvements extend beyond cost

The balanced policy also produced:

- **8.4% lower latency**
- **28.3% fewer human corrections**
- **0.084 higher average quality**
- **6.4 percentage-point lower frontier-model usage**

### 3. More restrictive policies are not necessarily better

Increasing policy strictness reduced the number of workloads for which the available tool portfolio could satisfy every requirement.

### 4. Workload difficulty matters

High-complexity and high-sensitivity workloads accounted for disproportionately high fallback rates.

### 5. Routing is a portfolio problem

The results suggest that enterprise AI optimization involves both:

```text
better routing
+
better tool coverage
```

A sophisticated router cannot compensate indefinitely for missing capabilities in the underlying tool portfolio.

## Reproducing the Experiments

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the synthetic workload dataset:

```bash
python -m src.workloads.generate_synthetic
```

Run observability analysis:

```bash
python -m src.evaluation.observability
```

Run inefficiency detection:

```bash
python -m src.evaluation.inefficiency
```

Generate counterfactual outcomes:

```bash
python -m src.simulation.counterfactuals
```

Run the balanced routing policy:

```bash
python -m src.routing.policy
```

Compare baseline and routed outcomes:

```bash
python -m src.simulation.compare_policies
```

Analyze constraint failures:

```bash
python -m src.evaluation.constraint_failures
```

Evaluate policy trade-offs:

```bash
python -m experiments.policy_tradeoffs
```

Run the multi-seed robustness experiment:

```bash
python -m experiments.multi_seed
```

Generate figures:

```bash
python -m src.visualization.routing_impact
python -m src.visualization.policy_tradeoffs
python -m src.visualization.constraint_failures
```

## Project Structure

```text
enterprise-ai-workload-intelligence/
├── experiments/
│   ├── multi_seed.py
│   └── policy_tradeoffs.py
│
├── results/
│   └── figures/
│       ├── constraint_failures.png
│       ├── policy_tradeoffs.png
│       └── routing_impact.png
│
├── src/
│   ├── evaluation/
│   │   ├── constraint_failures.py
│   │   ├── inefficiency.py
│   │   └── observability.py
│   │
│   ├── routing/
│   │   └── policy.py
│   │
│   ├── simulation/
│   │   ├── compare_policies.py
│   │   └── counterfactuals.py
│   │
│   ├── visualization/
│   │   ├── constraint_failures.py
│   │   ├── policy_tradeoffs.py
│   │   └── routing_impact.py
│   │
│   └── workloads/
│       ├── generate_synthetic.py
│       └── schema.py
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Limitations

This project is a **simulation framework**, not a production benchmark of ChatGPT, Claude, Codex, or any other model.

Tool behavior, cost, latency, quality, and reliability are synthetically generated according to assumptions encoded in the simulation.

Therefore, results such as the 20.7% average cost reduction should be interpreted as evidence about the behavior of the routing framework **within the simulated environment**, not as expected savings from deploying the system in a real organization.

The counterfactual outcomes are also simulated rather than observed from repeated execution of identical tasks across real models.

A production extension would replace the simulator with telemetry from actual enterprise AI workloads and empirical model evaluations.

## Future Work

Potential extensions include:

- calibration from real production telemetry
- learned routing policies
- contextual bandits for adaptive tool selection
- uncertainty-aware routing
- workload-specific model benchmarking
- budget-aware optimization
- dynamic model pricing
- queue and capacity constraints
- privacy and data-residency policies
- human escalation policies
- online monitoring for routing drift

## Why This Project Matters

Enterprise AI infrastructure is increasingly becoming a heterogeneous system rather than a single-model application.

The operational question is therefore shifting from:

> **Which model is best?**

to:

> **Which model, tool, or workflow should handle this task under the organization's actual constraints?**

This project provides a small experimental framework for studying that question.