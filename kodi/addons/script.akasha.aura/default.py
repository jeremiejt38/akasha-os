#!/usr/bin/env python3
"""Akasha Aura — script entry point (RunScript).

Triggered automatically at boot by service.akasha.aura (replacing the native
Kodi Home screen), or via the Home button (see
kodi/userdata/keymaps/akasha-aura.xml). All orchestration logic lives in
resources/lib/aura_window.py so it can evolve independently from this thin
entry point — same pattern as script.akasha.ambient (see
docs/ambient-mode/decisions.md) and docs/aura/decisions.md.
"""
import os
import sys

import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

from aura_window import AuraWindow  # noqa: E402

if __name__ == '__main__':
    window = AuraWindow('Aura.xml', ADDON_PATH, 'Default', '1080i')
    window.doModal()
    del window
