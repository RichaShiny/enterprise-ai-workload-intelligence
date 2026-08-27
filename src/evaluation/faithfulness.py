from dataclasses import dataclass
from typing import List

import torch
from sentence_transformers import SentenceTransformer, util
from transformers import AutoModelForSequenceClassification, AutoTokenizer


@dataclass
class FaithfulnessResult:
    score: float
    supported_claims: int
    total_claims: int
    unsupported_claims: List[str]
    contradiction_claims: List[str]


class FaithfulnessEvaluator:
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        nli_model_name: str = "facebook/bart-large-mnli",
        support_threshold: float = 0.55,
        entailment_threshold: float = 0.60,
    ):
        self.embedding_model = SentenceTransformer(
            embedding_model_name
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            nli_model_name
        )

        self.nli_model = AutoModelForSequenceClassification.from_pretrained(
            nli_model_name
        )

        self.support_threshold = support_threshold
        self.entailment_threshold = entailment_threshold

    def evaluate(
        self,
        claims: List[str],
        retrieved_contexts: List[str],
    ) -> FaithfulnessResult:
        if not claims:
            return FaithfulnessResult(
                score=1.0,
                supported_claims=0,
                total_claims=0,
                unsupported_claims=[],
                contradiction_claims=[],
            )

        if not retrieved_contexts:
            return FaithfulnessResult(
                score=0.0,
                supported_claims=0,
                total_claims=len(claims),
                unsupported_claims=claims,
                contradiction_claims=[],
            )

        context_embeddings = self.embedding_model.encode(
            retrieved_contexts,
            convert_to_tensor=True,
        )

        claim_embeddings = self.embedding_model.encode(
            claims,
            convert_to_tensor=True,
        )

        similarity_matrix = util.cos_sim(
            claim_embeddings,
            context_embeddings,
        )

        supported_claims = 0
        unsupported_claims = []
        contradiction_claims = []

        for claim, similarities in zip(
            claims,
            similarity_matrix,
        ):
            best_context_index = int(
                similarities.argmax()
            )

            best_similarity = float(
                similarities[best_context_index]
            )

            best_context = retrieved_contexts[
                best_context_index
            ]

            if best_similarity < self.support_threshold:
                unsupported_claims.append(claim)
                continue

            nli_result = self._run_nli(
                premise=best_context,
                hypothesis=claim,
            )

            if (
                nli_result["label"] == "entailment"
                and nli_result["score"]
                >= self.entailment_threshold
            ):
                supported_claims += 1

            elif nli_result["label"] == "contradiction":
                contradiction_claims.append(claim)

            else:
                unsupported_claims.append(claim)

        score = supported_claims / len(claims)

        return FaithfulnessResult(
            score=score,
            supported_claims=supported_claims,
            total_claims=len(claims),
            unsupported_claims=unsupported_claims,
            contradiction_claims=contradiction_claims,
        )

    def _run_nli(
        self,
        premise: str,
        hypothesis: str,
    ) -> dict:
        inputs = self.tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
        )

        with torch.no_grad():
            outputs = self.nli_model(**inputs)

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1,
        )[0]

        labels = {
            0: "contradiction",
            1: "neutral",
            2: "entailment",
        }

        best_index = int(
            torch.argmax(probabilities)
        )

        return {
            "label": labels[best_index],
            "score": float(
                probabilities[best_index]
            ),
        }