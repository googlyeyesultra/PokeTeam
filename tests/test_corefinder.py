import md_for_tests
import unittest
from dynamic_tests import dynamic

import corefinder


@dynamic(globals())
class CoreFinderTestCase(unittest.TestCase):
    def setUp(self):
        self.md = md_for_tests.get_test_md(self.dataset)
        self.target_edges = 100

    def test_zero_usage(self):
        cf = corefinder.CoreFinder(self.md, 0, self.target_edges)
        self.validate_cores(cf.find_cores())

    def test_non_zero_usage(self):
        cf = corefinder.CoreFinder(self.md, 5, self.target_edges)
        self.validate_cores(cf.find_cores())

    def validate_cores(self, cores):
        cores_set = set()
        self.assertLessEqual(len(cores), self.target_edges)
        self.assertTrue(cores)  # Should be non-empty.
        for core in cores:
            # Technically no upper limit on core size, but if they're ballooning up it's probably a bug.
            self.assertLessEqual(len(core), 30)
            self.assertGreaterEqual(len(core), 2)
            c = frozenset(core)
            for c_set in cores_set:
                self.assertFalse(c.issubset(c_set))
                self.assertFalse(c_set.issubset(c))
            cores_set.add(c)
