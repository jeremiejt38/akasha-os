"""Akasha Ambient — Open-Meteo weather client with a local JSON cache.

No API key required (https://open-meteo.com/), no third-party Python
dependency: network access is injected as a `fetch_json(url) -> dict`
callable so this module stays unit-testable without a real network call or
an `xbmc*` runtime. `ambient_window.py` supplies the real implementation
(stdlib `urllib.request`).
"""
import json
import os
import time

FORECAST_URL = (
    'https://api.open-meteo.com/v1/forecast'
    '?latitude={lat}&longitude={lon}'
    '&current=temperature_2m,weather_code'
    '&timezone=auto'
)
GEOCODING_URL = (
    'https://geocoding-api.open-meteo.com/v1/search'
    '?name={city}&count=1&language=fr&format=json'
)

DEFAULT_CACHE_MAX_AGE_SECONDS = 60 * 60  # 1 hour, per spec section 12.3

# WMO weather interpretation codes used by Open-Meteo.
_CONDITION_LABELS = {
    0: 'Ciel degage',
    1: 'Peu nuageux',
    2: 'Partiellement nuageux',
    3: 'Couvert',
    45: 'Brouillard',
    48: 'Brouillard givrant',
    51: 'Bruine legere',
    53: 'Bruine',
    55: 'Bruine forte',
    56: 'Bruine verglacante',
    57: 'Bruine verglacante forte',
    61: 'Pluie legere',
    63: 'Pluie',
    65: 'Pluie forte',
    66: 'Pluie verglacante',
    67: 'Pluie verglacante forte',
    71: 'Neige legere',
    73: 'Neige',
    75: 'Neige forte',
    77: 'Grains de neige',
    80: 'Averses legeres',
    81: 'Averses',
    82: 'Averses violentes',
    85: 'Averses de neige',
    86: 'Averses de neige fortes',
    95: 'Orage',
    96: 'Orage avec grele',
    99: 'Orage avec grele forte',
}


def condition_label_for_code(code):
    """Human-readable French label for a WMO weather code."""
    try:
        return _CONDITION_LABELS[int(code)]
    except (TypeError, ValueError, KeyError):
        return 'Inconnu'


def geocode_city(fetch_json, city_name):
    """Resolve a city name to (latitude, longitude) via Open-Meteo geocoding.

    Returns None on any failure (network error, unknown city, malformed
    response) so callers can keep using the previously configured
    coordinates instead of crashing.
    """
    if not city_name:
        return None
    try:
        url = GEOCODING_URL.format(city=city_name)
        data = fetch_json(url)
        results = data.get('results') or []
        if not results:
            return None
        first = results[0]
        return float(first['latitude']), float(first['longitude'])
    except Exception:
        return None


def fetch_current_weather(fetch_json, latitude, longitude):
    """Fetch current temperature and condition for the given coordinates.

    Returns a normalized dict, or None on failure.
    """
    try:
        url = FORECAST_URL.format(lat=latitude, lon=longitude)
        data = fetch_json(url)
        current = data['current']
        code = current['weather_code']
        return {
            'temperature': round(float(current['temperature_2m'])),
            'weather_code': int(code),
            'condition_label': condition_label_for_code(code),
            'fetched_at': time.time(),
        }
    except Exception:
        return None


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
            json.dump(data, f)
        return True
    except OSError:
        return False


def is_cache_fresh(cache, now, max_age_seconds=DEFAULT_CACHE_MAX_AGE_SECONDS):
    if not cache or 'fetched_at' not in cache:
        return False
    return (now - cache['fetched_at']) < max_age_seconds


def get_weather(fetch_json, cache_path, latitude, longitude, now=None,
                 max_age_seconds=DEFAULT_CACHE_MAX_AGE_SECONDS):
    """Return the best available weather reading.

    Order of preference: fresh cache -> live fetch (cached for next call) ->
    stale cache (offline fallback, per spec section 10.3) -> None.
    """
    now = time.time() if now is None else now
    cache = load_cache(cache_path)

    if is_cache_fresh(cache, now, max_age_seconds):
        return cache

    fresh = fetch_current_weather(fetch_json, latitude, longitude)
    if fresh is not None:
        save_cache(cache_path, fresh)
        return fresh

    # Offline / API error: serve the last known reading rather than nothing.
    return cache
