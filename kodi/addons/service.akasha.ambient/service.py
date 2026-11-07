"""Akasha Ambient Trigger — inactivity monitoring service.

Polls Kodi's global idle time and, once the configured inactivity
threshold elapses, activates the Ambient Mode window itself -- playing the
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

This service also owns the single long-lived AmbientWindow instance
reused by every activation, automatic or manual (script.akasha.ambient's
default.py just requests activation now, see ambient_activate_handler.py):
each xbmcgui.WindowXML construction permanently consumes one of Kodi's
~100 dynamic script-window IDs for the rest of the session, even after the
window closes and the Python object is deleted -- constructing a fresh one
on every idle-triggered activation (this loop can run for days without a
Kodi restart) used to exhaust that pool within hours of normal use,
leaving Ambient Mode permanently broken (constant "maximum number of
windows reached", retried every CHECK_INTERVAL_SECONDS forever) until the
next reboot. See docs/ambient-mode/decisions.md.
"""
import os
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
AMBIENT_ADDON_PATH = xbmcaddon.Addon('script.akasha.ambient').getAddonInfo('path')
sys.path.insert(0, os.path.join(AMBIENT_ADDON_PATH, 'resources', 'lib'))
import ambient_activate_handler  # noqa: E402
import config  # noqa: E402
from ambient_window import AmbientWindow  # noqa: E402

CHECK_INTERVAL_SECONDS = 5
LOCK_FILE = '/tmp/akasha-ambient.lock'
LOCK_TTL_SECONDS = 10
SETTINGS_ADDON_ID = 'script.akasha.settings'
ENABLED_SETTING_ID = 'ambient.enabled'
# Script windows get dynamic dialog ids from 13000 up: any current dialog
# at or above this bound is one of ours (the Aura shell or a child panel)
# and safe to close when making room for Ambient.
SCRIPT_MODAL_ID_MIN = 13000
MODAL_CLOSE_WAIT_SECONDS = 5.0


def _load_settings():
    addon = xbmcaddon.Addon('script.akasha.ambient')
    return {
        'inactivity_timeout_minutes': addon.getSetting('inactivity_timeout_minutes'),
        'schedule_enabled': addon.getSetting('schedule_enabled'),
        'schedule_start_hour': addon.getSetting('schedule_start_hour'),
        'schedule_end_hour': addon.getSetting('schedule_end_hour'),
    }


def _ambient_enabled():
    try:
        return xbmcaddon.Addon(SETTINGS_ADDON_ID).getSetting(ENABLED_SETTING_ID).lower() == 'true'
    except Exception:
        # If Akasha Settings isn't installed/reachable for some reason,
        # default to enabled rather than silently disabling the feature.
        return True


def _touch_lock():
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except OSError:
        pass


def _remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


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


class AmbientTriggerMonitor(xbmc.Monitor):
    """Owns the single long-lived AmbientWindow instance and reuses it for
    every activation -- automatic (idle trigger, below) or manual (a
    notification from script.akasha.ambient's default.py, see
    ambient_activate_handler.py). Kept as an xbmc.Monitor subclass (rather
    than a plain object) so onNotification fires reliably: per Kodi's own
    threading model, a Monitor only receives notifications while
    waitForAbort()/xbmc.sleep() is pumped from the same thread it was
    created on -- guaranteed here since the main loop below both drives
    this instance's waitForAbort() and calls activate() directly.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._window = None
        self._last_seen_activate_ts = 0.0

    def onNotification(self, sender, method, data):
        if sender != ambient_activate_handler.NOTIFY_SENDER:
            return
        # Kodi always delivers a NotifyAll(sender, message) call to
        # onNotification with method prefixed "Other." (its JSON-RPC
        # namespace for messages that don't match a built-in
        # Notifications.* type) -- confirmed live via debug logging (method
        # arrived as "Other.ActivateAmbient", not the bare message). Same
        # fix as script.akasha.aura's home_press_monitor.py, see
        # docs/remote/decisions.md.
        if method != 'Other.' + ambient_activate_handler.NOTIFY_METHOD:
            return
        ts = ambient_activate_handler.read_last_request()
        if ts is None or ts <= self._last_seen_activate_ts:
            return
        self._last_seen_activate_ts = ts
        self.activate()

    def activate(self):
        if xbmc.Player().isPlaying():
            return
        if _lock_file_fresh():
            # Already open (this instance's own onInit() touches the lock
            # periodically) -- avoid re-entering doModal() on a window
            # that's already showing.
            return
        # The Aura shell is a WindowXMLDialog -- an *always-active modal*.
        # Kodi refuses to activate another script window while one is up
        # ("Activate of window refused: active modal dialogs"), which kept
        # Ambient permanently dead once the launcher had opened Aura at
        # boot. Pre-touch the ambient lock first: Aura's supervisor loop
        # suppresses its own reopen while the lock is fresh, so the shell
        # stays closed for as long as Ambient runs (and a stale lock still
        # expires on its own if Ambient never makes it on screen).
        _touch_lock()
        xbmc.log('Akasha Ambient Trigger: activating Ambient Mode', xbmc.LOGINFO)
        # Ask the Aura shell to close itself first: a forced Dialog.Close
        # on the modal leaves its doModal() permanently wedged (observed
        # live), whereas window.close() returns cleanly and the Aura
        # supervision loop stays suppressed by the lock file until Ambient
        # exits. Dialog.Close below is only a fallback for a stale wedged
        # dialog that no longer answers notifications.
        xbmc.executebuiltin('NotifyAll(akasha.ambient, SuspendForAmbient)', wait=False)
        deadline = time.time() + MODAL_CLOSE_WAIT_SECONDS
        # Give the suspend notification a grace period to land before
        # resorting to the wedge-prone forced close.
        force_close_after = time.time() + 2.0
        while time.time() < deadline:
            try:
                dialog = xbmcgui.getCurrentWindowDialogId()
            except Exception:
                break
            if dialog in (0, 9999):
                # No dialog active at all (9999 is Kodi's "invalid/none").
                break
            if dialog >= SCRIPT_MODAL_ID_MIN:
                if time.time() >= force_close_after:
                    xbmc.executebuiltin('Dialog.Close({})'.format(dialog), wait=False)
            # A *native* modal below the script range (DialogOK, DialogSelect,
            # the OTA update prompts, ...) also refuses Ambient's own modal
            # activation -- keep waiting for it to clear on its own rather
            # than stealing a user-facing prompt by force-closing it.
            time.sleep(0.2)
        try:
            still_active = xbmcgui.getCurrentWindowDialogId()
        except Exception:
            still_active = 0
        if still_active not in (0, 9999):
            xbmc.log('Akasha Ambient Trigger: a modal dialog is still active '
                      '(id={}), skipping this activation'.format(still_active),
                      xbmc.LOGINFO)
            _remove_lock()
            return
        try:
            if self._window is None:
                self._window = AmbientWindow(
                    'Ambient.xml', AMBIENT_ADDON_PATH, 'Default', '1080i')
        except RuntimeError as e:
            # Should no longer happen now that this is the only place that
            # ever constructs an AmbientWindow (see module docstring), but
            # kept defensive: fail quietly for this one activation rather
            # than crashing the whole service, which would stop the idle
            # poll loop entirely until the next Kodi restart.
            xbmc.log('Akasha Ambient Trigger: could not open window ({}); giving up for '
                      'this activation'.format(e), xbmc.LOGWARNING)
            _remove_lock()
            return
        self._window.doModal()
        # doModal() returns once Ambient closed: its own exit() already
        # removed the lock. If it never activated at all, drop our
        # pre-touched lock so the Aura shell reopens without waiting out
        # the TTL.
        if not self._window.is_active():
            _remove_lock()


def main():
    monitor = AmbientTriggerMonitor()
    xbmc.log('Akasha Ambient Trigger: service starting', xbmc.LOGINFO)

    # Give Kodi a moment to finish starting up before the first check.
    if monitor.waitForAbort(5):
        return

    while not monitor.abortRequested():
        try:
            if _ambient_enabled():
                cfg = config.load_config(_load_settings())
                idle_time = xbmc.getGlobalIdleTime()
                if not config.schedule_allows(
                        time.localtime().tm_hour, cfg.schedule_start_hour,
                        cfg.schedule_end_hour, cfg.schedule_enabled):
                    # Outside the configured activation window (H6): skip the
                    # trigger entirely; manual activation stays unaffected.
                    monitor.waitForAbort(CHECK_INTERVAL_SECONDS)
                    continue
                if _should_trigger(idle_time, cfg.inactivity_timeout_seconds):
                    xbmc.log('Akasha Ambient Trigger: idle for {}s, activating Ambient Mode'.format(
                        idle_time), xbmc.LOGINFO)
                    monitor.activate()
        except Exception as e:
            xbmc.log('Akasha Ambient Trigger: error in main loop: {}'.format(e), xbmc.LOGERROR)

        monitor.waitForAbort(CHECK_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
