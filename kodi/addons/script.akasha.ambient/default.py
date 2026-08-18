#!/usr/bin/env python3
"""Akasha Ambient — script entry point (RunScript).

Triggered by service.akasha.ambient once the configured inactivity delay
elapses, or manually ("Mode Ambiant" in the Akasha Guide menu). This is a
plain script window, not a Kodi xbmc.ui.screensaver addon: see
docs/ambient-mode/decisions.md for why. All the orchestration logic lives
in resources/lib/ambient_window.py so it can evolve independently from
this thin entry point.
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

from ambient_window import AmbientWindow  # noqa: E402

if __name__ == '__main__':
    try:
        window = AmbientWindow('Ambient.xml', ADDON_PATH, 'Default', '1080i')
    except RuntimeError as e:
        # Kodi caps the number of dynamically-created script windows (~100)
        # for the whole session; each RunScript invocation of this addon
        # normally exits and lets Kodi reclaim its slot, but if some other
        # addon is leaking window IDs this call can fail outright. Fail
        # quietly instead of retrying every 5s (service.akasha.ambient's
        # idle trigger) and flooding the log with the same traceback --
        # this is a same-session, Kodi-restart-only condition either way.
        xbmc.log('Akasha Ambient: could not open window ({}); giving up for '
                 'this trigger cycle'.format(e), xbmc.LOGWARNING)
    else:
        window.doModal()
        # In fullscreen video mode doModal returns immediately after the
        # window is closed, but the script must stay alive while the video
        # plays and the sleep timer runs.
        while window.is_active():
            xbmc.sleep(100)
        del window
