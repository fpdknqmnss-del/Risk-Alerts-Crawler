from __future__ import annotations

import asyncio

from app.agents.classifier import ClassificationResult
from app.agents.llm_provider import LLMProviderFactory
from app.agents.severity_scorer import SeverityScoreResult
from app.agents.verification import VerificationResult
from app.sources.base import NormalizedNewsItem


class SummarizationAgent:
    def __init__(self, llm_factory: LLMProviderFactory | None = None) -> None:
        factory = llm_factory or LLMProviderFactory()
        self._chat_model = factory.build_chat_model(temperature=0.2)

    async def summarize(
        self,
        item: NormalizedNewsItem,
        classification: ClassificationResult,
        severity: SeverityScoreResult,
        verification: VerificationResult,
        max_chars: int = 450,
    ) -> str:
        if self._chat_model is None:
            return self._fallback_summary(item, classification, severity, max_chars=max_chars)

        prompt = (
            "Write a concise factual summary for a traveler risk alert.\n"
            f"Keep it under {max_chars} characters, no speculation.\n\n"
            f"Title: {item.title}\n"
            f"Description: {item.description}\n"
            f"Content: {item.content}\n"
            f"Category: {classification.category.value}\n"
            f"Country: {classification.country or item.country or 'Unknown'}\n"
            f"Region: {classification.region or item.region or 'Unknown'}\n"
            f"Severity: {severity.severity}\n"
            f"Verified: {verification.verified}\n"
            f"Verification score: {verification.verification_score}\n"
        )

        try:
            response = await asyncio.to_thread(self._chat_model.invoke, prompt)
            summary = str(getattr(response, "content", response)).strip()
            if summary:
                return summary[:max_chars]
        except Exception:
            pass

        return self._fallback_summary(item, classification, severity, max_chars=max_chars)

    def _fallback_summary(
        self,
        item: NormalizedNewsItem,
        classification: ClassificationResult,
        severity: SeverityScoreResult,
        max_chars: int,
    ) -> str:
        location = classification.region or classification.country or item.region or item.country
        location_text = f" in {location}" if location else ""
        detail = item.description or item.content or ""
        detail = " ".join(detail.split())
        base = (
            f"{item.title}. Classified as {classification.category.value.replace('_', ' ')}"
            f"{location_text} with severity {severity.severity}/5."
        )
        if detail:
            base = f"{base} {detail}"
        return base[:max_chars]
