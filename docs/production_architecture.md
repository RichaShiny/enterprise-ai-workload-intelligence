# Production Architecture

## Request Flow

1. Request Intake
   - Receive enterprise workload.
   - Assign request ID and capture non-sensitive metadata.

2. Workload Classification
   - Classify task type and complexity.
   - Detect sensitivity.
   - Use confidence-aware escalation for uncertain classifications.

3. Context Retrieval
   - Retrieve relevant organizational context.
   - Apply metadata and access-control filters before ranking.

4. Semantic Reranking
   - Rerank candidate context using semantic relevance.
   - Enforce context and latency budgets.

5. Routing Policy
   - Estimate expected quality, success probability, latency,
     cost, and correction risk for eligible tools.
   - Apply sensitivity and tool-access constraints.
   - Select the best feasible tool according to routing policy.

6. Model / Tool Execution
   - Send only authorized context to the selected provider.
   - Apply timeout and retry policies.

7. Output Evaluation
   - Evaluate faithfulness against retrieved evidence.
   - Run task-specific quality checks.
   - Escalate unsupported or low-confidence responses.

8. Response
   - Return accepted response or route to human review.

9. Observability
   - Record routing decision, model version, prompt version,
     retrieval metrics, latency, cost, quality signals,
     faithfulness, corrections, and final outcome.

## Failure Handling

- Retrieval failure:
  retry with broader retrieval or escalate.

- No eligible tool:
  use an explicit safe fallback rather than silently
  violating constraints.

- Model timeout:
  retry or route to a secondary eligible model.

- Low classifier confidence:
  abstain or escalate instead of forcing a routing decision.

- Faithfulness failure:
  regenerate with constrained context or require human review.

- Provider outage:
  circuit-break affected provider and route to another
  eligible tool.

## Deployment Strategy

New routing policies should first run in shadow mode against
production traffic without affecting user responses.

If offline and shadow evaluation pass regression gates,
release through a small canary or randomized A/B experiment.

Primary outcome:
- task success

Guardrails:
- faithfulness
- latency
- cost
- human correction rate
- sensitive-data violations

Increase treatment exposure only while guardrails remain within
predefined limits.

## Rollback

Every routing policy, model, prompt, retriever, and reranker
should be versioned.

A production regression should trigger rollback to the last
known-good configuration rather than requiring a new deployment
to be constructed manually.