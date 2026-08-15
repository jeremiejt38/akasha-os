import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import config  # noqa: E402


class LoadConfigTests(unittest.TestCase):
    def test_defaults_when_settings_empty(self):
        cfg = config.load_config({})
        self.assertEqual(cfg.content_path, config.DEFAULT_CONTENT_PATH)
        self.assertEqual(cfg.fallback_folder, config.DEFAULT_FALLBACK_FOLDER)
        self.assertEqual(cfg.inactivity_timeout_minutes, config.DEFAULTS['inactivity_timeout_minutes'])
        self.assertEqual(cfg.dim_after_minutes, config.DEFAULTS['dim_after_minutes'])
        self.assertEqual(cfg.sleep_after_minutes, config.DEFAULTS['sleep_after_minutes'])
        self.assertTrue(cfg.weather_enabled)
        self.assertEqual(cfg.weather_city, config.DEFAULTS['weather_city'])

    def test_defaults_when_settings_none(self):
        cfg = config.load_config(None)
        self.assertEqual(cfg.content_path, config.DEFAULT_CONTENT_PATH)

    def test_valid_overrides_are_applied(self):
        cfg = config.load_config({
            'content_path': '/storage/ambient/photos-perso',
            'inactivity_timeout_minutes': '10',
            'dim_after_minutes': '5',
            'sleep_after_minutes': '45',
            'weather_enabled': 'false',
            'weather_city': 'Lyon',
            'weather_latitude': '45.75',
            'weather_longitude': '4.85',
        })
        self.assertEqual(cfg.content_path, '/storage/ambient/photos-perso')
        self.assertEqual(cfg.inactivity_timeout_minutes, 10)
        self.assertEqual(cfg.dim_after_minutes, 5)
        self.assertEqual(cfg.sleep_after_minutes, 45)
        self.assertFalse(cfg.weather_enabled)
        self.assertEqual(cfg.weather_city, 'Lyon')
        self.assertEqual(cfg.weather_latitude, 45.75)
        self.assertEqual(cfg.weather_longitude, 4.85)

    def test_invalid_numeric_values_fall_back_to_defaults(self):
        cfg = config.load_config({
            'dim_after_minutes': 'not-a-number',
            'sleep_after_minutes': None,
        })
        self.assertEqual(cfg.dim_after_minutes, config.DEFAULTS['dim_after_minutes'])
        self.assertEqual(cfg.sleep_after_minutes, config.DEFAULTS['sleep_after_minutes'])

    def test_numeric_values_are_clamped_to_sane_bounds(self):
        cfg = config.load_config({
            'dim_after_minutes': '99999',
            'sleep_after_minutes': '-10',
        })
        self.assertLessEqual(cfg.dim_after_minutes, 120)
        self.assertGreaterEqual(cfg.sleep_after_minutes, 1)

    def test_blank_content_path_falls_back_to_default(self):
        cfg = config.load_config({'content_path': '   '})
        self.assertEqual(cfg.content_path, config.DEFAULT_CONTENT_PATH)

    def test_seconds_properties_are_derived_from_minutes(self):
        cfg = config.load_config({
            'inactivity_timeout_minutes': '5', 'dim_after_minutes': '2', 'sleep_after_minutes': '30',
        })
        self.assertEqual(cfg.inactivity_timeout_seconds, 300)
        self.assertEqual(cfg.dim_after_seconds, 120)
        self.assertEqual(cfg.sleep_after_seconds, 1800)


if __name__ == '__main__':
    unittest.main()
