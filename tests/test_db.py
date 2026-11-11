import os
import tempfile
import unittest

import game
from db import DB


class DBTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DB(os.path.join(self.tmp.name, "sub", "t.db"))
        await self.db.connect()

    async def asyncTearDown(self):
        await self.db.close()
        self.tmp.cleanup()

    async def test_daily_bonus_and_day_streak(self):
        await self.db.touch_user(1, "A", "a", "2026-11-10")
        r1 = await self.db.record_round(1, caught=6, best_streak=3, day="2026-11-10")
        self.assertEqual(r1["daily_bonus"], game.DAILY_BONUS)
        self.assertEqual(r1["streak_days"], 1)
        self.assertEqual(r1["earned"], 6 + 1)

        r2 = await self.db.record_round(1, caught=2, best_streak=1, day="2026-11-10")
        self.assertEqual(r2["daily_bonus"], 0)  # second round same day
        self.assertEqual(r2["streak_days"], 1)

        r3 = await self.db.record_round(1, caught=1, best_streak=1, day="2026-11-11")
        self.assertEqual(r3["streak_days"], 2)  # consecutive day
        self.assertEqual(r3["best_score"], 6)

        r4 = await self.db.record_round(1, caught=1, best_streak=1, day="2026-11-14")
        self.assertEqual(r4["streak_days"], 1)  # gap resets

    async def test_top_and_rank(self):
        for uid, name in [(1, "A"), (2, "B"), (3, "C")]:
            await self.db.touch_user(uid, name, None, "2026-11-11")
        await self.db.record_round(1, 3, 1, "2026-11-11")
        await self.db.record_round(2, 9, 9, "2026-11-11")
        top = await self.db.top(10)
        self.assertEqual([r["user_id"] for r in top], [2, 1])  # user 3 has 0 drops
        self.assertEqual(await self.db.rank(2), 1)
        self.assertEqual(await self.db.rank(1), 2)
        self.assertIsNone(await self.db.rank(3))

    async def test_due_reminders(self):
        today = "2026-11-11"
        await self.db.touch_user(1, "played", None, today)
        await self.db.record_round(1, 5, 2, today)
        await self.db.touch_user(2, "idle", None, "2026-11-10")
        await self.db.touch_user(3, "off", None, today)
        await self.db.set_remind(3, False)
        await self.db.touch_user(4, "dormant", None, "2026-10-01")
        await self.db.touch_user(5, "already", None, today)
        await self.db.mark_reminded(5, today)

        self.assertEqual(await self.db.due_reminders(today), [2])
        await self.db.mark_reminded(2, today)
        self.assertEqual(await self.db.due_reminders(today), [])


if __name__ == "__main__":
    unittest.main()
