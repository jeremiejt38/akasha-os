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

import divert_source


class PlexAPIError(Exception):
    """Raised when a Plex API call fails or returns an unexpected shape."""


class PlexClient:
    """Minimal JSON client for a local Plex Media Server."""

    def __init__(self, server_url, token, timeout=10):
        self.server_url = (server_url or '').strip().rstrip('/')
        self.token = (token or '').strip()
        self.timeout = timeout

    def _url(self, path, params=None):
        # Absolute URLs (cloud provider endpoints like
        # discover.provider.plex.tv) are used as-is; relative paths are
        # resolved against the local server.
        url = path if path.startswith('http') else self.server_url + path
        if params:
            # Hub `key`/`hubKey` values come back with their own query string
            # (e.g. '/library/sections/1/all?sort=addedAt:desc'), so pagination
            # params must be appended with '&' rather than a second '?'.
            url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
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
                body = resp.read().decode('utf-8')
                # Action endpoints (scrobble/unscrobble/rate) answer 200
                # with an empty body -- a bare decode would JSON-decode
                # crash and the caller would treat it as a failure.
                if not body.strip():
                    return {}
                return json.loads(body)
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
        def image_url(path):
            if not path:
                return ''
            # Cloud provider metadata (Discover/Trending hubs) carries
            # absolute image URLs -- just attach the token to them.
            if path.startswith('http'):
                sep = '&' if '?' in path else '?'
                if 'X-Plex-Token' not in path:
                    path += sep + 'X-Plex-Token=' + token
                return path
            return '{}?X-Plex-Token={}'.format(server_url + path, token)

        # Shared normaliser keeps connector and direct-Plex payloads identical
        # (see divert_source.build_video_item).
        return divert_source.build_video_item(item, image_url)

    def _metadata_list(self, data):
        mc = self._media_container(data)
        return [self._video_dict(item, self.server_url, self.token)
                for item in mc.get('Metadata', [])]

    def _metadata_list_with_total(self, data):
        """Like `_metadata_list`, but also returns the real total item count.

        Plex includes this in every MediaContainer response (`totalSize`,
        falling back to `size` for non-paginated responses) at no extra
        request cost -- see plan a3f9c2e1 in docs/aura/decisions.md: the UI
        should show the real total immediately, not just how many items are
        loaded so far.
        """
        mc = self._media_container(data)
        items = [self._video_dict(item, self.server_url, self.token)
                 for item in mc.get('Metadata', [])]
        total = mc.get('totalSize', mc.get('size'))
        return items, total

    def home_hubs(self, hub_count=24, per_hub=16):
        """The promoted "For You" hubs Plex TV renders as the home rows.

        `/hubs/promoted` returns the same curated list (Continue Watching,
        On Deck, Recently Added/Released, genre/director spotlights...) the
        official client shows, each hub already carrying its first `per_hub`
        items inline so the initial paint needs a single request.
        """
        data = self._request('/hubs/promoted', {
            'count': per_hub,
            'X-Plex-Container-Size': hub_count,
        })
        return self._hub_list(data)

    DISCOVER_BASE = 'https://discover.provider.plex.tv'

    def discover_hubs(self, hub_count=24, per_hub=16):
        """The promoted Discover hubs Plex TV renders under the home
        "Trending" tab (trailers, watchlisted, services...) -- served by
        Plex's cloud metadata provider rather than the local server."""
        data = self._request(self.DISCOVER_BASE + '/hubs/promoted', {
            'count': per_hub,
            'X-Plex-Container-Size': hub_count,
        })
        hubs = self._hub_list(data)
        for hub in hubs:
            # Provider hubs carry relative `key` paths and no inline items:
            # resolve the continuation endpoint against the provider base.
            if hub['key'] and not hub['key'].startswith('http'):
                hub['key'] = self.DISCOVER_BASE + hub['key']
        return hubs

    def section_hubs(self, section_key, hub_count=24, per_hub=16):
        """The per-library hubs Plex shows on a library's Recommended tab."""
        data = self._request('/hubs/sections/{}'.format(section_key), {
            'count': per_hub,
            'X-Plex-Container-Size': hub_count,
        })
        return self._hub_list(data)

    def _hub_list(self, data):
        mc = self._media_container(data)
        hubs = []
        for hub in mc.get('Hub', []):
            hubs.append({
                'title': hub.get('title') or hub.get('title2') or '',
                'key': hub.get('key') or hub.get('hubKey') or '',
                'identifier': hub.get('hubIdentifier') or '',
                'context': hub.get('context') or '',
                'type': hub.get('type') or '',
                'style': hub.get('style') or '',
                'more': bool(hub.get('more')),
                'items': [self._video_dict(item, self.server_url, self.token)
                          for item in hub.get('Metadata', [])],
            })
        return hubs

    def hub_items_with_total(self, key, limit=20, offset=0):
        """Paginate a hub's own `key`/`hubKey` path (its "more" endpoint)."""
        data = self._request(key, {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list_with_total(data)

    def on_deck(self, limit=20, offset=0):
        data = self._request('/library/onDeck', {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list(data)

    def recently_added(self, limit=20, offset=0):
        data = self._request('/library/recentlyAdded', {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list(data)

    def on_deck_with_total(self, limit=20, offset=0):
        data = self._request('/library/onDeck', {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list_with_total(data)

    def recently_added_with_total(self, limit=20, offset=0):
        data = self._request('/library/recentlyAdded', {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list_with_total(data)

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
        """Return genre names for a section.

        Plex's `/library/sections/{key}/genre` returns each genre as a
        `Directory` entry with a `title` field (not `tag`, used for
        per-item genre tags on movies/shows -- a different response shape),
        confirmed against a real server on 2026-08-18.
        """
        data = self._request('/library/sections/{}/genre'.format(section_key))
        mc = self._media_container(data)
        return [
            str(item.get('title'))
            for item in mc.get('Directory', [])
            if item.get('title')
        ]

    def by_genre(self, section_key, genre, limit=10, offset=0):
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'genre': genre,
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list(data)

    def by_genre_with_total(self, section_key, genre, limit=10, offset=0):
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'genre': genre,
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list_with_total(data)

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

    def section_items(self, section_key, sort='titleSort', limit=200, offset=0):
        """Return all items of a section, sorted.

        sort examples: titleSort, titleSort:desc, originallyAvailableAt:desc,
        addedAt:desc, rating:desc.
        """
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'sort': sort,
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list(data)

    def section_items_with_total(self, section_key, sort='titleSort', limit=200, offset=0,
                                  genre=None, unwatched=None):
        params = {
            'sort': sort,
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        }
        if genre:
            params['genre'] = genre
        if unwatched is True:
            params['unwatched'] = 1
        elif unwatched is False:
            params['unwatched'] = 0
        data = self._request('/library/sections/{}/all'.format(section_key), params)
        return self._metadata_list_with_total(data)

    def search(self, section_key, query, limit=50, offset=0):
        """Search items in a section by title (client-side filter)."""
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'search': query,
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list(data)

    def search_with_total(self, section_key, query, limit=50, offset=0):
        data = self._request('/library/sections/{}/all'.format(section_key), {
            'search': query,
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list_with_total(data)

    def section_collections_with_total(self, section_key, limit=200, offset=0):
        """JSON payloads list collections under `Metadata` (only XML uses
        `Directory`); same normaliser applies (thumb -> poster, childCount)."""
        data = self._request('/library/sections/{}/collections'.format(section_key), {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        mc = self._media_container(data)
        items = [self._video_dict(d, self.server_url, self.token)
                 for d in mc.get('Metadata', mc.get('Directory', []))]
        total = mc.get('totalSize', mc.get('size'))
        return items, total

    def collection_items_with_total(self, collection_key, limit=200, offset=0):
        data = self._request('/library/collections/{}/children'.format(collection_key), {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        })
        return self._metadata_list_with_total(data)

    def scrobble(self, rating_key):
        """Mark an item watched (Plex `scrobble` endpoint)."""
        self._request('/:/scrobble', {
            'key': rating_key,
            'identifier': 'com.plexapp.plugins.library',
        })

    def unscrobble(self, rating_key):
        """Mark an item unwatched."""
        self._request('/:/unscrobble', {
            'key': rating_key,
            'identifier': 'com.plexapp.plugins.library',
        })

    def rate(self, rating_key, rating):
        """Set a user rating (1-10) via Plex's `/:/rate` endpoint."""
        url = self._url('/:/rate', {
            'key': rating_key,
            'identifier': 'com.plexapp.plugins.library',
            'rating': int(rating),
        })
        req = urllib.request.Request(url, headers=self._headers(), method='PUT')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp.read()
        except urllib.error.URLError as e:
            raise PlexAPIError('Plex rate failed for {}: {}'.format(
                rating_key, getattr(e, 'reason', e))) from e

    def metadata_item(self, rating_key):
        """Fetch and normalise a single item by rating key (used to hydrate
        thin items before opening the detail page)."""
        data = self._request('/library/metadata/{}'.format(rating_key))
        items = self._metadata_list(data)
        return items[0] if items else None

    def show_seasons(self, show_rating_key):
        """Return the seasons of a TV show, ordered by Plex's default index."""
        data = self._request('/library/metadata/{}/children'.format(show_rating_key))
        return self._metadata_list(data)

    def season_episodes(self, season_rating_key):
        """Return the episodes of a season, ordered by Plex's default index."""
        data = self._request('/library/metadata/{}/children'.format(season_rating_key))
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
            {'label': 'Continuer à regarder', 'items': self.on_deck(limits['on_deck'])},
            {'label': 'Ajoutés récemment', 'items': self.recently_added(limits['recently_added'])},
        ]

        for section in self.movie_sections():
            rr = self.recently_released(section['key'], limits['recently_released'])
            if rr:
                rows.append({
                    'label': '{} — Sorties récentes'.format(section['title']),
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
