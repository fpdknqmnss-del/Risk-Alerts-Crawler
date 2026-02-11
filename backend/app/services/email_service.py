from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from_email = settings.SMTP_FROM_EMAIL

    def send_report_email(
        self,
        recipient_email: str,
        report_title: str,
        report_summary: str | None = None,
        report_pdf_url: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.smtp_from_email
        message["To"] = recipient_email
        message["Subject"] = f"Travel Risk Report: {report_title}"

        summary = report_summary or "A new travel risk report is ready."
        body_parts = [
            "Hello,",
            "",
            f"A report has been published: {report_title}",
            "",
            "Summary:",
            summary,
        ]
        if report_pdf_url:
            body_parts.extend(["", f"Download PDF: {report_pdf_url}"])
        body_parts.extend(["", "Best regards,", "Risk Alerts Platform"])
        message.set_content("\n".join(body_parts))

        if self.smtp_port == 465:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
                self._smtp_login(smtp)
                smtp.send_message(message)
            return

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            self._smtp_login(smtp)
            smtp.send_message(message)

    def _smtp_login(self, smtp: smtplib.SMTP) -> None:
        if self.smtp_user and self.smtp_password:
            smtp.login(self.smtp_user, self.smtp_password)
