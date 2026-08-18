"""Unit tests for sunshine_client.py — no xbmc dependency."""

import io
import json
import unittest
from unittest.mock import patch

import sunshine_client


class MockHTTPResponse:
    def __init__(self, payload):
        self._body = io.BytesIO(json.dumps(payload).encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body.read()


class TestSunshineClient(unittest.TestCase):
    def setUp(self):
        self.client = sunshine_client.SunshineClient(
            'https://10.20.0.4:47990', 'akasha', 'secret')

    def test_is_configured(self):
        self.assertTrue(self.client.is_configured())
        self.assertFalse(sunshine_client.SunshineClient('', '', '').is_configured())
        self.assertFalse(sunshine_client.SunshineClient('https://x', 'u', '').is_configured())

    def test_missing_config_raises(self):
        client = sunshine_client.SunshineClient('', '', '')
        with self.assertRaises(sunshine_client.SunshineAPIError):
            client.apps()

    @patch('urllib.request.urlopen')
    def test_apps_parses_response(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({
            'apps': [
                {'name': 'Desktop', 'image-path': 'desktop.png'},
                {'name': 'My Game', 'cmd': 'game.exe',
                 'image-path': 'https://example.com/cover.jpg'},
            ],
            'env': {},
        })
        apps = self.client.apps()
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0]['index'], 0)
        self.assertEqual(apps[0]['box_art_url'], '')
        self.assertEqual(apps[1]['box_art_url'], 'https://example.com/cover.jpg')

    @patch('urllib.request.urlopen')
    def test_sends_basic_auth_header(self, mock_urlopen):
        captured = {}

        def fake_urlopen(req, *args, **kwargs):
            captured['auth'] = req.get_header('Authorization')
            return MockHTTPResponse({'apps': []})

        mock_urlopen.side_effect = fake_urlopen
        self.client.apps()
        self.assertTrue(captured['auth'].startswith('Basic '))


if __name__ == '__main__':
    unittest.main()
