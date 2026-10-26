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
import xbmcgui

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

import home_press_handler  # noqa: E402
import settings_press_handler  # noqa: E402
import skip_marker  # noqa: E402
import stream_prefs  # noqa: E402
import timeline_reporter  # noqa: E402
import up_next  # noqa: E402
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


def _watch_external_playback(window, stop):
    """Yield Aura to fullscreen if playback starts through a path that
    bypasses AuraWindow._play -- JSON-RPC, PM4K, a CEC resume, etc.

    Aura's own launches set playback_started and close the window before the
    stream begins, so they never hit this watchdog. An externally started
    stream would otherwise keep playing silently behind the still-open
    modal; marking playback_started here also gives the user the same
    "return to Aura" behaviour once that playback ends.
    """
    while not stop.is_set():
        try:
            if (xbmc.Player().isPlayingVideo()
                    and not getattr(window, 'playback_started', False)):
                window.playback_started = True
                # External play isn't Aura's episode queue: keep a stale
                # Up Next prop from an earlier marathon out of the way.
                xbmcgui.Window(10000).setProperty('AuraUpNextQueue', '')
                window.close()
                return
        except Exception:
            pass
        stop.wait(1.0)


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
    # "osdmenu": invoked from the VideoOSD circles mid-playback, while the
    # Aura process below is parked in its wait-for-end loop -- handle it
    # BEFORE the already-running guard, as a standalone dialog.
    if 'skipmarker' in sys.argv[1:]:
        # The parked supervision loop spotted an intro/credits marker:
        # show the Plex-style skip chip as a standalone dialog.
        import skip_marker
        skip_marker.AuraSkipMarkerWindow(
            'AuraSkipMarker.xml', ADDON_PATH, 'Default', '1080i').doModal()
        sys.exit(0)
    if 'osdmenu' in sys.argv[1:]:
        import osd_menu
        if 'quality' in sys.argv[1:]:
            mode = 'quality'
        elif 'chapters' in sys.argv[1:]:
            mode = 'chapters'
        else:
            mode = 'streams'
        osd_menu.AuraOsdMenuWindow.mode = mode
        osd_menu.AuraOsdMenuWindow(
            'AuraOsdMenu.xml', ADDON_PATH, 'Default', '1080i').doModal()
        sys.exit(0)
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
            if open_settings:
                # Same double-press rule as SettingsPressMonitor: the
                # remote emits spurious single gear-wheel events, and a
                # lone one must not pop the settings panel "by itself".
                # The monitor handles presses while Aura runs; here the
                # file history decides -- record this press first, then
                # check whether it pairs with a recent previous one.
                prev = settings_press_handler.read_presses()
                settings_press_handler.record_settings_press()
                open_settings = (
                    bool(prev) and
                    time.time() - prev[-1]
                    <= settings_press_handler.DOUBLE_PRESS_WINDOW_SECONDS)
            window.open_settings_on_init = open_settings

            def _run_window():
                # Don't even open the modal if a video is already running:
                # skip straight to the wait-for-end loop below.
                if (xbmc.Player().isPlayingVideo()
                        and not getattr(window, 'playback_started', False)):
                    window.playback_started = True
                    return
                watch_stop = threading.Event()
                threading.Thread(
                    target=_watch_external_playback,
                    args=(window, watch_stop), daemon=True).start()
                window.doModal()
                watch_stop.set()

            _run_window()
            # Playback started from Aura: the window closed itself because
            # a modal dialog would otherwise cover the fullscreen video.
            # Wait for playback to end, then re-open Aura where the user
            # left it -- Plex-style "return to app" after watching.
            # Meanwhile the reporter keeps the server-side viewOffset
            # fresh (`/:/timeline`, parity B3) so resume works on any
            # device, and it survives the Up Next episode chaining below.
            reporter = timeline_reporter.TimelineReporter()
            reporter.start()
            # Initialized out here too: when the window closes without any
            # playback, the while body never runs and the post-loop cleanup
            # still reads these names (reporter.finish / persist_selection).
            last_pos_ms = None
            latest_item = None
            latest_selection = None
            while getattr(window, 'playback_started', False):
                # Player.play() is asynchronous: wait for the stream to
                # actually start before watching for its end, otherwise
                # Aura re-opens instantly and covers the video again.
                # playback_started deliberately stays True for the whole
                # session -- including the wait-for-start phase and the
                # gaps between chained episodes -- so monitors can tell
                # "Aura closed for playback" apart from "Aura just closed"
                # and ignore presses that should not open dialogs.
                waited = 0
                while not xbmc.Player().isPlayingVideo() and waited < 15000:
                    xbmc.sleep(200)
                    waited += 200
                # Track how much video is left while it plays: when the
                # item stops, the last polled remaining time tells a
                # natural episode end (Up Next card, B1) apart from a
                # user stop (straight back to Aura).
                remaining_s = None
                last_pos_ms = None
                silent = 0
                was_playing = False
                skip_shown_for = None
                # B15: per-show audio/subtitle continuity -- applied once
                # the player has enumerated its streams, captured
                # periodically and persisted per show.
                prefs_applied_for = None
                latest_selection = None
                latest_item = None
                last_capture = 0.0
                while silent < 4:
                    if xbmc.Player().isPlayingVideo():
                        silent = 0
                        if not was_playing:
                            # Play-start transition: report now, Plex-style,
                            # not at the next 10s tick -- a sub-10s play
                            # still lands a viewOffset for the stop report.
                            was_playing = True
                            try:
                                reporter.tick()
                            except Exception:
                                pass
                        try:
                            total = xbmc.Player().getTotalTime()
                            if total:
                                remaining_s = total - xbmc.Player().getTime()
                            last_pos_ms = int(xbmc.Player().getTime() * 1000)
                        except RuntimeError:
                            pass
                        item = stream_prefs.current_item()
                        item_key = (item or {}).get('rating_key')
                        if item_key and item_key != prefs_applied_for:
                            # Episode boundary: commit the previous item's
                            # last selection before applying the new one.
                            try:
                                stream_prefs.persist_selection(
                                    xbmcaddon.Addon(), latest_item,
                                    latest_selection)
                            except Exception:
                                pass
                            # Streams enumerate ~1s after play() resolves.
                            xbmc.sleep(1200)
                            try:
                                stream_prefs.apply_saved_streams(
                                    xbmcaddon.Addon(), item)
                            except Exception:
                                pass
                            prefs_applied_for = item_key
                        if item_key:
                            latest_item = item
                        if time.time() - last_capture >= 10:
                            last_capture = time.time()
                            try:
                                sel = stream_prefs.capture_selection()
                                if sel:
                                    latest_selection = sel
                            except Exception:
                                pass
                        # B2: inside an intro/credits marker, float the
                        # Plex-style skip chip -- once per marker window,
                        # and never again after a Back-dismiss.
                        marker = skip_marker.update_active_marker()
                        skip_key = ((marker.get('type'),
                                     marker.get('start_ms'))
                                    if marker else None)
                        if skip_key and skip_key != skip_shown_for:
                            skip_shown_for = skip_key
                            xbmc.executebuiltin(
                                'RunScript(script.akasha.aura,skipmarker)')
                        elif not skip_key:
                            skip_shown_for = None
                    # A quality switch stop/starts the player; the OSD menu
                    # holds this property across the gap so the brief silence
                    # isn't read as end-of-playback.
                    elif (xbmcgui.Window(10000)
                          .getProperty('AuraSwitchingPlayback')):
                        silent = 0
                        # Re-report on resume: the new stream starts at a
                        # different position/quality.
                        was_playing = False
                    else:
                        was_playing = False
                        silent += 1
                    xbmc.sleep(500)
                # Plex reports state=stopped the moment playback ends --
                # before the Up Next card even decides -- so the server's
                # viewOffset/Now Playing state lands while it matters.
                try:
                    reporter.stopped(last_pos_ms)
                except Exception:
                    pass
                if up_next.is_natural_end(remaining_s) \
                        and not (xbmcgui.Window(10000)
                                 .getProperty('AuraSwitchingPlayback')) \
                        and up_next.advance_via_up_next(ADDON_PATH):
                    # The card played the next episode: stay in playback
                    # mode and keep supervising the new item.
                    continue
                window.playback_started = False
                _run_window()
            # Playback session over: commit the last stream selection
            # (B15), then the final state=stopped report commits the
            # last position before the reporter thread exits.
            try:
                stream_prefs.persist_selection(
                    xbmcaddon.Addon(), latest_item, latest_selection)
            except Exception:
                pass
            reporter.finish(position_ms=last_pos_ms)
            del window
        finally:
            # The reporter is a daemon thread -- without this it would
            # outlive the script and keep pinging for the Kodi session.
            try:
                reporter.finish()
            except Exception:
                pass
            heartbeat_stop.set()
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
