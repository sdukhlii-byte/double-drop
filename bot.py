"""Double Drop — Telegram bot: a detective quest, plus the Raindrop Catch mini-game."""
from __future__ import annotations

import asyncio
import html
import logging
import random
import time
from datetime import datetime, timezone

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import game
from config import Config, load_config
from db import DB
from quest_ui import build_quest_router

log = logging.getLogger("double_drop")

# Active rounds live in memory: a round lasts ~30 seconds, losing one on restart is fine.
ROUNDS: dict[int, game.Round] = {}

REMINDER_TEXTS = [
    "💧 It's raining again! Today's shower is waiting — catch a few drops?",
    "☁️ Clouds are gathering over Port Meridian. A fresh shower of bonus drops is ready for you.",
    "🌧 Your daily rain has arrived. 30 seconds, ten drops — see how many you can catch.",
]

CASE_REMINDER_TEXTS = [
    "🕵️ Your case file is still open, Detective. Somebody in that hotel is lying — go and find out who.",
    "🌧 Rain on the glass, a notebook on the desk. The Halloran case is waiting for you.",
    "🕵️ Inspector Calloway is asking for you. The Double Drop is not going to solve itself.",
]


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# ---------------------------------------------------------------- keyboards
def main_menu(cfg: Config, remind_on: bool | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🕵️ The Double Drop — the case", callback_data="menu:case"))
    kb.row(InlineKeyboardButton(text="🌧 Raindrop Catch (mini-game)", callback_data="menu:rain"))
    kb.row(
        InlineKeyboardButton(text="🏆 Top", callback_data="menu:top"),
        InlineKeyboardButton(text="💧 My drops", callback_data="menu:me"),
    )
    if remind_on is not None:
        kb.row(
            InlineKeyboardButton(
                text="🔔 Daily reminder: on" if remind_on else "🔕 Daily reminder: off",
                callback_data="menu:remind",
            )
        )
    if cfg.coinplay_link:
        kb.row(InlineKeyboardButton(text="🪙 CoinPlay", url=cfg.coinplay_link))
    if cfg.community_link:
        kb.row(InlineKeyboardButton(text="👥 Community", url=cfg.community_link))
    return kb.as_markup()


def round_keyboard(rnd: game.Round) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(game.CELLS):
        kb.button(
            text="💧" if i == rnd.target else "☁️",
            callback_data=f"t:{rnd.game_id}:{i}",
        )
    kb.adjust(game.GRID_COLS)
    return kb.as_markup()


def round_text(rnd: game.Round) -> str:
    streak = f" · 🔥 {rnd.streak}" if rnd.streak >= 2 else ""
    return (
        f"🌧 <b>Raindrop Catch</b>\n"
        f"Drop {rnd.step}/{game.DROPS_PER_ROUND} · caught {rnd.caught}{streak}\n\n"
        f"Tap the 💧 before it vanishes!"
    )


def after_round_keyboard(cfg: Config) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔁 Play again", callback_data="menu:rain"))
    kb.row(
        InlineKeyboardButton(text="🕵️ The case", callback_data="menu:case"),
        InlineKeyboardButton(text="🏆 Top", callback_data="menu:top"),
    )
    kb.row(InlineKeyboardButton(text="💧 My drops", callback_data="menu:me"))
    if cfg.coinplay_link:
        kb.row(InlineKeyboardButton(text="🪙 CoinPlay", url=cfg.coinplay_link))
    return kb.as_markup()


# ------------------------------------------------------------------ helpers
async def safe_edit(msg: Message, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    try:
        await msg.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            log.warning("edit failed: %s", e)


def display_name(row) -> str:
    name = (row["first_name"] or "Player").strip() or "Player"
    return html.escape(name[:16])


async def start_round(target: Message, user_id: int) -> None:
    rnd = game.new_round(user_id, time.monotonic())
    ROUNDS[user_id] = rnd
    await target.answer(round_text(rnd), reply_markup=round_keyboard(rnd))


class TouchUser(BaseMiddleware):
    """Keep the users table up to date on every message / button press."""

    def __init__(self, db: DB):
        self.db = db

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            await self.db.touch_user(user.id, user.first_name, user.username, today_utc())
        return await handler(event, data)


# ----------------------------------------------------------------- routers
def build_router(db: DB, cfg: Config) -> Router:
    r = Router()

    # ----- text screens
    async def welcome(msg: Message, user_id: int) -> None:
        u = await db.get_user(user_id)
        await msg.answer(
            "🕵️ <b>Welcome to Double Drop</b>\n\n"
            "Port Meridian, 1947. A shipping magnate is dead in a locked room, and eight people "
            "had a reason. Search the scenes, question the suspects, put the evidence on the table — "
            "and name the killer.\n\n"
            "🌧 Between interrogations, step out into the rain: <b>Raindrop Catch</b> is a 30-second "
            "tap game. Catch drops, build a streak and climb the board. Your first round of the day "
            "brings bonus drops.",
            reply_markup=main_menu(cfg, bool(u["remind"])),
        )

    async def show_top(msg: Message, user_id: int) -> None:
        rows = await db.top(10)
        if not rows:
            await msg.answer("The board is empty. Be the first to catch some drops! 🌧",
                             reply_markup=main_menu(cfg))
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 <b>Top catchers</b>\n"]
        for i, row in enumerate(rows):
            mark = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{mark} {display_name(row)} — {row['drops']} 💧")
        rank = await db.rank(user_id)
        if rank and rank > 10:
            u = await db.get_user(user_id)
            lines.append(f"\nYou: #{rank} — {u['drops']} 💧")
        await msg.answer("\n".join(lines), reply_markup=main_menu(cfg))

    async def show_me(msg: Message, user_id: int) -> None:
        u = await db.get_user(user_id)
        rank = await db.rank(user_id)
        await msg.answer(
            f"💧 <b>Your drops</b>\n\n"
            f"Balance: <b>{u['drops']}</b> 💧\n"
            f"Rank: {'#' + str(rank) if rank else '—'}\n"
            f"Best round: {u['best_score']}/{game.DROPS_PER_ROUND}\n"
            f"Rounds played: {u['games']}\n"
            f"Day streak: {u['streak_days']} 🔥",
            reply_markup=main_menu(cfg, bool(u["remind"])),
        )

    async def toggle_remind(msg: Message, user_id: int) -> None:
        u = await db.get_user(user_id)
        new = not bool(u["remind"])
        await db.set_remind(user_id, new)
        await msg.answer(
            "🔔 Daily reminder is on. I'll nudge you once a day when the rain starts."
            if new else "🔕 Daily reminder is off.",
            reply_markup=main_menu(cfg, new),
        )

    # ----- commands
    @r.message(CommandStart())
    async def cmd_start(msg: Message):
        await welcome(msg, msg.from_user.id)

    @r.message(Command("rain"))
    async def cmd_rain(msg: Message):
        await start_round(msg, msg.from_user.id)

    @r.message(Command("top"))
    async def cmd_top(msg: Message):
        await show_top(msg, msg.from_user.id)

    @r.message(Command("me"))
    async def cmd_me(msg: Message):
        await show_me(msg, msg.from_user.id)

    @r.message(Command("reminder"))
    async def cmd_reminder(msg: Message):
        await toggle_remind(msg, msg.from_user.id)

    # ----- menu buttons
    @r.callback_query(F.data.regexp(r"^menu:(rain|home|top|me|remind)$"))
    async def on_menu(cb: CallbackQuery):
        action = cb.data.split(":", 1)[1]
        await cb.answer()
        uid = cb.from_user.id
        if action == "rain":
            await start_round(cb.message, uid)
        elif action == "home":
            await welcome(cb.message, uid)
        elif action == "top":
            await show_top(cb.message, uid)
        elif action == "me":
            await show_me(cb.message, uid)
        elif action == "remind":
            await toggle_remind(cb.message, uid)

    # ----- the game
    @r.callback_query(F.data.startswith("t:"))
    async def on_tap(cb: CallbackQuery):
        _, gid, idx = cb.data.split(":")
        rnd = ROUNDS.get(cb.from_user.id)
        if rnd is None or rnd.game_id != gid:
            await cb.answer("This round is over — start a new one!", show_alert=True)
            return

        res = game.tap(rnd, int(idx), time.monotonic())

        if not res.finished:
            await safe_edit(cb.message, round_text(rnd), round_keyboard(rnd))
            await cb.answer("💧 +1" if res.hit else ("🐢 Too slow" if res.slow else "☁️ Missed"))
            return

        ROUNDS.pop(cb.from_user.id, None)
        out = await db.record_round(cb.from_user.id, rnd.caught, rnd.best_streak, today_utc())
        lines = [
            "🌧 <b>Round complete!</b>\n",
            f"Caught: <b>{rnd.caught}/{game.DROPS_PER_ROUND}</b>   Best streak: {rnd.best_streak} 🔥",
            f"Drops earned: +{out['earned']} 💧",
        ]
        if out["daily_bonus"]:
            lines.append(f"Daily shower bonus: +{out['daily_bonus']} 💧")
        lines.append(f"\nBalance: <b>{out['drops']}</b> 💧 · Day streak: {out['streak_days']} 🔥")
        await safe_edit(cb.message, "\n".join(lines), after_round_keyboard(cfg))
        await cb.answer("💧 +1" if res.hit else "Round over")

    return r


# ---------------------------------------------------------- daily reminders
async def reminder_loop(bot: Bot, db: DB, cfg: Config) -> None:
    """Once a day, inside a 3-hour window starting at REMINDER_HOUR_UTC (covers late restarts)."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            if cfg.reminder_hour_utc <= now.hour < cfg.reminder_hour_utc + 3:
                today = now.date().isoformat()
                for uid in await db.due_reminders(today):
                    try:
                        kb = InlineKeyboardBuilder()
                        if await db.has_open_case(uid):
                            text = random.choice(CASE_REMINDER_TEXTS)
                            kb.row(InlineKeyboardButton(text="🕵️ Continue the case", callback_data="menu:case"))
                            kb.row(InlineKeyboardButton(text="🌧 Catch the drops", callback_data="menu:rain"))
                        else:
                            text = random.choice(REMINDER_TEXTS)
                            kb.row(InlineKeyboardButton(text="🌧 Catch the drops", callback_data="menu:rain"))
                            kb.row(InlineKeyboardButton(text="🕵️ The case", callback_data="menu:case"))
                        await bot.send_message(uid, text, reply_markup=kb.as_markup())
                        await db.mark_reminded(uid, today)
                    except TelegramForbiddenError:
                        await db.set_remind(uid, False)  # user blocked the bot
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                    except Exception:
                        log.exception("reminder to %s failed", uid)
                    await asyncio.sleep(0.05)  # stay well under Telegram's broadcast limits
        except Exception:
            log.exception("reminder loop error")
        await asyncio.sleep(300)


# --------------------------------------------------------------------- main
def build_dispatcher(db: DB, cfg: Config) -> Dispatcher:
    dp = Dispatcher()
    mw = TouchUser(db)
    dp.message.outer_middleware(mw)
    dp.callback_query.outer_middleware(mw)
    dp.include_router(build_router(db, cfg))
    dp.include_router(build_quest_router(db))
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    db = DB(cfg.db_path)
    await db.connect()
    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(db, cfg)
    reminder_task = asyncio.create_task(reminder_loop(bot, db, cfg))
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
