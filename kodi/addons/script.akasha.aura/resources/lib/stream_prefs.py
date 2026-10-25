"""Akasha Aura — per-show audio/subtitle stream continuity (B15).

Plex remembers which audio and subtitle tracks the viewer picked on a
series: the next episode of the same show starts with the same tracks
instead of falling back to the file defaults. Stream *indexes* are
unstable across episodes (different files, different orders), so the
selection is persisted by language+name and re-matched against the new
file's stream list on every playback start.

Streams are read through JSON-RPC `Player.GetProperties` (audiostreams /
currentaudiostream / subtitles / currentsubtitle / subtitlesenabled) —
the only Kodi API exposing the active selection. Preference key is the
grandparent rating key (whole show) falling back to the item's own
rating key (movies).
"""

import json

import xbmc
import xbmcgui

PREF_KEY = 'stream.pref.{}'
PROP_ITEM = 'AuraPlaybackItem'

_STREAM_PROPS = {
    'playerid': 1,
    'properties': ['audiostreams', 'currentaudiostream',
                   'subtitles', 'currentsubtitle', 'subtitlesenabled'],
}


def _home():
    return xbmcgui.Window(10000)


def _rpc(method, params=None):
    try:
        resp = json.loads(xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0', 'id': 1,
            'method': method, 'params': params or {},
        })))
    except Exception as e:
        xbmc.log('Akasha Aura StreamPrefs: RPC {} failed: {}'.format(
            method, e), xbmc.LOGWARNING)
        return {}
    if not isinstance(resp, dict):
        return {}
    return resp.get('result') or {}


def current_item():
    """The QUEUE_ITEM_FIELDS dict of the currently playing item."""
    try:
        item = json.loads(_home().getProperty(PROP_ITEM) or '{}')
        return item if isinstance(item, dict) else {}
    except (ValueError, TypeError):
        return {}


def _pref_key(item):
    return PREF_KEY.format(
        item.get('grandparent_rating_key') or item.get('rating_key') or '')


def capture_selection():
    """Snapshot the player's active audio/subtitle streams.

    Returns None when nothing meaningful is playing (never persist an
    empty snapshot over a good one)."""
    props = _rpc('Player.GetProperties', _STREAM_PROPS)
    audio = props.get('currentaudiostream') or {}
    if not audio:
        return None
    sub = props.get('currentsubtitle') or {}
    return {
        'audio': {k: audio.get(k)
                  for k in ('index', 'language', 'name', 'codec')
                  if audio.get(k) is not None},
        'sub': {k: sub.get(k)
                for k in ('index', 'language', 'name')
                if sub.get(k) is not None},
        'sub_enabled': bool(props.get('subtitlesenabled')),
    }


def persist_selection(addon, item, selection):
    """Write the latest captured selection for `item`'s show."""
    key = _pref_key(item or {})
    if key != PREF_KEY.format('') and selection:
        try:
            addon.setSetting(key, json.dumps(selection))
        except Exception:
            pass


def _pick_stream(streams, saved):
    """Index of the stream matching the saved language+name, else just
    the language. Streams shift between files, so Plex's 'same track'
    means same language/track identity, not same index."""
    if not saved or not streams:
        return None
    lang = (saved.get('language') or '').lower()
    name = saved.get('name') or ''
    if not lang:
        return None
    for stream in streams:
        if (stream.get('language') or '').lower() == lang \
                and (stream.get('name') or '') == name:
            return stream.get('index')
    for stream in streams:
        if (stream.get('language') or '').lower() == lang:
            return stream.get('index')
    return None


def apply_saved_streams(addon, item):
    """Re-apply the stored tracks for `item`'s show on the new file.

    Called once per playback start, after the player has enumerated its
    streams. Returns True when any stream was switched."""
    key = _pref_key(item or {})
    if key == PREF_KEY.format(''):
        return False
    try:
        prefs = json.loads(addon.getSetting(key) or '')
    except Exception:
        return False
    if not isinstance(prefs, dict) or not prefs:
        return False
    props = _rpc('Player.GetProperties', _STREAM_PROPS)
    changed = False
    audio_idx = _pick_stream(props.get('audiostreams') or [],
                             prefs.get('audio'))
    if audio_idx is not None and audio_idx != \
            (props.get('currentaudiostream') or {}).get('index'):
        _rpc('Player.SetAudioStream',
             {'playerid': 1, 'stream': audio_idx})
        changed = True
    if prefs.get('sub_enabled'):
        sub_idx = _pick_stream(props.get('subtitles') or [],
                               prefs.get('sub'))
        if sub_idx is not None and sub_idx != \
                (props.get('currentsubtitle') or {}).get('index'):
            _rpc('Player.SetSubtitle',
                 {'playerid': 1, 'subtitle': sub_idx, 'enable': True})
            changed = True
    elif (props.get('currentsubtitle') or {}).get('index') is not None:
        _rpc('Player.SetSubtitle',
             {'playerid': 1, 'subtitle': 'off', 'enable': False})
        changed = True
    return changed
