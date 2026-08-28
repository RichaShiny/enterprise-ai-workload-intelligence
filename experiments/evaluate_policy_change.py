import json
import time
from pathlib import Path

import numpy as np
import torch
from peft import PeftModel
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_PATH = Path("results/qwen_routing_lora")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

FIELDS = [
    "task_type",
    "sensitivity",
    "risk_level",
    "recommended_strategy",
]

UPDATED_POLICY = [
    {
        "id": "privileged_retrieval",
        "text": (
            "UPDATED POLICY: Retrieval involving privileged, elevated, "
            "administrator, root-account, or sensitive access controls is "
            "high sensitivity and high risk and must use direct_frontier."
        ),
    },
    {
        "id": "ordinary_retrieval",
        "text": (
            "Ordinary internal retrieval means locating information in "
            "documentation, policies, or knowledge bases. When it does not "
            "involve privileged or sensitive access controls, it is medium "
            "sensitivity and medium risk and should use verified_cascade."
        ),
    },
]

TEST_EXAMPLES = [
    "Find the approval rule for privileged database administrator access.",
    "Locate the policy governing emergency root-account access.",
    "Search the knowledge base for elevated credential approval requirements.",
    "Find the documentation defining privileged production access.",
    "Locate the internal rule for administrator account authorization.",
    "Retrieve the policy covering elevated system permissions.",
]

EXPECTED = {
    "task_type": "retrieval",
    "sensitivity": "high",
    "risk_level": "high",
    "recommended_strategy": "direct_frontier",
}


def normalize(matrix):
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


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


def generate(model, tokenizer, prompt, device):
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to(device)

    start = time.perf_counter()

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    latency = time.perf_counter() - start

    new_tokens = output[
        0,
        inputs["input_ids"].shape[1]:,
    ]

    text = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True,
    ).strip()

    return parse_json(text), text, latency


def build_lora_prompt(tokenizer, workload):
    instruction = (
        "Classify the enterprise workload and recommend a routing strategy. "
        "Return valid JSON with task_type, sensitivity, risk_level, "
        "and recommended_strategy."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an enterprise AI routing assistant. "
                "Follow the requested output format exactly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{instruction}\n\n"
                f"Workload: {workload}\n\n"
                "Return only the JSON object. Do not include markdown "
                "or additional explanation."
            ),
        },
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def build_rag_prompt(tokenizer, workload, context):
    instruction = (
        "Classify the enterprise workload and recommend a routing strategy. "
        "Return valid JSON with task_type, sensitivity, risk_level, "
        "and recommended_strategy."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an enterprise AI routing assistant. "
                "The supplied routing policy is authoritative and represents "
                "the current policy. Follow it exactly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Current routing policy:\n{context}\n\n"
                f"{instruction}\n\n"
                f"Workload: {workload}\n\n"
                "Return only the JSON object. "
                "Use only retrieval for task_type. "
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

    print(f"Loading models on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    base_for_lora = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16 if device == "mps" else torch.float32,
    ).to(device)

    lora_model = PeftModel.from_pretrained(
        base_for_lora,
        ADAPTER_PATH,
    )
    lora_model.eval()

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16 if device == "mps" else torch.float32,
    ).to(device)
    base_model.eval()

    print("Loading policy retriever...")

    embedder = SentenceTransformer(EMBEDDING_MODEL)

    policy_texts = [
        item["text"]
        for item in UPDATED_POLICY
    ]

    policy_embeddings = normalize(
        embedder.encode(
            policy_texts,
            convert_to_numpy=True,
        )
    )

    lora_predictions = []
    rag_predictions = []
    results = []

    for i, workload in enumerate(TEST_EXAMPLES, start=1):
        lora_prompt = build_lora_prompt(
            tokenizer,
            workload,
        )

        lora_prediction, lora_raw, lora_latency = generate(
            lora_model,
            tokenizer,
            lora_prompt,
            device,
        )

        query_embedding = normalize(
            embedder.encode(
                [workload],
                convert_to_numpy=True,
            )
        )[0]

        scores = policy_embeddings @ query_embedding
        best_index = int(np.argmax(scores))
        retrieved = UPDATED_POLICY[best_index]

        rag_prompt = build_rag_prompt(
            tokenizer,
            workload,
            retrieved["text"],
        )

        rag_prediction, rag_raw, rag_latency = generate(
            base_model,
            tokenizer,
            rag_prompt,
            device,
        )

        lora_predictions.append(lora_prediction)
        rag_predictions.append(rag_prediction)

        results.append(
            {
                "input": workload,
                "expected": EXPECTED,
                "lora_prediction": lora_prediction,
                "lora_raw": lora_raw,
                "lora_latency_seconds": lora_latency,
                "retrieved_policy": retrieved,
                "retrieval_score": float(scores[best_index]),
                "rag_prediction": rag_prediction,
                "rag_raw": rag_raw,
                "rag_latency_seconds": rag_latency,
            }
        )

        print(f"\n[{i:02d}/{len(TEST_EXAMPLES)}]")
        print("LoRA:", lora_prediction)
        print("Retrieved:", retrieved["id"])
        print("RAG:", rag_prediction)

    summary = {
        "n_examples": len(TEST_EXAMPLES),
        "policy_change": (
            "Privileged-access retrieval changed from "
            "verified_cascade to direct_frontier."
        ),
        "lora_without_updated_context": score(
            lora_predictions
        ),
        "base_with_updated_rag": score(
            rag_predictions
        ),
    }

    output_path = Path(
        "results/generative_policy_change_results.json"
    )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "examples": results,
            },
            f,
            indent=2,
        )

    print("\nPolicy-change evaluation")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()