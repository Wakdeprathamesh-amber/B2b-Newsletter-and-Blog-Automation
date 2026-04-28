# Slack Integration Guide

*Real-time notifications for the Amber Content Engine*

---

## Overview

The Slack integration sends real-time notifications to your team about:
- ✅ Cycle start/completion
- ⏳ Stage progress updates
- ⏸️ Human gates (approval needed)
- 📊 Content generation completion
- ❌ Errors and failures

All notifications are sent to a single Slack channel configured in your `.env` file.

---

## Setup

### 1. Slack App Configuration

Your Slack app needs these **OAuth scopes**:
- `chat:write` — Send messages to channels
- `chat:write.public` — Send messages to public channels

### 2. Environment Variables

Add these to your `.env` file:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CHANNEL_ID=C0B01Q2BJF4
```

**Where to find these:**
- **Bot Token:** Slack App → OAuth & Permissions → Bot User OAuth Token
- **Signing Secret:** Slack App → Basic Information → App Credentials
- **Channel ID:** Right-click channel → View channel details → Copy ID

### 3. Test the Integration

```bash
python test_slack.py
```

Expected output:
```
🔍 Testing Slack Integration

Credentials:
  SLACK_BOT_TOKEN: ✅ Set
  SLACK_SIGNING_SECRET: ✅ Set
  SLACK_CHANNEL_ID: ✅ Set

Initializing Slack client...
✅ Slack client initialized (channel: C0B01Q2BJF4)

Sending test message...
✅ Test message sent successfully!

Check your Slack channel: C0B01Q2BJF4
```

---

## Notification Types

### 🚀 Cycle Started

Sent when a new cycle begins.

**Example:**
```
🚀 New Cycle Started

Cycle ID: cycle-20260427-143022
Started: 27 Apr 2026 14:30 UTC

Phase 1 running: Scraping signals → Ranking topics → Shortlisting
```

### ⏳ Stage Progress

Sent during long-running stages.

**Examples:**
```
⏳ Stage 1: Scraping signals... (cycle-20260427-143022)
⏳ Stage 2: Ranking 45 signals... (cycle-20260427-143022)
⏳ Generating Newsroom Blog from 38 topics... (cycle-20260427-143022)
```

### ✅ Cycle Completed

Sent when Phase 1 completes successfully.

**Example:**
```
✅ Cycle Completed

Cycle ID: cycle-20260427-143022
Duration: 12 min

Signals: 45
Ranked: 38
Shortlisted: 35

📊 Open Google Sheet to review topics
```

### ⏸️ Gate 1: Topic Approval Needed

Sent when topics are ready for human review.

**Example:**
```
⏸️ Gate 1: Topic Approval Needed

Cycle ID: cycle-20260427-143022
Topics: 38

📊 Open Google Sheet to review and tag topics

Instructions:
• Set decision to Approve or Reject
• Set channels: Newsroom, LinkedIn, Blog, Newsletter
• If LinkedIn → pick linkedin_voice
• If Blog → pick blog_lens
```

### 📰 Content Generated

Sent when content generation completes.

**Examples:**
```
📰 Newsroom content generated: 42 items
💼 LinkedIn content generated: 15 items
📝 Blog content generated: 3 items
📧 Newsletter content generated: 1 items
```

### ❌ Cycle Failed

Sent when a cycle fails.

**Example:**
```
❌ Cycle Failed

Cycle ID: cycle-20260427-143022
Failed at: 27 Apr 2026 14:45 UTC

Error:
All 45 signals were filtered out (PR/opinion/irrelevant). 
Check the Signals tab.
```

### ⚠️ Error Notification

Sent when a specific stage encounters an error.

**Example:**
```
⚠️ Error in LinkedIn Generation
cycle-20260427-143022

No topics tagged for LinkedIn. In the sheet, add 'LinkedIn' 
to the channels column.
```

### ⏸️ Cancelled by User

Sent when a user stops a running cycle.

**Example:**
```
⏸️ Cycle cancelled by user: cycle-20260427-143022
```

---

## Integration Points

### Web Interface (UI Routes)

All web interface actions send Slack notifications:

| Action | Notifications Sent |
|--------|-------------------|
| Start New Cycle | 🚀 Cycle Started → ⏳ Progress → ✅ Completed → ⏸️ Gate 1 |
| Generate Newsroom | ⏳ Progress → 📰 Content Generated |
| Generate LinkedIn | ⏳ Progress → 💼 Content Generated |
| Generate Blog | ⏳ Progress → 📝 Content Generated |
| Generate Newsletter | ⏳ Progress → 📧 Content Generated |
| Stop | ⏸️ Cancelled |
| Any Error | ❌ Error Notification |

### CLI Scripts

CLI scripts (`run_phase1.py`, `run_phase2.py`) do NOT send Slack notifications by default. They only print to terminal.

To add Slack to CLI scripts, import and use the client:

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()
slack.send_message("🚀 Starting Phase 1 from CLI...")
```

---

## API Reference

### SlackClient Class

Located in `src/integrations/slack.py`

#### Methods

**`notify_cycle_started(cycle_id: str) -> bool`**
- Notify that a new cycle has started
- Returns `True` if sent successfully

**`notify_cycle_completed(cycle_id: str, counts: dict, duration_min: int) -> bool`**
- Notify that a cycle completed successfully
- `counts`: dict with keys `signals`, `ranked`, `shortlisted`
- `duration_min`: cycle duration in minutes

**`notify_cycle_failed(cycle_id: str, error: str) -> bool`**
- Notify that a cycle failed
- `error`: error message (truncated to 500 chars)

**`notify_stage_progress(cycle_id: str, stage: str, message: str) -> bool`**
- Send a progress update for a specific stage
- `stage`: stage name (e.g., "Stage 1", "Newsroom Generation")
- `message`: progress message

**`notify_content_generated(cycle_id: str, channel: str, count: int) -> bool`**
- Notify that content generation is complete
- `channel`: "newsroom", "linkedin", "blog", or "newsletter"
- `count`: number of items generated

**`notify_gate1_waiting(cycle_id: str, topic_count: int) -> bool`**
- Notify that Gate 1 (topic approval) is waiting
- `topic_count`: number of topics awaiting review

**`notify_gate2_waiting(cycle_id: str, draft_counts: dict) -> bool`**
- Notify that Gate 2 (content review) is waiting
- `draft_counts`: dict with keys for each channel

**`notify_error(cycle_id: str, stage: str, error: str) -> bool`**
- Send an error notification
- `stage`: stage name where error occurred
- `error`: error message (truncated to 500 chars)

**`send_message(message: str) -> bool`**
- Send a simple text message
- Synchronous (blocks until sent)

**`send_message_async(message: str) -> None`**
- Send a simple text message asynchronously
- Fire-and-forget (doesn't block)

#### Properties

**`is_available -> bool`**
- Returns `True` if Slack is configured and ready

---

## Usage Examples

### Basic Usage

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()

# Simple message
slack.send_message("Hello from Amber!")

# Async message (fire and forget)
slack.send_message_async("Background task started...")

# Check if available
if slack.is_available:
    slack.send_message("Slack is configured!")
```

### Cycle Notifications

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()
cycle_id = "cycle-20260427-143022"

# Start
slack.notify_cycle_started(cycle_id)

# Progress
slack.notify_stage_progress(cycle_id, "Stage 1", "Scraping 45 signals...")

# Complete
slack.notify_cycle_completed(
    cycle_id,
    counts={"signals": 45, "ranked": 38, "shortlisted": 35},
    duration_min=12
)

# Or failed
slack.notify_cycle_failed(cycle_id, "All signals filtered out")
```

### Content Generation

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()
cycle_id = "cycle-20260427-143022"

# Newsroom
slack.notify_content_generated(cycle_id, "newsroom", 42)

# LinkedIn
slack.notify_content_generated(cycle_id, "linkedin", 15)

# Blog
slack.notify_content_generated(cycle_id, "blog", 3)

# Newsletter
slack.notify_content_generated(cycle_id, "newsletter", 1)
```

### Error Handling

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()
cycle_id = "cycle-20260427-143022"

try:
    # Some operation
    result = do_something()
except Exception as e:
    slack.notify_error(cycle_id, "Stage Name", str(e))
    raise
```

---

## Troubleshooting

### "Slack is not configured"

**Cause:** Missing environment variables.

**Fix:**
1. Check `.env` file has all three variables:
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
   - `SLACK_CHANNEL_ID`
2. Restart the server after updating `.env`

### "channel_not_found"

**Cause:** Invalid channel ID or bot not invited to channel.

**Fix:**
1. Verify channel ID is correct (right-click channel → View details → Copy ID)
2. Invite the bot to the channel: `/invite @YourBotName`

### "not_authed" or "invalid_auth"

**Cause:** Invalid bot token.

**Fix:**
1. Go to Slack App → OAuth & Permissions
2. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
3. Update `SLACK_BOT_TOKEN` in `.env`
4. Restart the server

### "missing_scope"

**Cause:** Bot doesn't have required permissions.

**Fix:**
1. Go to Slack App → OAuth & Permissions
2. Add these scopes:
   - `chat:write`
   - `chat:write.public`
3. Reinstall the app to your workspace
4. Copy the new bot token to `.env`

### Messages not appearing

**Cause:** Bot not in channel or wrong channel ID.

**Fix:**
1. Invite bot to channel: `/invite @YourBotName`
2. Verify channel ID in `.env` matches the channel
3. Run `python test_slack.py` to verify

### Rate limiting

**Cause:** Too many messages sent too quickly.

**Fix:**
- Slack allows ~1 message per second per channel
- The integration uses async sending to avoid blocking
- If you hit rate limits, add delays between messages

---

## Best Practices

### 1. Use Async for Non-Critical Messages

```python
# Blocking (waits for Slack API)
slack.send_message("Important: Cycle failed!")

# Non-blocking (fire and forget)
slack.send_message_async("Progress update...")
```

### 2. Keep Messages Concise

- Use structured blocks for rich formatting
- Truncate long error messages
- Link to Google Sheet for details

### 3. Don't Spam

- Send progress updates only for long-running stages (>30 seconds)
- Batch related notifications when possible
- Use async sending for non-critical updates

### 4. Handle Failures Gracefully

```python
success = slack.send_message("Important notification")
if not success:
    # Log to file or database as fallback
    log.warning("slack_failed", message="Important notification")
```

### 5. Test Before Deploying

```bash
# Always test after configuration changes
python test_slack.py
```

---

## Configuration Options

### Multiple Channels

To send different notifications to different channels, modify `src/integrations/slack.py`:

```python
class SlackClient:
    def __init__(self):
        self._client = WebClient(token=settings.slack_bot_token)
        self._default_channel = settings.slack_channel_id
        self._error_channel = settings.slack_error_channel_id  # Add to settings
        
    def notify_error(self, cycle_id: str, stage: str, error: str):
        # Send errors to dedicated error channel
        return self._send(text, blocks, channel=self._error_channel)
```

### Custom Message Formatting

Modify the `blocks` in each notification method to customize appearance:

```python
def notify_cycle_started(self, cycle_id: str):
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚀 Custom Header"},
        },
        # Add more blocks...
    ]
    return self._send(text, blocks)
```

See [Slack Block Kit Builder](https://app.slack.com/block-kit-builder) for interactive design.

---

## Monitoring

### Check Slack Status

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()
print(f"Slack available: {slack.is_available}")
```

### View Sent Messages

- Open your Slack channel
- All messages from the bot appear with the bot's name/icon
- Click on a message to see timestamp and thread

### Logs

All Slack operations are logged via `structlog`:

```
slack_connected channel=C0B01Q2BJF4
slack_sent channel=C0B01Q2BJF4 ts=1714234567.123456
slack_failed error="channel_not_found" message="Test message"
```

---

## Security

### Token Safety

- ✅ **DO:** Store tokens in `.env` (never commit to git)
- ✅ **DO:** Use environment variables in production
- ✅ **DO:** Rotate tokens if compromised
- ❌ **DON'T:** Hardcode tokens in source code
- ❌ **DON'T:** Share tokens in chat or email
- ❌ **DON'T:** Commit `.env` to version control

### Permissions

- Only grant `chat:write` scope (minimum required)
- Don't grant admin or user scopes unless needed
- Review app permissions regularly

### Channel Access

- Use a dedicated channel for bot notifications
- Restrict channel access to team members only
- Don't send sensitive data (API keys, passwords) via Slack

---

## Next Steps

1. **Test the integration:** `python test_slack.py`
2. **Start a cycle:** Watch notifications appear in Slack
3. **Customize messages:** Edit `src/integrations/slack.py`
4. **Add more channels:** Extend for errors, alerts, etc.

---

## Support

**Documentation:**
- [Slack API Docs](https://api.slack.com/docs)
- [Block Kit Builder](https://app.slack.com/block-kit-builder)
- [OAuth Scopes](https://api.slack.com/scopes)

**Files:**
- `src/integrations/slack.py` — Integration code
- `src/settings.py` — Configuration
- `test_slack.py` — Test script
- `.env` — Credentials (not in git)

**Logs:**
- Terminal output (real-time)
- Check for `slack_*` log entries
