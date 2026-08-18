"""Unit tests for steam_client.py — no xbmc dependency."""

import io
import json
import unittest
from unittest.mock import patch

import steam_client


class MockHTTPResponse:
    def __init__(self, payload):
        self._body = io.BytesIO(json.dumps(payload).encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body.read()


class TestSteamClient(unittest.TestCase):
    def setUp(self):
        self.client = steam_client.SteamClient('APIKEY', '76561198000000000')

    def test_is_configured(self):
        self.assertTrue(self.client.is_configured())
        self.assertFalse(steam_client.SteamClient('', '').is_configured())
        self.assertFalse(steam_client.SteamClient('key', '').is_configured())

    def test_missing_config_raises(self):
        client = steam_client.SteamClient('', '')
        with self.assertRaises(steam_client.SteamAPIError):
            client.owned_games_sorted_by_recent()

    @patch('urllib.request.urlopen')
    def test_owned_games_sorted_by_recent_played_first(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'response': {
                'games': [
                    {'appid': 10, 'name': 'Old Game', 'rtime_last_played': 100, 'playtime_forever': 50},
                    {'appid': 20, 'name': 'Recent Game', 'rtime_last_played': 999, 'playtime_forever': 10},
                    {'appid': 30, 'name': 'Never Played', 'rtime_last_played': 0, 'playtime_forever': 0},
                ]
            }
        })
        games = self.client.owned_games_sorted_by_recent()
        self.assertEqual([g['name'] for g in games], ['Recent Game', 'Old Game', 'Never Played'])

    @patch('urllib.request.urlopen')
    def test_box_art_url_uses_appid(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'response': {'games': [{'appid': 815370, 'name': 'Green Hell', 'rtime_last_played': 1}]}
        })
        games = self.client.owned_games_sorted_by_recent()
        self.assertIn('815370', games[0]['box_art_url'])

    @patch('urllib.request.urlopen')
    def test_respects_limit(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'response': {'games': [
                {'appid': i, 'name': 'Game {}'.format(i), 'rtime_last_played': i}
                for i in range(10)
            ]}
        })
        games = self.client.owned_games_sorted_by_recent(limit=3)
        self.assertEqual(len(games), 3)

    @patch('urllib.request.urlopen')
    def test_games_without_appid_are_skipped(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'response': {'games': [{'name': 'No appid', 'rtime_last_played': 5}]}
        })
        games = self.client.owned_games_sorted_by_recent()
        self.assertEqual(games, [])


if __name__ == '__main__':
    unittest.main()
