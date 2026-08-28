import json
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
TRAIN_PATH = Path("data/generative_fine_tuning/train.jsonl")
OUTPUT_DIR = Path("results/qwen_routing_lora")

MAX_LENGTH = 256
BATCH_SIZE = 1
EPOCHS = 5
LEARNING_RATE = 2e-4


class RoutingDataset(Dataset):
    def __init__(self, path, tokenizer):
        self.tokenizer = tokenizer
        self.examples = []

        with path.open(encoding="utf-8") as f:
            for line in f:
                self.examples.append(json.loads(line))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        row = self.examples[index]

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
            {
                "role": "assistant",
                "content": row["output"],
            },
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )

        encoded = self.tokenizer(
            text,
            truncation=True,
            max_length=MAX_LENGTH,
            padding="max_length",
            return_tensors="pt",
        )

        input_ids = encoded["input_ids"].squeeze(0)
        attention_mask = encoded["attention_mask"].squeeze(0)

        labels = input_ids.clone()
        labels[attention_mask == 0] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def main():
    torch.manual_seed(42)

    device = "mps" if torch.backends.mps.is_available() else "cpu"

    print(f"Loading {MODEL_NAME} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float32,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
        ],
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    model = model.to(device)

    model.print_trainable_parameters()

    dataset = RoutingDataset(TRAIN_PATH, tokenizer)

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    model.train()

    for epoch in range(EPOCHS):
        total_loss = 0.0

        for batch in loader:
            optimizer.zero_grad()

            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )

            loss = outputs.loss
            loss.backward()

            optimizer.step()

            total_loss += loss.item()

        average_loss = total_loss / len(loader)

        print(
            f"Epoch {epoch + 1}/{EPOCHS} "
            f"- loss: {average_loss:.4f}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"Saved LoRA adapter to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()