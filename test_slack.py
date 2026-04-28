"""Test Slack integration.

Quick test to verify Slack credentials and send a test message.

Usage:
    python test_slack.py
"""

import sys
from src.integrations.slack import get_slack_client
from src.settings import settings


def main():
    print("🔍 Testing Slack Integration\n")
    
    # Check credentials
    print("Credentials:")
    print(f"  SLACK_BOT_TOKEN: {'✅ Set' if settings.slack_bot_token else '❌ Missing'}")
    print(f"  SLACK_SIGNING_SECRET: {'✅ Set' if settings.slack_signing_secret else '❌ Missing'}")
    print(f"  SLACK_CHANNEL_ID: {'✅ Set' if settings.slack_channel_id else '❌ Missing'}")
    print()
    
    if not settings.is_slack_available:
        print("❌ Slack is not configured. Check your .env file.")
        return 1
    
    # Initialize client
    print("Initializing Slack client...")
    slack = get_slack_client()
    
    if not slack.is_available:
        print("❌ Slack client failed to initialize")
        return 1
    
    print(f"✅ Slack client initialized (channel: {settings.slack_channel_id})\n")
    
    # Send test message
    print("Sending test message...")
    success = slack.send_message("🧪 Test message from Amber Content Engine")
    
    if success:
        print("✅ Test message sent successfully!")
        print(f"\nCheck your Slack channel: {settings.slack_channel_id}")
        return 0
    else:
        print("❌ Failed to send test message")
        print("Check the logs above for error details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
