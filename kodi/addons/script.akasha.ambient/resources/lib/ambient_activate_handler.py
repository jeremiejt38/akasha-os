"""Akasha Ambient -- manual "Mode Ambiant" activation request handler.

Same IPC pattern as script.akasha.aura's home_press_handler.py /
settings_press_handler.py: the manual "Mode Ambiant" entry in the Akasha
Guide menu fires `RunScript(script.akasha.ambient)`, a short-lived process
that can't itself own the long-lived AmbientWindow instance (see
docs/ambient-mode/decisions.md -- reusing that single instance across
every activation, automatic or manual, is exactly what avoids permanently
consuming one of Kodi's ~100 dynamic script-window IDs per trigger). This
module lets that short-lived process record the request and notify the
long-lived service.akasha.ambient instance, which owns the shared
AmbientWindow and shows it.
"""
import os
import time

import xbmc

ACTIVATE_FILE = '/tmp/akasha-ambient-activate-request'
NOTIFY_SENDER = 'akasha.ambient'
NOTIFY_METHOD = 'ActivateAmbient'


def record_activate_request():
    try:
        os.makedirs(os.path.dirname(ACTIVATE_FILE), exist_ok=True)
        with open(ACTIVATE_FILE, 'w') as f:
            f.write(str(time.time()))
    except OSError as e:
        xbmc.log('Akasha Ambient: failed to record activate request: {}'.format(e),
                  xbmc.LOGWARNING)
    try:
        xbmc.executebuiltin('NotifyAll({}, {})'.format(NOTIFY_SENDER, NOTIFY_METHOD))
    except Exception as e:
        xbmc.log('Akasha Ambient: failed to notify activate request: {}'.format(e),
                  xbmc.LOGWARNING)


def read_last_request():
    try:
        with open(ACTIVATE_FILE) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return None
