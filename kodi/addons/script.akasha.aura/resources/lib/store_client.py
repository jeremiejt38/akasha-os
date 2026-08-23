"""Akasha Aura -- Akasha OS Store catalogue client.

Fetches the real akasha-os-store index.json (a separate, metadata-only
GitHub repo, see plan f4e069bb) and caches it locally with a 24h TTL plus
manual refresh, same pattern as script.akasha.ambient's weather_client.py:
network access is injected as a `fetch_json(url) -> dict` callable so this
module stays unit-testable without a real network call or an `xbmc*`
runtime -- aura_store.py supplies the real implementation (stdlib
urllib.request).

Deviation from the plan's own section 4.1 ("via akasha-os-connector pour la
mise en cache/acceleration"): fetched directly from GitHub's raw content
CDN instead of proxying through akasha-os-connector. The connector's whole
purpose (see its own docs/architecture.md) is caching/authenticating
*Plex* metadata for multiple akasha-os users behind one admin token --
index.json is public, static, unauthenticated JSON already served from a
CDN, so routing it through the connector would add a hop and a new
unrelated endpoint to that service for no real benefit. Revisit only if a
concrete need for connector-side caching emerges in practice.
"""
import json
import os
import time

INDEX_URL = (
    'https://raw.githubusercontent.com/jeremiejt38/akasha-os-store/main/index.json'
)
DEFAULT_CACHE_PATH = '/storage/.config/akasha-os/store-index-cache.json'
DEFAULT_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60  # 24h, per plan section 1.4


def load_cache(cache_path):
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_cache(cache_path, data):
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except OSError:
        return False


def is_cache_fresh(cache, now, max_age_seconds=DEFAULT_CACHE_MAX_AGE_SECONDS):
    if not cache or 'fetched_at' not in cache:
        return False
    return (now - cache['fetched_at']) < max_age_seconds


def _normalize_index(raw):
    """Validate/normalize a raw index.json payload into a stable shape:
    {'generated_at': str, 'entries': [manifest dict, ...]}. Malformed or
    missing fields fall back to safe defaults rather than raising, so one
    bad payload can't crash the whole Store tab."""
    if not isinstance(raw, dict):
        return {'generated_at': None, 'entries': []}
    entries = raw.get('entries')
    if not isinstance(entries, list):
        entries = []
    return {
        'generated_at': raw.get('generated_at'),
        'entries': [e for e in entries if isinstance(e, dict) and e.get('id')],
    }


def fetch_index(fetch_json, url=INDEX_URL):
    """Fetch and normalize the live index.json. Returns None on failure
    (network error, malformed JSON) so callers can fall back to a cached
    copy instead of crashing."""
    try:
        raw = fetch_json(url)
    except Exception:
        return None
    normalized = _normalize_index(raw)
    normalized['fetched_at'] = time.time()
    return normalized


def get_index(fetch_json, cache_path=DEFAULT_CACHE_PATH, now=None,
               max_age_seconds=DEFAULT_CACHE_MAX_AGE_SECONDS, force_refresh=False):
    """Return the best available catalogue: fresh cache -> live fetch
    (cached for next call) -> stale cache (offline fallback) -> an empty
    catalogue. `force_refresh=True` is the "refresh manuel" entry point
    from plan section 1.4, bypassing the 24h TTL."""
    now = time.time() if now is None else now
    cache = load_cache(cache_path)

    if not force_refresh and is_cache_fresh(cache, now, max_age_seconds):
        return cache

    fresh = fetch_index(fetch_json)
    if fresh is not None:
        save_cache(cache_path, fresh)
        return fresh

    if cache is not None:
        return cache

    return {'generated_at': None, 'entries': [], 'fetched_at': None}


def entries_by_id(index):
    return {e['id']: e for e in index.get('entries', [])}


def entries_by_category(index):
    """Group entries by category (plan section 4.2: "catalogue groupe par
    category, avec recherche/filtre"), preserving index.json's own order
    within each group."""
    grouped = {}
    for entry in index.get('entries', []):
        grouped.setdefault(entry.get('category', 'autre'), []).append(entry)
    return grouped


def search_entries(index, query):
    """Case-insensitive substring match against name/description, per
    plan section 4.2's "recherche"."""
    query = (query or '').strip().lower()
    if not query:
        return list(index.get('entries', []))
    return [
        e for e in index.get('entries', [])
        if query in (e.get('name') or '').lower()
        or query in (e.get('description') or '').lower()
    ]
