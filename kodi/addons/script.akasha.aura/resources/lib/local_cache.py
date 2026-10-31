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
PURGE_INTERVAL_SECONDS = 300


class LocalCache:
    """A tiny sqlite-backed key/value TTL cache."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._next_purge = 0.0
        self._ensure_schema()

    def _connect(self):
        # WAL lets readers and the writer overlap instead of serialising
        # on the db lock; NORMAL sync is safe in WAL (a crash loses at
        # most the last transaction, which is just cache). Both pragmas
        # are best-effort -- a read-only profile dir must not break the
        # cache layer.
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
        except sqlite3.OperationalError:
            pass
        return conn

    def _ensure_schema(self):
        conn = self._connect()
        try:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS cache ('
                'key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL)'
            )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS cache_expires ON cache(expires_at)'
            )
            self._purge_expired(conn)
            conn.commit()
        finally:
            conn.close()

    def _purge_expired(self, conn):
        conn.execute('DELETE FROM cache WHERE expires_at < ?', (time.time(),))

    def _purge_if_due(self, conn):
        if time.time() >= self._next_purge:
            self._purge_expired(conn)
            self._next_purge = time.time() + PURGE_INTERVAL_SECONDS

    def _missing_table(self, error):
        return 'no such table' in str(error)

    def get(self, key):
        """Return the cached value for `key`, or None if missing/expired."""
        value, expired = self.get_stale(key)
        return None if expired else value

    def get_stale(self, key):
        """Return ``(value, expired)`` for `key`, or ``(None, True)`` absent.

        Unlike `get`, an expired-but-present row comes back with
        ``expired=True`` so callers can render it immediately and
        revalidate in the background (stale-while-revalidate).

        The cache is a pure optimisation layer and must never break a
        feature that happens to hit it: if the underlying sqlite file is
        ever missing its table (found on a real device after an external
        process removed/truncated the db file while Kodi still held it
        open -- "no such table: cache"), self-heal by recreating the
        schema and treat this call as a cache miss. Any other
        OperationalError (e.g. a transient lock) is likewise a miss,
        never an exception.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                'SELECT value, expires_at FROM cache WHERE key = ?', (key,)
            ).fetchone()
        except sqlite3.OperationalError as e:
            if self._missing_table(e):
                conn.close()
                self._ensure_schema()
            return None, True
        finally:
            conn.close()
        if row is None:
            return None, True
        value, expires_at = row
        return json.loads(value), expires_at < time.time()

    def set(self, key, value, ttl_seconds=DEFAULT_TTL_SECONDS):
        expires_at = time.time() + ttl_seconds
        payload = json.dumps(value)
        conn = self._connect()
        try:
            for attempt in range(2):
                try:
                    self._purge_if_due(conn)
                    conn.execute(
                        'INSERT OR REPLACE INTO cache (key, value, expires_at)'
                        ' VALUES (?, ?, ?)',
                        (key, payload, expires_at),
                    )
                    conn.commit()
                    return
                except sqlite3.OperationalError as e:
                    # Self-heal only on a genuinely missing schema; a
                    # locked or otherwise failing db just skips the write
                    # -- a cache store must never break the caller.
                    if attempt or not self._missing_table(e):
                        return
                    conn.close()
                    self._ensure_schema()
                    conn = self._connect()
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
