import json
import time
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

TEST_PATH = Path("data/generative_fine_tuning/test.jsonl")
POLICY_PATH = Path("data/generative_fine_tuning/routing_policy.json")
RESULTS_PATH = Path("results/generative_rag_results.json")

FIELDS = [
    "task_type",
    "sensitivity",
    "risk_level",
    "recommended_strategy",
]

TOP_K = 2


def load_test_data():
    rows = []

    with TEST_PATH.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            row["output"] = json.loads(row["output"])
            rows.append(row)

    return rows


def load_policy():
    with POLICY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def normalize(matrix):
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


def retrieve_policy(query, policy, embedder, policy_embeddings):
    query_embedding = embedder.encode(
        [query],
        convert_to_numpy=True,
    )

    query_embedding = normalize(query_embedding)

    scores = (
        policy_embeddings @ query_embedding[0]
    )

    indices = np.argsort(scores)[::-1][:TOP_K]

    retrieved = []

    for index in indices:
        retrieved.append(
            {
                "id": policy[index]["id"],
                "text": policy[index]["text"],
                "score": float(scores[index]),
            }
        )

    return retrieved


def build_prompt(tokenizer, row, retrieved):
    context = "\n".join(
        f"- {item['text']}"
        for item in retrieved
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an enterprise AI routing assistant. "
                "Use the supplied routing policy as the authoritative "
                "source for classification and routing decisions. "
                "Follow the requested output format exactly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Routing policy:\n{context}\n\n"
                f"{row['instruction']}\n\n"
                f"Workload: {row['input']}\n\n"
                "Return only the JSON object. Do not include markdown "
                "or additional explanation. Use only these task_type values: "
                "summarization, retrieval, technical_reasoning, compliance, "
                "classification, generation. Use only low, medium, or high "
                "for sensitivity and risk_level. Use only direct_small, "
                "verified_cascade, or direct_frontier for recommended_strategy."
            ),
        },
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


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

        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(
                    text[start:end + 1]
                )
            except json.JSONDecodeError:
                pass

    return None


def main():
    device = (
        "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )

    print("Loading policy retriever...")

    policy = load_policy()

    embedder = SentenceTransformer(
        EMBEDDING_MODEL
    )

    policy_texts = [
        item["text"]
        for item in policy
    ]

    policy_embeddings = embedder.encode(
        policy_texts,
        convert_to_numpy=True,
    )

    policy_embeddings = normalize(
        policy_embeddings
    )

    print(
        f"Loading {MODEL_NAME} on {device}..."
    )

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=(
            torch.float16
            if device == "mps"
            else torch.float32
        ),
    ).to(device)

    model.eval()

    test_rows = load_test_data()

    valid_json = 0
    exact_matches = 0

    field_correct = {
        field: 0
        for field in FIELDS
    }

    predictions = []
    latencies = []

    retrieval_hits = 0

    for i, row in enumerate(
        test_rows,
        start=1,
    ):
        retrieved = retrieve_policy(
            row["input"],
            policy,
            embedder,
            policy_embeddings,
        )

        expected_task = row["output"]["task_type"]

        retrieval_hit = any(
            item["id"] == expected_task
            for item in retrieved
        )

        retrieval_hits += int(retrieval_hit)

        prompt = build_prompt(
            tokenizer,
            row,
            retrieved,
        )

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
        ).to(device)

        start_time = time.perf_counter()

        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

        latency = (
            time.perf_counter()
            - start_time
        )

        latencies.append(latency)

        new_tokens = generated[
            0,
            inputs["input_ids"].shape[1]:,
        ]

        text = tokenizer.decode(
            new_tokens,
            skip_special_tokens=True,
        ).strip()

        prediction = parse_json(text)
        expected = row["output"]

        if prediction is not None:
            valid_json += 1

            if all(
                prediction.get(field)
                == expected[field]
                for field in FIELDS
            ):
                exact_matches += 1

            for field in FIELDS:
                if (
                    prediction.get(field)
                    == expected[field]
                ):
                    field_correct[field] += 1

        predictions.append(
            {
                "input": row["input"],
                "expected": expected,
                "retrieved_policy": retrieved,
                "retrieval_hit": retrieval_hit,
                "raw_output": text,
                "parsed_output": prediction,
                "latency_seconds": latency,
            }
        )

        print(
            f"[{i:02d}/{len(test_rows)}] "
            f"retrieval_hit={retrieval_hit} "
            f"valid_json={prediction is not None}"
        )

    n = len(test_rows)

    summary = {
        "model": MODEL_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "n_examples": n,
        "top_k": TOP_K,
        "retrieval_hit_rate": (
            retrieval_hits / n
        ),
        "valid_json_rate": (
            valid_json / n
        ),
        "exact_match_rate": (
            exact_matches / n
        ),
        "field_accuracy": {
            field: (
                field_correct[field] / n
            )
            for field in FIELDS
        },
        "average_generation_latency_seconds": (
            sum(latencies) / n
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
                "predictions": predictions,
            },
            f,
            indent=2,
        )

    print("\nRAG evaluation")
    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    print(
        f"\nSaved results to "
        f"{RESULTS_PATH}"
    )


if __name__ == "__main__":
    main()