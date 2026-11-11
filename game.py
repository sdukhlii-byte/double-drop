"""Pure game logic for Raindrop Catch (no Telegram, no I/O) so it is easy to test."""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

GRID_ROWS = 3
GRID_COLS = 4
CELLS = GRID_ROWS * GRID_COLS
DROPS_PER_ROUND = 10
REACTION_WINDOW = 3.5  # seconds to tap a drop before it counts as missed
DAILY_BONUS = 5  # extra drops for the first round of the day
STREAK_STEP = 3  # every full STREAK_STEP of best streak gives +1 bonus drop


@dataclass
class Round:
    game_id: str
    user_id: int
    target: int
    shown_at: float
    step: int = 1
    caught: int = 0
    streak: int = 0
    best_streak: int = 0


@dataclass
class TapResult:
    hit: bool
    slow: bool
    finished: bool


def pick_target(prev: int | None = None, rng: random.Random | None = None) -> int:
    rng = rng or random
    while True:
        cell = rng.randrange(CELLS)
        if cell != prev:
            return cell


def new_round(user_id: int, now: float, rng: random.Random | None = None) -> Round:
    return Round(
        game_id=uuid.uuid4().hex[:8],
        user_id=user_id,
        target=pick_target(None, rng),
        shown_at=now,
    )


def tap(rnd: Round, cell: int, now: float, rng: random.Random | None = None) -> TapResult:
    """Register a tap on `cell`, then advance to the next drop (or finish)."""
    on_target = cell == rnd.target
    hit = on_target and (now - rnd.shown_at) <= REACTION_WINDOW
    slow = on_target and not hit

    if hit:
        rnd.caught += 1
        rnd.streak += 1
        rnd.best_streak = max(rnd.best_streak, rnd.streak)
    else:
        rnd.streak = 0

    finished = rnd.step >= DROPS_PER_ROUND
    if not finished:
        rnd.step += 1
        rnd.target = pick_target(rnd.target, rng)
        rnd.shown_at = now
    return TapResult(hit=hit, slow=slow, finished=finished)


def round_drops(caught: int, best_streak: int) -> int:
    """Drops earned for a finished round (without the daily bonus)."""
    return caught + best_streak // STREAK_STEP
