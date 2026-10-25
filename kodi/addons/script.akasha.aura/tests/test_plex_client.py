"""Unit tests for plex_client.py — no xbmc dependency."""

import io
import json
import unittest
from unittest.mock import patch

import plex_client


class MockHTTPResponse:
    """Minimal file-like stand-in for urllib.urlopen return value."""

    def __init__(self, payload, status=200):
        self._body = io.BytesIO(json.dumps(payload).encode('utf-8'))
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body.read()


class TestPlexClient(unittest.TestCase):
    def setUp(self):
        self.client = plex_client.PlexClient(
            'http://192.168.100.133:32400', 'tok123')

    @patch('urllib.request.urlopen')
    def test_on_deck_parses_metadata(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Metadata': [
                    {
                        'title': 'Inception',
                        'type': 'movie',
                        'ratingKey': '123',
                        'thumb': '/library/metadata/123/thumb/1',
                        'year': 2010,
                        'originallyAvailableAt': '2010-07-16',
                    }
                ]
            }
        })
        items = self.client.on_deck(limit=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Inception')
        self.assertEqual(items[0]['rating_key'], '123')
        self.assertEqual(items[0]['year'], 2010)
        self.assertIn('tok123', items[0]['thumb_url'])
        self.assertIsNone(items[0]['section_id'])

    @patch('urllib.request.urlopen')
    def test_video_dict_captures_section_id(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Metadata': [{'title': 'Inception', 'librarySectionID': 1}]
            }
        })
        items = self.client.on_deck(limit=1)
        self.assertEqual(items[0]['section_id'], '1')

    @patch('urllib.request.urlopen')
    def test_recently_added_endpoint(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Metadata': [
                    {'title': 'Nouveau', 'type': 'movie', 'ratingKey': '2'}
                ]
            }
        })
        items = self.client.recently_added(limit=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Nouveau')

    @patch('urllib.request.urlopen')
    def test_movie_sections_filters_by_type(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Directory': [
                    {'key': '1', 'title': 'Films', 'type': 'movie'},
                    {'key': '2', 'title': 'Séries', 'type': 'show'},
                ]
            }
        })
        sections = self.client.movie_sections()
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['title'], 'Films')

    @patch('urllib.request.urlopen')
    def test_recently_released_uses_sort_param(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.recently_released('1', limit=5)
        self.assertIn('sort=originallyAvailableAt%3Adesc', captured['url'])

    @patch('urllib.request.urlopen')
    def test_genre_list(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Directory': [
                    {'title': 'Action'},
                    {'title': 'Comédie'},
                ]
            }
        })
        genres = self.client.section_genres('1')
        self.assertEqual(genres, ['Action', 'Comédie'])

    @patch('urllib.request.urlopen')
    def test_by_genre(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Metadata': [
                    {'title': 'Action Man', 'type': 'movie', 'ratingKey': '9'}
                ]
            }
        })
        items = self.client.by_genre('1', 'Action', limit=5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Action Man')

    @patch('urllib.request.urlopen')
    def test_entertainment_rows_combines_sections_and_genres(self, mock_urlopen):
        responses = [
            # onDeck
            {'MediaContainer': {'Metadata': []}},
            # recentlyAdded
            {'MediaContainer': {'Metadata': []}},
            # movie_sections -> /library/sections
            {'MediaContainer': {'Directory': [
                {'key': '1', 'title': 'Films', 'type': 'movie'},
            ]}},
            # recently_released
            {'MediaContainer': {'Metadata': [
                {'title': 'New Release', 'type': 'movie', 'ratingKey': '10'}
            ]}},
            # section_genres
            {'MediaContainer': {'Directory': [
                {'title': 'Drame'},
            ]}},
            # by_genre
            {'MediaContainer': {'Metadata': [
                {'title': 'Drame One', 'type': 'movie', 'ratingKey': '11'}
            ]}},
        ]

        def fake_urlopen(req, *args, **kwargs):
            return MockHTTPResponse(responses.pop(0))

        mock_urlopen.side_effect = fake_urlopen
        rows = self.client.entertainment_rows(limits={
            'on_deck': 1,
            'recently_added': 1,
            'recently_released': 1,
            'per_genre': 1,
            'genres_per_section': 1,
        })
        labels = [r['label'] for r in rows]
        self.assertIn('Continuer à regarder', labels)
        self.assertIn('Ajoutés récemment', labels)
        self.assertIn('Films — Sorties récentes', labels)
        self.assertIn('Films — Drame', labels)

    @patch('urllib.request.urlopen')
    def test_video_sections_includes_movies_and_shows(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'Directory': [
                    {'key': '1', 'title': 'Films', 'type': 'movie'},
                    {'key': '2', 'title': 'Séries', 'type': 'show'},
                    {'key': '3', 'title': 'Musique', 'type': 'artist'},
                ]
            }
        })
        sections = self.client.video_sections()
        self.assertEqual(len(sections), 2)

    @patch('urllib.request.urlopen')
    def test_section_items_uses_sort_param(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.section_items('1', sort='titleSort')
        self.assertIn('sort=titleSort', captured['url'])

    @patch('urllib.request.urlopen')
    def test_search_uses_query_param(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.search('1', 'inception')
        self.assertIn('search=inception', captured['url'])

    @patch('urllib.request.urlopen')
    def test_show_seasons_uses_children_endpoint(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': [
                {'title': 'Saison 1', 'type': 'season', 'ratingKey': '20', 'index': 1},
            ]}})

        mock_urlopen.side_effect = fake_urlopen
        seasons = self.client.show_seasons('10')
        self.assertIn('/library/metadata/10/children', captured['url'])
        self.assertEqual(seasons[0]['title'], 'Saison 1')
        self.assertEqual(seasons[0]['index'], 1)

    @patch('urllib.request.urlopen')
    def test_season_episodes_uses_children_endpoint(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': [
                {'title': 'Pilote', 'type': 'episode', 'ratingKey': '30',
                 'index': 1, 'parentRatingKey': '20'},
            ]}})

        mock_urlopen.side_effect = fake_urlopen
        episodes = self.client.season_episodes('20')
        self.assertIn('/library/metadata/20/children', captured['url'])
        self.assertEqual(episodes[0]['title'], 'Pilote')
        self.assertEqual(episodes[0]['parent_rating_key'], '20')

    def test_missing_config_raises(self):
        client = plex_client.PlexClient('', '')
        with self.assertRaises(plex_client.PlexAPIError):
            client.on_deck()


class TestPlexClientWithTotal(unittest.TestCase):
    """_with_total variants: same items as the originals, plus a real total
    count (plan a3f9c2e1) taken from totalSize (falling back to size)."""

    def setUp(self):
        self.client = plex_client.PlexClient(
            'http://192.168.100.133:32400', 'tok123')

    @patch('urllib.request.urlopen')
    def test_on_deck_with_total_uses_total_size(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'size': 20, 'totalSize': 200,
                'Metadata': [{'title': 'Inception', 'type': 'movie', 'ratingKey': '1'}],
            }
        })
        items, total = self.client.on_deck_with_total(limit=20, offset=0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Inception')
        self.assertEqual(total, 200)

    @patch('urllib.request.urlopen')
    def test_recently_added_with_total_falls_back_to_size(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'size': 7,
                'Metadata': [{'title': 'New Show', 'type': 'show', 'ratingKey': '2'}],
            }
        })
        items, total = self.client.recently_added_with_total()
        self.assertEqual(len(items), 1)
        self.assertEqual(total, 7)

    @patch('urllib.request.urlopen')
    def test_section_items_with_total(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'size': 30, 'totalSize': 437,
                'Metadata': [{'title': 'Movie A', 'type': 'movie', 'ratingKey': '3'}],
            }
        })
        items, total = self.client.section_items_with_total('7', sort='addedAt:desc', limit=30)
        self.assertEqual(items[0]['title'], 'Movie A')
        self.assertEqual(total, 437)

    @patch('urllib.request.urlopen')
    def test_section_items_with_total_genre_param(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.section_items_with_total('7', genre='Action')
        self.assertIn('genre=Action', captured['url'])

    @patch('urllib.request.urlopen')
    def test_section_items_with_total_unwatched_true(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.section_items_with_total('7', unwatched=True)
        self.assertIn('unwatched=1', captured['url'])

    @patch('urllib.request.urlopen')
    def test_section_items_with_total_unwatched_false(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.section_items_with_total('7', unwatched=False)
        self.assertIn('unwatched=0', captured['url'])

    @patch('urllib.request.urlopen')
    def test_section_items_with_total_no_genre_or_unwatched_unchanged(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            return MockHTTPResponse({'MediaContainer': {'Metadata': []}})

        mock_urlopen.side_effect = fake_urlopen
        self.client.section_items_with_total('7')
        self.assertNotIn('genre=', captured['url'])
        self.assertNotIn('unwatched=', captured['url'])

    @patch('urllib.request.urlopen')
    def test_by_genre_with_total(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'size': 6, 'totalSize': 42,
                'Metadata': [{'title': 'Action Movie', 'type': 'movie', 'ratingKey': '4'}],
            }
        })
        items, total = self.client.by_genre_with_total('7', 'Action', limit=10)
        self.assertEqual(items[0]['title'], 'Action Movie')
        self.assertEqual(total, 42)

    @patch('urllib.request.urlopen')
    def test_search_with_total(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {
                'size': 1, 'totalSize': 1,
                'Metadata': [{'title': 'Dragon Movie', 'type': 'movie', 'ratingKey': '5'}],
            }
        })
        items, total = self.client.search_with_total('7', 'dragon')
        self.assertEqual(items[0]['title'], 'Dragon Movie')
        self.assertEqual(total, 1)

    @patch('urllib.request.urlopen')
    def test_with_total_returns_none_when_no_size_field(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {'Metadata': [{'title': 'No Size', 'type': 'movie', 'ratingKey': '6'}]}
        })
        items, total = self.client.section_items_with_total('7')
        self.assertEqual(items[0]['title'], 'No Size')
        self.assertIsNone(total)


class TestPlexClientPeople(unittest.TestCase):
    def setUp(self):
        self.client = plex_client.PlexClient(
            'http://192.168.100.133:32400', 'tok123')
        plex_client._people_cache.clear()

    def tearDown(self):
        plex_client._people_cache.clear()

    _SECTIONS = {
        'MediaContainer': {
            'Directory': [
                {'key': '1', 'title': 'Films', 'type': 'movie'},
                {'key': '6', 'title': 'Musique', 'type': 'artist'},
                {'key': '2', 'title': 'Séries', 'type': 'show'},
            ]
        }
    }
    _ACTORS = {
        'MediaContainer': {
            'Directory': [
                {'key': '11550', 'title': 'Omar Sy',
                 'thumb': 'https://metadata-static.plex.tv/x/p.jpg'},
                {'key': '999', 'title': 'Nathan Fillion',
                 'thumb': '/:/resources/actor-icon.png'},
            ]
        }
    }

    @patch('urllib.request.urlopen')
    def test_people_directory_normalizes_and_caches(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse(self._ACTORS)
        people = self.client.people_directory('2')
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0]['id'], '11550')
        self.assertEqual(people[0]['name'], 'Omar Sy')
        self.assertEqual(people[0]['thumb_url'],
                         'https://metadata-static.plex.tv/x/p.jpg')
        # Server-relative thumbs get the base URL + token
        self.assertTrue(people[1]['thumb_url'].startswith(
            'http://192.168.100.133:32400/:/resources/actor-icon.png'))
        # Second call served from cache: still one HTTP request
        self.client.people_directory('2')
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch('urllib.request.urlopen')
    def test_search_people_filters_and_builds_filter(self, mock_urlopen):
        def fake_urlopen(req, *args, **kwargs):
            url = req.full_url
            if url.endswith('/library/sections'):
                return MockHTTPResponse(self._SECTIONS)
            return MockHTTPResponse(self._ACTORS)
        mock_urlopen.side_effect = fake_urlopen
        results = self.client.search_people('nathan')
        self.assertEqual(len(results), 1)  # same id deduped across sections
        p = results[0]
        self.assertEqual(p['name'], 'Nathan Fillion')
        self.assertEqual(p['person_filter'], 'actor=999')
        self.assertEqual(p['role'], 'Acteur')
        self.assertTrue(p['_person'])

    @patch('urllib.request.urlopen')
    def test_search_people_short_query(self, mock_urlopen):
        self.assertEqual(self.client.search_people('a'), [])
        self.assertEqual(mock_urlopen.call_count, 0)


class TestPlexErrorClassification(unittest.TestCase):
    """Transport failures must be distinguishable from API-level errors so
    the UI can show Plex's "server unreachable" state (B17)."""

    def setUp(self):
        self.client = plex_client.PlexClient(
            'http://192.168.100.133:32400', 'tok123')

    @patch('urllib.request.urlopen')
    def test_transport_error_raises_offline_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError('connection refused')
        with self.assertRaises(plex_client.PlexOfflineError):
            self.client.on_deck(limit=1)
        # Still a PlexAPIError subclass: existing handlers keep working.
        with self.assertRaises(plex_client.PlexAPIError):
            self.client.on_deck(limit=1)

    @patch('urllib.request.urlopen')
    def test_offline_backoff_raises_offline_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError('no route to host')
        with self.assertRaises(plex_client.PlexOfflineError):
            self.client.on_deck(limit=1)
        # Second call fast-fails on the breaker -- still an OfflineError,
        # and no new HTTP attempt was made.
        mock_urlopen.side_effect = None
        mock_urlopen.reset_mock()
        with self.assertRaises(plex_client.PlexOfflineError):
            self.client.on_deck(limit=1)
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    def test_http_error_is_not_offline(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            'http://x', 500, 'Server Error', {}, io.BytesIO(b'boom'))
        with self.assertRaises(plex_client.PlexAPIError) as ctx:
            self.client.on_deck(limit=1)
        self.assertNotIsInstance(ctx.exception, plex_client.PlexOfflineError)


class TestPlexClientTimeline(unittest.TestCase):
    """B3: /:/timeline progress reports."""

    def setUp(self):
        self.client = plex_client.PlexClient(
            'http://192.168.100.133:32400', 'tok123')

    @patch('urllib.request.urlopen')
    def test_report_timeline_params(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({})
        self.client.report_timeline('42', 61000, 2520000, 'playing')
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('/:/timeline', url)
        for expected in ('ratingKey=42',
                         'key=%2Flibrary%2Fmetadata%2F42',
                         'state=playing', 'time=61000',
                         'duration=2520000'):
            self.assertIn(expected, url)

    @patch('urllib.request.urlopen')
    def test_report_timeline_stopped_state(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({})
        self.client.report_timeline('42', 2400000, 2520000, 'stopped')
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('state=stopped', url)

    @patch('urllib.request.urlopen')
    def test_section_filters_lists_directory(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {'Directory': [
                {'filter': 'genre', 'title': 'Genre', 'filterType': 'tag'},
                {'filter': 'year', 'title': 'Année', 'filterType': 'integer'},
                {'title': 'Sans clé'},  # no 'filter' attr -> skipped
            ]}})
        filters = self.client.section_filters('1')
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('/library/sections/1/filters', url)
        self.assertEqual(filters, [
            {'key': 'genre', 'title': 'Genre', 'type': 'tag'},
            {'key': 'year', 'title': 'Année', 'type': 'integer'}])

    @patch('urllib.request.urlopen')
    def test_filter_values_lists_directory(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {'Directory': [
                {'key': 1999, 'title': '1999'},
                {'key': '2020', 'title': '2020'}]}})
        values = self.client.filter_values('1', 'year')
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('/library/sections/1/year', url)
        self.assertEqual(values, [
            {'key': '1999', 'title': '1999'},
            {'key': '2020', 'title': '2020'}])

    @patch('urllib.request.urlopen')
    def test_section_items_merges_dynamic_filters(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse(
            {'MediaContainer': {'Metadata': [], 'totalSize': 0}})
        self.client.section_items_with_total(
            '1', filters={'year': '1999', 'studio': '42'})
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('year=1999', url)
        self.assertIn('studio=42', url)

    @patch('urllib.request.urlopen')
    def test_related_items_flattens_and_dedupes_hubs(self, mock_urlopen):
        def video(rk, title):
            return {'ratingKey': rk, 'title': title, 'type': 'movie'}
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {'Hub': [
                {'title': 'Similar', 'Metadata': [video('1', 'A'),
                                                  video('2', 'B')]},
                {'title': 'Same genre', 'Metadata': [video('2', 'B'),
                                                     video('3', 'C')]},
            ]}})
        items = self.client.related_items('42')
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('/library/metadata/42/related', url)
        self.assertEqual([i['rating_key'] for i in items], ['1', '2', '3'])

    @patch('urllib.request.urlopen')
    def test_item_markers_normalises_windows(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'MediaContainer': {'Metadata': [{'Marker': [
                {'type': 'intro', 'startTimeOffset': 5000,
                 'endTimeOffset': 90000},
                {'type': 'credits', 'startTimeOffset': 2400000,
                 'endTimeOffset': 2520000}]}]}})
        markers = self.client.item_markers('42')
        url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('includeMarkers=1', url)
        self.assertEqual(markers, [
            {'type': 'intro', 'start_ms': 5000, 'end_ms': 90000},
            {'type': 'credits', 'start_ms': 2400000,
             'end_ms': 2520000}])

    @patch('urllib.request.urlopen')
    def test_item_markers_empty_when_absent(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse(
            {'MediaContainer': {'Metadata': [{'title': 'x'}]}})
        self.assertEqual(self.client.item_markers('42'), [])

    @patch('urllib.request.urlopen')
    def test_report_timeline_never_cached(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({})
        self.client.report_timeline('42', 1000, 2000)
        self.client.report_timeline('42', 2000, 2000)
        self.assertEqual(mock_urlopen.call_count, 2)


if __name__ == '__main__':
    unittest.main()
