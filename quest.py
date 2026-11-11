"""Detective-quest engine. Pure logic: content dataclasses, player state, screens.

A case is data (see cases/). The engine turns callback strings like "q:spot:study:desk"
into a Screen (text + button rows) and mutates the player's State. No Telegram imports,
so the whole case can be played and tested offline.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields

MAX_TEXT = 3900  # Telegram hard limit is 4096; keep headroom for the clue footer

# ----------------------------------------------------------------- content


@dataclass(frozen=True)
class Clue:
    id: str
    title: str  # short, shown on buttons
    text: str


@dataclass(frozen=True)
class Spot:
    id: str
    label: str
    text: str
    gives: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    locked_hint: str = "Not yet. You have no reason to look here."


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    intro: str
    spots: tuple[Spot, ...] = ()
    people: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    text: str
    gives: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Reaction:
    clue: str
    text: str
    gives: tuple[str, ...] = ()


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    role: str
    intro: str
    topics: tuple[Topic, ...] = ()
    reactions: tuple[Reaction, ...] = ()
    default_reaction: str = "A blank look. It doesn't seem to mean anything to them."


@dataclass(frozen=True)
class Choice:
    label: str
    correct: bool = False


@dataclass(frozen=True)
class Hint:
    unless: str  # shown while this clue is still missing
    text: str


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    tagline: str
    briefing: str
    locations: tuple[Location, ...]
    characters: tuple[Character, ...]
    clues: tuple[Clue, ...]
    suspects: tuple[str, ...]
    culprit: str
    hows: tuple[Choice, ...]
    whys: tuple[Choice, ...]
    hints: tuple[Hint, ...]
    wrong_culprit: dict  # character id -> Calloway's reply
    partial_text: str
    solved_text: str
    always_met: tuple[str, ...] = ()
    solved_drops: int = 30


# ------------------------------------------------------------------- state


@dataclass
class State:
    started: bool = False
    clues: list = field(default_factory=list)
    visited: list = field(default_factory=list)
    met: list = field(default_factory=list)
    done: list = field(default_factory=list)  # "s:loc:spot", "t:char:topic", "r:char:clue"
    actions: int = 0
    hints: int = 0
    accusations: int = 0
    solved: bool = False

    def dumps(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def loads(cls, raw: str) -> "State":
        data = json.loads(raw)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


# ----------------------------------------------------------------- screens


@dataclass
class Btn:
    label: str
    data: str


@dataclass
class Screen:
    text: str
    rows: list


def _row(label: str, data: str) -> list:
    return [Btn(label, data)]


# ------------------------------------------------------------------ engine


class Engine:
    HINT_COST = 2
    WRONG_ACCUSATION_COST = 5

    def __init__(self, case: Case):
        self.case = case
        self.locs = {l.id: l for l in case.locations}
        self.chars = {c.id: c for c in case.characters}
        self.clues = {c.id: c for c in case.clues}
        self.total_actions = sum(len(l.spots) for l in case.locations) + sum(
            len(c.topics) for c in case.characters
        )

    # ---- state helpers
    def new_state(self) -> State:
        return State(met=list(self.case.always_met))

    def _has(self, st: State, reqs) -> bool:
        return all(r in st.clues for r in reqs)

    def _gain(self, st: State, ids) -> list:
        titles = []
        for cid in ids:
            if cid not in st.clues:
                st.clues.append(cid)
                titles.append(self.clues[cid].title)
        return titles

    @staticmethod
    def _new_clue_lines(titles) -> str:
        return "".join(f"\n\n🔎 <b>New clue:</b> {t}" for t in titles[:1]) + "".join(
            f"\n🔎 <b>New clue:</b> {t}" for t in titles[1:]
        )

    def _spend(self, st: State, n: int = 1) -> None:
        st.actions += n

    def rank(self, st: State) -> str:
        ratio = st.actions / max(1, self.total_actions)
        if ratio <= 0.75:
            return "★★★ Ace detective"
        if ratio <= 1.0:
            return "★★☆ Sharp eye"
        return "★☆☆ Thorough"

    # ---- dispatcher
    def handle(self, st: State, data: str) -> Screen:
        p = data.split(":")
        cmd = p[1] if len(p) > 1 else "hub"
        try:
            if cmd == "intro":
                return self.intro(st)
            if cmd == "begin":
                st.started = True
                return self.hub(st)
            if cmd == "hub":
                return self.hub(st)
            if cmd == "locs":
                return self.locations(st)
            if cmd == "loc":
                return self.location(st, p[2])
            if cmd == "spot":
                return self.spot(st, p[2], p[3])
            if cmd == "ppl":
                return self.people(st)
            if cmd == "p":
                return self.person(st, p[2])
            if cmd == "t":
                return self.topic(st, p[2], p[3])
            if cmd == "pr":
                return self.present_menu(st, p[2])
            if cmd == "pc":
                return self.present(st, p[2], p[3])
            if cmd == "nb":
                return self.notebook(st)
            if cmd == "c":
                return self.clue_detail(st, p[2])
            if cmd == "h":
                return self.hint(st)
            if cmd == "acc":
                return self.accuse_menu(st)
            if cmd == "a1":
                return self.accuse_how(st, p[2])
            if cmd == "a2":
                return self.accuse_why(st, p[2], int(p[3]))
            if cmd == "a3":
                return self.accuse_result(st, p[2], int(p[3]), int(p[4]))
            if cmd == "new":
                return self.confirm_restart()
        except (KeyError, IndexError, ValueError):
            pass
        return self.hub(st)

    # ---- screens
    def intro(self, st: State) -> Screen:
        c = self.case
        return Screen(
            f"🕵️ <b>{c.title}</b>\n<i>{c.tagline}</i>\n\n{c.briefing}",
            [_row("🔍 Begin the investigation", "q:begin")],
        )

    def hub(self, st: State) -> Screen:
        c = self.case
        text = (
            f"🕵️ <b>{c.title}</b>\n\n"
            f"Clues in your notebook: <b>{len(st.clues)}</b>\n"
            f"Actions used: <b>{st.actions}</b>\n\n"
            "Where to next, Detective?"
        )
        rows = [
            _row("📍 Locations", "q:locs"),
            _row("👥 People", "q:ppl"),
            _row(f"🗒 Notebook ({len(st.clues)})", "q:nb"),
            [Btn("💡 Hint", "q:h"), Btn("⚖️ Accuse", "q:acc")],
            [Btn("🏠 Menu", "menu:home"), Btn("🔄 Restart case", "q:new")],
        ]
        return Screen(text, rows)

    def locations(self, st: State) -> Screen:
        rows, locked = [], 0
        for loc in self.case.locations:
            if self._has(st, loc.requires):
                mark = "✔ " if loc.id in st.visited else ""
                rows.append(_row(f"📍 {mark}{loc.name}", f"q:loc:{loc.id}"))
            else:
                locked += 1
        text = "📍 <b>Locations</b>\n\nWhere do you want to go?"
        if locked:
            text += f"\n\n🔒 {locked} more place(s) you haven't found a reason to visit yet."
        rows.append(_row("⬅ Case file", "q:hub"))
        return Screen(text, rows)

    def location(self, st: State, lid: str) -> Screen:
        loc = self.locs[lid]
        if not self._has(st, loc.requires):
            return self.locations(st)
        if lid not in st.visited:
            st.visited.append(lid)
        for cid in loc.people:
            if cid not in st.met:
                st.met.append(cid)
        rows = []
        for sp in loc.spots:
            if not self._has(st, sp.requires):
                rows.append(_row(f"🔒 {sp.label}", f"q:spot:{lid}:{sp.id}"))
            else:
                mark = "✔ " if f"s:{lid}:{sp.id}" in st.done else ""
                rows.append(_row(f"🔎 {mark}{sp.label}", f"q:spot:{lid}:{sp.id}"))
        for cid in loc.people:
            ch = self.chars[cid]
            rows.append(_row(f"💬 {ch.name}", f"q:p:{cid}"))
        rows.append(_row("⬅ Locations", "q:locs"))
        return Screen(f"📍 <b>{loc.name}</b>\n\n{loc.intro}", rows)

    def spot(self, st: State, lid: str, sid: str) -> Screen:
        loc = self.locs[lid]
        sp = next(s for s in loc.spots if s.id == sid)
        back = [_row("⬅ Back", f"q:loc:{lid}")]
        if not self._has(st, sp.requires):
            return Screen(f"🔒 <b>{sp.label}</b>\n\n{sp.locked_hint}", back)
        key = f"s:{lid}:{sid}"
        if key in st.done:
            return Screen(f"🔎 <b>{sp.label}</b> <i>(already searched)</i>\n\n{sp.text}", back)
        st.done.append(key)
        self._spend(st)
        titles = self._gain(st, sp.gives)
        return Screen(f"🔎 <b>{sp.label}</b>\n\n{sp.text}{self._new_clue_lines(titles)}", back)

    def people(self, st: State) -> Screen:
        rows = []
        for cid in st.met:
            ch = self.chars[cid]
            rows.append(_row(f"💬 {ch.name} — {ch.role}", f"q:p:{cid}"))
        rows.append(_row("⬅ Case file", "q:hub"))
        return Screen("👥 <b>People</b>\n\nWho do you want to talk to?", rows)

    def person(self, st: State, cid: str) -> Screen:
        ch = self.chars[cid]
        if cid not in st.met:
            return self.people(st)
        rows = []
        for tp in ch.topics:
            if self._has(st, tp.requires):
                mark = "✔ " if f"t:{cid}:{tp.id}" in st.done else ""
                rows.append(_row(f"💬 {mark}{tp.label}", f"q:t:{cid}:{tp.id}"))
        if st.clues:
            rows.append(_row("📎 Present evidence", f"q:pr:{cid}"))
        rows.append(_row("⬅ People", "q:ppl"))
        return Screen(f"💬 <b>{ch.name}</b> — <i>{ch.role}</i>\n\n{ch.intro}", rows)

    def topic(self, st: State, cid: str, tid: str) -> Screen:
        ch = self.chars[cid]
        tp = next(t for t in ch.topics if t.id == tid)
        back = [_row("⬅ Back", f"q:p:{cid}")]
        if not self._has(st, tp.requires):
            return self.person(st, cid)
        key = f"t:{cid}:{tid}"
        titles = []
        if key not in st.done:
            st.done.append(key)
            self._spend(st)
            titles = self._gain(st, tp.gives)
        return Screen(f"💬 <b>{ch.name}</b>\n\n{tp.text}{self._new_clue_lines(titles)}", back)

    def present_menu(self, st: State, cid: str) -> Screen:
        ch = self.chars[cid]
        rows, pair = [], []
        for clue_id in st.clues:
            pair.append(Btn(f"📌 {self.clues[clue_id].title}", f"q:pc:{cid}:{clue_id}"))
            if len(pair) == 2:
                rows.append(pair)
                pair = []
        if pair:
            rows.append(pair)
        rows.append(_row("⬅ Back", f"q:p:{cid}"))
        return Screen(f"📎 <b>Present evidence to {ch.name}</b>\n\nWhat do you put on the table?", rows)

    def present(self, st: State, cid: str, clue_id: str) -> Screen:
        ch = self.chars[cid]
        if clue_id not in st.clues:
            return self.present_menu(st, cid)
        back = [_row("⬅ Back", f"q:pr:{cid}")]
        reaction = next((r for r in ch.reactions if r.clue == clue_id), None)
        key = f"r:{cid}:{clue_id}"
        head = f"📎 <b>{self.clues[clue_id].title}</b> → <b>{ch.name}</b>\n\n"
        if reaction is None:
            if key not in st.done:
                st.done.append(key)
                self._spend(st)
            return Screen(head + ch.default_reaction, back)
        titles = []
        if key not in st.done:
            st.done.append(key)
            self._spend(st)
            titles = self._gain(st, reaction.gives)
        return Screen(head + reaction.text + self._new_clue_lines(titles), back)

    def notebook(self, st: State) -> Screen:
        rows = [_row(f"📌 {self.clues[c].title}", f"q:c:{c}") for c in st.clues]
        rows.append(_row("⬅ Case file", "q:hub"))
        text = "🗒 <b>Notebook</b>\n\n" + (
            "Tap a clue to re-read it." if st.clues else "Empty. Start by searching a scene or talking to someone."
        )
        return Screen(text, rows)

    def clue_detail(self, st: State, clue_id: str) -> Screen:
        if clue_id not in st.clues:
            return self.notebook(st)
        c = self.clues[clue_id]
        return Screen(f"📌 <b>{c.title}</b>\n\n{c.text}", [_row("⬅ Notebook", "q:nb")])

    def hint(self, st: State) -> Screen:
        back = [_row("⬅ Case file", "q:hub")]
        for h in self.case.hints:
            if h.unless not in st.clues:
                st.hints += 1
                self._spend(st, self.HINT_COST)
                return Screen(f"💡 <b>Hint</b> <i>(costs {self.HINT_COST} actions)</i>\n\n{h.text}", back)
        return Screen("💡 You have everything you need. Time to name the killer.", back)

    # ---- accusation
    def accuse_menu(self, st: State) -> Screen:
        rows = [_row(f"⚖️ {self.chars[c].name}", f"q:a1:{c}") for c in self.case.suspects]
        rows.append(_row("⬅ Case file", "q:hub"))
        return Screen(
            "⚖️ <b>The accusation</b>\n\nInspector Calloway is waiting. Name the killer. "
            f"A wrong guess costs you {self.WRONG_ACCUSATION_COST} actions of credibility.",
            rows,
        )

    def accuse_how(self, st: State, cid: str) -> Screen:
        rows = [_row(c.label, f"q:a2:{cid}:{i}") for i, c in enumerate(self.case.hows)]
        rows.append(_row("⬅ Back", "q:acc"))
        return Screen(f"⚖️ Accusing <b>{self.chars[cid].name}</b>.\n\n<b>How</b> was Victor Halloran killed?", rows)

    def accuse_why(self, st: State, cid: str, how: int) -> Screen:
        rows = [_row(c.label, f"q:a3:{cid}:{how}:{i}") for i, c in enumerate(self.case.whys)]
        rows.append(_row("⬅ Back", f"q:a1:{cid}"))
        return Screen(f"⚖️ Accusing <b>{self.chars[cid].name}</b>.\n\n<b>Why</b> did they do it?", rows)

    def accuse_result(self, st: State, cid: str, how: int, why: int) -> Screen:
        case = self.case
        st.accusations += 1
        right_c = cid == case.culprit
        right_h = case.hows[how].correct
        right_w = case.whys[why].correct
        if right_c and right_h and right_w:
            st.solved = True
            return Screen(
                f"{case.solved_text}\n\n<b>Rank:</b> {self.rank(st)}\n"
                f"Actions: {st.actions} · Accusations: {st.accusations}",
                [_row("🏠 Menu", "menu:home")],
            )
        self._spend(st, self.WRONG_ACCUSATION_COST)
        text = case.partial_text if right_c else case.wrong_culprit.get(
            cid, "Calloway shakes her head. 'That won't hold up. Keep digging.'"
        )
        return Screen(
            f"⚖️ {text}\n\n<i>The case stays open. Go back to the evidence.</i>",
            [_row("⬅ Case file", "q:hub"), _row("⚖️ Try again", "q:acc")],
        )

    def confirm_restart(self) -> Screen:
        return Screen(
            "🔄 Restart the case from the beginning? All your clues will be lost.",
            [[Btn("Yes, restart", "q:newy"), Btn("No", "q:hub")]],
        )
