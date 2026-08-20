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
    def test_request_sets_explicit_user_agent(self, mock_urlopen):
        # Cloudflare (fronting connector.akasha.ing) blocks the default
        # Python-urllib User-Agent as a bot signature (HTTP 403) -- regression
        # test for the explicit override.
        mock_urlopen.return_value = MockHTTPResponse({'token': 'abc123'})

        self.client.login('user', 'pass')

        sent_request = mock_urlopen.call_args[0][0]
        self.assertNotIn('python-urllib', sent_request.get_header('User-agent').lower())

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
        self.assertIn('sort=addedAt%3Adesc', sent_request.full_url)
        self.assertIn('limit=50', sent_request.full_url)

    @patch('urllib.request.urlopen')
    def test_section_items_with_genre(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {'Metadata': []}})
        self.client.token = 'abc123'

        self.client.section_items('1', genre='Action')
        self.assertIn('genre=Action', mock_urlopen.call_args[0][0].full_url)

    @patch('urllib.request.urlopen')
    def test_section_items_with_search(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {'Metadata': []}})
        self.client.token = 'abc123'

        self.client.section_items('1', search='dragon')
        self.assertIn('search=dragon', mock_urlopen.call_args[0][0].full_url)

    @patch('urllib.request.urlopen')
    def test_section_items_with_unwatched_true(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {'Metadata': []}})
        self.client.token = 'abc123'

        self.client.section_items('1', unwatched=True)
        self.assertIn('unwatched=1', mock_urlopen.call_args[0][0].full_url)

    @patch('urllib.request.urlopen')
    def test_section_items_with_unwatched_false(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {'Metadata': []}})
        self.client.token = 'abc123'

        self.client.section_items('1', unwatched=False)
        self.assertIn('unwatched=0', mock_urlopen.call_args[0][0].full_url)

    @patch('urllib.request.urlopen')
    def test_section_items_with_unwatched_none_omitted(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse({'MediaContainer': {'Metadata': []}})
        self.client.token = 'abc123'

        self.client.section_items('1')
        self.assertNotIn('unwatched=', mock_urlopen.call_args[0][0].full_url)

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

    def test_image_url_includes_encoded_path_and_auth_header(self):
        self.client.token = 'abc123'

        url = self.client.image_url('/library/metadata/98481/thumb/1784765860')

        self.assertIn('/api/plex/image?path=', url)
        self.assertIn('thumb%2F1784765860', url)
        self.assertIn('|Authorization=Bearer%20abc123', url)

    def test_image_url_without_token_omits_auth_header(self):
        url = self.client.image_url('/library/metadata/1/thumb/1')

        self.assertNotIn('Authorization', url)

    def test_image_url_empty_path_returns_empty_string(self):
        self.client.token = 'abc123'

        self.assertEqual(self.client.image_url(''), '')


if __name__ == '__main__':
    unittest.main()
