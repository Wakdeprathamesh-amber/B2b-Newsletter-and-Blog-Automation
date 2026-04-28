# Slack Notification Flow

Visual guide to when and what notifications are sent.

---

## Phase 1: Start New Cycle

```
User clicks "Start New Cycle"
    ↓
🚀 Slack: "New cycle started: cycle-20260427-143022"
    ↓
Archive previous cycle (30-60 sec)
    ↓
⏳ Slack: "Stage 1: Scraping signals..."
    ↓
Scrape RSS + Google News (2-5 min)
    ↓
⏳ Slack: "Stage 2: Ranking 45 signals..."
    ↓
LLM ranks topics (2-5 min)
    ↓
Write to Google Sheet
    ↓
✅ Slack: "Cycle Completed"
         Duration: 12 min
         Signals: 45
         Ranked: 38
         Shortlisted: 35
    ↓
⏸️ Slack: "Gate 1: Topic Approval Needed"
         Topics: 38
         📊 Open Google Sheet to review
```

---

## Phase 2: Human Review (Manual)

```
User opens Google Sheet
    ↓
Reviews topics
    ↓
Sets decision: Approve/Reject
    ↓
Tags channels: Newsroom, LinkedIn, Blog, Newsletter
    ↓
Picks voices/lenses
    ↓
(No Slack notifications during manual review)
```

---

## Phase 3: Generate Newsroom Blog

```
User clicks "Newsroom Blog"
    ↓
⏳ Slack: "Generating Newsroom Blog from 38 topics..."
    ↓
LLM generates 7-12 items per region (2-3 min)
    ↓
Write to Google Sheet
    ↓
📰 Slack: "Newsroom content generated: 42 items"
         📊 Open Google Sheet to review
```

---

## Phase 3: Generate LinkedIn Posts

```
User clicks "LinkedIn Posts"
    ↓
⏳ Slack: "Generating LinkedIn posts from 5 topics..."
    ↓
LLM generates 5 topics × 3 voices = 15 posts (3-5 min)
    ↓
Write to Google Sheet
    ↓
💼 Slack: "LinkedIn content generated: 15 items"
         📊 Open Google Sheet to review
```

---

## Phase 3: Generate Blog Posts

```
User clicks "Blog Posts"
    ↓
⏳ Slack: "Generating Blog posts from 3 topics..."
    ↓
LLM generates 3 posts (2-4 min)
    ↓
Write to Google Sheet
    ↓
📝 Slack: "Blog content generated: 3 items"
         📊 Open Google Sheet to review
```

---

## Phase 3: Generate Newsletter

```
User clicks "Newsletter"
    ↓
⏳ Slack: "Generating Newsletter from 42 newsroom items..."
    ↓
LLM curates from newsroom blog (1-2 min)
    ↓
Write to Google Sheet
    ↓
📧 Slack: "Newsletter content generated: 1 items"
         📊 Open Google Sheet to review
```

---

## Error Scenarios

### All Signals Filtered Out

```
User clicks "Start New Cycle"
    ↓
🚀 Slack: "New cycle started..."
    ↓
Scrape signals
    ↓
All signals filtered (PR/opinion/irrelevant)
    ↓
❌ Slack: "Cycle Failed"
         Error: All 45 signals were filtered out.
         Check the Signals tab.
```

### No Topics Tagged for Channel

```
User clicks "LinkedIn Posts"
    ↓
Read topics from sheet
    ↓
No topics tagged with "LinkedIn"
    ↓
⚠️ Slack: "Error in LinkedIn Generation"
         No topics tagged for LinkedIn.
         Add 'LinkedIn' to channels column.
```

### LLM API Error

```
User clicks "Newsroom Blog"
    ↓
⏳ Slack: "Generating Newsroom Blog..."
    ↓
LLM API call fails
    ↓
⚠️ Slack: "Error in Newsroom Generation"
         OpenAI API error: Rate limit exceeded
```

### User Cancels

```
User clicks "Start New Cycle"
    ↓
🚀 Slack: "New cycle started..."
    ↓
⏳ Slack: "Stage 1: Scraping signals..."
    ↓
User clicks "Stop"
    ↓
⏸️ Slack: "Cycle cancelled by user: cycle-20260427-143022"
```

---

## Notification Timing

| Notification Type | When Sent | Blocking? |
|------------------|-----------|-----------|
| 🚀 Cycle Started | Immediately when cycle starts | No (async) |
| ⏳ Progress | Start of each long stage (>30 sec) | No (async) |
| ✅ Cycle Completed | After Phase 1 finishes | No (async) |
| ⏸️ Gate 1 Waiting | After Phase 1 finishes | No (async) |
| 📰 Content Generated | After content written to sheet | No (async) |
| ❌ Error | When error occurs | No (async) |
| ⏸️ Cancelled | When user clicks Stop | No (async) |

**All notifications are async (non-blocking)** — they don't slow down the pipeline!

---

## Message Format Examples

### Rich Formatted Message (Cycle Completed)

```
┌─────────────────────────────────────┐
│ ✅ Cycle Completed                  │
├─────────────────────────────────────┤
│ Cycle ID: cycle-20260427-143022     │
│ Duration: 12 min                    │
│                                     │
│ Signals: 45                         │
│ Ranked: 38                          │
│ Shortlisted: 35                     │
│                                     │
│ 📊 Open Google Sheet to review      │
│    topics                           │
└─────────────────────────────────────┘
```

### Simple Text Message (Progress)

```
⏳ Stage 1: Scraping signals... (cycle-20260427-143022)
```

### Error Message

```
┌─────────────────────────────────────┐
│ ⚠️ Error in LinkedIn Generation     │
├─────────────────────────────────────┤
│ cycle-20260427-143022               │
│                                     │
│ No topics tagged for LinkedIn.      │
│ In the sheet, add 'LinkedIn' to     │
│ the channels column.                │
└─────────────────────────────────────┘
```

---

## Notification Frequency

### Typical Cycle (15-30 min)

**Total notifications: 6-8**

1. 🚀 Cycle Started (1)
2. ⏳ Progress updates (2-3)
3. ✅ Cycle Completed (1)
4. ⏸️ Gate 1 Waiting (1)
5. ⏳ Content generation progress (1-2)
6. 📰 Content generated (1)

**Rate: ~1 notification every 3-5 minutes**

### Error Scenario

**Total notifications: 3-4**

1. 🚀 Cycle Started (1)
2. ⏳ Progress updates (1-2)
3. ❌ Error (1)

**Rate: ~1 notification per minute**

---

## Customization

### Change Notification Frequency

Edit `src/api/ui_routes.py`:

```python
# Current: Send progress at start of each stage
slack.send_message_async(f"⏳ Stage 1: Scraping...")

# Option 1: Remove progress updates (only start/complete/error)
# Comment out progress lines

# Option 2: Add more granular updates
slack.send_message_async(f"⏳ Scraped 10/45 signals...")
```

### Change Message Format

Edit `src/integrations/slack.py`:

```python
def notify_cycle_completed(self, cycle_id: str, counts: dict, duration_min: int):
    # Customize the blocks array
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🎉 Custom Header"},
        },
        # Add your custom blocks...
    ]
    return self._send(text, blocks)
```

### Add New Notification Types

Add methods to `SlackClient` class:

```python
def notify_custom_event(self, message: str):
    text = f"🔔 {message}"
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
    ]
    return self._send(text, blocks)
```

Then call from your code:

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()
slack.notify_custom_event("Custom event occurred!")
```

---

## Testing Notifications

### Test Individual Notifications

```python
from src.integrations.slack import get_slack_client

slack = get_slack_client()

# Test cycle started
slack.notify_cycle_started("test-cycle-001")

# Test progress
slack.notify_stage_progress("test-cycle-001", "Test Stage", "Testing...")

# Test completed
slack.notify_cycle_completed(
    "test-cycle-001",
    counts={"signals": 10, "ranked": 8, "shortlisted": 5},
    duration_min=5
)

# Test error
slack.notify_error("test-cycle-001", "Test Stage", "Test error message")
```

### Test Full Flow

```bash
# Start the server
python src/main.py

# Open web interface
# → http://localhost:8000

# Click "Start New Cycle"
# Watch Slack for notifications!
```

---

## Monitoring

### Check Notification Logs

Terminal output shows all Slack operations:

```
slack_connected channel=C0B01Q2BJF4
slack_sent channel=C0B01Q2BJF4 ts=1714234567.123456
slack_failed error="channel_not_found" message="Test message"
```

### Slack Message History

- Open your Slack channel
- All bot messages are timestamped
- Click message → "View thread" to see context

### Failed Notifications

If a notification fails:
1. Check terminal logs for error
2. Verify bot is in channel
3. Check bot token is valid
4. Run `python test_slack.py`

---

## Best Practices

### ✅ DO

- Use async sending for non-critical updates
- Keep messages concise and actionable
- Include links to Google Sheet
- Test after configuration changes
- Monitor for rate limiting

### ❌ DON'T

- Send notifications for every small step
- Include sensitive data (API keys, passwords)
- Spam the channel with too many messages
- Block the pipeline waiting for Slack
- Ignore failed notification logs

---

## Summary

**Notification Flow:**
```
Start Cycle → Progress → Complete → Gate 1 → Generate Content → Content Ready
     ↓           ↓          ↓          ↓            ↓                ↓
   Slack       Slack      Slack      Slack        Slack           Slack
```

**All notifications are:**
- ✅ Async (non-blocking)
- ✅ Formatted with rich blocks
- ✅ Include cycle ID for tracking
- ✅ Link to Google Sheet
- ✅ Logged to terminal

**You get notified about:**
- ✅ Cycle lifecycle (start/complete/fail)
- ✅ Stage progress
- ✅ Content generation
- ✅ Human gates (approval needed)
- ✅ Errors and failures
