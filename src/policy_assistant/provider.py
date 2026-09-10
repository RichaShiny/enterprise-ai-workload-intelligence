"""Optional provider-backed summaries for approved policy evidence.

Retrieval and abstention stay deterministic.  A provider can only rewrite the
already-selected evidence into a concise answer; it never chooses policy
sources or fills gaps where the retriever abstains.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CITATION_PATTERN = re.compile(r"\[([a-z0-9-]+) v([^\]\s]+)\]", re.IGNORECASE)


def validate_citations(text: str, evidence: list[dict]) -> list[dict] | None:
    """Return validated citations, or ``None`` when the summary is not traceable.

    This does not claim to prove every generated sentence is faithful. It stops a
    provider result from being displayed as grounded if it has no citation or
    refers to a policy document/version outside the retrieved evidence.
    """
    allowed = {
        (item["document_id"].lower(), str(item["version"]))
        for item in evidence
    }
    found = [(document_id.lower(), version) for document_id, version in CITATION_PATTERN.findall(text)]
    if not found or any(citation not in allowed for citation in found):
        return None
    return [
        {"document_id": document_id, "version": version}
        for document_id, version in dict.fromkeys(found)
    ]


class PolicySummaryProvider:
    """Call the OpenAI Responses API only when explicitly enabled by config."""

    def __init__(
        self,
        api_key: str | None = None,
        enabled: bool | None = None,
        model: str | None = None,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("POLICY_SUMMARY_ENABLED", "false").lower() == "true"
        )
        self.model = model or os.getenv("POLICY_SUMMARY_MODEL", "gpt-5-mini")
        self._opener = opener

    def status(self) -> dict:
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": "openai",
                "model": self.model,
                "reason": "Set POLICY_SUMMARY_ENABLED=true to allow provider-backed summaries.",
            }
        if not self.api_key:
            return {
                "status": "not_configured",
                "provider": "openai",
                "model": self.model,
                "reason": "Set OPENAI_API_KEY in the service environment before enabling summaries.",
            }
        return {"status": "ready", "provider": "openai", "model": self.model}

    def summarize(self, question: str, evidence: list[dict]) -> dict:
        """Return a provider summary, or a non-sensitive fallback state.

        The request deliberately contains only the submitted question and the
        approved excerpts selected for it. It is not persisted by this service,
        and ``store=false`` asks the provider not to retain the response.
        """
        provider_status = self.status()
        if provider_status["status"] != "ready":
            return provider_status

        sources = "\n\n".join(
            "[{document_id} v{version}] {title}: {excerpt}".format(**item)
            for item in evidence
        )
        payload = {
            "model": self.model,
            "store": False,
            "max_output_tokens": 220,
            "instructions": (
                "You summarize approved company-policy evidence. Use only the supplied "
                "sources. Do not add facts, assumptions, or instructions. If the sources "
                "do not fully answer the question, say that the policy owner should review it. "
                "Keep the answer under 120 words and cite every claim using the supplied "
                "[document_id vversion] labels."
            ),
            "input": f"Question: {question}\n\nApproved sources:\n{sources}",
        }
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            text = body.get("output_text", "").strip()
            if not text:
                raise ValueError("The provider returned no output text.")
            citations = validate_citations(text, evidence)
            if citations is None:
                return {
                    "status": "fallback",
                    "provider": "openai",
                    "model": self.model,
                    "reason": "Provider summary did not cite only the selected approved evidence.",
                }
            return {
                "status": "generated",
                "provider": "openai",
                "model": self.model,
                "answer": text,
                "citations": citations,
            }
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return {
                "status": "fallback",
                "provider": "openai",
                "model": self.model,
                "reason": "Provider summary was unavailable; use the cited evidence extract instead.",
            }
