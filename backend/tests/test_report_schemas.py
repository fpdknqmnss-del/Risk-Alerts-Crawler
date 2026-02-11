"""Tests for report Pydantic schema validation (backend/app/schemas/report.py).

No database needed – tests schema validation only.
"""

import unittest
from datetime import date

from pydantic import ValidationError

from app.models.alert import AlertCategory
from app.schemas.report import ReportGenerationRequest


class TestReportGenerationRequest(unittest.TestCase):
    """ReportGenerationRequest schema validation."""

    def test_report_generation_request_valid(self) -> None:
        """Valid payload passes validation."""
        payload = ReportGenerationRequest(
            title="Weekly Risk Report",
            geographic_scope="Asia Pacific",
            date_range_start=date(2025, 1, 1),
            date_range_end=date(2025, 1, 7),
            categories=[AlertCategory.HEALTH, AlertCategory.POLITICAL],
            max_alerts=100,
            include_unverified=False,
            generate_pdf=True,
        )
        self.assertEqual(payload.title, "Weekly Risk Report")
        self.assertEqual(payload.geographic_scope, "Asia Pacific")
        self.assertEqual(payload.date_range_start, date(2025, 1, 1))
        self.assertEqual(payload.date_range_end, date(2025, 1, 7))
        self.assertEqual(len(payload.categories), 2)
        self.assertEqual(payload.max_alerts, 100)
        self.assertFalse(payload.include_unverified)
        self.assertTrue(payload.generate_pdf)

    def test_report_generation_request_invalid_date_range(self) -> None:
        """End before start raises ValueError (Pydantic v2 wraps as ValidationError)."""
        with self.assertRaises((ValueError, ValidationError)) as ctx:
            ReportGenerationRequest(
                title="Invalid Report",
                date_range_start=date(2025, 1, 15),
                date_range_end=date(2025, 1, 10),
            )
        self.assertIn("date_range_end must be on or after date_range_start", str(ctx.exception))

    def test_report_generation_request_defaults(self) -> None:
        """Check default values."""
        payload = ReportGenerationRequest()
        self.assertIsNone(payload.title)
        self.assertIsNone(payload.geographic_scope)
        self.assertIsNone(payload.date_range_start)
        self.assertIsNone(payload.date_range_end)
        self.assertEqual(payload.categories, [])
        self.assertEqual(payload.max_alerts, 50)
        self.assertFalse(payload.include_unverified)
        self.assertTrue(payload.generate_pdf)


if __name__ == "__main__":
    unittest.main()
