# Research Questions and Experiment Notes

This file captures the main questions explored in the project, what was built to investigate them, and the main result from each experiment.

## Q1. Is cost per request the right optimization target for enterprise AI routing?

Not necessarily. I extended the router to model the expected cost of completing a Work Unit, including inference, escalation, verification, and unresolved failure cost instead of looking only at the price of the first model call.

## Q2. When should the system use a cheaper model first and escalate versus route directly to a stronger model?

I compared three strategies: direct-small, direct-frontier, and small-to-frontier cascade. The optimal strategy changed depending on workload-specific model capability, failure cost, and escalation overhead.

## Q3. Does introducing escalation cost change the optimal routing policy?

Yes. Without escalation overhead, cascades looked unrealistically attractive because failed first attempts were almost free; once escalation cost was included, high-risk workloads could become cheaper to route directly to the frontier model.

## Q4. Where does the routing policy switch?

I built a threshold sweep over failure cost and escalation cost. At a 20% escalation-cost ratio in the tested grid, the policy moved from direct-small to cascade around a failure cost of $0.05 and from cascade to direct-frontier around $0.50.

These are grid-observed switch points, not universal thresholds.

## Q5. Is there one globally optimal routing strategy?

No. The simulation produced three distinct regimes: direct-small for inexpensive failures, cascade for intermediate-risk work, and direct-frontier when failure and escalation became sufficiently expensive.

## Q6. Why is a single model-level success probability not enough?

Model performance depends on workload type. A smaller model can be strong enough for summarization while performing much worse on technical reasoning or compliance, so I made success probability and quality workload-dependent.

## Q7. What did workload-aware routing show?

For summarization, direct-small was cheapest at an expected total cost of $0.0050 with 90% success. Technical reasoning favored a cascade at $0.0178 and 98.4% success, while compliance favored direct-frontier at $0.0580 because the smaller model's lower capability and escalation economics made cascade routing too expensive.

## Q8. What happens if the router's model-performance estimates are wrong?

I perturbed both small-model and frontier-model success estimates by ±5 and ±10 percentage points across 25 combinations per workload. Summarization stayed direct-small in 100% of cases, while technical reasoning and compliance kept their base strategies in 92% of cases.

## Q9. What do policy flips under uncertainty tell you?

They identify workloads near a routing decision boundary. In production, those cases should receive stronger calibration, more evaluation evidence, or more conservative routing rather than treating one point estimate as certain.

## Q10. What happens when failure detection is imperfect?

I replaced the unrealistic oracle failure signal with a verifier defined by sensitivity and specificity. Weak verifiers accepted more bad outputs, while stronger verifiers reduced unresolved failure rates and improved final success.

## Q11. Does stronger verification always reduce execution cost?

No. Stronger verification can increase escalation because it catches more actual failures, which means more frontier-model usage and higher execution cost.

Under the simulated assumptions, expected total Work Unit cost still fell because the reduction in unresolved failure cost outweighed the additional escalation cost.

## Q12. Why was verification especially important for compliance?

Compliance had a much larger assumed failure cost, so false negatives were expensive. Moving from the weak to strong verifier reduced accepted bad responses from 13.5% to 2.3% and reduced expected total cost from $0.2365 to $0.1416.

## Q13. Why did escalation increase with a stronger verifier for technical and compliance workloads?

Higher sensitivity caused more actual small-model failures to be detected correctly. That increased escalation frequency, but it also reduced unresolved failure cost.

## Q14. How did imperfect verification change the cascade result?

The oracle cascade was optimistic because it assumed perfect failure detection. For technical reasoning, the oracle cascade produced an expected total cost of $0.0178 with 98.4% success, while the strong-verifier cascade produced $0.0213 with 96.8% success.

That made the cascade less attractive, but it still slightly outperformed direct-frontier under the current assumptions.

## Q15. What did imperfect verification imply for compliance routing?

Even with a strong verifier, the verified cascade cost about $0.1416, while direct-frontier cost about $0.0580 in the base Work Unit experiment. That reinforces the direct-frontier decision for high-risk compliance work under the current assumptions.

## Q16. Why separate expected outcomes from realized outcomes?

An earlier router design could indirectly use realized quality and success values when making the routing decision. That created outcome leakage, so I changed the decision layer to use only pre-decision quantities such as expected quality, success probability, expected latency, expected corrections, and estimated cost.

## Q17. What did stricter routing constraints reveal?

Stricter policies did not automatically improve realized outcomes because fewer tools could satisfy the operating requirements. As constraint coverage fell, fallback behavior increased.

## Q18. Why is constraint satisfaction itself an important metric?

A policy can look strict on paper but fail to find feasible tools for many workloads. Measuring constraint satisfaction shows whether the available model portfolio can actually support the operating policy.

## Q19. What was the main result from the multi-seed routing experiment?

Across 10 seeds, the balanced router reduced simulated cost by about 20.7% on average while improving task success by 17.6 percentage points. It also reduced latency, human corrections, and frontier-model usage within the simulated environment.

## Q20. Why evaluate retrieval separately from generation?

If the correct evidence was never retrieved, generation quality cannot fix that failure reliably. Separating retrieval evaluation makes it possible to diagnose whether a failure came from evidence selection, ranking, or answer generation.

## Q21. What did the retrieval benchmark show?

Lexical retrieval already achieved Recall@3 of 1.0, so the relevant documents were present. Semantic reranking improved MRR from 0.8 to 1.0 by moving difficult relevant documents higher in the ranking.

## Q22. Why wasn't semantic similarity enough for faithfulness?

A claim can be semantically similar to the evidence while still contradicting it. I added NLI-based entailment and contradiction checking after semantic candidate selection to distinguish relevance from actual support.

## Q23. What failure exposed the weakness of the original faithfulness evaluator?

A claim that frontier models always have lower latency than local models could score as semantically similar to evidence discussing frontier and local-model latency even when the evidence contradicted the claim. The NLI-enhanced evaluator rejected that case.

## Q24. Why use regression gates instead of one aggregate evaluation score?

A candidate can improve task success or cost while degrading a critical metric like faithfulness. The regression framework therefore evaluates multiple dimensions independently and blocks changes that cross metric-specific tolerances.

## Q25. Why use metric-specific tolerances?

Different metrics have different units and risk implications. A tolerance of 0.02 can make sense for a normalized quality score but not for latency measured in milliseconds or cost measured in dollars.

## Q26. What did the encoder fine-tuning experiment show?

Fine-tuning DistilBERT for four-class workload classification improved accuracy from 0.25 to 0.688 and macro F1 from 0.105 to 0.657 on the diagnostic test set. The experiment demonstrates encoder transfer learning rather than generative LLM instruction tuning.

## Q27. What did the encoder fine-tuning experiment reveal about confidence?

The average maximum predicted probability was only about 0.418, and a threshold of 0.65 would have escalated all 16 held-out examples. That showed that predictive performance and confidence calibration are separate problems.

## Q28. Why didn't you simply lower the confidence threshold?

That would risk tuning against the test set to manufacture a better result. A production system should choose thresholds using separate validation data and evaluate calibration and coverage explicitly.

## Q29. What is the purpose of the simulated A/B experiment?

It demonstrates how a routing policy could be evaluated with randomized treatment assignment and guardrails. It is a design and analysis framework, not empirical causal evidence because the outcomes are generated from assumed distributions.

## Q30. What would the primary metric and guardrails be in a real routing experiment?

Task success could serve as the primary outcome. Guardrails would include cost, latency, faithfulness, human correction rate, and safety or compliance failures.

## Q31. Why is a naive historical comparison of routing policies not necessarily causal?

Historical routing is not randomized. Workload complexity, sensitivity, and business priority can affect both which routing policy is selected and whether the task succeeds.

That creates confounding.

In the observational simulation, the naive treated-versus-control difference estimated a treatment effect of 0.0956 even though the known simulated average treatment effect was 0.1471.

## Q32. What causal estimators did you compare for observational routing data?

I compared:

- naive treated-versus-control difference
- inverse propensity weighting
- doubly robust estimation
- cross-fitted residualization using a simplified partially linear Double ML-style estimator

The goal was not to identify a universally best estimator. It was to test whether adjustment could recover more of the known treatment effect under simulated confounding.

## Q33. What were the observational causal results?

The known simulated ATE was 0.1471.

The estimates were:

```text
Naive comparison      0.0956
IPW                   0.1476
Doubly robust         0.1410
Double ML-style       0.1296
```

Absolute errors relative to the known simulated ATE were approximately:

```text
Naive comparison      0.0514
IPW                   0.0005
Doubly robust         0.0060
Double ML-style       0.0175
```

The adjustment methods all reduced error relative to the naive comparison in this simulation.

## Q34. Why did IPW outperform the Double ML-style estimator in this simulation?

There is no reason Double ML should universally dominate IPW.

In this data-generating process, treatment assignment was generated from a logistic function of observed workload characteristics, so the logistic propensity model was well matched to the assignment mechanism.

The Double ML-style estimator also uses a simplified partially linear constant-effect formulation despite heterogeneous treatment effects, and finite-sample nuisance-model error still matters.

The correct conclusion is that IPW happened to be closest to the known effect in this simulation, not that IPW is generally superior.

## Q35. What assumptions are required for the observational causal estimates?

The main assumptions include:

- conditional ignorability given the observed confounders
- sufficient overlap or positivity in treatment assignment
- consistency of the treatment definition
- no major interference between Work Units

Conditional ignorability holds by construction in the simulation because the relevant confounders are included.

That would not be guaranteed with real enterprise telemetry.

## Q36. Can these methods fix unobserved confounding?

No.

IPW, doubly robust methods, and Double ML can adjust for observed confounding under their assumptions, but they cannot recover causal identification if important drivers of both routing assignment and task success were never measured.

A production analysis would therefore need overlap diagnostics, sensitivity analysis, and strong domain reasoning about likely omitted confounders.

## Q37. Why use cross-fitting in the Double ML-style estimator?

Cross-fitting reduces overfitting bias from flexible nuisance models.

The model estimating expected outcome and the model estimating treatment probability are trained on folds that do not contain the observation being residualized.

The treatment effect is then estimated from residualized treatment and outcome.

The current implementation is intentionally simplified and should be described as cross-fitted residualization or a simplified partially linear Double ML-style estimator.

## Q38. Did the treatment effect vary across workload complexity?

Yes, by construction.

The known simulated treatment effects were approximately:

```text
Low complexity       0.0879
Medium complexity    0.1466
High complexity      0.2084
```

The routing benefit therefore increased with workload complexity under the simulation assumptions.

These are known effects from the simulator rather than estimated conditional treatment effects.

## Q39. How would you estimate heterogeneous treatment effects in production?

I would separate average-effect estimation from heterogeneous-effect estimation.

For heterogeneous effects, I would consider methods such as causal forests, DR-learners, or other doubly robust CATE estimators, then validate whether discovered heterogeneity is stable across time and business-relevant workload slices.

The current project does not claim to estimate CATEs from the observational data.

## Q40. When would you prefer randomized experimentation over observational causal adjustment?

Whenever randomization is operationally and ethically feasible.

Randomization gives cleaner identification because treatment assignment is controlled rather than reconstructed from historical selection behavior.

Observational methods are useful when experimentation is impossible, too risky, or when analyzing historical telemetry, but their causal interpretation depends more heavily on assumptions.

## Q41. What did the generative baseline experiment show?

The untouched `Qwen/Qwen2.5-0.5B-Instruct` model achieved 100% valid JSON but 0% exact-match accuracy on the 20-example held-out routing benchmark.

Field accuracy was:

```text
Task type          0%
Sensitivity        5%
Risk level         5%
Routing strategy   0%
```

The failure was therefore not basic JSON generation.

The model did not know the controlled workload ontology or routing policy.

## Q42. Why was valid JSON not a sufficient evaluation metric?

All three generative approaches eventually achieved 100% valid JSON.

A system can produce perfectly valid JSON while assigning the wrong task type, risk level, sensitivity, or routing strategy.

Schema validity measures syntax.

It does not establish semantic correctness.

## Q43. What did the LoRA experiment show?

LoRA adaptation improved exact-match accuracy from 0% to 65% on the 20 held-out examples.

All four field-level accuracies reached 80%:

```text
Task type          80%
Sensitivity        80%
Risk level         80%
Routing strategy   80%
```

The result suggests that parameter-efficient fine-tuning successfully taught the model the project's stable ontology and repeated routing behavior on this small synthetic benchmark.

## Q44. How much of the Qwen model was actually trained?

The LoRA configuration updated approximately:

```text
1,081,344 trainable parameters
```

out of roughly 495 million total parameters in the PEFT-wrapped model.

That is approximately:

```text
0.218%
```

of parameters.

LoRA targeted:

```text
q_proj
k_proj
v_proj
o_proj
```

with rank 8, alpha 16, and dropout 0.05.

## Q45. What did the LoRA model actually learn?

The base model already knew how to generate JSON.

The main improvement was behavioral specialization.

It became much better at mapping workload descriptions into the intended:

- task taxonomy
- sensitivity levels
- risk levels
- routing strategies

So I would describe the experiment as teaching a stable decision ontology rather than teaching structured output from scratch.

## Q46. What were the main LoRA failure modes?

The held-out error analysis showed several systematic boundary failures:

- summarization versus generation confusion
- retrieval tasks with serious-sounding language being over-escalated
- some technical-reasoning workloads being classified as higher risk than intended

That matters because a single aggregate accuracy score would hide where the routing boundary is unstable.

## Q47. When should you fine-tune instead of using prompt engineering?

I would start with prompting or context engineering when the desired behavior can be expressed clearly and the task does not require large repeated prompts or strong behavioral consistency.

Fine-tuning becomes more attractive when the behavior is stable and repeated, for example:

- a fixed ontology
- consistent output behavior
- domain-specific classification
- tool-selection policy
- style or response patterns
- reducing repeated prompt burden

Fine-tuning is not the first solution to every LLM problem.

## Q48. When should you use RAG instead of fine-tuning?

RAG is better suited to knowledge that is:

- proprietary
- frequently changing
- too large to encode reliably in model weights
- required to be auditable or cited
- specific to a user, organization, or current policy state

Fine-tuning is better suited to stable behavioral adaptation.

In many production systems I would expect the two to be used together.

## Q49. What did the generative RAG experiment show?

The expected routing-policy chunk appeared in the retrieved context for 85% of held-out workloads.

However, exact-match routing accuracy remained 0%.

Field-level accuracy was:

```text
Task type          25%
Sensitivity        60%
Risk level         35%
Routing strategy   25%
```

So retrieval improved some dimensions relative to the base model, but correct context availability did not guarantee correct policy execution.

## Q50. Why does retrieval hit rate not equal end-to-end success?

Retrieval hit rate answers:

> Did the correct policy or evidence make it into the model's context?

End-to-end success answers:

> Did the model interpret and apply that context correctly?

Those are separate failure surfaces.

A production RAG system should therefore evaluate both retrieval quality and context utilization rather than stopping at Recall@k or hit rate.

## Q51. Was the RAG comparison a pure retrieval-only comparison?

No.

The RAG arm also included explicit controlled-label instructions in addition to retrieved policy context.

So improvement relative to the base prompt combines retrieval with stronger context engineering.

I would describe it as a context-engineered RAG condition rather than attributing all of the difference exclusively to retrieval.

## Q52. What happened in the first dynamic-policy experiment?

The first experiment changed privileged-access retrieval to high sensitivity, high risk, and `direct_frontier`.

LoRA without receiving the updated policy still achieved five of six exact matches.

At first glance that could look like successful adaptation, but it was not.

Earlier held-out errors showed that the model already tended to over-escalate privileged-access language, so the new rule accidentally aligned with an existing learned tendency.

That made the first experiment a poor test of stale fine-tuned knowledge.

## Q53. Why was catching that policy-change design flaw important?

Because otherwise I could have reported a misleading success.

The model had not actually learned a new policy at inference time.

The evaluation itself was confounded by a behavior the model already exhibited.

Rather than tuning the story around the result, I treated that as an experiment-design failure and constructed a second stress test with an arbitrary rule.

## Q54. What was the arbitrary policy-change stress test?

The updated policy stated that Product-department summarization should remain:

```text
low sensitivity
low risk
```

but should change routing from:

```text
direct_small
```

to:

```text
verified_cascade
```

There is no semantic reason the model should infer that new routing decision from the workload text alone.

That made it a cleaner test of whether inference-time context could override learned behavior.

## Q55. How did LoRA behave without the updated policy?

Without new policy context, the model selected `direct_small` for all six workloads.

That was consistent with the behavior learned during fine-tuning.

The result demonstrated that the fine-tuned behavior was stable enough to preserve the old routing rule on these fresh examples.

## Q56. What happened when the updated policy was injected into the fine-tuned model?

The model changed the routing decision on all six workloads.

However, instead of selecting the required:

```text
verified_cascade
```

it selected:

```text
direct_frontier
```

for every workload.

So the model reacted to the policy change but did not faithfully execute the exact rule.

## Q57. What does the hybrid policy experiment tell you?

Fine-tuning and retrieval do not automatically compose correctly.

The fine-tuned model had learned a stable routing behavior.

Updated context was able to alter that behavior.

But context availability did not guarantee precise policy following.

A production hybrid system therefore needs explicit tests for:

- context utilization
- instruction hierarchy
- policy faithfulness
- over-escalation
- stale learned behavior
- regression across unchanged workloads

## Q58. Would you say fine-tuning beat RAG in this project?

Only within this tiny controlled benchmark for this specific stable ontology task.

LoRA performed much better than the current RAG configuration on exact match and field-level accuracy.

That does not establish a universal ordering between fine-tuning and RAG.

The two techniques solve different problems.

The stronger production interpretation is:

```text
Fine-tuning → stable behavior
RAG         → dynamic knowledge
Hybrid      → often useful, but must be evaluated as a combined system
```

## Q59. How should a generative fine-tune be evaluated before and after training?

I would freeze a held-out evaluation set and compare the base and adapted model using the same decoding configuration.

For this task I used:

- exact match
- field-level accuracy
- JSON validity

In production I would add:

- risk-weighted error rates
- high-risk slice performance
- calibration or abstention
- faithfulness
- latency
- cost
- regression tests
- human evaluation
- downstream task success

Hyperparameter tuning should use a separate validation split rather than the final test set.

## Q60. What is one technical limitation of the current LoRA training setup?

The current causal language-modeling setup calculates loss across the tokenized training sequence, including prompt tokens.

A stronger supervised fine-tuning implementation would mask the system and user prompt tokens and calculate training loss only over the assistant response.

The current experiment still demonstrates parameter-efficient behavioral adaptation, but I would improve the loss masking before treating it as a stronger SFT implementation.

## Q61. Why didn't you keep tuning the prompts after seeing the policy-change failures?

Because the test examples had already been inspected.

Repeatedly modifying the prompt until those same examples passed would amount to tuning against the evaluation set.

The failure itself was more informative than a manufactured perfect score.

Further prompt or retrieval optimization should use validation data and then be evaluated on a new untouched test set.

## Q62. How would this system be deployed safely?

I would move from offline evaluation to regression gates, then shadow mode, canary release, randomized A/B testing, and gradual rollout.

Routing policies, models, prompts, retrievers, rerankers, evaluators, adapters, and thresholds should all be independently versioned for rollback.

## Q63. What would you monitor in production?

I would monitor both component metrics and end-to-end outcomes.

Examples include:

- task success
- accepted bad-response rate
- cost per completed Work Unit
- latency
- human correction
- escalation rate
- retrieval recall
- ranking quality
- faithfulness
- policy-following accuracy
- abstention rate
- sensitive-data violations
- provider failures
- routing distribution drift
- workload mix drift

Monitoring only model accuracy would miss several important operational failure modes.

## Q64. What are the biggest current limitations?

The workload economics, model success probabilities, verifier characteristics, and many routing outcomes are synthetic.

The causal experiment is simulated and assumes the relevant confounders are observed.

The retrieval benchmarks are intentionally small.

The encoder and generative fine-tuning datasets are small synthetic diagnostic datasets.

The RAG knowledge base is manually authored and simple.

The LoRA training implementation could use stronger response-only loss masking.

Production use would require empirical telemetry, larger independently labeled evaluation sets, calibration, risk-weighted metrics, conditional fallback estimates, and continuous monitoring.

## Q65. What is the biggest architectural lesson from the project?

Routing, retrieval, fine-tuning, verification, causal evaluation, and regression testing cannot be treated as independent optimization problems.

The cheapest or most accurate model in isolation may not produce the lowest-cost or safest completed Work Unit once failures, retries, verification, escalation, stale policy, context utilization, and downstream consequences are included.

The system has to be evaluated as an end-to-end decision process.