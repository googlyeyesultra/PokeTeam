import unittest
import md_for_tests
from analyze import Weights


class CustomDataAnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.md = md_for_tests.get_custom_test_md("minitest")

    def test_find_counters(self):
        counters = sorted(self.md.find_counters("Rock").items(), key=lambda kv: -kv[1])

        self.assertEqual(counters[0][0], "MegaPaper")
        self.assertEqual(counters[1][0], "Paper")

        counters = sorted(self.md.find_counters("Paper").items(), key=lambda kv: -kv[1])
        self.assertEqual(counters[0][0], "MegaScissors")
        self.assertEqual(counters[1][0], "Scissors")

    def test_analyze_empty(self):
        weights = Weights(1, 1, 1)
        threats, scores, my_team, swaps = self.md.analyze([], weights)
        self.assertFalse(swaps)

        # Checks for duplicates by checking length and all members.
        self.assertEqual(len(my_team), 6)
        self.assertIn("Rock", my_team)
        self.assertIn("Paper", my_team)
        self.assertIn("Scissors", my_team)
        self.assertIn("MegaRock", my_team)
        self.assertIn("MegaPaper", my_team)
        self.assertIn("MegaScissors", my_team)

        # With no mons, usage score is only thing to go off of.
        sorted_by_combined = sorted(scores, key=lambda kv: kv[1])
        sorted_by_usage = sorted(scores, key=lambda kv: kv[4])
        self.assertListEqual(sorted_by_combined, sorted_by_usage)

    def test_usage_no_duplicates(self):
        # Even a small team weight should prevent duplicates.
        weights = Weights(0, .01, 100)
        _, _, my_team, _ = self.md.analyze([], weights)

        # Should be in order by usage (since highest usage will be added first, then next, etc.)
        self.assertListEqual(my_team, ["MegaScissors", "MegaPaper", "MegaRock",
                                       "Scissors", "Paper", "Rock"])

    def test_usage_duplicates(self):
        # No team weight should allow duplicates.
        weights = Weights(0, 0, 1)
        _, _, my_team, _ = self.md.analyze([], weights)

        # With only usage, the top Pokemon should appear over and over.
        self.assertListEqual(my_team, ["MegaScissors", "MegaScissors", "MegaScissors",
                                       "MegaScissors", "MegaScissors", "MegaScissors"])
