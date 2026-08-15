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

import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

from ambient_window import AmbientWindow  # noqa: E402

if __name__ == '__main__':
    window = AmbientWindow('Ambient.xml', ADDON_PATH, 'Default', '1080i')
    window.doModal()
    del window
