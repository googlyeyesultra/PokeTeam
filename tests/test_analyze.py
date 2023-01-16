import md_for_tests
import unittest
from dynamic_tests import dynamic

import analyze
import math


@dynamic(globals())
class AnalyzeTestCase(unittest.TestCase):
    def setUp(self):
        self.md = md_for_tests.get_test_md(self.dataset)

    def test_zero_weights(self):
        for counter in [0, 1]:
            for team in [0, 1]:
                for usage in [0, 1]:
                    with self.subTest(counter=counter, team=team, usage=usage):
                        weights = analyze.Weights(counter, team, usage)
                        threats, scores, _, _ = self.md.analyze([], weights)
                        self.validate_scores(scores)
                        self.validate_threats(threats)

    def test_order_invariance(self):
        poke_iter = iter(self.md.pokemon)
        poke1 = next(poke_iter)
        poke2 = next(poke_iter)
        threats1, scores1, team1, _ = self.md.analyze([poke1, poke2], analyze.Weights(1, 1, 1))
        threats2, scores2, team2, _ = self.md.analyze([poke2, poke1], analyze.Weights(1, 1, 1))
        self.assertListEqual(sorted(team1), sorted(team2))
        self.assertEqual(len(threats1), len(threats2))
        self.assertEqual(len(scores1), len(scores2))
        for threat in threats1:
            self.assertIn(threat, threats2)
            self.assertAlmostEqual(threats1[threat], threats2[threat])

        scores1_dict = {}
        for poke, combined, c, t, u in scores1:
            scores1_dict[poke] = (combined, c, t, u)

        for poke, combined, c, t, u in scores2:
            combined1, c1, t1, u1 = scores1_dict[poke]
            self.assertAlmostEqual(combined, combined1)
            self.assertAlmostEqual(c, c1)
            self.assertAlmostEqual(t, t1)
            self.assertAlmostEqual(u, u1)

    def test_no_swaps(self):  # Shouldn't be swaps on either empty team or team generated from empty.
        _, _, team, empty_swaps = self.md.analyze([], analyze.Weights(1, 1, 1))
        self.assertDictEqual(empty_swaps, {})
        _, _, _, team_swaps = self.md.analyze(team, analyze.Weights(1, 1, 1))
        self.assertDictEqual(team_swaps, {})

    def test_swaps(self):
        poke_iter = iter(self.md.pokemon)
        team = [next(poke_iter), next(poke_iter), next(poke_iter),
                next(poke_iter), next(poke_iter), next(poke_iter)]
        _, _, _, swaps = self.md.analyze(team, analyze.Weights(1, 1, 1))
        self.assertLessEqual(len(swaps), len(team))
        for swap in swaps:
            self.assertIn(swap, team)
            self.assertIn(swaps[swap][0], self.md.pokemon)
            self.validate_number(swaps[swap][1])
            self.assertGreater(swaps[swap][1], 0)

    def validate_number(self, number):
        self.assertFalse(math.isnan(number))
        self.assertFalse(math.isinf(number))

    def validate_scores(self, scores):
        for score in scores:
            self.assertIn(score[0], self.md.pokemon)
            for subscore in score[1:]:
                self.validate_number(subscore)
                self.assertGreaterEqual(subscore, 0)

    def validate_threats(self, threats_dict):
        for threat in threats_dict:
            self.assertIn(threat, self.md.pokemon)
            self.validate_number(threats_dict[threat])
