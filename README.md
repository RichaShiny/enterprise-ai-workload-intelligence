# Enterprise AI Workload Intelligence

A simulation and evaluation framework for workload-aware routing of enterprise AI tasks across heterogeneous tools under cost, quality, reliability, latency, sensitivity, verification, and failure-risk constraints.

Rather than assuming one model or tool should handle every enterprise workload, this project asks:

> **Given a specific workload and its operational requirements, which available AI tool should handle it?**

The framework extends that question one step further:

> **When should an enterprise AI system use a cheaper model first and escalate, and when is it more efficient or safer to route directly to a stronger model?**

The framework simulates enterprise workloads, estimates potential outcomes across multiple AI tools, detects inefficient tool allocation, applies constraint-aware routing policies, and evaluates the resulting system under repeated simulation seeds.

It also explores Work-Unit-aware routing, failure and escalation economics, uncertainty-aware routing, imperfect verification, retrieval and semantic reranking, faithfulness evaluation, regression testing, workload-classifier fine-tuning, randomized experimentation, and production-oriented deployment reasoning.

---

## Motivation

Enterprise AI systems increasingly combine multiple execution options:

- frontier language models
- coding-specialized models
- smaller local models
- deterministic automation

These tools have different cost, latency, quality, reliability, and governance characteristics.

Routing every request to the most capable model can be expensive and unnecessary. Routing everything to the cheapest tool can reduce reliability.

There is also a deeper economic problem: **the cheapest model call is not necessarily the cheapest completed task**.

A cheaper model may create additional cost through:

- failed attempts
- retries
- escalation to stronger models
- verification
- human intervention
- additional latency
- downstream business failures

This project therefore explores enterprise AI routing as a **workload allocation and decision-policy problem**.

The objective is not to identify one universally best model. It is to determine which tool or execution strategy is appropriate for each workload given its characteristics, operational constraints, and consequences of failure.

---

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
Work-Unit / Failure-Aware Routing
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
Verification + Faithfulness Evaluation
            |
      +-----+------------------+
      |                        |
    Accept              Retry / Escalate
                               |
                               v
                     Stronger Model / Human
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

The core simulation studies routing behavior.

Additional modules explore how Work Unit economics, verification, retrieval, evaluation, fine-tuning, experimentation, and production safeguards fit around that routing layer.

---

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

---

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

---

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

---

## Inefficiency Detection

The framework flags patterns such as:

- frontier models used for simple workloads
- coding-specialized tools used for mismatched tasks
- deterministic automation used where task complexity exceeds its capabilities
- expensive failed executions
- successful executions requiring substantial human correction

These signals are intended as diagnostic indicators rather than definitive judgments about individual tool calls.

---

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

---

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

---

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

---

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

---

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

---

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

---

## Work-Unit-Aware Routing

The initial routing framework evaluates which model or tool should handle a workload using expected cost, quality, reliability, latency, correction burden, and operational constraints.

A second set of experiments extends the problem from **model-call economics** to **Work Unit completion economics**.

The central question is:

> **When should an enterprise AI system use a cheaper model first and escalate, and when should it route directly to a stronger model?**

A Work Unit represents a discrete piece of work with attributes including:

- task type
- complexity
- sensitivity
- business value
- failure cost
- escalation cost

The routing decision can therefore account for more than inference price.

It considers:

```text
Model execution cost
        +
Escalation overhead
        +
Expected unresolved failure cost
        +
Verification cost
        +
Latency and reliability considerations
```

All success probabilities, failure costs, escalation costs, and verifier characteristics in these experiments are **synthetic simulation assumptions**.

They are used to study system behavior and decision boundaries rather than represent measured production economics.

---

## Direct Routing vs Cascaded Routing

Three execution strategies are compared:

```text
Direct Small
Work Unit
    |
    v
Small Model
```

```text
Direct Frontier
Work Unit
    |
    v
Frontier Model
```

```text
Cascade
Work Unit
    |
    v
Small Model
    |
 failure
    |
    v
Frontier Model
```

For direct execution:

```text
Expected Total Cost
    =
Model Cost
    +
P(Failure) × Failure Cost
```

For the idealized cascade:

```text
Expected Execution + Escalation Cost
    =
Small Model Cost
    +
P(Small Failure) × Frontier Cost
    +
P(Small Failure) × Escalation Cost
```

and:

```text
Expected Failure Cost
    =
P(Small Failure)
× P(Frontier Failure)
× Failure Cost
```

This first experiment assumes that failure after the small-model attempt is observable. A later verifier experiment relaxes that assumption and models imperfect failure detection explicitly.

---

## Workload-Dependent Model Capability

A single global success probability for each model is unlikely to represent a heterogeneous enterprise environment.

A smaller model may be highly capable at summarization while substantially weaker at technical reasoning or compliance.

The simulation therefore assigns workload-specific model capability assumptions.

| Work Unit | Small-model success | Frontier success | Failure cost |
|---|---:|---:|---:|
| Summarization | 0.90 | 0.97 | $0.01 |
| Technical reasoning | 0.68 | 0.95 | $0.10 |
| Compliance | 0.55 | 0.96 | $1.00 |

The idealized cascade experiment produced:

### Summarization

```text
Direct small
Expected total cost: $0.0050
Success probability: 0.900

Direct frontier
Expected total cost: $0.0183
Success probability: 0.970

Idealized cascade
Expected total cost: $0.0060
Success probability: 0.997
```

Optimal strategy:

```text
direct:small_model
```

### Technical Reasoning

```text
Direct small
Expected total cost: $0.0360
Success probability: 0.680

Direct frontier
Expected total cost: $0.0230
Success probability: 0.950

Idealized cascade
Expected total cost: $0.0178
Success probability: 0.984
```

Optimal strategy:

```text
cascade:small_model->frontier_model
```

### Compliance

```text
Direct small
Expected total cost: $0.4540
Success probability: 0.550

Direct frontier
Expected total cost: $0.0580
Success probability: 0.960

Idealized cascade
Expected total cost: $0.1201
Success probability: 0.982
```

Optimal strategy:

```text
direct:frontier_model
```

The experiment therefore produces three routing regimes:

```text
Low-cost failure
      |
      v
DIRECT SMALL

Intermediate failure / escalation economics
      |
      v
SMALL → FRONTIER CASCADE

High-cost failure
      |
      v
DIRECT FRONTIER
```

The result demonstrates why neither:

```text
always use the cheapest model
```

nor:

```text
always start cheap and escalate
```

is universally optimal within the simulation.

---

## Verifier-Aware Cost and Reliability

The idealized cascade is useful for understanding routing economics, but it assumes that the system knows when the small model has failed.

The verifier-aware experiment provides a more realistic comparison by introducing imperfect failure detection.

Using the strong verifier configuration:

| Work Unit | Direct small | Strong verified cascade | Direct frontier | Lowest expected cost |
|---|---:|---:|---:|---|
| Summarization | $0.0050 / 90.0% | $0.0083 / 99.2% | $0.0183 / 97.0% | Direct small |
| Technical reasoning | $0.0360 / 68.0% | $0.0213 / 96.8% | $0.0230 / 95.0% | Verified cascade |
| Compliance | $0.4540 / 55.0% | $0.1416 / 96.0% | $0.0580 / 96.0% | Direct frontier |

Each cell reports:

```text
Expected total cost / final success probability
```

![Cost vs reliability across routing strategies](results/figures/cost_reliability_frontier.png)

The cost-reliability frontier shows why routing decisions depend on the Work Unit.

For summarization, direct-small has the lowest expected total cost, while verified cascading buys substantially higher modeled reliability at additional cost.

For technical reasoning, the strong verified cascade provides slightly higher modeled reliability than direct-frontier at slightly lower expected total cost.

For compliance, direct-frontier dominates the verified cascade on expected cost at the same modeled 96% final success rate.

This comparison makes the broader routing problem explicit: the best strategy depends on both **economic consequences and required reliability**.

---

## Failure-Cost and Escalation-Cost Decision Boundaries

The next experiment asks:

> **Where does the optimal routing policy change as failure and escalation become more expensive?**

To isolate failure and escalation economics, this sweep uses fixed small-model and frontier-model capability assumptions and the idealized cascade.

Failure costs are swept across:

```text
0.00
0.01
0.02
0.05
0.10
0.20
0.50
1.00
2.00
```

Escalation cost is modeled as a percentage of failure cost:

```text
0%
5%
10%
20%
30%
```

The experiment reveals distinct policy transitions.

At a 20% escalation-cost ratio, for example, the tested grid produced:

```text
Low failure cost
      |
      v
Direct Small

around $0.05
      |
      v
Cascade

around $0.50
      |
      v
Direct Frontier
```

These values are **observed switch points in the tested simulation grid**, not exact analytical thresholds or universal routing rules.

![Optimal routing strategy by Work Unit economics](results/figures/work_unit_decision_map.png)

The decision map makes the routing regimes explicit. As the cost of unresolved failure and escalation increases, the optimal strategy shifts from direct-small to cascade and eventually to direct-frontier within the simulated environment.

The experiment also exposed an important modeling issue.

Without an escalation penalty, cascades can appear unrealistically attractive because a failed first attempt has almost no operational consequence if the fallback eventually succeeds.

Explicitly modeling escalation overhead changes the decision boundary and allows direct-frontier routing to become optimal for sufficiently expensive failures.

---

## Robustness to Model-Performance Uncertainty

Routing decisions depend on estimated model success probabilities.

Those estimates will never be perfectly known in a production system.

The framework therefore tests:

> **What happens if the router's model-performance estimates are wrong?**

Both small-model and frontier-model success estimates are independently perturbed by:

```text
-10 percentage points
 -5 percentage points
  0 percentage points
 +5 percentage points
+10 percentage points
```

This creates 25 performance combinations per workload.

Results:

| Work Unit | Base Strategy | Strategy Stability |
|---|---|---:|
| Summarization | Direct small | 100% |
| Technical reasoning | Cascade | 92% |
| Compliance | Direct frontier | 92% |

For summarization, direct-small remained optimal in all 25 perturbation scenarios.

For technical reasoning:

```text
Cascade          23 / 25 = 92%
Direct frontier   2 / 25 = 8%
```

For compliance:

```text
Direct frontier  23 / 25 = 92%
Cascade            2 / 25 = 8%
```

The policy flips are useful diagnostic information.

They identify workloads close to a routing decision boundary where small errors in capability estimation can change the selected strategy.

A production router could use this information to trigger:

- conservative routing
- additional evaluation
- improved calibration
- more telemetry collection
- human review for high-risk decisions

Routing therefore has two related questions:

```text
Which strategy has the best expected outcome?

and

How stable is that decision to estimation uncertainty?
```

This experiment is a deterministic sensitivity analysis over assumed point estimates rather than a statistical uncertainty estimate.

---

## Imperfect Failure Detection

The basic cascade contains an unrealistic assumption:

> The system knows when the first model failed.

Real LLM systems usually do not expose a clean success or failure signal.

An incorrect response may still be fluent, plausible, and highly confident.

The framework therefore introduces an imperfect verifier.

The verifier is characterized by:

### Sensitivity

```text
P(verifier flags response | response is actually bad)
```

### Specificity

```text
P(verifier accepts response | response is actually good)
```

This creates two important error types.

### False Negative

```text
Bad response
     |
     v
Verifier accepts
     |
     v
Unresolved failure
```

### False Positive

```text
Good response
     |
     v
Verifier flags
     |
     v
Unnecessary escalation
```

False negatives increase downstream failure risk.

False positives increase model cost, escalation overhead, and latency.

---

## Verifier Profiles

Three synthetic verifier profiles are evaluated:

| Verifier | Sensitivity | Specificity |
|---|---:|---:|
| Weak | 0.70 | 0.90 |
| Moderate | 0.85 | 0.95 |
| Strong | 0.95 | 0.98 |

Verification itself has an assumed cost of:

```text
$0.002 per Work Unit
```

These verifier characteristics are synthetic assumptions rather than empirically measured classifier performance.

---

## Verification Results

### Summarization

| Verifier | Accepted bad rate | Escalation rate | Final success | Expected total cost |
|---|---:|---:|---:|---:|
| Weak | 3.0% | 16.0% | 96.5% | $0.0095 |
| Moderate | 1.5% | 13.0% | 98.1% | $0.0088 |
| Strong | 0.5% | 11.3% | 99.2% | $0.0083 |

### Technical Reasoning

| Verifier | Accepted bad rate | Escalation rate | Final success | Expected total cost |
|---|---:|---:|---:|---:|
| Weak | 9.6% | 29.2% | 88.9% | $0.0282 |
| Moderate | 4.8% | 30.6% | 93.7% | $0.0240 |
| Strong | 1.6% | 31.8% | 96.8% | $0.0213 |

### Compliance

| Verifier | Accepted bad rate | Escalation rate | Final success | Expected total cost |
|---|---:|---:|---:|---:|
| Weak | 13.5% | 37.0% | 85.0% | $0.2365 |
| Moderate | 6.8% | 41.0% | 91.6% | $0.1793 |
| Strong | 2.3% | 43.8% | 96.0% | $0.1416 |

![Verification economics](results/figures/verifier_economics.png)

Verification quality changes both reliability and Work Unit economics.

Stronger verification reduces accepted bad responses across all three workloads, with the largest economic effect appearing in compliance because unresolved failures carry a substantially higher simulated cost.

The compliance workload exposes the strongest verifier trade-off.

For the strong verifier:

```text
Expected inference cost:     $0.0119
Expected escalation cost:    $0.0877
Expected verification cost:  $0.0020
Expected failure cost:       $0.0400
Expected total cost:         $0.1416
```

The strong verifier causes **more escalation** because it catches more genuine small-model failures.

That raises execution and escalation spending.

However, the accepted bad-response rate falls from:

```text
13.5% → 2.3%
```

and expected failure cost falls enough to reduce overall expected Work Unit cost relative to weaker verifier configurations.

This illustrates an important system-level result:

> **Higher model usage or escalation is not necessarily inefficient if the additional execution prevents sufficiently expensive failures.**

However, better verification does not imply that a verified cascade is the optimal routing strategy.

For compliance, the strong verified cascade still costs approximately `$0.1416`, compared with `$0.0580` for direct-frontier execution under the base assumptions.

That result reinforces the value of jointly optimizing routing and verification rather than optimizing either component independently.

---

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

---

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

---

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

---

## Fine-Tuning Experiment

The repository includes a small transfer-learning experiment using `distilbert-base-uncased` for enterprise workload classification.

This is an encoder classification fine-tuning experiment rather than generative LLM instruction tuning.

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

---

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

---

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
Constraint + Work-Unit-Aware Routing
      |
      v
Model / Tool Execution
      |
      v
Verification + Faithfulness Evaluation
      |
      +--> Accept
      |
      +--> Retry
      |
      +--> Escalate to Stronger Model
      |
      +--> Human Review
      |
      v
Response
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
- verifier uncertainty
- sensitivity restrictions
- failed model attempts
- escalation overhead

Low-confidence or unsupported decisions can be escalated rather than forcing the system to return a result.

Provider failures can trigger retries, alternate eligible providers, or circuit breakers.

High-risk Work Units can bypass cheap-first execution entirely when the expected cost of failure or escalation makes direct frontier execution preferable.

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

Task success can serve as a primary outcome while faithfulness, latency, cost, human correction, accepted bad-response rate, and sensitive-data violations act as guardrails.

### Versioning and Rollback

Production decisions depend on more than model version alone.

The design therefore assumes versioning for:

- routing policies
- models
- prompts
- retrievers
- rerankers
- verifier configurations
- evaluation configurations
- classifier versions
- confidence thresholds

A detected regression can roll traffic back to a known-good configuration.

The complete design is documented in:

```text
docs/production_architecture.md
```

---

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

---

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

### 6. The cheapest request is not necessarily the cheapest completed Work Unit

Once failure and escalation costs are modeled, cheap-first routing is not universally optimal.

The simulation produced three regimes:

```text
Summarization       → Direct small
Technical reasoning → Small → frontier
Compliance          → Direct frontier
```

### 7. Escalation economics change routing decisions

Without explicit escalation cost, cascades can appear unrealistically attractive.

As failure and escalation costs increase, the optimal policy can move from:

```text
Direct small
      ↓
Cascade
      ↓
Direct frontier
```

### 8. Routing decisions should be evaluated for stability

Perturbing model success probabilities produced:

```text
Summarization       100% base-policy stability
Technical reasoning  92% base-policy stability
Compliance            92% base-policy stability
```

This provides a way to identify decisions near a policy boundary.

### 9. Verification is part of the routing problem

A cascade only works if the system can determine when escalation is necessary.

Modeling imperfect verification showed that false negatives create downstream failure risk while false positives create unnecessary escalation.

### 10. More escalation is not automatically inefficient

For high-risk compliance work, the strong verifier escalated more often but reduced accepted bad responses from **13.5% to 2.3%** and expected total cost from **$0.2365 to $0.1416** relative to the weak verifier.

The additional execution was justified by the reduction in expensive unresolved failures within the simulation.

### 11. Routing and verification must be optimized jointly

A stronger verifier improved the compliance cascade, but the resulting `$0.1416` expected total cost was still substantially higher than the `$0.0580` direct-frontier alternative.

Improving one component of an AI execution pipeline does not necessarily make the overall strategy optimal.

### 12. Retrieval coverage and ranking quality are different

The retrieval benchmark maintained perfect Recall@3 while semantic reranking improved MRR from 0.800 to 1.000.

The retriever had already found the relevant documents. The remaining problem was ordering them correctly.

### 13. Semantic similarity is not faithfulness

Embedding similarity can identify related evidence without establishing whether the evidence entails or contradicts a claim.

Faithfulness evaluation therefore requires stronger checks than semantic proximity alone.

### 14. AI regressions are multidimensional

A candidate configuration should not be considered better simply because an aggregate score improves.

Critical dimensions such as faithfulness, latency, cost, and sensitive-data handling require independent guardrails.

### 15. Fine-tuning and calibration solve different problems

Fine-tuning substantially improved workload classification on the diagnostic dataset, but confidence remained low.

Production systems therefore need explicit calibration and abstention strategies rather than assuming prediction confidence is trustworthy.

---

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

### Core Routing Simulation

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

### Work-Unit Routing Experiment

Compare direct-small, direct-frontier, and idealized cascaded execution:

```bash
python -m experiments.work_unit_routing_experiment
```

### Work-Unit Decision-Boundary Sweep

Sweep failure cost and escalation overhead:

```bash
python -m experiments.work_unit_threshold_sweep
```

### Routing Uncertainty Sweep

Perturb model-performance assumptions and measure policy stability:

```bash
python -m experiments.work_unit_uncertainty_sweep
```

### Imperfect Verifier Experiment

Evaluate cascade behavior under different verifier sensitivity and specificity assumptions:

```bash
python -m experiments.verifier_routing_experiment
```

### Retrieval Benchmark

```bash
python -m experiments.retrieval_benchmark
```

### Faithfulness Benchmark

```bash
python -m experiments.faithfulness_benchmark
```

### Regression Suite

```bash
python -m experiments.regression_suite
```

### Fine-Tuning Experiment

```bash
python -m experiments.train_fine_tuned_model
```

### Fine-Tuning Strategy Benchmark

```bash
python -m experiments.fine_tuning_benchmark
```

### Simulated A/B Experiment

```bash
python -m experiments.ab_routing_experiment
```

### Generate Figures

```bash
python -m src.visualization.routing_impact
python -m src.visualization.policy_tradeoffs
python -m src.visualization.constraint_failures
python -m src.visualization.work_unit_decision_map
python -m src.visualization.cost_reliability_frontier
python -m src.visualization.verifier_economics
```

---

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
│   ├── production_architecture.md
│   └── research_questions.md
│
├── experiments/
│   ├── ab_routing_experiment.py
│   ├── faithfulness_benchmark.py
│   ├── fine_tuning_benchmark.py
│   ├── multi_seed.py
│   ├── policy_tradeoffs.py
│   ├── regression_suite.py
│   ├── retrieval_benchmark.py
│   ├── train_fine_tuned_model.py
│   ├── verifier_routing_experiment.py
│   ├── work_unit_routing_experiment.py
│   ├── work_unit_threshold_sweep.py
│   └── work_unit_uncertainty_sweep.py
│
├── results/
│   └── figures/
│       ├── constraint_failures.png
│       ├── cost_reliability_frontier.png
│       ├── policy_tradeoffs.png
│       ├── routing_impact.png
│       ├── verifier_economics.png
│       └── work_unit_decision_map.png
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
│   │   ├── counterfactuals.py
│   │   └── work_unit.py
│   │
│   ├── visualization/
│   │   ├── constraint_failures.py
│   │   ├── cost_reliability_frontier.py
│   │   ├── policy_tradeoffs.py
│   │   ├── routing_impact.py
│   │   ├── verifier_economics.py
│   │   └── work_unit_decision_map.py
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

---

## Limitations

This project is a **simulation and evaluation framework**, not a production benchmark of ChatGPT, Claude, Codex, or any other model.

Tool behavior, cost, latency, quality, and reliability in the routing experiments are synthetically generated according to assumptions encoded in the simulation.

Therefore, results such as the 20.7% average cost reduction should be interpreted as evidence about the behavior of the routing framework **within the simulated environment**, not as expected savings from deploying the system in a real organization.

The counterfactual outcomes are simulated rather than observed from repeated execution of identical tasks across real models.

The Work Unit experiments also use synthetic assumptions for:

- workload-specific model success probabilities
- failure costs
- escalation costs
- verification costs
- verifier sensitivity
- verifier specificity

The dollar-denominated values in these experiments are illustrative simulation inputs rather than measured business costs.

The threshold-sweep results identify policy switches on a finite simulation grid. They should not be interpreted as exact analytical thresholds or general decision rules.

The uncertainty sweep perturbs assumed success probabilities by fixed amounts. It demonstrates policy sensitivity but does not represent a statistically estimated distribution over model performance.

The verifier experiment assumes known sensitivity and specificity values. A production system would need to estimate and continuously monitor these characteristics on representative labeled workloads.

The verifier-aware cascade assumes that an escalated frontier response replaces the original small-model response. It also uses the supplied frontier success probability after escalation. In a real system, workloads that defeat the smaller model may be disproportionately difficult for the frontier model as well, so conditional fallback performance may differ from marginal frontier performance.

Verifier latency is not currently included in the Work Unit economics.

The direct-frontier comparison does not currently add a separate verification step. In a production environment where high-risk frontier outputs also require mandatory verification, that cost and reliability effect should be included in the comparison.

The current Work Unit objective focuses primarily on execution, escalation, verification, and unresolved failure economics. A production policy would also enforce explicit quality, latency, sensitivity, governance, and reliability constraints when comparing strategies.

The A/B experiment is simulated. Its treatment effect is generated from assumed outcome distributions and should not be interpreted as an empirically measured causal effect.

The retrieval benchmark contains only five synthetic diagnostic queries. Its MRR improvement demonstrates the behavior of the reranking implementation but does not establish generalized retrieval performance.

The fine-tuning experiment uses a very small synthetic training and held-out dataset. Its results demonstrate the transfer-learning and evaluation workflow rather than production-level generalization.

The confidence thresholds included in the experiment are illustrative and have not been calibrated on an independent validation set.

The regression tolerances are also illustrative. Production thresholds should be tied to empirical variance, service-level requirements, and business risk.

A production extension would replace simulated outcomes with telemetry from actual enterprise AI workloads and empirical model evaluations.

---

## Future Work

Potential extensions include:

- calibration from real production telemetry
- empirical workload-specific model success estimation
- conditional fallback-performance estimation
- learned failure-cost models
- workload-specific verifier selection
- verifier calibration from labeled outcomes
- verifier latency modeling
- verification requirements for direct-frontier execution
- explicit quality and reliability constraints in Work Unit optimization
- larger and independently labeled retrieval benchmarks
- dense first-stage retrieval
- learned hybrid lexical-dense retrieval
- retrieval evaluation with nDCG and larger relevance sets
- probability calibration using a dedicated validation split
- workload-specific abstention thresholds
- learned routing policies
- contextual bandits for adaptive tool selection
- probabilistic uncertainty estimates rather than fixed perturbation sweeps
- budget-aware optimization
- dynamic model pricing
- queue and capacity constraints
- provider-load-aware routing
- privacy and data-residency policies
- explicit human escalation policies
- human-review cost and latency modeling
- online monitoring for routing drift
- empirical shadow-mode evaluation
- production A/B experimentation

---

## Why This Project Matters

Enterprise AI infrastructure is increasingly becoming a heterogeneous system rather than a single-model application.

The operational question is therefore shifting from:

> **Which model is best?**

to:

> **Which model, tool, or workflow should handle this task under the organization's actual constraints?**

and, increasingly:

> **What is the most efficient and reliable way to complete this Work Unit once failures, verification, retries, escalation, and downstream consequences are included?**

That decision cannot be made from model quality or inference price alone.

It depends on:

- workload characteristics
- model capability for that workload
- organizational context
- retrieval quality
- sensitivity
- cost
- latency
- reliability
- confidence
- verification quality
- escalation overhead
- uncertainty
- consequences of failure

The experiments show why routing, verification, and evaluation should not be treated as independent components.

A cheap model can be the correct choice for one Work Unit, a cheap-to-frontier cascade can be appropriate for another, and direct-frontier execution can be economically preferable for sufficiently high-risk work.

The goal of this project is therefore not simply to minimize AI spend.

It is to provide an experimental framework for studying **how enterprise AI systems allocate intelligence to complete work reliably and efficiently**, from workload characterization and routing through retrieval, verification, evaluation, experimentation, and production safeguards.