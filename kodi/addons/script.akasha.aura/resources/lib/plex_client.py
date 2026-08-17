"""Akasha Aura — pure Plex Media Server API client.

No dependency on xbmc* so this module can be unit tested with plain
`python3 -m unittest`, and safely delegated to Talos (see
docs/talos-strategy.md).

It mirrors the endpoints consumed by the official Plex/Fire TV clients:
- /library/onDeck
- /library/recentlyAdded
- /library/sections/{key}/all (sorted by release date or filtered by genre)
- /library/sections/{key}/genre
"""

import json
import urllib.error
import urllib.parse
import urllib.request


class PlexAPIError(Exception):
    """Raised when a Plex API call fails or returns an unexpected shape."""


class PlexClient:
    """Minimal JSON client for a local Plex Media Server."""

    def __init__(self, server_url, token, timeout=10):
        self.server_url = (server_url or '').strip().rstrip('/')
        self.token = (token or '').strip()
        self.timeout = timeout

    def _url(self, path, params=None):
        url = self.server_url + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        return url

    def _headers(self):
        return {
            'X-Plex-Token': self.token,
            'Accept': 'application/json',
        }

    def _request(self, path, params=None):
        if not self.server_url or not self.token:
            raise PlexAPIError('Plex server URL and token are required')
        url = self._url(path, params)
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:500]
            raise PlexAPIError('Plex API {} for {}: {}'.format(e.code, path, body)) from e
        except urllib.error.URLError as e:
            raise PlexAPIError('Plex URL error for {}: {}'.format(path, e.reason)) from e
        except json.JSONDecodeError as e:
            raise PlexAPIError('Plex JSON decode error for {}: {}'.format(path, e)) from e

    @staticmethod
    def _media_container(data):
        if not isinstance(data, dict):
            raise PlexAPIError('Plex response is not a JSON object')
        return data.get('MediaContainer', data)

    @staticmethod
    def _video_dict(item, server_url, token):
        thumb = item.get('thumb') or ''
        art = item.get('art') or ''

        def image_url(path):
            if not path:
                return ''
            return '{}?X-Plex-Token={}'.format(server_url + path, token)

        return {
            'title': item.get('title') or 'Sans titre',
            'type': item.get('type') or 'video',
            'rating_key': item.get('ratingKey'),
            'year': item.get('year'),
            'originally_available_at': item.get('originallyAvailableAt'),
            'summary': item.get('summary') or '',
            'thumb_url': image_url(thumb),
            'art_url': image_url(art),
        }

    def _metadata_list(self, data):
        mc = self._media_container(data)
        return [self._video_dict(item, self.server_url, self.token)
                for item in mc.get('Metadata', [])]

    def on_deck(self, limit=20):
        data = self._request('/library/onDeck', {
            'X-Plex-Container-Size': limit,
        })
        return self._metadata_list(data)

    def recently_added(self, limit=20):
        data = self._request('/library/recentlyAdded', {
            'X-Plex-Container-Size': limit,
        })
        return self._metadata_list(data)

    def movie_sections(self):
        data = self._request('/library/sections')
        mc = self._media_container(data)
        return [
            {
                'key': str(item.get('key')),
                'title': item.get('title') or 'Section',
                'type': item.get('type'),
            }
            for item in mc.get('Directory', [])
            if item.get('type') == 'movie'
        ]

    def recently_released(self, section_key, limit=20):
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'sort': 'originallyAvailableAt:desc',
            'X-Plex-Container-Size': limit,
        })
        return self._metadata_list(data)

    def section_genres(self, section_key):
        data = self._request('/library/sections/{}/genre'.format(section_key))
        mc = self._media_container(data)
        return [
            str(item.get('tag'))
            for item in mc.get('Directory', [])
            if item.get('tag')
        ]

    def by_genre(self, section_key, genre, limit=10):
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'genre': genre,
            'X-Plex-Container-Size': limit,
        })
        return self._metadata_list(data)

    def video_sections(self):
        """Return all library sections that contain video content."""
        data = self._request('/library/sections')
        mc = self._media_container(data)
        return [
            {
                'key': str(item.get('key')),
                'title': item.get('title') or 'Section',
                'type': item.get('type'),
            }
            for item in mc.get('Directory', [])
            if item.get('type') in ('movie', 'show')
        ]

    def section_items(self, section_key, sort='titleSort', limit=200):
        """Return all items of a section, sorted.

        sort examples: titleSort, titleSort:desc, originallyAvailableAt:desc,
        addedAt:desc, rating:desc.
        """
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'sort': sort,
            'X-Plex-Container-Size': limit,
        })
        return self._metadata_list(data)

    def search(self, section_key, query, limit=50):
        """Search items in a section by title (client-side filter)."""
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'search': query,
            'X-Plex-Container-Size': limit,
        })
        return self._metadata_list(data)

    def entertainment_rows(self, limits=None):
        """Build the default Divertissement rows for the UI.

        Returns a list of dicts: {'label': str, 'items': [video_dict, ...]}
        """
        if limits is None:
            limits = {
                'on_deck': 10,
                'recently_added': 10,
                'recently_released': 10,
                'per_genre': 6,
                'genres_per_section': 4,
            }

        rows = [
            {'label': 'Continuer a regarder', 'items': self.on_deck(limits['on_deck'])},
            {'label': 'Ajoutes recemment', 'items': self.recently_added(limits['recently_added'])},
        ]

        for section in self.movie_sections():
            rr = self.recently_released(section['key'], limits['recently_released'])
            if rr:
                rows.append({
                    'label': '{} — Sortis recemment'.format(section['title']),
                    'items': rr,
                })

            genres = self.section_genres(section['key'])
            for genre in genres[:limits['genres_per_section']]:
                items = self.by_genre(section['key'], genre, limits['per_genre'])
                if items:
                    rows.append({
                        'label': '{} — {}'.format(section['title'], genre),
                        'items': items,
                    })

        return rows
