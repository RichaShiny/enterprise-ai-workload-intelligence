import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
TEST_PATH = Path("data/generative_fine_tuning/test.jsonl")
RESULTS_PATH = Path("results/generative_baseline_results.json")

FIELDS = [
    "task_type",
    "sensitivity",
    "risk_level",
    "recommended_strategy",
]


def load_jsonl(path):
    rows = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            row["output"] = json.loads(row["output"])
            rows.append(row)

    return rows


def build_prompt(tokenizer, row):
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
                f"{row['instruction']}\n\n"
                f"Workload: {row['input']}\n\n"
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


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    return None


def main():
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    print(f"Loading {MODEL_NAME} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16 if device == "mps" else torch.float32,
    ).to(device)

    model.eval()

    test_rows = load_jsonl(TEST_PATH)

    valid_json = 0
    exact_matches = 0
    field_correct = {field: 0 for field in FIELDS}
    predictions = []
    latencies = []

    for i, row in enumerate(test_rows, start=1):
        prompt = build_prompt(tokenizer, row)

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

        latency = time.perf_counter() - start_time
        latencies.append(latency)

        new_tokens = generated[0, inputs["input_ids"].shape[1]:]

        text = tokenizer.decode(
            new_tokens,
            skip_special_tokens=True,
        ).strip()

        prediction = parse_json(text)
        expected = row["output"]

        if prediction is not None:
            valid_json += 1

            if all(
                prediction.get(field) == expected[field]
                for field in FIELDS
            ):
                exact_matches += 1

            for field in FIELDS:
                if prediction.get(field) == expected[field]:
                    field_correct[field] += 1

        predictions.append(
            {
                "input": row["input"],
                "expected": expected,
                "raw_output": text,
                "parsed_output": prediction,
                "latency_seconds": latency,
            }
        )

        print(
            f"[{i:02d}/{len(test_rows)}] "
            f"valid_json={prediction is not None}"
        )

    n = len(test_rows)

    summary = {
        "model": MODEL_NAME,
        "n_examples": n,
        "valid_json_rate": valid_json / n,
        "exact_match_rate": exact_matches / n,
        "field_accuracy": {
            field: field_correct[field] / n
            for field in FIELDS
        },
        "average_latency_seconds": sum(latencies) / n,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "predictions": predictions,
            },
            f,
            indent=2,
        )

    print("\nBaseline evaluation")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()