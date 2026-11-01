"""Unit tests for aura_detail.py pure helpers.

The module imports xbmc/xbmcgui (dialog class) so tests stub them out
before importing — same approach the Kodi runtime provides natively.
"""

import sys
import types
import unittest

for mod in ('xbmc', 'xbmcgui', 'xbmcaddon', 'xbmcvfs'):
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)
sys.modules['xbmcgui'].WindowXMLDialog = object
sys.modules['xbmcvfs'].translatePath = lambda p: p
sys.modules['xbmc'].log = lambda *args, **kwargs: None
sys.modules['xbmc'].LOGWARNING = 3
sys.modules['xbmc'].LOGERROR = 4

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


class TestProviderIcon(unittest.TestCase):
    RT = 'rottentomatoes://image.rating'

    def test_fresh_tomato_at_60_and_above(self):
        for v in (6.0, 60, 7.5, 100):
            self.assertEqual(
                aura_detail._provider_icon(self.RT, value=v), 'prov-rt.png',
                v)

    def test_splat_below_60(self):
        for v in (4.1, 41, 59):
            self.assertEqual(
                aura_detail._provider_icon(self.RT, value=v),
                'prov-rt-splat.png', v)

    def test_audience_keeps_popcorn(self):
        self.assertEqual(
            aura_detail._provider_icon(self.RT, audience=True, value=20),
            'prov-rt-aud.png')

    def test_unparseable_score_defaults_fresh(self):
        self.assertEqual(
            aura_detail._provider_icon(self.RT, value='n/a'), 'prov-rt.png')


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


class _SeasonsClient:
    """Minimal client stub recording show_seasons calls."""

    def __init__(self, seasons):
        self.seasons = seasons
        self.calls = []

    def show_seasons(self, rating_key):
        self.calls.append(rating_key)
        return self.seasons


class TestLoadSeasons(unittest.TestCase):
    """_load_seasons keys its cache by rating_key (the window instance
    is reused across detail pages) and drops seasons whose
    parentRatingKey names another show — the backend once served an
    Alya season on Black Butler's page (rk=82547)."""

    def _window(self, rk='82547', seasons=None, seasons_key=None,
                client=None, bg_seasons=None):
        win = types.SimpleNamespace()
        win.item = {'rating_key': rk}
        win.client = client
        win._seasons = list(seasons) if seasons else []
        win._seasons_key = seasons_key
        win._bg_done = {}
        win._bg_results = {}
        if bg_seasons is not None:
            win._bg_done['seasons'] = True
            win._bg_get = lambda key, timeout=12.0: bg_seasons
        return win

    def _load(self, win):
        aura_detail.AuraDetailWindow._load_seasons(win)

    def test_short_circuits_only_for_the_same_show(self):
        client = _SeasonsClient([{'index': 9}])
        win = self._window(
            seasons=[{'index': 1, 'parent_rating_key': '82547'}],
            seasons_key='82547', client=client)
        self._load(win)
        self.assertEqual(client.calls, [])
        self.assertEqual(win._seasons[0]['index'], 1)

    def test_refetches_when_cached_list_belongs_to_another_show(self):
        client = _SeasonsClient(
            [{'index': 1, 'parent_rating_key': '82547'}])
        win = self._window(
            seasons=[{'index': 3, 'parent_rating_key': '81486'}],
            seasons_key='81486', client=client)
        self._load(win)
        self.assertEqual(client.calls, ['82547'])
        self.assertEqual(win._seasons_key, '82547')
        self.assertEqual(win._seasons[0]['parent_rating_key'], '82547')

    def test_prefetched_background_result_wins_and_stamps_key(self):
        client = _SeasonsClient([])
        win = self._window(
            client=client,
            bg_seasons=[{'index': 5, 'parent_rating_key': '82547'}])
        self._load(win)
        self.assertEqual(client.calls, [])
        self.assertEqual(win._seasons[0]['index'], 5)
        self.assertEqual(win._seasons_key, '82547')

    def test_drops_seasons_parented_to_another_show(self):
        client = _SeasonsClient([
            {'index': 1, 'parent_rating_key': '82547'},
            {'index': 2, 'parent_rating_key': '82547'},
            {'index': 1, 'parent_rating_key': '81486'},
        ])
        win = self._window(client=client)
        logs = []
        original_log = aura_detail.xbmc.log
        aura_detail.xbmc.log = lambda msg, level=None: logs.append(msg)
        try:
            self._load(win)
        finally:
            aura_detail.xbmc.log = original_log
        self.assertEqual(
            [s['parent_rating_key'] for s in win._seasons],
            ['82547', '82547'])
        self.assertTrue(any('foreign seasons' in m for m in logs))

    def test_keeps_seasons_without_or_with_matching_parent(self):
        client = _SeasonsClient([
            {'index': 1, 'parent_rating_key': 82547},  # int == str rk
            {'index': 2},                            # no parent key
        ])
        win = self._window(client=client)
        self._load(win)
        self.assertEqual(len(win._seasons), 2)

    def test_failed_fetch_resets_seasons_and_key(self):
        class BoomClient:
            def show_seasons(self, rating_key):
                raise RuntimeError('boom')

        win = self._window(client=BoomClient())
        self._load(win)
        self.assertEqual(win._seasons, [])
        self.assertIsNone(win._seasons_key)

    def test_clear_fetch_state_forces_a_fresh_fetch_for_the_new_item(self):
        """Regression: _open_detail swaps self.item while the window's
        bg maps still hold the previous page's fetches; a deferred
        reader joining them once served an Alya season on Black
        Butler's page. Clearing the state forces a fresh fetch."""
        client = _SeasonsClient(
            [{'index': 1, 'parent_rating_key': '82547'}])
        win = self._window(
            client=client,
            bg_seasons=[{'index': 1, 'parent_rating_key': '81486'}])
        aura_detail.AuraDetailWindow._clear_fetch_state(win)
        self._load(win)
        self.assertEqual(client.calls, ['82547'])
        self.assertEqual(
            [s['parent_rating_key'] for s in win._seasons], ['82547'])
        self.assertEqual(win._seasons_key, '82547')
        self.assertEqual(win._bg_done, {})


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
