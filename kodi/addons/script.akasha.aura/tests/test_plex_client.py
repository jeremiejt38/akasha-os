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
                    {'tag': 'Action'},
                    {'tag': 'Comédie'},
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
                {'tag': 'Drame'},
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
        self.assertIn('Continuer a regarder', labels)
        self.assertIn('Ajoutes recemment', labels)
        self.assertIn('Films — Sortis recemment', labels)
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

    def test_missing_config_raises(self):
        client = plex_client.PlexClient('', '')
        with self.assertRaises(plex_client.PlexAPIError):
            client.on_deck()


if __name__ == '__main__':
    unittest.main()
