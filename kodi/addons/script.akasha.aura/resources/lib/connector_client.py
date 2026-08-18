"""Akasha Aura — pure client for the akasha-os-connector API.

No dependency on xbmc* so this module can be unit tested with plain
`python3 -m unittest`, and safely delegated to Talos (see
docs/talos-strategy.md). Mirrors the style of plex_client.py.
"""

import json
import urllib.error
import urllib.parse
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

        # Cloudflare (which fronts connector.akasha.ing) blocks the default
        # Python-urllib User-Agent as a bot signature (HTTP 403, error 1010)
        # -- always send an explicit one, both here and in image_url()'s
        # Kodi texture request (see below).
        headers = {'Accept': 'application/json', 'User-Agent': 'AkashaOSAura/1.0'}
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

    def section_items(self, section_key, sort='titleSort', limit=200, genre=None, search=None):
        path = '/api/plex/sections/{}/all?sort={}&limit={}'.format(
            section_key, urllib.parse.quote(sort, safe=''), limit)
        if genre:
            path += '&genre={}'.format(urllib.parse.quote(genre, safe=''))
        if search:
            path += '&search={}'.format(urllib.parse.quote(search, safe=''))
        return self._request('GET', path)

    def section_genres(self, section_key):
        return self._request('GET', '/api/plex/sections/{}/genres'.format(section_key))

    def metadata_children(self, rating_key):
        return self._request('GET', '/api/plex/metadata/{}/children'.format(rating_key))

    def image_url(self, plex_path):
        """Build a Kodi-playable URL for a Plex image via the connector's proxy.

        The admin Plex token never reaches the client: the connector resolves
        it server-side (see docs/api.md of akasha-os-connector). The session
        token is attached as a custom HTTP header using Kodi's URL option
        syntax (`url|Header=Value`), which Kodi's texture downloader honours
        for `ListItem.setArt()` sources — see akasha-os-connector's decision
        to keep session tokens opaque/revocable rather than embedding them in
        the URL query string itself.
        """
        if not plex_path:
            return ''
        encoded_path = urllib.parse.quote(plex_path, safe='')
        base = '{}/api/plex/image?path={}'.format(self.server_url, encoded_path)
        if not self.token:
            return base
        header_value = urllib.parse.quote('Bearer {}'.format(self.token), safe='')
        return '{}|Authorization={}'.format(base, header_value)
