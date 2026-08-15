import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import energy  # noqa: E402


class DimAlphaTests(unittest.TestCase):
    def test_no_dim_before_threshold(self):
        self.assertEqual(energy.dim_alpha(0, 120, 1800), 0)
        self.assertEqual(energy.dim_alpha(119, 120, 1800), 0)

    def test_ramps_linearly_between_dim_and_sleep(self):
        # Halfway between dim_after (120) and sleep_after (1800) => ~half of max_alpha.
        halfway = 120 + (1800 - 120) / 2
        alpha = energy.dim_alpha(halfway, 120, 1800, max_alpha=200)
        self.assertAlmostEqual(alpha, 100, delta=1)

    def test_reaches_max_alpha_at_sleep_threshold(self):
        self.assertEqual(energy.dim_alpha(1800, 120, 1800, max_alpha=200), 200)

    def test_never_exceeds_max_alpha_after_sleep_threshold(self):
        self.assertEqual(energy.dim_alpha(999999, 120, 1800, max_alpha=200), 200)

    def test_degenerate_config_sleep_before_dim(self):
        # Misconfiguration guard: sleep_after <= dim_after should not crash
        # or divide by zero, and should just jump to full darkness.
        self.assertEqual(energy.dim_alpha(500, 300, 300, max_alpha=200), 200)
        self.assertEqual(energy.dim_alpha(500, 300, 100, max_alpha=200), 200)


class DimOverlayColorTests(unittest.TestCase):
    def test_transparent_before_threshold(self):
        self.assertEqual(energy.dim_overlay_color(0, 120, 1800), energy.NO_DIM_COLOR)

    def test_hex_format_after_threshold(self):
        color = energy.dim_overlay_color(1800, 120, 1800)
        self.assertRegex(color, r'^[0-9A-F]{2}000000$')
        self.assertTrue(color.startswith('{:02X}'.format(energy.MAX_DIM_ALPHA)))


class ShouldSleepTests(unittest.TestCase):
    def test_false_before_threshold(self):
        self.assertFalse(energy.should_sleep(1799, 1800))

    def test_true_at_and_after_threshold(self):
        self.assertTrue(energy.should_sleep(1800, 1800))
        self.assertTrue(energy.should_sleep(5000, 1800))


class WidgetPresetTests(unittest.TestCase):
    def test_cycles_through_all_presets(self):
        interval = energy.WIDGET_PRESET_INTERVAL_SECONDS
        seen = {energy.widget_preset_for_elapsed(i * interval) for i in range(8)}
        self.assertEqual(seen, {0, 1, 2, 3})

    def test_stays_within_bounds(self):
        for elapsed in (0, 1, 599, 600, 601, 10**7):
            preset = energy.widget_preset_for_elapsed(elapsed)
            self.assertGreaterEqual(preset, 0)
            self.assertLess(preset, energy.WIDGET_PRESET_COUNT)


if __name__ == '__main__':
    unittest.main()
