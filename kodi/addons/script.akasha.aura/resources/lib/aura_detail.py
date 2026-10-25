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
import time

import xbmc
import xbmcgui
import i18n

import osd_menu

ACTION_MOVE_LEFT = 1
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PREVIOUS_MENU = 10
ACTION_CONTEXT_MENU = 117
ACTION_NAV_BACK = 92


def episode_queue_items(client, item):
    """Episodes to chain after `item`: the current one plus every later
    episode in its season -- Plex-style continuous playback built on a
    Kodi video playlist. Returns None when chaining doesn't apply (movie,
    missing season key, lookup failure, or a single-episode queue)."""
    if item.get('type') != 'episode' or not item.get('parent_rating_key'):
        return None
    if not client:
        return None
    try:
        eps = client.season_episodes(item['parent_rating_key'])
    except Exception as e:
        xbmc.log('Akasha Aura Detail: season queue lookup failed: {}'.format(e),
                 xbmc.LOGWARNING)
        return None
    if not eps:
        return None
    for i, ep in enumerate(eps):
        if ep.get('rating_key') and ep.get('rating_key') == item.get('rating_key'):
            return eps[i:]
    idx = item.get('index')
    if idx is not None:
        for i, ep in enumerate(eps):
            if ep.get('index') == idx:
                return eps[i:]
    return None


def apply_resume_point(li, item, start_over=False):
    """Set the Kodi 20+ resume point (resumetime/totaltime properties are
    deprecated) when the item carries a Plex view offset."""
    if not item.get('view_offset_ms') or start_over:
        return
    try:
        li.getVideoInfoTag().setResumePoint(
            float(item['view_offset_ms']) / 1000.0,
            float(item.get('duration_ms') or 0) / 1000.0)
    except Exception:
        li.setProperty('resumetime', str(float(item['view_offset_ms']) / 1000.0))
        li.setProperty('totaltime', str(float(item['duration_ms'] or 0) / 1000.0))

WATCH_BUTTON_ID = 7100
WATCHED_BUTTON_ID = 7101
MORE_BUTTON_ID = 7102
WATCHLIST_BUTTON_ID = 7103
RATE_BUTTON_ID = 7104
RESTART_BUTTON_ID = 7106
EXTRAS_BUTTON_ID = 7109
CAST_LIST_ID = 7110
SEASON_STRIP_ID = 7120
EPISODES_LIST_ID = 7130
SEASONS_LIST_ID = 7140

# "Plus d'actions" side panel entries (Plex More Actions sheet).
MORE_SUBTITLES_ID = 7200
MORE_LIST_ID = 7201
MORE_PLAYLIST_ID = 7202
MORE_MANAGE_ID = 7203
MORE_FILE_INFO_ID = 7204
MORE_WAYS_ID = 7205
MORE_RELATED_ID = 7206
MORE_GO_SHOW_ID = 7208
MORE_VERSION_ID = 7209
MORE_PANEL_FIRST_ID = MORE_SUBTITLES_ID
# Cloud-only Plex entries (List, Playlist, Manage, More Ways) are hidden in
# the skin; only Subtitles, File Info and Similar Titles remain reachable.
MORE_PANEL_IDS = (MORE_SUBTITLES_ID, MORE_FILE_INFO_ID, MORE_RELATED_ID,
                  MORE_GO_SHOW_ID, MORE_VERSION_ID)

ACTION_ROW_IDS = (WATCH_BUTTON_ID, RESTART_BUTTON_ID, EXTRAS_BUTTON_ID,
                  WATCHLIST_BUTTON_ID, RATE_BUTTON_ID, WATCHED_BUTTON_ID,
                  MORE_BUTTON_ID)
# light/dark icon overlay pairs that ride on top of each action button
ACTION_ICON_OVERLAYS = {
    WATCH_BUTTON_ID: (7087, 7088, 7089, 7090),
    RESTART_BUTTON_ID: (7107, 7108),
    EXTRAS_BUTTON_ID: (7111, 7112),
    WATCHLIST_BUTTON_ID: (7092, 7093),
    RATE_BUTTON_ID: (7099, 7105),
    WATCHED_BUTTON_ID: (7094, 7095, 7096),
    MORE_BUTTON_ID: (7097, 7098),
}
ACTION_ROW_TOP = 576
ACTION_ROW_LEFT = 105
ACTION_ROW_GAP = 32
ACTION_CIRCLE_W = 64


def _set(window, prop, value):
    window.setProperty(prop, value or '')


class AuraDetailWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.item = {}
        self.watched = False
        self.mode = 'item'          # 'item' | 'show' | 'season'
        # WindowXMLDialog ctor arg 2 is the script path -- kept so the
        # person page can be opened as a sub-dialog.
        self.addon_path = args[1] if len(args) > 1 else ''
        self._show_item = None      # saved show item while in episode mode
        self._seasons = []
        self._episodes = []
        self._extras = []
        self._extras_key = None
        self._activity_key = None
        self._activity_date = ''
        self._next_episode = None
        self._active_season = 0     # 0 = "Show" overview tab
        self._pending_season_index = None  # season card entry point
        self.exit_to_sidebar = False

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
        # Plex tints the page field with the item's UltraBlurColors; reuse
        # the top-left palette color for the dim layer, neutral fallback.
        try:
            dim = self.getControl(7002)
            tint = str((item.get('blur_colors') or {}).get('topLeft') or '')
            dim.setColorDiffuse('73' + tint.lstrip('#')[-6:].upper()
                                if tint else '7310131A')
        except (RuntimeError, AttributeError):
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
        summary = item.get('summary') or ''
        if len(summary) > 240:
            summary = summary[:240].rsplit(' ', 1)[0].rstrip(',. ') + '...'
        try:
            self.getControl(7030).setText(summary)
        except RuntimeError:
            pass
        director = ''
        if item.get('directors'):
            director = i18n.tr(33117).format(', '.join(item['directors'][:2]))
        elif item.get('type') == 'episode' and item.get('show_title') \
                and not item.get('logo_url'):
            director = item['show_title']
        try:
            self.getControl(7040).setLabel(director)
        except RuntimeError:
            pass

        # Bonus clips (trailer, deleted scenes...): Plex shows a trailer
        # button whenever /extras answers -- fetched once per item.
        if self._extras_key != item.get('rating_key'):
            self._extras_key = item.get('rating_key')
            self._extras = []
            if self.client and item.get('rating_key'):
                try:
                    self._extras = self.client.item_extras(
                        item['rating_key'])
                except Exception as e:
                    xbmc.log('Akasha Aura Detail: extras failed: {}'.format(e),
                             xbmc.LOGWARNING)
        _set(self, 'AuraDetailExtras', '1' if self._extras else '')

        # "Vous l'avez regarde le..." (B6): Plex's "Activity by you" hint
        # from the server watch history -- one fetch per item.
        if self._activity_key != item.get('rating_key'):
            self._activity_key = item.get('rating_key')
            self._activity_date = ''
            watch_history = getattr(self.client, 'watch_history', None)
            if watch_history and item.get('rating_key'):
                try:
                    for entry in watch_history(limit=50):
                        if str(entry.get('rating_key')) == str(item['rating_key']) \
                                and entry.get('viewed_at'):
                            self._activity_date = i18n.fmt_air_date(
                                time.strftime('%Y-%m-%d',
                                              time.localtime(entry['viewed_at'])))
                            break
                except Exception as e:
                    xbmc.log('Akasha Aura Detail: watch history failed: {}'
                             .format(e), xbmc.LOGWARNING)
        _set(self, 'AuraDetailActivity',
             i18n.tr(33578).format(self._activity_date)
             if self._activity_date else '')

        # Plex's 'Go to Show' entry (B11): episodes only.
        _set(self, 'AuraDetailGoToShow',
             '1' if (item.get('type') == 'episode'
                     and item.get('grandparent_rating_key')) else '')
        # Plex's 'Play Version' entry (B12): multi-version items only.
        _set(self, 'AuraDetailVersions',
             '1' if len(item.get('versions') or []) > 1 else '')

        # Action row: labels live on the buttons themselves (invisible
        # while unfocused via transparent textcolor, dark on the white
        # pill when focused) and _sync_action_row() lays the row out --
        # the focused circle expands into a labeled pill, Plex-style.
        restart = bool(self._playable_item() and
                       self._playable_item().get('view_offset_ms'))
        _set(self, 'AuraDetailRestart', '1' if restart else '')
        _set(self, 'AuraDetailWatched', '1' if self.watched else '0')
        # Plex draws a resume ring instead of the play glyph when the
        # item carries a resume offset.
        _set(self, 'AuraDetailResume', '1' if restart else '')
        self._set_action_labels()
        self._sync_action_row()

        # Media badges, right-packed like Plex (video, audio, subtitles)
        video = item.get('video_label') or ''
        audio = item.get('audio_label') or ''
        subs = item.get('subtitle_label') or ''
        badge_x = 1890
        for text, bg_id, lb_id, ic_id in ((subs, 7054, 7055, 7057),
                                          (audio, 7052, 7053, 7056),
                                          (video, 7050, 7051, 0)):
            if not text:
                continue
            ic_w = 36 if ic_id else 0
            w = 34 + len(text) * 11 + ic_w
            badge_x -= w
            try:
                self.getControl(bg_id).setPosition(badge_x, 584)
                self.getControl(bg_id).setWidth(w)
                self.getControl(lb_id).setPosition(badge_x + ic_w, 584)
                self.getControl(lb_id).setWidth(w - ic_w)
                self.getControl(lb_id).setLabel(text)
                if ic_id:
                    self.getControl(ic_id).setPosition(badge_x + 12, 592)
            except RuntimeError:
                pass
            badge_x -= 14
        _set(self, 'AuraDetailVideoBadge', '1' if video else '')
        _set(self, 'AuraDetailAudioBadge', '1' if audio else '')
        _set(self, 'AuraDetailSubsBadge', '1' if subs else '')

        # Bottom section
        if self.mode == 'item':
            self._render_cast()
            _set(self, 'AuraDetailSectionTitle',
                 '1' if item.get('cast') else '')
            try:
                self.getControl(7060).setLabel(i18n.tr(33100))
            except RuntimeError:
                pass
        elif self.mode == 'show':
            self._load_seasons()
            self._render_seasons()
            # Opened from a season card: jump straight into that season's
            # tab, like Plex TV opening a recently-added season.
            pending = self._pending_season_index
            self._pending_season_index = None
            if pending is not None:
                for pos, season in enumerate(self._seasons):
                    if season.get('index') == pending:
                        try:
                            self.getControl(SEASON_STRIP_ID).selectItem(pos + 1)
                        except RuntimeError:
                            pass
                        self._show_season(pos + 1)
                        break
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
        # Each chip: (text, provider icon or ''). Plex draws a provider
        # glyph (IMDb / RT splat / popcorn / TMDB) before the value; text
        # prefixes are only the fallback when no icon is known.
        chips = []
        if item.get('content_rating'):
            chips.append((_age_label(item['content_rating']), ''))
        if item.get('rating'):
            chips.append(self._rating_chip(item['rating'],
                                           item.get('rating_image')))
        if item.get('audience_rating'):
            chips.append(self._rating_chip(item['audience_rating'],
                                           item.get('audience_rating_image'),
                                           audience=True))
        chip_x = 105
        for slot in range(3):
            _set(self, 'AuraDetailChip{}'.format(slot), '')
            _set(self, 'AuraDetailChipIcon{}'.format(slot), '')
        for slot, (text, icon) in enumerate(chips[:3]):
            width = 34 + len(text) * 11 + (30 if icon else 0)
            _set(self, 'AuraDetailChip{}'.format(slot), '1')
            try:
                self.getControl(7021 + slot * 2).setPosition(chip_x, 356)
                self.getControl(7021 + slot * 2).setWidth(width)
                if icon:
                    self.getControl(7045 + slot).setPosition(chip_x + 8, 362)
                    _set(self, 'AuraDetailChipIcon{}'.format(slot), icon)
                    lbl_x, lbl_w = chip_x + 34, width - 40
                else:
                    lbl_x, lbl_w = chip_x, width
                self.getControl(7022 + slot * 2).setPosition(lbl_x, 356)
                self.getControl(7022 + slot * 2).setWidth(lbl_w)
                self.getControl(7022 + slot * 2).setLabel(text)
            except RuntimeError:
                pass
            chip_x += width + 12

    @staticmethod
    def _rating_chip(value, rating_image, audience=False):
        icon = _provider_icon(rating_image, audience)
        text = _fmt_rating(value, rating_image)
        if not icon:
            text = '{} {}'.format(_provider_label(rating_image),
                                  text).strip()
        return (text, icon)

    def _render_cast(self):
        cast = self.item.get('cast') or []
        try:
            lst = self.getControl(CAST_LIST_ID)
            lst.reset()
            for member in cast[:20]:
                li = xbmcgui.ListItem(member['name'], member.get('role') or '')
                li.setArt({'thumb': member.get('thumb_url') or 'actor-fallback.png'})
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
            self.getControl(7060).setLabel(i18n.tr(33103).format(
                len(self._seasons), 's' if len(self._seasons) > 1 else ''))
        except RuntimeError:
            pass
        _set(self, 'AuraDetailSectionTitle', '1' if self._seasons else '')
        # Top strip: Show | Saison 1 | Saison 2 | ...
        try:
            strip = self.getControl(SEASON_STRIP_ID)
            strip.reset()
            strip.addItem(xbmcgui.ListItem(i18n.tr(33101)))
            for season in self._seasons:
                idx = season.get('index')
                strip.addItem(xbmcgui.ListItem(i18n.tr(33102).format(
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
                    right_id = (
                        RESTART_BUTTON_ID
                        if self.getProperty('AuraDetailRestart')
                        else (EXTRAS_BUTTON_ID
                              if self.getProperty('AuraDetailExtras')
                              else RATE_BUTTON_ID))
                    watch.setNavigation(strip, row, watch,
                                        self.getControl(right_id))
                    row.setNavigation(watch, row, row, row)
            if self.mode in ('show', 'season'):
                strip.setNavigation(strip, watch, strip, strip)
        except RuntimeError as e:
            xbmc.log('Akasha Aura Detail: nav sync failed: {}'.format(e),
                     xbmc.LOGWARNING)

    # ------------------------------------------------------------- input

    def _action_label(self, control_id):
        """Text shown inside an action pill once it is focused (Plex:
        circles expand into 'Add to Watchlist' / 'Mark as Unwatched'...)."""
        if control_id == WATCH_BUTTON_ID:
            return self._watch_label()
        return {
            RESTART_BUTTON_ID: i18n.tr(33107),
            EXTRAS_BUTTON_ID: self._extras_label(),
            WATCHLIST_BUTTON_ID: i18n.tr(33110),
            RATE_BUTTON_ID: i18n.tr(33111),
            WATCHED_BUTTON_ID: (i18n.tr(33113) if self.watched
                                else i18n.tr(33112)),
            MORE_BUTTON_ID: i18n.tr(33007),
        }[control_id]

    def _extras_label(self):
        """'Bande-annonce' when a trailer clip exists, 'Bonus' otherwise."""
        if any(e.get('subtype') == 'trailer' for e in self._extras):
            return i18n.tr(33108)
        return i18n.tr(33109)

    def _set_action_labels(self):
        for cid in ACTION_ROW_IDS:
            try:
                self.getControl(cid).setLabel(self._action_label(cid))
            except (RuntimeError, KeyError):
                pass

    def _action_width(self, control_id, focused_id):
        if control_id != focused_id:
            return ACTION_CIRCLE_W
        label = self._action_label(control_id)
        # Rough text measure for RobotoCondensed-Bold 24 (font_tiny_bold):
        # narrow glyphs ~12px, average ~16px, wide ones ~22px -- Kodi has
        # no text-metrics API and clips overflowing labels into a scroll.
        text_w = sum(22 if c in 'mwMWÉÈÊ' else
                     (12 if c.isdigit() or c in ' ilj.,:;·\'()-–' else 16)
                     for c in label)
        return max(96, 110 + text_w)

    def _sync_action_row(self):
        """Plex layout: unfocused actions are 64px circles; the focused
        one expands into a white pill (icon + label) and pushes the rest
        of the row right."""
        restart = bool(self._playable_item() and
                       self._playable_item().get('view_offset_ms'))
        order = ([WATCH_BUTTON_ID]
                 + ([RESTART_BUTTON_ID] if restart else [])
                 + ([EXTRAS_BUTTON_ID] if self._extras else [])
                 + [RATE_BUTTON_ID, WATCHED_BUTTON_ID, MORE_BUTTON_ID])
        # Plex watchlist sync is a plex.tv cloud feature -- the button stays
        # hidden rather than surfacing an "unavailable" notification.
        for cid in (WATCHLIST_BUTTON_ID,) + ACTION_ICON_OVERLAYS.get(
                WATCHLIST_BUTTON_ID, ()):
            try:
                self.getControl(cid).setVisible(False)
            except RuntimeError:
                pass
        try:
            focused = self.getFocusId()
        except RuntimeError:
            focused = 0
        if focused not in ACTION_ROW_IDS:
            focused = 0
        x = ACTION_ROW_LEFT
        for cid in order:
            w = self._action_width(cid, focused)
            try:
                self.getControl(cid).setPosition(x, ACTION_ROW_TOP)
                self.getControl(cid).setWidth(w)
            except RuntimeError:
                pass
            for ov_id in ACTION_ICON_OVERLAYS.get(cid, ()):
                try:
                    # 28px glyphs centred in the 64px circle, like Plex.
                    self.getControl(ov_id).setPosition(x + 18,
                                                       ACTION_ROW_TOP + 18)
                except RuntimeError:
                    pass
            x += w + ACTION_ROW_GAP
        # Left/right nav follows the visible order exactly -- hidden
        # buttons (watchlist, and restart/extras when absent) must never
        # land under the cursor. Up reaches the season strip in show
        # mode, Down the visible bottom row.
        bottom_id = {'item': CAST_LIST_ID, 'show': SEASONS_LIST_ID,
                     'season': EPISODES_LIST_ID}.get(self.mode)
        bottom_prop = {'item': 'AuraDetailCastRow',
                       'show': 'AuraDetailSeasonsRow',
                       'season': 'AuraDetailEpisodesRow'}.get(self.mode)
        show_strip = self.mode in ('show', 'season')
        for i, cid in enumerate(order):
            try:
                ctl = self.getControl(cid)
                if i:
                    ctl.controlLeft(self.getControl(order[i - 1]))
                if i + 1 < len(order):
                    ctl.controlRight(self.getControl(order[i + 1]))
                if show_strip:
                    ctl.controlUp(self.getControl(SEASON_STRIP_ID))
                if self.getProperty(bottom_prop):
                    ctl.controlDown(self.getControl(bottom_id))
            except RuntimeError:
                pass

    def onFocus(self, controlID):
        self._sync_action_row()

    def onClick(self, controlID):
        if controlID == WATCH_BUTTON_ID:
            self._play()
        elif controlID == RESTART_BUTTON_ID:
            self._play(start_over=True)
        elif controlID == WATCHED_BUTTON_ID:
            self._toggle_watched()
        elif controlID == WATCHLIST_BUTTON_ID:
            # Plex watchlist sync is an online-account feature; surface it
            # once the connector proxies it.
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33124), xbmcgui.NOTIFICATION_INFO, 1500)
        elif controlID == EXTRAS_BUTTON_ID:
            self._play_extra()
        elif controlID == RATE_BUTTON_ID:
            self._rate()
        elif controlID == MORE_BUTTON_ID:
            self._open_more_menu()
        elif controlID in MORE_PANEL_IDS:
            self._on_more_entry(controlID)
        elif controlID == SEASON_STRIP_ID:
            self._on_strip_selected()
        elif controlID == SEASONS_LIST_ID:
            pos = self.getControl(SEASONS_LIST_ID).getSelectedPosition()
            if 0 <= pos < len(self._seasons):
                self._show_season(pos + 1)
        elif controlID == EPISODES_LIST_ID:
            self._open_episode()
        elif controlID == CAST_LIST_ID:
            self._open_person()

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
        # The "Plus d'actions" side panel swallows Back/Left like Plex's
        # sheet: it collapses back onto the action row instead of closing
        # the whole page.
        if self._more_menu_open():
            if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK,
                                  ACTION_MOVE_LEFT):
                self._close_more_menu()
                return
            if action.getId() in (ACTION_MOVE_DOWN, ACTION_MOVE_UP):
                self._panel_nav(action.getId() == ACTION_MOVE_DOWN)
                return
        elif action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            if not self._back_to_show():
                self.close()
            return
        if action.getId() == ACTION_CONTEXT_MENU:
            # Plex long-press parity: a long press fires the same action
            # as a plain click on the focused control (open the episode,
            # the action button, ...) and never raises a context menu.
            try:
                self.onClick(self.getFocusId())
            except Exception:
                pass
            return
        if action.getId() == ACTION_MOVE_LEFT and self._at_left_edge():
            # Plex: pressing Left on the left edge opens the sidebar rail.
            self.exit_to_sidebar = True
            self.close()
            return
        super().onAction(action)

    def _at_left_edge(self):
        try:
            focused = self.getFocusId()
        except RuntimeError:
            return False
        if focused == WATCH_BUTTON_ID:
            return True
        if focused in (CAST_LIST_ID, EPISODES_LIST_ID, SEASONS_LIST_ID,
                       SEASON_STRIP_ID):
            try:
                return self.getControl(focused).getSelectedPosition() == 0
            except RuntimeError:
                return False
        return False

    # ------------------------------------------------------------ actions

    def _playable_item(self):
        """The item Watch/Resume would actually start (OnDeck episode for
        shows, the item itself otherwise)."""
        if self.mode in ('show', 'season'):
            nxt = self._find_next_episode()
            if nxt:
                return nxt
            if self._seasons:
                self._load_episodes(0)
                return self._episodes[0] if self._episodes else None
            return None
        return self.item

    def _watch_label(self):
        item = self.item
        if self.mode in ('show', 'season'):
            nxt = self._find_next_episode()
            if nxt:
                label = i18n.tr(33105).format(
                    nxt.get('season') or '?', nxt.get('index') or '?')
                if nxt.get('view_offset_ms') and nxt.get('duration_ms'):
                    left = _fmt_duration(
                        nxt['duration_ms'] - nxt['view_offset_ms'])
                    label += ' · ' + i18n.tr(33131).format(left)
                return label
            return i18n.tr(33104)
        if item.get('view_offset_ms'):
            left_ms = (item.get('duration_ms') or 0) - item['view_offset_ms']
            return i18n.tr(33106).format(_fmt_duration(left_ms))
        return i18n.tr(33104)

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
        # Extras parts carry their own query string ('?fmt=4&bitrate=...').
        joiner = '&' if '?' in item['part_key'] else '?'
        return '{}{}{}X-Plex-Token={}'.format(
            base, item['part_key'], joiner, token)

    def _open_person(self):
        """Cast & Crew pick -> Plex-style person page (photo + the
        person's server-side filmography across the video sections)."""
        try:
            pos = self.getControl(CAST_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        cast = self.item.get('cast') or []
        if not (0 <= pos < len(cast)):
            return
        member = cast[pos]
        person_filter = member.get('person_filter')
        if not person_filter and self.client and \
                self.item.get('grandparent_rating_key'):
            # Episode-level Role entries carry no filter: resolve it from
            # the parent show's cast (same tag, with 'actor=ID').
            try:
                parent = self.client.metadata_item(
                    self.item['grandparent_rating_key'])
                for parent_member in (parent or {}).get('cast', []):
                    if parent_member.get('name') == member.get('name') \
                            and parent_member.get('person_filter'):
                        person_filter = parent_member['person_filter']
                        break
            except Exception:
                pass
        if not person_filter or not self.client:
            return
        try:
            filmography = self.client.person_filmography(person_filter)
        except Exception as e:
            xbmc.log('Akasha Aura Detail: filmography failed: {}'.format(e),
                     xbmc.LOGWARNING)
            filmography = []
        import aura_person
        person = aura_person.AuraPersonWindow(
            'AuraPerson.xml', self.addon_path, 'Default', '1080i')
        person.client = self.client
        person.addon_path = self.addon_path
        person.person = member
        person.items = filmography
        person.doModal()

    def _play_extra(self):
        """Bande-annonce/Bonus button: a single extra plays straight
        away, several open Plex's pick list first."""
        if not self._extras:
            return
        pick = self._extras[0]
        if len(self._extras) > 1:
            trailers = [e for e in self._extras
                        if e.get('subtype') == 'trailer']
            ordered = trailers + [e for e in self._extras
                                  if e.get('subtype') != 'trailer']
            pos = xbmcgui.Dialog().select(
                self._extras_label(),
                [e.get('title') or i18n.tr(33109) for e in ordered])
            if pos < 0:
                return
            pick = ordered[pos]
        url = self._stream_url(pick)
        if not url:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33075),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        li = xbmcgui.ListItem(pick.get('title') or '')
        li.setMimeType('video/mp4')
        self.playback_started = True
        self.close()
        osd_menu.store_playback_context(self.client, [pick])
        xbmc.Player().play(url, li)

    def _play(self, start_over=False):
        item = self.item
        if self.mode in ('show', 'season'):
            item = self._find_next_episode()
            if not item and self._seasons:
                # Fall back to the very first episode, like Plex's Play.
                self._load_episodes(0)
                item = self._episodes[0] if self._episodes else None
            if not item:
                xbmcgui.Dialog().notification(
                    'Akasha Aura', i18n.tr(33121),
                    xbmcgui.NOTIFICATION_INFO, 2000)
                return
        self._start_playback(item, start_over)

    def _start_playback(self, item, start_over=False):
        url = self._stream_url(item)
        if not url:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33075),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        li = xbmcgui.ListItem(item.get('title') or '')
        self._apply_info_tags(li, item)
        # Kodi 20+ resume point (resumetime/totaltime are deprecated).
        apply_resume_point(li, item, start_over)
        li.setMimeType('video/mp4')
        # Tells the owner (Aura window + default.py) that playback began:
        # every modal dialog must leave the screen for the fullscreen
        # video to activate, and Aura re-opens once playback ends.
        self.playback_started = True
        self.close()
        # Single-item play + serialized season queue for the Up Next
        # card (B1), like aura_window._ctx_play.
        queue = episode_queue_items(self.client, item)
        osd_menu.store_playback_context(self.client, queue or [item])
        xbmc.Player().play(url, li)

    @staticmethod
    def _apply_info_tags(li, item):
        """Feed VideoPlayer.* infolabels (OSD title block) — Kodi 21's
        InfoTagVideo API, with the legacy setInfo as fallback."""
        try:
            tag = li.getVideoInfoTag()
            if item.get('type') == 'episode':
                tag.setMediaType('episode')
                if item.get('show_title'):
                    tag.setTvShowTitle(item['show_title'])
                if item.get('season') is not None:
                    tag.setSeason(int(item['season']))
                if item.get('index') is not None:
                    tag.setEpisode(int(item['index']))
            else:
                tag.setMediaType('movie')
            tag.setTitle(item.get('title') or '')
            if item.get('year'):
                tag.setYear(int(item['year']))
            if item.get('summary'):
                tag.setPlot(item['summary'])
            if item.get('genres'):
                tag.setGenres(item['genres'])
        except Exception:
            try:
                info = {'title': item.get('title') or ''}
                if item.get('type') == 'episode':
                    info.update({
                        'tvshowtitle': item.get('show_title') or '',
                        'season': int(item.get('season') or 0),
                        'episode': int(item.get('index') or 0),
                    })
                if item.get('year'):
                    info['year'] = int(item['year'])
                if item.get('summary'):
                    info['plot'] = item['summary']
                li.setInfo('video', info)
            except Exception:
                pass

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
        # 'Mark as watched/unwatched' label flips with the state
        try:
            self.getControl(WATCHED_BUTTON_ID).setLabel(
                self._action_label(WATCHED_BUTTON_ID))
        except RuntimeError:
            pass
        self._sync_action_row()

    def _open_more_menu(self):
        """Plex's 'More' button opens a 'More Actions' side panel
        (Subtitles, Add to List, Playlist/Collection, Manage, File Info,
        More Ways to Watch). The panel slides over the dimmed page from
        the right edge; cloud-only entries surface an explicit
        notification and File Info shows the media data we actually
        have."""
        _set(self, 'AuraDetailMore', '1')
        try:
            self.setFocus(self.getControl(MORE_PANEL_FIRST_ID))
        except RuntimeError:
            pass

    def _close_more_menu(self):
        _set(self, 'AuraDetailMore', '')
        try:
            self.setFocus(self.getControl(MORE_BUTTON_ID))
        except RuntimeError:
            pass

    def _more_menu_open(self):
        return self.getProperty('AuraDetailMore') == '1'

    def _panel_entry_visible(self, cid):
        """Conditional More-panel entries (props set in _render)."""
        if cid == MORE_GO_SHOW_ID:
            return self.getProperty('AuraDetailGoToShow') == '1'
        if cid == MORE_VERSION_ID:
            return self.getProperty('AuraDetailVersions') == '1'
        return True

    def _panel_nav(self, down):
        """MOVE_UP/DOWN inside the More panel: skip entries hidden by
        props -- static XML navigation cannot express that."""
        order = (MORE_SUBTITLES_ID, MORE_FILE_INFO_ID, MORE_RELATED_ID,
                 MORE_GO_SHOW_ID, MORE_VERSION_ID)
        try:
            focused = self.getFocusId()
        except RuntimeError:
            return
        visible = [c for c in order if self._panel_entry_visible(c)]
        if focused not in visible:
            return
        i = visible.index(focused) + (1 if down else -1)
        if 0 <= i < len(visible):
            try:
                self.setFocus(self.getControl(visible[i]))
            except RuntimeError:
                pass

    def _on_more_entry(self, control_id):
        self._close_more_menu()
        if control_id == MORE_FILE_INFO_ID:
            self._show_file_info()
            return
        if control_id == MORE_RELATED_ID:
            self._open_related()
            return
        if control_id == MORE_GO_SHOW_ID:
            self._go_to_show()
            return
        if control_id == MORE_VERSION_ID:
            self._pick_version()
            return
        msg = {
            MORE_SUBTITLES_ID: 'Choix des sous-titres pendant la lecture',
            MORE_LIST_ID: 'Listes indisponibles (fonction Plex cloud)',
            MORE_PLAYLIST_ID: 'Playlists indisponibles (fonction Plex cloud)',
            MORE_MANAGE_ID: 'Gestion indisponible (fonction Plex cloud)',
            MORE_WAYS_ID: 'Sources externes indisponibles (fonction Plex cloud)',
        }.get(control_id)
        if msg:
            xbmcgui.Dialog().notification('Akasha Aura', msg,
                                          xbmcgui.NOTIFICATION_INFO, 2500)

    def _open_related(self):
        """Plex's 'More Like This' (B7): the /related hub flattened into
        a poster row. Rendered through the person-page window -- same
        layout, the item standing in for the person's photo/title."""
        base_item = self._playable_item() or self.item
        rating_key = base_item.get('rating_key')
        items = []
        if self.client and rating_key:
            fetch = getattr(self.client, 'related_items', None)
            if fetch:
                try:
                    items = fetch(rating_key)
                except Exception as e:
                    xbmc.log('Akasha Aura Detail: related fetch failed: {}'
                             .format(e), xbmc.LOGWARNING)
        import aura_person
        related = aura_person.AuraPersonWindow(
            'AuraRelated.xml', self.addon_path, 'Default', '1080i')
        related.client = self.client
        related.addon_path = self.addon_path
        related.person = {
            'name': base_item.get('title') or '',
            'thumb_url': (base_item.get('poster_url')
                          or base_item.get('thumb_url') or ''),
        }
        related.items = items
        related.doModal()

    def _go_to_show(self):
        """Plex's 'Go to Show' (B11): from an episode fiche, open the
        parent show's page on top of the current detail."""
        item = self._playable_item() or self.item
        show_key = item.get('grandparent_rating_key')
        if not (self.client and show_key):
            return
        try:
            show = self.client.metadata_item(show_key)
        except Exception as e:
            xbmc.log('Akasha Aura Detail: show fetch failed: {}'.format(e),
                     xbmc.LOGWARNING)
            return
        if not show:
            return
        detail = AuraDetailWindow(
            'AuraDetail.xml', self.addon_path, 'Default', '1080i')
        detail.client = self.client
        detail.item = show
        detail.mode = 'show'
        detail.doModal()

    def _pick_version(self):
        """Plex's 'Play Version' (B12): pick among the item's Media
        versions and play the chosen part."""
        item = self._playable_item() or self.item
        versions = [v for v in (item.get('versions') or [])
                    if v.get('part_key')]
        if len(versions) < 2:
            return
        pos = xbmcgui.Dialog().select(
            i18n.tr(33583), [v['label'] for v in versions])
        if pos < 0:
            return
        versioned = dict(item)
        versioned['part_key'] = versions[pos]['part_key']
        self._start_playback(versioned)

    def _show_file_info(self):
        item = self._playable_item() or self.item
        lines = [item.get('title') or '']
        meta = [x for x in (item.get('year'),
                            _fmt_duration(item.get('duration_ms')))
                if x]
        if meta:
            lines.append(' · '.join(str(m) for m in meta))
        for label, key in ((i18n.tr(33132), 'video_label'),
                           (i18n.tr(33201), 'audio_label'),
                           (i18n.tr(33115), 'subtitle_label')):
            if item.get(key):
                lines.append('{} : {}'.format(label, item[key]))
        xbmcgui.Dialog().ok(i18n.tr(33116), '[CR]'.join(lines))

    def _rate(self):
        if not self.client or not self.item.get('rating_key'):
            return
        choices = ['{} / 10'.format(i) for i in range(1, 11)]
        pos = xbmcgui.Dialog().select(i18n.tr(33111), choices)
        if pos < 0:
            return
        try:
            self.client.rate(self.item['rating_key'], pos + 1)
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33120).format(choices[pos]),
                xbmcgui.NOTIFICATION_INFO, 1500)
        except Exception as e:
            xbmc.log('Akasha Aura Detail: rate failed: {}'.format(e), xbmc.LOGERROR)


_AGE_RATINGS = {
    'g': 'age 0+', 'tv-y': 'age 0+', 'tv-g': 'age 0+', 'u': 'age 0+',
    'pg': 'age 9+', 'tv-pg': 'age 9+', '10': 'age 10+',
    'pg-13': 'age 13+', 'tv-14': 'age 13+', '12': 'age 12+',
    'r': 'age 17+', 'tv-ma': 'age 17+', '16': 'age 16+',
    'nc-17': 'age 18+', '18': 'age 18+',
}


def _age_label(content_rating):
    """Plex renders the content rating as a friendly 'age N+' chip."""
    raw = (content_rating or '').strip()
    mapped = _AGE_RATINGS.get(raw.lower())
    if mapped == 'age 0+':
        return i18n.tr(33145)
    return mapped or raw


def _provider_icon(rating_image, audience=False):
    """Plex chips draw a provider glyph (IMDb yellow, RT splat, popcorn,
    TMDB teal) before the value -- small generated textures in media/."""
    img = rating_image or ''
    if 'imdb' in img:
        return 'prov-imdb.png'
    if 'themoviedb' in img:
        return 'prov-tmdb.png'
    if 'rottentomatoes' in img:
        return 'prov-rt-aud.png' if audience else 'prov-rt.png'
    return ''


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
    return i18n.fmt_air_date(iso_date)


def _fmt_duration(duration_ms):
    if not duration_ms:
        return ''
    minutes = int(duration_ms) // 60000
    hours, minutes = divmod(minutes, 60)
    if hours:
        return '{}h {}m'.format(hours, minutes)
    return '{}m'.format(minutes)
