import random
import unittest

import game


class GameTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1)

    def test_target_never_repeats(self):
        prev = None
        for _ in range(500):
            t = game.pick_target(prev, self.rng)
            self.assertNotEqual(t, prev)
            self.assertTrue(0 <= t < game.CELLS)
            prev = t

    def test_perfect_round(self):
        rnd = game.new_round(1, now=0.0, rng=self.rng)
        t = 0.0
        for i in range(game.DROPS_PER_ROUND):
            t += 0.5
            res = game.tap(rnd, rnd.target, t, self.rng)
            self.assertTrue(res.hit)
            self.assertEqual(res.finished, i == game.DROPS_PER_ROUND - 1)
        self.assertEqual(rnd.caught, game.DROPS_PER_ROUND)
        self.assertEqual(rnd.best_streak, game.DROPS_PER_ROUND)
        self.assertEqual(game.round_drops(rnd.caught, rnd.best_streak), 10 + 10 // 3)

    def test_miss_resets_streak(self):
        rnd = game.new_round(1, now=0.0, rng=self.rng)
        game.tap(rnd, rnd.target, 0.5, self.rng)
        game.tap(rnd, rnd.target, 1.0, self.rng)
        wrong = (rnd.target + 1) % game.CELLS
        res = game.tap(rnd, wrong, 1.5, self.rng)
        self.assertFalse(res.hit)
        self.assertFalse(res.slow)
        self.assertEqual(rnd.streak, 0)
        self.assertEqual(rnd.best_streak, 2)
        self.assertEqual(rnd.caught, 2)

    def test_slow_tap_is_a_miss(self):
        rnd = game.new_round(1, now=0.0, rng=self.rng)
        res = game.tap(rnd, rnd.target, game.REACTION_WINDOW + 0.1, self.rng)
        self.assertTrue(res.slow)
        self.assertFalse(res.hit)
        self.assertEqual(rnd.caught, 0)

    def test_round_always_finishes_after_n_taps(self):
        rnd = game.new_round(1, now=0.0, rng=self.rng)
        results = [game.tap(rnd, 0, float(i), self.rng) for i in range(game.DROPS_PER_ROUND)]
        self.assertTrue(results[-1].finished)
        self.assertFalse(any(r.finished for r in results[:-1]))


if __name__ == "__main__":
    unittest.main()
