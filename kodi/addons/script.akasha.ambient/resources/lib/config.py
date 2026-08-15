"""Akasha Ambient — pure configuration handling.

No dependency on xbmc/xbmcaddon/xbmcgui, so this module can be unit-tested
without a Kodi runtime. `ambient_window.py` and `service.akasha.ambient`
adapt Kodi's addon settings into the plain dict expected by `load_config()`.
"""

DEFAULT_CONTENT_PATH = '/storage/ambient/photos'
# Kodi's multiimage skin control requires a *folder*, not a single file. This
# folder is bundled with the addon itself (see resources/media/fallback/) so
# there is always at least one valid image to show, even before the user
# adds any photo to DEFAULT_CONTENT_PATH.
DEFAULT_FALLBACK_FOLDER = '/storage/.kodi/addons/script.akasha.ambient/resources/media/fallback'
DEFAULT_WEATHER_CACHE_PATH = '/storage/.config/akasha-os/ambient-weather-cache.json'

DEFAULTS = {
    'content_path': DEFAULT_CONTENT_PATH,
    'inactivity_timeout_minutes': 5,
    'dim_after_minutes': 2,
    'sleep_after_minutes': 30,
    'weather_enabled': True,
    'weather_city': 'Paris',
    'weather_latitude': 48.8566,
    'weather_longitude': 2.3522,
}

# Bounds used to reject nonsensical settings values (e.g. corrupted addon
# settings) instead of crashing the screensaver window.
_MIN_INACTIVITY_MINUTES = 1
_MAX_INACTIVITY_MINUTES = 120
_MIN_DIM_MINUTES = 1
_MAX_DIM_MINUTES = 120
_MIN_SLEEP_MINUTES = 1
_MAX_SLEEP_MINUTES = 720


class AmbientConfig:
    """Validated, immutable snapshot of the Ambient Mode configuration."""

    __slots__ = (
        'content_path', 'fallback_folder', 'inactivity_timeout_minutes',
        'dim_after_minutes', 'sleep_after_minutes', 'weather_enabled',
        'weather_city', 'weather_latitude', 'weather_longitude',
        'weather_cache_path',
    )

    def __init__(self, content_path, fallback_folder, inactivity_timeout_minutes,
                 dim_after_minutes, sleep_after_minutes, weather_enabled, weather_city,
                 weather_latitude, weather_longitude, weather_cache_path):
        self.content_path = content_path
        self.fallback_folder = fallback_folder
        self.inactivity_timeout_minutes = inactivity_timeout_minutes
        self.dim_after_minutes = dim_after_minutes
        self.sleep_after_minutes = sleep_after_minutes
        self.weather_enabled = weather_enabled
        self.weather_city = weather_city
        self.weather_latitude = weather_latitude
        self.weather_longitude = weather_longitude
        self.weather_cache_path = weather_cache_path

    @property
    def inactivity_timeout_seconds(self):
        return self.inactivity_timeout_minutes * 60

    @property
    def dim_after_seconds(self):
        return self.dim_after_minutes * 60

    @property
    def sleep_after_seconds(self):
        return self.sleep_after_minutes * 60


def _as_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _as_bool(value, default):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes')
    return default


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_config(settings):
    """Build an `AmbientConfig` from a plain dict of raw setting values.

    Unknown or invalid values fall back to `DEFAULTS` rather than raising,
    since Ambient Mode must never crash Kodi's GUI over a bad setting.
    """
    settings = settings or {}

    content_path = str(settings.get('content_path') or DEFAULTS['content_path']).strip()
    if not content_path:
        content_path = DEFAULTS['content_path']

    return AmbientConfig(
        content_path=content_path,
        fallback_folder=DEFAULT_FALLBACK_FOLDER,
        inactivity_timeout_minutes=_as_int(
            settings.get('inactivity_timeout_minutes'), DEFAULTS['inactivity_timeout_minutes'],
            _MIN_INACTIVITY_MINUTES, _MAX_INACTIVITY_MINUTES,
        ),
        dim_after_minutes=_as_int(
            settings.get('dim_after_minutes'), DEFAULTS['dim_after_minutes'],
            _MIN_DIM_MINUTES, _MAX_DIM_MINUTES,
        ),
        sleep_after_minutes=_as_int(
            settings.get('sleep_after_minutes'), DEFAULTS['sleep_after_minutes'],
            _MIN_SLEEP_MINUTES, _MAX_SLEEP_MINUTES,
        ),
        weather_enabled=_as_bool(settings.get('weather_enabled'), DEFAULTS['weather_enabled']),
        weather_city=str(settings.get('weather_city') or DEFAULTS['weather_city']).strip()
        or DEFAULTS['weather_city'],
        weather_latitude=_as_float(settings.get('weather_latitude'), DEFAULTS['weather_latitude']),
        weather_longitude=_as_float(settings.get('weather_longitude'), DEFAULTS['weather_longitude']),
        weather_cache_path=str(settings.get('weather_cache_path') or DEFAULT_WEATHER_CACHE_PATH),
    )
