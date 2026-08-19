"""Unit tests for battery_alert.py — no xbmc dependency."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

from battery_alert import BatteryAlertTracker  # noqa: E402


class BatteryAlertTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = BatteryAlertTracker()

    def test_no_alert_while_above_threshold(self):
        self.assertFalse(self.tracker.observe(100))
        self.assertFalse(self.tracker.observe(20))
        self.assertFalse(self.tracker.observe(15))

    def test_alert_fires_once_when_crossing_below_threshold(self):
        self.tracker.observe(20)
        self.assertTrue(self.tracker.observe(14))

    def test_alert_does_not_spam_while_staying_low(self):
        self.tracker.observe(20)
        self.assertTrue(self.tracker.observe(14))
        self.assertFalse(self.tracker.observe(13))
        self.assertFalse(self.tracker.observe(10))
        self.assertFalse(self.tracker.observe(14))

    def test_alert_rearms_after_recovering_above_reset_threshold(self):
        self.tracker.observe(20)
        self.assertTrue(self.tracker.observe(14))
        self.assertFalse(self.tracker.observe(19))  # below reset_threshold, still armed off
        self.assertFalse(self.tracker.observe(20))  # reaches reset_threshold, re-arms
        self.assertTrue(self.tracker.observe(14))    # drops below again -> alert fires again

    def test_observe_none_never_alerts(self):
        self.assertFalse(self.tracker.observe(None))
        self.tracker.observe(20)
        self.assertFalse(self.tracker.observe(None))

    def test_constructor_rejects_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            BatteryAlertTracker(low_threshold=20, reset_threshold=15)
        with self.assertRaises(ValueError):
            BatteryAlertTracker(low_threshold=20, reset_threshold=20)


if __name__ == '__main__':
    unittest.main()
