import re
import unittest

from cases import CASES, DEFAULT_CASE_ID
from quest import MAX_TEXT, Engine, State, Screen

CASE = CASES[DEFAULT_CASE_ID]
ENGINE = Engine(CASE)
ALLOWED_TAGS = re.compile(r"</?(b|i)>")


def all_texts(case):
    for c in case.clues:
        yield f"clue:{c.id}", c.title + " " + c.text
    for l in case.locations:
        yield f"loc:{l.id}", l.intro
        for s in l.spots:
            yield f"spot:{s.id}", s.text + " " + s.locked_hint
    for ch in case.characters:
        yield f"char:{ch.id}", ch.intro + " " + ch.default_reaction
        for t in ch.topics:
            yield f"topic:{ch.id}:{t.id}", t.text
        for r in ch.reactions:
            yield f"react:{ch.id}:{r.clue}", r.text
    for h in case.hints:
        yield f"hint:{h.unless}", h.text
    for k, v in case.wrong_culprit.items():
        yield f"wrong:{k}", v
    yield "briefing", case.briefing
    yield "partial", case.partial_text
    yield "solved", case.solved_text


def play_everything(engine: Engine) -> State:
    """Do every available action until nothing new unlocks. Returns the final state."""
    st = engine.new_state()
    st.started = True
    for _ in range(50):
        before = (len(st.clues), len(st.done), len(st.visited), len(st.met))
        for loc in engine.case.locations:
            engine.handle(st, f"q:loc:{loc.id}")
            for sp in loc.spots:
                engine.handle(st, f"q:spot:{loc.id}:{sp.id}")
        for cid in list(st.met):
            for tp in engine.chars[cid].topics:
                engine.handle(st, f"q:t:{cid}:{tp.id}")
            for clue in list(st.clues):
                engine.handle(st, f"q:pc:{cid}:{clue}")
        if before == (len(st.clues), len(st.done), len(st.visited), len(st.met)):
            break
    return st


class IntegrityTests(unittest.TestCase):
    def test_references_exist(self):
        clue_ids = {c.id for c in CASE.clues}
        loc_ids = {l.id for l in CASE.locations}
        chars = {c.id for c in CASE.characters}
        self.assertEqual(len(clue_ids), len(CASE.clues), "duplicate clue ids")
        for l in CASE.locations:
            self.assertTrue(set(l.requires) <= clue_ids, l.id)
            self.assertTrue(set(l.people) <= chars, l.id)
            for s in l.spots:
                self.assertTrue(set(s.requires) | set(s.gives) <= clue_ids, s.id)
        for c in CASE.characters:
            ids = [t.id for t in c.topics]
            self.assertEqual(len(ids), len(set(ids)), f"dup topic in {c.id}")
            for t in c.topics:
                self.assertTrue(set(t.requires) | set(t.gives) <= clue_ids, f"{c.id}:{t.id}")
            for r in c.reactions:
                self.assertIn(r.clue, clue_ids, f"{c.id} reaction")
                self.assertTrue(set(r.gives) <= clue_ids)
        for h in CASE.hints:
            self.assertIn(h.unless, clue_ids)
        self.assertTrue(set(CASE.suspects) <= chars)
        self.assertIn(CASE.culprit, CASE.suspects)
        self.assertEqual(sum(c.correct for c in CASE.hows), 1)
        self.assertEqual(sum(c.correct for c in CASE.whys), 1)
        self.assertEqual(set(CASE.wrong_culprit), set(CASE.suspects) - {CASE.culprit})
        self.assertTrue(loc_ids)

    def test_text_is_telegram_html_safe(self):
        for name, text in all_texts(CASE):
            stripped = ALLOWED_TAGS.sub("", text)
            self.assertNotRegex(stripped, r"[<>&]", f"{name} has raw <, > or &")
            self.assertLess(len(text), 1800, f"{name} is long")

    def test_callback_data_fits_telegram_limit(self):
        ids = [c.id for c in CASE.clues] + [l.id for l in CASE.locations] + [c.id for c in CASE.characters]
        ids += [s.id for l in CASE.locations for s in l.spots] + [t.id for c in CASE.characters for t in c.topics]
        self.assertLess(max(len(i) for i in ids) * 3 + 12, 64)
        self.assertLess(len(f"q:pc:{max((c.id for c in CASE.characters), key=len)}:{max((c.id for c in CASE.clues), key=len)}"), 64)


class SolvabilityTests(unittest.TestCase):
    def test_every_clue_is_obtainable(self):
        st = play_everything(ENGINE)
        missing = {c.id for c in CASE.clues} - set(st.clues)
        self.assertFalse(missing, f"unreachable clues: {missing}")

    def test_every_location_and_person_reachable(self):
        st = play_everything(ENGINE)
        self.assertEqual({l.id for l in CASE.locations}, set(st.visited))
        self.assertEqual({c.id for c in CASE.characters}, set(st.met))

    def test_every_topic_and_spot_gets_unlocked(self):
        st = play_everything(ENGINE)
        for l in CASE.locations:
            for s in l.spots:
                self.assertIn(f"s:{l.id}:{s.id}", st.done)
        for c in CASE.characters:
            for t in c.topics:
                self.assertIn(f"t:{c.id}:{t.id}", st.done, f"{c.id}:{t.id} never unlocked")

    def test_every_screen_fits_in_a_message(self):
        st = play_everything(ENGINE)
        for l in CASE.locations:
            for data in [f"q:loc:{l.id}"] + [f"q:spot:{l.id}:{s.id}" for s in l.spots]:
                self.assertLess(len(ENGINE.handle(st, data).text), MAX_TEXT)
        for c in CASE.characters:
            for clue in st.clues:
                s = ENGINE.handle(st, f"q:pc:{c.id}:{clue}")
                self.assertLess(len(s.text), MAX_TEXT)
        for data in ["q:hub", "q:locs", "q:ppl", "q:nb", "q:pr:voss", "q:acc"]:
            s = ENGINE.handle(st, data)
            self.assertLess(len(s.text), MAX_TEXT)
            for row in s.rows:
                for b in row:
                    self.assertLess(len(b.data.encode()), 64, b.data)

    def test_hints_progress_and_run_out(self):
        st = ENGINE.new_state()
        seen = set()
        for _ in range(len(CASE.hints) + 2):
            text = ENGINE.handle(st, "q:h").text
            seen.add(text)
        self.assertEqual(len(seen), 1, "hint should not change while no clue is gained")
        full = play_everything(ENGINE)
        self.assertIn("everything you need", ENGINE.handle(full, "q:h").text)


class PlaythroughTests(unittest.TestCase):
    def test_gating_blocks_early_shortcuts(self):
        st = ENGINE.new_state()
        st.started = True
        # rug needs the coroner's report
        screen = ENGINE.handle(st, "q:spot:study:rug")
        self.assertIn("🔒", screen.text)
        self.assertNotIn("ampule_shard", st.clues)
        # Blue Heron and Pier 9 are closed
        ENGINE.handle(st, "q:loc:heron")
        self.assertNotIn("heron", st.visited)
        ENGINE.handle(st, "q:loc:pier9")
        self.assertNotIn("pier9", st.visited)
        # a topic with unmet requirements doesn't pay out
        ENGINE.handle(st, "q:t:calloway:parcel")
        self.assertNotIn("calloway_ok", st.clues)

    def test_repeat_actions_are_free_and_do_not_duplicate(self):
        st = ENGINE.new_state()
        ENGINE.handle(st, "q:spot:study:desk")
        a = st.actions
        ENGINE.handle(st, "q:spot:study:desk")
        self.assertEqual(st.actions, a)
        self.assertEqual(st.clues.count("flask"), 1)

    def test_wrong_and_partial_accusations_keep_case_open(self):
        st = play_everything(ENGINE)
        s = ENGINE.handle(st, "q:a3:eleanor:1:1")
        self.assertFalse(st.solved)
        self.assertIn("Eleanor", s.text)
        s = ENGINE.handle(st, "q:a3:voss:0:1")  # right killer, wrong method
        self.assertFalse(st.solved)
        self.assertIn("proof", s.text)

    def test_correct_accusation_solves(self):
        st = play_everything(ENGINE)
        how = next(i for i, c in enumerate(CASE.hows) if c.correct)
        why = next(i for i, c in enumerate(CASE.whys) if c.correct)
        s = ENGINE.handle(st, f"q:a3:{CASE.culprit}:{how}:{why}")
        self.assertTrue(st.solved)
        self.assertIn("CASE CLOSED", s.text)
        self.assertIn("Rank", s.text)

    def test_shortest_critical_path_exists(self):
        """A player who follows only the key chain can solve the case."""
        st = ENGINE.new_state()
        path = [
            "q:t:calloway:coroner", "q:spot:study:desk", "q:spot:study:rug", "q:spot:study:ashtray",
            "q:spot:study:sofa", "q:loc:heron", "q:pc:vera:lipstick_glass", "q:t:vera:upstairs",
            "q:loc:lobby", "q:t:nell:parcel", "q:t:calloway:parcel", "q:t:nell:release",
            "q:t:webb:ice", "q:t:webb:monday", "q:loc:clinic", "q:spot:clinic:cabinet", "q:spot:clinic:rolltop",
        ]
        for step in path:
            ENGINE.handle(st, step)
        for needed in ("lab_report", "flask", "ampule_shard", "two_drops", "real_ledger", "ice_run",
                       "vera_saw", "monday_threat", "ampule_log", "deposit_slips"):
            self.assertIn(needed, st.clues)
        self.assertLess(st.actions, ENGINE.total_actions)

    def test_state_roundtrip(self):
        st = play_everything(ENGINE)
        again = State.loads(st.dumps())
        self.assertEqual(st, again)
        self.assertEqual(State.loads('{"started": true, "bogus": 1}').started, True)

    def test_restart_confirm_screen(self):
        self.assertIsInstance(ENGINE.handle(ENGINE.new_state(), "q:new"), Screen)


if __name__ == "__main__":
    unittest.main()
