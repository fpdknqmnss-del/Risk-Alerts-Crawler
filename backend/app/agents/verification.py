from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.agents.llm_provider import LLMProviderFactory, try_parse_json
from app.sources.base import NormalizedNewsItem


@dataclass(slots=True)
class VerificationResult:
    verified: bool
    verification_score: float
    rationale: str


class VerificationAgent:
    def __init__(self, llm_factory: LLMProviderFactory | None = None) -> None:
        factory = llm_factory or LLMProviderFactory()
        self._chat_model = factory.build_chat_model(temperature=0.0)

    async def verify(self, item: NormalizedNewsItem) -> VerificationResult:
        if self._chat_model is None:
            return self._fallback_verification(item)

        prompt = (
            "You are a travel-risk verification analyst.\n"
            "Assess if this report appears credible for operational alerting.\n"
            "Return strict JSON with keys: verified (bool), verification_score (0 to 1), rationale (string).\n\n"
            f"Source: {item.source}\n"
            f"Title: {item.title}\n"
            f"URL: {item.url}\n"
            f"Published: {item.published_at}\n"
            f"Description: {item.description}\n"
            f"Content: {item.content}\n"
        )

        try:
            response = await asyncio.to_thread(self._chat_model.invoke, prompt)
            parsed = try_parse_json(getattr(response, "content", response))
            if parsed is None:
                return self._fallback_verification(item)

            score = float(parsed.get("verification_score", 0.0))
            score = min(max(score, 0.0), 1.0)
            verified = bool(parsed.get("verified", score >= 0.55))
            rationale = str(parsed.get("rationale") or "LLM verification output.")

            return VerificationResult(
                verified=verified,
                verification_score=score,
                rationale=rationale[:500],
            )
        except Exception:
            return self._fallback_verification(item)

    def _fallback_verification(self, item: NormalizedNewsItem) -> VerificationResult:
        score = 0.30
        if item.url.lower().startswith("https://"):
            score += 0.20
        if item.published_at is not None:
            score += 0.20
        if item.source and item.source.strip().lower() not in {"unknown", "rss"}:
            score += 0.15

        body_length = len((item.content or "") + " " + (item.description or ""))
        if body_length >= 120:
            score += 0.15

        score = min(max(score, 0.0), 0.95)
        verified = score >= 0.55
        rationale = "Heuristic verification based on source metadata completeness."
        return VerificationResult(verified=verified, verification_score=score, rationale=rationale)
