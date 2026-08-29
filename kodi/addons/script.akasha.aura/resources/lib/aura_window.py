"""Akasha Aura — main WindowXML orchestration.

Milestone 1 (socle, see docs/aura/roadmap.md): navigable 3-tab shell with
placeholder content. Milestone 2 adds Plex entertainment rows via
plex_client.py. Later milestones fill the Games and App tabs
(addons_inventory.py, store_manifest.py) without changing this navigation
skeleton.
"""
import json
import os
import random
import subprocess
import sys

import xbmc
import xbmcaddon
import xbmcgui

import addons_inventory
import aura_app
import aura_settings_panel
import aura_show
import aura_store
import config
import connector_client
import divert_source
import games_shortcuts
import home_press_monitor
import local_cache
import paged_list
import plex_client
import steam_client
import store_manifest
import sunshine_client

TAB_BUTTON_IDS = (2001, 2002, 2003)

# Main-tab IDs in the same order as config.TABS.
TAB_DIVERTISSEMENT = 0
TAB_JEUX = 1
TAB_APP = 2

# Module 0 (search) and the settings gear are part of the same top bar but
# are not "tabs" -- neither switches active_tab/content, see plan 04bda1b4.
MODULE_SEARCH_ID = 2000
GEAR_BUTTON_ID = 2004

# Dynamic layout of the Divertissement/Jeux/App group (correctif
# c7f0636a), see _layout_top_modules(). (button_id, pill_group_id,
# icon_id) per module, same left-to-right order as TAB_BUTTON_IDS.
MODULE_CONTROL_IDS = ((2001, 2101, 2102), (2002, 2103, 2104), (2003, 2105, 2106))
MODULE_LAYOUT_START_X = 100
MODULE_BUTTON_OFFSET = 40
MODULE_ICON_OFFSETS = (28, 40, 55)
MODULE_ICON_TOPS = (20, 20, 25)
MODULE_ITEM_WIDTH = 100
MODULE_PILL_WIDTH = 360
MODULE_ICON_TOP = 20
MODULE_PILL_TOP = 20

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_MENU = 163

DIVERT_SIDEBAR_ID = 3310
DIVERT_STATUS_ID = 3220
DIVERT_PANEL_ID = 3230
DIVERT_SIDEBAR_HOME_INDEX = 0
DIVERT_SIDEBAR_MORE_INDEX = 999  # placeholder, added dynamically
DIVERT_CACHE_TTL_SECONDS = 300
# Skeleton loaders (plan a3f9c2e1 phase 5): capped regardless of how large
# the real remainder is, so a huge library doesn't balloon a panel/list
# control with thousands of extra placeholder items just to convey "there's
# more below" -- see _sync_placeholders().
PLACEHOLDER_ITEM_CAP = 50

# Recommande content, rendered inline instead of a separate doModal() dialog
# (previously aura_recommendations.AuraRecommendationsWindow), see
# docs/aura/decisions.md.
RECO_ON_DECK_LABEL_ID = 5100
RECO_ON_DECK_LIST_ID = 5110
RECO_RECENT_LABEL_ID = 5200
RECO_RECENT_LIST_ID = 5210
RECO_RELEASES_LABEL_ID = 5300
RECO_RELEASES_LIST_ID = 5310
RECO_LIST_IDS = (RECO_ON_DECK_LIST_ID, RECO_RECENT_LIST_ID, RECO_RELEASES_LIST_ID)
RECO_CACHE_TTL_SECONDS = 120
RECO_ON_DECK_FETCH_LIMIT = 50  # over-fetch before client-side section filtering
RECO_MAX_ITEMS_PER_ROW = 100

# Categories content, rendered inline instead of a separate doModal() dialog
# (previously aura_genres.AuraGenresWindow).
CATEGORY_STATUS_ID = 6020
CATEGORY_PANEL_ID = 6010

# Bibliotheque toolbar (plan f41ce1ad phase A).
DIVERT_TYPE_LABEL_ID = 3210
DIVERT_FILTER_BUTTON_ID = 3211
DIVERT_SORT_BUTTON_ID = 3212
DIVERT_GENRE_BUTTON_ID = 3213
DIVERT_PLAY_BUTTON_ID = 3215
DIVERT_SHUFFLE_BUTTON_ID = 3216
DIVERT_PLAYLIST_BUTTON_ID = 3217
DIVERT_RESET_BUTTON_ID = 3218
DIVERT_TOOLBAR_BUTTON_IDS = (
    DIVERT_FILTER_BUTTON_ID, DIVERT_SORT_BUTTON_ID, DIVERT_GENRE_BUTTON_ID,
    DIVERT_PLAY_BUTTON_ID, DIVERT_SHUFFLE_BUTTON_ID,
    DIVERT_PLAYLIST_BUTTON_ID, DIVERT_RESET_BUTTON_ID,
)

# Mirrors aura_library.py's SORT_OPTIONS so both list the exact same choices
# (full labels used in the selection dialog); DIVERT_SORT_SHORT_LABELS are
# the abbreviated captions shown directly on the toolbar button, which has
# much less room than a full-screen dialog.
DIVERT_SORT_OPTIONS = [
    ('addedAt:desc', "Date d'ajout"),
    ('titleSort', 'Titre'),
    ('originallyAvailableAt:desc', 'Date de sortie'),
    ('rating:desc', 'Note'),
]
DIVERT_SORT_SHORT_LABELS = {
    'addedAt:desc': 'Ajout',
    'titleSort': 'Titre',
    'originallyAvailableAt:desc': 'Sortie',
    'rating:desc': 'Note',
}

# Quick filter: only "Tout"/"Non vus"/"Vus" are wired to a real Plex/connector
# parameter (unwatched). HDR/DOVI/Sans correspondance/Doublons from the
# original cahier des charges are not exposed by either source today -- see
# docs/aura/decisions.md.
DIVERT_FILTER_OPTIONS = [
    (None, 'Tout'),
    (True, 'Non vus'),
    (False, 'Vus'),
]

GAME_BUTTON_IDS = (2010, 2011, 2012)
APP_TILE_IDS = (2030, 2031, 2032, 2033)

DIVERT_SUBTAB_IDS = (3050, 3100, 3060)
DIVERT_SUBTAB_RECOMMANDE = 0
DIVERT_SUBTAB_BIBLIOTHEQUES = 1
DIVERT_SUBTAB_CATEGORIES = 2

JEUX_SUBTAB_IDS = (2050, 2051, 2052)
JEUX_STATUS_ID = 2055
JEUX_PANEL_ID = 2060
JEUX_SUBTAB_STEAMLINK = 0
JEUX_SUBTAB_MOONLIGHT = 1
JEUX_SUBTAB_OTHERS = 2
# Shortcuts launched from their own dedicated sub-tab, excluded from "Autres".
JEUX_DEDICATED_ACTIONS = ('steamlink', 'moonlight')

APP_SUBTAB_IDS = (2041, 2042)
APP_SUBTAB_MES_APPS = 0
APP_SUBTAB_STORE = 1

BAR_CONTROL_IDS = set(
    (MODULE_SEARCH_ID, GEAR_BUTTON_ID) + TAB_BUTTON_IDS
    + DIVERT_SUBTAB_IDS + JEUX_SUBTAB_IDS + APP_SUBTAB_IDS)


class AuraWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        addon = xbmcaddon.Addon('script.akasha.aura')
        # Always Divertissement by default -- plan 04bda1b4 section 5
        # explicitly requires this on every arrival at the global menu, not
        # just cold boot, so unlike the Divertissement-internal state
        # (library/filters, still persisted), the active top-level tab is
        # deliberately not remembered across visits.
        self.active_tab = TAB_DIVERTISSEMENT
        self.addon = addon
        self.addon_path = addon.getAddonInfo('path')
        self._plex_client = None
        self._connector_client = None
        self._divert_sections = []
        self._all_divert_sections = []
        self._divert_active_section = 0
        self._divert_items = []
        self._divert_paged = None
        # Skeleton loaders (plan a3f9c2e1 phase 5): how many trailing
        # placeholder ListItems are currently in each list/panel, so the
        # next render can remove exactly that many before appending fresh
        # real items -- see _sync_placeholders().
        self._divert_placeholder_count = 0
        self._reco_placeholder_counts = {}
        # Bibliotheque toolbar state (plan f41ce1ad phase A): reset whenever
        # the sidebar selection changes to a different library, same
        # pattern as aura_library.py's onInit -- otherwise a search/filter
        # left active would silently stick to the next library visited.
        self._divert_sort = DIVERT_SORT_OPTIONS[0][0]
        self._divert_filter_genre = None
        self._divert_filter_unwatched = None  # None=Tout, True=Non vus, False=Vus
        self._divert_search_query = ''
        # Recommande/Categories, rendered inline like Bibliotheque -- see
        # docs/aura/decisions.md ("recommandations et categories inlinees").
        self._reco_rows = {}  # {list_control_id: (label_control_id, title, PagedList)}
        self._reco_first_section = None
        self._category_section = None
        self._category_genres = []
        # 'home' (Accueil, no library selected) or 'library' (a sidebar library is
        # active and the contextual Recommande/Bibliotheque/Categories tabs apply).
        self._divert_view = addon.getSetting('divert.last_view') or 'home'
        self._divert_library_tab = config.default_subtab_index(
            addon.getSetting('divert.last_subtab'))
        self._divert_pinned_libraries = config.parse_pinned(
            addon.getSetting('divert.pinned_libraries'))
        self._divert_library_order = config.parse_pinned(
            addon.getSetting('divert.library_order'))
        self._divert_last_library_key = addon.getSetting('divert.last_library') or ''
        self._cache = local_cache.open_addon_cache(addon)
        self._games = games_shortcuts.load_shortcuts(self.addon_path)
        self._other_games = [
            g for g in self._games
            if not any(a in (g.get('action') or '').lower() for a in JEUX_DEDICATED_ACTIONS)
        ]
        self._jeux_active_subtab = JEUX_SUBTAB_STEAMLINK
        self._jeux_items = []
        self._app_subtab = APP_SUBTAB_MES_APPS
        self._pinned_apps = []
        # Sub-windows (Recommandations/Bibliotheque/Categories/App/Store/Show)
        # are constructed once and reused for every subsequent open instead
        # of a fresh instance per click: each xbmcgui.WindowXMLDialog
        # subclass permanently consumes one of Kodi's ~100 dynamic
        # script-window IDs when constructed, and that slot is never freed
        # within the same Kodi session even after the window closes and the
        # Python object is deleted -- repeatedly re-instantiating these
        # (normal daily use: Recommande/Bibliotheque/Categories are each a
        # few clicks away) eventually exhausts the pool and every *other*
        # addon that tries to open a window next starts failing with
        # "RuntimeError: maximum number of windows reached" (observed in
        # production against script.akasha.ambient, see docs/aura/decisions.md).
        # doModal() can safely be called again on the same already-built
        # instance -- onInit() re-runs each time (Kodi reloads the skin XML
        # on every activation), so state/data refresh exactly like before.
        self._sub_windows = {}
        self._divert_load_attempted = False
        # Listen for repeated Home presses while Aura is already open so we can
        # distinguish simple press (return to Divertissement tab) from double
        # press (open app switcher). See docs/remote/decisions.md.
        self._home_press_monitor = home_press_monitor.HomePressMonitor(
            self._on_home_press_action)
        # Gear-wheel remote button (dd440e2e section 9), same rationale as
        # the Home press monitor just above: RunScript can't just stack a
        # second AuraWindow while one is already running.
        self._settings_press_monitor = home_press_monitor.SettingsPressMonitor(
            self._open_settings_panel)
        # Set by default.py before doModal() when launched via
        # RunScript(script.akasha.aura, opensettings) and Aura wasn't
        # already running.
        self.open_settings_on_init = False

    def onInit(self):
        try:
            self._show_tab(self.active_tab)
            self._load_divertissement()
            self._divert_load_attempted = True
            self._restore_divert_view(focus=False)
            self._select_jeux_subtab(JEUX_SUBTAB_STEAMLINK)
            self._load_pinned_apps()
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            self._update_bar_focused()
            if getattr(self, 'open_settings_on_init', False):
                self.open_settings_on_init = False
                self._open_settings_panel()
        except Exception as e:
            xbmc.log('Akasha Aura: init error: {}'.format(e), xbmc.LOGERROR)

    def _get_connector_client(self, prompt_if_missing=False):
        """Return an authenticated ConnectorClient, or None if unavailable.

        The connector is optional: if not configured (or unreachable/session
        expired), callers fall back to direct Plex API access. Only the
        session token is persisted (`connector.session_token`), never the
        password.
        """
        server_url = self.addon.getSetting('connector.server_url')
        if not server_url:
            return None

        client = connector_client.ConnectorClient(server_url, timeout=15)
        stored_token = self.addon.getSetting('connector.session_token')
        if stored_token:
            client.token = stored_token
            return client

        if not prompt_if_missing:
            return None

        username = self.addon.getSetting('connector.username')
        if not username:
            kb = xbmc.Keyboard('', "Nom d'utilisateur (Akasha OS Connector)")
            kb.doModal()
            if not kb.isConfirmed():
                return None
            username = kb.getText().strip()
            self.addon.setSetting('connector.username', username)
        if not username:
            return None

        kb = xbmc.Keyboard('', 'Mot de passe (Akasha OS Connector)')
        kb.setHiddenInput(True)
        kb.doModal()
        if not kb.isConfirmed():
            return None
        password = kb.getText().strip()
        if not password:
            return None

        try:
            client.login(username, password)
        except connector_client.ConnectorAPIError as e:
            xbmc.log('Akasha Aura: connector login failed: {}'.format(e), xbmc.LOGERROR)
            return None
        self.addon.setSetting('connector.session_token', client.token)
        return client

    def _restore_divert_view(self, focus=True):
        """Re-select whatever Accueil/library state was last persisted.

        Falls back to Accueil if the persisted library key no longer exists
        (unpinned, removed source...) or no sections loaded at all.
        """
        if self._divert_view == 'library' and self._divert_last_library_key:
            index = next(
                (i for i, s in enumerate(self._divert_sections)
                 if s['key'] == self._divert_last_library_key), None)
            if index is not None:
                self._activate_library(index, tab=self._divert_library_tab, focus=focus)
                return
        self._activate_home(focus=focus)

    def _activate_home(self, focus=True):
        """Select Accueil in the sidebar: no library header/tabs, global rows.

        Mirrors the Plex reference (cahier des charges 780ecf80, section 2.2):
        Accueil has no per-library tab row, just "Continuer a regarder" across
        every library -- reuses the same inline Recommande content as a
        library's own Recommande tab, unscoped (section=None).
        """
        self._divert_view = 'home'
        self.setProperty('DivertView', 'home')
        self.addon.setSetting('divert.last_view', 'home')
        self._set_sidebar_selection(DIVERT_SIDEBAR_HOME_INDEX)
        self._load_recommendations(None)

    def _activate_library(self, section_index, tab=None, focus=True):
        """Select a library in the sidebar: shows its header + contextual tabs."""
        if not (0 <= section_index < len(self._divert_sections)):
            return
        self._divert_view = 'library'
        self.setProperty('DivertView', 'library')
        self.addon.setSetting('divert.last_view', 'library')
        self._select_divert_section(section_index)
        self._set_sidebar_selection(section_index + 1)
        section = self._divert_sections[section_index]
        try:
            self.getControl(3400).setLabel(section['title'])
        except RuntimeError:
            pass
        self._select_library_tab(
            self._divert_library_tab if tab is None else tab, focus=focus)

    def _select_library_tab(self, index, focus=True):
        """Switch the contextual tab (Recommande/Bibliotheque/Categories) of the
        currently selected library. No-op if no library is selected."""
        if not self._divert_sections:
            return
        section = self._divert_sections[self._divert_active_section]
        self._divert_library_tab = index
        self.setProperty('DivertLibraryTab', str(index))
        self.addon.setSetting('divert.last_subtab', str(index))

        if index == DIVERT_SUBTAB_RECOMMANDE:
            self._load_recommendations(section)
            return

        if index == DIVERT_SUBTAB_CATEGORIES:
            self._load_categories(section)
            return

        # Bibliotheque: inline grid, already populated by _select_divert_section.
        # Deliberately NOT auto-focusing the grid here: setFocus() on a
        # control gated by a <visible> condition toggled via setProperty()
        # a moment earlier, in the same onClick handler, is unreliable --
        # it can report success (getFocusId() briefly matches) yet silently
        # revert once Kodi's engine re-validates it on a later frame (seen
        # in practice: a subsequent Up press behaved as if focus had never
        # left the tab button). Leaving focus on the tab button and relying
        # on its <ondown> to reach the grid avoids the race entirely, since
        # that next input is a separate, later action -- see
        # docs/aura/decisions.md.

    def _load_recommendations(self, section):
        """Populate the 3 Recommande rows (Continuer a regarder / Ajoutes
        recemment / Sorties recentes), scoped to `section` or unscoped
        (Accueil) when None. Ported from the former
        aura_recommendations.AuraRecommendationsWindow (now rendered inline
        instead of a separate doModal() dialog, see docs/aura/decisions.md)
        -- reuses self._connector_client/self._plex_client/self._cache,
        already established by _load_divertissement(), instead of
        reconnecting independently."""
        on_deck_title = 'Continuer a regarder'
        recent_title = 'Ajoutes recemment'
        if section:
            on_deck_title += ' dans {}'.format(section['title'])
            recent_title += ' dans {}'.format(section['title'])
        self._reco_init_row(
            RECO_ON_DECK_LABEL_ID, RECO_ON_DECK_LIST_ID, on_deck_title,
            lambda offset, limit: self._reco_fetch_on_deck_page(section, offset, limit))
        self._reco_init_row(
            RECO_RECENT_LABEL_ID, RECO_RECENT_LIST_ID, recent_title,
            lambda offset, limit: self._reco_fetch_recently_added_page(section, offset, limit))

        releases_section = section or self._reco_get_first_video_section()
        releases_title = 'Sorties recentes dans {}'.format(releases_section['title']) \
            if releases_section else 'Sorties recentes'
        self._reco_init_row(
            RECO_RELEASES_LABEL_ID, RECO_RELEASES_LIST_ID, releases_title,
            lambda offset, limit: self._reco_fetch_recent_releases_page(
                releases_section, offset, limit))

    def _reco_init_row(self, label_control_id, list_control_id, title, fetch_page_fn):
        # Capped at 100 items per row regardless of how large the underlying
        # library/hub is -- these are "quick highlight" rows, not meant to
        # be a full browse surface (that's what Bibliotheque is for).
        paged = paged_list.PagedList(fetch_page_fn, max_items=RECO_MAX_ITEMS_PER_ROW)
        error = None
        try:
            paged.load_initial()
        except Exception as e:  # defensive: never crash the tab on a row failure
            error = e

        self._reco_rows[list_control_id] = (label_control_id, title, paged)
        self._render_reco_row_label(list_control_id, error)

        if error:
            xbmc.log('Akasha Aura: recommendations row "{}" failed: {}'.format(title, error),
                     xbmc.LOGWARNING)
            return
        try:
            lst = self.getControl(list_control_id)
            lst.reset()
            for item in paged.items:
                lst.addItem(_build_divert_list_item(item))
        except Exception as e:
            xbmc.log('Akasha Aura: recommendations row render error for {}: {}'
                     .format(title, e), xbmc.LOGERROR)
        self._reco_placeholder_counts[list_control_id] = self._sync_placeholders(
            list_control_id, 0, paged)

    def _render_reco_row_label(self, list_control_id, error=None):
        label_control_id, title, paged = self._reco_rows[list_control_id]
        try:
            count = paged.total if paged.total is not None else len(paged.items)
            self.getControl(label_control_id).setLabel(
                '{} — erreur de chargement'.format(title) if error else
                '{} ({} element(s))'.format(title, count))
        except RuntimeError:
            pass

    def _maybe_load_more_reco(self, list_control_id):
        row = self._reco_rows.get(list_control_id)
        if not row:
            return
        label_control_id, title, paged = row
        try:
            position = self.getControl(list_control_id).getSelectedPosition()
        except RuntimeError:
            return
        try:
            new_items = paged.maybe_load_more(position)
        except Exception as e:
            xbmc.log('Akasha Aura: recommendations pagination failed for {}: {}'
                     .format(title, e), xbmc.LOGWARNING)
            return
        if not new_items:
            return
        try:
            lst = self.getControl(list_control_id)
            for _ in range(self._reco_placeholder_counts.get(list_control_id, 0)):
                try:
                    lst.removeItem(lst.size() - 1)
                except Exception:
                    break
            lst.addItems([_build_divert_list_item(item) for item in new_items])
        except Exception as e:
            xbmc.log('Akasha Aura: recommendations append render error for {}: {}'
                     .format(title, e), xbmc.LOGERROR)
        self._reco_placeholder_counts[list_control_id] = self._sync_placeholders(
            list_control_id, 0, paged)
        self._render_reco_row_label(list_control_id)

    def _reco_fetch_on_deck_page(self, section, offset, limit):
        key = local_cache.page_cache_key(
            'on-deck', section['key'] if section else 'home', offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, RECO_CACHE_TTL_SECONDS,
            lambda: self._reco_fetch_on_deck_page_uncached(section, offset, limit))

    def _reco_fetch_on_deck_page_uncached(self, section, offset, limit):
        # No dedicated "on-deck for this section" endpoint -- over-fetch the
        # global on-deck list and filter client-side by section_id (see
        # divert_source.filter_by_section). Only an approximation of the
        # real total when scoped to a library, documented in
        # docs/aura/decisions.md.
        fetch_limit = RECO_ON_DECK_FETCH_LIMIT if section else limit
        fetch_offset = 0 if section else offset
        if self._connector_client:
            raw = self._connector_client.on_deck(limit=fetch_limit, offset=fetch_offset)
            items = divert_source.parse_metadata_list(raw, self._connector_client.image_url)
            total = divert_source.parse_total_size(raw)
        elif self._plex_client:
            items, total = self._plex_client.on_deck_with_total(
                limit=fetch_limit, offset=fetch_offset)
        else:
            return [], None
        if not section:
            return items, total
        filtered = divert_source.filter_by_section(items, section['key'])
        return filtered[offset:offset + limit], len(filtered)

    def _reco_fetch_recently_added_page(self, section, offset, limit):
        if section:
            return self._divert_section_page_uncached_sorted(
                section, 'addedAt:desc', offset, limit)
        key = local_cache.page_cache_key('recently-added', offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, RECO_CACHE_TTL_SECONDS,
            lambda: self._reco_fetch_recently_added_page_uncached(offset, limit))

    def _reco_fetch_recently_added_page_uncached(self, offset, limit):
        if self._connector_client:
            raw = self._connector_client.recently_added(limit=limit, offset=offset)
            items = divert_source.parse_metadata_list(raw, self._connector_client.image_url)
            return items, divert_source.parse_total_size(raw)
        if self._plex_client:
            return self._plex_client.recently_added_with_total(limit=limit, offset=offset)
        return [], None

    def _reco_get_first_video_section(self):
        if self._reco_first_section is not None:
            return self._reco_first_section or None
        self._reco_first_section = self._divert_sections[0] if self._divert_sections else False
        return self._reco_first_section or None

    def _reco_fetch_recent_releases_page(self, section, offset, limit):
        if not section:
            return [], None
        return self._divert_section_page_uncached_sorted(
            section, 'originallyAvailableAt:desc', offset, limit)

    def _divert_section_page_uncached_sorted(self, section, sort, offset, limit):
        """Shared by the Recommande rows above: a plain sort with no
        genre/search/unwatched filter, unlike _divert_section_page_uncached
        (the Bibliotheque toolbar's own fetch, which layers those in)."""
        if self._connector_client:
            raw = self._connector_client.section_items(
                section['key'], sort=sort, limit=limit, offset=offset)
            items = divert_source.parse_metadata_list(raw, self._connector_client.image_url)
            return items, divert_source.parse_total_size(raw)
        if self._plex_client:
            return self._plex_client.section_items_with_total(
                section['key'], sort=sort, limit=limit, offset=offset)
        return [], None

    def _load_categories(self, section):
        """Populate the Categories genre grid for `section`. Ported from the
        former aura_genres.AuraGenresWindow (now rendered inline)."""
        self._category_section = section
        self._category_genres = []
        try:
            status = self.getControl(CATEGORY_STATUS_ID)
        except RuntimeError:
            status = None
        if not section:
            if status:
                status.setLabel('Aucune bibliotheque video disponible')
            return
        try:
            if self._connector_client:
                genres = divert_source.parse_genres(
                    self._connector_client.section_genres(section['key']))
            else:
                genres = self._plex_client.section_genres(section['key'])
        except Exception as e:
            xbmc.log('Akasha Aura: categories load failed: {}'.format(e), xbmc.LOGERROR)
            genres = []
        # Kept untranslated for _on_category_genre_selected() -- the Plex/
        # connector genre filter API expects the original (English) tag,
        # only the on-screen label is translated (Plex's metadata agents
        # report genre names in the source database's language, English
        # regardless of Akasha's own French interface).
        self._category_genres = genres
        if status:
            status.setLabel('{} — {} categorie(s)'.format(section['title'], len(genres)))
        try:
            panel = self.getControl(CATEGORY_PANEL_ID)
            panel.reset()
            for genre in genres:
                panel.addItem(xbmcgui.ListItem(divert_source.translate_genre_fr(genre)))
        except RuntimeError:
            pass

    def _on_category_genre_selected(self):
        """A genre tile was picked: jump straight to Bibliotheque, pre-filtered
        to that genre, instead of the former separate AuraLibraryWindow --
        same in-place-navigation rationale as the rest of this change."""
        try:
            pos = self.getControl(CATEGORY_PANEL_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._category_genres)) or not self._category_section:
            return
        genre = self._category_genres[pos]
        index = next(
            (i for i, s in enumerate(self._divert_sections)
             if s['key'] == self._category_section['key']), None)
        if index is None:
            return
        self._divert_active_section = index
        self._divert_filter_genre = genre
        self._divert_search_query = ''
        self._select_library_tab(DIVERT_SUBTAB_BIBLIOTHEQUES)
        self._load_divert_section_items(self._category_section)
        try:
            self.setFocus(self.getControl(3100))  # Bibliotheque tab button
        except RuntimeError:
            pass

    def _set_sidebar_selection(self, index):
        try:
            sidebar = self.getControl(DIVERT_SIDEBAR_ID)
            if 0 <= index < sidebar.size():
                sidebar.selectItem(index)
        except RuntimeError:
            pass

    def _load_divertissement(self):
        # prompt_if_missing=False here: this runs on every unattended Aura
        # startup (onInit(), including after an automatic/overnight Kodi
        # restart), and a missing/expired session token must never block
        # the whole UI behind a blocking password Keyboard dialog with no
        # one there to type into it -- observed in production after a
        # connector outage cleared the stored token (see the
        # ConnectorAPIError handler below): every subsequent restart froze
        # on "Mot de passe (Akasha OS Connector)" until someone walked up
        # and pressed Back. Silently falls back to direct Plex access
        # instead; the user can explicitly re-authenticate via the gear
        # menu's "Se connecter (Connector)" entry (_reconnect_connector()),
        # which does prompt. See docs/aura/decisions.md.
        connector = self._get_connector_client(prompt_if_missing=False)
        if connector:
            try:
                self._divert_sections = divert_source.parse_sections(connector.sections())
                self._connector_client = connector
                self._plex_client = None
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura: connector sections load failed, falling back to Plex '
                         'direct: {}'.format(e), xbmc.LOGWARNING)
                self.addon.setSetting('connector.session_token', '')
                self._connector_client = None

        if not self._connector_client:
            server_url = self.addon.getSetting('plex.server_url')
            token = self.addon.getSetting('plex.token')
            if not config.is_plex_configured(server_url, token):
                xbmc.log('Akasha Aura: Plex not configured, skipping Divertissement', xbmc.LOGINFO)
                try:
                    self.getControl(DIVERT_STATUS_ID).setLabel(
                        'Plex non configure — renseignez plex.server_url et plex.token')
                except RuntimeError:
                    pass
                return
            try:
                self._plex_client = plex_client.PlexClient(server_url, token, timeout=15)
                self._divert_sections = self._plex_client.video_sections()
            except Exception as e:
                xbmc.log('Akasha Aura: Plex sections load failed: {}'.format(e), xbmc.LOGERROR)
                self._divert_sections = []

        self._all_divert_sections = config.ordered_items(
            self._divert_sections, self._divert_library_order)
        pinned_set = set(self._divert_pinned_libraries)
        if pinned_set:
            self._divert_sections = [
                s for s in self._all_divert_sections if s['key'] in pinned_set]
            if not self._divert_sections:
                # All libraries were unpinned; fall back to showing everything
                # so the sidebar never stays empty.
                self._divert_sections = list(self._all_divert_sections)
        else:
            self._divert_sections = list(self._all_divert_sections)
        self._populate_sidebar()

        # Which library (if any) becomes active is decided by the caller
        # (onInit restores the persisted Accueil/library state, _show_tab's
        # empty-sections retry re-activates Accueil) -- this only loads and
        # orders the sidebar's data, it never picks a view on its own.

    def _populate_sidebar(self):
        try:
            sidebar = self.getControl(DIVERT_SIDEBAR_ID)
        except RuntimeError:
            return
        sidebar.reset()

        home_item = xbmcgui.ListItem('Accueil')
        home_item.setArt({'icon': 'icon-home.png'})
        sidebar.addItem(home_item)

        for section in self._divert_sections:
            li = xbmcgui.ListItem(section['title'])
            li.setArt({'icon': self._divert_section_icon(section)})
            sidebar.addItem(li)

        more_item = xbmcgui.ListItem('Plus')
        more_item.setArt({'icon': 'icon-more.png'})
        sidebar.addItem(more_item)

    def _divert_section_icon(self, section):
        """Return a distinct icon name for a library section.

        Maps common library titles to dedicated textures; new textures can be
        added without touching this code as long as the file name matches the
        convention `icon-<slug>.png`.
        """
        title = (section.get('title') or '').lower()
        if 'anime' in title:
            return 'icon-anime.png'
        if 'documentaire' in title or 'documentary' in title:
            return 'icon-documentary.png'
        if 'concert' in title or 'musique' in title or 'music' in title:
            return 'icon-music.png'
        if section.get('type') == 'show':
            return 'icon-tv.png'
        return 'icon-film.png'

    def _divert_cache_mode_key(self):
        """search and genre are mutually exclusive filters; sort and
        unwatched are independent axes that always apply on top of
        whichever one is active, so both must always be part of the cache
        key -- otherwise changing the sort while a genre/search filter is
        active would silently keep returning the old sort's cached page
        (found while testing Phase A: switching "Trier" had no visible
        effect once a genre filter was set). See the identical fix needed
        in aura_library.py's _current_mode_key/_fetch_page."""
        if self._divert_search_query:
            base = ('search', self._divert_search_query)
        elif self._divert_filter_genre:
            base = ('genre', self._divert_filter_genre)
        else:
            base = ('all',)
        return base + (self._divert_sort, self._divert_filter_unwatched)

    def _divert_section_page(self, section, offset, limit):
        key = local_cache.page_cache_key(
            'divert', section['key'], self._divert_cache_mode_key(), offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, DIVERT_CACHE_TTL_SECONDS,
            lambda: self._divert_section_page_uncached(section, offset, limit))

    def _divert_section_page_uncached(self, section, offset, limit):
        unwatched = self._divert_filter_unwatched
        if self._connector_client:
            raw = self._connector_client.section_items(
                section['key'], sort=self._divert_sort, limit=limit, offset=offset,
                genre=self._divert_filter_genre, search=self._divert_search_query or None,
                unwatched=unwatched)
            items = divert_source.parse_metadata_list(raw, self._connector_client.image_url)
            return items, divert_source.parse_total_size(raw)
        if self._divert_search_query:
            return self._plex_client.search_with_total(
                section['key'], self._divert_search_query, limit=limit, offset=offset)
        return self._plex_client.section_items_with_total(
            section['key'], sort=self._divert_sort, limit=limit, offset=offset,
            genre=self._divert_filter_genre, unwatched=unwatched)

    def _select_divert_section(self, index):
        if index >= len(self._divert_sections):
            return
        self._divert_active_section = index
        section = self._divert_sections[index]
        self._divert_last_library_key = section['key']
        self.addon.setSetting('divert.last_library', section['key'])
        # Reset the toolbar state: a search/filter/sort left over from a
        # previous library must never silently stick to this one (same
        # regression class already fixed once for Recommande/Categories).
        self._divert_sort = DIVERT_SORT_OPTIONS[0][0]
        self._divert_filter_genre = None
        self._divert_filter_unwatched = None
        self._divert_search_query = ''
        self._load_divert_section_items(section)

    def _load_divert_section_items(self, section):
        # page_size/prefetch_margin=50: only the visible portion of the grid
        # plus roughly the next/previous 50 items are ever fetched from the
        # server at once, matching the "50 before / 50 after" smoothness
        # requested -- items already loaded are kept (no eviction of
        # earlier pages once fetched, Kodi's panel control has no supported
        # way to evict/re-virtualize arbitrary items from the middle of an
        # already-populated list without breaking scroll position), so this
        # is forward-progressive loading rather than a true sliding window.
        # See docs/aura/decisions.md.
        self._divert_paged = paged_list.PagedList(
            lambda offset, limit: self._divert_section_page(section, offset, limit),
            page_size=50, prefetch_margin=50)
        error = None
        try:
            self._divert_paged.load_initial()
        except Exception as e:
            xbmc.log('Akasha Aura: section items load failed: {}'.format(e), xbmc.LOGERROR)
            error = e
        self._divert_items = self._divert_paged.items

        self._render_divert_toolbar(section)
        self._render_divert_status(section, error)

        try:
            panel = self.getControl(DIVERT_PANEL_ID)
            panel.reset()
            for item in self._divert_items:
                panel.addItem(_build_divert_list_item(item))
        except Exception as e:
            xbmc.log('Akasha Aura: panel render error: {}'.format(e), xbmc.LOGERROR)
        self._divert_placeholder_count = self._sync_placeholders(
            DIVERT_PANEL_ID, 0, self._divert_paged)

    def _render_divert_toolbar(self, section):
        try:
            type_label = 'Series TV' if section.get('type') == 'show' else 'Films'
            self.getControl(DIVERT_TYPE_LABEL_ID).setLabel(type_label)
        except RuntimeError:
            pass
        try:
            filter_label = next(
                label for value, label in DIVERT_FILTER_OPTIONS
                if value == self._divert_filter_unwatched)
            self.getControl(DIVERT_FILTER_BUTTON_ID).setLabel('Filtre: {}'.format(filter_label))
        except RuntimeError:
            pass
        try:
            sort_label = DIVERT_SORT_SHORT_LABELS.get(self._divert_sort, '-')
            self.getControl(DIVERT_SORT_BUTTON_ID).setLabel('Trier: {}'.format(sort_label))
        except RuntimeError:
            pass

    def _render_divert_status(self, section, error=None):
        try:
            status = self.getControl(DIVERT_STATUS_ID)
            if error:
                status.setLabel('{} — erreur de chargement'.format(section['title']))
            else:
                count = self._divert_paged.total if self._divert_paged.total is not None \
                    else len(self._divert_items)
                label = '{} — {} element(s)'.format(section['title'], count)
                if self._divert_search_query:
                    label += ' pour "{}"'.format(self._divert_search_query)
                if self._divert_filter_genre:
                    label += ' ({})'.format(self._divert_filter_genre)
                status.setLabel(label)
        except RuntimeError:
            pass

    def _divert_open_filter_menu(self):
        if not self._divert_sections:
            return
        idx = xbmcgui.Dialog().select(
            'Filtre', [label for _, label in DIVERT_FILTER_OPTIONS])
        if idx < 0:
            return
        self._divert_filter_unwatched = DIVERT_FILTER_OPTIONS[idx][0]
        self._load_divert_section_items(self._divert_sections[self._divert_active_section])

    def _divert_open_sort_menu(self):
        if not self._divert_sections:
            return
        idx = xbmcgui.Dialog().select(
            'Trier par', [label for _, label in DIVERT_SORT_OPTIONS])
        if idx < 0:
            return
        self._divert_sort = DIVERT_SORT_OPTIONS[idx][0]
        self._load_divert_section_items(self._divert_sections[self._divert_active_section])

    def _divert_open_genre_menu(self):
        if not self._divert_sections:
            return
        section = self._divert_sections[self._divert_active_section]
        try:
            if self._connector_client:
                genres = divert_source.parse_genres(
                    self._connector_client.section_genres(section['key']))
            else:
                genres = self._plex_client.section_genres(section['key'])
        except Exception as e:
            xbmc.log('Akasha Aura: divert genre load failed: {}'.format(e), xbmc.LOGERROR)
            genres = []
        if not genres:
            return
        idx = xbmcgui.Dialog().select('Genre', ['Tous'] + genres)
        if idx < 0:
            return
        self._divert_filter_genre = None if idx == 0 else genres[idx - 1]
        if self._divert_filter_genre:
            self._divert_search_query = ''
        self._load_divert_section_items(section)

    def _divert_reset_filters(self):
        if not self._divert_sections:
            return
        self._divert_sort = DIVERT_SORT_OPTIONS[0][0]
        self._divert_filter_genre = None
        self._divert_filter_unwatched = None
        self._divert_search_query = ''
        self._load_divert_section_items(self._divert_sections[self._divert_active_section])

    def _divert_play_item(self, item):
        # Playback resolution for Divertissement items is not decided yet
        # (see docs/aura/decisions.md) -- the single-item click handler
        # (_on_divert_item_selected) already only surfaces a notification
        # for non-show items, so the quick-action buttons mirror that same
        # placeholder rather than pretending to actually start playback.
        xbmcgui.Dialog().notification(
            'Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)

    def _divert_play_first(self):
        if self._divert_items:
            self._divert_play_item(self._divert_items[0])

    def _divert_play_random(self):
        if self._divert_items:
            self._divert_play_item(random.choice(self._divert_items))

    def _divert_add_to_playlist(self):
        if self._divert_items:
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Playlists : pas encore disponible', xbmcgui.NOTIFICATION_INFO,
                2000)

    def _sync_placeholders(self, control_id, current_placeholder_count, paged):
        """Skeleton loaders (plan a3f9c2e1 phase 5): replace whatever
        trailing placeholder items a control already has with a freshly
        sized run reflecting how many more items are actually left to load,
        so scrolling towards the loaded end shows dimmed silhouettes
        instead of the list abruptly stopping. No-op (returns 0) once the
        source is exhausted or its real total is unknown -- a placeholder
        implies "more is coming", which would be misleading otherwise.
        """
        try:
            control = self.getControl(control_id)
        except RuntimeError:
            return 0
        for _ in range(current_placeholder_count):
            try:
                control.removeItem(control.size() - 1)
            except Exception:
                break
        if paged is None or paged.exhausted or paged.total is None:
            return 0
        remaining = max(0, paged.total - len(paged.items))
        if paged.max_items is not None:
            # Rows like Recommande cap how many items they'll ever load
            # (a "quick highlight" row, not a full browse surface) --
            # never promise more placeholders than that cap allows.
            remaining = min(remaining, max(0, paged.max_items - len(paged.items)))
        new_count = min(remaining, PLACEHOLDER_ITEM_CAP)
        if new_count:
            try:
                control.addItems([_build_placeholder_list_item() for _ in range(new_count)])
            except Exception:
                return 0
        return new_count

    def _maybe_load_more_divert(self):
        if not self._divert_paged or not self._divert_sections:
            return
        try:
            position = self.getControl(DIVERT_PANEL_ID).getSelectedPosition()
        except RuntimeError:
            return
        try:
            new_items = self._divert_paged.maybe_load_more(position)
        except Exception as e:
            xbmc.log('Akasha Aura: Divertissement pagination fetch failed: {}'.format(e),
                     xbmc.LOGWARNING)
            return
        if not new_items:
            return
        self._divert_items = self._divert_paged.items
        try:
            panel = self.getControl(DIVERT_PANEL_ID)
            # Remove the stale trailing placeholders first: they were
            # standing in for exactly the items `new_items` now replaces
            # (see _sync_placeholders() -- ControlList has no "insert
            # before" primitive, so the real items are appended after
            # removal, then a fresh, shorter run of placeholders is added
            # back to represent whatever remains).
            for _ in range(self._divert_placeholder_count):
                try:
                    panel.removeItem(panel.size() - 1)
                except Exception:
                    break
            panel.addItems([_build_divert_list_item(item) for item in new_items])
        except Exception as e:
            xbmc.log('Akasha Aura: Divertissement append render error: {}'.format(e),
                     xbmc.LOGERROR)
        self._divert_placeholder_count = self._sync_placeholders(
            DIVERT_PANEL_ID, 0, self._divert_paged)
        section = self._divert_sections[self._divert_active_section]
        self._render_divert_status(section)

    def _load_other_games(self):
        for i, control_id in enumerate(GAME_BUTTON_IDS):
            try:
                btn = self.getControl(control_id)
            except RuntimeError:
                continue
            if i < len(self._other_games):
                btn.setLabel(self._other_games[i]['label'])
            else:
                btn.setLabel('')

    def _select_jeux_subtab(self, index):
        self._jeux_active_subtab = index
        self.setProperty('JeuxActiveSubtab', str(index))

        if index == JEUX_SUBTAB_OTHERS:
            self._load_other_games()
            try:
                self.getControl(JEUX_STATUS_ID).setLabel('Autres applications de jeu')
            except RuntimeError:
                pass
            return

        if index == JEUX_SUBTAB_STEAMLINK:
            client = self._get_steam_client(prompt_if_missing=True)
            if not client or not client.is_configured():
                self._set_jeux_panel([], 'SteamLink non configure — cle API et SteamID64 requis')
                return
            try:
                games = client.owned_games_sorted_by_recent()
            except steam_client.SteamAPIError as e:
                xbmc.log('Akasha Aura: Steam load failed: {}'.format(e), xbmc.LOGERROR)
                self._set_jeux_panel([], 'Erreur de chargement de la bibliotheque Steam')
                return
            self._jeux_items = [
                {'title': g['name'], 'thumb_url': g['box_art_url'], 'source': 'steam'}
                for g in games
            ]
            self._set_jeux_panel(self._jeux_items, '{} jeu(x) Steam'.format(len(games)))
            return

        if index == JEUX_SUBTAB_MOONLIGHT:
            client = self._get_sunshine_client(prompt_if_missing=True)
            if not client or not client.is_configured():
                self._set_jeux_panel([], 'Sunshine non configure — URL, utilisateur et mot de passe requis')
                return
            try:
                apps = client.apps()
            except sunshine_client.SunshineAPIError as e:
                xbmc.log('Akasha Aura: Sunshine load failed: {}'.format(e), xbmc.LOGERROR)
                self._set_jeux_panel([], 'Erreur de chargement des applications Sunshine')
                return
            self._jeux_items = [
                {'title': a['name'], 'thumb_url': a['box_art_url'], 'source': 'sunshine'}
                for a in apps
            ]
            self._set_jeux_panel(self._jeux_items, '{} application(s) Sunshine'.format(len(apps)))

    def _select_app_subtab(self, index):
        self._app_subtab = index
        self.setProperty('AppActiveSubtab', str(index))
        if index == APP_SUBTAB_MES_APPS:
            self._get_sub_window('app', aura_app.AuraAppWindow, 'AuraApp.xml').doModal()
            self._load_pinned_apps()
        elif index == APP_SUBTAB_STORE:
            self._get_sub_window('store', aura_store.AuraStoreWindow, 'AuraStore.xml').doModal()
            self._load_pinned_apps()

    def _set_jeux_panel(self, items, status_text):
        try:
            self.getControl(JEUX_STATUS_ID).setLabel(status_text)
        except RuntimeError:
            pass
        try:
            panel = self.getControl(JEUX_PANEL_ID)
            panel.reset()
            for item in items:
                li = xbmcgui.ListItem(item['title'])
                if item.get('thumb_url'):
                    li.setArt({'thumb': item['thumb_url']})
                panel.addItem(li)
        except Exception as e:
            xbmc.log('Akasha Aura: Jeux panel render error: {}'.format(e), xbmc.LOGERROR)

    def _get_steam_client(self, prompt_if_missing=False):
        api_key = self.addon.getSetting('steam.api_key')
        steam_id = self.addon.getSetting('steam.steam_id')
        if prompt_if_missing and not (api_key and steam_id):
            api_key, steam_id = self._prompt_steam_credentials(api_key, steam_id)
        return steam_client.SteamClient(api_key, steam_id, timeout=15)

    def _prompt_steam_credentials(self, api_key, steam_id):
        if not api_key:
            kb = xbmc.Keyboard(api_key, 'Cle API Steam (Web API)')
            kb.doModal()
            if kb.isConfirmed():
                api_key = kb.getText().strip()
                self.addon.setSetting('steam.api_key', api_key)
        if api_key and not steam_id:
            kb = xbmc.Keyboard(steam_id, 'SteamID64')
            kb.doModal()
            if kb.isConfirmed():
                steam_id = kb.getText().strip()
                self.addon.setSetting('steam.steam_id', steam_id)
        return api_key, steam_id

    def _get_sunshine_client(self, prompt_if_missing=False):
        server_url = self.addon.getSetting('sunshine.server_url')
        username = self.addon.getSetting('sunshine.username')
        password = self.addon.getSetting('sunshine.password')
        if prompt_if_missing and not (server_url and username and password):
            server_url, username, password = self._prompt_sunshine_credentials(
                server_url, username, password)
        return sunshine_client.SunshineClient(server_url, username, password, timeout=15)

    def _prompt_sunshine_credentials(self, server_url, username, password):
        if not server_url:
            kb = xbmc.Keyboard(server_url, 'URL du serveur Sunshine (ex: https://192.168.1.x:47990)')
            kb.doModal()
            if kb.isConfirmed():
                server_url = kb.getText().strip()
                self.addon.setSetting('sunshine.server_url', server_url)
        if server_url and not username:
            kb = xbmc.Keyboard(username, "Nom d'utilisateur Sunshine")
            kb.doModal()
            if kb.isConfirmed():
                username = kb.getText().strip()
                self.addon.setSetting('sunshine.username', username)
        if server_url and username and not password:
            kb = xbmc.Keyboard(password, 'Mot de passe Sunshine')
            kb.setHiddenInput(True)
            kb.doModal()
            if kb.isConfirmed():
                password = kb.getText().strip()
                self.addon.setSetting('sunshine.password', password)
        return server_url, username, password

    def _load_pinned_apps(self):
        pinned_ids = addons_inventory.parse_pinned(self.addon.getSetting('app.pinned'))
        self._pinned_apps = []

        try:
            status = self.getControl(2029)
        except RuntimeError:
            status = None

        if not pinned_ids:
            if status:
                status.setLabel('Aucune application epinglee — utilisez "Gerer les applications"')
            for control_id in APP_TILE_IDS:
                try:
                    self.getControl(control_id).setLabel('')
                except RuntimeError:
                    continue
            return

        try:
            request = addons_inventory.build_get_addons_request()
            raw_response = xbmc.executeJSONRPC(json.dumps(request))
            all_addons = addons_inventory.parse_get_addons_response(raw_response)
        except Exception as e:
            xbmc.log('Akasha Aura: App inventory load failed: {}'.format(e), xbmc.LOGERROR)
            all_addons = []

        by_id = {a['addonid']: a for a in all_addons}
        self._pinned_apps = [by_id[aid] for aid in pinned_ids if aid in by_id]

        if status:
            status.setLabel('Applications epinglees')

        for i, control_id in enumerate(APP_TILE_IDS):
            try:
                btn = self.getControl(control_id)
            except RuntimeError:
                continue
            if i < len(self._pinned_apps):
                btn.setLabel(self._pinned_apps[i]['name'])
            else:
                btn.setLabel('')

    def _get_sub_window(self, key, cls, xml_file):
        """Return a cached sub-window instance, constructing it only once.

        See the note in __init__ about why re-instantiating these on every
        open exhausts Kodi's dynamic window ID pool.
        """
        window = self._sub_windows.get(key)
        if window is None:
            window = cls(xml_file, self.addon.getAddonInfo('path'), 'Default', '1080i')
            self._sub_windows[key] = window
        return window

    def _show_tab(self, index):
        index = index % len(config.TABS)
        self.active_tab = index
        self.setProperty('AuraActiveTab', str(index))

        if index == TAB_DIVERTISSEMENT:
            self.setProperty('DivertView', self._divert_view)
            self.setProperty('DivertLibraryTab', str(self._divert_library_tab))
        elif index == TAB_JEUX:
            self.setProperty('JeuxActiveSubtab', str(self._jeux_active_subtab))
        elif index == TAB_APP:
            self.setProperty('AppActiveSubtab', str(self._app_subtab))

        # AuraWindow is now a single long-lived instance for the whole Kodi
        # session (see the note in __init__): onInit() -- and so
        # _load_divertissement() -- only ever runs once. If that one
        # attempt hit a transient failure (network hiccup, connector
        # briefly unreachable), the sidebar stays empty for the rest of the
        # session with no way to recover -- retry it whenever the user
        # (re)selects the Divertissement tab and it's still empty, so
        # navigating away and back is enough to pick back up once the
        # network/connector recovers.
        if index == TAB_DIVERTISSEMENT and self._divert_load_attempted and not self._divert_sections:
            self._load_divertissement()
            self._restore_divert_view(focus=False)

    def _update_bar_focused(self):
        """Update the top-bar focused property used by the retract animation."""
        focused = self.getFocusId()
        is_bar_focused = focused in BAR_CONTROL_IDS
        self.setProperty('AuraBarFocused', 'true' if is_bar_focused else 'false')
        self._layout_top_modules(focused)

    def _layout_top_modules(self, focused):
        """Correctif c7f0636a: Divertissement/Jeux/App must stay a single
        contiguous group (pill of the focused one + the other two icons
        immediately following), never leaving one of them isolated with a
        large gap before it -- Kodi has no native flexbox-style reflow, so
        this recomputes each one's <left> by hand and repositions the
        button/pill/icon controls via setPosition() every time focus
        moves onto/off of one of them (called from _update_bar_focused(),
        itself run after every action -- including onInit's own initial
        call, so the very first render is already laid out correctly)."""
        try:
            focused_index = TAB_BUTTON_IDS.index(focused)
        except ValueError:
            focused_index = None
        x = MODULE_LAYOUT_START_X
        for i, (button_id, pill_id, icon_id) in enumerate(MODULE_CONTROL_IDS):
            try:
                self.getControl(pill_id).setPosition(x, MODULE_PILL_TOP)
                self.getControl(button_id).setPosition(x + MODULE_BUTTON_OFFSET, MODULE_ICON_TOP)
                self.getControl(icon_id).setPosition(
                    x + MODULE_ICON_OFFSETS[i], MODULE_ICON_TOPS[i])
            except RuntimeError:
                pass
            x += MODULE_PILL_WIDTH if i == focused_index else MODULE_ITEM_WIDTH

    def onAction(self, action):
        aid = action.getId()
        if aid == ACTION_MENU:
            self._open_settings_panel()
            return
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        focused = self.getFocusId()
        # Left/Right across the whole top bar (search, the 3 modules, gear)
        # is a single native <onleft>/<onright> loop declared directly in
        # Aura.xml; no Python override needed there. Found on-device (plan
        # 04bda1b4): a bare button with no <texturefocus> at all appears to
        # get silently skipped by Kodi's own focus resolution -- an earlier
        # attempt to also redirect focus from Python compounded on top of
        # that native skip instead of replacing it, causing a double hop.
        # Adding a (barely visible) texturefocus to 2001/2002/2003 fixed
        # the native loop on its own; this handler now only keeps
        # AuraActiveTab/content in sync with whichever module ends up
        # focused, without moving focus itself.
        if focused in TAB_BUTTON_IDS and TAB_BUTTON_IDS.index(focused) != self.active_tab:
            self._show_tab(TAB_BUTTON_IDS.index(focused))
            self._update_bar_focused()
        if aid == ACTION_MOVE_DOWN and focused in TAB_BUTTON_IDS:
            self._focus_first_subtab()
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_UP and focused in (DIVERT_SUBTAB_IDS + JEUX_SUBTAB_IDS + APP_SUBTAB_IDS):
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            self._update_bar_focused()
            return
        # NOTE (known issue, see docs/aura/decisions.md): pressing Up from
        # DIVERT_PANEL_ID's grid lands on the main tab bar (2001) instead of
        # the Bibliotheque tab button (3100), even though the grid's XML
        # declares <onup>3100</onup> and 3100 is confirmed visible/enabled
        # at that moment (verified on-device with a System.CurrentControlID
        # debug label). Neither an explicit Python-side focused==
        # DIVERT_PANEL_ID interception nor per-control <visible> duplication
        # changed this -- Kodi's native navigation appears to resolve Up
        # geometrically for this horizontal list rather than honouring the
        # explicit onup. Not a dead end (2001 is a perfectly navigable
        # state), so left as a documented quirk rather than blocking this
        # release.
        super().onAction(action)
        if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_MOVE_UP, ACTION_MOVE_DOWN):
            focused = self.getFocusId()
            # DIVERT_PANEL_ID is a wrapping grid (scrolls vertically), so
            # Up/Down are its primary scroll directions now -- Left/Right
            # only move a column within the currently loaded rows, kept
            # here too in case a future layout changes column count.
            if focused == DIVERT_PANEL_ID:
                self._maybe_load_more_divert()
            elif focused in RECO_LIST_IDS and aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT):
                self._maybe_load_more_reco(focused)
        self._update_bar_focused()

    def _focus_first_subtab(self):
        """Move focus from the main tab to the first meaningful content control."""
        try:
            if self.active_tab == TAB_DIVERTISSEMENT:
                if self._divert_view == 'library':
                    self.setFocus(self.getControl(DIVERT_SUBTAB_IDS[self._divert_library_tab]))
                else:
                    lst = self.getControl(RECO_LIST_IDS[0])
                    if lst.size() > 0:
                        lst.selectItem(0)
                    self.setFocus(lst)
            elif self.active_tab == TAB_JEUX:
                self.setFocus(self.getControl(JEUX_SUBTAB_IDS[self._jeux_active_subtab]))
            elif self.active_tab == TAB_APP:
                self.setFocus(self.getControl(APP_SUBTAB_IDS[self._app_subtab]))
        except Exception as e:
            xbmc.log('Akasha Aura: focus first subtab failed: {}'.format(e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID in TAB_BUTTON_IDS:
            self._show_tab(TAB_BUTTON_IDS.index(controlID))
        elif controlID in DIVERT_SUBTAB_IDS:
            self._select_library_tab(DIVERT_SUBTAB_IDS.index(controlID))
        elif controlID in JEUX_SUBTAB_IDS:
            self._select_jeux_subtab(JEUX_SUBTAB_IDS.index(controlID))
        elif controlID in APP_SUBTAB_IDS:
            self._select_app_subtab(APP_SUBTAB_IDS.index(controlID))
        elif controlID in GAME_BUTTON_IDS:
            idx = GAME_BUTTON_IDS.index(controlID)
            if idx < len(self._other_games):
                action = self._other_games[idx]['action']
                if action:
                    xbmc.executebuiltin(action)
        elif controlID == JEUX_PANEL_ID:
            self._on_jeux_item_selected()
        elif controlID in APP_TILE_IDS:
            idx = APP_TILE_IDS.index(controlID)
            if idx < len(self._pinned_apps):
                xbmc.executebuiltin('RunAddon({})'.format(self._pinned_apps[idx]['addonid']))
        elif controlID == DIVERT_SIDEBAR_ID:
            self._on_sidebar_item_selected()
        elif controlID == 3402:
            self._manage_libraries()
        elif controlID == DIVERT_PANEL_ID:
            self._on_divert_item_selected()
        elif controlID == CATEGORY_PANEL_ID:
            self._on_category_genre_selected()
        elif controlID == DIVERT_FILTER_BUTTON_ID:
            self._divert_open_filter_menu()
        elif controlID == DIVERT_SORT_BUTTON_ID:
            self._divert_open_sort_menu()
        elif controlID == DIVERT_GENRE_BUTTON_ID:
            self._divert_open_genre_menu()
        elif controlID == DIVERT_PLAY_BUTTON_ID:
            self._divert_play_first()
        elif controlID == DIVERT_SHUFFLE_BUTTON_ID:
            self._divert_play_random()
        elif controlID == DIVERT_PLAYLIST_BUTTON_ID:
            self._divert_add_to_playlist()
        elif controlID == DIVERT_RESET_BUTTON_ID:
            self._divert_reset_filters()
        elif controlID == MODULE_SEARCH_ID:
            self._open_search()
        elif controlID == GEAR_BUTTON_ID:
            self._open_settings_menu()

    def _on_jeux_item_selected(self):
        try:
            pos = self.getControl(JEUX_PANEL_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._jeux_items)):
            return
        item = self._jeux_items[pos]
        # Launching a specific game/app is not reliably scriptable (Steam
        # Link and Moonlight are streaming clients, not launchers with a
        # documented deep-link API) — surface the title and open the
        # relevant streaming client generally, consistent with the
        # placeholder pattern used for Divertissement/App tiles.
        if item['source'] == 'steam':
            xbmc.executebuiltin('RunAddon(plugin.program.steamlink)')
        else:
            xbmc.executebuiltin('RunAddon(plugin.program.moonlight-qt)')
        xbmcgui.Dialog().notification('Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)

    def _on_sidebar_item_selected(self):
        try:
            pos = self.getControl(DIVERT_SIDEBAR_ID).getSelectedPosition()
        except RuntimeError:
            return
        if pos == DIVERT_SIDEBAR_HOME_INDEX:
            self._activate_home()
            return
        more_index = len(self._divert_sections) + 1
        if pos == more_index:
            self._manage_libraries()
            return
        section_index = pos - 1
        if 0 <= section_index < len(self._divert_sections):
            self._activate_library(section_index)

    def _open_search(self):
        """Module 0: unified search (plan 04bda1b4 phase 2)."""
        kb = xbmc.Keyboard('', 'Rechercher')
        kb.doModal()
        if not kb.isConfirmed():
            return
        query = kb.getText().strip()
        if not query:
            return
        self._run_unified_search(query)

    def _run_unified_search(self, query):
        groups = []  # list of (category_label, [(result_label, callback), ...])

        groups.append(('Films et series', self._search_divert(query)))
        groups.append(('Jeux', self._search_games(query)))
        groups.append(('Applications', self._search_apps(query)))
        groups.append(('Parametres', self._search_settings(query)))

        flat_labels = []
        flat_callbacks = []
        for category, results in groups:
            if not results:
                continue
            flat_labels.append('-- {} --'.format(category))
            flat_callbacks.append(None)
            for label, callback in results:
                flat_labels.append('   {}'.format(label))
                flat_callbacks.append(callback)

        if not flat_callbacks:
            xbmcgui.Dialog().notification(
                'Akasha Aura', 'Aucun resultat pour "{}"'.format(query),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return

        choice = xbmcgui.Dialog().select(
            'Resultats pour "{}"'.format(query), flat_labels)
        if choice < 0 or flat_callbacks[choice] is None:
            return
        flat_callbacks[choice]()

    def _search_divert(self, query):
        """Search movies/shows across every Divertissement library section
        (Plex's search() is per-section, so this fans out over the small
        number of sections rather than a single global-hub call -- there is
        no such global endpoint wired in plex_client.py/connector_client.py
        today)."""
        results = []
        query_lower = query.lower()
        for section in self._divert_sections:
            try:
                if self._connector_client:
                    raw = self._connector_client.section_items(section['key'], search=query)
                    items = divert_source.parse_metadata_list(
                        raw, self._connector_client.image_url)
                else:
                    items = self._plex_client.search(section['key'], query)
            except Exception as e:
                xbmc.log('Akasha Aura: search failed for section {}: {}'.format(
                    section['key'], e), xbmc.LOGWARNING)
                continue
            for item in items:
                if query_lower not in item['title'].lower():
                    continue
                results.append((
                    '{} ({})'.format(item['title'], section['title']),
                    self._make_search_divert_callback(section, item)))
        return results[:20]

    def _make_search_divert_callback(self, section, item):
        def _callback():
            if section['type'] == 'show':
                self._open_show(item)
            else:
                xbmcgui.Dialog().notification(
                    'Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)
        return _callback

    def _search_games(self, query):
        # Searches the static shortcuts list (games.DATA.xml, already
        # loaded at __init__) rather than live-fetching the full Steam/
        # Sunshine catalogs on every keystroke-free search -- keeps the
        # search responsive; a documented scope limitation, see
        # docs/aura/decisions.md.
        query_lower = query.lower()
        results = []
        for game in self._games:
            if query_lower in (game.get('label') or '').lower():
                results.append((game['label'], self._make_search_game_callback(game)))
        return results[:20]

    def _make_search_game_callback(self, game):
        action = game.get('action') or ''

        def _callback():
            if action:
                xbmc.executebuiltin(action)
        return _callback

    def _search_apps(self, query):
        query_lower = query.lower()
        results = []
        try:
            request = addons_inventory.build_get_addons_request()
            raw_response = xbmc.executeJSONRPC(json.dumps(request))
            installed = addons_inventory.parse_get_addons_response(raw_response)
        except Exception as e:
            xbmc.log('Akasha Aura: search installed apps failed: {}'.format(e), xbmc.LOGWARNING)
            installed = []
        installed_ids = set()
        for addon in installed:
            installed_ids.add(addon['addonid'])
            if query_lower in addon['name'].lower():
                results.append((
                    '{} (installee)'.format(addon['name']),
                    self._make_search_app_callback(addon['addonid'])))
        try:
            manifest = store_manifest.load_manifest(self.addon_path)
            catalog = store_manifest.with_install_status(manifest, installed_ids)
        except Exception as e:
            xbmc.log('Akasha Aura: search store catalog failed: {}'.format(e), xbmc.LOGWARNING)
            catalog = []
        for entry in catalog:
            if entry.get('installed'):
                continue
            if query_lower in (entry.get('name') or '').lower():
                results.append((
                    '{} (a installer)'.format(entry['name']),
                    self._make_search_store_callback()))
        return results[:20]

    def _make_search_app_callback(self, addonid):
        def _callback():
            xbmc.executebuiltin('RunAddon({})'.format(addonid))
        return _callback

    def _make_search_store_callback(self):
        def _callback():
            self._show_tab(TAB_APP)
            self._select_app_subtab(APP_SUBTAB_STORE)
            try:
                self.setFocus(self.getControl(TAB_BUTTON_IDS[TAB_APP]))
            except RuntimeError:
                pass
        return _callback

    def _search_settings(self, query):
        query_lower = query.lower()
        results = []
        for label, callback in self._settings_menu_options():
            if query_lower in label.lower():
                results.append((label, callback))
        return results

    def _settings_menu_options(self):
        """The gear's context menu entries. Originally 3 separate "Parametres
        Kodi/LibreELEC/Akasha" entries (plan 04bda1b4 section 4); plan
        a5a87f03 explicitly asks for these to be merged into a single
        "Parametres" entry opening the unified settings panel instead
        (see docs/settings/decisions.md) -- the action items below stay
        unchanged, they are not "settings" per that plan's own wording."""
        return [
            ('Parametres', self._open_settings_panel),
            ('Se connecter (Connector Akasha OS)', self._reconnect_connector),
            ('Mise en veille', self._settings_sleep),
            ('Redemarrer', self._settings_restart_menu),
            ('Arret du systeme', self._settings_shutdown),
        ]

    def _reconnect_connector(self):
        """Manual, explicit counterpart to _load_divertissement()'s silent
        prompt_if_missing=False: the only place a user is actually present
        to type a password into the blocking Keyboard dialog, so this is
        the only call site allowed to pass prompt_if_missing=True."""
        connector = self._get_connector_client(prompt_if_missing=True)
        if not connector:
            return
        try:
            self._divert_sections = divert_source.parse_sections(connector.sections())
        except connector_client.ConnectorAPIError as e:
            xbmc.log('Akasha Aura: connector reconnect failed: {}'.format(e), xbmc.LOGWARNING)
            self.addon.setSetting('connector.session_token', '')
            xbmcgui.Dialog().notification(
                'Akasha', 'Connexion au Connector echouee', xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        self._connector_client = connector
        self._plex_client = None
        xbmcgui.Dialog().notification(
            'Akasha', 'Connecte au Connector Akasha OS', xbmcgui.NOTIFICATION_INFO, 3000)
        self._restore_divert_view(focus=False)

    def _open_settings_menu(self):
        """Settings gear: context menu (plan 04bda1b4 phase 3). Uses the
        native contextmenu() dialog -- same mechanism already relied on by
        script.akasha.guide for its own quick-access menu -- rather than a
        custom XML popup, so it inherits the skin's standard placement/
        close-on-select/close-on-back behaviour for free."""
        options = self._settings_menu_options()
        choice = xbmcgui.Dialog().contextmenu([label for label, _ in options])
        if choice < 0:
            return
        options[choice][1]()

    def _open_settings_panel(self):
        """Unified settings panel (plan a5a87f03): categories list + curated
        actions, replacing the old direct Kodi/LibreELEC/Akasha shortcuts."""
        win = self._get_sub_window(
            'settings_panel', aura_settings_panel.AuraSettingsPanelWindow,
            'AuraSettingsPanel.xml')
        # Aura itself is a type="dialog" window (see docs/aura/decisions.md
        # on why -- it needs to sit on top of native Kodi Home as a safety
        # net), which means it keeps rendering on top of any *base* window
        # a row's action might activate (Kodi's own Settings, System,
        # Profiles... windows are base windows, not dialogs) -- addon
        # dialogs (LibreELEC settings, Plex, Jellyfin...) stack fine on
        # their own since they are dialogs too, but base windows would
        # silently open invisibly behind Aura otherwise. The panel is told
        # to close Aura first for every row, uniformly, rather than trying
        # to special-case which actions need it.
        win.parent_window = self
        win.doModal()

    def _settings_sleep(self):
        # Reuses the exact same standby+wake-on-input script already used
        # by script.akasha.guide's "Mise en veille" entry, rather than
        # duplicating it -- see docs/aura/decisions.md.
        if not xbmcgui.Dialog().yesno(
                'Akasha', "Mettre l'appareil et le televiseur en veille ?"):
            return
        script = '/storage/.kodi/scripts/akasha-sleep.py'
        try:
            subprocess.Popen([sys.executable, script],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            xbmc.log('Akasha Aura: sleep launch error: {}'.format(e), xbmc.LOGERROR)

    def _settings_restart_menu(self):
        choice = xbmcgui.Dialog().select(
            'Redemarrer', ['Redemarrer Akasha', 'Redemarrer le systeme'])
        if choice == 0:
            self._settings_restart_akasha()
        elif choice == 1:
            self._settings_restart_system()

    def _settings_restart_akasha(self):
        # Same mechanism as script.akasha.guide's "Redemarrer Akasha":
        # restarting the kodi service is the only Akasha-only restart
        # available today (there is no app-level relaunch separate from
        # the Kodi process) -- flagged as an assumption in the recette
        # report per the plan's own instruction (section 8).
        if not xbmcgui.Dialog().yesno('Akasha', 'Redemarrer Akasha maintenant ?'):
            return
        try:
            with open('/tmp/.kodi-restart', 'w') as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
        subprocess.Popen(['systemctl', 'restart', 'kodi'], start_new_session=True)

    def _settings_restart_system(self):
        if not xbmcgui.Dialog().yesno('Akasha', 'Redemarrer le systeme maintenant ?'):
            return
        subprocess.Popen(['systemctl', 'reboot'], start_new_session=True)

    def _settings_shutdown(self):
        # Same splash + CEC-TV-off sequence as script.akasha.guide/
        # script.akasha.settings' shutdown action.
        if not xbmcgui.Dialog().yesno(
                'Akasha', 'Eteindre le systeme maintenant ?\n(La TV sera aussi eteinte via CEC)'):
            return
        subprocess.run(['/storage/.kodi/scripts/show-splash.sh',
                         '/storage/.kodi/media/splash-shutdown.png', '1'])
        subprocess.Popen(['systemctl', 'poweroff'], start_new_session=True)

    def _manage_libraries(self):
        """Show a dialog to pin/unpin and reorder every library section."""
        if not self._all_divert_sections:
            return

        all_sections = list(self._all_divert_sections)
        pinned_set = set(self._divert_pinned_libraries)

        options = []
        actions = []
        for section in all_sections:
            key = section['key']
            pinned = key in pinned_set
            options.append(
                '{} {}'.format('Desepingler' if pinned else 'Epingler', section['title']))
            actions.append(('toggle', key))
            idx = all_sections.index(section)
            if idx > 0:
                options.append('Monter {}'.format(section['title']))
                actions.append(('up', key))
            if idx < len(all_sections) - 1:
                options.append('Descendre {}'.format(section['title']))
                actions.append(('down', key))

        dialog = xbmcgui.Dialog()
        idx = dialog.select('Gerer les bibliotheques', options)
        if idx < 0:
            return

        action, key = actions[idx]
        if action == 'toggle':
            if key in pinned_set:
                pinned_set.remove(key)
            else:
                pinned_set.add(key)
            self._divert_pinned_libraries = list(pinned_set)
            self.addon.setSetting(
                'divert.pinned_libraries',
                config.serialize_pinned(self._divert_pinned_libraries))
        elif action in ('up', 'down'):
            order = [s['key'] for s in all_sections]
            i = order.index(key)
            if action == 'up' and i > 0:
                order[i - 1], order[i] = order[i], order[i - 1]
            elif action == 'down' and i < len(order) - 1:
                order[i], order[i + 1] = order[i + 1], order[i]
            self._divert_library_order = order
            self.addon.setSetting(
                'divert.library_order', config.serialize_pinned(order))

        self._load_divertissement()
        # Pin/reorder can change section indices, so returning to a
        # specific library by stale index would be unsafe -- go back to
        # Accueil, the same safe default as an empty/first load.
        self._activate_home()

    def _open_show(self, item):
        """Open AuraShowWindow with the active Connector or direct Plex client."""
        client = self._connector_client or self._plex_client
        if not client:
            xbmcgui.Dialog().notification(
                'Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)
            return
        show_window = self._get_sub_window(
            'show', aura_show.AuraShowWindow, 'AuraShow.xml')
        show_window.client = client
        show_window.show_title = item['title']
        show_window.show_rating_key = item['rating_key']
        show_window.doModal()

    def _on_divert_item_selected(self):
        try:
            pos = self.getControl(DIVERT_PANEL_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._divert_items)):
            return
        item = self._divert_items[pos]
        section = self._divert_sections[self._divert_active_section]

        if section['type'] == 'show':
            self._open_show(item)
        else:
            # Playback delegation is not decided yet (see docs/aura/decisions.md);
            # for now just surface the title so selection feels responsive.
            xbmcgui.Dialog().notification(
                'Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)

    def _on_home_press_action(self, action):
        """React to a repeated Home press while Aura is already open.

        'single' -> return to the main Divertissement tab (close any sub-window).
        'double' -> open the minimal app switcher.
        """
        xbmc.log('Akasha Aura: home press action: {}'.format(action), xbmc.LOGINFO)
        if action == 'single':
            self._close_sub_windows()
            self._show_tab(0)
            try:
                self.setFocus(self.getControl(TAB_BUTTON_IDS[0]))
            except RuntimeError:
                pass
        elif action == 'double':
            switcher = self._get_sub_window(
                'app_switcher', _HomePressAppSwitcher, 'AuraSwitcher.xml')
            switcher.parent_window = self
            switcher.doModal()

    def _close_sub_windows(self):
        """Close any currently open sub-windows so we land back on Aura shell."""
        for key in list(self._sub_windows.keys()):
            window = self._sub_windows[key]
            try:
                window.close()
            except Exception:
                pass


def _build_divert_list_item(item):
    li = xbmcgui.ListItem(item['title'], divert_source.item_subtitle(item))
    if item.get('thumb_url'):
        li.setArt({'thumb': item['thumb_url']})
    return li


def _build_placeholder_list_item():
    """Skeleton loader item (plan a3f9c2e1 phase 5): an empty ListItem
    flagged via a custom property so the skin can render a dimmed
    silhouette instead of a poster/label, standing in for a real item not
    fetched yet. See _sync_placeholders()."""
    li = xbmcgui.ListItem('')
    li.setProperty('IsPlaceholder', '1')
    return li


class _HomePressAppSwitcher(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_window = None
        self._actions = []

    def onInit(self):
        panel = self.getControl(100)
        panel.reset()
        self._actions = []
        apps = self.parent_window._pinned_apps if self.parent_window else []
        for app in apps:
            item = xbmcgui.ListItem(app['name'])
            if app.get('thumbnail'):
                item.setArt({'thumb': app['thumbnail']})
            panel.addItem(item)
            self._actions.append('RunAddon({})'.format(app['addonid']))
        for label, action, icon in (
                ('Parametres Akasha', 'RunAddon(script.akasha.settings)', 'icon-gear.png'),
                ('Guide Akasha', 'RunScript(script.akasha.guide)', 'tab-divertissement.png'),
                ('Mode Ambiant', 'RunScript(script.akasha.ambient)', 'tab-app.png')):
            item = xbmcgui.ListItem(label)
            item.setArt({'thumb': icon})
            panel.addItem(item)
            self._actions.append(action)
        panel.selectItem(0)
        self.setFocus(panel)

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)

    def onClick(self, controlID):
        if controlID != 100:
            return
        pos = self.getControl(100).getSelectedPosition()
        if not (0 <= pos < len(self._actions)):
            return
        action = self._actions[pos]
        self.close()
        xbmc.executebuiltin(action)

