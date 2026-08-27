import json
import random
from pathlib import Path
import torch.nn.functional as F

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)


MODEL_NAME = "distilbert-base-uncased"

LABELS = [
    "general",
    "sensitive",
    "technical",
    "retrieval",
]

LABEL_TO_ID = {
    label: index
    for index, label in enumerate(LABELS)
}

SEED = 42


def set_seed(seed: int = SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_jsonl(path):
    records = []

    with open(path, "r") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            records.append(json.loads(line))

    return records


class WorkloadDataset(Dataset):
    def __init__(
        self,
        records,
        tokenizer,
        max_length=128,
    ):
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]

        encoded = self.tokenizer(
            record["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )

        return {
            "input_ids": encoded[
                "input_ids"
            ].squeeze(0),
            "attention_mask": encoded[
                "attention_mask"
            ].squeeze(0),
            "labels": torch.tensor(
                LABEL_TO_ID[record["label"]],
                dtype=torch.long,
            ),
        }

def evaluate(model, loader, device):
    model.eval()

    predictions = []
    labels = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)

            attention_mask = batch[
                "attention_mask"
            ].to(device)

            targets = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )

            preds = torch.argmax(
                outputs.logits,
                dim=-1,
            )

            predictions.extend(
                preds.cpu().tolist()
            )

            labels.extend(
                targets.cpu().tolist()
            )

    accuracy = accuracy_score(
        labels,
        predictions,
    )

    macro_f1 = f1_score(
        labels,
        predictions,
        average="macro",
        zero_division=0,
    )

    report = classification_report(
        labels,
        predictions,
        labels=list(range(len(LABELS))),
        target_names=LABELS,
        zero_division=0,
    )

    matrix = confusion_matrix(
        labels,
        predictions,
        labels=list(range(len(LABELS))),
    )

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "classification_report": report,
        "confusion_matrix": matrix,
    }

def evaluate_with_confidence(
    model,
    loader,
    device,
    confidence_threshold=0.65,
    sensitive_threshold=0.30,
):
    model.eval()

    predictions = []
    labels = []
    confidences = []
    escalated = 0
    sensitive_overrides = 0

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            targets = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )

            probabilities = F.softmax(
                outputs.logits,
                dim=-1,
            )

            for probs, target in zip(
                probabilities,
                targets,
            ):
                predicted_class = int(
                    torch.argmax(probs).item()
                )

                confidence = float(
                    torch.max(probs).item()
                )

                sensitive_probability = float(
                    probs[LABEL_TO_ID["sensitive"]].item()
                )

                if (
                    predicted_class
                    != LABEL_TO_ID["sensitive"]
                    and sensitive_probability
                    >= sensitive_threshold
                ):
                    predicted_class = LABEL_TO_ID["sensitive"]
                    sensitive_overrides += 1

                if confidence < confidence_threshold:
                    escalated += 1

                predictions.append(predicted_class)
                labels.append(int(target.item()))
                confidences.append(confidence)

    accuracy = accuracy_score(
        labels,
        predictions,
    )

    macro_f1 = f1_score(
        labels,
        predictions,
        average="macro",
        zero_division=0,
    )

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "average_confidence": sum(confidences) / len(confidences),
        "escalated": escalated,
        "escalation_rate": escalated / len(labels),
        "sensitive_overrides": sensitive_overrides,
    }


def train(
    model,
    loader,
    device,
    epochs=5,
    learning_rate=2e-5,
):
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
    )

    model.train()

    for epoch in range(epochs):
        total_loss = 0.0

        for batch in loader:
            optimizer.zero_grad()

            input_ids = batch["input_ids"].to(device)

            attention_mask = batch[
                "attention_mask"
            ].to(device)

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
            f"Epoch {epoch + 1}/{epochs} "
            f"loss: {average_loss:.4f}"
        )


def main():
    set_seed()

    project_root = Path(__file__).resolve().parents[1]

    train_path = (
        project_root
        / "data"
        / "fine_tuning"
        / "train.jsonl"
    )

    test_path = (
        project_root
        / "data"
        / "fine_tuning"
        / "test.jsonl"
    )

    train_records = load_jsonl(train_path)
    test_records = load_jsonl(test_path)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(LABELS),
    )

    if torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    
    print(f"Device: {device}")

    model.to(device)

    train_dataset = WorkloadDataset(
        train_records,
        tokenizer,
    )

    test_dataset = WorkloadDataset(
        test_records,
        tokenizer,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=4,
        shuffle=True,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=4,
        shuffle=False,
    )

    print("\nPretrained baseline")

    baseline_metrics = evaluate(
        model,
        test_loader,
        device,
    )

    print(
        f"Accuracy: "
        f"{baseline_metrics['accuracy']:.3f}"
    )

    print(
        f"Macro F1: "
        f"{baseline_metrics['macro_f1']:.3f}"
    )

    print("\nFine-tuning")

    train(
        model,
        train_loader,
        device,
    )
    
    print("\nFine-tuned model")

    tuned_metrics = evaluate(
        model,
        test_loader,
        device,
    )

    print(
        f"Accuracy: "
        f"{tuned_metrics['accuracy']:.3f}"
    )

    print(
        f"Macro F1: "
        f"{tuned_metrics['macro_f1']:.3f}"
    )
    print("\nClassification report")
    print(
        tuned_metrics["classification_report"]
    )

    print("Confusion matrix")
    print(
        tuned_metrics["confusion_matrix"]
    )


    confidence_metrics = evaluate_with_confidence(
        model=model,
        loader=test_loader,
        device=device,
        confidence_threshold=0.65,
        sensitive_threshold=0.30,
    )

    print("\nConfidence-aware evaluation")
    print(
     f"Accuracy: "
     f"{confidence_metrics['accuracy']:.3f}"
    )
    print(
     f"Macro F1: "
        f"{confidence_metrics['macro_f1']:.3f}"
    )
    print(
     f"Average confidence: "
     f"{confidence_metrics['average_confidence']:.3f}"
    )
    print(
     f"Escalated: "
     f"{confidence_metrics['escalated']}/{len(test_records)}"
    )
    print(
      f"Escalation rate: "
     f"{confidence_metrics['escalation_rate']:.3f}"
    )
    print(
      f"Sensitive overrides: "
     f"{confidence_metrics['sensitive_overrides']}"
    )

    print("\nChange")

    print(
        "Accuracy: "
        f"{baseline_metrics['accuracy']:.3f}"
        " -> "
        f"{tuned_metrics['accuracy']:.3f}"
    )

    print(
        "Macro F1: "
        f"{baseline_metrics['macro_f1']:.3f}"
        " -> "
        f"{tuned_metrics['macro_f1']:.3f}"
    )


if __name__ == "__main__":
    main()