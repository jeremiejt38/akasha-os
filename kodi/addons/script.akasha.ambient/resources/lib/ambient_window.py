"""Akasha Ambient — window orchestration.

Wires the pure logic modules (config, content_manager, weather_client,
energy) to the Kodi runtime: reads addon settings, drives the Ambient.xml
skin via window properties, and hands off to the existing CEC sleep
sequence (akasha-sleep.py) once the configured sleep delay elapses.

This is a plain xbmcgui.WindowXMLDialog opened via RunScript (see
default.py), the same pattern as kodi/scripts/akasha-guide.py's
GuideWindow — deliberately NOT a Kodi xbmc.ui.screensaver addon. Kodi's
CPythonInvoker watchdog was observed to kill screensaver-type scripts
~20s after activation regardless of their implementation, a known,
long-standing Kodi issue (see docs/ambient-mode/decisions.md). The
inactivity trigger is handled by service.akasha.ambient instead of
Kodi's native screensaver mechanism.
"""
import json
import os
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

ADDON_ID = 'script.akasha.ambient'
SLEEP_SCRIPT = 'RunScript(/storage/.kodi/scripts/akasha-sleep.py)'
WEATHER_REFRESH_SECONDS = weather_client.DEFAULT_CACHE_MAX_AGE_SECONDS
TICK_SECONDS = 1.0
# Touched on start and refreshed periodically so service.akasha.ambient can
# tell this window is already open and avoid triggering a second one.
LOCK_FILE = '/tmp/akasha-ambient.lock'


def _touch_lock():
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


def _fetch_json(url):
    """Real network fetch (stdlib only) used outside of unit tests."""
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))


def _load_raw_settings():
    addon = xbmcaddon.Addon(ADDON_ID)
    return {
        'content_path': addon.getSetting('content_path'),
        'inactivity_timeout_minutes': addon.getSetting('inactivity_timeout_minutes'),
        'dim_after_minutes': addon.getSetting('dim_after_minutes'),
        'sleep_after_minutes': addon.getSetting('sleep_after_minutes'),
        'weather_enabled': addon.getSetting('weather_enabled'),
        'weather_city': addon.getSetting('weather_city'),
        'weather_latitude': addon.getSetting('weather_latitude'),
        'weather_longitude': addon.getSetting('weather_longitude'),
    }


def _build_video_playlist(video_paths):
    """Build a Kodi video playlist from an ordered list of file paths."""
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    # Give Kodi a moment to process the clear, known timing issue on some versions.
    xbmc.sleep(100)
    for path in video_paths:
        listitem = xbmcgui.ListItem(path=path)
        playlist.add(path, listitem)
    playlist.shuffle()
    return playlist


class AmbientWindow(xbmcgui.WindowXMLDialog):
    """Fullscreen ambient dialog. onInit() only sets up initial state and
    starts background threads (weather refresh, dim/preset/sleep ticker);
    doModal() (called from default.py) provides the actual blocking wait.
    Closes on any user input (onAction) or once the configured sleep delay
    elapses (handing off to akasha-sleep.py first).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active = False
        self._player = None
        try:
            self.cfg = config.load_config(_load_raw_settings())
        except Exception as e:
            xbmc.log('Akasha Ambient: failed to load settings, using defaults: {}'.format(e),
                     xbmc.LOGERROR)
            self.cfg = config.load_config({})

    def onInit(self):
        self._active = True
        _touch_lock()
        try:
            self._setup_background()
            self._start_weather_thread()
            threading.Thread(target=self._ticker_loop, daemon=True).start()
        except Exception as e:
            xbmc.log('Akasha Ambient: fatal error during init: {}'.format(e), xbmc.LOGERROR)
            self.exit()

    def onAction(self, action):
        # Any input dismisses Ambient Mode immediately (spec section 17:
        # "reveil immediat", the recommended default for a TV).
        self.exit()

    def onClick(self, controlID):
        self.exit()

    def _setup_background(self):
        media_type, content = content_manager.resolve_media(
            self.cfg.content_path, self.cfg.fallback_folder,
        )
        if media_type == 'videos':
            self.setProperty('has_videos', '1')
            try:
                playlist = _build_video_playlist(content)
                # Make sure any active busy dialog is closed before playing,
                # otherwise Kodi may render the video behind the window.
                xbmc.executebuiltin('Dialog.Close(busydialog,true)', wait=False)
                self._player = xbmc.Player()
                self._player.play(playlist, windowed=True)
                # Repeat the whole playlist so the ambient background never stops.
                xbmc.executebuiltin('PlayerControl(RepeatAll)', wait=False)
                xbmc.log('Akasha Ambient: playing {} video(s)'.format(len(content)), xbmc.LOGINFO)
            except Exception as e:
                xbmc.log('Akasha Ambient: video playback failed, falling back to images: {}'.format(e),
                         xbmc.LOGERROR)
                # Fall back to the multiimage path if video playback fails.
                self._player = None
                self.setProperty('has_videos', '')
                self.setProperty('content_path', self.cfg.fallback_folder)
        else:
            self.setProperty('content_path', content)

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

    def _ticker_loop(self):
        started_at = time.time()
        while self._active:
            elapsed = time.time() - started_at
            _touch_lock()

            self.setProperty('widget_preset', str(energy.widget_preset_for_elapsed(elapsed)))
            self.setProperty('dim_color', energy.dim_overlay_color(
                elapsed, self.cfg.dim_after_seconds, self.cfg.sleep_after_seconds,
            ))

            if energy.should_sleep(elapsed, self.cfg.sleep_after_seconds):
                self._trigger_sleep()
                return

            time.sleep(TICK_SECONDS)

    def _trigger_sleep(self):
        xbmc.log('Akasha Ambient: sleep delay reached, handing off to akasha-sleep.py', xbmc.LOGINFO)
        xbmc.executebuiltin(SLEEP_SCRIPT)
        self.exit()

    def exit(self):
        if not self._active:
            return
        self._active = False
        if self._player is not None:
            try:
                self._player.stop()
            except Exception:
                pass
            self._player = None
        _remove_lock()
        try:
            self.close()
        except Exception:
            pass
