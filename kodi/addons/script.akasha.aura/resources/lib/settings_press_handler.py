"""Akasha Aura -- "open settings" remote-button press handler.

Same pattern as home_press_handler.py: the Fire TV remote's gear-wheel
button (dd440e2e section 9) fires `RunScript(script.akasha.aura,
opensettings)` on every press via the global keymap. If Aura is
already running, default.py can't just construct a second AuraWindow
(see its own module docstring on window-id exhaustion) -- it instead
records the request here and notifies the running instance, which
opens the unified settings panel (plan a5a87f03) itself.
"""
import json
import os
import time

import xbmc

PRESS_FILE = '/tmp/akasha-aura-settings-press'
NOTIFY_SENDER = 'akasha.aura'
NOTIFY_METHOD = 'SettingsPress'


def record_settings_press():
    try:
        os.makedirs(os.path.dirname(PRESS_FILE), exist_ok=True)
        with open(PRESS_FILE, 'w') as f:
            f.write(str(time.time()))
    except OSError as e:
        xbmc.log('Akasha Aura: failed to record settings press: {}'.format(e), xbmc.LOGWARNING)
    try:
        xbmc.executebuiltin('NotifyAll({}, {}, "{}")'.format(
            NOTIFY_SENDER, NOTIFY_METHOD, json.dumps({'ping': True})))
    except Exception as e:
        xbmc.log('Akasha Aura: failed to notify settings press: {}'.format(e), xbmc.LOGWARNING)
