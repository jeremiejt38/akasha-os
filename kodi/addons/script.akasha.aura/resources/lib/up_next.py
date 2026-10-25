#!/usr/bin/env python3
"""Plex-style "Up Next" chaining between episodes (B1).

Plex does not chain episodes silently: when one ends it shows a post-play
card with the next episode's art, a countdown and Play-now/Cancel
actions. Aura mirrors that with:

- aura_window/aura_detail play a SINGLE item (no more auto-advancing
  Kodi playlist) and persist the remaining season queue through
  osd_menu.store_playback_context() -> Window(10000).AuraUpNextQueue.
- default.py's parked playback loop watches the position; when the item
  ends naturally (last polled remaining time under
  NATURAL_END_REMAINING_SECONDS) it opens AuraUpNextWindow. The user's
  choice -- or the countdown reaching zero -- either starts the next
  episode or lets Aura re-open.

Every display/timing value lives in a named constant so it can be
retuned once the real Plex values are measured on screen (Claude
flagged most of them as unverified: countdown length, overlay vs
dedicated screen, default focus).
"""

import json
import threading

import xbmc
import xbmcgui
import i18n
import osd_menu

# Tuneable Plex-parity parameters (unverified against the real app --
# Claude flagged countdown/focus/back semantics as "à vérifier à
# l'écran"): kept as constants for a cheap post-audit adjustment.
UP_NEXT_COUNTDOWN_SECONDS = 15
NATURAL_END_REMAINING_SECONDS = 3.0

HEADING_ID = 6400
TITLE_ID = 6401
SUBTITLE_ID = 6402
COUNTDOWN_ID = 6403
PLAY_ID = 6404
CANCEL_ID = 6405
THUMB_ID = 6406
BACKDROP_ID = 6407


def _home():
    return xbmcgui.Window(10000)


def is_natural_end(remaining_seconds):
    """True when the player stopped with essentially nothing left to
    play -- distinguishes 'episode finished' (Up Next) from a user
    stop/back (straight back to Aura)."""
    return (remaining_seconds is not None
            and remaining_seconds <= NATURAL_END_REMAINING_SECONDS)


def _read_queue():
    try:
        return json.loads(_home().getProperty(osd_menu.PROP_QUEUE) or '[]')
    except (ValueError, TypeError):
        return []


def peek_queue():
    """Next queued episode dict, or None."""
    queue = _read_queue()
    return queue[0] if queue else None


def pop_queue():
    """Drop and return the episode about to play so the prop always
    holds *what comes after the currently playing item*."""
    queue = _read_queue()
    item = queue.pop(0) if queue else None
    _home().setProperty(osd_menu.PROP_QUEUE, json.dumps(queue))
    return item


def _season_episode_label(item):
    """'S2 - E5' -- same pattern as divert_source/aura_detail."""
    season = item.get('season')
    index = item.get('index')
    if season is None or index is None:
        return ''
    return 'S{} - E{}'.format(season, index)


def _hydrate(item):
    """Queued hub episodes can lack part_key; one metadata fetch fixes
    it (same trick as aura_window._hydrate_item)."""
    if item.get('part_key') or not item.get('rating_key'):
        return item
    server, token, _, _ = osd_menu._playback_context()
    if not server or not token:
        return item
    try:
        import plex_client
        full = plex_client.PlexClient(
            server, token, timeout=5).metadata_item(item['rating_key'])
        if isinstance(full, dict) and full:
            full.setdefault('type', item.get('type'))
            item = full
    except Exception as e:
        xbmc.log('Akasha Aura UpNext: hydration failed: {}'.format(e),
                 xbmc.LOGWARNING)
    return item


def _stream_url(item):
    server, token, _, _ = osd_menu._playback_context()
    part = item.get('part_key')
    if not server or not token or not part:
        return None
    joiner = '&' if '?' in part else '?'
    return '{}{}{}X-Plex-Token={}'.format(server, part, joiner, token)


class AuraUpNextWindow(xbmcgui.WindowXMLDialog):
    """The post-play card. One instance per Aura run, re-doModal'd for
    every episode boundary -- each WindowXMLDialog construction costs a
    Kodi window id permanently, so building one per episode would burn
    the ~100-id pool during a long session."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = None
        self.result = 'cancel'
        self._stop = threading.Event()

    def onInit(self):
        item = self.item or {}
        self.result = 'cancel'
        self._stop.clear()
        try:
            self.getControl(HEADING_ID).setLabel(i18n.tr(33561))
            self.getControl(TITLE_ID).setLabel(item.get('title') or '')
            parts = [p for p in (_season_episode_label(item),
                                 item.get('show_title')) if p]
            self.getControl(SUBTITLE_ID).setLabel(' · '.join(parts))
            self.getControl(PLAY_ID).setLabel(i18n.tr(33563))
            self.getControl(CANCEL_ID).setLabel(i18n.tr(33564))
            art = (item.get('art_url') or item.get('fanart_url')
                   or item.get('thumb_url') or '')
            thumb = item.get('thumb_url') or art
            self.getControl(BACKDROP_ID).setImage(art)
            self.getControl(THUMB_ID).setImage(thumb)
            self.setFocusId(PLAY_ID)
        except RuntimeError:
            pass
        threading.Thread(target=self._countdown, daemon=True).start()

    def _countdown(self):
        for left in range(UP_NEXT_COUNTDOWN_SECONDS, 0, -1):
            if self._stop.wait(1):
                return
            try:
                self.getControl(COUNTDOWN_ID).setLabel(
                    i18n.tr(33562).format(left))
            except RuntimeError:
                return
        self.result = 'play'
        self._dismiss()

    def _dismiss(self):
        self._stop.set()
        self.close()

    def onClick(self, controlID):
        if controlID == PLAY_ID:
            self.result = 'play'
        elif controlID == CANCEL_ID:
            self.result = 'cancel'
        else:
            return
        self._dismiss()

    def onAction(self, action):
        if action.getId() in osd_menu._back_ids():
            self.result = 'cancel'
            self._dismiss()


_dialog = None


def _up_next_dialog(addon_path):
    global _dialog
    if _dialog is None:
        _dialog = AuraUpNextWindow(
            'AuraUpNext.xml', addon_path, 'Default', '1080i')
    return _dialog


def advance_via_up_next(addon_path):
    """Offer the Up Next card for the queued episode.

    Returns True when the next episode was launched (user confirm or
    countdown expiry) -- False on cancel / empty queue / unplayable
    item, in which case the caller re-opens Aura.
    """
    server, token, _, _ = osd_menu._playback_context()
    if not server or not token:
        # No playback context stored by Aura (external play, cleared
        # props): never chain on a leftover queue.
        return False
    item = peek_queue()
    if not item:
        return False
    dlg = _up_next_dialog(addon_path)
    dlg.item = item
    dlg.doModal()
    if dlg.result != 'play':
        return False
    pop_queue()
    item = _hydrate(item)
    url = _stream_url(item)
    if not url:
        return False
    try:
        # B2: the chained episode has its own intro/credits windows --
        # refresh the stored markers before the supervision loop polls.
        import plex_client
        osd_menu.store_markers(
            plex_client.PlexClient(server, token, timeout=5), item)
    except Exception:
        pass
    li = xbmcgui.ListItem(item.get('title') or '')
    try:
        import aura_detail
        aura_detail.AuraDetailWindow._apply_info_tags(li, item)
        aura_detail.apply_resume_point(li, item)
    except Exception:
        pass
    li.setMimeType('video/mp4')
    # The chained episode direct-plays again: a quality preset picked
    # mid-marathon only ever applied to the item it was chosen on.
    _home().setProperty(osd_menu.PROP_QUALITY, 'original')
    xbmc.Player().play(url, li)
    return True
