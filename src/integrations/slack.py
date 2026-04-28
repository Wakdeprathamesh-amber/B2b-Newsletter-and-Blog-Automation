"""Slack integration for notifications and status updates.

Sends notifications for:
- Cycle start/completion
- Stage progress updates
- Human gate approvals needed
- Errors and failures
- Content generation completion
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.settings import settings

log = structlog.get_logger()


class SlackClient:
    """Thin wrapper around Slack SDK for pipeline notifications."""

    def __init__(self) -> None:
        if not settings.slack_bot_token:
            log.warning("slack_not_configured", message="SLACK_BOT_TOKEN not set")
            self._client = None
            return

        self._client = WebClient(token=settings.slack_bot_token)
        self._channel = settings.slack_channel_id
        log.info("slack_connected", channel=self._channel)

    @property
    def is_available(self) -> bool:
        return self._client is not None and bool(self._channel)

    def _send(self, text: str, blocks: list[dict] | None = None) -> bool:
        """Send a message to the configured channel."""
        if not self.is_available:
            log.debug("slack_disabled", message=text)
            return False

        try:
            response = self._client.chat_postMessage(
                channel=self._channel,
                text=text,
                blocks=blocks,
            )
            log.info("slack_sent", channel=self._channel, ts=response["ts"])
            return True
        except SlackApiError as e:
            log.error("slack_failed", error=str(e), message=text)
            return False

    def _send_async(self, text: str, blocks: list[dict] | None = None) -> None:
        """Send message asynchronously (fire and forget)."""
        asyncio.create_task(asyncio.to_thread(self._send, text, blocks))

    # ── Cycle notifications ──────────────────────────────────────────────

    def notify_cycle_started(self, cycle_id: str) -> bool:
        """Notify that a new cycle has started."""
        text = f"🚀 New cycle started: `{cycle_id}`"
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚀 New Cycle Started"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Cycle ID:*\n`{cycle_id}`"},
                    {"type": "mrkdwn", "text": f"*Started:*\n{_now()}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Phase 1 running: Scraping signals → Ranking topics → Shortlisting",
                },
            },
        ]
        return self._send(text, blocks)

    def notify_cycle_completed(
        self, cycle_id: str, counts: dict[str, int], duration_min: int
    ) -> bool:
        """Notify that a cycle has completed successfully."""
        text = f"✅ Cycle completed: `{cycle_id}`"
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Cycle Completed"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Cycle ID:*\n`{cycle_id}`"},
                    {"type": "mrkdwn", "text": f"*Duration:*\n{duration_min} min"},
                ],
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Signals:*\n{counts.get('signals', 0)}"},
                    {"type": "mrkdwn", "text": f"*Ranked:*\n{counts.get('ranked', 0)}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Shortlisted:*\n{counts.get('shortlisted', 0)}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 <https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}|Open Google Sheet> to review topics",
                },
            },
        ]
        return self._send(text, blocks)

    def notify_cycle_failed(self, cycle_id: str, error: str) -> bool:
        """Notify that a cycle has failed."""
        text = f"❌ Cycle failed: `{cycle_id}`"
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "❌ Cycle Failed"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Cycle ID:*\n`{cycle_id}`"},
                    {"type": "mrkdwn", "text": f"*Failed at:*\n{_now()}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Error:*\n```{error[:500]}```"},
            },
        ]
        return self._send(text, blocks)

    # ── Stage progress ───────────────────────────────────────────────────

    def notify_stage_progress(self, cycle_id: str, stage: str, message: str) -> bool:
        """Send a progress update for a specific stage."""
        text = f"⏳ {stage}: {message}"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⏳ *{stage}*\n{message}\n`{cycle_id}`",
                },
            },
        ]
        return self._send(text, blocks)

    # ── Content generation ───────────────────────────────────────────────

    def notify_content_generated(
        self, cycle_id: str, channel: str, count: int
    ) -> bool:
        """Notify that content generation is complete."""
        emoji = {
            "newsroom": "📰",
            "linkedin": "💼",
            "blog": "📝",
            "newsletter": "📧",
        }.get(channel, "✅")

        text = f"{emoji} {channel.title()} content generated: {count} items"
        blocks = [
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Channel:*\n{channel.title()}"},
                    {"type": "mrkdwn", "text": f"*Items:*\n{count}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 <https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}|Open Google Sheet> to review content",
                },
            },
        ]
        return self._send(text, blocks)

    # ── Human gates ──────────────────────────────────────────────────────

    def notify_gate1_waiting(self, cycle_id: str, topic_count: int) -> bool:
        """Notify that Gate 1 (topic approval) is waiting for human review."""
        text = f"⏸️ Gate 1: {topic_count} topics awaiting approval"
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⏸️ Gate 1: Topic Approval Needed"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Cycle ID:*\n`{cycle_id}`"},
                    {"type": "mrkdwn", "text": f"*Topics:*\n{topic_count}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 <https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}|Open Google Sheet> to review and tag topics\n\n"
                    "*Instructions:*\n"
                    "• Set `decision` to Approve or Reject\n"
                    "• Set `channels`: Newsroom, LinkedIn, Blog, Newsletter\n"
                    "• If LinkedIn → pick `linkedin_voice`\n"
                    "• If Blog → pick `blog_lens`",
                },
            },
        ]
        return self._send(text, blocks)

    def notify_gate2_waiting(
        self, cycle_id: str, draft_counts: dict[str, int]
    ) -> bool:
        """Notify that Gate 2 (content review) is waiting for human review."""
        total = sum(draft_counts.values())
        text = f"⏸️ Gate 2: {total} drafts awaiting review"

        fields = [
            {"type": "mrkdwn", "text": f"*Cycle ID:*\n`{cycle_id}`"},
            {"type": "mrkdwn", "text": f"*Total Drafts:*\n{total}"},
        ]
        for channel, count in draft_counts.items():
            if count > 0:
                fields.append(
                    {"type": "mrkdwn", "text": f"*{channel.title()}:*\n{count}"}
                )

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⏸️ Gate 2: Content Review Needed"},
            },
            {"type": "section", "fields": fields},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 <https://docs.google.com/spreadsheets/d/{settings.google_master_sheet_id}|Open Google Sheet> to review content",
                },
            },
        ]
        return self._send(text, blocks)

    # ── Errors ───────────────────────────────────────────────────────────

    def notify_error(self, cycle_id: str, stage: str, error: str) -> bool:
        """Send an error notification."""
        text = f"⚠️ Error in {stage}: {error[:100]}"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Error in {stage}*\n`{cycle_id}`\n```{error[:500]}```",
                },
            },
        ]
        return self._send(text, blocks)

    # ── Simple text messages ─────────────────────────────────────────────

    def send_message(self, message: str) -> bool:
        """Send a simple text message."""
        return self._send(message)

    def send_message_async(self, message: str) -> None:
        """Send a simple text message asynchronously."""
        self._send_async(message)


# ── Helpers ──────────────────────────────────────────────────────────────


def _now() -> str:
    """Return current time in human-readable format."""
    return datetime.utcnow().strftime("%-d %b %Y %H:%M UTC")


# ── Singleton instance ───────────────────────────────────────────────────

_slack_client: SlackClient | None = None


def get_slack_client() -> SlackClient:
    """Get or create the singleton Slack client."""
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackClient()
    return _slack_client
