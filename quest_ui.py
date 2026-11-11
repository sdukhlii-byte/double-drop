"""Telegram glue for the detective quest: loads/saves State, renders Screens."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from cases import CASES, DEFAULT_CASE_ID
from db import DB
from quest import Engine, Screen, State

log = logging.getLogger("double_drop.quest")

ENGINE = Engine(CASES[DEFAULT_CASE_ID])


def to_markup(screen: Screen) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b.label, callback_data=b.data) for b in row] for row in screen.rows
        ]
    )


async def load_state(db: DB, user_id: int) -> State:
    raw = await db.get_quest(user_id, ENGINE.case.id)
    return State.loads(raw) if raw else ENGINE.new_state()


async def save_state(db: DB, user_id: int, st: State) -> None:
    await db.save_quest(user_id, ENGINE.case.id, st.dumps(), st.started, st.solved)


def entry_screen(st: State) -> Screen:
    """What the player sees when they open the case from the menu."""
    return ENGINE.hub(st) if st.started else ENGINE.intro(st)


def build_quest_router(db: DB) -> Router:
    r = Router()

    @r.message(Command("case"))
    async def cmd_case(msg: Message):
        st = await load_state(db, msg.from_user.id)
        screen = entry_screen(st)
        await msg.answer(screen.text, reply_markup=to_markup(screen))

    @r.message(Command("notebook"))
    async def cmd_notebook(msg: Message):
        st = await load_state(db, msg.from_user.id)
        screen = ENGINE.notebook(st) if st.started else ENGINE.intro(st)
        await msg.answer(screen.text, reply_markup=to_markup(screen))

    @r.callback_query(F.data == "menu:case")
    async def on_menu_case(cb: CallbackQuery):
        await cb.answer()
        st = await load_state(db, cb.from_user.id)
        screen = entry_screen(st)
        await show(cb.message, screen)

    @r.callback_query(F.data.startswith("q:"))
    async def on_quest(cb: CallbackQuery):
        uid = cb.from_user.id
        st = await load_state(db, uid)

        if cb.data == "q:newy":
            st = ENGINE.new_state()
            await save_state(db, uid, st)
            await cb.answer("Case restarted")
            await show(cb.message, ENGINE.intro(st))
            return

        was_solved = st.solved
        screen = ENGINE.handle(st, cb.data)
        await save_state(db, uid, st)
        if st.solved and not was_solved and not await db.case_rewarded(uid, ENGINE.case.id):
            await db.add_drops(uid, ENGINE.case.solved_drops)
            await db.mark_rewarded(uid, ENGINE.case.id)
            screen = Screen(
                screen.text + f"\n\n💧 Case reward: +{ENGINE.case.solved_drops} drops", screen.rows
            )
        await cb.answer()
        await show(cb.message, screen)

    return r


async def show(msg: Message, screen: Screen) -> None:
    try:
        await msg.edit_text(screen.text, reply_markup=to_markup(screen))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        log.warning("edit failed, sending a new message instead: %s", e)
        await msg.answer(screen.text, reply_markup=to_markup(screen))
