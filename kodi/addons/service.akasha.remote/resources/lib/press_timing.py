"""Akasha Remote — pure press-timing classification (simple vs double press).

No dependency on xbmc*, so this module can be unit tested with plain
`python3 -m unittest` (see docs/talos-strategy.md in the akasha-os repo).

Long-press is handled natively by Kodi's own keymap `mod="longpress"`
support (keyboard keymaps only, ~250ms hold threshold -- see
docs/remote/decisions.md), so this module only needs to distinguish a
simple press from a double press: Kodi's keymap has no "double press"
modifier, so every simple press fires immediately and unconditionally --
telling a genuine simple press apart from the *first* press of a double
press requires tracking how recently the previous press happened.
"""

DOUBLE_PRESS_WINDOW_SECONDS = 0.3

FIRST = 'first'
DOUBLE = 'double'


def classify_press(now, last_press_at, window_seconds=DOUBLE_PRESS_WINDOW_SECONDS):
    """Classify a new press given the timestamp of the previous one.

    Returns DOUBLE if `now` is within `window_seconds` of `last_press_at`
    (or exactly at the edge of the window), FIRST otherwise (including when
    `last_press_at` is None, i.e. no previous press recorded).

    The caller is responsible for the actual scheduling: on FIRST, defer
    the "simple press" action for `window_seconds` (e.g. via Kodi's
    AlarmClock built-in) so a subsequent press within the window can cancel
    it and fire the "double press" action instead.
    """
    if last_press_at is None:
        return FIRST
    if now - last_press_at <= window_seconds:
        return DOUBLE
    return FIRST
