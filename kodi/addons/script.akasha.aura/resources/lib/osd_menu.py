#!/usr/bin/env python3
"""Plex-style OSD quick menus for the Akasha video player.

Two modes, opened from the VideoOSD circles via
RunScript(script.akasha.aura,osdmenu,<mode>):

- ``streams``: audio track + subtitle pickers combined, like Plex's
  bottom-right "speech" circle.
- ``quality``: playback settings like Plex's gear -- a quality preset list
  (Original = direct play, the rest re-mux through Plex's universal
  HLS transcoder) plus escape hatches to Kodi's own OSD settings.

The OSD menu is opened while a video plays, i.e. while the Aura process is
parked in default.py's wait-for-playback-end loop. It therefore runs as its
own RunScript invocation constructing a standalone WindowXMLDialog -- no
shared state with AuraWindow. What it needs from Aura (which Plex server,
token, and ratingKey back the playing item) is persisted by Aura at play
time into Window(10000) properties via store_playback_context().
"""
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import uuid

import xbmc
import xbmcaddon
import xbmcgui
import gui_guard
import i18n

try:
    ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
    sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))
except (AttributeError, RuntimeError):
    # Unit tests stub xbmcaddon without an Addon singleton; the helpers below
    # (store_playback_context, URL building) don't need the path anyway.
    ADDON_PATH = ''

PROP_SERVER = 'AuraPlaybackServer'
PROP_TOKEN = 'AuraPlaybackToken'
PROP_MAP = 'AuraPlaybackMap'
PROP_QUALITY = 'AuraPlaybackQuality'
# Serialized remaining-episode queue for the Up Next card (B1) --
# items after the one currently playing. up_next.py owns the read side.
PROP_QUEUE = 'AuraUpNextQueue'
PROP_ITEM = 'AuraPlaybackItem'
QUEUE_ITEM_FIELDS = (
    'rating_key', 'part_key', 'type', 'title', 'show_title', 'season',
    'index', 'duration_ms', 'view_offset_ms', 'thumb_url', 'art_url',
    'fanart_url', 'parent_rating_key', 'grandparent_rating_key',
    'video_label', 'audio_label', 'subtitle_label',
)
# Set around a quality-switch restart so default.py's silence detector does
# not mistake the stop/start gap for end-of-playback and reopen Aura on top.
PROP_SWITCHING = 'AuraSwitchingPlayback'
# Intro/credits marker windows fetched at play time (B2), keyed by
# ratingKey so a quality switch still resolves them after the restart.
PROP_MARKERS = 'AuraPlaybackMarkers'
# Plex-side chapters of the item about to play (B14). Kodi's JSON-RPC
# has no chapter enumeration, so the list comes from the server.
PROP_CHAPTERS = 'AuraPlaybackChapters'

QUALITY_PRESETS = [
    ('original', i18n.tr(33210), None, None),
    ('1080p8', '1080p - 8 Mbps', 8000, '1920x1080'),
    ('720p4', '720p - 4 Mbps', 4000, '1280x720'),
    ('720p2', '720p - 2 Mbps', 2000, '1280x720'),
    ('480p', '480p - 1.5 Mbps', 1500, '854x480'),
    ('360p', '360p - 0.7 Mbps', 700, '640x360'),
]

def _back_ids():
    # getattr fallbacks keep the module importable under the minimal xbmcgui
    # stub used by the unit tests (10=ACTION_PREVIOUS_MENU, 92=ACTION_NAV_BACK).
    return (getattr(xbmcgui, 'ACTION_PREVIOUS_MENU', 10),
            getattr(xbmcgui, 'ACTION_NAV_BACK', 92))


def _close_on_playback_end(dialog):
    """Self-close a transient playback dialog when the video stops.

    These dialogs outlive their purpose the moment playback ends; if one is
    still open while Kodi tears the GUI down for the Home transition, a
    queued input callback can hit the window's controls mid-destruction --
    that race is what SEGV'd ControlList::getSelectedPosition() on
    2026-10-29. Closing on our own terms first shrinks the window to ~0."""
    def worker():
        while xbmc.Player().isPlayingVideo():
            if getattr(dialog, '_closed', False):
                return
            xbmc.sleep(500)
        if getattr(dialog, '_closed', False):
            return
        dialog._closed = True
        try:
            dialog.close()
        except RuntimeError:
            pass

    threading.Thread(target=worker, daemon=True).start()


def _home():
    return xbmcgui.Window(10000)


def _jsonrpc(method, params=None):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        req['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req))).get('result') or {}
    except (ValueError, TypeError):
        return {}


def store_playback_context(client, items):
    """Persist what the OSD menus need to rebuild the playing item's URLs.

    `items` is every item queued for playback (current item first) --
    keyed by part_key so the currently playing file can be traced back
    to its ratingKey when the user changes quality mid-season-marathon.
    Everything after items[0] is serialized into PROP_QUEUE for the
    Up Next card (B1).
    """
    server = getattr(client, 'server_url', '') or ''
    token = getattr(client, 'token', '') or ''
    mapping = {}
    for it in items or []:
        part = it.get('part_key')
        rk = it.get('rating_key')
        if part and rk:
            mapping[part] = rk
    win = _home()
    win.setProperty(PROP_SERVER, server)
    win.setProperty(PROP_TOKEN, token)
    win.setProperty(PROP_MAP, json.dumps(mapping))
    win.setProperty(PROP_QUALITY, 'original')
    win.setProperty(PROP_QUEUE, json.dumps([
        {k: it.get(k) for k in QUEUE_ITEM_FIELDS if it.get(k) is not None}
        for it in (items or [])[1:]]))
    win.setProperty(PROP_ITEM, json.dumps(
        {k: (items or [{}])[0].get(k)
         for k in QUEUE_ITEM_FIELDS if (items or [{}])[0].get(k) is not None}))
    store_markers(client, (items or [None])[0])
    store_chapters(client, (items or [None])[0])


def store_markers(client, item):
    """Fetch and persist the intro/credits markers of the item about to
    play (B2). Best-effort: a server without marker support, an offline
    host or a connector client simply stores an empty map -- playback
    must never wait on this."""
    win = _home()
    markers = {}
    rk = (item or {}).get('rating_key')
    fetch = getattr(client, 'item_markers', None)
    if rk and fetch:
        try:
            result = fetch(rk)
            if isinstance(result, list) and result:
                markers[rk] = result
        except Exception as e:
            getattr(xbmc, 'log', lambda *a, **k: None)(
                'Akasha Aura OSD: marker fetch failed: {}'.format(e),
                getattr(xbmc, 'LOGWARNING', 2))
    win.setProperty(PROP_MARKERS, json.dumps(markers))


def store_chapters(client, item):
    """Fetch and persist the Plex chapters of the item about to play.

    Stored as [{'name', 'time'}] with `time` in seconds so the OSD list
    helpers stay shape-compatible; '' when the item has none so the
    OSD circle visibility can key on the property. Best-effort like
    store_markers: any failure stores empty."""
    win = _home()
    chapters = []
    rk = (item or {}).get('rating_key')
    fetch = getattr(client, 'item_chapters', None)
    if rk and fetch:
        try:
            server = getattr(client, 'server_url', '') or ''
            token = getattr(client, 'token', '') or ''
            # Plex chapter cards show the BIF index frame at the chapter
            # start: /library/parts/<id>/indexes/sd/<ms>.
            part_bits = ((item or {}).get('part_key') or '').split('/')
            part_id = part_bits[3] if len(part_bits) > 3 else ''
            chapters = [
                {'name': ch.get('name') or '',
                 'time': (ch.get('start_ms') or 0) / 1000.0,
                 'thumb': ('{}/library/parts/{}/indexes/sd/{}'
                           '?X-Plex-Token={}'.format(
                               server, part_id,
                               int(ch.get('start_ms') or 0), token)
                           if part_id and server and token else '')}
                for ch in fetch(rk) or []
            ]
        except Exception as e:
            getattr(xbmc, 'log', lambda *a, **k: None)(
                'Akasha Aura OSD: chapter fetch failed: {}'.format(e),
                getattr(xbmc, 'LOGWARNING', 2))
    win.setProperty(PROP_CHAPTERS, json.dumps(chapters) if chapters else '')


def _current_chapters():
    """Chapter list of the *currently* playing item, [] when unknown."""
    raw = _home().getProperty(PROP_CHAPTERS)
    if not raw:
        return []
    try:
        chapters = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return chapters if isinstance(chapters, list) else []


def _current_markers():
    """Marker list of the *currently* playing item, [] when unknown."""
    _server, _token, rating_key, _part = _playback_context()
    if not rating_key:
        return []
    try:
        markers = json.loads(_home().getProperty(PROP_MARKERS) or '{}')
    except (ValueError, TypeError):
        return []
    return markers.get(rating_key) or []


def _playback_context():
    """(server, token, rating_key, part_key) for the *currently* playing
    file, resolved from Window props + the playing URL itself."""
    win = _home()
    server = win.getProperty(PROP_SERVER)
    token = win.getProperty(PROP_TOKEN)
    playing = ''
    try:
        player = xbmc.Player()
        # getPlayingFile() raises "Kodi is not playing any file" when
        # idle; even caught, Kodi logs every raise -- isPlaying() keeps
        # the timeline reporter's 10s ticks out of kodi.log.
        if player.isPlaying():
            playing = player.getPlayingFile() or ''
    except RuntimeError:
        pass
    rating_key = part_key = ''
    if 'transcode' in playing:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(playing).query)
        path = (query.get('path') or [''])[0]
        rating_key = path.rsplit('/', 1)[-1] if '/metadata/' in path else ''
    else:
        part_key = urllib.parse.urlsplit(playing).path
        try:
            mapping = json.loads(win.getProperty(PROP_MAP) or '{}')
        except (ValueError, TypeError):
            mapping = {}
        rating_key = mapping.get(part_key, '')
    return server, token, rating_key, part_key


# The server's built-in client profiles declare NO transcode target at all
# ("No conversion profile found for protocol hls") -- Plex clients declare
# their own via this profile-extra, sent as a HEADER (putting the X-Plex-*
# params in the query string is ignored and returns 400).
_PROFILE_EXTRA = ('add-transcode-target(type=videoProfile&context=streaming'
                  '&protocol=hls&container=mpegts&videoCodec=h264'
                  '&audioCodec=aac,mp3&replace=true)')

_TRANSCODE_HEADERS = {
    'User-Agent': 'AkashaOSAura/1.0',
    'X-Plex-Client-Identifier': 'akasha-aura',
    'X-Plex-Client-Profile-Name': 'Generic',
    'X-Plex-Product': 'Plex for Kodi',
    'X-Plex-Platform': 'Linux',
    'X-Plex-Device': 'PC',
    'X-Plex-Client-Profile-Extra': _PROFILE_EXTRA,
}


def _transcode_playlist(server, token, rating_key, kbps, resolution,
                        offset_seconds=0):
    """Ask Plex's universal transcoder for an HLS session and return the
    directly playable playlist URL (Kodi needs no custom headers on it --
    only the start.m3u8 bootstrap wants the X-Plex-* headers, and the
    session-authenticated segments don't even need the token).
    Returns None when the server refuses the transcode."""
    q = {
        'hasMDE': '1',
        'mediaBufferSize': '50000',
        'path': '/library/metadata/{}'.format(rating_key),
        'mediaIndex': '0',
        'partIndex': '0',
        'protocol': 'hls',
        'fastSeek': '1',
        'directPlay': '0',
        'directStream': '0',
        'directStreamAudio': '0',
        'maxVideoBitrate': str(kbps),
        'videoResolution': resolution,
        'subtitleSize': '100',
        'audioBoost': '100',
        'session': uuid.uuid4().hex,
        'offset': str(int(offset_seconds)),
        'X-Plex-Token': token,
    }
    url = '{}/video/:/transcode/universal/start.m3u8?{}'.format(
        server, urllib.parse.urlencode(q))
    try:
        req = urllib.request.Request(url, headers=_TRANSCODE_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8', 'replace')
    except Exception as e:
        xbmc.log('Akasha Aura OSD: transcode bootstrap failed: {}'.format(e),
                 xbmc.LOGWARNING)
        return None
    # Master playlist -> single variant line "session/<id>/base/index.m3u8".
    variant = next((ln.strip() for ln in body.splitlines()
                    if ln.strip() and not ln.startswith('#')), '')
    if not variant:
        return None
    playlist = urllib.parse.urljoin(
        '{}/video/:/transcode/universal/'.format(server), variant)
    sep = '&' if '?' in playlist else '?'
    return '{}{}X-Plex-Token={}'.format(playlist, sep, token)


def _chapter_time_seconds(value):
    """JSON-RPC reports chapter times in plain seconds; Player 'time'
    fields are {hours,minutes,seconds,milliseconds} dicts. Accept both."""
    if isinstance(value, dict):
        return (value.get('hours', 0) * 3600 + value.get('minutes', 0) * 60
                + value.get('seconds', 0))
    return float(value or 0)


def _fmt_chapter_time(seconds):
    """'42:17' / '1:02:17' -- Plex-style chapter timestamp."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return '{}:{:02d}:{:02d}'.format(hours, minutes, secs)
    return '{}:{:02d}'.format(minutes, secs)


def _chapter_label(chapter, index):
    name = chapter.get('name') or i18n.tr(33566).format(index + 1)
    return '{} — {}'.format(
        name, _fmt_chapter_time(_chapter_time_seconds(chapter.get('time'))))


def chapter_entries(chapters, position_s):
    """(label, seconds, is_current) rows for the OSD chapters list.
    Current chapter = the last one starting at or before `position_s`
    (Plex highlights where you are in the chapter list)."""
    rows = [(ch, _chapter_time_seconds(ch.get('time')))
            for ch in chapters or []]
    current_idx = -1
    for i, (_, t) in enumerate(rows):
        if t <= position_s:
            current_idx = i
        else:
            break
    return [(_chapter_label(ch, i), t, i == current_idx)
            for i, (ch, t) in enumerate(rows)]


class AuraOsdMenuWindow(xbmcgui.WindowXMLDialog):
    """The floating picker. `mode` selects which Plex circle invoked it."""

    mode = 'streams'

    def onInit(self):
        self._closed = False
        self._actions = []
        lst = self.getControl(1000)
        lst.reset()
        if self.mode == 'quality':
            self.getControl(10).setLabel(i18n.tr(33019))
            self._build_quality(lst)
        elif self.mode == 'chapters':
            self.getControl(10).setLabel(i18n.tr(33565))
            self._build_chapters(lst)
        else:
            self.getControl(10).setLabel(i18n.tr(33200))
            self._build_streams(lst)
        gui_guard.focus(self, 1000)
        # Land on the first actionable row -- headers carry no action
        # and Plex never lets them take the selection pill.
        for i, action in enumerate(self._actions):
            if action:
                lst.selectItem(i)
                break
        _close_on_playback_end(self)

    # -- item construction ------------------------------------------------

    def _add(self, lst, label, selected=False, header=False, action=None):
        li = xbmcgui.ListItem(label)
        if selected:
            li.setProperty('selected', '1')
        if header:
            li.setProperty('header', '1')
        lst.addItem(li)
        self._actions.append(action)

    def _build_streams(self, lst):
        props = _jsonrpc('Player.GetProperties', {
            'playerid': 1,
            'properties': ['audiostreams', 'currentaudiostream',
                           'subtitles', 'currentsubtitle',
                           'subtitleenabled']})
        current_audio = (props.get('currentaudiostream') or {}).get('index')
        current_sub = (props.get('currentsubtitle') or {}).get('index')
        subs_on = bool(props.get('subtitleenabled'))

        self._add(lst, i18n.tr(33201), header=True)
        for stream in props.get('audiostreams') or []:
            idx = stream.get('index')
            name = stream.get('name') or i18n.tr(33204).format(idx + 1)
            lang = (stream.get('language') or '').upper()
            extra = stream.get('codec') or ''
            if stream.get('channels'):
                extra = (extra + ' ' + str(stream['channels']) + 'ch').strip()
            if lang and lang.lower() not in name.lower():
                name = '{} · {}'.format(lang, name)
            label = name if not extra else '{} ({})'.format(name, extra)
            self._add(lst, label, selected=(idx == current_audio),
                      action=('audio', idx))

        self._add(lst, i18n.tr(33115), header=True)
        self._add(lst, i18n.tr(33202), selected=not subs_on,
                  action=('sub', 'off'))
        for sub in props.get('subtitles') or []:
            idx = sub.get('index')
            name = sub.get('name') or sub.get('language') or i18n.tr(33204).format(idx + 1)
            self._add(lst, name,
                      selected=(subs_on and idx == current_sub),
                      action=('sub', idx))
        if not props.get('audiostreams') and not props.get('subtitles'):
            self._add(lst, i18n.tr(33203), header=True)

    def _build_quality(self, lst):
        current = _home().getProperty(PROP_QUALITY) or 'original'
        _, _, rating_key, _ = _playback_context()

        # Plex's gear sheet leads with track pickers (audio + subtitles)
        # -- rebuild the same dialog in streams mode on click.
        self._add(lst, i18n.tr(33200), action=('mode', 'streams'))

        self._add(lst, i18n.tr(33205), header=True)
        for pid, label, kbps, res in QUALITY_PRESETS:
            self._add(lst, label, selected=(pid == current),
                      action=('quality', pid, kbps, res))
        if not rating_key:
            self._add(lst, i18n.tr(33206), header=True)

        self._add(lst, i18n.tr(33207), header=True)
        self._add(lst, i18n.tr(33208),
                  action=('builtin', 'osdsubtitlesettings'))
        self._add(lst, i18n.tr(33209),
                  action=('builtin', 'osdvideosettings'))
        self._add(lst, i18n.tr(33211),
                  action=('builtin', 'osdaudiosettings'))

    def _build_chapters(self, lst):
        """Chapters of the playing item (B14): title + timestamp rows,
        current chapter selected -- seek on pick like Plex's list.
        The list itself comes from the Plex metadata persisted by
        store_chapters (Kodi's JSON-RPC has no chapter enumeration)."""
        try:
            position = xbmc.Player().getTime()
        except RuntimeError:
            props = _jsonrpc('Player.GetProperties', {
                'playerid': 1, 'properties': ['time']})
            position = _chapter_time_seconds(props.get('time'))
        entries = chapter_entries(_current_chapters(), position)
        if not entries:
            self._add(lst, i18n.tr(33567), header=True)
            return
        for label, seconds, current in entries:
            self._add(lst, label, selected=current,
                      action=('chapter', seconds))

    # -- actions ----------------------------------------------------------

    def onClick(self, control_id):
        if control_id != 1000 or self._closed:
            return
        pos = gui_guard.selpos(self, 1000)
        if not (0 <= pos < len(self._actions)) or not self._actions[pos]:
            return
        kind = self._actions[pos][0]
        if kind == 'audio':
            _jsonrpc('Player.SetAudioStream',
                     {'playerid': 1, 'stream': self._actions[pos][1]})
            self._closed = True
            self.close()
        elif kind == 'sub':
            _jsonrpc('Player.SetSubtitle', {
                'playerid': 1, 'subtitle': self._actions[pos][1],
                'enable': True})
            self._closed = True
            self.close()
        elif kind == 'builtin':
            self._closed = True
            self.close()
            xbmc.executebuiltin(
                'ActivateWindow({})'.format(self._actions[pos][1]))
        elif kind == 'chapter':
            self._closed = True
            self.close()
            try:
                xbmc.Player().seekTime(float(self._actions[pos][1]))
            except RuntimeError:
                pass
        elif kind == 'quality':
            _, pid, kbps, res = self._actions[pos]
            self._closed = True
            self.close()
            self._switch_quality(pid, kbps, res)
        elif kind == 'mode':
            self.mode = self._actions[pos][1]
            lst = self.getControl(1000)
            lst.reset()
            self._actions = []
            if self.mode == 'streams':
                self.getControl(10).setLabel(i18n.tr(33200))
                self._build_streams(lst)
            for i, a in enumerate(self._actions):
                if a:
                    lst.selectItem(i)
                    break

    def onAction(self, action):
        if action.getId() in _back_ids():
            self._closed = True
            self.close()

    def _switch_quality(self, preset_id, kbps, resolution):
        """Restart the stream at the chosen quality, keeping position."""
        server, token, rating_key, part_key = _playback_context()
        if not server or not token or not rating_key:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33130),
                xbmcgui.NOTIFICATION_INFO, 2500)
            return
        win = _home()
        win.setProperty(PROP_SWITCHING, '1')
        try:
            player = xbmc.Player()
            position = player.getTime()
            li = xbmcgui.ListItem(xbmc.getInfoLabel('VideoPlayer.Title') or '')
            if preset_id == 'original' and part_key:
                url = '{}{}?X-Plex-Token={}'.format(server, part_key, token)
                li.setMimeType('video/mp4')
            elif preset_id == 'original':
                # part_key lost (transcode chain edge case): stay transcoded
                # at max bitrate rather than failing outright.
                url = _transcode_playlist(
                    server, token, rating_key, 20000, '1920x1080',
                    offset_seconds=position)
            else:
                url = _transcode_playlist(
                    server, token, rating_key, kbps, resolution,
                    offset_seconds=position)
                li.setMimeType('application/vnd.apple.mpegurl')
            if not url:
                xbmcgui.Dialog().notification(
                    'Akasha Aura', i18n.tr(33122),
                    xbmcgui.NOTIFICATION_INFO, 2500)
                return
            player.play(url, li)
            waited = 0
            while not xbmc.Player().isPlayingVideo() and waited < 12000:
                xbmc.sleep(250)
                waited += 250
            # Direct-play restarts from zero: restore position explicitly
            # (the transcode path already starts at `offset` server-side).
            if (preset_id == 'original' and position > 5
                    and xbmc.Player().isPlayingVideo()):
                player.seekTime(position)
            win.setProperty(PROP_QUALITY, preset_id)
        finally:
            win.setProperty(PROP_SWITCHING, '')


def _queue_items():
    """[current item] + queued episodes, read from the playback props."""
    win = _home()
    try:
        current = json.loads(win.getProperty(PROP_ITEM) or '{}')
    except (ValueError, TypeError):
        current = {}
    try:
        rest = json.loads(win.getProperty(PROP_QUEUE) or '[]')
    except (ValueError, TypeError):
        rest = []
    items = [current] if current else []
    items += [it for it in rest if isinstance(it, dict)]
    return items


def _queue_subtitle(item):
    """'S7 • E13 • Show title' -- Plex's secondary line under queue cards."""
    season, index, show = (item.get('season'), item.get('index'),
                           item.get('show_title'))
    if season is not None and index is not None:
        head = 'S{} • E{}'.format(season, index)
        return '{} • {}'.format(head, show) if show else head
    return show or ''


class AuraOsdQueueWindow(xbmcgui.WindowXMLDialog):
    """Down-on-OSD overlay: chapter thumbnails + the play queue, exactly
    like Plex Android TV's bottom sheet. The video keeps playing behind
    it; selecting a chapter seeks, selecting a queued episode jumps."""

    def onInit(self):
        self._closed = False
        self._chapters = _current_chapters()
        self._queue = _queue_items()
        if self._chapters:
            self.setProperty('haschapters', '1')
            try:
                position = xbmc.Player().getTime()
            except RuntimeError:
                position = 0
            entries = chapter_entries(self._chapters, position)
            lst = self.getControl(1001)
            for (label, _seconds, _current), ch in zip(
                    entries, self._chapters):
                name, _, stamp = label.rpartition(' — ')
                li = xbmcgui.ListItem(name or label, stamp)
                if ch.get('thumb'):
                    li.setArt({'thumb': ch['thumb'], 'icon': ch['thumb']})
                lst.addItem(li)
        qlst = self.getControl(1002)
        for i, it in enumerate(self._queue):
            li = xbmcgui.ListItem(it.get('title') or '',
                                  _queue_subtitle(it))
            art = (it.get('thumb_url') or it.get('art_url')
                   or it.get('fanart_url') or '')
            if art:
                li.setArt({'thumb': art, 'icon': art})
            if i == 0:
                li.setProperty('playing', '1')
            qlst.addItem(li)
        if not self._chapters and not self._queue:
            # Nothing to show: an open-but-unfocusable dialog is exactly the
            # state that logged "Control 1002 has been asked to focus, but
            # it can't" before the teardown SEGV -- bail immediately.
            self._closed = True
            self.close()
            return
        gui_guard.focus(self, 1001 if self._chapters else 1002)
        _close_on_playback_end(self)

    def onClick(self, control_id):
        if self._closed:
            return
        if control_id == 1001:
            pos = gui_guard.selpos(self, 1001)
            if 0 <= pos < len(self._chapters):
                self._closed = True
                self.close()
                try:
                    xbmc.Player().seekTime(float(
                        _chapter_time_seconds(
                            self._chapters[pos].get('time'))))
                except RuntimeError:
                    pass
        elif control_id == 1002:
            pos = gui_guard.selpos(self, 1002)
            self._closed = True
            self.close()
            if pos > 0:
                self._play_queue_index(pos)

    def onAction(self, action):
        if self._closed:
            return
        if action.getId() in _back_ids():
            self._closed = True
            self.close()
        elif action.getId() == getattr(xbmcgui, 'ACTION_MOVE_UP', 3):
            try:
                focus = self.getFocusId()
            except RuntimeError:
                return
            if focus == 1002 and not self._chapters:
                self._closed = True
                self.close()
            elif (focus == 1001
                    and gui_guard.selpos(self, 1001) == 0):
                self._closed = True
                self.close()

    def _play_queue_index(self, pos):
        """Jump to queue[pos] (queue[0] is the playing item): the props
        are rewritten exactly like the Up Next advance does, then the
        part URL is played directly."""
        win = _home()
        server, token, _, _ = _playback_context()
        item = self._queue[pos] if pos < len(self._queue) else None
        if not item or not server or not token:
            return
        rest = self._queue[pos + 1:]
        win.setProperty(PROP_QUEUE, json.dumps(rest))
        win.setProperty(PROP_ITEM, json.dumps(item))
        try:
            import up_next
            item = up_next._hydrate(item)
        except Exception:
            pass
        part = item.get('part_key')
        if not part:
            return
        joiner = '&' if '?' in part else '?'
        url = '{}{}{}X-Plex-Token={}'.format(server, part, joiner, token)
        win.setProperty(PROP_SWITCHING, '1')
        try:
            import plex_client
            client = plex_client.PlexClient(server, token, timeout=5)
            store_markers(client, item)
            store_chapters(client, item)
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
        win.setProperty(PROP_QUALITY, 'original')
        try:
            player = xbmc.Player()
            player.play(url, li)
            waited = 0
            while not player.isPlayingVideo() and waited < 12000:
                xbmc.sleep(250)
                waited += 250
        finally:
            win.setProperty(PROP_SWITCHING, '')
