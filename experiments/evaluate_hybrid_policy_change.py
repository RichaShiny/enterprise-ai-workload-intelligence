import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_PATH = Path("results/qwen_routing_lora")
RESULTS_PATH = Path("results/generative_hybrid_policy_change_results.json")

FIELDS = [
    "task_type",
    "sensitivity",
    "risk_level",
    "recommended_strategy",
]

UPDATED_POLICY = (
    "POLICY VERSION 2: Product-department summarization workloads must use "
    "verified_cascade. This rule applies even when the information is "
    "non-sensitive and the workload remains low sensitivity and low risk. "
    "This policy overrides the previous direct_small routing rule for these workloads."
)

TEST_EXAMPLES = [
    "Summarize the Product team's routine weekly planning notes.",
    "Condense the Product department's non-confidential roadmap update.",
    "Create a short recap of the Product team's ordinary sprint review.",
    "Summarize these public feature updates for the Product organization.",
    "Reduce the Product department's weekly status report to five key points.",
    "Prepare a concise summary of the Product team's non-sensitive meeting notes.",
]

EXPECTED = {
    "task_type": "summarization",
    "sensitivity": "low",
    "risk_level": "low",
    "recommended_strategy": "verified_cascade",
}


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = (
            text.replace("```json", "")
            .replace("```", "")
            .strip()
        )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    return None


def build_prompt(tokenizer, workload, policy=None):
    instruction = (
        "Classify the enterprise workload and recommend a routing strategy. "
        "Return valid JSON with task_type, sensitivity, risk_level, "
        "and recommended_strategy."
    )

    if policy is None:
        system = (
            "You are an enterprise AI routing assistant. "
            "Follow the requested output format exactly."
        )

        policy_text = ""
    else:
        system = (
            "You are an enterprise AI routing assistant. "
            "The supplied current policy is authoritative. "
            "Apply it even if it differs from behavior learned previously."
        )

        policy_text = (
            f"Current routing policy:\n{policy}\n\n"
        )

    messages = [
        {
            "role": "system",
            "content": system,
        },
        {
            "role": "user",
            "content": (
                f"{policy_text}"
                f"{instruction}\n\n"
                f"Workload: {workload}\n\n"
                "Return only the JSON object. "
                "Use only summarization, retrieval, technical_reasoning, "
                "compliance, classification, or generation for task_type. "
                "Use only low, medium, or high for sensitivity and risk_level. "
                "Use only direct_small, verified_cascade, or direct_frontier "
                "for recommended_strategy."
            ),
        },
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def generate(model, tokenizer, prompt, device):
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = generated[
        0,
        inputs["input_ids"].shape[1]:,
    ]

    text = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True,
    ).strip()

    return parse_json(text), text


def score(predictions):
    n = len(predictions)

    valid = sum(
        prediction is not None
        for prediction in predictions
    )

    exact = sum(
        prediction is not None
        and all(
            prediction.get(field) == EXPECTED[field]
            for field in FIELDS
        )
        for prediction in predictions
    )

    field_accuracy = {}

    for field in FIELDS:
        correct = sum(
            prediction is not None
            and prediction.get(field) == EXPECTED[field]
            for prediction in predictions
        )

        field_accuracy[field] = correct / n

    return {
        "valid_json_rate": valid / n,
        "exact_match_rate": exact / n,
        "field_accuracy": field_accuracy,
    }


def main():
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    print(f"Loading LoRA model on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16 if device == "mps" else torch.float32,
    ).to(device)

    model = PeftModel.from_pretrained(
        base_model,
        ADAPTER_PATH,
    )

    model.eval()

    lora_predictions = []
    hybrid_predictions = []
    examples = []

    for i, workload in enumerate(TEST_EXAMPLES, start=1):
        old_prompt = build_prompt(
            tokenizer,
            workload,
        )

        hybrid_prompt = build_prompt(
            tokenizer,
            workload,
            UPDATED_POLICY,
        )

        old_prediction, old_raw = generate(
            model,
            tokenizer,
            old_prompt,
            device,
        )

        hybrid_prediction, hybrid_raw = generate(
            model,
            tokenizer,
            hybrid_prompt,
            device,
        )

        lora_predictions.append(old_prediction)
        hybrid_predictions.append(hybrid_prediction)

        examples.append(
            {
                "input": workload,
                "expected": EXPECTED,
                "lora_without_updated_policy": old_prediction,
                "lora_raw": old_raw,
                "hybrid_with_updated_policy": hybrid_prediction,
                "hybrid_raw": hybrid_raw,
            }
        )

        print(f"\n[{i:02d}/{len(TEST_EXAMPLES)}]")
        print("LoRA:", old_prediction)
        print("LoRA + updated context:", hybrid_prediction)

    summary = {
        "n_examples": len(TEST_EXAMPLES),
        "policy_change": (
            "Product-department summarization remains low-risk but "
            "must now route through verified_cascade."
        ),
        "lora_without_updated_policy": score(
            lora_predictions
        ),
        "lora_with_updated_policy_context": score(
            hybrid_predictions
        ),
    }

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "summary": summary,
                "examples": examples,
            },
            f,
            indent=2,
        )

    print("\nHybrid policy-change evaluation")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()