"""Akasha Aura — pure press-timing classification (simple vs double press).

Duplicated from service.akasha.remote/resources/lib/press_timing.py to avoid
a cross-addon dependency. See docs/remote/decisions.md for the rationale.
"""

DOUBLE_PRESS_WINDOW_SECONDS = 0.3

FIRST = 'first'
DOUBLE = 'double'


def classify_press(now, last_press_at, window_seconds=DOUBLE_PRESS_WINDOW_SECONDS):
    """Classify a new press given the timestamp of the previous one.

    Returns DOUBLE if `now` is within `window_seconds` of `last_press_at`,
    FIRST otherwise (including when `last_press_at` is None).
    """
    if last_press_at is None:
        return FIRST
    if now - last_press_at <= window_seconds:
        return DOUBLE
    return FIRST
