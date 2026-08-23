#!/usr/bin/env python3
"""Akasha Ambient — script entry point (RunScript).

Manual "Mode Ambiant" entry in the Akasha Guide menu fires
RunScript(script.akasha.ambient), which lands here. This process no
longer constructs its own AmbientWindow: every xbmcgui.WindowXML
construction permanently consumes one of Kodi's ~100 dynamic
script-window IDs for the rest of the session, even after the window
closes and the Python object is deleted (see docs/ambient-mode/decisions.md
and docs/aura/decisions.md) -- fine for the occasional manual trigger, but
this same window is also (re-)opened automatically every few minutes by
service.akasha.ambient's idle-trigger polling loop, which used to exhaust
the pool within hours of normal use.

Both entry points now share a single long-lived AmbientWindow instance
owned by service.akasha.ambient (a persistent process for Kodi's whole
uptime, unlike this short-lived RunScript invocation): this manual trigger
just records the request and notifies that service, the same IPC pattern
already used by script.akasha.aura's home_press_handler.py /
settings_press_handler.py.
"""
import os
import sys

import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

import ambient_activate_handler  # noqa: E402

if __name__ == '__main__':
    ambient_activate_handler.record_activate_request()
