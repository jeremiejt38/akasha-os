"""Unit tests for connector_client.py — no xbmc dependency."""

import io
import json
import urllib.error
import unittest
from unittest.mock import patch

import connector_client


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


class TestConnectorClient(unittest.TestCase):
    def setUp(self):
        self.client = connector_client.ConnectorClient('http://connector.local:8300')

    @patch('urllib.request.urlopen')
    def test_login_stores_token(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'token': 'abc123', 'expires_at': '2026-01-01'})

        self.client.login('user', 'pass')

        self.assertTrue(self.client.is_authenticated())
        self.assertEqual(self.client.token, 'abc123')

    @patch('urllib.request.urlopen')
    def test_on_deck_without_auth_raises(self, mock_urlopen):
        with self.assertRaises(connector_client.ConnectorAPIError):
            self.client.on_deck()
        mock_urlopen.assert_not_called()

    @patch('urllib.request.urlopen')
    def test_http_error_raises_connector_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            'http://connector.local:8300/api/auth/login', 401, 'Unauthorized',
            hdrs=None, fp=io.BytesIO(b'{"detail":"Unauthorized"}'))

        with self.assertRaises(connector_client.ConnectorAPIError):
            self.client.login('user', 'wrong')

    @patch('urllib.request.urlopen')
    def test_sections_sends_bearer_token(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse(
            {'MediaContainer': {'Directory': [{'title': 'Films'}]}})
        self.client.token = 'abc123'

        result = self.client.sections()

        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.get_header('Authorization'), 'Bearer abc123')
        self.assertEqual(
            result['MediaContainer']['Directory'][0]['title'], 'Films')

    @patch('urllib.request.urlopen')
    def test_section_items_builds_query_string(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {'Metadata': []}})
        self.client.token = 'abc123'

        self.client.section_items('1', sort='addedAt:desc', limit=50)

        sent_request = mock_urlopen.call_args[0][0]
        self.assertIn('/api/plex/sections/1/all', sent_request.full_url)
        self.assertIn('sort=addedAt:desc', sent_request.full_url)
        self.assertIn('limit=50', sent_request.full_url)

    @patch('urllib.request.urlopen')
    def test_section_genres(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {}})
        self.client.token = 'abc123'

        self.client.section_genres('1')
        self.assertIn('/api/plex/sections/1/genres', mock_urlopen.call_args[0][0].full_url)

    @patch('urllib.request.urlopen')
    def test_metadata_children(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {}})
        self.client.token = 'abc123'

        self.client.metadata_children('42')
        self.assertIn('/api/plex/metadata/42/children', mock_urlopen.call_args[0][0].full_url)


if __name__ == '__main__':
    unittest.main()
