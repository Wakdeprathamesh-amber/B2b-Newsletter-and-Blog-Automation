"""Application settings loaded from environment variables.

In dev mode (no LLM API key set), the app uses SQLite
and mock data so you can run and test the pipeline without external services.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM (provider-agnostic) ──
    llm_provider: str = "openai"  # "openai" or "anthropic"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    generation_model: str = "gpt-4o-mini"
    editorial_model: str = "gpt-4o-mini"
    langsmith_api_key: str = ""
    langsmith_project: str = "amber-content-engine"

    # Database -- defaults to SQLite for local dev
    database_url: str = "sqlite:///amber_content.db"

    # Scraping
    firecrawl_api_key: str = ""

    # Google
    google_service_account_json: str = ""
    google_master_sheet_id: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_channel_id: str = ""
    slack_review_channel: str = "content-review"
    slack_escalation_channel: str = "content-escalation"

    # LinkedIn / Buffer
    linkedin_access_token: str = ""
    buffer_access_token: str = ""

    # HubSpot
    hubspot_api_key: str = ""

    # Scheduling
    cycle_cron: str = "0 7 */14 * *"
    timezone: str = "Europe/London"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Review gate timeouts (hours)
    gate1_reminder_hours: int = 12
    gate1_escalation_hours: int = 24
    gate1_pause_hours: int = 48
    gate2_reminder_hours: int = 24
    gate2_escalation_hours: int = 48
    gate2_pause_hours: int = 72

    # Dev mode -- set to True to use mock data instead of real API calls
    dev_mode: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def is_llm_available(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        elif self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False

    @property
    def is_slack_available(self) -> bool:
        return bool(self.slack_bot_token and self.slack_channel_id)


settings = Settings()
