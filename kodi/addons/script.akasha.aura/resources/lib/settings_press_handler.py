"""Akasha Aura -- "open settings" remote-button press handler.

Same pattern as home_press_handler.py: the Fire TV remote's gear-wheel
button (dd440e2e section 9) fires `RunScript(script.akasha.aura,
opensettings)` on every press via the global keymap. If Aura is
already running, default.py can't just construct a second AuraWindow
(see its own module docstring on window-id exhaustion) -- it instead
records the request here and notifies the running instance, which
opens the unified settings panel (plan a5a87f03) itself.

The press file keeps the last few timestamps (not just the latest one):
the remote emits isolated SPURIOUS gear-wheel events, so the settings
panel requires a double press -- and detecting a double press needs the
previous timestamp, even across an Aura (re)launch where the monitor is
not listening yet.
"""
import json
import os
import time

import xbmc

PRESS_FILE = '/tmp/akasha-aura-settings-press'
NOTIFY_SENDER = 'akasha.aura'
NOTIFY_METHOD = 'SettingsPress'
# Two presses within this window count as an intentional double press.
# Wider than Home's 0.3s: the gear-wheel is a less habitual button.
DOUBLE_PRESS_WINDOW_SECONDS = 0.9
_HISTORY = 4


def record_settings_press():
    now = time.time()
    try:
        stamps = read_presses()[-_HISTORY + 1:]
        stamps.append(now)
        with open(PRESS_FILE, 'w') as f:
            f.write(' '.join(str(s) for s in stamps))
    except OSError as e:
        xbmc.log('Akasha Aura: failed to record settings press: {}'.format(e), xbmc.LOGWARNING)
    try:
        xbmc.executebuiltin('NotifyAll({}, {}, "{}")'.format(
            NOTIFY_SENDER, NOTIFY_METHOD, json.dumps({'ping': True})))
    except Exception as e:
        xbmc.log('Akasha Aura: failed to notify settings press: {}'.format(e), xbmc.LOGWARNING)


def read_presses():
    """Recorded press timestamps, oldest first (empty list on failure)."""
    try:
        with open(PRESS_FILE) as f:
            return [float(s) for s in f.read().split() if s]
    except (OSError, ValueError):
        return []


def double_press_just_happened(freshness=4.0):
    """True when the two newest recorded presses form a recent double.

    Used by AuraWindow.onInit to catch a double press that completed
    while Aura was still launching -- the monitor may have missed that
    second notification entirely.
    """
    presses = read_presses()
    if len(presses) < 2:
        return False
    last, prev = presses[-1], presses[-2]
    return (time.time() - last) <= freshness and \
        0 < (last - prev) <= DOUBLE_PRESS_WINDOW_SECONDS
