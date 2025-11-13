"""
Notification system for critical events in Grokputer swarm.
Supports Email (SMTP) and Slack webhooks.
"""

import os
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    """Represents an alert notification."""

    def __init__(
        self, title: str, message: str, level: AlertLevel = AlertLevel.INFO, metadata: Optional[Dict[str, Any]] = None
    ):
        self.title = title
        self.message = message
        self.level = level
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def format_email_body(self) -> str:
        """Format alert as email body."""
        emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        body = f"""
{emoji.get(self.level.value, "")} GROKPUTER ALERT: {self.title}

Level: {self.level.value.upper()}
Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{self.message}

"""
        if self.metadata:
            body += "\nDetails:\n"
            for key, value in self.metadata.items():
                body += f"  • {key}: {value}\n"

        body += "\n---\nGrokputer Autonomous Swarm\nZA GROKA. ZA VRZIBRZI. ZA SERVER."
        return body

    def format_slack_payload(self) -> Dict[str, Any]:
        """Format alert as Slack webhook payload."""
        color_map = {
            AlertLevel.INFO: "#36a64f",  # green
            AlertLevel.WARNING: "#ff9900",  # orange
            AlertLevel.CRITICAL: "#ff0000",  # red
        }

        emoji_map = {
            AlertLevel.INFO: ":information_source:",
            AlertLevel.WARNING: ":warning:",
            AlertLevel.CRITICAL: ":rotating_light:",
        }

        fields = []
        if self.metadata:
            for key, value in self.metadata.items():
                fields.append({"title": key.replace("_", " ").title(), "value": str(value), "short": True})

        return {
            "text": f"{emoji_map[self.level]} *{self.title}*",
            "attachments": [
                {
                    "color": color_map[self.level],
                    "fields": [
                        {"title": "Level", "value": self.level.value.upper(), "short": True},
                        {"title": "Time", "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True},
                    ]
                    + fields,
                    "text": self.message,
                    "footer": "Grokputer Swarm",
                    "ts": int(self.timestamp.timestamp()),
                }
            ],
        }


class Notifier:
    """
    Multi-channel notification system.
    Sends alerts via Email and/or Slack based on configuration.
    """

    def __init__(
        self,
        enable_email: bool = None,
        enable_slack: bool = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        email_from: Optional[str] = None,
        email_to: Optional[List[str]] = None,
        slack_webhook_url: Optional[str] = None,
        min_level: AlertLevel = AlertLevel.WARNING,
    ):
        """
        Initialize notifier with email and Slack configuration.

        Args:
            enable_email: Enable email notifications (defaults to env ENABLE_EMAIL_ALERTS)
            enable_slack: Enable Slack notifications (defaults to env ENABLE_SLACK_ALERTS)
            smtp_host: SMTP server host (defaults to env SMTP_HOST)
            smtp_port: SMTP server port (defaults to env SMTP_PORT)
            smtp_user: SMTP username (defaults to env SMTP_USER)
            smtp_password: SMTP password (defaults to env SMTP_PASSWORD)
            email_from: From email address (defaults to env EMAIL_FROM)
            email_to: List of recipient emails (defaults to env EMAIL_TO, comma-separated)
            slack_webhook_url: Slack webhook URL (defaults to env SLACK_WEBHOOK_URL)
            min_level: Minimum alert level to send (INFO, WARNING, CRITICAL)
        """
        # Load from env or use provided
        self.enable_email = (
            enable_email if enable_email is not None else os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true"
        )
        self.enable_slack = (
            enable_slack if enable_slack is not None else os.getenv("ENABLE_SLACK_ALERTS", "false").lower() == "true"
        )

        # Email config
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.email_from = email_from or os.getenv("EMAIL_FROM", self.smtp_user)

        email_to_str = email_to or os.getenv("EMAIL_TO", "")
        self.email_to = email_to_str.split(",") if isinstance(email_to_str, str) else email_to_str

        # Slack config
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        # Alert level filtering
        self.min_level = min_level

        # Validation
        if self.enable_email and not all([self.smtp_user, self.smtp_password, self.email_to]):
            logger.warning(
                "Email alerts enabled but missing SMTP credentials or recipients. Email alerts will be disabled."
            )
            self.enable_email = False

        if self.enable_slack and not self.slack_webhook_url:
            logger.warning("Slack alerts enabled but SLACK_WEBHOOK_URL not set. Slack alerts will be disabled.")
            self.enable_slack = False

        logger.info(
            f"Notifier initialized: Email={self.enable_email}, Slack={self.enable_slack}, MinLevel={min_level.value}"
        )

    def should_send(self, alert: Alert) -> bool:
        """Check if alert meets minimum level threshold."""
        level_order = {AlertLevel.INFO: 0, AlertLevel.WARNING: 1, AlertLevel.CRITICAL: 2}
        return level_order[alert.level] >= level_order[self.min_level]

    async def send(self, alert: Alert) -> Dict[str, bool]:
        """
        Send alert via all enabled channels.

        Returns:
            Dict with results: {"email": bool, "slack": bool}
        """
        if not self.should_send(alert):
            logger.debug(f"Skipping alert (level {alert.level.value} < {self.min_level.value}): {alert.title}")
            return {"email": False, "slack": False}

        results = {}

        # Send email
        if self.enable_email:
            results["email"] = await self._send_email(alert)
        else:
            results["email"] = False

        # Send Slack
        if self.enable_slack:
            results["slack"] = await self._send_slack(alert)
        else:
            results["slack"] = False

        logger.info(f"Alert sent: {alert.title} | Email: {results['email']}, Slack: {results['slack']}")
        return results

    async def _send_email(self, alert: Alert) -> bool:
        """Send email via SMTP (async wrapper)."""

        def _smtp_send():
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[{alert.level.value.upper()}] {alert.title}"
                msg["From"] = self.email_from
                msg["To"] = ", ".join(self.email_to)

                body = alert.format_email_body()
                msg.attach(MIMEText(body, "plain"))

                # Connect and send
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

                return True
            except Exception as e:
                logger.error(f"Email send failed: {e}", exc_info=True)
                return False

        # Run blocking SMTP in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _smtp_send)

    async def _send_slack(self, alert: Alert) -> bool:
        """Send Slack webhook message."""
        try:
            payload = alert.format_slack_payload()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook_url, json=payload, headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Slack webhook failed: {response.status} - {await response.text()}")
                        return False
                    return True
        except Exception as e:
            logger.error(f"Slack send failed: {e}", exc_info=True)
            return False

    async def send_critical_proposal_alert(self, proposal_data: Dict[str, Any]):
        """
        Convenience method for critical proposal alerts.

        Args:
            proposal_data: Dict with keys: finding_id, severity, description, risk_level, etc.
        """
        alert = Alert(
            title=f"Critical Proposal: {proposal_data.get('finding_id', 'Unknown')}",
            message=f"A critical code proposal has been generated.\n\n{proposal_data.get('description', 'No description')}",
            level=AlertLevel.CRITICAL,
            metadata={
                "severity": proposal_data.get("severity", "unknown"),
                "risk_level": proposal_data.get("risk_level", "unknown"),
                "file": proposal_data.get("file_path", "unknown"),
                "auto_applied": proposal_data.get("auto_applied", False),
            },
        )
        return await self.send(alert)

    async def send_evolution_alert(self, evolution_data: Dict[str, Any]):
        """
        Convenience method for evolution alerts.

        Args:
            evolution_data: Dict with keys: agent, improvement, metric, old_value, new_value
        """
        improvement = evolution_data.get("improvement_percent", 0)

        # Determine level based on improvement
        if improvement >= 100:
            level = AlertLevel.CRITICAL
        elif improvement >= 50:
            level = AlertLevel.WARNING
        else:
            level = AlertLevel.INFO

        alert = Alert(
            title=f"Agent Evolution: {evolution_data.get('agent', 'Unknown')} +{improvement}%",
            message=f"Agent self-optimization detected significant improvement.\n\nMetric: {evolution_data.get('metric', 'unknown')}",
            level=level,
            metadata={
                "agent": evolution_data.get("agent", "unknown"),
                "metric": evolution_data.get("metric", "unknown"),
                "old_value": evolution_data.get("old_value", "N/A"),
                "new_value": evolution_data.get("new_value", "N/A"),
                "improvement": f"+{improvement}%",
            },
        )
        return await self.send(alert)

    async def send_yolo_apply_alert(self, apply_data: Dict[str, Any]):
        """
        Convenience method for auto-apply (yolo mode) alerts.

        Args:
            apply_data: Dict with keys: proposal_id, file_path, changes_made
        """
        alert = Alert(
            title=f"Auto-Apply: {apply_data.get('proposal_id', 'Unknown')}",
            message=f"Proposal automatically applied in YOLO mode.\n\nFile: {apply_data.get('file_path', 'unknown')}\nChanges: {apply_data.get('changes_made', 'unknown')}",
            level=AlertLevel.WARNING,
            metadata={
                "proposal_id": apply_data.get("proposal_id", "unknown"),
                "file": apply_data.get("file_path", "unknown"),
                "risk_level": apply_data.get("risk_level", "unknown"),
                "timestamp": datetime.now().isoformat(),
            },
        )
        return await self.send(alert)


# Example usage
if __name__ == "__main__":

    async def test_notifier():
        # Initialize with env vars
        notifier = Notifier(min_level=AlertLevel.INFO)

        # Test critical alert
        critical_alert = Alert(
            title="Security Vulnerability Detected",
            message="Shell injection vulnerability found in executor.py:141",
            level=AlertLevel.CRITICAL,
            metadata={"severity": "high", "file": "src/executor.py", "line": 141},
        )

        await notifier.send(critical_alert)

        # Test evolution alert
        await notifier.send_evolution_alert(
            {
                "agent": "scanner",
                "metric": "findings_detected",
                "old_value": 25,
                "new_value": 65,
                "improvement_percent": 160,
            }
        )

        # Test proposal alert
        await notifier.send_critical_proposal_alert(
            {
                "finding_id": "SEC-001",
                "severity": "critical",
                "description": "Fix command injection in bash executor",
                "risk_level": "medium",
                "file_path": "src/executor.py",
                "auto_applied": False,
            }
        )

    # Run test
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_notifier())
