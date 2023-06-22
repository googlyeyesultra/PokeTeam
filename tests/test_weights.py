import unittest
from analyze import Weights


class WeightsTestCase(unittest.TestCase):
    def test_weights(self):
        weights = Weights(1, 2, 3)
        self.assertEqual(weights.counter, 1)
        self.assertEqual(weights.team, 2)
        self.assertEqual(weights.usage, 3)

    def test_all_zero(self):
        weights = Weights(0, 0, 0)
        self.assertEqual(weights.counter, weights.team)
        self.assertEqual(weights.team, weights.usage)
        self.assertNotEqual(weights.counter, 0)
