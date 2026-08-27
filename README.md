# Enterprise AI Workload Intelligence

A simulation and evaluation framework for workload-aware routing of enterprise AI tasks across heterogeneous tools under cost, quality, reliability, latency, and sensitivity constraints.

Rather than assuming one model or tool should handle every enterprise workload, this project asks:

> **Given a specific workload and its operational requirements, which available AI tool should handle it?**

The framework simulates enterprise workloads, estimates potential outcomes across multiple AI tools, detects inefficient tool allocation, applies constraint-aware routing policies, and evaluates the resulting system under repeated simulation seeds.

It also explores retrieval and semantic reranking, faithfulness evaluation, regression testing, workload-classifier fine-tuning, randomized experimentation, and production-oriented deployment reasoning.

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

The framework follows this conceptual pipeline:

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
Constraint-Aware Routing
            |
            v
Context Retrieval
            |
            v
Semantic Reranking
            |
            v
Model / Tool Execution
            |
            v
Faithfulness + Quality Evaluation
            |
            v
Regression Gates
            |
            v
Offline / A-B Evaluation
            |
            v
Production Monitoring + Fallbacks
```

The core simulation studies routing behavior. Additional modules explore how retrieval, evaluation, fine-tuning, experimentation, and production safeguards would fit around that routing layer.

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

The effect therefore does not depend on a single random seed within the simulated environment.

## Retrieval and Semantic Reranking

The framework includes a small retrieval benchmark for studying how enterprise context can be selected before model execution.

The first-stage retriever uses TF-IDF lexical retrieval with unigram and bigram features. Retrieved candidates are then reranked using semantic embeddings from `all-MiniLM-L6-v2`.

The benchmark deliberately includes queries with lexical ambiguity to test whether semantic reranking can improve the ordering of retrieved candidates.

On the current five-query diagnostic benchmark:

| Metric | Lexical retrieval | Semantic reranking |
|---|---:|---:|
| Recall@3 | 1.000 | 1.000 |
| Precision@3 | 0.333 | 0.333 |
| MRR | 0.800 | 1.000 |
| Hit Rate@3 | 1.000 | 1.000 |

The semantic reranker moved the relevant document to rank one for the ambiguous cases, increasing MRR while retrieval coverage remained unchanged.

The benchmark is intentionally small and synthetic. The result demonstrates the behavior of the retrieval/reranking pipeline rather than establishing a generalized performance improvement.

## Faithfulness Evaluation

Retrieval quality does not guarantee that a generated answer is supported by the retrieved evidence.

The project therefore evaluates faithfulness separately.

An initial evaluator used embedding similarity to identify whether claims were supported by context. An adversarial example exposed an important failure mode: a claim could be semantically similar to the evidence while directly contradicting it.

For example, evidence describing frontier models as having higher latency could still be semantically close to a claim stating that frontier models always have lower latency.

The evaluator was therefore extended into two stages:

```text
Claim
  |
  v
Semantic Candidate Matching
  |
  v
Natural Language Inference
  |
  +--> Entailment
  +--> Neutral
  +--> Contradiction
```

The implementation uses semantic similarity for candidate evidence selection and an NLI model for entailment and contradiction detection.

This separates two different questions:

1. Is this evidence relevant to the claim?
2. Does the evidence actually support the claim?

The adversarial contradiction that passed the similarity-only evaluator is rejected by the NLI-enhanced evaluator.

## Regression Testing

AI-system changes can improve one metric while silently degrading another.

The project therefore includes a regression gate that compares candidate configurations against a known baseline across:

- task success
- quality
- faithfulness
- latency
- cost per request

Rather than applying one absolute tolerance to every metric, the evaluator supports metric-specific tolerances.

For example:

```text
task_success       0.02
quality            0.02
faithfulness       0.01
latency_ms         100
cost_per_request   0.002
```

This matters because a tolerance meaningful for a normalized quality score is not meaningful for milliseconds or dollar-denominated cost.

A candidate can therefore improve success, quality, and cost while still being blocked if a critical metric such as faithfulness regresses.

In the diagnostic regression suite, one candidate is rejected specifically because faithfulness declines despite improvements on several other dimensions, while another candidate passes after improving all tracked metrics beyond their configured tolerances.

The tolerance values in the repository are illustrative. In production they would be derived from service-level requirements, business risk, and empirical metric variance.

## Fine-Tuning Experiment

The repository includes a small transfer-learning experiment using `distilbert-base-uncased` for enterprise workload classification.

The classifier predicts four workload categories:

- general
- sensitive
- technical
- retrieval

The training set contains deliberately small synthetic examples so the experiment remains lightweight and reproducible locally.

A harder held-out diagnostic set contains overlapping categories such as:

- sensitive + retrieval
- technical + retrieval
- general + technical
- sensitive + summarization

Results:

| Metric | Pretrained baseline | Fine-tuned |
|---|---:|---:|
| Accuracy | 0.250 | 0.688 |
| Macro F1 | 0.105 | 0.657 |

Per-class evaluation showed that technical workloads were easiest to identify, while general workloads were more frequently confused with technical tasks.

Sensitive-workload classification showed:

```text
Precision: 1.00
Recall:    0.60
F1:        0.75
```

This is operationally important because false negatives for sensitive workloads may be more costly than ordinary classification errors.

### Confidence-Aware Evaluation

The experiment also evaluates maximum predicted probability as a confidence signal.

Average maximum-class confidence on the held-out set was:

```text
0.418
```

Using a naive confidence threshold of `0.65` would escalate all 16 held-out examples.

This demonstrates an important distinction:

> Better classification accuracy does not imply well-calibrated confidence.

The threshold was intentionally not tuned against the test set to manufacture a better escalation rate.

A production implementation would use separate validation data for threshold selection and would evaluate probability calibration before relying on confidence for routing or abstention.

This experiment demonstrates the fine-tuning and evaluation workflow. It is not intended as evidence of production-level classifier performance.

## Simulated A/B Experimentation

Offline evaluation is useful, but routing policies ultimately need to be evaluated against user or business outcomes.

The project therefore includes a simulated randomized A/B experiment comparing:

```text
Control:
baseline routing policy

Treatment:
workload-aware routing policy
```

Task success is treated as the primary outcome.

Guardrails include:

- cost per request
- latency
- faithfulness
- human correction rate

A representative simulated experiment with 2,000 assignments produced:

| Metric | Control | Treatment | Change |
|---|---:|---:|---:|
| Task success | 0.833 | 0.880 | +0.048 |
| Cost/request | $0.024 | $0.019 | -$0.005 |
| Latency | 1450 ms | 1311 ms | -139 ms |
| Faithfulness | 0.909 | 0.920 | +0.011 |
| Human correction rate | 0.204 | 0.148 | -0.057 |

The simulated task-success lift was approximately:

```text
+4.8 percentage points
```

with a 95% confidence interval of approximately:

```text
+1.7 to +7.8 percentage points
```

Because treatment and control outcomes are generated from assumed distributions, these results are **not empirical evidence that the router caused a 4.8-point improvement**.

The experiment demonstrates the randomized evaluation and analysis framework that could be applied to real production traffic.

## Production Architecture

The repository includes a production-oriented design for extending the offline framework into an enterprise AI execution system.

The proposed request path is:

```text
Request Intake
      |
      v
Workload Classification
      |
      v
Context Retrieval
      |
      v
Semantic Reranking
      |
      v
Constraint-Aware Routing
      |
      v
Model / Tool Execution
      |
      v
Faithfulness + Quality Evaluation
      |
      v
Response / Human Escalation
      |
      v
Telemetry + Monitoring
```

### Failure Handling

The architecture explicitly considers:

- retrieval failure
- low classifier confidence
- unavailable eligible tools
- provider timeouts
- provider outages
- faithfulness failures
- sensitivity restrictions

Low-confidence or unsupported decisions can be escalated rather than forcing the system to return a result.

Provider failures can trigger retries, alternate eligible providers, or circuit breakers.

### Deployment Strategy

A new routing policy would first run in **shadow mode**, allowing its decisions to be compared against the active system without affecting user responses.

If offline evaluation and shadow testing pass regression gates, the policy can move through:

```text
Offline Evaluation
        |
        v
Shadow Mode
        |
        v
Canary Release
        |
        v
Randomized A/B Test
        |
        v
Gradual Rollout
```

Task success can serve as a primary outcome while faithfulness, latency, cost, human correction, and sensitive-data violations act as guardrails.

### Versioning and Rollback

Production decisions depend on more than model version alone.

The design therefore assumes versioning for:

- routing policies
- models
- prompts
- retrievers
- rerankers
- evaluation configurations

A detected regression can roll traffic back to a known-good configuration.

The complete design is documented in:

```text
docs/production_architecture.md
```

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

### 1. Workload-aware routing can outperform static allocation within the simulation

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

### 6. Retrieval coverage and ranking quality are different

The retrieval benchmark maintained perfect Recall@3 while semantic reranking improved MRR from 0.800 to 1.000.

The retriever had already found the relevant documents. The remaining problem was ordering them correctly.

### 7. Semantic similarity is not faithfulness

Embedding similarity can identify related evidence without establishing whether the evidence entails or contradicts a claim.

Faithfulness evaluation therefore requires stronger checks than semantic proximity alone.

### 8. AI regressions are multidimensional

A candidate configuration should not be considered better simply because an aggregate score improves.

Critical dimensions such as faithfulness, latency, cost, and sensitive-data handling require independent guardrails.

### 9. Fine-tuning and calibration solve different problems

Fine-tuning substantially improved workload classification on the diagnostic dataset, but confidence remained low.

Production systems therefore need explicit calibration and abstention strategies rather than assuming prediction confidence is trustworthy.

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

### Core routing simulation

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

### Retrieval benchmark

```bash
python -m experiments.retrieval_benchmark
```

### Faithfulness benchmark

```bash
python -m experiments.faithfulness_benchmark
```

### Regression suite

```bash
python -m experiments.regression_suite
```

### Fine-tuning experiment

```bash
python -m experiments.train_fine_tuned_model
```

### Fine-tuning strategy benchmark

```bash
python -m experiments.fine_tuning_benchmark
```

### Simulated A/B experiment

```bash
python -m experiments.ab_routing_experiment
```

### Generate figures

```bash
python -m src.visualization.routing_impact
python -m src.visualization.policy_tradeoffs
python -m src.visualization.constraint_failures
```

## Project Structure

```text
enterprise-ai-workload-intelligence/
│
├── data/
│   └── fine_tuning/
│       ├── train.jsonl
│       └── test.jsonl
│
├── docs/
│   └── production_architecture.md
│
├── experiments/
│   ├── ab_routing_experiment.py
│   ├── faithfulness_benchmark.py
│   ├── fine_tuning_benchmark.py
│   ├── multi_seed.py
│   ├── policy_tradeoffs.py
│   ├── regression_suite.py
│   ├── retrieval_benchmark.py
│   └── train_fine_tuned_model.py
│
├── results/
│   └── figures/
│       ├── constraint_failures.png
│       ├── policy_tradeoffs.png
│       └── routing_impact.png
│
├── src/
│   ├── evaluation/
│   │   ├── ab_experiment.py
│   │   ├── constraint_failures.py
│   │   ├── faithfulness.py
│   │   ├── inefficiency.py
│   │   ├── observability.py
│   │   ├── regression.py
│   │   └── retrieval_eval.py
│   │
│   ├── models/
│   │   └── fine_tuning.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── index.py
│   │   └── ranker.py
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

This project is a **simulation and evaluation framework**, not a production benchmark of ChatGPT, Claude, Codex, or any other model.

Tool behavior, cost, latency, quality, and reliability in the routing experiments are synthetically generated according to assumptions encoded in the simulation.

Therefore, results such as the 20.7% average cost reduction should be interpreted as evidence about the behavior of the routing framework **within the simulated environment**, not as expected savings from deploying the system in a real organization.

The counterfactual outcomes are simulated rather than observed from repeated execution of identical tasks across real models.

The A/B experiment is also simulated. Its treatment effect is generated from assumed outcome distributions and should not be interpreted as an empirically measured causal effect.

The retrieval benchmark contains only five synthetic diagnostic queries. Its MRR improvement demonstrates the behavior of the reranking implementation but does not establish generalized retrieval performance.

The fine-tuning experiment uses a very small synthetic training and held-out dataset. Its results demonstrate the transfer-learning and evaluation workflow rather than production-level generalization.

The confidence thresholds included in the experiment are illustrative and have not been calibrated on an independent validation set.

The regression tolerances are also illustrative. Production thresholds should be tied to empirical variance, service-level requirements, and business risk.

A production extension would replace simulated outcomes with telemetry from actual enterprise AI workloads and empirical model evaluations.

## Future Work

Potential extensions include:

- calibration from real production telemetry
- larger and independently labeled retrieval benchmarks
- dense first-stage retrieval
- learned hybrid lexical-dense retrieval
- retrieval evaluation with nDCG and larger relevance sets
- probability calibration using a dedicated validation split
- workload-specific abstention thresholds
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
- empirical shadow-mode evaluation
- production A/B experimentation

## Why This Project Matters

Enterprise AI infrastructure is increasingly becoming a heterogeneous system rather than a single-model application.

The operational question is therefore shifting from:

> **Which model is best?**

to:

> **Which model, tool, or workflow should handle this task under the organization's actual constraints?**

That decision cannot be made from model quality alone.

It depends on workload characteristics, organizational context, retrieval quality, sensitivity, cost, latency, reliability, confidence, and the consequences of failure.

This project provides an experimental framework for studying those decisions across the lifecycle from workload characterization and routing through retrieval, evaluation, experimentation, and production safeguards.