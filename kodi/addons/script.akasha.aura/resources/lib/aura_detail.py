"""Akasha Aura — Plex-style item detail page (movies / episodes / clips).

Opened with doModal() from Aura when a playable item is picked (reco rows,
Browse grid, collections). Mirrors the Android TV detail screen measured
in docs/plex-parity/: right-weighted backdrop, clear logo or bold title,
meta line, rating chips, 3-line synopsis, action pills, media badges and
a circular Cast & Crew row.

The caller must set `item` (a divert_source normalised dict) and `client`
(a plex_client.PlexClient, or None) before doModal().
"""
import xbmc
import xbmcgui

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

WATCH_BUTTON_ID = 7100
WATCHED_BUTTON_ID = 7101
MORE_BUTTON_ID = 7102
CAST_LIST_ID = 7110


def _set(window, prop, value):
    window.setProperty(prop, value or '')


class AuraDetailWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.item = {}
        self.watched = False

    def onInit(self):
        try:
            self._render()
        except Exception as e:
            xbmc.log('Akasha Aura Detail: init error: {}'.format(e), xbmc.LOGERROR)

    def _render(self):
        item = self.item
        self.watched = bool(item.get('watched'))

        try:
            self.getControl(7001).setImage(
                item.get('fanart_url') or item.get('art_url') or '', useCache=False)
        except RuntimeError:
            pass
        _set(self, 'AuraDetailLogo', item.get('logo_url') or '')
        if item.get('logo_url'):
            try:
                self.getControl(7010).setImage(item['logo_url'], useCache=False)
            except RuntimeError:
                pass
        else:
            try:
                self.getControl(7011).setLabel(item.get('title') or '')
            except RuntimeError:
                pass

        # Meta line: year - duration - genres (Plex separator style)
        parts = []
        if item.get('year'):
            parts.append(str(item['year']))
        duration = _fmt_duration(item.get('duration_ms'))
        if duration:
            parts.append(duration)
        if item.get('genres'):
            parts.append(', '.join(item['genres'][:3]))
        try:
            self.getControl(7020).setLabel('   '.join(parts))
        except RuntimeError:
            pass

        # Rating chips, packed left-to-right with widths sized to the text
        chips = []
        if item.get('content_rating'):
            chips.append(item['content_rating'])
        if item.get('rating'):
            chips.append('{} {}'.format(
                _provider_label(item.get('rating_image')),
                _fmt_rating(item['rating'], item.get('rating_image'))).strip())
        if item.get('audience_rating'):
            chips.append('{} {}'.format(
                _provider_label(item.get('audience_rating_image')),
                _fmt_rating(item['audience_rating'],
                            item.get('audience_rating_image'))).strip())
        chip_x = 105
        for slot, text in enumerate(chips[:3]):
            width = 34 + len(text) * 11
            _set(self, 'AuraDetailChip{}'.format(slot), '1')
            try:
                self.getControl(7021 + slot * 2).setPosition(chip_x, 356)
                self.getControl(7021 + slot * 2).setWidth(width)
                self.getControl(7022 + slot * 2).setPosition(chip_x, 356)
                self.getControl(7022 + slot * 2).setWidth(width)
                self.getControl(7022 + slot * 2).setLabel(text)
            except RuntimeError:
                pass
            chip_x += width + 12

        # Synopsis + director
        try:
            self.getControl(7030).setText(item.get('summary') or '')
        except RuntimeError:
            pass
        director = ''
        if item.get('directors'):
            director = 'Réalisé par ' + ', '.join(item['directors'][:2])
        elif item.get('type') == 'episode' and item.get('show_title'):
            director = '{} — {} · E{}'.format(
                item['show_title'], item.get('season') or '?', item.get('index') or '?')
        try:
            self.getControl(7040).setLabel(director)
        except RuntimeError:
            pass

        # Watch button: "Reprendre" when partially watched, else "Regarder"
        label = 'Regarder'
        if item.get('view_offset_ms'):
            left_ms = (item.get('duration_ms') or 0) - item['view_offset_ms']
            label = 'Reprendre · {} restantes'.format(_fmt_duration(left_ms))
        try:
            self.getControl(WATCH_BUTTON_ID).setLabel(label)
        except RuntimeError:
            pass
        _set(self, 'AuraDetailWatched', '1' if self.watched else '0')

        # Media badges
        _set(self, 'AuraDetailVideoBadge', item.get('video_label') or '')
        try:
            self.getControl(7051).setLabel(item.get('video_label') or '')
        except RuntimeError:
            pass
        audio = item.get('audio_label') or ''
        if item.get('subtitle_label'):
            audio = (audio + ' · ' if audio else '') + item['subtitle_label']
        _set(self, 'AuraDetailAudioBadge', audio)
        try:
            self.getControl(7053).setLabel(audio)
        except RuntimeError:
            pass

        # Cast & Crew
        cast = item.get('cast') or []
        _set(self, 'AuraDetailHasCast', '1' if cast else '')
        try:
            lst = self.getControl(CAST_LIST_ID)
            lst.reset()
            for member in cast[:20]:
                li = xbmcgui.ListItem(member['name'], member.get('role') or '')
                li.setArt({'thumb': member.get('thumb_url') or 'DefaultActor.png'})
                lst.addItem(li)
        except RuntimeError:
            pass

        try:
            self.setFocus(self.getControl(WATCH_BUTTON_ID))
        except RuntimeError:
            pass

    def onClick(self, controlID):
        if controlID == WATCH_BUTTON_ID:
            self._play()
        elif controlID == WATCHED_BUTTON_ID:
            self._toggle_watched()
        elif controlID == 7103:
            # Plex watchlist sync is an online-account feature; surface it
            # once the connector proxies it.
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Watchlist indisponible', xbmcgui.NOTIFICATION_INFO, 1500)
        elif controlID == MORE_BUTTON_ID:
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Plus d\u2019options à venir', xbmcgui.NOTIFICATION_INFO, 1500)
        elif controlID == CAST_LIST_ID:
            pass

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)

    def _stream_url(self):
        item = self.item
        if not self.client or not item.get('part_key'):
            return None
        base = getattr(self.client, 'server_url', None)
        token = getattr(self.client, 'token', None)
        if not base or not token:
            return None
        return '{}{}?X-Plex-Token={}'.format(base, item['part_key'], token)

    def _play(self):
        url = self._stream_url()
        if not url:
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Lecture indisponible (flux introuvable)',
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        li = xbmcgui.ListItem(self.item.get('title') or '')
        if self.item.get('view_offset_ms'):
            # Kodi honours resumetime/totaltime as start offset.
            li.setProperty('resumetime', str(float(self.item['view_offset_ms']) / 1000.0))
            li.setProperty('totaltime', str(float(self.item.get('duration_ms') or 0) / 1000.0))
        li.setMimeType('video/mp4')
        self.close()
        xbmc.Player().play(url, li)

    def _toggle_watched(self):
        if not self.client or not self.item.get('rating_key'):
            return
        try:
            if self.watched:
                self.client.unscrobble(self.item['rating_key'])
            else:
                self.client.scrobble(self.item['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: watched toggle failed: {}'.format(e), xbmc.LOGERROR)
            return
        self.watched = not self.watched
        _set(self, 'AuraDetailWatched', '1' if self.watched else '0')


def _provider_label(rating_image):
    """Map Plex ratingImage URIs (imdb://..., themoviedb://...,
    rottentomatoes://...) to a short provider prefix like Plex shows."""
    img = rating_image or ''
    if 'imdb' in img:
        return 'IMDb'
    if 'themoviedb' in img:
        return 'TMDB'
    if 'rottentomatoes' in img:
        return 'RT'
    return ''


def _fmt_rating(value, rating_image):
    """Ratings are 0-10 on IMDb/TMDB, 0-100 (percent) on Rotten Tomatoes."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ''
    if 'rottentomatoes' in (rating_image or ''):
        return '{:.0f}%'.format(v)
    if v > 10:
        return '{:.0f}%'.format(v)
    return '{:.1f}'.format(v)


def _fmt_duration(duration_ms):
    if not duration_ms:
        return ''
    minutes = int(duration_ms) // 60000
    hours, minutes = divmod(minutes, 60)
    if hours:
        return '{}h {}m'.format(hours, minutes)
    return '{}m'.format(minutes)
