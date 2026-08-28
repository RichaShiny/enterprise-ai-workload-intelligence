import json
from pathlib import Path

OUTPUT_DIR = Path("data/generative_fine_tuning")

INSTRUCTION = (
    "Classify the enterprise workload and recommend a routing strategy. "
    "Return valid JSON with task_type, sensitivity, risk_level, "
    "and recommended_strategy."
)


def example(text, task_type, sensitivity, risk, strategy):
    return {
        "instruction": INSTRUCTION,
        "input": text,
        "output": {
            "task_type": task_type,
            "sensitivity": sensitivity,
            "risk_level": risk,
            "recommended_strategy": strategy,
        },
    }


TRAIN_EXAMPLES = [
    # Summarization: low-risk, inexpensive model is sufficient
    example(
        "Summarize these public product release notes into three bullet points.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Condense this internal team update into a short weekly summary.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Create a concise summary of these non-confidential conference notes.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Summarize these customer feature requests for the product team.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Turn this long project status update into five key takeaways.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Summarize this public industry article for an internal newsletter.",
        "summarization", "low", "low", "direct_small",
    ),

    # Retrieval: usually benefits from verification
    example(
        "Find the section of the engineering handbook describing rollback procedures.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Locate the internal policy that defines the approval process for production deployments.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Retrieve the documentation describing our database backup requirements.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Find the policy passage specifying who can approve elevated system access.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Locate the technical document explaining the service recovery procedure.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Find the internal guidance covering incident escalation responsibilities.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),

    # Technical reasoning: complex enough to justify verification/escalation
    example(
        "Diagnose why this distributed service occasionally deadlocks during concurrent writes.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Determine why this API returns stale state after retries under heavy load.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Analyze why this data pipeline produces duplicate records after partial failures.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Explain the likely cause of intermittent race conditions in this worker queue.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Investigate why model-serving latency spikes when concurrent traffic increases.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Reason through why this caching strategy sometimes serves inconsistent results.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Analyze a production database failover issue affecting transaction consistency.",
        "technical_reasoning", "high", "high", "direct_frontier",
    ),

    # Compliance: high consequence, route directly to stronger capability
    example(
        "Review this vendor agreement for data-retention requirements and regulatory exposure.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Assess whether this customer-data workflow complies with contractual privacy restrictions.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Review this proposed data-sharing process for regulatory and contractual risk.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Determine whether this retention policy satisfies the organization's legal obligations.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Evaluate this employee-data workflow for privacy and compliance concerns.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Review this third-party processing agreement for sensitive-data obligations.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Assess whether this cross-border data transfer creates regulatory risk.",
        "compliance", "high", "high", "direct_frontier",
    ),

    # Classification: routine categorization
    example(
        "Categorize these support tickets by product area.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Assign each incoming feedback message to a predefined topic category.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Label these public product reviews as bug report, feature request, or general feedback.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Classify these documentation pages by technical topic.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Sort these generic help-desk questions into predefined request types.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Classify these anonymized survey comments into broad themes.",
        "classification", "low", "low", "direct_small",
    ),

    # Generation: risk depends on what is being generated
    example(
        "Draft three informal headline options for a public company blog post.",
        "generation", "low", "low", "direct_small",
    ),
    example(
        "Generate several alternative titles for this internal presentation.",
        "generation", "low", "low", "direct_small",
    ),
    example(
        "Draft a short non-sensitive description for a product feature.",
        "generation", "low", "low", "direct_small",
    ),
    example(
        "Write a first draft of a customer-facing explanation of a technical outage.",
        "generation", "medium", "medium", "verified_cascade",
    ),
    example(
        "Draft a response to a customer complaint that should be reviewed before sending.",
        "generation", "medium", "medium", "verified_cascade",
    ),
    example(
        "Generate a technical migration plan that an engineer will validate before execution.",
        "generation", "medium", "medium", "verified_cascade",
    ),
    example(
        "Draft an external statement concerning a sensitive regulatory investigation.",
        "generation", "high", "high", "direct_frontier",
    ),
    example(
        "Prepare a response containing confidential financial information for executive review.",
        "generation", "high", "high", "direct_frontier",
    ),
]


TEST_EXAMPLES = [
    # Harder, unseen formulations
    example(
        "Give leadership a compact recap of these publicly available quarterly product updates.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Reduce these ordinary sprint retrospective notes to the most important themes.",
        "summarization", "low", "low", "direct_small",
    ),
    example(
        "Produce a short digest of these non-sensitive user research notes.",
        "summarization", "low", "low", "direct_small",
    ),

    example(
        "Identify where our internal documentation states the required steps for restoring a failed service.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Search the company knowledge base for the rule governing privileged account approvals.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),
    example(
        "Find the authoritative internal guidance on escalating a critical infrastructure incident.",
        "retrieval", "medium", "medium", "verified_cascade",
    ),

    example(
        "Work out why requests occasionally produce conflicting values after automatic retries.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Trace the likely cause of duplicate events appearing after a consumer restarts.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Determine why concurrent jobs sometimes overwrite one another's state.",
        "technical_reasoning", "medium", "medium", "verified_cascade",
    ),
    example(
        "Reason about a production consistency failure that could corrupt financial transaction records.",
        "technical_reasoning", "high", "high", "direct_frontier",
    ),

    example(
        "Check whether sending these customer records to an overseas processor is permissible under the governing policy.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Evaluate a proposed deletion schedule for confidential customer information against regulatory requirements.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Determine whether this new third-party analytics workflow creates privacy obligations.",
        "compliance", "high", "high", "direct_frontier",
    ),
    example(
        "Assess the legal-risk implications of retaining employee records beyond the approved period.",
        "compliance", "high", "high", "direct_frontier",
    ),

    example(
        "Group these anonymized customer comments into the existing feedback taxonomy.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Map these routine service requests to their predefined operational categories.",
        "classification", "low", "low", "direct_small",
    ),
    example(
        "Assign these public forum posts to the appropriate product topic.",
        "classification", "low", "low", "direct_small",
    ),

    example(
        "Come up with five possible names for an internal engineering workshop.",
        "generation", "low", "low", "direct_small",
    ),
    example(
        "Prepare a customer-facing explanation of a service degradation that must be checked before publication.",
        "generation", "medium", "medium", "verified_cascade",
    ),
    example(
        "Draft an executive communication containing sensitive acquisition information.",
        "generation", "high", "high", "direct_frontier",
    ),
]


def write_jsonl(path, examples):
    with path.open("w", encoding="utf-8") as f:
        for item in examples:
            row = {
                "instruction": item["instruction"],
                "input": item["input"],
                "output": json.dumps(item["output"]),
            }
            f.write(json.dumps(row) + "\n")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    assert len(TRAIN_EXAMPLES) == 40
    assert len(TEST_EXAMPLES) == 20

    train_inputs = {x["input"] for x in TRAIN_EXAMPLES}
    test_inputs = {x["input"] for x in TEST_EXAMPLES}

    assert len(train_inputs) == len(TRAIN_EXAMPLES)
    assert len(test_inputs) == len(TEST_EXAMPLES)
    assert train_inputs.isdisjoint(test_inputs)

    write_jsonl(OUTPUT_DIR / "train.jsonl", TRAIN_EXAMPLES)
    write_jsonl(OUTPUT_DIR / "test.jsonl", TEST_EXAMPLES)

    print(f"Saved {len(TRAIN_EXAMPLES)} unique training examples.")
    print(f"Saved {len(TEST_EXAMPLES)} unique test examples.")
    print("Train/test input overlap: 0")


if __name__ == "__main__":
    main()