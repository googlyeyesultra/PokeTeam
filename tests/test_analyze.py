import md_for_tests
import unittest
from dynamic_tests import dynamic


@dynamic(globals())
class AnalyzeTestCase(unittest.TestCase):
    def setUp(self):
        self.md = md_for_tests.get_test_md(self.dataset)

    def test_something(self):
        self.assertEqual(True, False)  # add assertion here
