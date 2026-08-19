"""Akasha Aura — home-button press handler.

Handles the case where the user presses the Home button while Akasha Aura is
already open. Kodi's global keymap fires RunScript on every Home press, so this
module lets the already-running AuraWindow instance distinguish a simple press
(return to the main Divertissement tab) from a double press within 300ms
(open the app switcher).

Communication uses a timestamp file + Kodi NotifyAll. Each new invocation writes
the current timestamp to a file and broadcasts a notification; the long-lived
AuraWindow instance has a Monitor thread that reacts to the notification and
classifies the press using the recorded timestamps.
"""
import json
import os
import time

import xbmc

PRESS_FILE = '/tmp/akasha-aura-home-press'
NOTIFY_SENDER = 'akasha.aura'
NOTIFY_METHOD = 'HomePress'


def record_home_press():
    """Write the current timestamp to the signal file and notify the running
    AuraWindow instance (if any). Safe to call from a short-lived RunScript
    process."""
    try:
        os.makedirs(os.path.dirname(PRESS_FILE), exist_ok=True)
        with open(PRESS_FILE, 'w') as f:
            f.write(str(time.time()))
    except OSError as e:
        xbmc.log('Akasha Aura: failed to record home press: {}'.format(e), xbmc.LOGWARNING)
    try:
        xbmc.executebuiltin('NotifyAll({}, {}, "{}")'.format(
            NOTIFY_SENDER, NOTIFY_METHOD, json.dumps({'ping': True})))
    except Exception as e:
        xbmc.log('Akasha Aura: failed to notify home press: {}'.format(e), xbmc.LOGWARNING)


def read_last_press():
    """Return the timestamp of the last recorded home press, or None."""
    try:
        with open(PRESS_FILE) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return None
