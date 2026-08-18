"""Akasha Aura — on-device TTL cache for already-displayed pages/metadata.

The connector already caches server-side, but every request still crosses
the network (and, for connector.akasha.ing, the public internet). Caching
the pages we've already fetched *on the Pi itself* (SQLite file under the
addon's profile directory) makes revisiting a row/section/library near-
instant and keeps things working through brief network hiccups.

Posters/thumbnails are intentionally NOT duplicated here: Kodi's own
texture cache (`Textures13.db`) already persists downloaded images across
sessions keyed by URL, which is exactly what we want for images.

No dependency on xbmc*, testable with plain `python3 -m unittest`.
"""

import json
import sqlite3
import time

DEFAULT_TTL_SECONDS = 600


class LocalCache:
    """A tiny sqlite-backed key/value TTL cache."""

    def __init__(self, db_path):
        self.db_path = db_path
        conn = self._connect()
        try:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS cache ('
                'key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL)'
            )
            conn.commit()
        finally:
            conn.close()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def get(self, key):
        """Return the cached value for `key`, or None if missing/expired."""
        conn = self._connect()
        try:
            row = conn.execute(
                'SELECT value, expires_at FROM cache WHERE key = ?', (key,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        value, expires_at = row
        if expires_at < time.time():
            return None
        return json.loads(value)

    def set(self, key, value, ttl_seconds=DEFAULT_TTL_SECONDS):
        expires_at = time.time() + ttl_seconds
        conn = self._connect()
        try:
            conn.execute(
                'INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)',
                (key, json.dumps(value), expires_at),
            )
            conn.commit()
        finally:
            conn.close()

    def get_or_set(self, key, ttl_seconds, compute_fn):
        """Return the cached value for `key`, computing and storing it on a miss."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute_fn()
        self.set(key, value, ttl_seconds)
        return value


def page_cache_key(*parts):
    """Build a stable cache key from arbitrary string/int parts."""
    return ':'.join(str(p) for p in parts if p is not None and p != '')


def get_or_set_page(cache, key, ttl_seconds, compute_fn):
    """Like `LocalCache.get_or_set`, but safe for `(items, total)` tuples.

    `compute_fn` may return either a plain list or a `(items, total)` tuple
    (see paged_list.PagedList). `LocalCache.set` stores values as JSON,
    which round-trips a tuple as a list -- so a cache HIT would otherwise
    return `[items, total]` instead of `(items, total)`, and
    `PagedList._load_next_page`'s `isinstance(result, tuple)` check would
    then treat that 2-element list itself as the page (bug found on a real
    device 2026-08-18: repeated cache hits silently corrupted every
    paginated view into "2 element(s)").

    Always returns a `(items, total)` tuple, regardless of what `compute_fn`
    returned or how the cache backend serialised it.
    """
    cached = cache.get(key)
    if cached is not None:
        if isinstance(cached, dict) and 'items' in cached:
            return cached['items'], cached.get('total')
        return cached, None

    result = compute_fn()
    if isinstance(result, tuple):
        items, total = result
    else:
        items, total = result, None
    cache.set(key, {'items': items, 'total': total}, ttl_seconds)
    return items, total


def open_addon_cache(addon, filename='page_cache.db'):
    """Return a LocalCache backed by a file in the addon's profile directory.

    Kept out of the pure/tested part of this module since it needs xbmcvfs
    (available in the Kodi runtime only).
    """
    import xbmcvfs

    profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    xbmcvfs.mkdirs(profile_dir)
    return LocalCache(_join_path(profile_dir, filename))


def _join_path(directory, filename):
    if directory.endswith('/') or directory.endswith('\\'):
        return directory + filename
    return directory + '/' + filename
