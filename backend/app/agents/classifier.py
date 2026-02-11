from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from app.agents.llm_provider import LLMProviderFactory, try_parse_json
from app.models.alert import AlertCategory
from app.sources.base import NormalizedNewsItem

_CATEGORY_KEYWORDS: dict[AlertCategory, tuple[str, ...]] = {
    AlertCategory.NATURAL_DISASTER: (
        "earthquake",
        "flood",
        "storm",
        "hurricane",
        "wildfire",
        "volcano",
        "tsunami",
        "landslide",
    ),
    AlertCategory.POLITICAL: (
        "election",
        "government",
        "diplomatic",
        "embassy",
        "sanction",
        "policy",
    ),
    AlertCategory.CRIME: (
        "robbery",
        "kidnap",
        "theft",
        "crime",
        "gang",
        "assault",
    ),
    AlertCategory.HEALTH: (
        "outbreak",
        "disease",
        "health",
        "virus",
        "epidemic",
        "pandemic",
        "cholera",
    ),
    AlertCategory.TERRORISM: (
        "terror",
        "bomb",
        "explosion",
        "extremist",
        "militant",
        "hostage",
    ),
    AlertCategory.CIVIL_UNREST: (
        "protest",
        "riot",
        "clash",
        "curfew",
        "civil unrest",
        "demonstration",
        "strike",
    ),
}

_COUNTRY_HINTS: dict[str, str] = {
    "usa": "United States",
    "u.s.": "United States",
    "united states": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "myanmar": "Myanmar",
    "thailand": "Thailand",
    "malaysia": "Malaysia",
    "singapore": "Singapore",
    "indonesia": "Indonesia",
    "philippines": "Philippines",
    "japan": "Japan",
    "china": "China",
    "india": "India",
}


@dataclass(slots=True)
class ClassificationResult:
    category: AlertCategory
    country: str | None
    region: str | None
    rationale: str


class ClassificationAgent:
    def __init__(self, llm_factory: LLMProviderFactory | None = None) -> None:
        factory = llm_factory or LLMProviderFactory()
        self._chat_model = factory.build_chat_model(temperature=0.0)

    async def classify(self, item: NormalizedNewsItem) -> ClassificationResult:
        if self._chat_model is None:
            return self._fallback_classification(item)

        prompt = (
            "Classify this travel-risk event.\n"
            "Allowed categories: natural_disaster, political, crime, health, terrorism, civil_unrest.\n"
            "Return strict JSON with keys: category, country, region, rationale.\n\n"
            f"Title: {item.title}\n"
            f"Description: {item.description}\n"
            f"Content: {item.content}\n"
            f"Existing country hint: {item.country}\n"
            f"Existing region hint: {item.region}\n"
        )

        try:
            response = await asyncio.to_thread(self._chat_model.invoke, prompt)
            parsed = try_parse_json(getattr(response, "content", response))
            if parsed is None:
                return self._fallback_classification(item)

            category = self._parse_category(parsed.get("category"))
            country = self._normalize_text(parsed.get("country")) or item.country
            region = self._normalize_text(parsed.get("region")) or item.region
            rationale = str(parsed.get("rationale") or "LLM category classification.")

            return ClassificationResult(
                category=category,
                country=country,
                region=region,
                rationale=rationale[:500],
            )
        except Exception:
            return self._fallback_classification(item)

    def _fallback_classification(self, item: NormalizedNewsItem) -> ClassificationResult:
        text = " ".join(
            part for part in [item.title, item.description, item.content, item.region] if part
        ).lower()

        top_category = AlertCategory.NATURAL_DISASTER
        top_score = -1
        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(text.count(keyword) for keyword in keywords)
            if score > top_score:
                top_score = score
                top_category = category

        country = item.country or self._extract_country_from_text(text)
        region = item.region
        rationale = "Heuristic keyword-based category and geography classification."
        return ClassificationResult(
            category=top_category,
            country=country,
            region=region,
            rationale=rationale,
        )

    def _parse_category(self, value: object) -> AlertCategory:
        normalized = self._normalize_text(value)
        if not normalized:
            return AlertCategory.NATURAL_DISASTER

        candidate = normalized.lower().replace(" ", "_")
        for category in AlertCategory:
            if category.value == candidate:
                return category
        return AlertCategory.NATURAL_DISASTER

    def _extract_country_from_text(self, text: str) -> str | None:
        for hint, country in _COUNTRY_HINTS.items():
            if re.search(rf"\b{re.escape(hint)}\b", text):
                return country
        return None

    def _normalize_text(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None
