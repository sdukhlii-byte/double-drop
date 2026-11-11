"""Feeds real-looking updates through the dispatcher with a fake Telegram session."""
import os
import tempfile
import unittest
from datetime import datetime

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, GetMe, SendMessage
from aiogram.types import Chat, Message, Update, User

import bot as botmod
import game
from config import Config
from db import DB


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def stream_content(self, *a, **kw):  # pragma: no cover
        yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        chat = Chat(id=42, type="private")
        if isinstance(method, GetMe):
            return User(id=1, is_bot=True, first_name="Double Drop", username="doubledrop_test_bot")
        if isinstance(method, (SendMessage, EditMessageText)):
            return Message(message_id=len(self.calls), date=datetime.now(), chat=chat, text=method.text)
        if isinstance(method, AnswerCallbackQuery):
            return True
        raise AssertionError(f"unexpected method {method}")


def user():
    return {"id": 42, "is_bot": False, "first_name": "Stan"}


class SmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config("123456:TEST", os.path.join(self.tmp.name, "t.db"), 17)
        self.db = DB(self.cfg.db_path)
        await self.db.connect()
        self.session = FakeSession()
        self.bot = Bot("123456:TEST", session=self.session)
        self.dp = botmod.build_dispatcher(self.db, self.cfg)
        self.n = 0
        botmod.ROUNDS.clear()

    async def asyncTearDown(self):
        await self.db.close()
        self.tmp.cleanup()

    async def feed(self, payload):
        self.n += 1
        payload["update_id"] = self.n
        upd = Update.model_validate(payload, context={"bot": self.bot})
        await self.dp.feed_update(self.bot, upd)

    def msg(self, text, **extra):
        return {"message_id": self.n + 100, "date": 1700000000, "chat": {"id": 42, "type": "private"},
                "from": user(), "text": text, **extra}

    async def test_start_then_full_round(self):
        await self.feed({"message": self.msg(
            "/start", entities=[{"type": "bot_command", "offset": 0, "length": 6}])})
        sent = [c for c in self.session.calls if isinstance(c, SendMessage)]
        self.assertIn("Welcome to Double Drop", sent[-1].text)

        await self.feed({"callback_query": {
            "id": "1", "from": user(), "chat_instance": "x", "data": "menu:rain",
            "message": self.msg("menu")}})
        rnd = botmod.ROUNDS[42]

        for i in range(game.DROPS_PER_ROUND):
            await self.feed({"callback_query": {
                "id": str(10 + i), "from": user(), "chat_instance": "x",
                "data": f"t:{rnd.game_id}:{rnd.target}", "message": self.msg("round")}})

        self.assertNotIn(42, botmod.ROUNDS)
        last_edit = [c for c in self.session.calls if isinstance(c, EditMessageText)][-1]
        self.assertIn("Round complete", last_edit.text)
        u = await self.db.get_user(42)
        self.assertEqual(u["games"], 1)
        self.assertEqual(u["drops"], 10 + 10 // 3 + game.DAILY_BONUS)

    async def test_stale_tap_is_ignored(self):
        await self.feed({"callback_query": {
            "id": "1", "from": user(), "chat_instance": "x", "data": "t:deadbeef:3",
            "message": self.msg("round")}})
        answers = [c for c in self.session.calls if isinstance(c, AnswerCallbackQuery)]
        self.assertIn("over", answers[-1].text)
        self.assertEqual((await self.db.get_user(42))["games"], 0)

    async def tap(self, data):
        self.n += 1
        await self.feed({"callback_query": {
            "id": f"q{self.n}", "from": user(), "chat_instance": "x", "data": data,
            "message": self.msg("quest")}})
        return [c for c in self.session.calls if isinstance(c, EditMessageText)][-1].text

    async def test_quest_full_playthrough_and_reward_once(self):
        text = await self.tap("menu:case")
        self.assertIn("The Double Drop", text)
        await self.tap("q:begin")
        from quest import State
        # replay every action through real callbacks
        for step in [
            "q:t:calloway:coroner", "q:spot:study:desk", "q:spot:study:rug", "q:spot:study:ashtray",
            "q:spot:study:sofa", "q:loc:heron", "q:pc:vera:lipstick_glass", "q:t:vera:upstairs",
            "q:loc:lobby", "q:t:nell:parcel", "q:t:calloway:parcel", "q:t:nell:release",
            "q:t:webb:ice", "q:t:webb:monday", "q:loc:clinic", "q:spot:clinic:cabinet",
            "q:spot:clinic:rolltop",
        ]:
            await self.tap(step)
        raw = await self.db.get_quest(42, "double_drop")
        st = State.loads(raw)
        self.assertIn("deposit_slips", st.clues)

        wrong = await self.tap("q:a3:eleanor:1:1")
        self.assertIn("bad marriage", wrong)
        self.assertEqual((await self.db.get_user(42))["drops"], 0)

        ok = await self.tap("q:a3:voss:1:1")
        self.assertIn("CASE CLOSED", ok)
        self.assertIn("+30 drops", ok)
        self.assertEqual((await self.db.get_user(42))["drops"], 30)
        self.assertFalse(await self.db.has_open_case(42))

        # restart and solve again: no second reward
        await self.tap("q:newy")
        self.assertTrue((await self.db.get_user(42))["drops"] == 30)
        st = State.loads(await self.db.get_quest(42, "double_drop"))
        self.assertFalse(st.solved)
        ok2 = await self.tap("q:a3:voss:1:1")
        self.assertIn("CASE CLOSED", ok2)
        self.assertNotIn("Case reward", ok2)
        self.assertEqual((await self.db.get_user(42))["drops"], 30)

    async def test_quest_progress_survives_and_open_case_flag(self):
        await self.tap("menu:case")
        await self.tap("q:begin")
        await self.tap("q:spot:study:desk")
        self.assertTrue(await self.db.has_open_case(42))
        text = await self.tap("menu:case")  # re-open from menu: lands on the hub, not the intro
        self.assertIn("Clues in your notebook: <b>1</b>", text)

    async def test_top_me_and_reminder_toggle(self):
        await self.feed({"message": self.msg(
            "/me", entities=[{"type": "bot_command", "offset": 0, "length": 3}])})
        await self.feed({"message": self.msg(
            "/top", entities=[{"type": "bot_command", "offset": 0, "length": 4}])})
        await self.feed({"message": self.msg(
            "/reminder", entities=[{"type": "bot_command", "offset": 0, "length": 9}])})
        self.assertEqual((await self.db.get_user(42))["remind"], 0)


if __name__ == "__main__":
    unittest.main()
