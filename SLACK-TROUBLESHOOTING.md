# Slack Integration — Quick Fix

## ❌ Current Issue: `channel_not_found`

Your Slack credentials are correct, but the bot needs to be invited to the channel!

---

## ✅ Quick Fix (2 minutes)

### Step 1: Find Your Channel

Your channel ID is: **`C0B01Q2BJF4`**

1. Open Slack
2. Find the channel with this ID (or the channel where you want notifications)

**How to find channel ID:**
- Right-click the channel name
- Click "View channel details"
- Scroll down to see the Channel ID

### Step 2: Invite the Bot

In the Slack channel, type:

```
/invite @YourBotName
```

Replace `YourBotName` with your actual bot's name.

**Don't know your bot name?**
1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Select your app
3. Look for "Display Name" or "Bot User"

### Step 3: Test Again

```bash
source venv/bin/activate
python test_slack.py
```

You should see:
```
✅ Test message sent successfully!
```

And a message will appear in your Slack channel! 🎉

---

## Alternative: Use a Different Channel

If you want to use a different channel:

### Option 1: Public Channel

1. Create or find a public channel
2. Invite the bot: `/invite @YourBotName`
3. Get the channel ID:
   - Right-click channel → View details → Copy ID
4. Update `.env`:
   ```bash
   SLACK_CHANNEL_ID=C0XXXXXXXXX  # Your new channel ID
   ```
5. Test: `python test_slack.py`

### Option 2: Private Channel

1. Create or find a private channel
2. Add the bot as a member (not just invite)
3. Get the channel ID
4. Update `.env` with the new ID
5. Test: `python test_slack.py`

---

## Verify Bot Permissions

Your bot needs these OAuth scopes:

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Select your app
3. Go to **OAuth & Permissions**
4. Check **Scopes** section:
   - ✅ `chat:write` — Send messages
   - ✅ `chat:write.public` — Send to public channels

If missing, add them and **reinstall the app** to your workspace.

---

## Test Results

### ✅ What's Working

- Credentials are configured correctly
- Bot token is valid
- Slack client initializes successfully

### ❌ What Needs Fixing

- Bot is not in the channel (channel_not_found)

**Fix:** Invite the bot to the channel!

---

## After Fixing

Once the bot is in the channel, you'll get:

```bash
$ python test_slack.py

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

And you'll see this in Slack:
```
🧪 Test message from Amber Content Engine
```

---

## Next Steps

1. **Invite bot to channel:** `/invite @YourBotName`
2. **Test again:** `python test_slack.py`
3. **Start using:** All web interface actions will send notifications!

---

## Need Help?

### Find Your Bot Name

```bash
# Your bot token starts with: xoxb-53335601925-9010945601921-...
# The numbers after xoxb- are your bot's workspace and bot IDs
```

Go to [Slack API Apps](https://api.slack.com/apps) to see your bot's display name.

### Still Not Working?

Check these:

1. **Bot token valid?**
   - Go to Slack API → OAuth & Permissions
   - Copy the Bot User OAuth Token
   - Update `.env` if different

2. **Channel ID correct?**
   - Right-click channel → View details
   - Copy the Channel ID
   - Update `.env` if different

3. **Bot has permissions?**
   - Slack API → OAuth & Permissions
   - Check for `chat:write` scope
   - Reinstall app if needed

---

## Summary

**Current Status:** ⚠️ Bot not in channel

**Quick Fix:** `/invite @YourBotName` in the Slack channel

**After Fix:** ✅ Notifications will work automatically!
