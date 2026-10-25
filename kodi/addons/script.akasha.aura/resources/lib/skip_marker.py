#!/usr/bin/env python3
"""Plex-style "Skip Intro / Skip Credits" (parity backlog B2).

Plex embeds `Marker` windows (intro/credits) in the item metadata; while
the position sits inside one it floats a labelled chip at the bottom
right of the player -- pressing it seeks to the marker end.

Split of responsibilities:

- osd_menu.store_markers() fetched the marker list at play time and
  keeps it in Window(10000).AuraPlaybackMarkers keyed by ratingKey.
- update_active_marker() is called every poll of default.py's playback
  supervision: it resolves the currently playing ratingKey, checks the
  position against the stored windows, and publishes the active marker
  on AuraActiveMarker -- spawning the chip dialog is the caller's job.
- AuraSkipMarkerWindow is the chip itself: a small modal (opened via
  RunScript(script.akasha.aura,skipmarker)) that seeks on click,
  dismisses on Back, and auto-closes when the marker window ends.
"""
import json
import threading

import xbmc
import xbmcgui
import i18n
import osd_menu

# Marker currently inside the playback position, JSON
# {'type','start_ms','end_ms'} -- empty when none.
PROP_ACTIVE = 'AuraActiveMarker'

SKIP_BUTTON_ID = 6410


def _home():
    return xbmcgui.Window(10000)


def active_marker(markers, position_ms):
    """The marker window containing `position_ms`, or None.

    Markers list entries: {'type','start_ms','end_ms'} as normalised by
    PlexClient.item_markers."""
    for marker in markers or []:
        try:
            if int(marker['start_ms']) <= position_ms < int(marker['end_ms']):
                return marker
        except (KeyError, TypeError, ValueError):
            continue
    return None


def update_active_marker():
    """Poll-side helper for default.py's supervision loop.

    Resolves the playing item's stored markers, compares the position,
    and keeps AuraActiveMarker in sync. Returns the active marker dict
    (or None) so the caller can decide whether to spawn the chip."""
    win = _home()
    try:
        if not xbmc.Player().isPlayingVideo():
            win.setProperty(PROP_ACTIVE, '')
            return None
        position_ms = int(xbmc.Player().getTime() * 1000)
    except RuntimeError:
        return None
    marker = active_marker(osd_menu._current_markers(), position_ms)
    if marker:
        win.setProperty(PROP_ACTIVE, json.dumps(marker))
    else:
        win.setProperty(PROP_ACTIVE, '')
    return marker


def _active_marker():
    try:
        return json.loads(_home().getProperty(PROP_ACTIVE) or '{}')
    except (ValueError, TypeError):
        return {}


def _marker_label_id(marker_type):
    if marker_type == 'intro':
        return 33568
    if marker_type == 'credits':
        return 33569
    return 33570


class AuraSkipMarkerWindow(xbmcgui.WindowXMLDialog):
    """The floating skip chip. Focus lands on the button (Plex focuses
    it too), OK seeks to the marker end, Back dismisses; a watcher
    thread closes it the moment playback leaves the marker window."""

    def onInit(self):
        self._end_ms = 0
        self._stop = threading.Event()
        marker = _active_marker()
        if not marker:
            self.close()
            return
        try:
            self._end_ms = int(marker['end_ms'])
        except (KeyError, TypeError, ValueError):
            self.close()
            return
        self.getControl(SKIP_BUTTON_ID).setLabel(
            i18n.tr(_marker_label_id(marker.get('type'))))
        self.setFocusId(SKIP_BUTTON_ID)
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        while not self._stop.wait(0.3):
            try:
                if not xbmc.Player().isPlayingVideo():
                    break
                # A seek back INTO the marker must not dismiss the chip:
                # only leaving the window does.
                pos_ms = int(xbmc.Player().getTime() * 1000)
            except RuntimeError:
                break
            if pos_ms >= self._end_ms or pos_ms < 0:
                break
            if not _home().getProperty(PROP_ACTIVE):
                break
        self._dismiss()

    def _dismiss(self):
        self._stop.set()
        try:
            _home().setProperty(PROP_ACTIVE, '')
        except Exception:
            pass
        try:
            self.close()
        except RuntimeError:
            pass

    def onClick(self, control_id):
        if control_id != SKIP_BUTTON_ID:
            return
        end_ms = self._end_ms
        self._dismiss()
        try:
            xbmc.Player().seekTime(end_ms / 1000.0)
        except RuntimeError:
            pass

    def onAction(self, action):
        if action.getId() in osd_menu._back_ids():
            self._dismiss()
