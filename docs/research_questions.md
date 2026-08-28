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

## Q26. What did the fine-tuning experiment show?

Fine-tuning DistilBERT for four-class workload classification improved accuracy from 0.25 to 0.688 and macro F1 from 0.105 to 0.657 on the diagnostic test set. The experiment demonstrates encoder transfer learning rather than generative LLM instruction tuning.

## Q27. What did the fine-tuning experiment reveal about confidence?

The average maximum predicted probability was only about 0.418, and a threshold of 0.65 would have escalated all 16 held-out examples. That showed that predictive performance and confidence calibration are separate problems.

## Q28. Why didn't you simply lower the confidence threshold?

That would risk tuning against the test set to manufacture a better result. A production system should choose thresholds using separate validation data and evaluate calibration and coverage explicitly.

## Q29. What is the purpose of the simulated A/B experiment?

It demonstrates how a routing policy could be evaluated with randomized treatment assignment and guardrails. It is a design and analysis framework, not empirical causal evidence because the outcomes are generated from assumed distributions.

## Q30. What would the primary metric and guardrails be in a real routing experiment?

Task success could serve as the primary outcome. Guardrails would include cost, latency, faithfulness, human correction rate, and safety or compliance failures.

## Q31. How would this system be deployed safely?

I would move from offline evaluation to regression gates, then shadow mode, canary release, randomized A/B testing, and gradual rollout. Routing policies, models, prompts, retrievers, rerankers, evaluators, and thresholds should all be independently versioned for rollback.

## Q32. What are the biggest current limitations?

The workload economics, model success probabilities, verifier characteristics, and many outcomes are synthetic. A production version would need empirical telemetry, calibrated workload-specific model performance, conditional fallback estimates, business-derived failure costs, and measured verifier performance.

## Q33. What is the biggest architectural lesson from the project?

Routing, verification, and evaluation cannot be treated as separate optimization problems. The cheapest or most accurate model in isolation may not produce the lowest-cost or safest completed Work Unit once failures, retries, verification, escalation, and downstream consequences are included.