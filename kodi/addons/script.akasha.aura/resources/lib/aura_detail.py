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
import threading
import time

import xbmc
import xbmcgui
import aura_menu
import i18n

import osd_menu

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
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
    """Set the resume point when the item carries a Plex view offset.

    Three mechanisms are set: for Player.play(url, li), Kodi only honors
    the ListItem 'StartOffset' property -- the videotag resume point
    (setResumePoint/resumetime) is only consulted through the Kodi media
    database, which never has an entry for a bare stream URL (verified
    on-device: the InfoTag-only path restarted the episode at 0:00
    instead of the Plex viewOffset)."""
    if not item.get('view_offset_ms') or start_over:
        return
    offset = float(item['view_offset_ms']) / 1000.0
    try:
        li.getVideoInfoTag().setResumePoint(
            offset, float(item.get('duration_ms') or 0) / 1000.0)
    except Exception:
        pass
    li.setProperty('resumetime', str(offset))
    li.setProperty('totaltime', str(float(item['duration_ms'] or 0) / 1000.0))
    li.setProperty('StartOffset', str(offset))

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
EXTRAS_ROW_ID = 7170
RELATED_LIST_ID = 7175

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
MORE_EXTRAS_ID = 7210
MORE_AUDIO_ID = 7211
ACTIVITY_PANEL_ID = 7195
ACTIVITY_ROW_ID = 7196
ACTIVITY_FEED_ID = 7197

# Plex opens the sheet on its first entry: Audio Stream.
MORE_PANEL_FIRST_ID = MORE_AUDIO_ID

# Panel geometry (matches Plex's measured sheet) and the aux-control
# ids so _pack_more_panel() can re-pack rows around hidden
# conditional entries (Go to show / Version / Extras).
MORE_PANEL_TOP = 210
MORE_PANEL_PITCH = 77
# Icon/value control ids per panel button. The original entries keep
# the 7230+i / 7250+i scheme; Audio Stream (added later) takes free
# ids after them so no existing XML id moves.
MORE_ICON_LIGHT = {MORE_SUBTITLES_ID: 7230, MORE_LIST_ID: 7231,
                   MORE_PLAYLIST_ID: 7232, MORE_MANAGE_ID: 7233,
                   MORE_FILE_INFO_ID: 7234, MORE_WAYS_ID: 7235,
                   MORE_RELATED_ID: 7236, MORE_GO_SHOW_ID: 7237,
                   MORE_VERSION_ID: 7238, MORE_EXTRAS_ID: 7239,
                   MORE_AUDIO_ID: 7240}
MORE_ICON_DARK = {MORE_SUBTITLES_ID: 7250, MORE_LIST_ID: 7251,
                  MORE_PLAYLIST_ID: 7252, MORE_MANAGE_ID: 7253,
                  MORE_FILE_INFO_ID: 7254, MORE_WAYS_ID: 7255,
                  MORE_RELATED_ID: 7256, MORE_GO_SHOW_ID: 7257,
                  MORE_VERSION_ID: 7258, MORE_EXTRAS_ID: 7259,
                  MORE_AUDIO_ID: 7241}
MORE_VALUE_IDS = {MORE_SUBTITLES_ID: (7260, 7261),
                  MORE_AUDIO_ID: (7262, 7263)}
# Cloud-only Plex entries (List, Playlist, Manage, More Ways) show a
# notification; Subtitles, Audio, File Info and Similar Titles work.
# Plex's order (official-live/22-detail-overflow): Audio Stream,
# Subtitles, Add to List, Add To Playlist/Collection, Watch Trailer,
# Manage, File Info, More Ways to Watch -- the conditional entries
# (Similar Titles, Go to show, Version) sit after them.
MORE_PANEL_IDS = (MORE_AUDIO_ID, MORE_SUBTITLES_ID, MORE_LIST_ID,
                  MORE_PLAYLIST_ID, MORE_EXTRAS_ID, MORE_MANAGE_ID,
                  MORE_FILE_INFO_ID, MORE_WAYS_ID, MORE_RELATED_ID,
                  MORE_GO_SHOW_ID, MORE_VERSION_ID)

# Plex's action order: Play/Resume | Restart | Watchlist | Rate |
# Watched | Extras | More -- extras sit next to More, not in the core
# five (Plex ATV refs: focus_rate_005, focus_morelabel_010).
LIST_BUTTON_ID = 7164      # cloud-only 'Add to List' circle (official 56)

# Watched | Extras | More -- extras sit next to More, not in the core
# five (Plex ATV refs: focus_rate_005, focus_morelabel_010).
ACTION_ROW_IDS = (WATCH_BUTTON_ID, RESTART_BUTTON_ID, WATCHLIST_BUTTON_ID,
                  LIST_BUTTON_ID, RATE_BUTTON_ID, WATCHED_BUTTON_ID,
                  EXTRAS_BUTTON_ID, MORE_BUTTON_ID)
# light/dark icon overlay pairs that ride on top of each action button
ACTION_ICON_OVERLAYS = {
    WATCH_BUTTON_ID: (7088, 7089, 7090, 7091, 7163),
    RESTART_BUTTON_ID: (7107, 7108),
    EXTRAS_BUTTON_ID: (7111, 7112),
    WATCHLIST_BUTTON_ID: (7092, 7093),
    LIST_BUTTON_ID: (7165, 7166),
    RATE_BUTTON_ID: (7099, 7105),
    WATCHED_BUTTON_ID: (7094, 7095, 7096),
    MORE_BUTTON_ID: (7097, 7098),
}
# Chip label ids per slot (7030 is the synopsis textbox -- the 5th label
# jumps to 7032).
CHIP_LABEL_IDS = (7022, 7024, 7026, 7028, 7032)

# label overlay per action button: ControlButton.setLabel is not rendered
# on this Kodi build (XML <label> bakes at parse time), so the pill text
# lives on a sibling label control, visible only while the action has focus
ACTION_PILL_UNDERLAYS = {
    WATCH_BUTTON_ID: 7160,
    RESTART_BUTTON_ID: 7161,
}
ACTION_LABEL_OVERLAYS = {
    WATCH_BUTTON_ID: 7150,
    RESTART_BUTTON_ID: 7151,
    EXTRAS_BUTTON_ID: 7152,
    WATCHLIST_BUTTON_ID: 7153,
    LIST_BUTTON_ID: 7157,
    RATE_BUTTON_ID: 7154,
    WATCHED_BUTTON_ID: 7155,
    MORE_BUTTON_ID: 7156,
}
ACTION_ROW_LEFT = 128
ACTION_ROW_GAP = 32
ACTION_CIRCLE_W = 64
ACTION_LABEL_X = 62      # label zone offset inside the expanded pill
ACTION_LABEL_PAD = 22    # right padding inside the pill


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
        self._activity_label = ''
        self._activity_avatar2 = ''
        self._activity_avatar3 = ''
        self._activity_initial2 = ''
        self._activity_initial3 = ''
        self._activity_color2 = ''
        self._activity_color3 = ''
        self._feed_open = False
        self._next_episode = None
        self._hero_episode = None     # focused episode painted as hero (season mode)
        self._action_top = 564      # action row y (below cards in season mode)
        self._badge_top = 672       # media pills y (director line in season)
        self._active_season = 0     # 0 = "Show" overview tab
        self._row_pos = {}          # last absolute row positions (wrap guard)
        self._pending_season_index = None  # season card entry point
        self._restore_episode_pos = None   # episode pos to restore on Back
        # Plex stacks sections under the content row: Cast & Crew,
        # Trailers & Extras, Related titles. Kodi windows can't scroll,
        # so the inactive sections park off-screen and the focused one
        # takes the bottom slot (see _apply_flow / _set_section).
        self._bottom = 'content'    # 'content' | 'cast' | 'extras' | 'related'
        self._related = []
        self._related_title = ''
        self._related_key = None
        self._related_title = ''
        self.exit_to_sidebar = False
        # Vertical rhythm of the lower block (see _apply_flow): the Plex
        # action pill sits at y564 under a director line, y524 without.
        self._flow_top = 564
        # Background fetches kicked off at the top of _render() so the
        # independent Plex calls overlap instead of serialising on the
        # GUI thread (the "buttons appear one by one" root cause).
        self._bg_done = {}
        self._bg_results = {}

    def onInit(self):
        # Reveal veil (bottom of AuraDetail.xml): drop it for this open --
        # _render lifts it once populated. Reset here, not in _render:
        # mode swaps (episode <-> show) re-render without re-veiling.
        _set(self, 'AuraDetailReady', '')
        _set(self, 'AuraDetailFeed', '')
        self._feed_open = False
        _set(self, 'AuraDetailFanart',
             self.item.get('fanart_url') or self.item.get('art_url') or '')
        try:
            self._render()
        except Exception as e:
            xbmc.log('Akasha Aura Detail: init error: {}'.format(e), xbmc.LOGERROR)
            # Never leave the reveal veil down on a failed render -- a
            # stuck 'empty' prop would mask the whole page as black.
            _set(self, 'AuraDetailReady', '1')

    # ------------------------------------------------------------ render

    def _bg_start(self, key, fn_name, *args, **kwargs):
        """Fire one independent client call on a daemon thread; _bg_get()
        joins it where the result is consumed. On a warm read cache the
        call returns instantly -- on a cold one the requests overlap."""
        fn = getattr(self.client, fn_name, None)
        if fn is None:
            return
        done = threading.Event()
        self._bg_done[key] = done
        # Capture THIS render's result map: a late thread from a previous
        # _render must not write stale data into the new item's map.
        results = self._bg_results

        def run():
            try:
                results[key] = fn(*args, **kwargs)
            except Exception as e:
                xbmc.log('Akasha Aura Detail: {} failed: {}'.format(
                    fn_name, e), xbmc.LOGWARNING)
                results[key] = None
            finally:
                done.set()

        threading.Thread(target=run, daemon=True).start()

    def _bg_get(self, key, timeout=12.0):
        """Join a _bg_start()ed call. Returns None when the fetch was
        never started or failed -- callers treat both as 'no data'."""
        done = self._bg_done.get(key)
        if done is None:
            return None
        done.wait(timeout)
        return self._bg_results.get(key)

    def _render(self):
        item = self.item
        self.watched = bool(item.get('watched'))
        # A full render always resets the episode hero: season mode
        # re-seeds it on the focused/next-up card right below. Bumping
        # the generation also cancels any in-flight hero hydration from
        # the previous page.
        self._hero_episode = None
        self._hero_gen = getattr(self, '_hero_gen', 0) + 1

        # Kick off the independent Plex calls in parallel FIRST: extras,
        # watch history, on-deck and seasons each used to run serially
        # here (~4.5s cold on the Pi), which is what made the page
        # materialise control-by-control behind the reveal veil.
        # Reset the maps: the window instance is reused, and a stale
        # 'done' event would otherwise serve the PREVIOUS item's data.
        self._bg_done = {}
        self._bg_results = {}
        if self.client and item.get('rating_key'):
            rk = item['rating_key']
            cloud = bool(item.get('cloud'))
            if not cloud:
                # Cloud (Discover) records have hex provider keys: the
                # local server 404s every one of these calls.
                self._bg_start('extras', 'item_extras', rk)
                if hasattr(self.client, 'item_related'):
                    self._bg_start('related', 'item_related', rk)
                if not item.get('last_viewed_at'):
                    # Scoped by metadataItemID: unscoped history answers
                    # the WHOLE log (~25MB) -- the OOM that killed Kodi.
                    self._bg_start('history', 'watch_history',
                                   limit=50, rating_key=rk)
                self._bg_start('ondeck', 'on_deck', limit=60)
            if self.mode == 'show':
                if cloud and hasattr(self.client, 'provider_children'):
                    # The provider serves seasons on the node's own key
                    # (/library/metadata/<hex>/children).
                    self._bg_start('seasons', 'provider_children',
                                   item.get('key') or '')
                elif not cloud:
                    self._bg_start('seasons', 'show_seasons', rk)
            if not cloud and (not item.get('ratings')
                              or not item.get('cast')):
                # Hub/list records are thin: Role entries have no thumbs
                # and Media streams often lack audio/subtitle detail, so
                # the Cast & Crew row, the provider rating chips (IMDb /
                # RT) and the audio/sub badges would render empty where
                # Plex shows them. The full metadata record has all of
                # it -- fetch overlaps the synchronous render, joined
                # just before the badge block. Skipped when the caller
                # already passed a full record (nothing to hydrate).
                self._bg_start('meta', 'metadata_item', rk)

        # Thin items get hydrated by the 'meta' fetch started above:
        # merge the fields the full record fills in (cast thumbs, page
        # tint, stream badges, richer ratings) BEFORE anything renders,
        # so the UltraBlurColors tint picks up the real palette too.
        if 'meta' in self._bg_done:
            full = self._bg_get('meta') or {}
            if full:
                for key in ('cast', 'ratings', 'rating', 'audience_rating',
                            'rating_image', 'audience_rating_image',
                            'content_rating', 'content_rating_age',
                            'blur_colors', 'logo_url', 'fanart_url',
                            'video_label', 'audio_label', 'subtitle_label'):
                    if full.get(key):
                        item[key] = full[key]

        _set(self, 'AuraDetailCloud',
             '1' if item.get('cloud') else '')
        _set(self, 'AuraDetailShowStrip',
             '1' if self.mode in ('show', 'season') else '')
        _set(self, 'AuraDetailSeasonsRow',
             '1' if self.mode == 'show' else '')
        _set(self, 'AuraDetailEpisodesRow',
             '1' if self.mode == 'season' else '')
        self._bottom = 'content'
        # Plex exposes Cast & Crew on every detail flavour -- movies,
        # shows, seasons, episodes (27-detail-show).
        _set(self, 'AuraDetailCastRow', '1' if item.get('cast') else '')

        try:
            self.getControl(7001).setImage(
                item.get('fanart_url') or item.get('art_url') or '', useCache=False)
        except RuntimeError:
            pass
        # Plex tints the page field with the item's UltraBlurColors: the
        # flat dim layer and the (now white) bottom gradient both pick up
        # the topLeft palette color, neutral navy fallback.
        tint = str((item.get('blur_colors') or {}).get('topLeft') or '')
        tint = tint.lstrip('#')[-6:].upper() if tint else '10131A'
        for cid, alpha in ((7002, '73'), (7003, 'FF')):
            try:
                self.getControl(cid).setColorDiffuse(alpha + tint)
            except (RuntimeError, AttributeError):
                pass
        self._paint_hero(item)

        # Bonus clips (trailer, deleted scenes...): Plex shows a trailer
        # button whenever /extras answers -- fetched once per item.
        if self._extras_key != item.get('rating_key'):
            self._extras_key = item.get('rating_key')
            self._extras = []
            if self.client and item.get('rating_key'):
                if 'extras' in self._bg_done:
                    self._extras = self._bg_get('extras') or []
                elif item.get('cloud'):
                    self._extras = []
                else:
                    try:
                        self._extras = self.client.item_extras(
                            item['rating_key'])
                    except Exception as e:
                        xbmc.log('Akasha Aura Detail: extras failed: {}'
                                 .format(e), xbmc.LOGWARNING)
        _set(self, 'AuraDetailExtras', '1' if self._extras else '')
        _set(self, 'AuraDetailExtrasRow', '1' if self._extras else '')
        self._render_extras_row()

        # Related hubs ('Related Shows', 'More with <actor>'): the row
        # stacks under Trailers & Extras like Plex's page scroll.
        if self._related_key != item.get('rating_key'):
            self._related_key = item.get('rating_key')
            self._related = []
            self._related_title = ''
            if 'related' in self._bg_done:
                hubs = self._bg_get('related') or []
                if hubs:
                    self._related_title = hubs[0].get('title') or ''
                    for hub in hubs:
                        self._related.extend(hub.get('items') or [])
            self._render_related()
        _set(self, 'AuraDetailRelatedRow', '1' if self._related else '')

        # "Activity by you and X" (B6): Plex names every server account
        # with history on this item ('you' first, then the others) and
        # stacks their avatars; the expanded feed lives on the right
        # column in Plex. The entry list (50 rows) is cached on the
        # reused window for 5 min -- without it every detail open paid
        # a full history fetch for a single line.
        if self._activity_key != item.get('rating_key'):
            self._activity_key = item.get('rating_key')
            self._activity_date = ''
            self._activity_avatar2 = ''
            self._activity_avatar3 = ''
            self._activity_initial2 = ''
            self._activity_initial3 = ''
            self._activity_color2 = ''
            self._activity_color3 = ''
            self._activity_label = ''
            entries = self._watch_history_entries(item.get('rating_key'))
            viewed_at = item.get('last_viewed_at')
            if not viewed_at:
                # Thin items (hub cards) lack lastViewedAt: fall back to
                # the item-scoped history call (metadataItemID, ~1KB).
                for entry in entries:
                    if entry.get('viewed_at'):
                        viewed_at = entry['viewed_at']
                        break
            if viewed_at:
                self._activity_date = i18n.fmt_air_date(
                    time.strftime('%Y-%m-%d',
                                  time.localtime(viewed_at)))
            own, names = self._activity_names(
                entries, item.get('rating_key'))
            # Plex: one name then 'and N other(s)' once two or more
            # other accounts appear ('by you, clara, and 2 others').
            rest = len(names) - 1
            if own and len(names) > 1:
                self._activity_label = (i18n.tr(33601).format(names[0])
                                        if rest == 1 else
                                        i18n.tr(33602).format(names[0], rest))
            elif own and names:
                self._activity_label = i18n.tr(33595).format(names[0])
            elif own:
                self._activity_label = i18n.tr(33594)
            elif len(names) > 1:
                self._activity_label = (i18n.tr(33603).format(names[0])
                                        if rest == 1 else
                                        i18n.tr(33604).format(names[0], rest))
            elif names:
                self._activity_label = i18n.tr(33596).format(names[0])
            elif self._activity_date:
                # No account data (older servers/connectors): keep the
                # previous date-only line rather than nothing.
                self._activity_label = i18n.tr(33578).format(
                    self._activity_date)
        _set(self, 'AuraDetailActivity', self._activity_label or '')
        _set(self, 'AuraDetailActivityAvatar2',
             self._activity_avatar2 or '')
        _set(self, 'AuraDetailActivityAvatar3',
             self._activity_avatar3 or '')
        _set(self, 'AuraDetailActivityInitial2',
             self._activity_initial2 or '')
        _set(self, 'AuraDetailActivityInitial3',
             self._activity_initial3 or '')
        _set(self, 'AuraDetailActivityColor2',
             self._activity_color2 or '')
        _set(self, 'AuraDetailActivityColor3',
             self._activity_color3 or '')
        try:
            self.getControl(7207).setPosition(
                296 if (self._activity_avatar3
                        or self._activity_initial3) else
                (248 if (self._activity_avatar2
                         or self._activity_initial2) else 200),
                self._flow_top + 105)
        except RuntimeError:
            pass

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
        self._layout_media_badges()

        # Bottom section
        if self.mode == 'item':
            self._render_cast()
            _set(self, 'AuraDetailSectionTitle',
                 '1' if item.get('cast') else '')
            try:
                self.getControl(7060).setPosition(128,
                                                self._flow_top + 202)
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

        if self.mode != 'item':
            # Item mode renders the cast row inline above; on show
            # pages it waits parked below the content row.
            self._render_cast()

        self._sync_navigation()
        # Plex lands focus on the most meaningful content: the
        # Watch/Resume action in show overview (it stays the expanded
        # white pill in the reference captures), the next episode to
        # watch inside a season -- never the tab strip.
        try:
            if self.mode == 'show' and getattr(self, 'land_on_strip', False):
                # Back from playback: Plex drops focus on the 'Show' tab
                # rather than the Resume pill (44-after-back).
                pos = self._preferred_season_pos()
                self.getControl(SEASONS_LIST_ID).selectItem(pos)
                self.setFocus(self.getControl(SEASON_STRIP_ID))
            elif self.mode == 'show':
                pos = self._preferred_season_pos()
                lst = self.getControl(SEASONS_LIST_ID)
                lst.selectItem(pos)
                self.setFocus(self.getControl(WATCH_BUTTON_ID))
            elif self.mode == 'season':
                pos = (self._restore_episode_pos
                       if self._restore_episode_pos is not None
                       else self._preferred_episode_pos())
                self._restore_episode_pos = None
                lst = self.getControl(EPISODES_LIST_ID)
                if self._episodes:
                    lst.selectItem(pos)
                self.setFocus(lst)
                self._row_pos[EPISODES_LIST_ID] = pos + 1
                # Plex's season view is an episode page: hero = that card.
                self._set_hero_episode(pos)
            else:
                self.setFocus(self.getControl(WATCH_BUTTON_ID))
        except RuntimeError:
            pass
        # Everything is populated and focused: lift the reveal veil so the
        # page materialises in a single paint instead of control-by-control.
        _set(self, 'AuraDetailReady', '1')

    def _apply_flow(self):
        """Seat the lower block on Plex's vertical rhythm, measured on the
        Plex ATV refs: activity avatars at T+91, media badges at T+108,
        the section heading at T+202 and the bottom row at T+264 -- all
        pinned to the action pill top (T). The window is reused across
        modes so every offset is re-applied on each render."""
        t = self._flow_top
        # Plex's season page stacks differently from the show overview
        # (official-live/27-detail-show): no section heading, episode
        # cards right under the hero (~y585), and the action circles
        # BELOW the cards (~y930). The Cast & Crew swap restores the
        # standard actions-over-cast stack, matching Plex's scroll.
        season_cards = (self.mode == 'season' and
                        self._bottom == 'content')
        # The tall lower sections (extras 380px, related 430px) only
        # appear in Plex's fully-scrolled state: the action row, the
        # activity line and the media pills have scrolled off the top,
        # so we park them and lift the row until its captions fit.
        deep = self._bottom in ('extras', 'related')
        self._action_top = (2200 if deep
                            else 930 if season_cards else t)
        # The activity line is a show-level section: Plex draws it
        # neither on the season page nor in the scrolled-off state.
        act_top = (2200 if (self.mode == 'season' or deep)
                   else t + 92)
        for cid in (7180, 7181, 7182):
            try:
                self.getControl(cid).setPosition(132, act_top)
            except RuntimeError:
                pass
        # Avatar-initial overlays ride on the same y (act_top parks the
        # whole activity line on Plex's season page) but keep their
        # baked x: the second stack sits at 224.
        for cid in (7183, 7184, 7187, 7188):
            try:
                self.getControl(cid).setPosition(178, act_top)
            except RuntimeError:
                pass
        for cid in (7185, 7186, 7189, 7192):
            try:
                self.getControl(cid).setPosition(224, act_top)
            except RuntimeError:
                pass
        try:
            self.getControl(7196).setPosition(
                128, act_top - 2 if not (self.mode == 'season' or deep)
                else 2200)
            # 7207 is the 'Vous l'avez regarde...' activity label -- the
            # whole activity line is parked on Plex's season page and in
            # the scrolled-off state. The media pills ride at the
            # director line instead (~y530, official-live/27); elsewhere
            # they sit under the actions.
            self.getControl(7207).setPosition(
                200, act_top + 13 if not (self.mode == 'season' or deep)
                else 2200)
            self._badge_top = (2200 if deep
                               else t - 40 if season_cards else t + 108)
            # On the season cards view Plex shows no section heading --
            # only the NEXT section's title peeking at the bottom edge
            # above its cropped row ('Cast & Crew' sliver, or extras/
            # related when the item has no cast).
            label_ctl = self.getControl(7060)
            secs = self._bottom_sections()
            # 'content' isn't a section on plain item pages -- the first
            # real section (Cast & Crew, or extras/related when there
            # is no cast) owns the slot.
            if self._bottom not in secs:
                self._bottom = secs[0] if secs else 'content'
            # Full section heights incl. captions -- the deep rows are
            # bottom-anchored ~10px off the screen edge like Plex's
            # fully-scrolled state.
            _ROW_H = {SEASONS_LIST_ID: 380, EPISODES_LIST_ID: 296,
                      CAST_LIST_ID: 250, EXTRAS_ROW_ID: 380,
                      RELATED_LIST_ID: 430}
            if season_cards:
                nxt = secs[1] if len(secs) > 1 else None
                label_ctl.setLabel(
                    self._section_title(nxt) if nxt else '')
                label_ctl.setPosition(128, 1005)
            else:
                label_ctl.setLabel(self._section_title(self._bottom))
                label_ctl.setPosition(128, t + 202)
            row_top = 590 if season_cards else t + 264
            if deep:
                active_list = self._section_list(self._bottom)
                row_top = 1070 - _ROW_H.get(active_list, 300)
                label_ctl.setPosition(128, row_top - 64)
            active = self._section_list(self._bottom)
            # The sliver row is the next section's list peeking under
            # the season cards' bottom edge.
            sliver = self._section_list(secs[1]) \
                if season_cards and len(secs) > 1 else None
            # Parked sections keep their 'visible' state (Kodi only
            # moves focus natively into visible controls) but sit past
            # the screen edge; the focused one owns the bottom slot.
            for cid in (SEASONS_LIST_ID, EPISODES_LIST_ID, CAST_LIST_ID,
                        EXTRAS_ROW_ID, RELATED_LIST_ID):
                top = (row_top if cid == active
                       else 1050 if cid == sliver else 2200)
                self.getControl(cid).setPosition(128, top)
        except RuntimeError:
            pass

    def _paint_hero(self, item):
        """Logo/title, meta line + content-rating box, provider chips,
        synopsis and director line for `item` -- the detail record for
        movies/shows, the FOCUSED EPISODE on season pages (Plex's season
        view is an episode page: 'Le retour', 'S7 • E16', 'Directed
        by...'). Re-runnable: _set_hero_episode() repaints it per card."""
        # Plex's season hero keeps the SHOW clearlogo with the episode
        # title as a heading under it (official-live/27: 'THE ROOKIE'
        # logo + 'Le retour'). The episode record has no logo of its
        # own, so it borrows the show's and the title moves to the
        # AuraDetailEpTitle label (7013); the logo itself shrinks to
        # Plex's ~85px season size.
        hero_logo = item.get('logo_url') or ''
        season_hero = (self.mode == 'season' and item is not self.item
                       and bool(hero_logo or self.item.get('logo_url')))
        if season_hero and not hero_logo:
            hero_logo = self.item['logo_url']
        _set(self, 'AuraDetailLogo', hero_logo)
        _set(self, 'AuraDetailEpTitle',
             (item.get('title') or '') if season_hero else '')
        try:
            logo_ctl = self.getControl(7010)
            logo_ctl.setWidth(560 if season_hero else 720)
            logo_ctl.setHeight(85 if season_hero else 162)
        except RuntimeError:
            pass
        if hero_logo:
            try:
                self.getControl(7010).setImage(hero_logo,
                                               useCache=False)
                self.getControl(7011).setLabel('')
            except RuntimeError:
                pass
        else:
            try:
                self.getControl(7011).setLabel(item.get('title') or '')
            except RuntimeError:
                pass

        # Meta line: Plex shows "S1 - E4  ·  air date  ·  duration" for
        # episodes, "year  ·  duration  ·  genres" otherwise. Unreleased
        # items get Plex's amber "Releasing Oct 29" in place of year/air.
        parts = []
        unreleased = _unreleased_label(item)
        if item.get('type') == 'episode':
            se = _season_episode_label(item)
            if se:
                parts.append(se.replace(' - ', ' • '))
            air = unreleased or _fmt_air_date(
                item.get('originally_available_at'))
            if air:
                parts.append(air)
        elif unreleased:
            parts.append(unreleased)
        elif item.get('year'):
            parts.append(str(item['year']))
        duration = _fmt_duration(item.get('duration_ms'))
        if duration:
            parts.append(duration)
        elif self.mode in ('show', 'season') and self._seasons:
            parts.append('{} saison{}'.format(
                len(self._seasons), 's' if len(self._seasons) > 1 else ''))
        if item.get('genres'):
            parts.append(', '.join(item['genres'][:2]))
        meta_text = '    '.join(parts)
        meta_display = meta_text
        if unreleased:
            # Keep meta_text plain for text_width() below; the amber wrap
            # is display-only or the rating chip would be pushed right.
            meta_display = meta_text.replace(
                unreleased,
                '[COLOR FFE5A00D]{}[/COLOR]'.format(unreleased), 1)
        try:
            self.getControl(7020).setLabel(meta_display)
        except RuntimeError:
            pass
        # Plex trails the meta line with a small bordered box holding the
        # content rating ("12" / "10" / "TV-MA"), ~16px after the text.
        rating = (item.get('content_rating') or '').strip()
        _set(self, 'AuraDetailMetaRating', '1' if rating else '')
        if rating:
            # PIL under-measures Kodi's Inter ~1.0x here (see i18n.ellipsize)
            box_x = 128 + int(i18n.text_width(meta_text, 20) or 0) + 24
            box_w = max(40, int((i18n.text_width(rating, 19) or 20)
                                * 0.96) + 20)
            try:
                self.getControl(7190).setPosition(box_x, 294)
                self.getControl(7190).setWidth(box_w)
                self.getControl(7191).setPosition(box_x, 294)
                self.getControl(7191).setWidth(box_w)
                self.getControl(7191).setLabel(rating)
            except RuntimeError:
                pass

        self._render_chips(item)

        # Synopsis + director
        summary = item.get('summary') or ''
        # The synopsis box holds exactly 3 lines of font_aura_plot in
        # 800px -- measure-trim to fill them (~1950px PIL * ~1.2 Kodi
        # width factor = ~2.9 rendered lines) so no overflow fades the
        # edges; the 240-char cap stays as a no-PIL fallback.
        summary = i18n.ellipsize(summary, 25, budget_px=1950)
        if summary.endswith('…') and ' ' in summary:
            # Plex breaks the ellipsis on a word boundary.
            summary = summary[:-1].rsplit(' ', 1)[0].rstrip(',. ') + '…'
        if len(summary) > 240:
            summary = summary[:240].rsplit(' ', 1)[0].rstrip(',. ') + '...'
        try:
            box = self.getControl(7030)
            box.setText(summary)
            # setText leaves the box scrolled to the tail (first line
            # fades under the top-edge scrim) -- reset() restores the
            # scroll offset to the top.
            box.reset()
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
        # Plex flows the whole lower block up 40px when the page has no
        # director/creator line (shows, director-less items): measured on
        # the Plex ATV refs -- action pill y564 with director, y524
        # without. The reused window re-applies every offset each render.
        self._flow_top = 564 if director else 524
        self._apply_flow()

    def _set_hero_episode(self, pos):
        """Plex's season page hero follows the focused episode card.
        Paint the thin children record immediately (title/synopsis are
        already there), then hydrate the full record behind a debounce
        -- provider chips, 'Directed by' and the real stream badges land
        a beat later exactly like Plex's hero does on a Right-hold."""
        if self.mode != 'season' or not (0 <= pos < len(self._episodes)):
            return
        ep = self._episodes[pos]
        if ep is self._hero_episode:
            return
        self._hero_episode = ep
        gen = self._hero_gen = getattr(self, '_hero_gen', 0) + 1
        self._paint_hero(ep)
        self._layout_media_badges(hydrate=False)
        # Resume/Restart state and the pill label follow the focused
        # card ('Resume S1 E2 · Nm left'), like Plex's hero actions.
        self._sync_action_row()

        def work():
            time.sleep(0.25)
            if gen != getattr(self, '_hero_gen', 0):
                return
            self._hydrate_stream_labels(ep)
            if gen != getattr(self, '_hero_gen', 0):
                return
            self._paint_hero(ep)
            self._layout_media_badges()
            self._sync_action_row()
        threading.Thread(target=work, daemon=True).start()

    def _render_chips(self, item):
        # Each chip: (text, provider icon or ''). Plex draws a provider
        # glyph (IMDb / RT splat / popcorn / TMDB) before the value; text
        # prefixes are only the fallback when no icon is known.
        chips = []
        age = item.get('content_rating_age')
        if age is not None and str(age) != '':
            # Plex: shield glyph + "age N+" + chevron inside the pill,
            # sourced from contentRatingAge like the official app.
            label = (i18n.tr(33145) if str(age) == '0'
                     else 'age {}+'.format(age))
            chips.append((label + ' ›', 'age-shield.png', 30, True))
        elif item.get('content_rating'):
            chips.append((_age_label(item['content_rating']) + ' ›',
                          'age-shield.png', 30, True))
        # Plex draws up to 4 bare provider chips (icon + value, no pill)
        # from the Ratings array; the legacy scalar fields are the
        # fallback when the array is absent.
        ratings = item.get('ratings') or []
        if ratings:
            for r in ratings[:4]:
                chips.append((self._rating_chip(r.get('value'),
                                               r.get('image'),
                                               audience=r.get('type') == 'audience')
                              + (False,)))
        else:
            if item.get('rating'):
                chips.append((self._rating_chip(item['rating'],
                                               item.get('rating_image'))
                              + (False,)))
            if item.get('audience_rating'):
                chips.append((self._rating_chip(item['audience_rating'],
                                               item.get('audience_rating_image'),
                                               audience=True)
                              + (False,)))
        chip_x = 128
        for slot in range(5):
            _set(self, 'AuraDetailChip{}'.format(slot), '')
            _set(self, 'AuraDetailChipIcon{}'.format(slot), '')
            _set(self, 'AuraDetailChipBg{}'.format(slot), '')
        for slot, (text, icon, icon_w, pill) in enumerate(chips[:5]):
            text_w = int((i18n.text_width(text, 19) or len(text) * 10)
                         * 0.96)
            width = (text_w + (icon_w + 8 if icon else 0)
                     + (14 if pill else 0))
            _set(self, 'AuraDetailChip{}'.format(slot), '1')
            if pill:
                _set(self, 'AuraDetailChipBg{}'.format(slot), '1')
            try:
                self.getControl(7021 + slot * 2).setPosition(chip_x, 340)
                self.getControl(7021 + slot * 2).setWidth(width)
                if icon:
                    ic = self.getControl(7045 + slot)
                    if icon == 'age-shield.png':
                        # Plex's green shield-check overshoots the pill
                        # edge (~44px tall on a 40px pill).
                        ic.setPosition(chip_x + 4, 338)
                        ic.setWidth(30)
                        ic.setHeight(44)
                    else:
                        ic.setPosition(chip_x + (10 if pill else 0), 348)
                        ic.setWidth(icon_w)
                        ic.setHeight(24)
                    _set(self, 'AuraDetailChipIcon{}'.format(slot), icon)
                    lbl_x = chip_x + icon_w + (4 if pill else 6)
                    lbl_w = width - (lbl_x - chip_x)
                else:
                    lbl_x, lbl_w = chip_x, width
                self.getControl(CHIP_LABEL_IDS[slot]).setPosition(lbl_x, 340)
                self.getControl(CHIP_LABEL_IDS[slot]).setWidth(lbl_w)
                self.getControl(CHIP_LABEL_IDS[slot]).setLabel(text)
            except RuntimeError:
                pass
            chip_x += width + 20

    @staticmethod
    def _rating_chip(value, rating_image, audience=False):
        icon = _provider_icon(rating_image, audience)
        # IMDb/TMDB are pill badges (64x32 texture at 48x24); the tomato
        # splat and popcorn stay bare glyphs.
        icon_w = {'prov-imdb.png': 34, 'prov-tmdb.png': 42}.get(icon, 24)
        text = _fmt_rating(value, rating_image)
        if not icon:
            text = '{} {}'.format(_provider_label(rating_image),
                                  text).strip()
        return (text, icon, icon_w)

    def _render_cast(self):
        cast = self.item.get('cast') or []
        if 'meta' in self._bg_done:
            full = self._bg_get('meta') or {}
            full_cast = full.get('cast') or []
            if any(m.get('thumb_url') for m in full_cast):
                cast = full_cast
                self.item['cast'] = cast
        # The bg meta hydration lands AFTER the prop is first set, so
        # re-assert it with the resolved cast: a thin hub item would
        # otherwise leave the row populated but unreachable.
        _set(self, 'AuraDetailCastRow', '1' if cast else '')
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
            if 'seasons' in self._bg_done:
                self._seasons = self._bg_get('seasons') or []
            elif self.item.get('cloud') \
                    and hasattr(self.client, 'provider_children'):
                self._seasons = self.client.provider_children(
                    self.item.get('key') or '') or []
            else:
                self._seasons = self.client.show_seasons(
                    self.item['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: seasons failed: {}'.format(e), xbmc.LOGERROR)
            self._seasons = []
        if self.item.get('cloud'):
            self._seasons = [s for s in self._seasons
                             if s.get('type') == 'season']

    def _render_seasons(self):
        try:
            # The window is reused across modes: always re-seat the
            # heading on the current vertical rhythm.
            self.getControl(7060).setPosition(128, self._flow_top + 202)
            self.getControl(7060).setLabel(i18n.tr(33103).format(
                len(self._seasons), 's' if len(self._seasons) > 1 else ''))
        except RuntimeError:
            pass
        _set(self, 'AuraDetailSectionTitle', '1' if self._seasons else '')
        # Top strip: Show | Saison 1 | Saison 2 | ...
        self._refresh_strip()
        try:
            lst = self.getControl(SEASONS_LIST_ID)
            lst.reset()
            for season in self._seasons:
                li = xbmcgui.ListItem(self._season_label(season))
                li.setArt({'poster': season.get('poster_url')
                                       or season.get('thumb_url') or ''})
                li.setProperty('watched', '1' if season.get('watched') else '0')
                lst.addItem(li)
        except RuntimeError:
            pass

    def _refresh_strip(self):
        """(Re)build the tab strip. Re-adding items is also the only
        reliable way to make Kodi re-evaluate Control.HasFocus(7120)
        inside the layout, so the selected tab switches between Plex's
        outline (unfocused) and filled (focused) states."""
        try:
            strip = self.getControl(SEASON_STRIP_ID)
            # The capsule marks the ACTIVE view, not the last focused
            # tab -- deriving it from the mode makes the rebuild
            # self-healing whatever the focus-event ordering.
            if self.mode == 'season':
                pos = self._active_season + 1
            elif self.mode == 'show':
                pos = 0
            else:
                pos = strip.getSelectedPosition()
            strip.reset()
            strip.addItem(xbmcgui.ListItem(i18n.tr(33101)))
            for season in self._seasons:
                idx = season.get('index')
                strip.addItem(xbmcgui.ListItem(i18n.tr(33102).format(
                    idx if idx is not None else season.get('title', '?'))))
            # Plex wraps the tab row in a translucent container sized to
            # the tabs (160px pitch, ~16px trailing pad).
            self.getControl(7135).setWidth(
                min(820, (len(self._seasons) + 1) * 135 + 16))
            if pos >= 0:
                strip.selectItem(pos)
        except RuntimeError:
            pass

    @staticmethod
    def _season_label(season):
        """UI label for a season row card / episodes header -- the server
        title is in the server locale ('Season 7'), so rebuild it through
        i18n like the strip pills do (33102 'Saison {}')."""
        idx = season.get('index')
        return i18n.tr(33102).format(
            idx if idx is not None else (season.get('title') or '?'))

    def _load_episodes(self, season_pos):
        season = self._seasons[season_pos]
        try:
            if self.item.get('cloud') \
                    and hasattr(self.client, 'provider_children'):
                self._episodes = [
                    e for e in (self.client.provider_children(
                        season.get('key') or '') or [])
                    if e.get('type') == 'episode']
            else:
                self._episodes = self.client.season_episodes(
                    season['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: episodes failed: {}'.format(e), xbmc.LOGERROR)
            self._episodes = []

    def _render_episodes(self):
        season = self._seasons[self._active_season]
        try:
            self.getControl(7060).setPosition(128, self._flow_top + 202)
            self.getControl(7060).setLabel(self._season_label(season))
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
                # Plex truncates the caption with a true '…' rather than
                # letting the focused card marquee-scroll.
                label = i18n.ellipsize(label, 22, budget_px=253)
                meta2 = _fmt_duration(ep.get('duration_ms'))
                li = xbmcgui.ListItem(label, meta2)
                li.setArt({'thumb': ep.get('landscape_url')
                                    or ep.get('thumb_url') or ''})
                if ep.get('view_offset_ms') and ep.get('duration_ms'):
                    # No resume info on the episode cards: the card draws
                    # its own Plex-style progress from the PercentPlayed
                    # property, and playback items get a real resume point
                    # later via apply_resume_point().
                    pass
                if num:
                    li.setProperty('epnum', 'E{}'.format(num))
                if ep.get('progress'):
                    li.setProperty('PercentPlayed',
                                   str(int(ep['progress'] * 100)))
                li.setProperty('watched', '1' if ep.get('watched') else '0')
                lst.addItem(li)
        except RuntimeError:
            pass

    def _render_extras_row(self):
        """Plex's 'Trailers & Extras' row: landscape stills, title +
        subtype caption under each card (official 24-detail-bottom2)."""
        _EXTRA_KINDS = {
            'trailer': i18n.tr(33108),
            'behind_the_scenes': 'Behind the Scenes',
            'featurette': 'Featurette',
            'deleted_or_extended_scene': 'Deleted Scene',
            'interview': 'Interview',
            'scene_or_sample': 'Clip',
            'short': 'Short',
        }
        try:
            lst = self.getControl(EXTRAS_ROW_ID)
            lst.reset()
            for ex in self._extras:
                li = xbmcgui.ListItem(ex.get('title') or '')
                li.setArt({'thumb': ex.get('thumb_url') or
                           ex.get('art_url') or ''})
                li.setLabel2(_EXTRA_KINDS.get(ex.get('subtype') or '',
                                              i18n.tr(33109)))
                lst.addItem(li)
        except RuntimeError:
            pass

    def _render_related(self):
        """Plex's 'Related' row: poster cards, title + year caption."""
        try:
            lst = self.getControl(RELATED_LIST_ID)
            lst.reset()
            for it in self._related:
                li = xbmcgui.ListItem(it.get('title') or '')
                li.setArt({'thumb': it.get('poster_url') or
                           it.get('thumb_url') or ''})
                li.setLabel2(str(it.get('year') or ''))
                li.setProperty('watched',
                               '1' if it.get('watched') else '0')
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
            activity = self.getControl(ACTIVITY_ROW_ID)
            for cid, mode in bottom.items():
                row = self.getControl(cid)
                if mode == self.mode or (mode == 'item' and
                                         self.mode == 'item'):
                    right_id = (
                        RESTART_BUTTON_ID
                        if self.getProperty('AuraDetailRestart')
                        else WATCHLIST_BUTTON_ID)
                    # The activity row sits between the action row and
                    # the content rows (Plex's vertical stack).
                    mid = activity if self._activity_label else watch
                    watch.setNavigation(strip, mid, watch,
                                        self.getControl(right_id))
                    row.setNavigation(mid, row, row, row)
                    activity.setNavigation(watch, row, activity, activity)
            secs = self._bottom_sections()
            ids = [self._section_list(s) for s in secs]
            if self.mode in ('show', 'season'):
                strip.setNavigation(strip, watch, strip, strip)
            if self.mode == 'item' and ids:
                # Plain fiche: the first real section is the bottom row
                # (cast when present, else extras/related).
                first = self.getControl(ids[0])
                first.setNavigation(mid, first, first, first)
                activity.setNavigation(watch, first,
                                       activity, activity)
            if self.mode == 'season':
                # Plex's season column (official-live/27): tab strip ->
                # episode cards -> action circles -> lower sections.
                ep = self.getControl(EPISODES_LIST_ID)
                right_id = (
                    RESTART_BUTTON_ID
                    if self.getProperty('AuraDetailRestart')
                    else WATCHLIST_BUTTON_ID)
                strip.setNavigation(strip, ep, strip, strip)
                ep.setNavigation(strip, watch, ep, ep)
                down_ctl = (self.getControl(ids[1])
                            if len(ids) > 1 else watch)
                watch.setNavigation(ep, down_ctl, watch,
                                    self.getControl(right_id))
            # Stack the lower sections Plex-style (23/24-detail-bottom):
            # content -> Cast & Crew -> Trailers & Extras -> Related.
            for i in range(1, len(ids)):
                ctl = self.getControl(ids[i])
                prev = self.getControl(ids[i - 1])
                nxt = (self.getControl(ids[i + 1])
                       if i + 1 < len(ids) else ctl)
                # On the season page the first lower section goes back
                # up to the action row, not to the episode cards.
                ctl.controlUp(watch if (self.mode == 'season' and i == 1)
                              else prev)
                ctl.controlDown(nxt)
                if not (self.mode == 'season' and i == 1):
                    prev.controlDown(ctl)
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
            LIST_BUTTON_ID: i18n.tr(33605),
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
        # The pill text is drawn by the label overlay controls
        # (ACTION_LABEL_OVERLAYS): ControlButton.setLabel writes a field
        # this Kodi build never renders, so setting it is pointless.
        for cid in ACTION_ROW_IDS:
            try:
                self.getControl(ACTION_LABEL_OVERLAYS[cid]).setLabel(
                    self._action_label(cid))
            except (RuntimeError, KeyError):
                pass

    def _action_width(self, control_id, focused_id):
        # Plex expands only the focused action into a label pill; every
        # unfocused action (including the primary CTA) is a plain circle.
        if control_id != focused_id:
            return ACTION_CIRCLE_W
        label = self._action_label(control_id)
        # Real text measure (Inter Bold 22 = font_aura_mini_bold); PIL
        # over-measures Kodi ~0.96x. Fallback = the old char heuristic.
        text_w = i18n.text_width(label, 22)
        if text_w is not None:
            text_w = int(text_w)
        else:
            text_w = sum(26 if c in 'mwMWÉÈÊ' else
                         (14 if c.isdigit() or c in ' ilj.,:;·\'()-–'
                          else 19) for c in label)
        return max(96, ACTION_LABEL_X + text_w + ACTION_LABEL_PAD)

    def _sync_action_row(self):
        """Plex layout: unfocused actions are 64px circles; the focused
        one expands into a white pill (icon + label) and pushes the rest
        of the row right."""
        restart = bool(self._playable_item() and
                       self._playable_item().get('view_offset_ms'))
        # Plex ATV row order: Watch | restart? | watchlist | rate |
        # watched | more -- trailers/extras live in the More panel like
        # Plex's "Trailers & Extras" entry, not in the action row. The
        # watchlist bookmark stays visible like Plex even though cloud
        # sync is unavailable (click surfaces the notification). On a
        # cloud (Discover) page the bookmark circle folds into the
        # 'Add to Watchlist' pill like official-live/56.
        cloud = bool(self.item.get('cloud'))
        order = ([WATCH_BUTTON_ID]
                 + ([RESTART_BUTTON_ID] if restart else [])
                 + ([LIST_BUTTON_ID] if cloud else [WATCHLIST_BUTTON_ID])
                 + [RATE_BUTTON_ID, WATCHED_BUTTON_ID, MORE_BUTTON_ID])
        for cid, vis in ((WATCHLIST_BUTTON_ID, not cloud),
                         (LIST_BUTTON_ID, cloud)):
            for cid2 in (cid,) + ACTION_ICON_OVERLAYS.get(cid, ()):
                try:
                    self.getControl(cid2).setVisible(vis)
                except RuntimeError:
                    pass
        # The extras circle left the row for the More panel: hide it on
        # this reused window no matter what a previous render did.
        for cid in (EXTRAS_BUTTON_ID,) + ACTION_ICON_OVERLAYS.get(
                EXTRAS_BUTTON_ID, ()):
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
            # Plex keeps the labelled Resume CTA a full white pill even
            # unfocused on item/show pages (official-live/44) -- but the
            # season page draws a bare circle like every other action
            # (official-live/27). Restart collapses to a circle too once
            # the cursor leaves the row. The cloud 'Add to Watchlist'
            # pill is likewise the page's standing CTA (official-live/56).
            always = cid == WATCH_BUTTON_ID and (cloud or (
                restart and self.mode != 'season'))
            w = self._action_width(cid, cid if always else focused)
            underlay = ACTION_PILL_UNDERLAYS.get(cid)
            if underlay:
                expanded_unfocused = w > ACTION_CIRCLE_W \
                    and cid != focused
                _set(self, 'AuraPill{}'.format(cid),
                     '1' if expanded_unfocused else '')
                try:
                    u = self.getControl(underlay)
                    u.setPosition(x, self._action_top)
                    u.setWidth(w)
                except RuntimeError:
                    pass
            try:
                self.getControl(cid).setPosition(x, self._action_top)
                self.getControl(cid).setWidth(w)
            except RuntimeError:
                pass
            for ov_id in ACTION_ICON_OVERLAYS.get(cid, ()):
                try:
                    # 28px glyphs centred in the 64px circle, like Plex.
                    self.getControl(ov_id).setPosition(x + 13,
                                                       self._action_top + 11)
                except RuntimeError:
                    pass
            lb = ACTION_LABEL_OVERLAYS.get(cid)
            if lb:
                try:
                    lbl = self.getControl(lb)
                    # Collapsed actions must not leave their pill label
                    # floating over the row (dark text, but it lands on
                    # whatever pill slides underneath it).
                    lbl.setVisible(w > ACTION_CIRCLE_W)
                except RuntimeError:
                    pass
            if lb and w > ACTION_CIRCLE_W:
                try:
                    lbl = self.getControl(lb)
                    lbl.setPosition(x + ACTION_LABEL_X, self._action_top)
                    # Kodi insets label text ~10px: keep a generous zone
                    # so 'Reprendre S# E# · Nm restantes' never ellipsizes.
                    lbl.setWidth(w - ACTION_LABEL_X - 12)
                    # _set_action_labels() runs at populate time, when the
                    # resume/next-episode lookup can still be empty -- the
                    # pill then stays blank until re-set (observed on the
                    # Pi: empty 648px 'Reprendre' pill). Re-sync the text
                    # here so late-resolving labels always render.
                    text = self._action_label(cid)
                    if lbl.getLabel() != text:
                        lbl.setLabel(text)
                except RuntimeError:
                    pass
            x += w + ACTION_ROW_GAP
        # Left/right nav follows the visible order exactly -- hidden
        # buttons (watchlist, and restart/extras when absent) must never
        # land under the cursor. Up reaches the season strip in show
        # mode, Down the visible bottom row -- the first real lower
        # section, which may be extras/related when there is no cast.
        secs = self._bottom_sections()
        lower = [s for s in secs if s != 'content']
        if self.mode == 'show':
            bottom_id = SEASONS_LIST_ID
            bottom_ok = bool(self._seasons)
        elif self.mode == 'season':
            bottom_id = self._section_list(lower[0]) if lower else None
            bottom_ok = bool(lower)
        else:
            bottom_id = self._section_list(secs[0]) if secs else None
            bottom_ok = bool(secs)
        show_strip = self.mode in ('show', 'season')
        for i, cid in enumerate(order):
            try:
                ctl = self.getControl(cid)
                if i:
                    ctl.controlLeft(self.getControl(order[i - 1]))
                if i + 1 < len(order):
                    ctl.controlRight(self.getControl(order[i + 1]))
                if show_strip:
                    # Plex's season page puts the action circles under
                    # the episode cards: Up goes back to the cards, not
                    # straight to the tab strip.
                    ctl.controlUp(self.getControl(
                        EPISODES_LIST_ID if self.mode == 'season'
                        else SEASON_STRIP_ID))
                if bottom_ok:
                    ctl.controlDown(self.getControl(
                        ACTIVITY_ROW_ID if (self._activity_label and
                                            self.mode != 'season')
                        else bottom_id))
            except RuntimeError:
                pass

    def _section_label(self):
        """The 7060 heading text for the current bottom section."""
        if self.mode == 'season' and self._seasons:
            return self._season_label(self._seasons[self._active_season])
        if self.mode == 'show':
            return i18n.tr(33103).format(
                len(self._seasons), 's' if len(self._seasons) > 1 else '')
        return i18n.tr(33100)

    def _bottom_sections(self):
        """Ordered lower sections Plex stacks under the content row:
        Cast & Crew, then Trailers & Extras, then Related titles --
        each present only when it has data."""
        secs = []
        if self.mode in ('show', 'season'):
            secs.append('content')
        if self.item.get('cast'):
            secs.append('cast')
        if self._extras:
            secs.append('extras')
        if self._related:
            secs.append('related')
        return secs

    def _section_list(self, sec):
        if sec == 'content':
            return (SEASONS_LIST_ID if self.mode == 'show'
                    else EPISODES_LIST_ID)
        return {'cast': CAST_LIST_ID, 'extras': EXTRAS_ROW_ID,
                'related': RELATED_LIST_ID}.get(sec)

    def _section_title(self, sec):
        if sec == 'cast':
            return i18n.tr(33100)
        if sec == 'extras':
            return i18n.tr(33589)
        if sec == 'related':
            return self._related_title or i18n.tr(33574)
        return self._section_label()

    def _set_section(self, sec):
        """Swap a parked lower section into the bottom slot. Same end
        state as Plex's page scroll: focusing a lower row slides it in,
        focus back on the content row restores it."""
        if sec == self._bottom:
            return
        self._bottom = sec
        self._apply_flow()
        try:
            # On the season cards view the heading already reads the
            # next section's title (bottom-edge sliver); every other
            # state carries the section title.
            if not (self.mode == 'season' and sec == 'content'):
                self.getControl(7060).setLabel(self._section_title(sec))
        except RuntimeError:
            pass

    def onFocus(self, controlID):
        if controlID == CAST_LIST_ID:
            self._set_section('cast')
        elif controlID == EXTRAS_ROW_ID:
            self._set_section('extras')
        elif controlID == RELATED_LIST_ID:
            self._set_section('related')
        elif controlID in (SEASONS_LIST_ID, EPISODES_LIST_ID):
            self._set_section('content')
        if controlID == EPISODES_LIST_ID and self.mode == 'season':
            try:
                pos = self.getControl(EPISODES_LIST_ID) \
                    .getSelectedPosition()
            except RuntimeError:
                pos = -1
            self._set_hero_episode(pos)
        self._sync_action_row()
        # Kodi never re-evaluates Control.HasFocus(7120) inside a list
        # layout when focus moves elsewhere -- the selected tab would
        # keep whichever state was painted last (filled or outline).
        # Repopulating the (tiny) strip on every focus change forces a
        # re-draw against the real focus state.
        if controlID != SEASON_STRIP_ID and self.mode in ('show', 'season'):
            self._refresh_strip()

    def onClick(self, controlID):
        if controlID == WATCH_BUTTON_ID:
            if self.item.get('cloud'):
                # 'Add to Watchlist' pill: cloud watchlist sync is a
                # plex.tv feature, like the standalone bookmark circle.
                xbmcgui.Dialog().notification(
                    'Akasha Aura', i18n.tr(33124),
                    xbmcgui.NOTIFICATION_INFO, 1500)
            else:
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
        elif controlID == LIST_BUTTON_ID:
            # Same cloud-only list feature as the More panel entry.
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Listes indisponibles (fonction Plex cloud)',
                xbmcgui.NOTIFICATION_INFO, 2500)
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
        elif controlID == EXTRAS_ROW_ID:
            try:
                pos = self.getControl(EXTRAS_ROW_ID).getSelectedPosition()
            except RuntimeError:
                pos = -1
            self._play_extra(pos)
        elif controlID == RELATED_LIST_ID:
            self._open_related_card()
        elif controlID == ACTIVITY_ROW_ID:
            self._open_activity_feed()

    def _preferred_season_pos(self):
        """Season card to focus on the overview row: the season carrying
        the On Deck episode, else the first unwatched one, else the first.
        """
        nxt = self._find_next_episode()
        if nxt and nxt.get('parent_rating_key'):
            for i, season in enumerate(self._seasons):
                if season.get('rating_key') == nxt['parent_rating_key']:
                    return i
        for i, season in enumerate(self._seasons):
            if not season.get('watched'):
                return i
        return 0

    def _preferred_episode_pos(self):
        """Episode to focus inside a season: in-progress or first
        unwatched (the one Plex would highlight next), else the first."""
        for i, ep in enumerate(self._episodes):
            if ep.get('progress') or not ep.get('watched'):
                return i
        return 0

    def _on_strip_selected(self):
        try:
            pos = self.getControl(SEASON_STRIP_ID).getSelectedPosition()
        except RuntimeError:
            return
        if pos == 0:
            self._show_overview()
        else:
            self._show_season(pos)

    def _show_overview(self):
        """Back to the seasons overview: restore the seasons row and land
        on the season just left -- navigation stays centred on the
        content, never bouncing back up to the tab strip."""
        self.mode = 'show'
        self._bottom = 'content'
        self._hero_episode = None
        # Back on the seasons overview Plex paints the SHOW hero again
        # (no media badges -- _badge_item() now yields None here).
        self._paint_hero(self.item)
        self._layout_media_badges()
        _set(self, 'AuraDetailSeasonsRow', '1')
        _set(self, 'AuraDetailEpisodesRow', '')
        self._render_seasons()
        self._apply_flow()
        self._sync_navigation()
        try:
            lst = self.getControl(SEASONS_LIST_ID)
            lst.selectItem(self._active_season)
            self.setFocus(lst)
            self.getControl(SEASON_STRIP_ID).selectItem(0)
        except RuntimeError:
            pass

    def _show_season(self, strip_pos):
        season_pos = strip_pos - 1
        if not (0 <= season_pos < len(self._seasons)):
            return
        self._active_season = season_pos
        self._load_episodes(season_pos)
        self.mode = 'season'
        self._bottom = 'content'
        _set(self, 'AuraDetailSeasonsRow', '')
        _set(self, 'AuraDetailEpisodesRow', '1')
        self._render_episodes()
        self._apply_flow()
        self._sync_navigation()
        # Landing on the next episode to watch, like Plex's season pages.
        try:
            lst = self.getControl(EPISODES_LIST_ID)
            pos = self._preferred_episode_pos()
            if self._episodes:
                lst.selectItem(pos)
            self.setFocus(lst)
            self.getControl(SEASON_STRIP_ID).selectItem(strip_pos)
        except RuntimeError:
            pos = -1
        # Seed the tracker so the very first Right/Left off the landing
        # card is seen as a position change (Plex hero follows focus).
        self._row_pos[EPISODES_LIST_ID] = pos + 1
        self._set_hero_episode(pos)

    def _episode_sheet(self):
        try:
            pos = self.getControl(EPISODES_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._episodes)):
            return
        import context_sheet
        context_sheet.open_sheet(
            self, self.client, self._episodes[pos], EPISODES_LIST_ID,
            self._open_episode,
            on_removed=lambda p: self._episodes.pop(p)
            if p < len(self._episodes) else None)

    def _open_episode(self):
        try:
            pos = self.getControl(EPISODES_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._episodes)):
            return
        # Swap into episode mode (same hero, playable item); Back returns here.
        self._show_item = self.item
        self._restore_episode_pos = pos
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
        if self._feed_open:
            if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK,
                                  ACTION_MOVE_LEFT):
                self._close_activity_feed()
                return
            super().onAction(action)
            return
        if self._more_menu_open():
            if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK,
                                  ACTION_MOVE_LEFT):
                self._close_more_menu()
                return
            if action.getId() in (ACTION_MOVE_DOWN, ACTION_MOVE_UP):
                self._panel_nav(action.getId() == ACTION_MOVE_DOWN)
                return
        elif action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            if self.mode == 'season':
                # Episodes -> seasons overview, focus back on the season
                # card (Plex keeps navigation centred on the content).
                self._show_overview()
                return
            if not self._back_to_show():
                self.close()
            return
        if action.getId() == ACTION_CONTEXT_MENU:
            # Plex long-press: episode cards open the option sheet;
            # everything else keeps long-press == click parity.
            try:
                if self.getFocusId() == EPISODES_LIST_ID:
                    self._episode_sheet()
                    return
                self.onClick(self.getFocusId())
            except Exception:
                pass
            return
        if action.getId() == ACTION_MOVE_LEFT:
            track = self._track_row_pos()
            if track is not None:
                if track[3] > 0 and track[1] == 1:
                    # Plex: Left while already on the first row item
                    # opens the sidebar rail.
                    self.exit_to_sidebar = True
                    self.close()
                return
            if self._at_left_edge():
                self.exit_to_sidebar = True
                self.close()
                return
            super().onAction(action)
            return
        if action.getId() == ACTION_MOVE_RIGHT:
            track = self._track_row_pos()
            if track is not None:
                focused, prev, current, total = track
                if prev == total and current == 1:
                    # Plex rows stop at the last item -- undo the wrap.
                    self._row_pos[focused] = total
                    self._reassert_position(focused, total - 1)
                return
            super().onAction(action)
            return
        if action.getId() in (ACTION_MOVE_UP, ACTION_MOVE_DOWN):
            self._track_row_pos()
        super().onAction(action)

    def _track_row_pos(self):
        """Kodi applies directional moves natively, so onAction sees the
        position only AFTER the move and cannot swallow it. Track the
        absolute position (CurrentItem, 1-based) so edges are detected
        from the prev->current transition. Returns
        (control_id, prev, current, total) or None off a row list."""
        try:
            focused = self.getFocusId()
        except RuntimeError:
            return None
        if focused not in (CAST_LIST_ID, EPISODES_LIST_ID,
                           SEASONS_LIST_ID, SEASON_STRIP_ID):
            return None
        try:
            total = int(xbmc.getInfoLabel(
                'Container({}).NumItems'.format(focused)) or 0)
            current = int(xbmc.getInfoLabel(
                'Container({}).CurrentItem'.format(focused)) or 0)
        except ValueError:
            return None
        prev = self._row_pos.get(focused, current)
        self._row_pos[focused] = current
        if focused == EPISODES_LIST_ID and current != prev \
                and self.mode == 'season':
            # Plex's season-page hero follows the focused card.
            self._set_hero_episode(current - 1)
        return focused, prev, current, total

    def _reassert_position(self, control_id, position):
        def worker():
            time.sleep(0.15)
            try:
                self.getControl(control_id).selectItem(position)
            except RuntimeError:
                pass
        threading.Thread(target=worker, daemon=True).start()

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
        """The item Watch/Resume would actually start: the OnDeck
        episode when one exists, else the first UNWATCHED episode of the
        current season -- Plex badges and plays that one, not blindly
        S1E1 (and never the bare show record, which carries no
        streams)."""
        if self.item.get('cloud'):
            # Discover records carry no local part: nothing is playable,
            # Plex draws 'Add to Watchlist' instead of a Watch CTA.
            return None
        if self.mode == 'season' and self._hero_episode:
            # Plex's season page actions act on the focused card (the
            # hero): play/resume, stream pickers and badges all follow it.
            return self._hero_episode
        if self.mode in ('show', 'season'):
            nxt = self._find_next_episode()
            if nxt:
                return nxt
            self._load_seasons()
            if not self._seasons:
                return None
            season_pos = self._active_season \
                if self.mode == 'season' else 0
            self._load_episodes(season_pos)
            for ep in self._episodes:
                if not ep.get('watched'):
                    return ep
            return self._episodes[0] if self._episodes else None
        return self.item

    def _watch_label(self):
        item = self.item
        if item.get('cloud'):
            return i18n.tr(33110)
        if self.mode in ('show', 'season'):
            nxt = (self._hero_episode or self._find_next_episode()) \
                if self.mode == 'season' else self._find_next_episode()
            if nxt:
                label = i18n.tr(33105).format(
                    nxt.get('season') or '?', nxt.get('index') or '?')
                if nxt.get('view_offset_ms') and nxt.get('duration_ms'):
                    left = _fmt_duration(
                        nxt['duration_ms'] - nxt['view_offset_ms'])
                    label += ' • ' + i18n.tr(33131).format(left)
                return label
            return i18n.tr(33104)
        if item.get('view_offset_ms'):
            left_ms = (item.get('duration_ms') or 0) - item['view_offset_ms']
            return i18n.tr(33106).format(_fmt_duration(left_ms))
        return i18n.tr(33104)

    _WATCH_HISTORY_TTL = 300.0

    def _watch_history_entries(self, rating_key):
        """Item-scoped watch history for the 'Vous l'avez regarde le...'
        line, cached on this (reused) window for 5 minutes per key."""
        now = time.time()
        cache = getattr(self, '_wh_cache', None)
        if cache and cache[0] == rating_key \
                and now - cache[1] < self._WATCH_HISTORY_TTL:
            return cache[2]
        entries = []
        if 'history' in self._bg_done:
            entries = list(self._bg_get('history') or [])
        else:
            fn = getattr(self.client, 'watch_history', None)
            if fn and rating_key:
                try:
                    entries = list(fn(limit=50, rating_key=rating_key))
                except TypeError:
                    try:
                        entries = list(fn(limit=50))
                    except Exception as e:
                        xbmc.log('Akasha Aura Detail: watch history '
                                 'failed: {}'.format(e), xbmc.LOGWARNING)
                except Exception as e:
                    xbmc.log('Akasha Aura Detail: watch history failed: {}'
                             .format(e), xbmc.LOGWARNING)
        self._wh_cache = (rating_key, now, entries)
        return entries

    def _activity_names(self, entries, rating_key=None):
        """(own_watched, other_names) for Plex's 'Activity by you and X':
        each distinct account in this item's history, matched against the
        server /accounts map. The configured account is 'you' -- id 1 is
        the owner on unmanaged setups, otherwise match the plex.tv name.
        Also records the first other account's avatar as _activity_avatar2.
        """
        own = False
        names = []
        others = []
        seen = set()
        accounts = {}
        if entries and self.client and hasattr(self.client, 'accounts'):
            try:
                accounts = self.client.accounts() or {}
            except Exception:
                accounts = {}
        # Plex names every account with history on the item, even those
        # outside the 50-entry normalisation window: watch_history()
        # stashes the full ordered id list from the scoped response.
        account_ids = []
        wh = getattr(self.client, '_wh_accounts', None)
        if wh and str(rating_key or '') == wh[0]:
            account_ids = list(wh[1])
        if not account_ids:
            for entry in entries or []:
                aid = str(entry.get('account_id') or '')
                if aid and aid not in account_ids:
                    account_ids.append(aid)
        own_name = ''
        try:
            own_name = (self.getProperty('AuraUserName') or '').lower()
        except RuntimeError:
            pass
        for aid in account_ids:
            if not aid or aid in seen:
                continue
            seen.add(aid)
            acc = accounts.get(aid) or {}
            name = acc.get('name') or ''
            if aid == '1' or (own_name and name and
                              name.lower() == own_name):
                own = True
                continue
            if name:
                names.append(name)
            others.append({'name': name, 'thumb': acc.get('thumb') or ''})
        # Plex stacks up to two extra avatars; accounts without a photo
        # get a colored disc with their initial (deterministic tint).
        # NOTE: colordiffuse on addon textures is plain AARRGGBB on this
        # build, so the palette keeps straight RRGGBB literals.
        _PALETTE = ('FF3C6B9E', 'FF3F7A7A', 'FF6B7A4E', 'FF7A4E6B',
                    'FF4E4E8A', 'FF8A6B4E', 'FF4E6B8A', 'FF4E7A5E')
        for slot, other in enumerate(others[:2], start=2):
            thumb = other.get('thumb') or ''
            name = other.get('name') or ''
            setattr(self, '_activity_avatar{}'.format(slot), thumb)
            if not thumb and name:
                idx = sum(bytearray(name.encode('utf-8'))) % len(_PALETTE)
                setattr(self, '_activity_initial{}'.format(slot),
                        name[0].upper())
                setattr(self, '_activity_color{}'.format(slot),
                        _PALETTE[idx])
            else:
                setattr(self, '_activity_initial{}'.format(slot), '')
                setattr(self, '_activity_color{}'.format(slot), '')
        return own, names

    def _activity_when(self, viewed_at):
        """Plex's feed rows show ONLY the relative time for recent events
        ('2m ago') and the absolute date for older ones ('May 17, 2026')."""
        if not viewed_at:
            return ''
        delta = time.time() - viewed_at
        if 0 <= delta < 60 * 86400:
            if delta < 3600:
                return i18n.tr(33599).format(
                    '{} min'.format(max(1, int(delta // 60))))
            if delta < 86400:
                return i18n.tr(33599).format(
                    '{} h'.format(int(delta // 3600)))
            return i18n.tr(33599).format(
                '{} j'.format(int(delta // 86400)))
        return i18n.fmt_air_date(
            time.strftime('%Y-%m-%d', time.localtime(viewed_at)))

    def _open_activity_feed(self):
        """Plex's right-column watch feed: every server account that
        viewed this item, newest first (watch history is item-scoped)."""
        entries = self._watch_history_entries(
            self.item.get('rating_key') if self.item else None)
        if not entries:
            return
        accounts = {}
        if self.client and hasattr(self.client, 'accounts'):
            try:
                accounts = self.client.accounts() or {}
            except Exception:
                pass
        own_name = ''
        try:
            own_name = (self.getProperty('AuraUserName') or '').lower()
        except RuntimeError:
            pass
        try:
            feed = self.getControl(ACTIVITY_FEED_ID)
            feed.reset()
            for entry in entries:
                aid = str(entry.get('account_id') or '')
                acc = accounts.get(aid) or {}
                name = acc.get('name') or ''
                is_own = (aid == '1' or
                          (own_name and name and name.lower() == own_name))
                who = i18n.tr(33597) if is_own else \
                    i18n.tr(33598).format(name or '?')
                li = xbmcgui.ListItem(who)
                li.setLabel2(self._activity_when(entry.get('viewed_at')))
                li.setProperty('entrytitle',
                               entry.get('show_title') or
                               entry.get('title') or '')
                li.setArt({'icon': acc.get('thumb') or 'avatar-plex.png'})
                feed.addItem(li)
            feed.selectItem(0)
        except RuntimeError as e:
            xbmc.log('Akasha Aura Detail: activity feed failed: {}'.format(e),
                     xbmc.LOGWARNING)
            return
        _set(self, 'AuraDetailFeed', '1')
        self._feed_open = True
        try:
            self.setFocus(self.getControl(ACTIVITY_FEED_ID))
        except RuntimeError:
            pass

    def _close_activity_feed(self):
        _set(self, 'AuraDetailFeed', '')
        self._feed_open = False
        try:
            self.setFocus(self.getControl(ACTIVITY_ROW_ID))
        except RuntimeError:
            pass

    def _find_next_episode(self):
        if self._next_episode:
            return self._next_episode
        if not self.client or self.item.get('cloud'):
            return None
        try:
            if 'ondeck' in self._bg_done:
                deck = self._bg_get('ondeck') or []
            else:
                deck = self.client.on_deck(limit=60)
            for ep in deck:
                if ep.get('grandparent_rating_key') == self.item.get('rating_key'):
                    self._next_episode = ep
                    return ep
        except Exception as e:
            xbmc.log('Akasha Aura Detail: onDeck lookup failed: {}'.format(e),
                     xbmc.LOGWARNING)
        return None

    def _stream_url(self, item=None):
        item = item or self.item
        # Cloud clips (Discover trailers) carry an absolute CDN url that
        # plays as-is -- no local part_key to resolve.
        if item.get('direct_url'):
            return item['direct_url']
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
        if getattr(person, 'playback_started', False):
            self.playback_started = True
            self._playback_item = person._playback_item
            self.close()

    def _play_extra(self, index=None):
        """Bande-annonce/Bonus button: a single extra plays straight
        away, several open Plex's pick list first. The Trailers &
        Extras row passes the focused card's index directly."""
        if not self._extras:
            return
        if index is not None and 0 <= index < len(self._extras):
            pick = self._extras[index]
            self._start_extra(pick)
            return
        pick = self._extras[0]
        if len(self._extras) > 1:
            trailers = [e for e in self._extras
                        if e.get('subtype') == 'trailer']
            ordered = trailers + [e for e in self._extras
                                  if e.get('subtype') != 'trailer']
            pos = aura_menu.select(
                self, self._extras_label(),
                [e.get('title') or i18n.tr(33109) for e in ordered])
            if pos < 0:
                return
            pick = ordered[pos]
        self._start_extra(pick)

    def _start_extra(self, pick):
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
            # Same pick the badges show: OnDeck episode, else first
            # unwatched of the season -- Plex's Play starts the next
            # episode, not blindly S1E1.
            item = self._playable_item()
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
        # The item dict is shared with the originating row card --
        # _open_detail pushes the mutation onto its ListItem on return.
        self.item['view_count'] = 1 if self.watched else 0
        _set(self, 'AuraDetailWatched', '1' if self.watched else '0')
        # 'Mark as watched/unwatched' label flips with the state
        try:
            self.getControl(ACTION_LABEL_OVERLAYS[WATCHED_BUTTON_ID]).setLabel(
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
        self._pack_more_panel()
        _set(self, 'AuraDetailMore', '1')
        try:
            self.setFocus(self.getControl(MORE_PANEL_FIRST_ID))
        except RuntimeError:
            pass

    def _pack_more_panel(self):
        """Plex keeps the sheet compact: entries hidden by props leave
        no empty slot. Controls keep their canonical slot in the XML;
        here each visible row is moved to its packed position."""
        visible = [c for c in MORE_PANEL_IDS if self._panel_entry_visible(c)]
        for slot, cid in enumerate(visible):
            top = MORE_PANEL_TOP + MORE_PANEL_PITCH * slot
            targets = {cid: top}
            for aux in (MORE_ICON_LIGHT.get(cid), MORE_ICON_DARK.get(cid)):
                if aux:
                    targets[aux] = top + 20
            for v in MORE_VALUE_IDS.get(cid, ()):
                targets[v] = top
            for aux, y in targets.items():
                try:
                    ctl = self.getControl(aux)
                    ctl.setPosition(ctl.getPosition()[0], y)
                except (RuntimeError, AttributeError):
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
        if cid == MORE_EXTRAS_ID:
            return self.getProperty('AuraDetailExtras') == '1'
        return True

    def _panel_nav(self, down):
        """MOVE_UP/DOWN inside the More panel: skip entries hidden by
        props -- static XML navigation cannot express that."""
        order = MORE_PANEL_IDS
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
        if control_id == MORE_AUDIO_ID:
            self._pick_audio()
            return
        if control_id == MORE_SUBTITLES_ID:
            self._pick_subtitle()
            return
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
        if control_id == MORE_EXTRAS_ID:
            self._play_extra()
            return
        msg = {
            MORE_LIST_ID: 'Listes indisponibles (fonction Plex cloud)',
            MORE_PLAYLIST_ID: 'Playlists indisponibles (fonction Plex cloud)',
            MORE_MANAGE_ID: 'Gestion indisponible (fonction Plex cloud)',
            MORE_WAYS_ID: 'Sources externes indisponibles (fonction Plex cloud)',
        }.get(control_id)
        if msg:
            xbmcgui.Dialog().notification('Akasha Aura', msg,
                                          xbmcgui.NOTIFICATION_INFO, 2500)

    def _open_related_card(self):
        """Clicking a poster in the Related row pushes that title's
        fiche on top of the current one -- Plex's drill-in; Back pops
        back to this page."""
        try:
            pos = self.getControl(RELATED_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._related)):
            return
        it = self._related[pos]
        detail = AuraDetailWindow(
            'AuraDetail.xml', self.addon_path, 'Default', '1080i')
        detail.client = self.client
        detail.item = it
        detail.mode = 'show' if it.get('type') == 'show' else 'item'
        detail.doModal()
        if getattr(detail, 'playback_started', False):
            self.playback_started = True
            self._playback_item = getattr(detail, '_playback_item', None)
            self.close()

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
        # Plex labels the row 'More Like This', not 'Filmographie' --
        # the person window's default title only fits real people.
        related.row_title = i18n.tr(33574)
        related.items = items
        related.doModal()
        if getattr(related, 'playback_started', False):
            self.playback_started = True
            self._playback_item = related._playback_item
            self.close()

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
        pos = aura_menu.select(
            self, i18n.tr(33583), [v['label'] for v in versions])
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
        aura_menu.message(self, i18n.tr(33116), '[CR]'.join(lines))

    def _hydrate_stream_labels(self, src):
        """On Deck / children records carry Media but no Stream detail,
        so their audio_label is empty and their subtitle_label falls
        back to 'Off' -- Plex badges the episode's REAL tracks ('French
        (EAC3 5.1)', 'French Forced (SRT)'). One full metadata fetch
        also fills the hero-only fields children lack (directors,
        provider ratings, richer summary). The _streams_checked flag
        keeps picks and re-renders from refetching."""
        if not src or src.get('_streams_checked'):
            return
        if not self.client or not src.get('rating_key'):
            return
        src['_streams_checked'] = True
        try:
            if self.item.get('cloud') or src.get('cloud'):
                # Provider records hydrate through the Discover base --
                # the hex key 404s on the local server.
                fn = getattr(self.client, 'provider_metadata', None)
                full = (fn(src.get('key')) or {}) if fn else {}
            else:
                full = self.client.metadata_item(src['rating_key']) or {}
        except Exception as e:
            xbmc.log('Akasha Aura Detail: stream labels failed: {}'
                     .format(e), xbmc.LOGWARNING)
            return
        for key in ('video_label', 'audio_label', 'subtitle_label',
                    'summary', 'directors', 'ratings', 'rating',
                    'audience_rating', 'rating_image',
                    'audience_rating_image', 'content_rating',
                    'content_rating_age'):
            if full.get(key):
                src[key] = full[key]

    def _badge_item(self):
        """The record the media pills describe -- Plex's matrix:
        show overview = NO badges at all, season page = the focused
        (hero) episode, movie/episode page = the item itself."""
        if self.mode == 'show' or self.item.get('cloud'):
            return None
        if self.mode == 'season':
            return self._hero_episode or self._playable_item()
        return self.item

    def _layout_media_badges(self, hydrate=True):
        """Media badges, right-packed like Plex (video, audio,
        subtitles) -- hidden on the show overview. Re-runnable:
        _pick_subtitle()/_pick_audio() and _set_hero_episode() call it
        again so the pills follow the current record. The More-panel
        track values keep reading the episode Watch would start even
        on the (badge-less) show page. hydrate=False paints whatever
        the record already carries -- focus moves stay instant while
        the deferred worker fills the real tracks behind it."""
        badge = self._badge_item()
        vals = badge if badge is not None \
            else (self._playable_item() or self.item)
        if hydrate:
            self._hydrate_stream_labels(vals)
            if badge is not vals:
                self._hydrate_stream_labels(badge)
        video = (badge or {}).get('video_label') or ''
        audio = (badge or {}).get('audio_label') or ''
        subs = (badge or {}).get('subtitle_label') or ''
        badge_x = 1890
        for text, bg_id, lb_id, ic_id in ((subs, 7054, 7055, 7057),
                                          (audio, 7052, 7053, 7056),
                                          (video, 7050, 7051, 0)):
            if not text:
                continue
            ic_w = 36 if ic_id else 0
            w = 34 + len(text) * 14 + ic_w
            badge_x -= w
            try:
                self.getControl(bg_id).setPosition(badge_x,
                                                  self._badge_top)
                self.getControl(bg_id).setWidth(w)
                self.getControl(lb_id).setPosition(badge_x + ic_w,
                                                  self._badge_top)
                self.getControl(lb_id).setWidth(w - ic_w)
                self.getControl(lb_id).setLabel(text)
                if ic_id:
                    self.getControl(ic_id).setPosition(badge_x + 12,
                                                       self._badge_top + 8)
            except RuntimeError:
                pass
            badge_x -= 14
        _set(self, 'AuraDetailVideoBadge', '1' if video else '')
        _set(self, 'AuraDetailAudioBadge', '1' if audio else '')
        _set(self, 'AuraDetailSubsBadge', '1' if subs else '')
        _set(self, 'AuraDetailSubsValue',
             (vals or {}).get('subtitle_label') or i18n.tr(33202))
        _set(self, 'AuraDetailAudioValue',
             (vals or {}).get('audio_label') or i18n.tr(33203))

    def _pick_audio(self):
        """Plex's More>Audio Stream picker: one row per audio track
        ('French (EAC3 5.1)'), the current default marked with a
        check; the choice persists as the part's default audio
        (audioStreamID) so playback picks it up like Plex."""
        item = self._playable_item() or self.item
        if not self.client or not item.get('rating_key'):
            return
        fetch = getattr(self.client, 'item_audio', None)
        apply_sel = getattr(self.client, 'select_audio', None)
        if not fetch or not apply_sel:
            return
        try:
            part_id, tracks = fetch(item['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: audio list failed: {}'
                     .format(e), xbmc.LOGWARNING)
            return
        if not part_id or not tracks:
            return
        entries = []
        stream_ids = []
        for s in tracks:
            language = s.get('language') or s.get('languageTag') or ''
            codec = str(s.get('codec') or '').upper()
            layout = {2: '2.0', 6: '5.1', 8: '7.1'}.get(
                s.get('channels'), str(s.get('channels') or ''))
            inner = ' '.join(p for p in (codec, layout) if p)
            label = ' '.join(
                p for p in (language,
                            '({})'.format(inner) if inner else '')
                if p) or i18n.tr(33201)
            if s.get('selected'):
                label += '  ✓'
            entries.append(label)
            stream_ids.append(s.get('id'))
        pos = aura_menu.select(self, i18n.tr(33626), entries)
        if pos < 0:
            return
        try:
            apply_sel(part_id, stream_ids[pos])
            # The badge + More-row value follow the new default, same
            # way Plex re-reads the part after the pick.
            new_label = entries[pos].replace('  ✓', '')
            item['audio_label'] = new_label
            if item is not self.item:
                self.item['audio_label'] = new_label
            self._layout_media_badges()
        except Exception as e:
            xbmc.log('Akasha Aura Detail: audio pick failed: {}'
                     .format(e), xbmc.LOGWARNING)

    def _pick_subtitle(self):
        """Plex's More>Subtitles picker: 'Off' plus one row per stream
        ('French Forced (SRT)'), the current default marked with a
        check; the choice is persisted as the part's default subtitle
        (subtitleStreamID) so playback picks it up like Plex."""
        item = self._playable_item() or self.item
        if not self.client or not item.get('rating_key'):
            return
        fetch = getattr(self.client, 'item_subtitles', None)
        apply_sel = getattr(self.client, 'select_subtitle', None)
        if not fetch or not apply_sel:
            return
        try:
            part_id, subs = fetch(item['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Detail: subtitle list failed: {}'
                     .format(e), xbmc.LOGWARNING)
            return
        if not part_id:
            return
        entries = [i18n.tr(33202)]
        stream_ids = [0]
        any_selected = False
        for s in subs:
            language = s.get('language') or s.get('languageTag') or ''
            forced = s.get('forced')
            if forced and str(forced).lower() not in ('0', 'false', 'none'):
                language = '{} Forced'.format(language) \
                    if language else 'Forced'
            codec = str(s.get('codec') or s.get('format') or '').upper()
            label = ' '.join(p for p in
                             (language, '({})'.format(codec) if codec else '')
                             if p) or i18n.tr(33115)
            if s.get('selected'):
                any_selected = True
                label += '  ✓'
            entries.append(label)
            stream_ids.append(s.get('id'))
        if not any_selected:
            entries[0] += '  ✓'
        pos = aura_menu.select(self, i18n.tr(33115), entries)
        if pos < 0:
            return
        try:
            apply_sel(part_id, stream_ids[pos])
            # The badge + More-row value follow the new default, same
            # way Plex re-reads the part after the pick.
            new_label = i18n.tr(33202) if pos == 0 else \
                entries[pos].replace('  ✓', '')
            item['subtitle_label'] = new_label
            if item is not self.item:
                self.item['subtitle_label'] = new_label
            self._layout_media_badges()
        except Exception as e:
            xbmc.log('Akasha Aura Detail: subtitle pick failed: {}'
                     .format(e), xbmc.LOGWARNING)

    def _rate(self):
        if not self.client or not self.item.get('rating_key'):
            return
        choices = ['{} / 10'.format(i) for i in range(1, 11)]
        pos = aura_menu.select(self, i18n.tr(33111), choices)
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
        return '{:g}%'.format(v * 10 if v <= 10 else v)
    if v > 10:
        return '{:g}%'.format(v)
    return '{:.1f}'.format(v)


def _season_episode_label(item):
    season, index = item.get('season'), item.get('index')
    if season is not None and index is not None:
        return 'S{} - E{}'.format(season, index)
    return ''


def _fmt_air_date(iso_date):
    return i18n.fmt_air_date(iso_date)


def _unreleased_label(item):
    """Plex's amber 'Releasing Oct 29' meta, shown in place of the
    year/air date while the release is still in the future."""
    oa = item.get('originally_available_at')
    if not oa:
        return ''
    try:
        ts = time.mktime(time.strptime(str(oa)[:10], '%Y-%m-%d'))
    except (ValueError, OverflowError):
        return ''
    if ts <= time.time():
        return ''
    return i18n.tr(33600).format(i18n.fmt_air_date(str(oa)[:10]))


def _fmt_duration(duration_ms):
    if not duration_ms:
        return ''
    minutes = int(duration_ms) // 60000
    hours, minutes = divmod(minutes, 60)
    if hours:
        return '{}h {}m'.format(hours, minutes)
    return '{}m'.format(minutes)
