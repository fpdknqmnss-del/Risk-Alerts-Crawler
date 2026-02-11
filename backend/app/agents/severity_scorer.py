from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.agents.classifier import ClassificationResult
from app.agents.llm_provider import LLMProviderFactory, try_parse_json
from app.agents.verification import VerificationResult
from app.models.alert import AlertCategory
from app.sources.base import NormalizedNewsItem

_BASE_SEVERITY_BY_CATEGORY: dict[AlertCategory, int] = {
    AlertCategory.NATURAL_DISASTER: 3,
    AlertCategory.POLITICAL: 3,
    AlertCategory.CRIME: 2,
    AlertCategory.HEALTH: 3,
    AlertCategory.TERRORISM: 4,
    AlertCategory.CIVIL_UNREST: 3,
}

_HIGH_RISK_TERMS = ("emergency", "evacuate", "critical", "massive", "major", "fatal")
_ESCALATION_TERMS = ("airport", "border", "tourist", "embassy", "nationwide", "capital")


@dataclass(slots=True)
class SeverityScoreResult:
    severity: int
    rationale: str


class SeverityScorerAgent:
    def __init__(self, llm_factory: LLMProviderFactory | None = None) -> None:
        factory = llm_factory or LLMProviderFactory()
        self._chat_model = factory.build_chat_model(temperature=0.0)

    async def score(
        self,
        item: NormalizedNewsItem,
        classification: ClassificationResult,
        verification: VerificationResult,
    ) -> SeverityScoreResult:
        if self._chat_model is None:
            return self._fallback_score(item, classification, verification)

        prompt = (
            "You score travel risk severity from 1 (low) to 5 (critical).\n"
            "Return strict JSON with keys: severity (int 1-5), rationale (string).\n\n"
            f"Title: {item.title}\n"
            f"Description: {item.description}\n"
            f"Content: {item.content}\n"
            f"Category: {classification.category.value}\n"
            f"Verified: {verification.verified}\n"
            f"Verification score: {verification.verification_score}\n"
        )

        try:
            response = await asyncio.to_thread(self._chat_model.invoke, prompt)
            parsed = try_parse_json(getattr(response, "content", response))
            if parsed is None:
                return self._fallback_score(item, classification, verification)

            severity = int(parsed.get("severity", 3))
            severity = min(max(severity, 1), 5)
            rationale = str(parsed.get("rationale") or "LLM severity score.")
            return SeverityScoreResult(severity=severity, rationale=rationale[:500])
        except Exception:
            return self._fallback_score(item, classification, verification)

    def _fallback_score(
        self,
        item: NormalizedNewsItem,
        classification: ClassificationResult,
        verification: VerificationResult,
    ) -> SeverityScoreResult:
        severity = _BASE_SEVERITY_BY_CATEGORY.get(classification.category, 3)
        text = " ".join(part for part in [item.title, item.description, item.content] if part).lower()

        if any(term in text for term in _HIGH_RISK_TERMS):
            severity += 1
        if any(term in text for term in _ESCALATION_TERMS):
            severity += 1
        if verification.verification_score < 0.45:
            severity -= 1

        severity = min(max(severity, 1), 5)
        rationale = "Heuristic severity score from category, urgency indicators, and confidence."
        return SeverityScoreResult(severity=severity, rationale=rationale)
