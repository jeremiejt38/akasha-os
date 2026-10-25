"""Unit tests for aura_detail.py pure helpers.

The module imports xbmc/xbmcgui (dialog class) so tests stub them out
before importing — same approach the Kodi runtime provides natively.
"""

import sys
import types
import unittest

for mod in ('xbmc', 'xbmcgui', 'xbmcaddon'):
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)
sys.modules['xbmcgui'].WindowXMLDialog = object

import aura_detail  # noqa: E402


class TestProviderLabel(unittest.TestCase):
    def test_imdb(self):
        self.assertEqual(
            aura_detail._provider_label('imdb://image.rating'), 'IMDb')

    def test_tmdb(self):
        self.assertEqual(
            aura_detail._provider_label('themoviedb://image.rating'), 'TMDB')

    def test_rotten_tomatoes(self):
        self.assertEqual(
            aura_detail._provider_label(
                'rottentomatoes://image.rating.ripe'), 'RT')

    def test_unknown_or_empty(self):
        self.assertEqual(aura_detail._provider_label(''), '')
        self.assertEqual(aura_detail._provider_label(None), '')


class TestFormatRating(unittest.TestCase):
    def test_ten_scale(self):
        self.assertEqual(aura_detail._fmt_rating(6.9, 'imdb://x'), '6.9')

    def test_rotten_tomatoes_percent(self):
        self.assertEqual(
            aura_detail._fmt_rating(37, 'rottentomatoes://x'), '37%')

    def test_over_ten_without_provider_is_percent(self):
        self.assertEqual(aura_detail._fmt_rating(84, ''), '84%')

    def test_bad_value(self):
        self.assertEqual(aura_detail._fmt_rating(None, ''), '')
        self.assertEqual(aura_detail._fmt_rating('n/a', ''), '')


class TestSeasonLabel(unittest.TestCase):
    """Season cards/headers must render in the UI locale, never the raw
    server title ('Season 7' comes back in the server locale)."""

    def test_french_label_from_index(self):
        season = {'index': 7, 'title': 'Season 7'}
        self.assertEqual(
            aura_detail.AuraDetailWindow._season_label(season), 'Saison 7')

    def test_missing_index_falls_back_to_title(self):
        season = {'title': 'Specials'}
        self.assertEqual(
            aura_detail.AuraDetailWindow._season_label(season),
            'Saison Specials')


class TestFormatDuration(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(aura_detail._fmt_duration(47 * 60000), '47m')

    def test_hours_and_minutes(self):
        self.assertEqual(aura_detail._fmt_duration(107 * 60000), '1h 47m')

    def test_empty(self):
        self.assertEqual(aura_detail._fmt_duration(0), '')
        self.assertEqual(aura_detail._fmt_duration(None), '')


if __name__ == '__main__':
    unittest.main()
