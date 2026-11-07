"""Akasha Ambient — energy/dimming schedule.

Pure functions (no `xbmc*`) computing how dark the black overlay control
should be, and when the full CEC sleep sequence should kick in, given how
long the screensaver has been active. Kept separate from `ambient_window.py`
so the ramp logic is unit-testable without a Kodi runtime.

Akasha OS drives an external TV over HDMI/CEC: there is no local backlight to
dim, so "brightness reduction" (spec section 15.1) is simulated with a
semi-transparent black overlay instead of real hardware dimming (see
decisions.md).
"""

MAX_DIM_ALPHA = 0xCC  # ~80% opaque at the darkest point before sleep, out of 0xFF.
NO_DIM_COLOR = '00000000'


def _clamp(value, low, high):
    return max(low, min(high, value))


def dim_alpha(elapsed_seconds, dim_after_seconds, sleep_after_seconds,
              max_alpha=MAX_DIM_ALPHA):
    """Return the overlay alpha (0..max_alpha) for the given elapsed time.

    - Before `dim_after_seconds`: fully transparent (0).
    - Between `dim_after_seconds` and `sleep_after_seconds`: linear ramp up
      to `max_alpha`, so the screen visibly darkens as sleep approaches.
    - At/after `sleep_after_seconds`: `max_alpha` (sleep is triggered
      separately by `should_sleep`).
    """
    if elapsed_seconds <= dim_after_seconds:
        return 0
    if sleep_after_seconds <= dim_after_seconds:
        # Degenerate config (sleep <= dim): jump straight to max darkness.
        return max_alpha
    span = sleep_after_seconds - dim_after_seconds
    progress = (elapsed_seconds - dim_after_seconds) / span
    return int(_clamp(progress, 0.0, 1.0) * max_alpha)


def dim_overlay_color(elapsed_seconds, dim_after_seconds, sleep_after_seconds,
                       max_alpha=MAX_DIM_ALPHA):
    """Return an AARRGGBB hex string for the dimming overlay's colordiffuse."""
    alpha = dim_alpha(elapsed_seconds, dim_after_seconds, sleep_after_seconds, max_alpha)
    if alpha <= 0:
        return NO_DIM_COLOR
    return '{:02X}000000'.format(alpha)


def should_sleep(elapsed_seconds, sleep_after_seconds):
    """True once the configured sleep delay has elapsed."""
    return elapsed_seconds >= sleep_after_seconds


def _hour_in_window(now_hour, start_hour, end_hour):
    """True if `now_hour` (0-23) falls inside the [start, end) window.

    Overnight windows wrap midnight: start=22, end=7 matches 22h..6h59.
    Equal bounds mean "always" (the whole day).
    """
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= now_hour < end_hour
    return now_hour >= start_hour or now_hour < end_hour


def night_dim_alpha(now_hour, start_hour, end_hour, percent):
    """Overlay alpha (0..0xFF) floor applied during the night window.

    No local backlight exists on this HDMI/CEC setup, so "luminosite
    nocturne" (H3) is a constant dim veil during the configured night
    hours — the screen stays readable but the room is not lit up by a
    bright slideshow at 2AM.
    """
    if percent <= 0 or not _hour_in_window(now_hour, start_hour, end_hour):
        return 0
    return int(round(percent / 100.0 * 0xFF))


def combined_dim_color(elapsed_seconds, dim_after_seconds, sleep_after_seconds,
                        now_hour, night_enabled, night_start_hour, night_end_hour,
                        night_dim_percent, max_alpha=MAX_DIM_ALPHA):
    """AARRGGBB for the dim overlay = max(ramp alpha, night floor)."""
    ramp = dim_alpha(elapsed_seconds, dim_after_seconds, sleep_after_seconds, max_alpha)
    night = night_dim_alpha(now_hour, night_start_hour, night_end_hour,
                            night_dim_percent) if night_enabled else 0
    alpha = max(ramp, night)
    if alpha <= 0:
        return NO_DIM_COLOR
    return '{:02X}000000'.format(min(alpha, 0xFF))


# Anti burn-in (spec section 16): cycle the clock/weather widget group through
# four corner presets on a fixed interval, mirroring Guide.xml's preset
# pattern rather than computing continuous pixel offsets (see decisions.md).
# The cycle starts on preset 3 (bottom-left in Ambient.xml), the position
# Google TV uses for its own Ambient Mode clock, then rotates through the
# other corners: BL -> TL -> TR -> BR.
WIDGET_PRESET_COUNT = 4
WIDGET_PRESET_INTERVAL_SECONDS = 10 * 60
WIDGET_PRESET_OFFSET = 3


def widget_preset_for_elapsed(elapsed_seconds, interval_seconds=WIDGET_PRESET_INTERVAL_SECONDS,
                               preset_count=WIDGET_PRESET_COUNT):
    """Return which corner preset (0..preset_count-1) should be active."""
    if interval_seconds <= 0 or preset_count <= 0:
        return WIDGET_PRESET_OFFSET
    return (int(elapsed_seconds // interval_seconds) + WIDGET_PRESET_OFFSET) % preset_count
