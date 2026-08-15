"""Akasha Ambient — screensaver window orchestration.

Wires the pure logic modules (config, content_manager, weather_client,
energy) to the Kodi runtime: reads addon settings, drives the Ambient.xml
skin via window properties, and hands off to the existing CEC sleep
sequence (akasha-sleep.py) once the configured sleep delay elapses.

This module intentionally keeps as little logic as possible: anything that
can be expressed without xbmc*/xbmcgui*/xbmcaddon* lives in the sibling
pure modules (config.py, content_manager.py, weather_client.py, energy.py)
and is covered by tests/. This file is only exercised on the real device.
"""
import json
import threading
import time
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

import config
import content_manager
import energy
import weather_client

ADDON_ID = 'screensaver.akasha.ambient'
SLEEP_SCRIPT = 'RunScript(/storage/.kodi/scripts/akasha-sleep.py)'
WEATHER_REFRESH_SECONDS = weather_client.DEFAULT_CACHE_MAX_AGE_SECONDS
TICK_SECONDS = 1.0


def _fetch_json(url):
    """Real network fetch (stdlib only) used outside of unit tests."""
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))


def _load_raw_settings():
    addon = xbmcaddon.Addon(ADDON_ID)
    return {
        'content_path': addon.getSetting('content_path'),
        'dim_after_minutes': addon.getSetting('dim_after_minutes'),
        'sleep_after_minutes': addon.getSetting('sleep_after_minutes'),
        'weather_enabled': addon.getSetting('weather_enabled'),
        'weather_city': addon.getSetting('weather_city'),
        'weather_latitude': addon.getSetting('weather_latitude'),
        'weather_longitude': addon.getSetting('weather_longitude'),
    }


class AmbientWindow(xbmcgui.WindowXMLDialog):
    """Fullscreen ambient dialog, following the same pattern as GuideWindow
    (kodi/scripts/akasha-guide.py): a WindowXMLDialog whose onInit() runs the
    main loop directly, exiting when Kodi signals the screensaver should
    deactivate (any user input) or once the configured sleep delay elapses.
    """

    class ExitMonitor(xbmc.Monitor):
        def __init__(self, exit_callback):
            super().__init__()
            self._exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            try:
                self._exit_callback()
            except Exception as e:
                xbmc.log('Akasha Ambient: exit callback error: {}'.format(e), xbmc.LOGERROR)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active = False
        self._monitor = None
        try:
            self.cfg = config.load_config(_load_raw_settings())
        except Exception as e:
            xbmc.log('Akasha Ambient: failed to load settings, using defaults: {}'.format(e),
                      xbmc.LOGERROR)
            self.cfg = config.load_config({})

    def onInit(self):
        self._active = True
        self._monitor = self.ExitMonitor(self.exit)
        try:
            self._setup_background()
            self._start_weather_thread()
            self._run_loop()
        except Exception as e:
            xbmc.log('Akasha Ambient: fatal error in screensaver loop: {}'.format(e), xbmc.LOGERROR)
            self.exit()

    def _setup_background(self):
        path = content_manager.resolve_slideshow_path(self.cfg.content_path, self.cfg.fallback_image)
        self.setProperty('content_path', path)

    def _start_weather_thread(self):
        if not self.cfg.weather_enabled:
            self.setProperty('weather_available', '')
            return
        thread = threading.Thread(target=self._weather_loop, daemon=True)
        thread.start()

    def _weather_loop(self):
        while self._active:
            reading = weather_client.get_weather(
                _fetch_json, self.cfg.weather_cache_path,
                self.cfg.weather_latitude, self.cfg.weather_longitude,
            )
            self._apply_weather(reading)
            # Sleep in 1s increments so `exit()` can stop this thread promptly
            # instead of waiting up to an hour for the next refresh.
            for _ in range(int(WEATHER_REFRESH_SECONDS)):
                if not self._active:
                    return
                time.sleep(1)

    def _apply_weather(self, reading):
        if not reading:
            self.setProperty('weather_available', '')
            return
        self.setProperty('weather_available', '1')
        self.setProperty('weather_temp', '{}°'.format(reading.get('temperature', '?')))
        self.setProperty('weather_condition', reading.get('condition_label', ''))

    def _run_loop(self):
        started_at = time.time()
        while self._active and self._monitor and not self._monitor.abortRequested():
            elapsed = time.time() - started_at

            self.setProperty('widget_preset', str(energy.widget_preset_for_elapsed(elapsed)))
            self.setProperty('dim_color', energy.dim_overlay_color(
                elapsed, self.cfg.dim_after_seconds, self.cfg.sleep_after_seconds,
            ))

            if energy.should_sleep(elapsed, self.cfg.sleep_after_seconds):
                self._trigger_sleep()
                return

            xbmc.sleep(int(TICK_SECONDS * 1000))

    def _trigger_sleep(self):
        xbmc.log('Akasha Ambient: sleep delay reached, handing off to akasha-sleep.py', xbmc.LOGINFO)
        xbmc.executebuiltin(SLEEP_SCRIPT)
        self.exit()

    def exit(self):
        if not self._active:
            return
        self._active = False
        self._monitor = None
        try:
            self.close()
        except Exception:
            pass
