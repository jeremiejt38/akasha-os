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
import slideshow
import weather_client

ADDON_ID = 'script.akasha.ambient'
SLEEP_SCRIPT = 'RunScript(/storage/.kodi/scripts/akasha-sleep.py)'
WEATHER_REFRESH_SECONDS = weather_client.DEFAULT_CACHE_MAX_AGE_SECONDS
TICK_SECONDS = 1.0
# Google TV Ambient Mode paces its photos in tens of seconds; 45s per photo
# with a 3s skin-side crossfade (see Ambient.xml) matches that feel.
PHOTO_SECONDS = 45.0
# Delay between pointing the hidden slot at the next photo and toggling the
# visibility property: the texture loads in the background so the crossfade
# never shows a black frame.
PHOTO_PRELOAD_SECONDS = 1.5
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


class AmbientWindow(xbmcgui.WindowXML):
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
        self._is_video_mode = False
        self._cycler = None

    def is_active(self):
        """Return True until exit() has been called."""
        return self._active

    def onInit(self):
        self._active = True
        _touch_lock()
        # Reloaded on every activation (not just __init__) since this same
        # instance is now reused across triggers -- see
        # service.akasha.ambient/service.py and docs/ambient-mode/decisions.md
        # ("reutiliser l'instance AmbientWindow au lieu d'en recreer une a
        # chaque declenchement") -- otherwise a settings change would only
        # take effect after a full Kodi restart.
        try:
            self.cfg = config.load_config(_load_raw_settings())
        except Exception as e:
            xbmc.log('Akasha Ambient: failed to load settings, using defaults: {}'.format(e),
                     xbmc.LOGERROR)
            self.cfg = config.load_config({})
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
        xbmc.log('Akasha Ambient: onAction id={}'.format(action.getId()), xbmc.LOGDEBUG)
        self.exit()

    def onClick(self, controlID):
        self.exit()

    def _setup_background(self):
        media_type, content = content_manager.resolve_media(
            self.cfg.content_path, self.cfg.fallback_folder,
        )
        if media_type == 'videos':
            self._is_video_mode = True
            try:
                playlist = _build_video_playlist(content)
                self._player = xbmc.Player()
                # Play fullscreen so the native player handles Back/Stop. We
                # monitor isPlaying() to close the ambient script once the user
                # exits the player. The WindowXML is closed immediately so the
                # video is not rendered behind it.
                self._player.play(playlist, windowed=False)
                # Repeat the whole playlist so the ambient background never stops.
                xbmc.executebuiltin('PlayerControl(RepeatAll)', wait=False)
                threading.Thread(target=self._video_monitor_loop, daemon=True).start()
                xbmc.log('Akasha Ambient: playing {} video(s)'.format(len(content)), xbmc.LOGINFO)
                # Close the XML window; the fullscreen player now owns the screen
                # and default.py keeps the script alive while playback runs.
                try:
                    self.close()
                except Exception:
                    pass
            except Exception as e:
                xbmc.log('Akasha Ambient: video playback failed, falling back to images: {}'.format(e),
                         xbmc.LOGERROR)
                # Fall back to the multiimage path if video playback fails.
                self._player = None
                self._is_video_mode = False
                self.setProperty('has_videos', '')
                self._start_slideshow(
                    content_manager.resolve_image_paths(
                        self.cfg.fallback_folder, self.cfg.fallback_folder))
        else:
            self._start_slideshow(
                content_manager.resolve_image_paths(content, self.cfg.fallback_folder))

    def _start_slideshow(self, image_paths):
        """Start the two-slot crossfade slideshow thread.

        The skin (Ambient.xml) owns two fullscreen `image` controls whose
        visibility follows `ambient.slot`; each slot runs a Ken Burns zoom
        variant picked per photo via `ambient.kb{slot}`. This thread only
        preloads the next photo onto the hidden slot then flips the
        property — the crossfade itself is a skin animation.
        """
        self._cycler = slideshow.PhotoCycler(image_paths)
        self.setProperty('ambient.slot', '')
        threading.Thread(target=self._slideshow_loop, daemon=True).start()

    def _slideshow_loop(self):
        slot = None
        while self._active and self._cycler is not None:
            photo = self._cycler.next_photo()
            if photo is None:
                return
            target = 0 if slot is None else 1 - slot
            try:
                self.setProperty('ambient.kb{}'.format(target), self._cycler.next_variant())
                self.setProperty('ambient.img{}'.format(target), photo)
            except Exception:
                # Window already closed.
                return
            if not self._sleep_chunked(PHOTO_PRELOAD_SECONDS):
                return
            try:
                self.setProperty('ambient.slot', str(target))
            except Exception:
                return
            slot = target
            if not self._sleep_chunked(PHOTO_SECONDS):
                return

    def _sleep_chunked(self, seconds):
        """Sleep up to `seconds` in 1s chunks; False when exit() ran meanwhile."""
        deadline = time.time() + seconds
        while self._active:
            remaining = deadline - time.time()
            if remaining <= 0:
                return True
            time.sleep(min(TICK_SECONDS, remaining))
        return False

    def _video_monitor_loop(self):
        """For fullscreen video mode, exit the ambient window once the user
        stops the player (Back/Stop). Allow a short startup delay so the
        first isPlaying() check does not race with player initialization.
        """
        time.sleep(1)
        while self._active and self._player is not None:
            try:
                if not self._player.isPlaying():
                    xbmc.log('Akasha Ambient: player stopped, exiting', xbmc.LOGINFO)
                    self.exit()
                    return
            except Exception:
                pass
            time.sleep(0.5)

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
        try:
            if not reading:
                self.setProperty('weather_available', '')
                return
            self.setProperty('weather_available', '1')
            self.setProperty('weather_temp', '{}°'.format(reading.get('temperature', '?')))
            self.setProperty('weather_condition', reading.get('condition_label', ''))
        except Exception:
            # Window may already be closed in fullscreen video mode.
            pass

    def _ticker_loop(self):
        started_at = time.time()
        while self._active:
            elapsed = time.time() - started_at
            _touch_lock()

            if not self._is_video_mode:
                # Keep focus on the hidden button so window actions (Back) are
                # delivered to onAction instead of being swallowed by the player.
                try:
                    self.setFocusId(9000)
                except Exception:
                    pass

                try:
                    self.setProperty('widget_preset', str(energy.widget_preset_for_elapsed(elapsed)))
                    self.setProperty('dim_color', energy.dim_overlay_color(
                        elapsed, self.cfg.dim_after_seconds, self.cfg.sleep_after_seconds,
                    ))
                except Exception:
                    pass

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
        if not self._is_video_mode:
            try:
                self.close()
            except Exception:
                pass
