import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str
    coinplay_link: str | None
    community_link: str | None
    reminder_hour_utc: int


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("BOT_TOKEN is not set")
    return Config(
        bot_token=token,
        db_path=os.getenv("DB_PATH", "coinplay.db"),
        coinplay_link=os.getenv("COINPLAY_LINK") or None,
        community_link=os.getenv("COMMUNITY_LINK") or None,
        reminder_hour_utc=int(os.getenv("REMINDER_HOUR_UTC", "17")),
    )
