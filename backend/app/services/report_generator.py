from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.report_writer import ReportWriterAgent
from app.config import settings
from app.models.alert import Alert
from app.models.report import Report, ReportStatus
from app.schemas.report import ReportGenerationRequest


@dataclass(slots=True)
class ReportGenerationResult:
    report: Report
    alerts_used: int


class ReportGeneratorService:
    def __init__(
        self,
        report_writer: ReportWriterAgent | None = None,
        output_directory: Path | None = None,
    ) -> None:
        self.report_writer = report_writer or ReportWriterAgent()
        configured_output_path = Path(settings.REPORT_OUTPUT_DIR)
        if output_directory:
            self.output_directory = output_directory
        elif configured_output_path.is_absolute():
            self.output_directory = configured_output_path
        else:
            self.output_directory = Path.cwd() / configured_output_path
        self.template_path = (
            Path(__file__).resolve().parent.parent / "templates" / "report_template.html"
        )

    async def generate_report(
        self,
        db: AsyncSession,
        created_by: int,
        payload: ReportGenerationRequest,
    ) -> ReportGenerationResult:
        await self._ensure_tables(db)

        date_range_start, date_range_end = self._resolve_date_range(
            payload.date_range_start,
            payload.date_range_end,
        )
        alerts = await self._fetch_alerts(
            db=db,
            payload=payload,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )
        if not alerts:
            raise ValueError("No alerts matched the selected report filters.")

        generated_content = await self.report_writer.compose_report_content(
            alerts=alerts,
            geographic_scope=payload.geographic_scope,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )
        report_content = self._build_report_content(
            alerts=alerts,
            generated_content=generated_content,
            geographic_scope=payload.geographic_scope,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )

        report = Report(
            title=payload.title or self._build_default_title(payload.geographic_scope),
            summary=report_content.get("executive_summary"),
            content_json=report_content,
            status=ReportStatus.DRAFT,
            created_by=created_by,
            geographic_scope=payload.geographic_scope,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )
        db.add(report)
        await db.flush()

        if payload.generate_pdf:
            html_content = self.render_report_html(report=report, report_content=report_content)
            pdf_filename = self._build_pdf_filename(report.id, report.title)
            pdf_output_path = self.output_directory / pdf_filename
            self.generate_pdf(html_content, pdf_output_path)
            report.pdf_path = pdf_filename
            await db.flush()

        await db.refresh(report)
        return ReportGenerationResult(report=report, alerts_used=len(alerts))

    def render_report_html(self, report: Report, report_content: dict[str, Any]) -> str:
        template = self._load_template()

        key_findings_list = self._render_list_items(
            report_content.get("key_findings", []),
            empty_label="No key findings available.",
        )
        recommendations_list = self._render_list_items(
            report_content.get("recommendations", []),
            empty_label="No recommendations available.",
        )
        category_rows = self._render_breakdown_rows(
            report_content.get("category_breakdown", []),
            key_column="category",
            value_label="Category",
        )
        country_rows = self._render_breakdown_rows(
            report_content.get("country_breakdown", []),
            key_column="country",
            value_label="Country",
        )
        alert_rows = self._render_alert_rows(report_content.get("top_alerts", []))

        replacements = {
            "title": escape(report.title),
            "created_at": report.created_at.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            "date_range_start": (
                report.date_range_start.date().isoformat()
                if report.date_range_start
                else "N/A"
            ),
            "date_range_end": (
                report.date_range_end.date().isoformat() if report.date_range_end else "N/A"
            ),
            "geographic_scope": escape(report.geographic_scope or "Global"),
            "status": report.status.value.replace("_", " ").title(),
            "summary": escape(str(report_content.get("executive_summary", ""))),
            "alerts_total": str(report_content.get("total_alerts", 0)),
            "alerts_high_severity": str(report_content.get("high_severity_alerts", 0)),
            "alerts_verified": str(report_content.get("verified_alerts", 0)),
            "key_findings": key_findings_list,
            "recommendations": recommendations_list,
            "category_breakdown_rows": category_rows,
            "country_breakdown_rows": country_rows,
            "top_alert_rows": alert_rows,
        }

        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered

    def generate_pdf(self, html_content: str, output_path: Path) -> None:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        from weasyprint import HTML

        HTML(string=html_content, base_url=str(self.template_path.parent)).write_pdf(
            str(output_path)
        )

    async def _fetch_alerts(
        self,
        db: AsyncSession,
        payload: ReportGenerationRequest,
        date_range_start: datetime,
        date_range_end: datetime,
    ) -> list[Alert]:
        filters = [
            Alert.created_at >= date_range_start,
            Alert.created_at <= date_range_end,
        ]

        if payload.categories:
            filters.append(Alert.category.in_(payload.categories))

        if payload.geographic_scope:
            scope = f"%{payload.geographic_scope.strip()}%"
            filters.append(
                or_(
                    Alert.country.ilike(scope),
                    Alert.region.ilike(scope),
                )
            )

        if not payload.include_unverified:
            filters.append(Alert.verified.is_(True))

        query = (
            select(Alert)
            .where(*filters)
            .order_by(Alert.severity.desc(), Alert.created_at.desc())
            .limit(payload.max_alerts)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _ensure_tables(self, db: AsyncSession) -> None:
        await db.run_sync(
            lambda sync_session: Alert.__table__.create(
                bind=sync_session.connection(),
                checkfirst=True,
            )
        )
        await db.run_sync(
            lambda sync_session: Report.__table__.create(
                bind=sync_session.connection(),
                checkfirst=True,
            )
        )

    def _build_report_content(
        self,
        alerts: list[Alert],
        generated_content: dict[str, Any],
        geographic_scope: str | None,
        date_range_start: datetime,
        date_range_end: datetime,
    ) -> dict[str, Any]:
        top_alert_ids = {
            int(alert_id)
            for alert_id in generated_content.get("top_alert_ids", [])
            if isinstance(alert_id, int)
        }
        sorted_alerts = sorted(
            alerts,
            key=lambda alert: (alert.severity, alert.created_at),
            reverse=True,
        )
        top_alerts = [alert for alert in sorted_alerts if alert.id in top_alert_ids][:8]
        if not top_alerts:
            top_alerts = sorted_alerts[:8]

        serialized_top_alerts = [self._serialize_alert(alert) for alert in top_alerts]
        verified_alerts = sum(1 for alert in alerts if alert.verified)
        high_severity_alerts = sum(1 for alert in alerts if alert.severity >= 4)

        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "geographic_scope": geographic_scope or "global",
            "date_range": {
                "start": date_range_start.date().isoformat(),
                "end": date_range_end.date().isoformat(),
            },
            "total_alerts": len(alerts),
            "verified_alerts": verified_alerts,
            "high_severity_alerts": high_severity_alerts,
            "executive_summary": generated_content.get("executive_summary"),
            "key_findings": generated_content.get("key_findings", []),
            "recommendations": generated_content.get("recommendations", []),
            "category_breakdown": generated_content.get("category_breakdown", []),
            "country_breakdown": generated_content.get("country_breakdown", []),
            "top_alerts": serialized_top_alerts,
        }

    def _serialize_alert(self, alert: Alert) -> dict[str, Any]:
        return {
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

    def _build_default_title(self, geographic_scope: str | None) -> str:
        scope_title = (geographic_scope or "Global").strip() or "Global"
        date_stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        return f"{scope_title} Travel Risk Report - {date_stamp}"

    def _build_pdf_filename(self, report_id: int, title: str) -> str:
        safe_title = "".join(char if char.isalnum() else "-" for char in title.lower())
        safe_title = "-".join(chunk for chunk in safe_title.split("-") if chunk).strip("-")
        safe_title = safe_title[:80] or "travel-risk-report"
        return f"report-{report_id}-{safe_title}.pdf"

    def _resolve_date_range(
        self,
        date_range_start: date | None,
        date_range_end: date | None,
    ) -> tuple[datetime, datetime]:
        today_utc = datetime.now(tz=timezone.utc).date()
        start_date = date_range_start or (today_utc - timedelta(days=7))
        end_date = date_range_end or today_utc
        return (
            datetime.combine(start_date, time.min, tzinfo=timezone.utc),
            datetime.combine(end_date, time.max, tzinfo=timezone.utc),
        )

    def _load_template(self) -> str:
        if self.template_path.exists():
            return self.template_path.read_text(encoding="utf-8")
        return self._default_template()

    def _render_list_items(self, values: Any, empty_label: str) -> str:
        if not isinstance(values, list) or not values:
            return f"<li>{escape(empty_label)}</li>"
        return "".join(f"<li>{escape(str(value))}</li>" for value in values if value)

    def _render_breakdown_rows(
        self,
        breakdown: Any,
        key_column: str,
        value_label: str,
    ) -> str:
        if not isinstance(breakdown, list) or not breakdown:
            return (
                "<tr>"
                f"<td>{escape(value_label)}</td>"
                "<td>0</td>"
                "</tr>"
            )

        rows: list[str] = []
        for item in breakdown:
            if not isinstance(item, dict):
                continue
            key_value = item.get(key_column)
            count = item.get("count")
            if key_value is None or count is None:
                continue
            rows.append(
                "<tr>"
                f"<td>{escape(str(key_value))}</td>"
                f"<td>{escape(str(count))}</td>"
                "</tr>"
            )
        return "".join(rows) if rows else "<tr><td>N/A</td><td>0</td></tr>"

    def _render_alert_rows(self, alerts: Any) -> str:
        if not isinstance(alerts, list) or not alerts:
            return (
                "<tr>"
                "<td colspan='5'>No alerts available for this report.</td>"
                "</tr>"
            )
        rows: list[str] = []
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            rows.append(
                "<tr>"
                f"<td>{escape(str(alert.get('title', '')))}</td>"
                f"<td>{escape(str(alert.get('category', '')))}</td>"
                f"<td>{escape(str(alert.get('severity', '')))}</td>"
                f"<td>{escape(str(alert.get('country', '')))}</td>"
                f"<td>{'Yes' if alert.get('verified') else 'No'}</td>"
                "</tr>"
            )
        return "".join(rows) if rows else "<tr><td colspan='5'>No alerts listed.</td></tr>"

    def _default_template(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{{title}}</title>
</head>
<body>
  <h1>{{title}}</h1>
  <p>{{summary}}</p>
</body>
</html>"""
