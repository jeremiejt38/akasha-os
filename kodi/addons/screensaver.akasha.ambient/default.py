#!/usr/bin/env python3
"""Akasha Ambient — Kodi screensaver entry point (xbmc.ui.screensaver).

Kodi instantiates this addon after `screensaver.time` minutes of
inactivity, or when explicitly activated (e.g. "Mode Ambiant" in the
Akasha Guide menu, via ActivateScreensaver). All the orchestration logic
lives in resources/lib/ambient_window.py so it can evolve independently
from this thin entry point.
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
