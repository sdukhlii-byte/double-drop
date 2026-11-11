import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str
    reminder_hour_utc: int


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("BOT_TOKEN is not set")
    return Config(
        bot_token=token,
        db_path=os.getenv("DB_PATH", "doubledrop.db"),
        reminder_hour_utc=int(os.getenv("REMINDER_HOUR_UTC", "17")),
    )
