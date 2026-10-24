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
import time
import urllib.error
import urllib.parse
import urllib.request

import divert_source
import i18n

# A dead server used to burn the full socket timeout on EVERY fetch --
# Aura loads rows sequentially on the GUI thread, so the interface froze
# for tens of seconds (reported as "Aura rame / impossible d'en sortir").
# Circuit breaker: after one transport failure, calls fail fast for this
# window; plus a short read-through cache so re-entering a view does not
# re-hit the server seconds later (user-reported "pas de cache").
_OFFLINE_BACKOFF_SECONDS = 30.0
_CACHE_TTL_SECONDS = 30.0
_CACHE_MAX_ENTRIES = 64
_offline_until = {}
_read_cache = {}

# People directories (/library/sections/<k>/actor|director) hold thousands
# of entries that barely change; a longer-lived cache keeps people search
# instant after the first query (the 30s read cache would refetch per
# search session).
_PEOPLE_CACHE_TTL_SECONDS = 600.0
_people_cache = {}


def _mark_offline(host):
    _offline_until[host] = time.time() + _OFFLINE_BACKOFF_SECONDS


def _mark_online(host):
    _offline_until.pop(host, None)


def _is_offline(host):
    return time.time() < _offline_until.get(host, 0.0)


def _cache_put(key, data):
    if len(_read_cache) >= _CACHE_MAX_ENTRIES:
        now = time.time()
        for k in [k for k, v in _read_cache.items() if v[0] <= now]:
            del _read_cache[k]
        if len(_read_cache) >= _CACHE_MAX_ENTRIES:
            _read_cache.clear()
    _read_cache[key] = (time.time() + _CACHE_TTL_SECONDS, data)


class PlexAPIError(Exception):
    """Raised when a Plex API call fails or returns an unexpected shape."""


class PlexClient:
    """Minimal JSON client for a local Plex Media Server."""

    def __init__(self, server_url, token, timeout=5):
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
            # Cloudflare fronts the public plex.akasha.ing endpoint and
            # blocks Python-urllib's default UA (HTTP 403, error 1010).
            'User-Agent': 'AkashaOSAura/1.0',
        }

    def _request(self, path, params=None, method=None):
        if not self.server_url or not self.token:
            raise PlexAPIError('Plex server URL and token are required')
        url = self._url(path, params)
        host = urllib.parse.urlparse(url).netloc
        if _is_offline(host):
            raise PlexAPIError('Plex server {} unreachable '
                               '(offline backoff)'.format(host))
        # Mutation endpoints (/:/scrobble, /:/rate, /actions/...) must
        # never be served from cache.
        cacheable = not path.startswith('/:') and method is None
        key = (host, path, tuple(sorted((params or {}).items())))
        if cacheable:
            entry = _read_cache.get(key)
            if entry and time.time() < entry[0]:
                return entry[1]
        req = urllib.request.Request(url, headers=self._headers(),
                                     method=method or 'GET')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode('utf-8')
                _mark_online(host)
                # Action endpoints (scrobble/unscrobble/rate) answer 200
                # with an empty body -- a bare decode would JSON-decode
                # crash and the caller would treat it as a failure.
                data = json.loads(body) if body.strip() else {}
                if cacheable:
                    _cache_put(key, data)
                return data
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:500]
            raise PlexAPIError('Plex API {} for {}: {}'.format(e.code, path, body)) from e
        except OSError as e:
            _mark_offline(host)
            reason = getattr(e, 'reason', e)
            raise PlexAPIError('Plex URL error for {}: {}'.format(path, reason)) from e
        except json.JSONDecodeError as e:
            raise PlexAPIError('Plex JSON decode error for {}: {}'.format(path, e)) from e

    @staticmethod
    def _media_container(data):
        if not isinstance(data, dict):
            raise PlexAPIError('Plex response is not a JSON object')
        return data.get('MediaContainer', data)

    @staticmethod
    def _video_dict(item, server_url, token):
        def image_url(path, width=None, height=None):
            if not path:
                return ''
            # Cloud provider metadata (Discover/Trending hubs) carries
            # absolute image URLs -- just attach the token to them.
            if path.startswith('http'):
                sep = '&' if '?' in path else '?'
                if 'X-Plex-Token' not in path:
                    path += sep + 'X-Plex-Token=' + token
                return path
            # Sized requests go through Plex's own photo transcoder: a
            # 240px card used to pull the full 2000x3000 JPEG and make
            # the Pi4 decode it (visible scroll stutter). Server-side
            # downscale is what official Plex clients do anyway.
            if width and height:
                return ('{}/photo/:/transcode?url={}&width={}&height={}'
                        '&minSize=1&upscale=0&X-Plex-Token={}'.format(
                            server_url, urllib.parse.quote(path),
                            width, height, token))
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

    def items_by_filter_with_total(self, section_key, filter_str,
                                   limit=200, offset=0):
        """Section items matching a Plex tag filter ('actor=11550', ...)."""
        params = {
            'X-Plex-Container-Size': limit,
            'X-Plex-Container-Start': offset,
        }
        if filter_str and '=' in filter_str:
            key, value = filter_str.split('=', 1)
            params[key] = value
        data = self._request('/library/sections/{}/all'.format(section_key),
                             params)
        return self._metadata_list_with_total(data)

    def person_filmography(self, filter_str):
        """Items tagged with a person ('actor=ID', 'director=ID'...) across
        every video section -- the server-side filmography Plex renders on
        a person page, deduped and newest first."""
        seen = set()
        items = []
        for section in self.video_sections():
            try:
                page, _total = self.items_by_filter_with_total(
                    section['key'], filter_str)
            except PlexAPIError:
                continue
            for item in page:
                if item.get('rating_key') in seen:
                    continue
                seen.add(item.get('rating_key'))
                items.append(item)
        items.sort(key=lambda i: i.get('year') or 0, reverse=True)
        return items

    def people_directory(self, section_key, kind='actor'):
        """Every person tagged in a section ('actor' or 'director').

        The Plex hub search reports matching people counts but never the
        items themselves, so people search is done client-side over this
        directory -- cached for a few minutes since it is huge.
        """
        cache_key = (section_key, kind)
        entry = _people_cache.get(cache_key)
        if entry and time.time() < entry[0]:
            return entry[1]
        data = self._request(
            '/library/sections/{}/{}'.format(section_key, kind))
        mc = self._media_container(data)
        people = []
        for d in mc.get('Directory', []):
            name = d.get('title') or d.get('tag')
            person_id = d.get('key')
            if not name or not person_id:
                continue
            thumb = d.get('thumb') or ''
            if thumb and not thumb.startswith('http'):
                thumb = '{}{}?X-Plex-Token={}'.format(
                    self.server_url, thumb, self.token)
            people.append({'id': str(person_id), 'name': name,
                           'thumb_url': thumb, 'kind': kind})
        _people_cache[cache_key] = (
            time.time() + _PEOPLE_CACHE_TTL_SECONDS, people)
        return people

    def search_people(self, query, kinds=('actor',)):
        """Client-side people search over the per-section directories.

        Returns AuraSearch-ready dicts flagged '_person' with a
        'person_filter' ('actor=ID') usable by person_filmography."""
        q = (query or '').strip().lower()
        if len(q) < 2:
            return []
        seen = set()
        out = []
        for section in self.video_sections():
            for kind in kinds:
                try:
                    people = self.people_directory(section['key'], kind)
                except PlexAPIError:
                    continue
                for person in people:
                    if q not in person['name'].lower() \
                            or person['id'] in seen:
                        continue
                    seen.add(person['id'])
                    out.append({
                        'name': person['name'],
                        'thumb_url': person['thumb_url'],
                        'role': (i18n.tr(33154) if kind == 'director'
                                 else i18n.tr(33127)),
                        'person_filter': '{}={}'.format(kind, person['id']),
                        '_person': True,
                    })
        return out[:20]

    def item_extras(self, rating_key):
        """Bonus clips attached to an item (trailers, deleted scenes...).

        Each normalised item keeps its Plex `subtype` ('trailer', ...) so
        the UI can prefer the trailer when several extras exist."""
        data = self._request('/library/metadata/{}/extras'.format(rating_key))
        mc = self._media_container(data)
        items = []
        for raw in mc.get('Metadata', []):
            item = self._video_dict(raw, self.server_url, self.token)
            item['subtype'] = raw.get('subtype') or ''
            items.append(item)
        return items

    def scrobble(self, rating_key):
        """Mark an item watched (Plex `scrobble` endpoint)."""
        self._request('/:/scrobble', {
            'key': rating_key,
            'identifier': 'com.plexapp.plugins.library',
        })

    def remove_from_continue_watching(self, rating_key):
        """Drop the card from the Continue Watching hub without touching
        the watched state (Plex `PUT /actions/removeFromContinueWatching`,
        unlike unscrobble which also clears viewCount)."""
        self._request('/actions/removeFromContinueWatching',
                      {'ratingKey': rating_key}, method='PUT')

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
            {'label': i18n.tr(33137), 'items': self.on_deck(limits['on_deck'])},
            {'label': i18n.tr(33138), 'items': self.recently_added(limits['recently_added'])},
        ]

        for section in self.movie_sections():
            rr = self.recently_released(section['key'], limits['recently_released'])
            if rr:
                rows.append({
                    'label': '{} — {}'.format(section['title'], i18n.tr(33139)),
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
