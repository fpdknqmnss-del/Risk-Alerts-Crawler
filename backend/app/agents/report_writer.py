from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.agents.llm_provider import LLMProviderFactory, try_parse_json
from app.models.alert import Alert, AlertCategory


class ReportWriterAgent:
    def __init__(self, llm_factory: LLMProviderFactory | None = None) -> None:
        self.llm_factory = llm_factory or LLMProviderFactory()

    async def compose_report_content(
        self,
        alerts: list[Alert],
        geographic_scope: str | None,
        date_range_start: datetime,
        date_range_end: datetime,
    ) -> dict[str, Any]:
        fallback_content = self._build_fallback_content(
            alerts=alerts,
            geographic_scope=geographic_scope,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )

        chat_model = self.llm_factory.build_chat_model(temperature=0.2)
        if chat_model is None or not alerts:
            return fallback_content

        prompt = self._build_prompt(
            alerts=alerts,
            geographic_scope=geographic_scope,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            fallback_content=fallback_content,
        )
        try:
            if hasattr(chat_model, "ainvoke"):
                response = await chat_model.ainvoke(prompt)
            else:
                response = await asyncio.to_thread(chat_model.invoke, prompt)
        except Exception:
            return fallback_content

        parsed = try_parse_json(getattr(response, "content", response))
        if not parsed:
            return fallback_content

        return self._merge_with_fallback(parsed, fallback_content)

    def _build_prompt(
        self,
        alerts: list[Alert],
        geographic_scope: str | None,
        date_range_start: datetime,
        date_range_end: datetime,
        fallback_content: dict[str, Any],
    ) -> str:
        compact_alerts = [
            {
                "id": alert.id,
                "title": alert.title,
                "summary": alert.summary,
                "category": alert.category.value,
                "severity": alert.severity,
                "country": alert.country,
                "region": alert.region,
                "verified": alert.verified,
                "verification_score": alert.verification_score,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts[:40]
        ]

        return (
            "You are generating a travel risk report for operations teams.\n"
            "Respond with strict JSON only (no markdown).\n"
            "Keep the response factual, concise, and actionable.\n\n"
            "Required keys:\n"
            "- executive_summary: string\n"
            "- key_findings: string[] (3-7 bullets)\n"
            "- recommendations: string[] (3-6 items)\n"
            "- category_breakdown: [{category: string, count: int}]\n"
            "- country_breakdown: [{country: string, count: int}]\n"
            "- top_alert_ids: int[] (up to 8 ids from provided alerts)\n\n"
            f"Geographic scope: {geographic_scope or 'global'}\n"
            f"Date range start: {date_range_start.isoformat()}\n"
            f"Date range end: {date_range_end.isoformat()}\n\n"
            "Alerts JSON:\n"
            f"{json.dumps(compact_alerts, ensure_ascii=True)}\n\n"
            "Fallback baseline JSON (use as style reference only):\n"
            f"{json.dumps(fallback_content, ensure_ascii=True)}"
        )

    def _merge_with_fallback(
        self,
        parsed: dict[str, Any],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(fallback)
        merged["executive_summary"] = str(
            parsed.get("executive_summary", fallback["executive_summary"])
        ).strip()

        key_findings = parsed.get("key_findings")
        if isinstance(key_findings, list):
            merged["key_findings"] = [str(item).strip() for item in key_findings if item]

        recommendations = parsed.get("recommendations")
        if isinstance(recommendations, list):
            merged["recommendations"] = [
                str(item).strip() for item in recommendations if item
            ]

        category_breakdown = parsed.get("category_breakdown")
        if isinstance(category_breakdown, list):
            normalized_category_breakdown: list[dict[str, Any]] = []
            for row in category_breakdown:
                if not isinstance(row, dict):
                    continue
                category = row.get("category")
                count = row.get("count")
                if isinstance(category, str) and isinstance(count, int):
                    normalized_category_breakdown.append(
                        {"category": category, "count": count}
                    )
            if normalized_category_breakdown:
                merged["category_breakdown"] = normalized_category_breakdown

        country_breakdown = parsed.get("country_breakdown")
        if isinstance(country_breakdown, list):
            normalized_country_breakdown: list[dict[str, Any]] = []
            for row in country_breakdown:
                if not isinstance(row, dict):
                    continue
                country = row.get("country")
                count = row.get("count")
                if isinstance(country, str) and isinstance(count, int):
                    normalized_country_breakdown.append(
                        {"country": country, "count": count}
                    )
            if normalized_country_breakdown:
                merged["country_breakdown"] = normalized_country_breakdown

        top_alert_ids = parsed.get("top_alert_ids")
        if isinstance(top_alert_ids, list):
            merged["top_alert_ids"] = [int(alert_id) for alert_id in top_alert_ids[:8]]

        return merged

    def _build_fallback_content(
        self,
        alerts: list[Alert],
        geographic_scope: str | None,
        date_range_start: datetime,
        date_range_end: datetime,
    ) -> dict[str, Any]:
        severity_sorted_alerts = sorted(
            alerts,
            key=lambda alert: (alert.severity, alert.created_at),
            reverse=True,
        )
        top_alert_ids = [alert.id for alert in severity_sorted_alerts[:8]]

        category_counter = Counter(alert.category.value for alert in alerts)
        country_counter = Counter(alert.country for alert in alerts if alert.country)
        high_severity_count = sum(1 for alert in alerts if alert.severity >= 4)
        verified_count = sum(1 for alert in alerts if alert.verified)

        top_category = category_counter.most_common(1)[0][0] if category_counter else None
        top_country = country_counter.most_common(1)[0][0] if country_counter else None

        summary_parts: list[str] = []
        summary_parts.append(
            f"{len(alerts)} alerts were assessed between "
            f"{date_range_start.date().isoformat()} and {date_range_end.date().isoformat()}."
        )
        if high_severity_count:
            summary_parts.append(
                f"{high_severity_count} alerts were marked high severity (4-5)."
            )
        if top_category:
            summary_parts.append(f"The dominant category was {top_category.replace('_', ' ')}.")
        if top_country:
            summary_parts.append(f"Most incidents were concentrated in {top_country}.")
        if geographic_scope:
            summary_parts.append(f"Scope focus: {geographic_scope}.")

        recommendations = self._build_recommendations(
            category_counter=category_counter,
            high_severity_count=high_severity_count,
        )

        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "scope": geographic_scope or "global",
            "executive_summary": " ".join(summary_parts).strip()
            if summary_parts
            else "No significant travel risk developments detected in this period.",
            "key_findings": [
                f"Verified alerts: {verified_count}/{len(alerts)}",
                f"High severity alerts: {high_severity_count}",
                f"Countries impacted: {len(country_counter)}",
            ],
            "recommendations": recommendations,
            "category_breakdown": [
                {"category": category, "count": count}
                for category, count in category_counter.most_common()
            ],
            "country_breakdown": [
                {"country": country, "count": count}
                for country, count in country_counter.most_common(10)
            ],
            "top_alert_ids": top_alert_ids,
        }

    def _build_recommendations(
        self,
        category_counter: Counter[str],
        high_severity_count: int,
    ) -> list[str]:
        recommendations = [
            "Reconfirm traveler communication channels for in-country incident updates.",
            "Review contingency transport and accommodation alternatives for affected zones.",
        ]

        if high_severity_count > 0:
            recommendations.append(
                "Prioritize executive escalation and daily monitoring for high-severity events."
            )

        if category_counter.get(AlertCategory.NATURAL_DISASTER.value, 0) > 0:
            recommendations.append(
                "Validate evacuation routes and weather-related disruption procedures."
            )
        if category_counter.get(AlertCategory.HEALTH.value, 0) > 0:
            recommendations.append(
                "Reinforce traveler health advisories and local medical access guidance."
            )
        if category_counter.get(AlertCategory.POLITICAL.value, 0) > 0:
            recommendations.append(
                "Avoid non-essential travel near political gathering points and civic hubs."
            )
        if category_counter.get(AlertCategory.CIVIL_UNREST.value, 0) > 0:
            recommendations.append(
                "Increase route risk checks around protest-prone districts."
            )

        return recommendations[:6]
