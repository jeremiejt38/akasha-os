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


# Anti burn-in (spec section 16): cycle the clock/weather widget group through
# four corner presets on a fixed interval, mirroring Guide.xml's preset
# pattern rather than computing continuous pixel offsets (see decisions.md).
WIDGET_PRESET_COUNT = 4
WIDGET_PRESET_INTERVAL_SECONDS = 10 * 60


def widget_preset_for_elapsed(elapsed_seconds, interval_seconds=WIDGET_PRESET_INTERVAL_SECONDS,
                               preset_count=WIDGET_PRESET_COUNT):
    """Return which corner preset (0..preset_count-1) should be active."""
    if interval_seconds <= 0 or preset_count <= 0:
        return 0
    return int(elapsed_seconds // interval_seconds) % preset_count
