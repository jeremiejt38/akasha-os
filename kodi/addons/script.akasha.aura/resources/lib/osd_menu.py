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
import urllib.parse
import urllib.request
import uuid

import xbmc
import xbmcaddon
import xbmcgui
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
# Set around a quality-switch restart so default.py's silence detector does
# not mistake the stop/start gap for end-of-playback and reopen Aura on top.
PROP_SWITCHING = 'AuraSwitchingPlayback'

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

    `items` is every item queued for playback (playlist included) -- keyed by
    part_key so the currently playing file can be traced back to its
    ratingKey when the user changes quality mid-season-marathon.
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


def _playback_context():
    """(server, token, rating_key, part_key) for the *currently* playing
    file, resolved from Window props + the playing URL itself."""
    win = _home()
    server = win.getProperty(PROP_SERVER)
    token = win.getProperty(PROP_TOKEN)
    playing = ''
    try:
        playing = xbmc.Player().getPlayingFile() or ''
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


class AuraOsdMenuWindow(xbmcgui.WindowXMLDialog):
    """The floating picker. `mode` selects which Plex circle invoked it."""

    mode = 'streams'

    def onInit(self):
        self._actions = []
        lst = self.getControl(1000)
        lst.reset()
        if self.mode == 'quality':
            self.getControl(10).setLabel(i18n.tr(33019))
            self._build_quality(lst)
        else:
            self.getControl(10).setLabel(i18n.tr(33200))
            self._build_streams(lst)
        self.setFocusId(1000)

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

    # -- actions ----------------------------------------------------------

    def onClick(self, control_id):
        if control_id != 1000:
            return
        pos = self.getControl(1000).getSelectedPosition()
        if not (0 <= pos < len(self._actions)) or not self._actions[pos]:
            return
        kind = self._actions[pos][0]
        if kind == 'audio':
            _jsonrpc('Player.SetAudioStream',
                     {'playerid': 1, 'stream': self._actions[pos][1]})
            self.close()
        elif kind == 'sub':
            _jsonrpc('Player.SetSubtitle', {
                'playerid': 1, 'subtitle': self._actions[pos][1],
                'enable': True})
            self.close()
        elif kind == 'builtin':
            self.close()
            xbmc.executebuiltin(
                'ActivateWindow({})'.format(self._actions[pos][1]))
        elif kind == 'quality':
            _, pid, kbps, res = self._actions[pos]
            self.close()
            self._switch_quality(pid, kbps, res)

    def onAction(self, action):
        if action.getId() in _back_ids():
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
