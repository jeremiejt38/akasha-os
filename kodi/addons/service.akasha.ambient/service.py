"""Akasha Ambient Trigger — inactivity monitoring service.

Polls Kodi's global idle time and triggers script.akasha.ambient (via
RunScript) once the configured inactivity threshold elapses, playing the
role a native Kodi screensaver would normally play.

This is a deliberate departure from Kodi's own xbmc.ui.screensaver
mechanism: on this device, a Python screensaver addon got killed by Kodi's
CPythonInvoker watchdog ~20s after activation regardless of its
implementation (loop structure, sleep function, background threads) -- a
known, long-standing Kodi issue with Python screensavers, not specific to
this addon's code. See docs/ambient-mode/decisions.md for the full
investigation. Implementing the idle check ourselves and opening a regular
script window (the same pattern as kodi/scripts/akasha-guide.py) avoids
that watchdog entirely.
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(
    xbmcaddon.Addon('script.akasha.ambient').getAddonInfo('path'), 'resources', 'lib',
))
import config  # noqa: E402

CHECK_INTERVAL_SECONDS = 5
LOCK_FILE = '/tmp/akasha-ambient.lock'
LOCK_TTL_SECONDS = 10
AMBIENT_SCRIPT = 'RunScript(script.akasha.ambient)'
SETTINGS_ADDON_ID = 'script.akasha.settings'
ENABLED_SETTING_ID = 'ambient.enabled'


def _load_settings():
    addon = xbmcaddon.Addon('script.akasha.ambient')
    return {
        'inactivity_timeout_minutes': addon.getSetting('inactivity_timeout_minutes'),
    }


def _ambient_enabled():
    try:
        return xbmcaddon.Addon(SETTINGS_ADDON_ID).getSetting(ENABLED_SETTING_ID).lower() == 'true'
    except Exception:
        # If Akasha Settings isn't installed/reachable for some reason,
        # default to enabled rather than silently disabling the feature.
        return True


def _lock_file_fresh():
    """True if script.akasha.ambient's own lock file was touched recently.

    The Ambient window touches this file on start and periodically while
    running (see ambient_window.py), the same pattern used by
    kodi/scripts/akasha-guide.py, so this service can tell it's already
    open without needing any other IPC with the running script.
    """
    try:
        import time
        return os.path.exists(LOCK_FILE) and (time.time() - os.path.getmtime(LOCK_FILE)) < LOCK_TTL_SECONDS
    except Exception:
        return False


def _should_trigger(idle_time, threshold_seconds):
    if idle_time < threshold_seconds:
        return False
    if xbmc.Player().isPlaying():
        return False
    if _lock_file_fresh():
        # Ambient window already open; avoid stacking a second RunScript.
        return False
    if config.is_foreground_app_active(
            lambda w: xbmc.getCondVisibility('Window.IsActive({})'.format(w))):
        # Some other addon/app (not the native Home screen or one of
        # Akasha Aura's own screens) is the active window -- e.g. a
        # third-party Plex/media client with its own custom UI that
        # doesn't necessarily use xbmc.Player() or reset Kodi's global
        # idle timer. Never interrupt that with Ambient Mode, no matter
        # how long xbmc.getGlobalIdleTime() has been climbing.
        return False
    return True


def main():
    monitor = xbmc.Monitor()

    # Give Kodi a moment to finish starting up before the first check.
    if monitor.waitForAbort(5):
        return

    while not monitor.abortRequested():
        try:
            if _ambient_enabled():
                cfg = config.load_config(_load_settings())
                idle_time = xbmc.getGlobalIdleTime()
                if _should_trigger(idle_time, cfg.inactivity_timeout_seconds):
                    xbmc.log('Akasha Ambient Trigger: idle for {}s, activating Ambient Mode'.format(
                        idle_time), xbmc.LOGINFO)
                    xbmc.executebuiltin(AMBIENT_SCRIPT)
        except Exception as e:
            xbmc.log('Akasha Ambient Trigger: error in main loop: {}'.format(e), xbmc.LOGERROR)

        monitor.waitForAbort(CHECK_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
