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
import threading
import time

import xbmc
import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

import home_press_handler  # noqa: E402
import settings_press_handler  # noqa: E402
from aura_window import AuraWindow  # noqa: E402

LOCK_FILE = '/tmp/akasha-aura.lock'
# The running script rewrites the lock on a heartbeat; a lock older than
# this means the previous script died without reaching its finally block
# (killed thread, addon reload, Kodi crash). The stored PID alone cannot
# detect that case: it is Kodi's own PID, which outlives every RunScript
# invocation -- a stale lock then kept reporting "already running" and
# swallowed every Home press for the rest of the session.
LOCK_STALE_SECONDS = 6.0
_LOCK_HEARTBEAT_SECONDS = 2.0


def _write_lock():
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except OSError:
        pass


def _heartbeat(stop_event):
    while not stop_event.wait(_LOCK_HEARTBEAT_SECONDS):
        _write_lock()


def _already_running():
    """True if a previous invocation's AuraWindow is still alive."""
    try:
        return (time.time() - os.path.getmtime(LOCK_FILE)) < LOCK_STALE_SECONDS
    except OSError:
        return False


if __name__ == '__main__':
    # "opensettings": the gear-wheel remote button's global keymap entry
    # (dd440e2e section 9), distinct from a plain Home press.
    open_settings = 'opensettings' in sys.argv[1:]
    if _already_running():
        # Aura is already open -- can't just construct a second AuraWindow
        # (see this module's own docstring on window-id exhaustion).
        if open_settings:
            xbmc.log('Akasha Aura: settings button pressed while running, '
                      'routing to active window', xbmc.LOGINFO)
            settings_press_handler.record_settings_press()
        else:
            # The user pressed Home again while inside Aura. Record the
            # press so the running AuraWindow instance can distinguish a
            # simple press (return to Divertissement tab) from a double
            # press (open app switcher). See home_press_handler.py and
            # docs/remote/decisions.md.
            xbmc.log('Akasha Aura: duplicate Home press while running, routing to active window',
                     xbmc.LOGINFO)
            home_press_handler.record_home_press()
    else:
        _write_lock()
        heartbeat_stop = threading.Event()
        threading.Thread(
            target=_heartbeat, args=(heartbeat_stop,), daemon=True).start()
        try:
            window = AuraWindow('Aura.xml', ADDON_PATH, 'Default', '1080i')
            window.open_settings_on_init = False
            window.doModal()
            # Playback started from Aura: the window closed itself because
            # a modal dialog would otherwise cover the fullscreen video.
            # Wait for playback to end, then re-open Aura where the user
            # left it -- Plex-style "return to app" after watching.
            while getattr(window, 'playback_started', False):
                window.playback_started = False
                # Player.play() is asynchronous: wait for the stream to
                # actually start before watching for its end, otherwise
                # Aura re-opens instantly and covers the video again.
                waited = 0
                while not xbmc.Player().isPlayingVideo() and waited < 15000:
                    xbmc.sleep(200)
                    waited += 200
                while xbmc.Player().isPlayingVideo():
                    xbmc.sleep(500)
                window.doModal()
            del window
        finally:
            heartbeat_stop.set()
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
