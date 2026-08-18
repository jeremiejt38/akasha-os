#!/usr/bin/env python3
"""Akasha Aura — script entry point (RunScript).

Triggered automatically at boot by service.akasha.aura (replacing the native
Kodi Home screen), or via the Home button (see
kodi/userdata/keymaps/akasha-aura.xml) -- a GLOBAL keymap binding, so it
fires every time Home is pressed even while Aura is already open. Without a
guard this would stack a brand new AuraWindow on top of the running one on
every single Home press: each xbmcgui.WindowXMLDialog construction
permanently consumes one of Kodi's ~100 dynamic script-window IDs for the
rest of the session (see docs/aura/decisions.md), and Home is by far the
most frequently pressed button on a living-room remote -- this would have
exhausted the pool far faster than anything else in the addon.

All orchestration logic lives in resources/lib/aura_window.py so it can
evolve independently from this thin entry point — same pattern as
script.akasha.ambient (see docs/ambient-mode/decisions.md) and
docs/aura/decisions.md.
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

from aura_window import AuraWindow  # noqa: E402

LOCK_FILE = '/tmp/akasha-aura.lock'


def _already_running():
    """True if a previous invocation's AuraWindow is still alive."""
    try:
        with open(LOCK_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # raises OSError if that PID is no longer alive
        return True
    except (OSError, ValueError, FileNotFoundError):
        return False


if __name__ == '__main__':
    if _already_running():
        xbmc.log('Akasha Aura: already running, ignoring duplicate launch', xbmc.LOGINFO)
    else:
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
        except OSError:
            pass
        try:
            window = AuraWindow('Aura.xml', ADDON_PATH, 'Default', '1080i')
            window.doModal()
            del window
        finally:
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
