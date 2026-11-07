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
    'weather_auto_coords': True,
    'credit_enabled': True,
    'pair_portraits': True,
    'night_dim_enabled': True,
    'night_start_hour': 22,
    'night_end_hour': 7,
    'night_dim_percent': 40,
    'schedule_enabled': False,
    'schedule_start_hour': 8,
    'schedule_end_hour': 23,
    'public_mode': False,
}

# Bounds used to reject nonsensical settings values (e.g. corrupted addon
# settings) instead of crashing the screensaver window.
_MIN_INACTIVITY_MINUTES = 1
_MAX_INACTIVITY_MINUTES = 120
_MIN_DIM_MINUTES = 1
_MAX_DIM_MINUTES = 120
_MIN_SLEEP_MINUTES = 1
_MAX_SLEEP_MINUTES = 720
_MIN_HOUR = 0
_MAX_HOUR = 23
_MIN_NIGHT_DIM_PERCENT = 0
_MAX_NIGHT_DIM_PERCENT = 80


class AmbientConfig:
    """Validated, immutable snapshot of the Ambient Mode configuration."""

    __slots__ = (
        'content_path', 'fallback_folder', 'inactivity_timeout_minutes',
        'dim_after_minutes', 'sleep_after_minutes', 'weather_enabled',
        'weather_city', 'weather_latitude', 'weather_longitude',
        'weather_auto_coords', 'credit_enabled', 'pair_portraits',
        'night_dim_enabled', 'night_start_hour', 'night_end_hour',
        'night_dim_percent', 'schedule_enabled', 'schedule_start_hour',
        'schedule_end_hour', 'weather_cache_path', 'public_mode',
    )

    def __init__(self, content_path, fallback_folder, inactivity_timeout_minutes,
                 dim_after_minutes, sleep_after_minutes, weather_enabled, weather_city,
                 weather_latitude, weather_longitude, weather_auto_coords,
                 credit_enabled, pair_portraits, night_dim_enabled, night_start_hour,
                 night_end_hour, night_dim_percent, schedule_enabled,
                 schedule_start_hour, schedule_end_hour, weather_cache_path,
                 public_mode):
        self.content_path = content_path
        self.fallback_folder = fallback_folder
        self.inactivity_timeout_minutes = inactivity_timeout_minutes
        self.dim_after_minutes = dim_after_minutes
        self.sleep_after_minutes = sleep_after_minutes
        self.weather_enabled = weather_enabled
        self.weather_city = weather_city
        self.weather_latitude = weather_latitude
        self.weather_longitude = weather_longitude
        self.weather_auto_coords = weather_auto_coords
        self.credit_enabled = credit_enabled
        self.pair_portraits = pair_portraits
        self.night_dim_enabled = night_dim_enabled
        self.night_start_hour = night_start_hour
        self.night_end_hour = night_end_hour
        self.night_dim_percent = night_dim_percent
        self.schedule_enabled = schedule_enabled
        self.schedule_start_hour = schedule_start_hour
        self.schedule_end_hour = schedule_end_hour
        self.weather_cache_path = weather_cache_path
        self.public_mode = public_mode

    @property
    def inactivity_timeout_seconds(self):
        return self.inactivity_timeout_minutes * 60

    @property
    def dim_after_seconds(self):
        return self.dim_after_minutes * 60

    @property
    def sleep_after_seconds(self):
        return self.sleep_after_minutes * 60


# Windows that are safe to interrupt with Ambient Mode purely based on
# Kodi's own global idle timer (native Home, and every one of Akasha Aura's
# own screens -- browsing Aura idly for the configured timeout should still
# trigger Ambient, exactly like sitting on the native Home screen would).
# Any *other* active window means some third-party addon (e.g. a script-type
# addon with its own custom browse/playback UI, like a Plex client that
# isn't going through xbmc.Player) is genuinely being used in the
# foreground -- Ambient must never interrupt that, even once the idle timer
# alone would otherwise justify it, since such addons don't necessarily
# reset Kodi's global idle timer or register with xbmc.Player() the way
# native video playback does. See docs/ambient-mode/decisions.md (bug found
# on the real device: Ambient/sleep triggered while the user was actively
# watching content through such an addon).
IDLE_SAFE_WINDOW_NAMES = (
    'home',
    '1194',  # script.akasha.aura: Aura.xml
    '1195',  # script.akasha.aura: AuraLibrary.xml
    '1196',  # script.akasha.aura: AuraApp.xml
    '1197',  # script.akasha.aura: AuraStore.xml
    '1198',  # script.akasha.aura: AuraShow.xml
    '1199',  # script.akasha.aura: AuraDetail.xml (Plex-style item page)
    '1200',  # script.akasha.aura: AuraGenres.xml
    '1201',  # script.akasha.aura: AuraSearch.xml (Plex-style search)
)


def schedule_allows(now_hour, start_hour, end_hour, enabled):
    """True if Ambient Mode may auto-trigger at `now_hour` (0-23).

    An overnight window (start > end, e.g. 22 -> 7) wraps midnight.
    A disabled schedule always allows activation.
    """
    if not enabled:
        return True
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= now_hour < end_hour
    return now_hour >= start_hour or now_hour < end_hour


def is_foreground_app_active(is_window_active_fn):
    """True if the active window is something other than the native Home
    screen or one of Akasha Aura's own screens.

    `is_window_active_fn` is a callable(window_name_or_id) -> bool, normally
    `lambda w: xbmc.getCondVisibility('Window.IsActive({})'.format(w))`
    (kept injectable so this stays testable without a Kodi runtime).
    """
    return not any(is_window_active_fn(w) for w in IDLE_SAFE_WINDOW_NAMES)


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
        weather_auto_coords=_as_bool(
            settings.get('weather_auto_coords'), DEFAULTS['weather_auto_coords']),
        credit_enabled=_as_bool(settings.get('credit_enabled'), DEFAULTS['credit_enabled']),
        pair_portraits=_as_bool(settings.get('pair_portraits'), DEFAULTS['pair_portraits']),
        night_dim_enabled=_as_bool(
            settings.get('night_dim_enabled'), DEFAULTS['night_dim_enabled']),
        night_start_hour=_as_int(
            settings.get('night_start_hour'), DEFAULTS['night_start_hour'],
            _MIN_HOUR, _MAX_HOUR,
        ),
        night_end_hour=_as_int(
            settings.get('night_end_hour'), DEFAULTS['night_end_hour'],
            _MIN_HOUR, _MAX_HOUR,
        ),
        night_dim_percent=_as_int(
            settings.get('night_dim_percent'), DEFAULTS['night_dim_percent'],
            _MIN_NIGHT_DIM_PERCENT, _MAX_NIGHT_DIM_PERCENT,
        ),
        schedule_enabled=_as_bool(
            settings.get('schedule_enabled'), DEFAULTS['schedule_enabled']),
        schedule_start_hour=_as_int(
            settings.get('schedule_start_hour'), DEFAULTS['schedule_start_hour'],
            _MIN_HOUR, _MAX_HOUR,
        ),
        schedule_end_hour=_as_int(
            settings.get('schedule_end_hour'), DEFAULTS['schedule_end_hour'],
            _MIN_HOUR, _MAX_HOUR,
        ),
        weather_cache_path=str(settings.get('weather_cache_path') or DEFAULT_WEATHER_CACHE_PATH),
        public_mode=_as_bool(settings.get('public_mode'), DEFAULTS['public_mode']),
    )
