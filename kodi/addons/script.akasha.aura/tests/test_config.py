import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import config  # noqa: E402


class NormalizeServerUrlTests(unittest.TestCase):
    def test_empty_returns_empty(self):
        self.assertEqual(config.normalize_server_url(''), '')
        self.assertEqual(config.normalize_server_url(None), '')

    def test_strips_whitespace_and_trailing_slash(self):
        self.assertEqual(
            config.normalize_server_url('  http://192.168.100.133:32400/ '),
            'http://192.168.100.133:32400',
        )


class IsPlexConfiguredTests(unittest.TestCase):
    def test_false_when_missing_url_or_token(self):
        self.assertFalse(config.is_plex_configured('', 'tok'))
        self.assertFalse(config.is_plex_configured('http://host:32400', ''))
        self.assertFalse(config.is_plex_configured('http://host:32400', '   '))

    def test_true_when_both_set(self):
        self.assertTrue(config.is_plex_configured('http://host:32400', 'tok123'))


class BuildPlexHeadersTests(unittest.TestCase):
    def test_includes_token(self):
        headers = config.build_plex_headers('tok123')
        self.assertEqual(headers['X-Plex-Token'], 'tok123')
        self.assertEqual(headers['Accept'], 'application/json')

    def test_handles_missing_token(self):
        headers = config.build_plex_headers(None)
        self.assertEqual(headers['X-Plex-Token'], '')


class DefaultTabIndexTests(unittest.TestCase):
    def test_valid_index(self):
        self.assertEqual(config.default_tab_index('1'), 1)

    def test_out_of_range_falls_back_to_zero(self):
        self.assertEqual(config.default_tab_index('5'), 0)
        self.assertEqual(config.default_tab_index('-1'), 0)

    def test_invalid_value_falls_back_to_zero(self):
        self.assertEqual(config.default_tab_index('abc'), 0)
        self.assertEqual(config.default_tab_index(None), 0)


if __name__ == '__main__':
    unittest.main()
