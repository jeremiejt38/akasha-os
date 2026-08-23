"""Akasha Aura — Monitor thread for home-button press notifications.

Runs inside the long-lived AuraWindow instance and classifies repeated Home
presses (simple vs double) using the timestamp file written by default.py.
See docs/remote/decisions.md for the architecture rationale.
"""
import threading
import time

import xbmc

import home_press_handler
import press_timing
import settings_press_handler

DOUBLE_PRESS_WINDOW_SECONDS = 0.3


class HomePressMonitor(xbmc.Monitor):
    """Listen for HomePress notifications and invoke the window callback.

    The callback is called from the Monitor thread. Most AuraWindow operations
    used in the callback are lightweight property/setFocus/executebuiltin calls;
    if Kodi ever raises thread-safety issues here, we can switch to a
    queued-handoff pattern later.
    """

    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback
        self._last_seen_ts = 0.0
        self._pending_single_timer = None
        self._lock = threading.Lock()

    def onNotification(self, sender, method, data):
        if sender != home_press_handler.NOTIFY_SENDER:
            return
        # Kodi always delivers a NotifyAll(sender, message) call to
        # onNotification with method prefixed "Other." (its JSON-RPC
        # namespace for messages that don't match a built-in
        # Notifications.* type) -- confirmed live via debug logging
        # (method arrived as "Other.HomePress"/"Other.SettingsPress", not
        # the bare message). This bridge was silently never firing before
        # this fix (see docs/remote/decisions.md).
        if method != 'Other.' + home_press_handler.NOTIFY_METHOD:
            return
        ts = home_press_handler.read_last_press()
        if ts is None:
            return
        with self._lock:
            if ts <= self._last_seen_ts:
                return
            self._last_seen_ts = ts
            if self._pending_single_timer is not None:
                self._pending_single_timer.cancel()
                self._pending_single_timer = None
                self._invoke('double')
                return
            self._pending_single_timer = threading.Timer(
                DOUBLE_PRESS_WINDOW_SECONDS, self._on_single_timeout)
            self._pending_single_timer.start()

    def _on_single_timeout(self):
        with self._lock:
            self._pending_single_timer = None
        self._invoke('single')

    def _invoke(self, action):
        try:
            self._callback(action)
        except Exception as e:
            xbmc.log('Akasha Aura: home press callback failed: {}'.format(e), xbmc.LOGERROR)

    def stop(self):
        with self._lock:
            if self._pending_single_timer is not None:
                self._pending_single_timer.cancel()
                self._pending_single_timer = None


class SettingsPressMonitor(xbmc.Monitor):
    """Listen for SettingsPress notifications (gear-wheel remote button,
    dd440e2e section 9) and invoke the window callback. No simple/double
    distinction needed here, unlike HomePressMonitor -- every press just
    opens the unified settings panel."""

    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback
        self._last_seen_ts = 0.0

    def onNotification(self, sender, method, data):
        if sender != settings_press_handler.NOTIFY_SENDER:
            return
        # See the identical "Other." prefix note in HomePressMonitor above.
        if method != 'Other.' + settings_press_handler.NOTIFY_METHOD:
            return
        ts = None
        try:
            with open(settings_press_handler.PRESS_FILE) as f:
                ts = float(f.read().strip())
        except (OSError, ValueError):
            return
        if ts <= self._last_seen_ts:
            return
        self._last_seen_ts = ts
        try:
            self._callback()
        except Exception as e:
            xbmc.log('Akasha Aura: settings press callback failed: {}'.format(e), xbmc.LOGERROR)
