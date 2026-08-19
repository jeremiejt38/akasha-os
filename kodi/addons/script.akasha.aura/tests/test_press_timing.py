"""Unit tests for the duplicated press_timing.py in script.akasha.aura."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

from press_timing import classify_press, DOUBLE, FIRST  # noqa: E402


class ClassifyPressTests(unittest.TestCase):
    def test_first_press_ever_is_first(self):
        self.assertEqual(classify_press(10.0, None), FIRST)

    def test_press_within_window_is_double(self):
        self.assertEqual(classify_press(10.1, 10.0, window_seconds=0.3), DOUBLE)

    def test_press_at_exact_window_edge_is_double(self):
        self.assertEqual(classify_press(0.3, 0.0, window_seconds=0.3), DOUBLE)

    def test_press_beyond_window_is_first(self):
        self.assertEqual(classify_press(10.31, 10.0, window_seconds=0.3), FIRST)

    def test_custom_window(self):
        self.assertEqual(classify_press(10.6, 10.0, window_seconds=0.5), FIRST)
        self.assertEqual(classify_press(10.4, 10.0, window_seconds=0.5), DOUBLE)


if __name__ == '__main__':
    unittest.main()
