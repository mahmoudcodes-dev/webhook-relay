import os
from dataclasses import dataclass


@dataclass
class Settings:
    webhook_secret: str
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    rate_limit_per_minute: int = 60
    db_path: str = "events.db"

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


def load_settings() -> Settings:
    secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError("WEBHOOK_SECRET is required (shared secret used to sign webhook payloads)")
    return Settings(
        webhook_secret=secret,
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID") or None,
        rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
        db_path=os.environ.get("DB_PATH", "events.db"),
    )
