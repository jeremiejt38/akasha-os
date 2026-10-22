"""Akasha Aura — Plex-style item detail page (movies / episodes / shows).

Opened with doModal() from Aura when an item is picked (reco rows, Browse
grid, collections). Mirrors the Android TV detail screen measured in
docs/plex-parity/: right-weighted backdrop, clear logo or bold title,
meta line, rating chips, 3-line synopsis, action pills, media badges and
a circular Cast & Crew row.

For shows the same hero is kept and the bottom section becomes Plex's
"Show | Season N" tab strip with a seasons poster row (Show tab) or an
episodes landscape row (Season tab). Picking an episode swaps the dialog
into episode mode; Back restores the show view.

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
WATCHLIST_BUTTON_ID = 7103
CAST_LIST_ID = 7110
SEASON_STRIP_ID = 7120
EPISODES_LIST_ID = 7130
SEASONS_LIST_ID = 7140


def _set(window, prop, value):
    window.setProperty(prop, value or '')


class AuraDetailWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.item = {}
        self.watched = False
        self.mode = 'item'          # 'item' | 'show' | 'season'
        self._show_item = None      # saved show item while in episode mode
        self._seasons = []
        self._episodes = []
        self._next_episode = None
        self._active_season = 0     # 0 = "Show" overview tab

    def onInit(self):
        try:
            self._render()
        except Exception as e:
            xbmc.log('Akasha Aura Detail: init error: {}'.format(e), xbmc.LOGERROR)

    # ------------------------------------------------------------ render

    def _render(self):
        item = self.item
        self.watched = bool(item.get('watched'))

        _set(self, 'AuraDetailShowStrip',
             '1' if self.mode in ('show', 'season') else '')
        _set(self, 'AuraDetailSeasonsRow',
             '1' if self.mode == 'show' else '')
        _set(self, 'AuraDetailEpisodesRow',
             '1' if self.mode == 'season' else '')
        _set(self, 'AuraDetailCastRow',
             '1' if self.mode == 'item' and item.get('cast') else '')

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

        # Meta line: Plex shows "S1 - E4  ·  air date  ·  duration" for
        # episodes, "year  ·  duration  ·  genres" otherwise.
        parts = []
        if item.get('type') == 'episode':
            se = _season_episode_label(item)
            if se:
                parts.append(se.replace(' - ', ' • '))
            air = _fmt_air_date(item.get('originally_available_at'))
            if air:
                parts.append(air)
        elif item.get('year'):
            parts.append(str(item['year']))
        duration = _fmt_duration(item.get('duration_ms'))
        if duration:
            parts.append(duration)
        elif self.mode in ('show', 'season') and self._seasons:
            parts.append('{} saison{}'.format(
                len(self._seasons), 's' if len(self._seasons) > 1 else ''))
        if item.get('genres'):
            parts.append(', '.join(item['genres'][:3]))
        try:
            self.getControl(7020).setLabel('   '.join(parts))
        except RuntimeError:
            pass

        self._render_chips(item)

        # Synopsis + director
        try:
            self.getControl(7030).setText(item.get('summary') or '')
        except RuntimeError:
            pass
        director = ''
        if item.get('directors'):
            director = 'Réalisé par ' + ', '.join(item['directors'][:2])
        elif item.get('type') == 'episode' and item.get('show_title') \
                and not item.get('logo_url'):
            director = item['show_title']
        try:
            self.getControl(7040).setLabel(director)
        except RuntimeError:
            pass

        # Watch button
        try:
            self.getControl(WATCH_BUTTON_ID).setLabel(self._watch_label())
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

        # Bottom section
        if self.mode == 'item':
            self._render_cast()
            _set(self, 'AuraDetailSectionTitle',
                 '1' if item.get('cast') else '')
            try:
                self.getControl(7060).setLabel('Cast & Crew')
            except RuntimeError:
                pass
        elif self.mode == 'show':
            self._load_seasons()
            self._render_seasons()
        elif self.mode == 'season':
            self._render_episodes()

        self._sync_navigation()
        try:
            if self.mode in ('show', 'season'):
                self.setFocus(self.getControl(SEASON_STRIP_ID))
            else:
                self.setFocus(self.getControl(WATCH_BUTTON_ID))
        except RuntimeError:
            pass

    def _render_chips(self, item):
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
        for slot in range(3):
            _set(self, 'AuraDetailChip{}'.format(slot), '')
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

    def _render_cast(self):
        cast = self.item.get('cast') or []
        try:
            lst = self.getControl(CAST_LIST_ID)
            lst.reset()
            for member in cast[:20]:
                li = xbmcgui.ListItem(member['name'], member.get('role') or '')
                li.setArt({'thumb': member.get('thumb_url') or 'DefaultActor.png'})
                lst.addItem(li)
        except RuntimeError:
            pass

    def _load_seasons(self):
        if self._seasons or not self.client or not self.item.get('rating_key'):
            return
        try:
            self._seasons = self.client.show_seasons(self.item['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: seasons failed: {}'.format(e), xbmc.LOGERROR)
            self._seasons = []

    def _render_seasons(self):
        try:
            self.getControl(7060).setLabel('{} Saison{}'.format(
                len(self._seasons), 's' if len(self._seasons) > 1 else ''))
        except RuntimeError:
            pass
        _set(self, 'AuraDetailSectionTitle', '1' if self._seasons else '')
        # Top strip: Show | Saison 1 | Saison 2 | ...
        try:
            strip = self.getControl(SEASON_STRIP_ID)
            strip.reset()
            strip.addItem(xbmcgui.ListItem('Série'))
            for season in self._seasons:
                idx = season.get('index')
                strip.addItem(xbmcgui.ListItem('Saison {}'.format(
                    idx if idx is not None else season.get('title', '?'))))
        except RuntimeError:
            pass
        try:
            lst = self.getControl(SEASONS_LIST_ID)
            lst.reset()
            for season in self._seasons:
                li = xbmcgui.ListItem(season.get('title') or '')
                li.setArt({'poster': season.get('poster_url')
                                       or season.get('thumb_url') or ''})
                li.setProperty('watched', '1' if season.get('watched') else '0')
                lst.addItem(li)
        except RuntimeError:
            pass

    def _load_episodes(self, season_pos):
        season = self._seasons[season_pos]
        try:
            self._episodes = self.client.season_episodes(season['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: episodes failed: {}'.format(e), xbmc.LOGERROR)
            self._episodes = []

    def _render_episodes(self):
        season = self._seasons[self._active_season]
        try:
            self.getControl(7060).setLabel(season.get('title') or '')
        except RuntimeError:
            pass
        _set(self, 'AuraDetailSectionTitle', '1')
        try:
            lst = self.getControl(EPISODES_LIST_ID)
            lst.reset()
            for ep in self._episodes:
                num = ep.get('index')
                label = '{}. {}'.format(num, ep.get('title') or '') if num \
                    else (ep.get('title') or '')
                meta2 = _fmt_duration(ep.get('duration_ms'))
                li = xbmcgui.ListItem(label, meta2)
                li.setArt({'thumb': ep.get('landscape_url')
                                    or ep.get('thumb_url') or ''})
                if ep.get('progress'):
                    li.setProperty('PercentPlayed', str(int(ep['progress'] * 100)))
                li.setProperty('watched', '1' if ep.get('watched') else '0')
                lst.addItem(li)
        except RuntimeError:
            pass

    def _sync_navigation(self):
        """Rewire directional targets to whichever bottom row is visible."""
        bottom = {CAST_LIST_ID: 'item', SEASONS_LIST_ID: 'show',
                  EPISODES_LIST_ID: 'season'}
        try:
            watch = self.getControl(WATCH_BUTTON_ID)
            strip = self.getControl(SEASON_STRIP_ID)
            for cid, mode in bottom.items():
                row = self.getControl(cid)
                if mode == self.mode or (mode == 'item' and
                                         self.mode == 'item'):
                    watch.setNavigation(strip, row, watch, self.getControl(7103))
                    row.setNavigation(watch, row, row, row)
            if self.mode in ('show', 'season'):
                strip.setNavigation(strip, watch, strip, strip)
        except RuntimeError as e:
            xbmc.log('Akasha Aura Detail: nav sync failed: {}'.format(e),
                     xbmc.LOGWARNING)

    # ------------------------------------------------------------- input

    def onClick(self, controlID):
        if controlID == WATCH_BUTTON_ID:
            self._play()
        elif controlID == WATCHED_BUTTON_ID:
            self._toggle_watched()
        elif controlID == WATCHLIST_BUTTON_ID:
            # Plex watchlist sync is an online-account feature; surface it
            # once the connector proxies it.
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Watchlist indisponible', xbmcgui.NOTIFICATION_INFO, 1500)
        elif controlID == MORE_BUTTON_ID:
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Plus d\u2019options à venir', xbmcgui.NOTIFICATION_INFO, 1500)
        elif controlID == SEASON_STRIP_ID:
            self._on_strip_selected()
        elif controlID == SEASONS_LIST_ID:
            pos = self.getControl(SEASONS_LIST_ID).getSelectedPosition()
            if 0 <= pos < len(self._seasons):
                self._show_season(pos + 1)
        elif controlID == EPISODES_LIST_ID:
            self._open_episode()
        elif controlID == CAST_LIST_ID:
            pass

    def _on_strip_selected(self):
        try:
            pos = self.getControl(SEASON_STRIP_ID).getSelectedPosition()
        except RuntimeError:
            return
        if pos == 0:
            self.mode = 'show'
        else:
            self._show_season(pos)

    def _show_season(self, strip_pos):
        season_pos = strip_pos - 1
        if not (0 <= season_pos < len(self._seasons)):
            return
        self._active_season = season_pos
        self._load_episodes(season_pos)
        self.mode = 'season'
        _set(self, 'AuraDetailSeasonsRow', '')
        _set(self, 'AuraDetailEpisodesRow', '1')
        self._render_episodes()
        self._sync_navigation()

    def _open_episode(self):
        try:
            pos = self.getControl(EPISODES_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._episodes)):
            return
        # Swap into episode mode (same hero, playable item); Back returns here.
        self._show_item = self.item
        self.item = self._episodes[pos]
        self.mode = 'item'
        self._render()

    def _back_to_show(self):
        if self._show_item is None:
            return False
        self.item = self._show_item
        self._show_item = None
        self.mode = 'season' if self._episodes else 'show'
        self._render()
        return True

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            if not self._back_to_show():
                self.close()
            return
        super().onAction(action)

    # ------------------------------------------------------------ actions

    def _watch_label(self):
        item = self.item
        if self.mode in ('show', 'season'):
            nxt = self._find_next_episode()
            if nxt:
                label = 'Reprendre S{} E{}'.format(
                    nxt.get('season') or '?', nxt.get('index') or '?')
                if nxt.get('view_offset_ms') and nxt.get('duration_ms'):
                    left = _fmt_duration(
                        nxt['duration_ms'] - nxt['view_offset_ms'])
                    label += ' · {} restantes'.format(left)
                return label
            return 'Regarder'
        if item.get('view_offset_ms'):
            left_ms = (item.get('duration_ms') or 0) - item['view_offset_ms']
            return 'Reprendre · {} restantes'.format(_fmt_duration(left_ms))
        return 'Regarder'

    def _find_next_episode(self):
        if self._next_episode:
            return self._next_episode
        if not self.client:
            return None
        try:
            for ep in self.client.on_deck(limit=60):
                if ep.get('grandparent_rating_key') == self.item.get('rating_key'):
                    self._next_episode = ep
                    return ep
        except Exception as e:
            xbmc.log('Akasha Aura Detail: onDeck lookup failed: {}'.format(e),
                     xbmc.LOGWARNING)
        return None

    def _stream_url(self, item=None):
        item = item or self.item
        if not self.client or not item.get('part_key'):
            return None
        base = getattr(self.client, 'server_url', None)
        token = getattr(self.client, 'token', None)
        if not base or not token:
            return None
        return '{}{}?X-Plex-Token={}'.format(base, item['part_key'], token)

    def _play(self):
        item = self.item
        if self.mode in ('show', 'season'):
            item = self._find_next_episode()
            if not item and self._seasons:
                # Fall back to the very first episode, like Plex's Play.
                self._load_episodes(0)
                item = self._episodes[0] if self._episodes else None
            if not item:
                xbmcgui.Dialog().notification(
                    'Akasha Aura', 'Aucun épisode lisible',
                    xbmcgui.NOTIFICATION_INFO, 2000)
                return
        url = self._stream_url(item)
        if not url:
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Lecture indisponible (flux introuvable)',
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        li = xbmcgui.ListItem(item.get('title') or '')
        if item.get('view_offset_ms'):
            # Kodi honours resumetime/totaltime as start offset.
            li.setProperty('resumetime', str(float(item['view_offset_ms']) / 1000.0))
            li.setProperty('totaltime', str(float(item.get('duration_ms') or 0) / 1000.0))
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


def _season_episode_label(item):
    season, index = item.get('season'), item.get('index')
    if season is not None and index is not None:
        return 'S{} - E{}'.format(season, index)
    return ''


def _fmt_air_date(iso_date):
    """'2025-10-19' -> '19 oct. 2025' (short French month names)."""
    if not iso_date:
        return ''
    months = ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.',
              'août', 'sept.', 'oct.', 'nov.', 'déc.')
    try:
        year, month, day = iso_date[:10].split('-')
        return '{} {} {}'.format(int(day), months[int(month) - 1], year)
    except (ValueError, IndexError):
        return ''


def _fmt_duration(duration_ms):
    if not duration_ms:
        return ''
    minutes = int(duration_ms) // 60000
    hours, minutes = divmod(minutes, 60)
    if hours:
        return '{}h {}m'.format(hours, minutes)
    return '{}m'.format(minutes)
