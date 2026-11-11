"""SQLite storage (aiosqlite). Drops = in-bot score; the hook for raindrops later."""
from __future__ import annotations

import os
from datetime import date, timedelta

import aiosqlite

import game

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id          INTEGER PRIMARY KEY,
    first_name       TEXT    NOT NULL DEFAULT '',
    username         TEXT,
    drops            INTEGER NOT NULL DEFAULT 0,
    best_score       INTEGER NOT NULL DEFAULT 0,
    games            INTEGER NOT NULL DEFAULT 0,
    streak_days      INTEGER NOT NULL DEFAULT 0,
    last_play_day    TEXT,
    last_seen_day    TEXT,
    remind           INTEGER NOT NULL DEFAULT 1,
    last_reminded_day TEXT,
    created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_drops ON users(drops DESC);
CREATE TABLE IF NOT EXISTS quest (
    user_id    INTEGER NOT NULL,
    case_id    TEXT    NOT NULL,
    state      TEXT    NOT NULL,
    started    INTEGER NOT NULL DEFAULT 0,
    solved     INTEGER NOT NULL DEFAULT 0,
    rewarded   INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, case_id)
);
"""


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # ---- users -------------------------------------------------------
    async def touch_user(self, user_id: int, first_name: str, username: str | None, day: str) -> None:
        await self.conn.execute(
            """INSERT INTO users (user_id, first_name, username, last_seen_day)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   first_name = excluded.first_name,
                   username = excluded.username,
                   last_seen_day = excluded.last_seen_day""",
            (user_id, first_name or "", username, day),
        )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()

    async def set_remind(self, user_id: int, on: bool) -> None:
        await self.conn.execute("UPDATE users SET remind = ? WHERE user_id = ?", (int(on), user_id))
        await self.conn.commit()

    # ---- game results ------------------------------------------------
    async def record_round(self, user_id: int, caught: int, best_streak: int, day: str) -> dict:
        u = await self.get_user(user_id)
        earned = game.round_drops(caught, best_streak)
        daily_bonus = 0
        streak_days = u["streak_days"]
        if u["last_play_day"] != day:
            daily_bonus = game.DAILY_BONUS
            yesterday = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
            streak_days = u["streak_days"] + 1 if u["last_play_day"] == yesterday else 1
        total = earned + daily_bonus
        best_score = max(u["best_score"], caught)
        await self.conn.execute(
            """UPDATE users SET drops = drops + ?, games = games + 1, best_score = ?,
                   streak_days = ?, last_play_day = ? WHERE user_id = ?""",
            (total, best_score, streak_days, day, user_id),
        )
        await self.conn.commit()
        return {
            "earned": earned,
            "daily_bonus": daily_bonus,
            "total": total,
            "drops": u["drops"] + total,
            "best_score": best_score,
            "streak_days": streak_days,
        }

    async def top(self, limit: int = 10) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT user_id, first_name, drops FROM users WHERE drops > 0 "
            "ORDER BY drops DESC, user_id ASC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()

    async def rank(self, user_id: int) -> int | None:
        u = await self.get_user(user_id)
        if not u or u["drops"] <= 0:
            return None
        cur = await self.conn.execute("SELECT COUNT(*) FROM users WHERE drops > ?", (u["drops"],))
        (ahead,) = await cur.fetchone()
        return ahead + 1

    # ---- detective quest ---------------------------------------------
    async def get_quest(self, user_id: int, case_id: str) -> str | None:
        cur = await self.conn.execute(
            "SELECT state FROM quest WHERE user_id = ? AND case_id = ?", (user_id, case_id)
        )
        row = await cur.fetchone()
        return row["state"] if row else None

    async def save_quest(self, user_id: int, case_id: str, state: str, started: bool, solved: bool) -> None:
        await self.conn.execute(
            """INSERT INTO quest (user_id, case_id, state, started, solved)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, case_id) DO UPDATE SET
                   state = excluded.state, started = excluded.started,
                   solved = excluded.solved, updated_at = CURRENT_TIMESTAMP""",
            (user_id, case_id, state, int(started), int(solved)),
        )
        await self.conn.commit()

    async def has_open_case(self, user_id: int) -> bool:
        cur = await self.conn.execute(
            "SELECT 1 FROM quest WHERE user_id = ? AND started = 1 AND solved = 0 LIMIT 1", (user_id,)
        )
        return await cur.fetchone() is not None

    async def case_rewarded(self, user_id: int, case_id: str) -> bool:
        """True if the solve reward was already paid (survives case restarts)."""
        cur = await self.conn.execute(
            "SELECT rewarded FROM quest WHERE user_id = ? AND case_id = ?", (user_id, case_id)
        )
        row = await cur.fetchone()
        return bool(row and row["rewarded"])

    async def mark_rewarded(self, user_id: int, case_id: str) -> None:
        await self.conn.execute(
            "UPDATE quest SET rewarded = 1 WHERE user_id = ? AND case_id = ?", (user_id, case_id)
        )
        await self.conn.commit()

    async def add_drops(self, user_id: int, amount: int) -> None:
        await self.conn.execute("UPDATE users SET drops = drops + ? WHERE user_id = ?", (amount, user_id))
        await self.conn.commit()

    # ---- reminders ---------------------------------------------------
    async def due_reminders(self, today: str, active_days: int = 14) -> list[int]:
        """Users who want reminders, haven't played or been reminded today,
        and were seen within the last `active_days` days (no spam to dormant users)."""
        cutoff = (date.fromisoformat(today) - timedelta(days=active_days)).isoformat()
        cur = await self.conn.execute(
            """SELECT user_id FROM users
               WHERE remind = 1
                 AND (last_play_day IS NULL OR last_play_day != ?)
                 AND (last_reminded_day IS NULL OR last_reminded_day != ?)
                 AND last_seen_day >= ?""",
            (today, today, cutoff),
        )
        return [r["user_id"] for r in await cur.fetchall()]

    async def mark_reminded(self, user_id: int, day: str) -> None:
        await self.conn.execute("UPDATE users SET last_reminded_day = ? WHERE user_id = ?", (day, user_id))
        await self.conn.commit()
