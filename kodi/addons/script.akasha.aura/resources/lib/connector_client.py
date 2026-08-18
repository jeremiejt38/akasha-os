"""Akasha Aura — pure client for the akasha-os-connector API.

No dependency on xbmc* so this module can be unit tested with plain
`python3 -m unittest`, and safely delegated to Talos (see
docs/talos-strategy.md). Mirrors the style of plex_client.py.
"""

import json
import urllib.error
import urllib.request


class ConnectorAPIError(Exception):
    """Raised when a connector API call fails or returns an unexpected shape."""


class ConnectorClient:
    """Minimal JSON client for the akasha-os-connector service."""

    def __init__(self, server_url, timeout=10):
        self.server_url = (server_url or '').strip().rstrip('/')
        self.timeout = timeout
        self.token = None

    def _request(self, method, path, json_body=None, auth=True):
        if auth and self.token is None:
            raise ConnectorAPIError('Not authenticated')

        headers = {'Accept': 'application/json'}
        if auth:
            headers['Authorization'] = 'Bearer {}'.format(self.token)

        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        url = self.server_url + path
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:500]
            raise ConnectorAPIError('Connector API {} for {}: {}'.format(e.code, path, body)) from e
        except urllib.error.URLError as e:
            raise ConnectorAPIError('Connector URL error for {}: {}'.format(path, e.reason)) from e
        except json.JSONDecodeError as e:
            raise ConnectorAPIError('Connector JSON decode error for {}: {}'.format(path, e)) from e

    def login(self, username, password):
        """Authenticate against the connector and store the session token."""
        response = self._request(
            'POST', '/api/auth/login',
            json_body={'username': username, 'password': password},
            auth=False,
        )
        token = response.get('token') if isinstance(response, dict) else None
        if not token:
            raise ConnectorAPIError('Login response missing token')
        self.token = token

    def is_authenticated(self):
        return self.token is not None

    def on_deck(self, limit=20):
        return self._request('GET', '/api/plex/on-deck')

    def recently_added(self, limit=20):
        return self._request('GET', '/api/plex/recently-added')

    def sections(self):
        return self._request('GET', '/api/plex/sections')
