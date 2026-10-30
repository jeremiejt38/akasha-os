"""Akasha Aura — main WindowXML orchestration.

Milestone 1 (socle, see docs/aura/roadmap.md): navigable 3-tab shell with
placeholder content. Milestone 2 adds Plex entertainment rows via
plex_client.py. Later milestones fill the Games and App tabs
(addons_inventory.py, store_manifest.py) without changing this navigation
skeleton.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
import random
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import aura_menu
import i18n

import addons_inventory
import aura_app
import aura_detail
import aura_search
import aura_settings_panel
import aura_store
import config
import context_sheet
import gui_guard
import settings_press_handler
import osd_menu
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

# The Divertissement/Jeux/App tabs are a single horizontal list control
# (same mechanism as the native skin main menu, see Aura.xml): the
# focused slot widens to the pill and the container animates the slide
# itself via scrolltime. Tab index == selected item position.
TAB_LIST_ID = 2007

# Main-tab IDs in the same order as config.TABS.
TAB_DIVERTISSEMENT = 0
TAB_JEUX = 1
TAB_APP = 2


def _ui_locked(fn):
    """Serialize a multi-step control mutation under the window's
    `_ui_lock` (an RLock, so worker render tails stay atomic across
    composed helpers). A worker's reset() landing between an input-path
    size() and getSelectedPosition() was the SEGV class in the October
    crash logs -- every list rebuild and every guarded selection read
    shares this lock so check-then-act races cannot interleave."""
    def wrapper(self, *args, **kwargs):
        with self._ui_lock:
            return fn(self, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper

# Module 0 (search) and the settings gear are part of the same top bar but
# are not "tabs" -- neither switches active_tab/content, see plan 04bda1b4.
MODULE_SEARCH_ID = 2000
GEAR_BUTTON_ID = 2004

# Home-window property the boot veil (skin-patches/patch_home_boot_veil.py)
# watches: set as soon as Aura owns the screen so the loading screen lifts.
HOME_READY_PROPERTY = 'Akasha.AuraReady'

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_MENU = 163
ACTION_CONTEXT_MENU = 117

DIVERT_SIDEBAR_ID = 3310
DIVERT_STATUS_ID = 3220
DIVERT_PANEL_ID = 3230
# Plex's expanded rail puts fixed entries above the libraries: Search,
# Home -- then a divider, the library sections and Plus. Plex cloud-only
# entries (profile, My Lists, playlists, On Plex) are hidden: they only
# surfaced "unavailable" notifications.
DIVERT_SIDEBAR_PROFILE_INDEX = 0
DIVERT_SIDEBAR_LISTS_INDEX = 1
DIVERT_SIDEBAR_SEARCH_INDEX = 2
DIVERT_SIDEBAR_HOME_INDEX = 3
DIVERT_SIDEBAR_LIBS_HEADER_INDEX = 4
DIVERT_SIDEBAR_LIBS_OFFSET = 5
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
RECO_ROW4_LABEL_ID = 5400
RECO_ROW4_LIST_ID = 5410
RECO_ROW5_LABEL_ID = 5500
RECO_ROW5_LIST_ID = 5510
# The 5 visible row slots form a sliding viewport over the hub list returned
# by /hubs/promoted (Plex "For You"): Plex keeps the focused row pinned at a
# fixed screen position and scrolls the rows above off the top, which Kodi
# can't clip natively -- so slot contents are re-bound when focus reaches an
# edge slot instead of scrolling the group pixel by pixel. See
# docs/plex-parity/SPEC.md.
RECO_SLOT_IDS = (
    (RECO_ON_DECK_LABEL_ID, RECO_ON_DECK_LIST_ID),
    (RECO_RECENT_LABEL_ID, RECO_RECENT_LIST_ID),
    (RECO_RELEASES_LABEL_ID, RECO_RELEASES_LIST_ID),
    (RECO_ROW4_LABEL_ID, RECO_ROW4_LIST_ID),
    (RECO_ROW5_LABEL_ID, RECO_ROW5_LIST_ID),
)
RECO_LIST_IDS = tuple(list_id for _, list_id in RECO_SLOT_IDS)
# Landscape twin of each reco slot list: a hub carrying style='hero'
# (e.g. home.continue "Continue Watching") renders as Plex's 16:9 banner
# cards instead of posters. Both lists of a slot share geometry and row
# data; the AuraRowStyle{slot} window property picks which is visible and
# navigation resolves against the effective id (_reco_slot_list_id).
RECO_LANDSCAPE_IDS = tuple(list_id + 1 for _, list_id in RECO_SLOT_IDS)
RECO_ALL_LIST_IDS = RECO_LIST_IDS + RECO_LANDSCAPE_IDS
# Home tab strip (Plex "For You" / "Trending" / "Activity"), only on the
# Divertissement Accueil view -- the library view has its own strip
# (3050/3100/3060). "Activité" has no usable public endpoint (the feed is a
# private GraphQL API on community.plex.tv), so it shows an honest
# empty-state instead of fake rows.
HOME_TAB_IDS = (3070, 3071, 3072)
HOME_TAB_FOR_YOU = 0
HOME_TAB_TRENDING = 1
HOME_TAB_ACTIVITY = 2
RECO_CACHE_TTL_SECONDS = 120
RECO_ON_DECK_FETCH_LIMIT = 50  # over-fetch before client-side section filtering
RECO_MAX_ITEMS_PER_ROW = 100

# Categories content, rendered inline instead of a separate doModal() dialog
# (previously aura_genres.AuraGenresWindow).
CATEGORY_STATUS_ID = 6020
CATEGORY_PANEL_ID = 6010

# Divertissement state view (B17, Plex's "server unreachable" pattern):
# centered icon + title + message + one contextual action button over the
# content area, declared in Aura.xml and driven through
# Window.Property(DivertState)/_set_divert_state(). Transport-level
# failures (dead host or offline-breaker fast fail) get the dedicated
# "offline" copy; other load errors get the generic "error" one.
DIVERT_STATE_TITLE_ID = 6301
DIVERT_STATE_MESSAGE_ID = 6302
DIVERT_STATE_BUTTON_ID = 6303
OFFLINE_ERROR_TYPES = (plex_client.PlexOfflineError,
                       connector_client.ConnectorOfflineError)

# Bibliotheque toolbar (plan f41ce1ad phase A).
DIVERT_TYPE_LABEL_ID = 3210
DIVERT_FILTER_BUTTON_ID = 3211
DIVERT_SORT_BUTTON_ID = 3212
DIVERT_GENRE_BUTTON_ID = 3213  # retired: genre lives in the "..." overflow
DIVERT_PLAY_BUTTON_ID = 3215
DIVERT_SHUFFLE_BUTTON_ID = 3216
DIVERT_RESET_BUTTON_ID = 3218
DIVERT_CLEAR_BUTTON_ID = 3219
DIVERT_AZ_RAIL_ID = 3250

# Surfaces whose Back press re-roots focus on the sidebar instead of
# closing the window (Plex two-level Back convention).
_CONTENT_BACK_IDS = frozenset(
    list(RECO_ALL_LIST_IDS)
    + [DIVERT_PANEL_ID, CATEGORY_PANEL_ID, DIVERT_AZ_RAIL_ID])
DIVERT_TOOLBAR_BUTTON_IDS = (
    DIVERT_FILTER_BUTTON_ID, DIVERT_SORT_BUTTON_ID,
    DIVERT_PLAY_BUTTON_ID, DIVERT_SHUFFLE_BUTTON_ID,
    DIVERT_RESET_BUTTON_ID,
)

# Mirrors aura_library.py's SORT_OPTIONS so both list the exact same choices
# (full labels used in the selection dialog); DIVERT_SORT_SHORT_LABELS are
# the abbreviated captions shown directly on the toolbar button, which has
# much less room than a full-screen dialog.
# Plex's Browse grid defaults to Title sort (official 15-lib-browse shows
# the A-Z rail active on 'A'); keep it first so DIVERT_SORT_OPTIONS[0] is
# both the default and the first row of the sort picker.
DIVERT_SORT_OPTIONS = [
    ('titleSort', i18n.tr(33057)),
    ('addedAt:desc', i18n.tr(33056)),
    ('originallyAvailableAt:desc', i18n.tr(33058)),
    ('rating:desc', i18n.tr(33059)),
]
DIVERT_SORT_SHORT_LABELS = {
    'addedAt:desc': i18n.tr(33060),
    'titleSort': i18n.tr(33057),
    'originallyAvailableAt:desc': i18n.tr(33160),
    'rating:desc': i18n.tr(33059),
}

# Quick filter: only "Tout"/"Non vus"/"Vus" are wired to a real Plex/connector
# parameter (unwatched). HDR/DOVI/Sans correspondance/Doublons from the
# original cahier des charges are not exposed by either source today -- see
# docs/aura/decisions.md.
DIVERT_FILTER_OPTIONS = [
    (None, i18n.tr(33052)),
    (True, i18n.tr(33054)),
    (False, i18n.tr(33055)),
]

GAME_BUTTON_IDS = (2010, 2011, 2012)
APP_TILE_IDS = (2030, 2031, 2032, 2033)

DIVERT_SUBTAB_IDS = (3050, 3100, 3075, 3060)
DIVERT_SUBTAB_RECOMMANDE = 0
DIVERT_SUBTAB_BIBLIOTHEQUES = 1
DIVERT_SUBTAB_COLLECTIONS = 2
DIVERT_SUBTAB_CATEGORIES = 3

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

# Only the *global* bar counts as "bar focused": the contextual sub-tab
# strips (Divertissement/Jeux/App/Home) live in the content area, so
# focusing them keeps the top bar recessed and lets the strip float up
# into the freed space -- Plex TV's exact behaviour.
BAR_CONTROL_IDS = {MODULE_SEARCH_ID, GEAR_BUTTON_ID, TAB_LIST_ID}


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
        self._divert_playlists = []
        # On Plex cloud entries (Live TV / Discover): rail index of the
        # segment divider and the lazily fetched channel list.
        self._sidebar_onplex_index = None
        self._live_channels = None
        self._divert_active_section = 0
        self._divert_items = []
        # What _divert_items/_divert_paged currently hold: 'browse' is the
        # section's own grid; the other loaders (collections, collection
        # children, playlists, music nodes) clobber the same slots, so
        # re-entering Bibliotheque must reload when the cache no longer
        # holds browse items.
        self._divert_items_source = 'browse'
        self._divert_paged = None
        # Letters actually present in the active section (Plex shows only
        # those on the A-Z rail, not the full alphabet); None keeps the
        # static <content> fallback and the '#'..'Z' position map.
        self._divert_az_letters = None
        self._divert_az_section = None
        # Skeleton loaders (plan a3f9c2e1 phase 5): how many trailing
        # placeholder ListItems are currently in each list/panel, so the
        # next render can remove exactly that many before appending fresh
        # real items -- see _sync_placeholders().
        self._divert_placeholder_count = 0
        self._reco_placeholder_counts = {}
        # Pages fetched by PagedList.prefetch_async workers wait here
        # (control_id -> [items]) until the next input event renders them
        # -- worker threads must never touch Kodi controls directly.
        self._pending_appends = {}
        self._pending_appends_lock = threading.Lock()
        # Plex-style hub rows (see RECO_SLOT_IDS): every row slot binds to a
        # hub descriptor {'title', 'paged'}; _hub_offset is the hub shown in
        # the top slot. Both the Plex /hubs source and the legacy 3-row
        # fallback produce the same shape.
        self._hub_rows = []
        # Async view loads (tab/section clicks no longer fetch on the
        # input path): every loader bumps this and the worker checks it
        # before rendering, so a superseded load never paints over the
        # view the user already moved on to. Both the bump and the check
        # run under _ui_lock so they cannot interleave with a render.
        self._view_load_gen = 0
        # Serializes every multi-step control mutation (worker renders,
        # skeleton fills, sidebar rebuilds) against gui_guard selection
        # reads on the input path -- see _ui_locked and gui_guard.
        self._ui_lock = threading.RLock()
        # Set on close(): worker render tails check it inside the lock so
        # no control is touched while the window is being torn down
        # (the stale native-pointer half of the crash class).
        self._closing = False
        # View-load jobs share a bounded pool: two WAN fetches in flight
        # at most, so a burst of tab clicks cannot stack unbounded
        # threads on the shared Plex/Unraid path. Each job re-checks the
        # view generation when it is finally dequeued.
        self._view_pool = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix='aura-views')
        self._warm_probe_timer = None
        self._az_jump_active = False
        self._hub_offset = 0
        # Plex home tab strip ("For You" / "Trending" / "Activity").
        # 0 = Pour vous (local /hubs/promoted), 1 = Tendances (Discover
        # provider hubs), 2 = Activité (social feed -- not supported, see
        # the empty-state note in Aura.xml).
        self._home_tab = 0
        # Bibliotheque toolbar state (plan f41ce1ad phase A): reset whenever
        # the sidebar selection changes to a different library, same
        # pattern as aura_library.py's onInit -- otherwise a search/filter
        # left active would silently stick to the next library visited.
        self._divert_sort = DIVERT_SORT_OPTIONS[0][0]
        self._divert_filter_genre = None
        self._divert_filter_unwatched = None  # None=Tout, True=Non vus, False=Vus
        self._divert_filters = {}  # B4 dynamic server filters {key: (value, title)}
        # Per-section 'has collections' probe: Plex only shows the
        # Collections tab on libraries that actually have some.
        self._divert_collections_probe = {}
        self._collection_probe_inflight = set()
        self._divert_search_query = ''
        # Recommande/Categories, rendered inline like Bibliotheque -- see
        # docs/aura/decisions.md ("recommandations et categories inlinees").
        self._reco_rows = {}  # {list_id: (label_id, title, suffix, PagedList)}
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
        # Divertissement state overlay (B17): active kind
        # ('offline'|'error'|'empty'|'config'|None) plus the thunk bound to
        # its single action button (retry of the failed load, or a
        # navigation like "Effacer les filtres").
        self._divert_state = None
        self._divert_state_action = None
        self._focus_generation = 0
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
        # Set when a detail page started playback: default.py then waits
        # for the video to end and re-opens Aura (modal dialogs suppress
        # the fullscreen video window, so Aura must leave the screen).
        self.playback_started = False
        # Home press received while the window was closed for fullscreen
        # playback: applied by onInit() once Aura re-opens.
        self._pending_home_action = None
        # Last settings-panel open, for the gear-wheel debounce in
        # _open_settings_panel() (spurious remote events burst).
        self._settings_last_open = 0.0
        # Hero backdrop debounce (see _schedule_hero_fanart): the pending
        # timer and the URL actually pushed to the skin property.
        self._hero_fanart_timer = None
        self._hero_fanart_lock = threading.Lock()
        self._hero_fanart_current = None
        # Detail prefetch debounce (see _prefetch_detail): without it a
        # fast scroll bursts one thread bundle per crossed card.
        self._prefetch_timer = None
        self._prefetch_lock = threading.Lock()

    def onInit(self):
        # Window reuse (re-open after playback/settings): the previous
        # close() armed _closing -- clear it before any loader can spawn.
        with self._ui_lock:
            self._closing = False
        # Lift the Home boot veil (skin-patches/patch_home_boot_veil.py):
        # Aura now owns the screen so the loading screen can fade out.
        try:
            xbmcgui.Window(10000).setProperty(HOME_READY_PROPERTY, '1')
        except RuntimeError:
            pass
        try:
            self._populate_tab_list()
            self._show_tab(self.active_tab)
            self._load_divertissement()
            self._divert_load_attempted = True
            self._restore_divert_view(focus=False)
            # interactive=False: missing Steam/Sunshine credentials must
            # never pop a Keyboard dialog during unattended startup (same
            # rule as the connector token -- docs/aura/decisions.md).
            self._select_jeux_subtab(JEUX_SUBTAB_STEAMLINK, interactive=False)
            self._load_pinned_apps()
            self._load_avatar()
            self._focus_tab(self.active_tab)
            self._sync_navigation()
            self._update_bar_focused()
            # Re-opened after a playback session: return to the item's
            # detail page like Plex does when a video stops.
            pending_home = getattr(self, '_pending_home_action', None)
            self._pending_home_action = None
            playback_item = getattr(self, '_playback_item', None)
            self._playback_item = None
            if playback_item and pending_home is None:
                self._open_detail(playback_item, return_from_playback=True)
            if pending_home:
                self._on_home_press_action(pending_home)
            # A double press completed across a (re)launch can evade both
            # paths: default.py only sees the first half, and the monitor
            # was not listening for the second notification. The press
            # file history is the ground truth.
            if (getattr(self, 'open_settings_on_init', False) or
                    settings_press_handler.double_press_just_happened()):
                self.open_settings_on_init = False
                self._open_settings_panel()
            elif (not playback_item and
                    self.addon.getSetting('plex.auto_sign_in') == 'false'):
                # Plex's 'Automatically Sign In' toggle off -> the app
                # opens on the 'Who's watching?' picker rather than the
                # last profile's home (not on post-playback re-opens).
                self._open_profile_picker()
            # Startup loads that failed surfaced the state view: its action
            # button takes over focus once the initial focus pass is done.
            if self._divert_state and self._divert_state_action:
                try:
                    self.setFocusId(DIVERT_STATE_BUTTON_ID)
                except RuntimeError:
                    pass
        except Exception as e:
            xbmc.log('Akasha Aura: init error: {}'.format(e), xbmc.LOGERROR)

    def close(self):
        # Arm _closing BEFORE the native teardown: worker render tails
        # check it under _ui_lock and bail rather than mutating controls
        # that are being freed (stale-pointer half of the crash class).
        with self._ui_lock:
            self._closing = True
        try:
            super().close()
        except AttributeError:  # test stubs / unusual bases
            pass

    def _load_avatar(self):
        """Fetch the plex.tv account avatar in the background.

        Plex TV renders the user's real picture (orange disc in the
        reference captures) instead of a generic placeholder. One shot
        per window open; a blank result keeps the bundled avatar-plex.png
        via the String.IsEmpty fallback in the XML."""
        def worker():
            try:
                client = self._plex_client
                if client is None:
                    server_url = self.addon.getSetting('plex.server_url')
                    token = self.addon.getSetting('plex.token')
                    if not config.is_plex_configured(server_url, token):
                        return
                    client = plex_client.PlexClient(server_url, token, timeout=12)
                thumb = client.user_thumb()
                if thumb:
                    circled = _circle_avatar(thumb)
                    self.setProperty('AuraAvatarRound', '1' if circled else '')
                    self.setProperty('AuraAvatar', circled or thumb)
                    # The search dialog's collapsed rail reads the avatar
                    # off the global home window (same pattern as the
                    # Up Next queue), not this window's own properties.
                    xbmcgui.Window(10000).setProperty('AuraAvatar', circled or thumb)
                name = client.user_name()
                if name:
                    self.setProperty('AuraUserName', name)
            except Exception as e:
                xbmc.log('Akasha Aura: avatar fetch failed: {}'.format(e),
                         xbmc.LOGWARNING)
        threading.Thread(target=worker, daemon=True).start()

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

        client = connector_client.ConnectorClient(server_url, timeout=12)
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
        # Plex draws the active-section outline on the Home row too --
        # the sidebar ring matches ListItem.Label to this property.
        self.setProperty('DivertActiveLibrary', i18n.tr(33005))
        self.setProperty('DivertHomeTab', str(self._home_tab))
        self.addon.setSetting('divert.last_view', 'home')
        self._set_sidebar_selection(DIVERT_SIDEBAR_HOME_INDEX)
        self._load_recommendations(None)
        self._sync_navigation()

    def _activate_library(self, section_index, tab=None, focus=True):
        """Select a library in the sidebar: shows its header + contextual tabs."""
        if not (0 <= section_index < len(self._divert_sections)):
            return
        self._divert_view = 'library'
        self.setProperty('DivertView', 'library')
        self.setProperty('DivertActiveLibrary', self._divert_sections[section_index]['title'])
        self.addon.setSetting('divert.last_view', 'library')
        self._select_divert_section(section_index)
        self._set_sidebar_selection(section_index + DIVERT_SIDEBAR_LIBS_OFFSET)
        self._sync_navigation()
        section = self._divert_sections[section_index]
        try:
            self.getControl(3400).setLabel(section['title'])
        except RuntimeError:
            pass
        self._select_library_tab(
            self._divert_library_tab if tab is None else tab, focus=focus)

    def _defer_focus(self, control_id, delay=0.3):
        """Focus a control a beat later instead of right now.

        A same-tick setFocus() on a control whose <visible> condition was
        toggled by setProperty() in the same handler silently reverts once
        Kodi re-validates visibility (see _select_library_tab's note in
        docs/aura/decisions.md). A delayed focus lands after the
        revalidation, which is what Plex's "selecting a tab moves focus
        into the content" needs. The generation guard makes only the
        latest scheduled focus apply, so rapid tab clicks don't queue
        yanks, and a press that already left the strip wins over a stale
        target.
        """
        self._focus_generation += 1
        generation = self._focus_generation

        def worker():
            time.sleep(delay)
            if generation != self._focus_generation:
                return
            try:
                xbmc.executebuiltin('SetFocus({})'.format(control_id))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _select_library_tab(self, index, focus=True):
        """Switch the contextual tab (Recommande/Bibliotheque/Categories) of the
        currently selected library. No-op if no library is selected."""
        if not self._divert_sections:
            return
        # _divert_active_section can go stale when _divert_sections is
        # repopulated in a different order/shape (pin/unpin, playlists
        # pseudo-entry) -- re-resolve by the library key instead of
        # blindly indexing (observed: IndexError on Recommande click).
        if not (0 <= self._divert_active_section
                < len(self._divert_sections)):
            self._divert_active_section = next(
                (i for i, s in enumerate(self._divert_sections)
                 if s['key'] == self._divert_last_library_key), 0)
        section = self._divert_sections[self._divert_active_section]
        if index == DIVERT_SUBTAB_COLLECTIONS \
                and not self._divert_collections_probe.get(section['key']):
            index = DIVERT_SUBTAB_RECOMMANDE
        self._divert_library_tab = index
        self.setProperty('DivertLibraryTab', str(index))
        self.addon.setSetting('divert.last_subtab', str(index))

        if index == DIVERT_SUBTAB_RECOMMANDE:
            self._load_recommendations(section)
            self._sync_navigation()
            if focus:
                self._defer_focus(self._first_content_id())
            return

        if index == DIVERT_SUBTAB_COLLECTIONS:
            self._load_collections(section)
            self._sync_navigation()
            if focus:
                self._defer_focus(self._first_content_id())
            return

        if index == DIVERT_SUBTAB_CATEGORIES:
            self._load_categories(section)
            self._sync_navigation()
            if focus:
                self._defer_focus(self._first_content_id())
            return

        # Bibliotheque: inline grid, already populated by _select_divert_section
        # -- unless a Collections/Categories/drill-down visit clobbered the
        # shared _divert_items slot since (observed: the Bibliotheque tab
        # kept rendering collection collages after a Collections visit).
        if self._divert_items_source != 'browse':
            self._load_divert_section_items(section)
        else:
            self._apply_browse_restate(section)
        self._sync_navigation()
        if focus:
            self._defer_focus(self._first_content_id())

    def _load_recommendations(self, section):
        """Populate the Recommande rows, scoped to `section` or unscoped
        (Accueil) when None.

        Plex direct mode reads the real `/hubs/promoted` ("For You") or
        `/hubs/sections/{key}` hub list -- the exact same rows, order and
        titles as the official Android TV client (see docs/plex-parity/).
        The connector has no hubs endpoint yet, so connector mode keeps the
        previous hand-built 3-row layout as a fallback; all rows bind
        through the same slot mechanism either way. The hub build runs
        on a worker -- the tab click returns instantly and only paints
        once the fetch lands (generation-guarded against fast re-clicks).
        """
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            if gen != self._view_load_gen:
                return  # superseded while queued on the bounded pool
            rows, fatal = self._reco_hub_rows(section)
            if rows is None:
                if fatal is None or not isinstance(fatal, OFFLINE_ERROR_TYPES):
                    rows = self._reco_legacy_rows(section)
                else:
                    # Offline hub failure: the legacy fallback would hit the
                    # same dead host -- keep a synthetic error row instead so
                    # _apply_reco_state() surfaces the Plex-style offline
                    # state without burning more timeouts.
                    rows = [{'title': '', 'paged': None, 'error': fatal}]
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return
                self._hub_rows = rows
                self._hub_offset = 0
                self._reco_rows = {}
                self._apply_reco_state(section)
                self._rebind_reco_slots()
                self._update_hero(clear_if_empty=True)
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _set_home_tab(self, index):
        """Switch the Accueil tab (Pour vous / Tendances / Activité) and
        rebuild the hub viewport -- mirrors Plex's home tab strip."""
        if index == self._home_tab:
            return
        self._home_tab = index
        self.setProperty('DivertHomeTab', str(index))
        self._load_recommendations(None)
        self._sync_navigation()
        # Same immediate+deferred pattern as _focus_first_subtab: the hub
        # load above is synchronous (Discover placeholders take ~40-60s),
        # so the slots are already bound -- the direct setFocus lands now
        # and the deferred re-apply covers Kodi's post-click restore.
        target = self._first_content_id()
        if target is not None:
            try:
                self.setFocus(self.getControl(target))
            except RuntimeError:
                pass
            self._defer_focus(target)

    def _reco_hub_rows(self, section):
        """Build row descriptors from real Plex hubs.

        Returns (rows, fatal): rows=None means "fall back to the legacy
        rows" (hub source unusable for a non-fatal reason); fatal carries
        the exception when the hub list itself failed, so the caller can
        skip the fallback on transport errors. ([], None) -- empty
        viewport, never the legacy fallback -- is returned for Tendances
        when there is no direct-Plex client."""
        if not self._plex_client:
            if section is None and self._home_tab != HOME_TAB_FOR_YOU:
                return [], None
            return None, None
        try:
            if section and section.get('type') in ('playlist', 'livetv'):
                return [], None  # playlists/live TV have no recommendation hubs
            if section:
                hubs = self._plex_client.section_hubs(section['key'])
            elif self._home_tab == HOME_TAB_TRENDING:
                hubs = self._plex_client.discover_hubs()
            elif self._home_tab == HOME_TAB_ACTIVITY:
                # Plex's Activité tab is a friend feed on a private API;
                # the honest local equivalent is the own watch history
                # (/status/sessions/history/all) rendered as one hub row.
                # History carries one entry per episode watched and no
                # grandparentRatingKey to dedup on -- collapse on the show
                # title so a series renders one card, like Plex's feed.
                history = self._plex_client.watch_history(
                    limit=50, since_days=180)
                deduped, seen_shows = [], set()
                for it in history:
                    k = it.get('show_title') or it.get('title') \
                        or it.get('rating_key')
                    if k in seen_shows:
                        continue
                    seen_shows.add(k)
                    deduped.append(it)
                hubs = [{
                    'title': i18n.tr(33577), 'key': '',
                    'identifier': 'aura.activity', 'context': '',
                    'type': '', 'style': 'shelf', 'more': False,
                    'items': deduped,
                }]
            else:
                hubs = self._plex_client.home_hubs()
        except Exception as e:
            xbmc.log('Akasha Aura: hubs load failed, falling back to legacy rows: {}'
                     .format(e), xbmc.LOGWARNING)
            if section is None and self._home_tab != HOME_TAB_FOR_YOU:
                # Tendances/Activité have no local equivalent: an empty
                # viewport is honest; re-serving the For You rows under
                # another tab is not.
                return [], e
            return None, e
        rows = []
        seen_keys = set()
        candidates = []
        for hub in hubs:
            # Discover emits non-shelf hubs (genre buttons, service pills)
            # that have no poster content to render.
            if hub.get('style') in ('button', 'availabilityPlatforms'):
                continue
            # 'On Deck' is the server's pre-merged continue queue: Plex
            # folds it into 'Continue Watching' and never renders a second
            # same-titled row on home (reference first_load/row2-7).
            if section is None and \
                    (hub.get('identifier') or '').lower() == 'home.ondeck':
                continue
            if not hub['items'] and not hub['key']:
                continue
            # Distinct sections can emit same-titled hubs ("Oh, The Horror!"
            # in Movies and TV): dedup on the hub's continuation key (or its
            # hubIdentifier for inline-only hubs), never on the title -- the
            # Android TV client renders each of them.
            hub_id = hub.get('key') or hub.get('identifier') or ''
            if hub_id and hub_id in seen_keys:
                continue
            if hub_id:
                seen_keys.add(hub_id)
            candidates.append(hub)
        # Placeholder hubs (Discover answers with zero inline items) each
        # need one continuation fetch -- hydrate them in parallel or a
        # 12-hub Tendances switch freezes the click handler for ~60s.
        # Bounded pool: each fetch is one GET with its own timeout and the
        # client's in-flight/cache guards; PagedLists share no state.
        if len(candidates) > 1:
            with ThreadPoolExecutor(max_workers=6) as pool:
                built = list(pool.map(self._reco_init_hub_row, candidates))
        else:
            built = [self._reco_init_hub_row(h) for h in candidates]
        for row in built:
            if not row:
                continue
            # Empty hubs (key present but zero items server-side) render as
            # a bare label -- Plex drops them, so do we.
            if not row['paged'].items and not row.get('error'):
                continue
            rows.append(row)
        if hubs:
            # The server answered with hubs but every one was filtered out
            # as empty -- the honest render is the empty state, not the
            # video-centric legacy rows (observed on a music section:
            # "Continuer a regarder"/"Ajoutes recemment" labels with no
            # cards underneath).
            return rows, None
        if section is None and self._home_tab != HOME_TAB_FOR_YOU:
            # Empty Discover/Activity response: same empty-viewport rule,
            # never the For You rows under a foreign tab.
            return [], None
        return None, None

    def _reco_init_hub_row(self, hub):
        """Wrap one hub in a PagedList: the first page is served from the
        hub's own inline Metadata (already fetched with the hub list, zero
        extra requests); later pages paginate the hub's `key` endpoint."""
        inline = list(hub.get('items') or [])
        key = hub.get('key') or ''
        cloud = bool(hub.get('cloud'))
        # page_size must match the inline page exactly: a shorter first page
        # would mark the PagedList exhausted even though the hub key can
        # still paginate further.
        page_size = len(inline) if inline else 16

        def fetch_page(offset, limit):
            if offset < len(inline):
                page = inline[offset:offset + limit]
                # Inline items exhausted and no continuation endpoint:
                # report the known total so the row is marked complete.
                if offset + limit >= len(inline) and not key:
                    return page, len(inline)
                return page, None
            if not key:
                return [], len(inline)
            try:
                page, total = self._plex_client.hub_items_with_total(
                    key, limit, offset)
                if cloud:
                    for it in page:
                        it['cloud'] = True
                return page, total
            except Exception as e:
                xbmc.log('Akasha Aura: hub page fetch failed for {}: {}'
                         .format(key, e), xbmc.LOGWARNING)
                return [], None

        paged = paged_list.PagedList(
            paged_list.dedup_fetch(fetch_page), page_size=page_size,
            max_items=RECO_MAX_ITEMS_PER_ROW)
        # Plex suffixes section hubs with the server name ('... · Akasha');
        # the friendly name is cached after the first '/' root fetch.
        server = ''
        if self._plex_client:
            try:
                server = self._plex_client.server_friendly_name() or ''
            except Exception:
                pass
        title, title_suffix = _hub_title_fr(hub, server)
        try:
            paged.load_initial()
        except Exception as e:  # defensive: never crash the tab on a row failure
            xbmc.log('Akasha Aura: hub row "{}" failed: {}'.format(hub.get('title'), e),
                     xbmc.LOGWARNING)
            return {'title': title, 'title_suffix': title_suffix,
                    'paged': paged, 'error': e, 'style': 'shelf'}
        return {'title': title, 'title_suffix': title_suffix,
                'paged': paged, 'error': None,
                'style': hub.get('style') or 'shelf'}

    def _reco_legacy_rows(self, section):
        """Connector mode: the connector has no hubs endpoint, so rebuild the
        original 3 hand-picked rows through the same slot mechanism."""
        on_deck_title = i18n.tr(33137)
        recent_title = i18n.tr(33138)
        if section:
            on_deck_title += ' ' + i18n.tr(33141).format(section['title'])
            recent_title += ' ' + i18n.tr(33141).format(section['title'])
        rows = [
            (on_deck_title,
             lambda offset, limit: self._reco_fetch_on_deck_page(section, offset, limit)),
            (recent_title,
             lambda offset, limit: self._reco_fetch_recently_added_page(section, offset, limit)),
        ]
        releases_section = section or self._reco_get_first_video_section()
        releases_title = '{} · {}'.format(
            i18n.tr(33139), releases_section['title']) \
            if releases_section else i18n.tr(33139)
        rows.append((
            releases_title,
            lambda offset, limit: self._reco_fetch_recent_releases_page(
                releases_section, offset, limit)))
        built = []
        for title, fetch_page in rows:
            paged = paged_list.PagedList(
                paged_list.dedup_fetch(fetch_page),
                max_items=RECO_MAX_ITEMS_PER_ROW)
            error = None
            try:
                paged.load_initial()
            except Exception as e:
                error = e
            # Plex drops empty rows -- a bare label with no cards reads as
            # broken (seen on empty libraries via the legacy path).
            if not paged.items and error is None:
                continue
            built.append({'title': title, 'paged': paged, 'error': error})
        return built

    def _reco_slot_index(self, list_control_id):
        """Slot index (0..4) for either variant of a slot's list, else -1."""
        if list_control_id in RECO_LIST_IDS:
            return RECO_LIST_IDS.index(list_control_id)
        if list_control_id in RECO_LANDSCAPE_IDS:
            return RECO_LANDSCAPE_IDS.index(list_control_id)
        return -1

    def _reco_slot_list_id(self, slot_index):
        """The list id actually visible in slot `slot_index`.

        Plex Android TV renders Continue Watching (the only style='hero'
        hub) as a poster shelf like every other row -- the landscape twin
        lists stay bound but permanently hidden (neutralised in
        _rebind_reco_slots), so this always resolves to the poster id."""
        return RECO_LIST_IDS[slot_index]

    @_ui_locked
    def _rebind_reco_slots(self):
        """Bind each visible row slot to `_hub_rows[_hub_offset + i]`.

        Called on (re)load and every time the viewport slides by one hub --
        see RECO_SLOT_IDS. Slots without a hub are emptied rather than
        hidden so their ondown/left navigation stays consistent.
        """
        self._drop_pending_appends(*RECO_ALL_LIST_IDS)
        for i, (label_id, list_id) in enumerate(RECO_SLOT_IDS):
            index = self._hub_offset + i
            row = self._hub_rows[index] if index < len(self._hub_rows) else None
            land_id = RECO_LANDSCAPE_IDS[i]
            try:
                poster_lst = self.getControl(list_id)
                land_lst = self.getControl(land_id)
            except RuntimeError:
                continue
            if row is None:
                poster_lst.reset()
                land_lst.reset()
                self._reco_rows.pop(list_id, None)
                self._reco_rows.pop(land_id, None)
                self.setProperty('AuraRowStyle{}'.format(i), '')
                try:
                    self.getControl(label_id).setLabel('')
                    self.getControl(label_id + 1).setLabel('')
                except RuntimeError:
                    pass
                continue
            style = row.get('style') or 'shelf'
            # Plex TV renders the 'hero' hub (Continue Watching) as a
            # poster shelf with progress bars (reference captures) -- the
            # server style hint does not map to landscape cards here.
            if style == 'hero':
                style = 'shelf'
            self.setProperty('AuraRowStyle{}'.format(i), style)
            effective_id = land_id if style == 'hero' else list_id
            hidden_id, hidden_lst = (list_id, poster_lst) \
                if style == 'hero' else (land_id, land_lst)
            lst = land_lst if style == 'hero' else poster_lst
            hidden_lst.reset()
            self._reco_rows.pop(hidden_id, None)
            self._reco_rows[effective_id] = (
                label_id, row['title'],
                row.get('title_suffix') or '', row['paged'])
            self._render_reco_row_label(effective_id, row.get('error'))
            if row.get('error'):
                lst.reset()
                continue
            try:
                lst.reset()
                for item in row['paged'].items:
                    lst.addItem(_build_divert_list_item(item))
            except Exception as e:
                xbmc.log('Akasha Aura: recommendations row render error for {}: {}'
                         .format(row['title'], e), xbmc.LOGERROR)
            self._reco_placeholder_counts[effective_id] = self._sync_placeholders(
                effective_id, 0, row['paged'])
        self._sync_navigation()

    def _reco_scroll(self, delta):
        """Slide the hub viewport by `delta` (+1 down / -1 up), if possible."""
        max_offset = max(0, len(self._hub_rows) - len(RECO_SLOT_IDS))
        new_offset = min(max(self._hub_offset + delta, 0), max_offset)
        if new_offset == self._hub_offset:
            return False
        self._hub_offset = new_offset
        self._rebind_reco_slots()
        # Rebinding resets the focused slot's list; if Kodi parked focus
        # elsewhere during the empty window (observed: Up at offset>0
        # landed on the sub-tab strip instead of the re-entered row),
        # bring it back to the slot the scroll was anchored on.
        slot = 0 if delta < 0 else len(RECO_SLOT_IDS) - 1
        try:
            if self.getFocusId() != self._reco_slot_list_id(slot):
                self._defer_focus(self._reco_slot_list_id(slot))
        except RuntimeError:
            self._defer_focus(self._reco_slot_list_id(slot))
        return True

    def _reco_slot_has_row(self, slot_index):
        return self._hub_offset + slot_index < len(self._hub_rows)

    def _reco_list_has_items(self, list_id):
        try:
            return self.getControl(list_id).size() > 0
        except RuntimeError:
            return False

    def _sync_navigation(self):
        """Re-wire directional navigation targets to the current state.

        Kodi resolves <ondown>/<onup> natively from whichever control held
        focus when the action started, so a setFocus() inside onAction is
        overridden by the XML-declared target (the earlier "double hop"
        bug). The only reliable way to get Plex-style nav (top bar ->
        contextual tabs -> pinned first row -> viewport scroll) is to keep
        the declared targets themselves in sync with the active view/tab.
        """
        # setNavigation() takes Control objects (not ids) and requires all
        # four positional args; passing the control itself pins a direction.
        def nav(control_id, up=None, down=None, left=None, right=None):
            try:
                ctl = self.getControl(control_id)
                ctl.setNavigation(
                    self.getControl(up) if up is not None else ctl,
                    self.getControl(down) if down is not None else ctl,
                    self.getControl(left) if left is not None else ctl,
                    self.getControl(right) if right is not None else ctl)
            except RuntimeError:
                pass

        # Top bar tab list: Down is intercepted in onAction (routed to the
        # active module's sub-tab strip); Left/Right edge exits are the
        # declared <onleft>/<onright> in Aura.xml. No setNavigation here:
        # nav() defaults unset directions to the control itself, which
        # would swallow the list's internal left/right item movement.

        # Reco slots: Up from the first slot reaches the contextual strip
        # only once the viewport is back at the top; while deeper hubs are
        # reachable it pins itself so _reco_scroll(-1) keeps focus anchored.
        # Up/down chain through slots that actually rendered items -- a hub
        # whose load failed stays bound (label shows the error) but empty,
        # and focusing an empty list is a dead end.
        strip_up = (DIVERT_SUBTAB_IDS[self._divert_library_tab]
                    if self._divert_view == 'library'
                    else HOME_TAB_IDS[self._home_tab])
        effective = [self._reco_slot_list_id(i)
                     for i in range(len(RECO_SLOT_IDS))]
        filled_slots = [lid for lid in effective
                        if self._reco_list_has_items(lid)]
        for i, (_, list_id) in enumerate(RECO_SLOT_IDS):
            eff_id = effective[i]
            before = [l for l in filled_slots
                      if effective.index(l) < i]
            after = [l for l in filled_slots
                     if effective.index(l) > i]
            up = (before[-1] if before
                  else (eff_id if self._hub_offset > 0 else strip_up))
            down = after[0] if after else eff_id
            # Wire both variants of the slot: setNavigation() persists on
            # the hidden twin too, so flipping a hub's style between
            # poster and landscape needs no extra sync.
            for lid in (list_id, RECO_LANDSCAPE_IDS[i]):
                nav(lid, up=up, down=down, left=DIVERT_SIDEBAR_ID)

        # State view's action button (B17): Up reaches whichever contextual
        # strip is active, Left exits to the sidebar like every content
        # edge; Down/Right stay on itself.
        nav(DIVERT_STATE_BUTTON_ID, up=strip_up, down=DIVERT_STATE_BUTTON_ID,
            left=DIVERT_SIDEBAR_ID, right=DIVERT_STATE_BUTTON_ID)

        first_sub = self._first_content_id()

        # Library grid: declared nav only applies at a container edge --
        # interior Up/Down stay inside the panel, which is exactly Plex's
        # "Up leaves the grid only from the top row" rule. On the
        # Bibliotheque tab the row above is the filter chips; on
        # Collections/Categories it is the contextual tab itself. Right
        # edge reaches the A-Z rail only where it is rendered (tab 1).
        grid_up = (DIVERT_FILTER_BUTTON_ID
                   if self._divert_library_tab == DIVERT_SUBTAB_BIBLIOTHEQUES
                   else strip_up)
        grid_right = (DIVERT_AZ_RAIL_ID
                      if self._divert_library_tab == DIVERT_SUBTAB_BIBLIOTHEQUES
                      else DIVERT_PANEL_ID)
        nav(DIVERT_PANEL_ID, up=grid_up, down=DIVERT_PANEL_ID,
            left=DIVERT_SIDEBAR_ID, right=grid_right)

        # Library subtabs: Down lands on the chips when they are rendered
        # (Bibliotheque), straight on the content otherwise -- the XML's
        # static 3211 target is invisible on Collections/Categories and
        # would swallow the press entirely.
        subtab_down = (DIVERT_FILTER_BUTTON_ID
                       if self._divert_library_tab == DIVERT_SUBTAB_BIBLIOTHEQUES
                       else first_sub) \
            if self._divert_view == 'library' else None
        if subtab_down is not None:
            subtab_lr = ((3050, DIVERT_SIDEBAR_ID, 3100),
                         (3100, 3050, 3075),
                         (3075, 3100, 3060),
                         (3060, 3075, 5110))
            for tid, tleft, tright in subtab_lr:
                nav(tid, up=TAB_LIST_ID, down=subtab_down,
                    left=tleft, right=tright)

        # Sidebar rail: Right must land on whatever content the active
        # view actually shows -- the XML's static 5110 target is a dead
        # end in library Browse/Collections/Categories (the reco rows are
        # hidden there), trapping the user inside the rail.
        if (self._divert_view == 'library' and
                self._divert_library_tab in (DIVERT_SUBTAB_BIBLIOTHEQUES,
                                             DIVERT_SUBTAB_COLLECTIONS)):
            sidebar_right = DIVERT_PANEL_ID
        elif (self._divert_view == 'library' and
                self._divert_library_tab == DIVERT_SUBTAB_CATEGORIES):
            sidebar_right = CATEGORY_PANEL_ID
        else:
            sidebar_right = (filled_slots[0] if filled_slots
                             else RECO_ON_DECK_LIST_ID)
        nav(DIVERT_SIDEBAR_ID, right=sidebar_right)

        # Top bar: the gear's declared <ondown>9000</ondown> was a leftover
        # milestone-1 placeholder -- an invisible 1x1 button whose only
        # exit is Up, trapping focus off-screen on every Down press from
        # the gear. Route Down from both top-bar buttons to the content
        # the tab list's own Down reaches (_first_content_id), and keep
        # 9000 itself escapable in every direction in case anything still
        # lands on it before the first sync. nav() pins unset directions
        # to the control itself, so the XML-declared left/right targets
        # must be repeated explicitly here.
        escape = first_sub if first_sub is not None else TAB_LIST_ID
        nav(GEAR_BUTTON_ID, up=GEAR_BUTTON_ID, down=escape,
            left=TAB_LIST_ID, right=MODULE_SEARCH_ID)
        nav(MODULE_SEARCH_ID, up=MODULE_SEARCH_ID, down=escape,
            left=GEAR_BUTTON_ID, right=TAB_LIST_ID)
        nav(9000, up=TAB_LIST_ID, down=escape,
            left=escape, right=escape)

    def _focused_reco_item(self):
        """The item dict currently focused in a Recommande row slot."""
        try:
            focused = self.getFocusId()
        except RuntimeError:
            return None
        if focused not in self._reco_rows:
            return None
        _, _, _, paged = self._reco_rows[focused]
        try:
            li = gui_guard.selitem(self, focused)
            if li is not None and li.getProperty('IsPlaceholder'):
                return None
            pos = gui_guard.selpos(self, focused)
        except RuntimeError:
            return None
        if not (0 <= pos < len(paged.items)):
            return None
        return paged.items[pos]

    def _prefetch_detail(self, item):
        """Debounce the detail prefetch: only fire once focus has dwelled
        ~250ms on a card. Without this, holding Right across a row would
        spawn a thread bundle per crossed card for pages never opened."""
        rk = (item or {}).get('rating_key')
        if not rk or getattr(self, '_prefetched_key', None) == rk:
            return
        with self._prefetch_lock:
            if self._prefetch_timer is not None:
                self._prefetch_timer.cancel()
            self._prefetch_timer = threading.Timer(
                0.25, self._prefetch_detail_now, args=(item,))
            self._prefetch_timer.daemon = True
            self._prefetch_timer.start()

    def _prefetch_detail_now(self, item):
        """Warm the clients' 30s GET cache for the endpoints the detail
        page hits on open (extras, watch history, on-deck, seasons).
        Runs on settled focus -- before the click -- so _render() usually
        finds every payload already cached and the page stops
        materialising its controls one network round-trip at a time.
        Params must match _render()'s own calls exactly: the read cache
        keys on (path, sorted params), so on_deck uses limit=60 like
        _find_next_episode, not the home row's limit=20."""
        rk = (item or {}).get('rating_key')
        if not rk or getattr(self, '_prefetched_key', None) == rk:
            return
        self._prefetched_key = rk
        client = self._connector_client or self._plex_client
        if client is None:
            return
        show_key = rk if item.get('type') == 'show' \
            else item.get('grandparent_rating_key')

        def hit(name, *args, **kw):
            fn = getattr(client, name, None)
            if fn is None:
                return
            try:
                fn(*args, **kw)
            except Exception:
                pass
        # One thread per endpoint: the clients' read cache keys on the
        # path, so parallel GETs warm distinct entries without a serial
        # ~2s chain eating the focus-to-click window.
        calls = [('item_extras', (rk,), {}),
                 ('watch_history', (), {'limit': 50, 'rating_key': rk}),
                 ('on_deck', (), {'limit': 60})]
        if show_key:
            calls.append(('show_seasons', (show_key,), {}))
        for name, args, kw in calls:
            threading.Thread(
                target=hit, args=(name,) + args, kwargs=kw,
                daemon=True).start()

    def _cloud_hydrate(self, item):
        """Merge a Discover/cloud card's full provider record in place
        (summary, genres, cast, ratings) -- the hub payloads carry thin
        cards only. Callers own the `cloud_full` one-shot marker; a
        failed fetch simply keeps the thin fields."""
        rk = item.get('rating_key')
        key = item.get('key') or ''
        if not self._plex_client or not (rk or key):
            return
        # Trailer clips key into '<movie>/extras/<clip>' -- the hero and
        # the detail page show the parent MOVIE's record, not the clip's.
        if '/extras/' in key:
            path = key.split('/extras/')[0]
        elif key.endswith('/children'):
            # A show/season node's own key IS its children endpoint --
            # the record itself sits one level up, otherwise items[0]
            # merges a SEASON's fields into the show card.
            path = key[:-len('/children')]
        elif key:
            path = key
        else:
            path = '/library/metadata/{}'.format(rk)
        try:
            fresh = self._plex_client.provider_metadata(path)
        except Exception:
            fresh = None
        if fresh:
            if '/extras/' in key:
                # Trailer/clip card: the detail page paints the PARENT
                # record -- adopt its type/key wholesale so a show
                # keeps its season strip and mode (the clip's own key
                # only routes into the /extras endpoint).
                item.update(fresh)
            else:
                for key, value in fresh.items():
                    if value and not item.get(key):
                        item[key] = value

    def _hydrate_cloud_item(self, item):
        """Background `_cloud_hydrate` for the hero: repaint once the full
        record is merged so the plot/cast/genres appear without stalling
        the UI thread on a provider round-trip."""
        def worker():
            self._cloud_hydrate(item)
            # Repaints whatever is focused now -- the dwell may have moved
            # on, in which case the new card's hero is the right paint.
            self._update_hero()
        threading.Thread(target=worker, daemon=True).start()

    def _hydrate_server_item(self, item):
        """Background metadata fetch for thin SERVER items -- watch-history
        entries (Activité row) ship duration=None/contentRating=None, so
        the hero's '24m TP' fragment only exists on the full record. Same
        merge-absent + repaint pattern as the cloud hydrate above."""
        def worker():
            rk = item.get('rating_key')
            client = self._plex_client or self._connector_client
            if client and rk and str(rk).isdigit():
                try:
                    fresh = client.metadata_item(rk)
                except Exception:
                    fresh = None
                if fresh:
                    for key, value in fresh.items():
                        if value and not item.get(key):
                            item[key] = value
            self._update_hero()
        threading.Thread(target=worker, daemon=True).start()

    def _defer_hero(self, delay=0.08):
        """Repaint the hero a beat after a programmatic slot hop.

        _update_hero() reads the *current* focus via getFocusId(), but
        Kodi has not applied the just-issued setFocus() yet when the
        Up/Down slot-chain runs inside onAction -- the hero then paints
        the item of the row we are LEAVING (observed: jumping from
        "Continuer" onto Chucky left an ANTIGANG hero). Deferring one
        tick lets the focus land first; the generation counter drops
        stale paints when several hops queue."""
        self._hero_generation = getattr(self, '_hero_generation', 0) + 1
        generation = self._hero_generation

        def worker():
            time.sleep(delay)
            if generation != self._hero_generation:
                return
            try:
                self._update_hero()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _update_hero(self, clear_if_empty=False):
        """Sync the Plex hero (backdrop/logo/meta/plot/cast) with the item
        currently focused in a Recommande row -- Plex repaints the whole
        header every time the focused card changes, including while
        scrolling horizontally inside one row."""
        item = self._focused_reco_item()
        if item is None:
            # Nothing focused yet (fresh load, focus still on the top bar):
            # seed the hero with the first item of the first row, matching
            # Plex's initial auto-highlight.
            for i in range(len(RECO_SLOT_IDS)):
                row = self._reco_rows.get(self._reco_slot_list_id(i))
                if row and row[3].items:
                    item = row[3].items[0]
                    break
        if item is None:
            # A reload that yields zero items must not keep the previous
            # view's hero painted (seen entering a music section: AHS hero
            # text over the album-art backdrop). Focus-time calls keep the
            # last hero so hopping to the tab strip does not blank it.
            if clear_if_empty:
                self._clear_hero()
            return

        # Discover/cloud cards render thin fields first, then the full
        # provider record (plot/cast/genres) fades in like Plex's own
        # progressive hero fill.
        if item.get('cloud') and not item.get('cloud_full'):
            # Mark before spawning so a rapid hero repaint does not queue
            # a second provider fetch for the same card.
            item['cloud_full'] = True
            self._hydrate_cloud_item(item)
        elif not item.get('cloud') and item.get('rating_key') \
                and not item.get('server_full') \
                and (not item.get('duration_ms')
                     or not item.get('content_rating')
                     or not item.get('blur_colors')):
            item['server_full'] = True
            self._hydrate_server_item(item)

        is_episode = item.get('type') == 'episode'
        title = item.get('show_title') if is_episode else item.get('title')
        title = title or item.get('title') or ''
        if is_episode:
            subtitle = item.get('title') or ''
        elif item.get('type') in ('show', 'season'):
            subtitle = ''  # the logo/title already names the show
        else:
            subtitle = ''

        # Plex paints the hero cast line on home/Tendances but not on the
        # library Recommande hero (official 13-library-films: meta, plot,
        # then the first row directly).
        cast = '' if self._divert_view == 'library' else ', '.join(
            c['name'] for c in (item.get('cast') or [])[:4])
        fanart = item.get('fanart_url') or item.get('art_url') or ''
        # Warm the texture cache through a hidden 1px image NOW so the
        # debounced backdrop swap below hits a ready texture instead of
        # stalling the renderer ~200ms mid-settle on decode+upload.
        self.setProperty('AuraHeroFanartPreload', fanart)
        self.setProperty('AuraHeroLogoPreload', item.get('logo_url') or '')
        # Plex washes the whole home field with the item's UltraBlurColors
        # (colored left/bottom veils); applied with the fanart swap so art
        # and tint never disagree.
        blur = item.get('blur_colors') or {}
        tint_left = _tint_hex(blur.get('topLeft'),
                              blur.get('bottomLeft'))
        tint_bottom = _tint_hex(blur.get('bottomLeft'),
                                blur.get('bottomRight'),
                                blur.get('topLeft'))
        self._schedule_hero_fanart(fanart, tint_left, tint_bottom)
        self.setProperty('AuraHeroLogo', item.get('logo_url') or '')
        self.setProperty('AuraHeroTitle', title)
        self.setProperty('AuraHeroSubtitle', subtitle)
        self.setProperty('AuraHeroMeta', _hero_meta_line(
            item, compact=(self._divert_view == 'library')))
        rating = item.get('content_rating') or ''
        self.setProperty('AuraHeroRating', rating)
        # Library heroes paint the solid chip like episodes; only the home
        # movie/show hero keeps the bordered meta-rating-box.
        self.setProperty('AuraHeroChipSolid',
                         '1' if (is_episode or
                                 self._divert_view == 'library') else '')
        # Plex's age chip hugs its text (~40px for "10"): resize the
        # chip group/image/label since Kodi cannot auto-size it.
        chip_w = max(44, 14 * len(rating) + 24)
        # 5005/5006/5007: chip group+image+label in the meta slot below the
        # episode subtitle; 5009/5010/5013/5012: same chip in the no-subtitle
        # (movie/show) meta slot.
        for cid in (5005, 5006, 5007, 5009, 5010, 5013, 5012):
            try:
                self.getControl(cid).setWidth(chip_w)
            except RuntimeError:
                pass
        self.setProperty('AuraHeroPlot', _truncate_plot(item.get('summary') or ''))
        self.setProperty('AuraHeroCast', cast)
        self._prefetch_detail(item)

    def _clear_hero(self):
        """Blank every hero property -- used when a (re)load produces no
        items at all so the previous view's title/plot does not linger
        over the new section's backdrop."""
        with self._hero_fanart_lock:
            if self._hero_fanart_timer is not None:
                self._hero_fanart_timer.cancel()
                self._hero_fanart_timer = None
            self._hero_fanart_current = None
        for prop in ('AuraHeroFanart', 'AuraHeroFanartPreload',
                     'AuraHeroLogo', 'AuraHeroLogoPreload',
                     'AuraHeroTitle', 'AuraHeroSubtitle', 'AuraHeroMeta',
                     'AuraHeroRating', 'AuraHeroChipSolid',
                     'AuraHeroPlot', 'AuraHeroCast'):
            try:
                self.setProperty(prop, '')
            except RuntimeError:
                pass
        for cid in (5020, 5021):  # field tint veils back to neutral
            try:
                self.getControl(cid).setColorDiffuse('00000000')
            except (RuntimeError, AttributeError):
                pass

    def _schedule_hero_fanart(self, url, tint_left='', tint_bottom=''):
        """Debounce the 1080p backdrop swap while the user scrolls.

        Without this every keypress pushes a new fanart URL into the skin
        property, and Kodi decodes a full-res JPEG on the Pi4's modest GPU
        for each one -- the classic hero stutter when holding Right. Text
        props still update immediately; the backdrop only catches up
        ~300ms after scrolling stops, matching Plex's own hero behaviour
        (it never repaints mid-fling either). The UltraBlurColors field
        tint rides along so artwork and color change in the same frame.
        """
        with self._hero_fanart_lock:
            if self._hero_fanart_timer is not None:
                self._hero_fanart_timer.cancel()
                self._hero_fanart_timer = None
            if url == self._hero_fanart_current:
                return
            if url is None:
                self._hero_fanart_current = None
                return
            self._hero_fanart_timer = threading.Timer(
                0.3, self._apply_hero_fanart,
                args=(url, tint_left, tint_bottom))
            self._hero_fanart_timer.daemon = True
            self._hero_fanart_timer.start()

    def _apply_hero_fanart(self, url, tint_left='', tint_bottom=''):
        with self._hero_fanart_lock:
            self._hero_fanart_timer = None
            changed = url != self._hero_fanart_current
            self._hero_fanart_current = url
        # 5020: left veil tinted topLeft; 5021: bottom veil tinted
        # bottomLeft. No palette (cloud items) -> alpha 0, neutral field.
        for cid, col in ((5020, tint_left), (5021, tint_bottom)):
            try:
                self.getControl(cid).setColorDiffuse(
                    ('FF' + col) if col else '00000000')
            except (RuntimeError, AttributeError):
                pass
        if changed:
            try:
                self.setProperty('AuraHeroFanart', url)
            except RuntimeError:
                pass

    def _on_reco_item_selected(self, list_control_id):
        row = self._reco_rows.get(list_control_id)
        if not row:
            return
        try:
            li = gui_guard.selitem(self, list_control_id)
            if li is not None and li.getProperty('IsPlaceholder'):
                return
            pos = gui_guard.selpos(self, list_control_id)
        except RuntimeError:
            return
        _, _, _, paged = row
        if not (0 <= pos < len(paged.items)):
            return
        self._reco_open(paged.items[pos])

    def _reco_open(self, item):
        if item['type'] == 'collection':
            self._open_collection(item)
            return
        if item['type'] == 'playlist':
            self._open_playlist(item)
            return
        if item['type'] in ('artist', 'album'):
            self._open_music_node(item)
            return
        if item['type'] == 'track':
            self._play_track(item)
            return
        # Cloud cards need their full provider record before the detail
        # page opens -- its local-server follow-up calls stay honest
        # no-ops, but the page at least paints Plex's metadata.
        if item.get('cloud') and not item.get('cloud_full'):
            item['cloud_full'] = True
            self._cloud_hydrate(item)
        if item['type'] in ('show', 'season'):
            self._open_show(item)
        elif item['type'] == 'episode' and item.get('grandparent_rating_key'):
            # Episode card -> open its show's page, like Plex does.
            self._open_show({
                'title': item.get('show_title') or item['title'],
                'rating_key': item['grandparent_rating_key'],
            })
        else:
            self._open_detail(item)

    def _on_reco_context_menu(self, list_control_id):
        row = self._reco_rows.get(list_control_id)
        if not row:
            return
        try:
            li = gui_guard.selitem(self, list_control_id)
            if li is not None and li.getProperty('IsPlaceholder'):
                return
            pos = gui_guard.selpos(self, list_control_id)
        except RuntimeError:
            return
        _, _, _, paged = row
        if not (0 <= pos < len(paged.items)):
            return
        item = paged.items[pos]
        self._open_item_context_menu(
            item, lambda: self._reco_open(item), list_control_id)

    def _open_detail(self, item, season_index=None,
                     return_from_playback=False):
        """Open the Plex-style detail page (AuraDetail.xml) for a playable
        item (movie, episode, trailer/clip). `season_index` pre-selects a
        season tab when a season card was the entry point.
        `return_from_playback` lands focus on the 'Show' tab strip like
        Plex does after a video stops (official-live/44)."""
        detail = self._get_sub_window(
            'detail', aura_detail.AuraDetailWindow, 'AuraDetail.xml')
        # Cloud (Discover) records live on the metadata provider: the
        # connector cannot resolve their hex keys, so always talk Plex.
        detail.client = (self._plex_client if item.get('cloud')
                         else self._connector_client or self._plex_client)
        detail.item = item
        detail.land_on_strip = return_from_playback
        # Reset per-open state (the window instance is cached/reused).
        detail.mode = 'show' if item.get('type') == 'show' else 'item'
        detail._show_item = None
        detail._seasons = []
        detail._episodes = []
        detail._next_episode = None
        detail._active_season = 0
        detail._pending_season_index = season_index
        detail.exit_to_sidebar = False
        # The detail instance is cached: reset the flag it raises when a
        # video starts, otherwise every later visit would close the whole
        # window again and re-arm the restore loop.
        detail.playback_started = False
        detail.doModal()
        # Detail-page mutations (watched toggle) live on the shared item
        # dict; push them onto the originating card so the row badge
        # matches on return, like Plex's live refresh.
        self._sync_focused_card(item)
        # Plex behavior: Left on the detail page's left edge pops the
        # sidebar rail open -- mirrored by closing the detail and handing
        # the focus to the sidebar list.
        if getattr(detail, 'exit_to_sidebar', False):
            try:
                self.setFocus(self.getControl(DIVERT_SIDEBAR_ID))
            except RuntimeError:
                pass
        # A modal WindowXMLDialog stays above the fullscreen video and
        # blocks its activation, so playback requested from the detail
        # page also has to close Aura itself. default.py waits for the
        # video to stop and re-opens this same window, like Plex's
        # "return to app" after playback.
        if getattr(detail, 'playback_started', False):
            self.playback_started = True
            # Plex returns to the item's detail page when playback stops;
            # onInit re-opens it via this marker.
            self._playback_item = item
            self.close()

    def _render_reco_row_label(self, list_control_id, error=None):
        label_control_id, title, title_suffix, paged = (
            self._reco_rows[list_control_id])
        try:
            # Plex shows the bare row title ("Continue Watching", "Top Movies
            # in Mystère · Akasha") -- no item counter on home rows.
            shown = '{} — erreur de chargement'.format(title) if error else title
            self.getControl(label_control_id).setLabel(shown)
            # Plex renders the server suffix (~' · Akasha') in a smaller,
            # dimmer face -- a separate label sized at ~60% of the title.
            suffix_control = self.getControl(label_control_id + 1)
            if error or not title_suffix:
                suffix_control.setLabel('')
            else:
                suffix_control.setLabel(title_suffix)
                width = i18n.text_width(shown, 34)
                if width is None:  # PIL unavailable: rough Inter-bold estimate
                    width = len(shown) * 17
                try:
                    _, y = suffix_control.getPosition()
                except RuntimeError:
                    y = 0
                suffix_control.setPosition(127 + width + 15, y)
        except RuntimeError:
            pass

    def _maybe_load_more_reco(self, list_control_id):
        row = self._reco_rows.get(list_control_id)
        if not row:
            return
        label_control_id, title, _suffix, paged = row
        try:
            position = gui_guard.selpos(self, list_control_id)
        except RuntimeError:
            return
        paged.prefetch_async(
            position,
            lambda items: self._queue_pending_append(
                list_control_id, paged, items),
            on_error=lambda e: xbmc.log(
                'Akasha Aura: recommendations pagination failed for {}: {}'
                .format(title, e), xbmc.LOGWARNING))

    def _render_reco_append(self, list_control_id, new_items):
        row = self._reco_rows.get(list_control_id)
        if not row:
            return
        _label, title, _suffix, paged = row
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

    def _drop_pending_appends(self, *control_ids):
        """Discard queued prefetch pages -- a full re-render or a failed
        load makes them redundant (and they would duplicate otherwise)."""
        with self._pending_appends_lock:
            for cid in control_ids:
                self._pending_appends.pop(cid, None)

    def _queue_pending_append(self, control_id, paged, new_items):
        """Stash a prefetched page for rendering by the next input event.

        Called on PagedList worker threads -- GUI mutation is deferred to
        _drain_pending_appends(), which runs on the regular input path.
        `paged` tags the batch with its source so a view switch mid-fetch
        drops the stale page instead of grafting it onto the new view.
        """
        with self._pending_appends_lock:
            self._pending_appends.setdefault(
                control_id, []).append((paged, new_items))

    @_ui_locked
    def _drain_pending_appends(self):
        """Render pages asynchronously fetched since the last keypress."""
        with self._pending_appends_lock:
            pending = self._pending_appends
            self._pending_appends = {}
        for control_id, batches in pending.items():
            for paged, new_items in batches:
                if not new_items:
                    continue
                if control_id == DIVERT_PANEL_ID:
                    if paged is not self._divert_paged:
                        continue
                    self._divert_items = paged.items
                    self._divert_append_new(new_items)
                elif control_id in RECO_ALL_LIST_IDS:
                    row = self._reco_rows.get(control_id)
                    if not row or row[3] is not paged:
                        continue
                    self._render_reco_append(control_id, new_items)

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
                status.setLabel(i18n.tr(33067))
            return
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            if gen != self._view_load_gen:
                return  # superseded while queued on the bounded pool
            error = None
            try:
                if section.get('type') in ('playlist', 'livetv'):
                    genres = []  # no genre directory for playlists/live TV
                elif self._connector_client:
                    genres = divert_source.parse_genres(
                        self._connector_client.section_genres(section['key']))
                else:
                    genres = self._plex_client.section_genres(section['key'])
            except Exception as e:
                xbmc.log('Akasha Aura: categories load failed: {}'.format(e), xbmc.LOGERROR)
                genres = []
                error = e
            # Kept untranslated for _on_category_genre_selected() -- the Plex/
            # connector genre filter API expects the original (English) tag,
            # only the on-screen label is translated (Plex's metadata agents
            # report genre names in the source database's language, English
            # regardless of Akasha's own French interface). Junk tags with no
            # letters/digits (';;' seen on the real server) are dropped --
            # Plex never renders them.
            genres = [g for g in genres if any(ch.isalnum() for ch in g or '')]
            # ListItems are pure data -- build them outside the lock.
            items = []
            for genre in genres:
                li = xbmcgui.ListItem(divert_source.display_genre(genre))
                li.setProperty('TileColor', 'B0' + _genre_tile_color(genre))
                items.append(li)
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return
                self._category_genres = genres
                # Plex's Categories tab is a bare 4-column tile grid -- no
                # "N categories" heading at all.
                if status:
                    status.setLabel('')
                try:
                    panel = self.getControl(CATEGORY_PANEL_ID)
                    panel.reset()
                    panel.addItems(items)
                except RuntimeError:
                    pass
                if error is not None:
                    self._state_for_error(
                        error, lambda: self._load_categories(section))
                elif not genres:
                    self._set_divert_state(
                        'empty', title=i18n.tr(33560), message='',
                        action_label=i18n.tr(33020), action=self._focus_sidebar)
                else:
                    self._set_divert_state(None)
                    self._fetch_category_art(section, genres)
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _fetch_category_art(self, section, genres):
        """Fill each genre tile's backdrop with a sample item's fanart --
        Plex tints a representative artwork with the genre colour. Runs in
        a worker: ~30 per-genre lookups would serialise for seconds on the
        UI thread. Items are re-added once art is known so the panel
        repaints with art + colour scrim."""
        window_id = xbmcgui.getCurrentWindowId()
        self._category_art_generation = \
            getattr(self, '_category_art_generation', 0) + 1
        generation = self._category_art_generation
        section_key = section['key']

        def fetch_one(genre):
            try:
                if self._connector_client:
                    raw = self._connector_client.section_items(
                        section_key, limit=1, offset=0, genre=genre)
                    items = divert_source.parse_metadata_list(
                        raw, self._connector_client.image_url)
                else:
                    items = self._plex_client.by_genre(
                        section_key, genre, limit=1)
                if items:
                    art = items[0].get('art_url') \
                        or items[0].get('fanart_url') \
                        or items[0].get('thumb_url') or ''
                    if art:
                        return genre, art
            except Exception:
                pass
            return genre, None

        def worker():
            # ~30 per-genre lookups serialise for tens of seconds on the
            # Pi -- fan them out to the bounded pool like the Discover
            # hub hydration.
            art_by_genre = {}
            with ThreadPoolExecutor(max_workers=6) as pool:
                for genre, art in pool.map(fetch_one, genres):
                    if art:
                        art_by_genre[genre] = art
            if generation != self._category_art_generation:
                return
            if xbmcgui.getCurrentWindowId() != window_id:
                return
            # Build all ListItems BEFORE taking the lock: pure data, no
            # control touched (network-free) -- the locked mutation below
            # stays short. bulk addItems() shrinks the critical section to
            # a single list mutation.
            items = []
            for genre in genres:
                li = xbmcgui.ListItem(divert_source.display_genre(genre))
                li.setProperty('TileColor', 'B0' + _genre_tile_color(genre))
                if genre in art_by_genre:
                    li.setArt({'fanart': art_by_genre[genre],
                               'thumb': art_by_genre[genre]})
                items.append(li)
            with self._ui_lock:
                if self._closing or generation != self._category_art_generation:
                    return
                try:
                    panel = self.getControl(CATEGORY_PANEL_ID)
                    pos = gui_guard.pos(panel)
                    panel.reset()
                    panel.addItems(items)
                    if pos >= 0:
                        panel.selectItem(pos)
                except RuntimeError:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _collections_paged(self, section):
        """PagedList over the section's Plex collections (Directory items)."""
        def fetch(offset, limit):
            if section.get('type') in ('playlist', 'livetv'):
                return [], 0  # pseudo-sections have no collections
            if self._plex_client:
                return self._plex_client.section_collections_with_total(
                    section['key'], limit=limit, offset=offset)
            # The connector has no collections proxy endpoint -- degrade to
            # an empty tab rather than failing hard.
            return [], 0
        return paged_list.PagedList(fetch, page_size=50, prefetch_margin=50)

    def _set_divert_state(self, kind, title=None, message=None,
                          action_label=None, action=None):
        """Show or hide the centered Divertissement state overlay (B17).

        kind: None clears the overlay; 'offline' (server unreachable),
        'error' (generic load failure), 'empty' (loaded, nothing to show)
        or 'config' (no Plex/connector source configured). `action` is the
        thunk bound to the single state button -- typically a retry of the
        failed load or a navigation ("Effacer les filtres", settings).
        """
        self._divert_state = kind
        self._divert_state_action = action
        if kind is None:
            self.setProperty('DivertState', '')
            self.setProperty('DivertStateAction', '')
            try:
                self.getControl(DIVERT_STATE_TITLE_ID).setLabel('')
                self.getControl(DIVERT_STATE_MESSAGE_ID).setLabel('')
                self.getControl(DIVERT_STATE_BUTTON_ID).setLabel('')
            except RuntimeError:
                pass
            return
        if kind == 'offline':
            title = title or i18n.tr(33550)
            message = message or i18n.tr(33551)
            if action_label is None:
                action_label = i18n.tr(33552)
        elif kind == 'config':
            title = title or i18n.tr(33558)
            message = message or i18n.tr(33559)
            if action_label is None:
                action_label = i18n.tr(33019)
        elif kind == 'empty':
            title = title or i18n.tr(33556)
        else:
            title = title or i18n.tr(33553)
            message = message or i18n.tr(33554)
            if action_label is None:
                action_label = i18n.tr(33552)
        self.setProperty('DivertState', kind)
        self.setProperty('DivertStateAction', action_label or '')
        try:
            self.getControl(DIVERT_STATE_TITLE_ID).setLabel(title)
            self.getControl(DIVERT_STATE_MESSAGE_ID).setLabel(message or '')
            if action_label:
                self.getControl(DIVERT_STATE_BUTTON_ID).setLabel(action_label)
        except RuntimeError:
            pass
        if action_label:
            # Plex puts the default focus on the state's primary action.
            try:
                self.setFocusId(DIVERT_STATE_BUTTON_ID)
            except RuntimeError:
                pass

    def _state_for_error(self, error, retry):
        """Map a load exception to the right state kind."""
        kind = ('offline' if isinstance(error, OFFLINE_ERROR_TYPES)
                else 'error')
        self._set_divert_state(kind, action=retry)

    def _apply_reco_state(self, section):
        """Terminal DivertState decision for the Recommande/Accueil rows.

        Plex drops silently failed hubs; but when *everything* failed (or
        the hub list itself did) it shows the full-panel server state --
        mirrored here. Partial failures keep the per-row
        "erreur de chargement" labels.
        """
        if not self._plex_client and not self._connector_client:
            self._hub_rows = []
            self._set_divert_state('config', action=self._open_settings_menu)
            return
        retry = (self._retry_divertissement if not self._divert_sections
                 else lambda: self._load_recommendations(section))
        rows = self._hub_rows
        # Some rows never touch the network on Accueil (recent releases is
        # a client-side filter returning an empty page with no error):
        # "everything failed" must mean "every row that produced anything
        # failed", so [error, error, empty-no-error] still maps to the
        # full-panel state like Plex's unreachable-server screen.
        filled = [row for row in rows
                  if not row.get('error')
                  and row['paged'] is not None and row['paged'].items]
        failed = [row for row in rows if row.get('error')]
        if failed and not filled:
            offline = any(isinstance(row['error'], OFFLINE_ERROR_TYPES)
                          for row in failed)
            self._hub_rows = []
            self._set_divert_state('offline' if offline else 'error',
                                   action=retry)
            return
        if not rows:
            self._set_divert_state('empty', title=i18n.tr(33560), message='',
                                   action_label=i18n.tr(33552), action=retry)
            return
        self._set_divert_state(None)

    def _divert_has_active_filters(self):
        return bool(self._divert_search_query or self._divert_filter_genre
                    or self._divert_filter_unwatched is not None
                    or self._divert_filters)

    def _apply_grid_empty_state(self, section):
        """Empty-state variants for the Bibliotheque grid: Plex's
        "No Results" + clear-filters action when filters are active,
        "Your library is empty" + Back otherwise."""
        filtered = self._divert_has_active_filters()
        if filtered:
            self._set_divert_state(
                'empty', title=i18n.tr(33556), message='',
                action_label=i18n.tr(33557),
                action=lambda: self._divert_clear_filters_and_reload(section))
        else:
            self._set_divert_state(
                'empty', title=i18n.tr(33555), message='',
                action_label=i18n.tr(33020), action=self._focus_sidebar)

    def _apply_browse_restate(self, section):
        """Re-derive the state for the already-loaded Bibliotheque grid on
        a tab switch that reloads nothing -- otherwise an 'empty'/'error'
        state set by another tab would linger over valid content. An
        error state set by the grid's own failed load is kept as-is."""
        if self._divert_items:
            self._set_divert_state(None)
        elif self._divert_state not in ('offline', 'error'):
            self._apply_grid_empty_state(section)

    def _divert_clear_filters_and_reload(self, section):
        self._divert_sort = DIVERT_SORT_OPTIONS[0][0]
        self._divert_filter_genre = None
        self._divert_filter_unwatched = None
        self._divert_filters = {}
        self._divert_search_query = ''
        self._load_divert_section_items(section)

    def _retry_divertissement(self):
        """State-view "Réessayer" when no library loaded at all: re-run the
        whole source init (sections AND content), not just the failed
        view -- a server that just came back would otherwise stay on the
        error screen because sections were never fetched again."""
        self._load_divertissement()
        self._restore_divert_view(focus=False)

    def _focus_sidebar(self):
        try:
            self.setFocus(self.getControl(DIVERT_SIDEBAR_ID))
        except RuntimeError:
            pass

    def _focus_divert_content(self):
        """Focus hand-back after a state action succeeded: the content
        surface of the current view, or the sidebar as last resort."""
        target = None
        if self._divert_view == 'library' \
                and self._divert_library_tab != DIVERT_SUBTAB_RECOMMANDE:
            target = (CATEGORY_PANEL_ID
                      if self._divert_library_tab == DIVERT_SUBTAB_CATEGORIES
                      else DIVERT_PANEL_ID)
        else:
            target = next((self._reco_slot_list_id(i)
                           for i in range(len(RECO_SLOT_IDS))
                           if self._reco_list_has_items(
                               self._reco_slot_list_id(i))), None)
        if target is None:
            target = DIVERT_SIDEBAR_ID
        try:
            self.setFocus(self.getControl(target))
        except RuntimeError:
            pass

    def _on_state_action(self):
        """Click on the state view's single action button."""
        action = self._divert_state_action
        self._divert_state_action = None
        if action is None:
            return
        action()
        self._sync_navigation()
        # The thunk decided the new state itself: on success the overlay
        # cleared and focus returns to the content; on failure a fresh
        # state is shown and focus stays on its button.
        if self._divert_state is None:
            self._focus_divert_content()

    @_ui_locked
    def _skeleton_divert_panel(self):
        """Seed skeleton cards while the first page is in flight.

        The WAN Plex fetch blocks ~7s on this network; a bare grid reads
        as "empty library" that whole time (observed post-restart), so
        paint the same dimmed silhouettes _sync_placeholders() uses while
        scrolling -- the real render below resets over them.
        """
        try:
            panel = self.getControl(DIVERT_PANEL_ID)
            panel.reset()
            panel.addItems([_build_placeholder_list_item()
                            for _ in range(PLACEHOLDER_ITEM_CAP)])
        except Exception:
            pass

    @_ui_locked
    def _fill_divert_panel(self):
        # A full rebuild supersedes every queued prefetch append: the
        # panel is repainted from paged.items wholesale, so a drained
        # batch afterwards would render the same items twice.
        self._drop_pending_appends(DIVERT_PANEL_ID)
        try:
            panel = self.getControl(DIVERT_PANEL_ID)
            panel.reset()
            panel.addItems([_build_divert_list_item(item)
                            for item in self._divert_items])
            # Kodi keeps a stale "selected" marker across reset() (observed
            # on-device: getSelectedPosition() returned a deep index like 96
            # while the visible cursor sat on the first poster, until the
            # first real move resynced it). Anchor the marker at the top so
            # the very first Up can exit to the filter chips.
            if self._divert_items:
                panel.selectItem(0)
        except Exception as e:
            xbmc.log('Akasha Aura: panel render error: {}'.format(e), xbmc.LOGERROR)
        self._divert_placeholder_count = self._sync_placeholders(
            DIVERT_PANEL_ID, 0, self._divert_paged)

    def _load_collections(self, section):
        """Plex's Collections library tab: the same poster grid as Browse,
        one card per collection."""
        self._divert_collection_key = None
        self._divert_items_source = 'collections'
        paged = self._collections_paged(section)
        self._divert_paged = paged
        self._skeleton_divert_panel()
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            if gen != self._view_load_gen:
                return  # superseded while queued on the bounded pool
            error = None
            try:
                paged.load_initial()
            except Exception as e:
                xbmc.log('Akasha Aura: collections load failed: {}'.format(e), xbmc.LOGERROR)
                error = e
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return
                if error is not None:
                    self._drop_pending_appends(DIVERT_PANEL_ID)
                self._divert_items = paged.items
                self._render_divert_status(section, error)
                self._fill_divert_panel()
                if error is not None:
                    self._state_for_error(
                        error, lambda: self._load_collections(section))
                elif not self._divert_items:
                    self._set_divert_state(
                        'empty', title=i18n.tr(33560), message='',
                        action_label=i18n.tr(33020), action=self._focus_sidebar)
                else:
                    self._set_divert_state(None)
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _open_collection(self, item):
        """Drill into a Plex collection: the grid shows its children until
        the tab is re-entered."""
        if not self._plex_client or not item.get('rating_key'):
            return

        def fetch(offset, limit):
            return self._plex_client.collection_items_with_total(
                item['rating_key'], limit=limit, offset=offset)
        self._divert_items_source = 'collection'
        paged = paged_list.PagedList(fetch, page_size=50, prefetch_margin=50)
        self._divert_paged = paged
        self._skeleton_divert_panel()
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            if gen != self._view_load_gen:
                return  # superseded while queued on the bounded pool
            try:
                paged.load_initial()
            except Exception as e:
                xbmc.log('Akasha Aura: collection children load failed: {}'.format(e), xbmc.LOGERROR)
                with self._ui_lock:
                    if not self._closing and gen == self._view_load_gen:
                        self._drop_pending_appends(DIVERT_PANEL_ID)
                        self._state_for_error(
                            e, lambda: self._open_collection(item))
                return
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return
                self._divert_items = paged.items
                self._divert_collection_key = item['rating_key']
                self._fill_divert_panel()
                self._set_divert_state(None)
                try:
                    self.getControl(DIVERT_STATUS_ID).setLabel(
                        '{} — {}'.format(item['title'],
                                    i18n.tr_count(len(self._divert_items), 33069)))
                    self.getControl(DIVERT_PANEL_ID).selectItem(0)
                except RuntimeError:
                    pass
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _open_playlist(self, item):
        """Drill into a server playlist (B10): the grid shows its items
        until the tab is re-entered -- same pattern as collections."""
        if not self._plex_client or not item.get('rating_key'):
            return

        def fetch(offset, limit):
            return self._plex_client.playlist_items_with_total(
                item['rating_key'], limit=limit, offset=offset)
        self._divert_items_source = 'playlist'
        paged = paged_list.PagedList(
            fetch, page_size=50, prefetch_margin=50)
        self._divert_paged = paged
        self._skeleton_divert_panel()
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            if gen != self._view_load_gen:
                return  # superseded while queued on the bounded pool
            try:
                paged.load_initial()
            except Exception as e:
                xbmc.log('Akasha Aura: playlist items load failed: {}'.format(e),
                         xbmc.LOGERROR)
                with self._ui_lock:
                    if not self._closing and gen == self._view_load_gen:
                        self._drop_pending_appends(DIVERT_PANEL_ID)
                        self._state_for_error(
                            e, lambda: self._open_playlist(item))
                return
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return
                self._divert_items = paged.items
                self._divert_collection_key = item['rating_key']
                self._fill_divert_panel()
                self._set_divert_state(None)
                try:
                    self.getControl(DIVERT_STATUS_ID).setLabel(
                        '{} — {}'.format(item['title'],
                                    i18n.tr_count(len(self._divert_items), 33069)))
                    self.getControl(DIVERT_PANEL_ID).selectItem(0)
                except RuntimeError:
                    pass
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _open_music_node(self, item):
        """Drill into an artist/album (B16): the grid shows its children
        (albums / tracks) until the tab is re-entered -- same pattern as
        collections and playlists. Plex exposes them through the generic
        /metadata/{key}/children endpoint."""
        client = self._plex_client or self._connector_client
        if not client or not item.get('rating_key') \
                or not hasattr(client, 'metadata_children'):
            return
        self._skeleton_divert_panel()
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            if gen != self._view_load_gen:
                return  # superseded while queued on the bounded pool
            try:
                children = client.metadata_children(item['rating_key'])
            except Exception as e:
                xbmc.log('Akasha Aura: music children load failed: {}'.format(e),
                         xbmc.LOGERROR)
                with self._ui_lock:
                    if not self._closing and gen == self._view_load_gen:
                        self._drop_pending_appends(DIVERT_PANEL_ID)
                        self._state_for_error(
                            e, lambda: self._open_music_node(item))
                return
            children = children or []
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return

                def fetch(offset, limit):
                    return children[offset:offset + limit], len(children)
                self._divert_items_source = 'music'
                paged = paged_list.PagedList(
                    fetch, page_size=50, prefetch_margin=50)
                self._divert_paged = paged
                paged.load_initial()
                self._divert_items = paged.items
                self._divert_collection_key = item['rating_key']
                self._fill_divert_panel()
                self._set_divert_state(None)
                try:
                    self.getControl(DIVERT_STATUS_ID).setLabel(
                        '{} — {}'.format(item['title'],
                                    i18n.tr_count(len(self._divert_items), 33069)))
                    self.getControl(DIVERT_PANEL_ID).selectItem(0)
                except RuntimeError:
                    pass
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _play_track(self, item):
        """Audio track from a music library (B16): Kodi plays it in the
        background -- no modal teardown needed unlike video playback."""
        client = self._plex_client or self._connector_client
        item = context_sheet.hydrate_item(client, item)
        base = getattr(client, 'server_url', None) if client else None
        token = getattr(client, 'token', None) if client else None
        url = ('{}{}?X-Plex-Token={}'.format(base, item['part_key'], token)
               if base and token and item.get('part_key') else None)
        if not url:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33075),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        li = xbmcgui.ListItem(item.get('title') or '')
        li.setMimeType('audio/mpeg')
        xbmc.Player().play(url, li)

    def _on_category_genre_selected(self):
        """A genre tile was picked: jump straight to Bibliotheque, pre-filtered
        to that genre, instead of the former separate AuraLibraryWindow --
        same in-place-navigation rationale as the rest of this change."""
        try:
            pos = gui_guard.selpos(self, CATEGORY_PANEL_ID)
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
        self._select_library_tab(DIVERT_SUBTAB_BIBLIOTHEQUES, focus=False)
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
                self._divert_sections = divert_source.parse_sections(connector.sections(), section_types=('movie', 'show', 'artist'))
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
                # Keep the fixed sidebar entries usable and surface the
                # config state instead of the old bare status label.
                self._populate_sidebar()
                self._set_divert_state('config',
                                       action=self._open_settings_menu)
                return
            try:
                self._plex_client = plex_client.PlexClient(server_url, token, timeout=12)
                self._divert_sections = self._plex_client.library_sections()
            except Exception as e:
                xbmc.log('Akasha Aura: Plex sections load failed: {}'.format(e), xbmc.LOGERROR)
                self._divert_sections = []

        # Server-local playlists (B10): Plex always surfaces a "Playlists"
        # sidebar entry (the rail shows it even when the list is empty --
        # the page then renders its empty state). Direct Plex only -- the
        # connector exposes no /playlists proxy. The pseudo-section joins
        # the ordered pool before pinning so its rail position follows
        # divert.library_order like a real section instead of being
        # forced last.
        self._divert_playlists = []
        if self._plex_client:
            try:
                self._divert_playlists = self._plex_client.playlists()
            except Exception as e:
                xbmc.log('Akasha Aura: playlists fetch failed: {}'.format(e),
                         xbmc.LOGWARNING)
            self._divert_sections.append({
                'key': 'playlists', 'type': 'playlist',
                'title': i18n.tr(33582)})

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

        # Warm the per-section collections probe off the input path:
        # _apply_collections_tab reads _divert_collections_probe when a
        # library tab is clicked, and a cold probe costs a WAN round-trip
        # (~7s) right in the click handler. Deferred until after the
        # first screen can render, de-duplicated across repeated calls,
        # and run on the bounded view pool rather than a bare thread.
        client = self._plex_client
        if client and hasattr(client, 'section_collections_with_total'):
            sections = list(self._divert_sections)

            def warm_probes():
                for s in sections:
                    if self._closing:
                        return
                    if s.get('type') not in ('movie', 'show'):
                        continue
                    key = s.get('key') or ''
                    if key in self._divert_collections_probe:
                        continue
                    try:
                        _items, total = \
                            client.section_collections_with_total(
                                key, limit=1)
                        self._divert_collections_probe[key] = bool(total)
                    except Exception:
                        pass

            if self._warm_probe_timer is not None:
                self._warm_probe_timer.cancel()

            def arm_probes():
                self._warm_probe_timer = None
                if not self._closing:
                    self._view_pool.submit(warm_probes)

            self._warm_probe_timer = threading.Timer(3.0, arm_probes)
            self._warm_probe_timer.daemon = True
            self._warm_probe_timer.start()

        # Which library (if any) becomes active is decided by the caller
        # (onInit restores the persisted Accueil/library state, _show_tab's
        # empty-sections retry re-activates Accueil) -- this only loads and
        # orders the sidebar's data, it never picks a view on its own.

    @_ui_locked
    def _populate_sidebar(self):
        try:
            sidebar = self.getControl(DIVERT_SIDEBAR_ID)
        except RuntimeError:
            return
        sidebar.reset()

        # Plex's first row is the profile switcher: round avatar +
        # account name + '>' affordance (is_profile restyles the row in
        # the itemlayout; the picture/name resolve live from the window
        # properties _load_avatar fills asynchronously).
        profile_item = xbmcgui.ListItem('')
        profile_item.setProperty('is_profile', '1')
        sidebar.addItem(profile_item)

        # Plex's second row is "My Lists" (bookmark icon): opens the
        # server-side lists view -- locally the playlists pseudo-section
        # is the closest equivalent (Plex's cloud watchlist has no
        # server-local API).
        lists_item = xbmcgui.ListItem(i18n.tr(33590))
        lists_item.setArt({'icon': 'icon-mylist.png'})
        sidebar.addItem(lists_item)

        search_item = xbmcgui.ListItem(i18n.tr(33001))
        search_item.setArt({'icon': 'icon-search.png'})
        sidebar.addItem(search_item)

        home_item = xbmcgui.ListItem(i18n.tr(33005))
        home_item.setArt({'icon': 'icon-home.png'})
        sidebar.addItem(home_item)

        # Plex's 'Libraries' divider label (is_header restyles it in the
        # itemlayout and keeps the white focus pill off it).
        header_item = xbmcgui.ListItem(i18n.tr(33006))
        header_item.setProperty('is_header', '1')
        sidebar.addItem(header_item)

        for section in self._divert_sections:
            # The live-TV pseudo-section lives under the 'On Plex'
            # divider (added lazily by _open_live_tv), never among the
            # library rows. It stays tail-appended in _divert_sections
            # so pos->index mapping still resolves every visible row.
            if section.get('type') == 'livetv':
                continue
            li = xbmcgui.ListItem(section['title'])
            li.setArt({'icon': self._divert_section_icon(section)})
            # Real sections get the '...' kebab on the focused row --
            # Left opens _sidebar_item_menu (pin/reorder). The playlists
            # pseudo-entry has no pin semantics, so no affordance.
            if section.get('type') not in ('playlist', 'livetv'):
                li.setProperty('is_library', '1')
            sidebar.addItem(li)

        more_item = xbmcgui.ListItem(i18n.tr(33007))
        more_item.setArt({'icon': 'icon-more.png'})
        sidebar.addItem(more_item)

        # Plex's "On Plex" segment below the libraries: a second divider
        # then the cloud Live TV + Discover entries (reference/sidebar/
        # scroll_down_*). Direct Plex only -- the connector has no cloud
        # endpoints.
        self._sidebar_onplex_index = None
        if self._plex_client:
            self._sidebar_onplex_index = sidebar.size()
            onplex_header = xbmcgui.ListItem(i18n.tr(33623))
            onplex_header.setProperty('is_header', '1')
            sidebar.addItem(onplex_header)
            livetv_item = xbmcgui.ListItem(i18n.tr(33624))
            livetv_item.setArt({'icon': 'icon-livetv.png'})
            sidebar.addItem(livetv_item)
            discover_item = xbmcgui.ListItem(i18n.tr(33625))
            discover_item.setArt({'icon': 'icon-discover.png'})
            sidebar.addItem(discover_item)

    def _divert_section_icon(self, section):
        """Return a distinct icon name for a library section.

        Maps common library titles to dedicated textures; new textures can be
        added without touching this code as long as the file name matches the
        convention `icon-<slug>.png`.
        """
        if section.get('type') == 'playlist':
            return 'icon-playlists.png'
        if section.get('type') == 'livetv':
            return 'icon-livetv.png'
        if section.get('type') == 'artist':
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
        return base + (self._divert_sort, self._divert_filter_unwatched,
                       tuple(sorted(self._divert_filters.items())))

    def _divert_section_page(self, section, offset, limit):
        key = local_cache.page_cache_key(
            'divert', section['key'], self._divert_cache_mode_key(), offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, DIVERT_CACHE_TTL_SECONDS,
            lambda: self._divert_section_page_uncached(section, offset, limit))

    def _divert_section_page_uncached(self, section, offset, limit):
        if section.get('type') in ('playlist', 'livetv'):
            # Both pseudo-sections page over a prefetched list --
            # /playlists and the EPG lineup have no pagination.
            pool = (self._live_channels if section.get('type') == 'livetv'
                    else self._divert_playlists) or []
            return (pool[offset:offset + limit], len(pool))
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
            genre=self._divert_filter_genre, unwatched=unwatched,
            filters=self._divert_filter_params())

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
        self._divert_filters = {}
        self._divert_search_query = ''
        self._apply_collections_tab(section)
        self._load_divert_section_items(section)

    def _apply_collections_tab(self, section):
        """Plex only shows the Collections library tab when the section
        actually has collections (Films has 556 here; Séries/Cartoons
        have none and the official strip collapses to 3 pills). One
        cached limit=1 probe per section; the Catégories pill and its
        overlays reseat onto the freed slot via DivertHasCollections."""
        key = section.get('key') or ''
        has = self._divert_collections_probe.get(key)
        if has is None:
            # Never probe synchronously here (~7s WAN on the click path):
            # default to hidden and re-apply once the background probe
            # lands -- same contract as the warm-up after
            # _load_divertissement.
            has = False
            self._probe_collections_async(section)
        self.setProperty('DivertHasCollections', '1' if has else '')
        if not has and self._divert_library_tab == DIVERT_SUBTAB_COLLECTIONS:
            self._divert_library_tab = DIVERT_SUBTAB_RECOMMANDE
            self.setProperty('DivertLibraryTab',
                             str(DIVERT_SUBTAB_RECOMMANDE))
        cat_x = 669 if has else 504
        try:
            self.getControl(3060).setPosition(cat_x, 128)
            for cid, top in ((3091, 128), (3092, 129), (3093, 129),
                             (3094, 129)):
                self.getControl(cid).setPosition(cat_x, top)
            self.getControl(3095).setWidth(695 if has else 530)
        except RuntimeError:
            pass

    def _probe_collections_async(self, section):
        """Cold collections probe off the click path. One in-flight probe
        per section; on completion the tab strip re-applies itself only
        if this section is still the active one (staleness is decided by
        section identity, not the view generation -- a probe must not
        invalidate an unrelated view load)."""
        key = section.get('key') or ''
        client = self._plex_client
        if not client or section.get('type') not in ('movie', 'show') \
                or not hasattr(client, 'section_collections_with_total'):
            self._divert_collections_probe[key] = False
            return
        if key in self._collection_probe_inflight:
            return
        self._collection_probe_inflight.add(key)

        def probe():
            found = False
            try:
                _items, total = client.section_collections_with_total(
                    key, limit=1)
                found = bool(total)
            except Exception:
                pass
            self._divert_collections_probe[key] = found
            self._collection_probe_inflight.discard(key)
            with self._ui_lock:
                if self._closing:
                    return
                try:
                    active = self._divert_sections[
                        self._divert_active_section]
                except (AttributeError, IndexError, TypeError):
                    active = None
                if active is not None and active.get('key') == key:
                    self._apply_collections_tab(active)

        self._view_pool.submit(probe)

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
        self._divert_items_source = 'browse'
        paged = paged_list.PagedList(
            lambda offset, limit: self._divert_section_page(section, offset, limit),
            page_size=50, prefetch_margin=50)
        self._divert_paged = paged
        self._skeleton_divert_panel()
        with self._ui_lock:
            self._view_load_gen += 1
            gen = self._view_load_gen

        def work():
            # Bail before doing anything if this load was superseded --
            # even the A-Z rail render must not paint another section's
            # letters over the view the user already moved to.
            if gen != self._view_load_gen:
                return
            self._load_az_rail(section)
            error = None
            try:
                paged.load_initial()
            except Exception as e:
                xbmc.log('Akasha Aura: section items load failed: {}'.format(e), xbmc.LOGERROR)
                error = e
            # ListItems are pure data -- build them outside the lock.
            items = [_build_divert_list_item(item) for item in paged.items]
            with self._ui_lock:
                if self._closing or gen != self._view_load_gen:
                    return
                if error is not None:
                    self._drop_pending_appends(DIVERT_PANEL_ID)
                self._divert_items = paged.items

                self._render_divert_toolbar(section)
                self._render_divert_status(section, error)

                try:
                    panel = self.getControl(DIVERT_PANEL_ID)
                    panel.reset()
                    panel.addItems(items)
                    # Same stale-marker resync as _fill_divert_panel.
                    if self._divert_items:
                        panel.selectItem(0)
                except Exception as e:
                    xbmc.log('Akasha Aura: panel render error: {}'.format(e), xbmc.LOGERROR)
                self._divert_placeholder_count = self._sync_placeholders(
                    DIVERT_PANEL_ID, 0, paged)

                if error is not None:
                    self._state_for_error(
                        error, lambda: self._load_divert_section_items(section))
                elif not self._divert_items:
                    self._apply_grid_empty_state(section)
                else:
                    self._set_divert_state(None)
                self._sync_navigation()

        threading.Thread(target=work, daemon=True).start()

    def _render_divert_toolbar(self, section):
        try:
            type_label = (i18n.tr(33050) if section.get('type') == 'show'
                          else i18n.tr(33051))
            self.getControl(DIVERT_TYPE_LABEL_ID).setLabel(type_label)
        except RuntimeError:
            pass
        try:
            # Plex's leading pill shows the ACTIVE filter value ('Action'
            # when genre-filtered, 'All' by default), and a separate
            # 'Clear' pill appears after the counter while filtered --
            # see rail_from_grid_004.png / grid_focus_item2_005.png.
            if self._divert_filter_genre:
                filter_label = self._divert_filter_genre
            else:
                filter_label = next(
                    label for value, label in DIVERT_FILTER_OPTIONS
                    if value == self._divert_filter_unwatched)
            self.getControl(DIVERT_FILTER_BUTTON_ID).setLabel(filter_label)
        except RuntimeError:
            pass
        self.setProperty('DivertFiltered',
                         '1' if self._divert_has_active_filters() else '')
        try:
            sort_label = DIVERT_SORT_SHORT_LABELS.get(self._divert_sort, '-')
            self.getControl(DIVERT_SORT_BUTTON_ID).setLabel(sort_label)
        except RuntimeError:
            pass
        self._layout_divert_toolbar()

    def _layout_divert_toolbar(self):
        """Reflow the library chip row so each pill hugs its label like Plex
        (Kodi has no auto-width controls: measure the text, then reposition
        the whole chain). All positions are in the chip group's coordinate
        space, so the recessed-state slide still applies on top."""
        def label_of(cid):
            try:
                return self.getControl(cid).getLabel()
            except RuntimeError:
                return ''

        def put(cid, x, y, w=None):
            try:
                ctrl = self.getControl(cid)
                ctrl.setPosition(x, y)
                if w is not None:
                    ctrl.setWidth(w)
            except RuntimeError:
                pass

        def pill_w(text, pad=34):
            return max(58, int(round(11 * len(text))) + pad)

        y = 190
        x = 127
        w = pill_w(label_of(DIVERT_FILTER_BUTTON_ID))
        for cid in (DIVERT_FILTER_BUTTON_ID, 3241, 3242):
            put(cid, x, y, w)
        x += w + 16
        w = pill_w(label_of(3210))
        put(3221, x, y, w)
        put(3210, x, y, w)
        x += w + 16
        put(3222, x, y, 36)
        x += 51
        w = pill_w(label_of(DIVERT_SORT_BUTTON_ID), pad=73)
        put(DIVERT_SORT_BUTTON_ID, x, y, w)
        put(3223, x + 17, 204)
        put(3224, x + 17, 204)
        put(3243, x + 56, y, w - 56)
        put(3244, x + 56, y, w - 56)
        x += w + 16
        w = max(44, int(round(9.7 * len(label_of(3220)))) + 16)
        put(3220, x, 198, w)
        x += w + 16
        # 'Clear' pill: present only while a filter is active, between
        # the counter and the '...' overflow like Plex.
        if self._divert_has_active_filters():
            w = pill_w(label_of(DIVERT_CLEAR_BUTTON_ID))
            for cid in (DIVERT_CLEAR_BUTTON_ID, 3247, 3248):
                put(cid, x, y, w)
            x += w + 16
        put(3218, x, y)
        put(3226, x + 12, 202)
        put(3227, x + 12, 202)

    def _render_divert_status(self, section, error=None):
        try:
            status = self.getControl(DIVERT_STATUS_ID)
            if error:
                status.setLabel(i18n.tr(33068).format(section['title']))
            else:
                count = self._divert_paged.total if self._divert_paged.total is not None \
                    else len(self._divert_items)
                label = i18n.tr_count(count, 33069)
                if self._divert_search_query:
                    label += ' ' + i18n.tr(33070).format(self._divert_search_query)
                # The leading filter pill already displays the active
                # genre name (Plex 'Action | Movies | by ... | N Items'),
                # so the counter stays bare for genre filters.
                if self._divert_filters:
                    label += ' ({})'.format(', '.join(
                        title for _v, title in self._divert_filters.values()))
                status.setLabel(label)
        except RuntimeError:
            pass
        self._layout_divert_toolbar()

    def _divert_open_filter_menu(self):
        if not self._divert_sections:
            return
        idx = aura_menu.select(
            self, i18n.tr(33061), [label for _, label in DIVERT_FILTER_OPTIONS])
        if idx < 0:
            return
        self._divert_filter_unwatched = DIVERT_FILTER_OPTIONS[idx][0]
        self._load_divert_section_items(self._divert_sections[self._divert_active_section])

    def _divert_open_sort_menu(self):
        if not self._divert_sections:
            return
        idx = aura_menu.select(
            self, i18n.tr(33062), [label for _, label in DIVERT_SORT_OPTIONS])
        if idx < 0:
            return
        self._divert_sort = DIVERT_SORT_OPTIONS[idx][0]
        self._load_divert_section_items(self._divert_sections[self._divert_active_section])

    def _divert_reset_filters(self):
        if not self._divert_sections:
            return
        self._divert_sort = DIVERT_SORT_OPTIONS[0][0]
        self._divert_filter_genre = None
        self._divert_filter_unwatched = None
        self._divert_filters = {}
        self._divert_search_query = ''
        self._load_divert_section_items(self._divert_sections[self._divert_active_section])

    def _divert_filter_params(self):
        """B4: {filter_key: value} params for the dynamic filters, only
        meaningful on the direct Plex client (the connector proxy does
        not expose /filters)."""
        return {key: value for key, (value, _title)
                in self._divert_filters.items()}

    def _divert_open_advanced_filters(self):
        """B4: generic server-driven filter picker -- Plex's filter
        panel reduced to a two-step select (category, then value)."""
        if not self._divert_sections:
            return
        section = self._divert_sections[self._divert_active_section]
        client = self._plex_client
        if client is None:
            return  # connector path has no /filters endpoint
        try:
            filters = client.section_filters(section['key'])
        except Exception as e:
            xbmc.log('Akasha Aura: section filters load failed: {}'
                     .format(e), xbmc.LOGERROR)
            filters = []
        if not filters:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33572),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        # Active filters are marked with a check so the state is
        # visible while browsing the categories.
        labels = []
        for f in filters:
            label = f['title']
            if f['key'] in self._divert_filters:
                label += ' ✓'
            labels.append(label)
        idx = aura_menu.select(self, i18n.tr(33571), labels)
        if idx < 0:
            return
        picked = filters[idx]
        try:
            values = client.filter_values(section['key'], picked['key'])
        except Exception as e:
            xbmc.log('Akasha Aura: filter values load failed: {}'
                     .format(e), xbmc.LOGERROR)
            values = []
        # Boolean filters carry no value list: they map to a plain
        # yes/no parameter (unmatched, duplicates...).
        if picked['type'] == 'boolean' and not values:
            values = [{'key': '1', 'title': i18n.tr(33054)},
                      {'key': '0', 'title': i18n.tr(33055)}]
        if not values:
            self._divert_filters.pop(picked['key'], None)
            self._load_divert_section_items(section)
            return
        options = [i18n.tr(33052)] + [v['title'] for v in values]
        vidx = aura_menu.select(
            self, i18n.tr(33573).format(picked['title']), options)
        if vidx < 0:
            return
        if vidx == 0:
            self._divert_filters.pop(picked['key'], None)
        else:
            v = values[vidx - 1]
            self._divert_filters[picked['key']] = (v['key'], v['title'])
            # Like the genre pill: an active dynamic filter replaces the
            # search/genre mode rather than silently mixing scopes.
            self._divert_filter_genre = None
            self._divert_search_query = ''
        self._load_divert_section_items(section)

    def _divert_open_more_menu(self):
        """The trailing "..." pill of the Browse toolbar: hosts the quick
        actions Plex keeps in its overflow menu."""
        actions = [
            (i18n.tr(33064), self._divert_play_first),
            (i18n.tr(33065), self._divert_play_random),
            (i18n.tr(33571), self._divert_open_advanced_filters),
            (i18n.tr(33066), self._divert_reset_filters),
        ]
        idx = aura_menu.contextmenu(self, [label for label, _ in actions])
        if idx < 0:
            return
        actions[idx][1]()

    def _load_az_rail(self, section):
        """A-Z rail: Plex shows only the initials actually present in the
        library (/firstCharacter buckets), not the full alphabet. The rail
        has no static <content> (Kodi appends programmatic items after
        static ones instead of replacing them) so the rail is always
        populated here -- full alphabet when the fetch fails or a section
        type has no letters endpoint."""
        key = section.get('key') if section else None
        if key == self._divert_az_section:
            return
        self._divert_az_section = key
        letters = None
        if (self._plex_client and section
                and section.get('type') in ('movie', 'show', 'artist')):
            try:
                letters = self._plex_client.section_letters(key)
            except Exception as e:
                xbmc.log('Akasha Aura: A-Z letters fetch failed: {}'.format(e), xbmc.LOGERROR)
        rail_items = [xbmcgui.ListItem(label=letter)
                      for letter in (letters or '#ABCDEFGHIJKLMNOPQRSTUVWXYZ')]
        with self._ui_lock:
            if self._closing:
                return
            self._divert_az_letters = letters or None
            try:
                rail = self.getControl(DIVERT_AZ_RAIL_ID)
                rail.reset()
                rail.addItems(rail_items)
            except Exception as e:
                xbmc.log('Akasha Aura: A-Z rail render failed: {}'.format(e), xbmc.LOGERROR)
                self._divert_az_letters = None

    def _divert_az_jump(self):
        """A-Z rail: jump the grid to the first loaded item starting with
        the selected letter (Plex only offers the rail on title sort).

        All network work runs on the bounded view pool -- the
        firstCharacter lookup plus up to 40 x 500-item chunk fetches is a
        ~70s worst case that must never sit on the input path. The jump
        aborts as soon as the view generation changes (a tab/section
        click), and an in-flight guard serializes repeated rail presses.
        """
        # The control-level getters misbehave on this rail list
        # (getSelectedPosition -> -1, getSelectedItem may raise),
        # but Kodi's infolabels report the selection correctly.
        try:
            pos = int(xbmc.getInfoLabel('Container({}).Position'.format(
                DIVERT_AZ_RAIL_ID)) or -1)
        except ValueError:
            return
        letters = self._divert_az_letters or '#ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if not (0 <= pos < len(letters)):
            return
        letter = letters[pos]
        try:
            section = self._divert_sections[self._divert_active_section]
        except (AttributeError, IndexError, TypeError):
            section = None
        paged = self._divert_paged
        with self._ui_lock:
            if self._az_jump_active:
                return
            self._az_jump_active = True
            gen = self._view_load_gen

        def work():
            try:
                # Server ground truth for the letter boundary: raw-title
                # matching is unreliable (this server sorts 'The Amateur'
                # under 'A' but 'The Tower' under 'T'), so ask Plex which
                # item opens the letter section -- /firstCharacter applies
                # the same sort + filters as the grid -- then locate THAT
                # item in the loaded window by ratingKey.
                target_key = None
                if (self._plex_client and section
                        and section.get('type') in ('movie', 'show', 'artist')
                        and not self._divert_search_query
                        and str(self._divert_sort).startswith('titleSort')):
                    try:
                        params = {
                            'sort': self._divert_sort,
                            'X-Plex-Container-Size': 1,
                        }
                        if self._divert_filter_genre:
                            params['genre'] = self._divert_filter_genre
                        unwatched = self._divert_filter_unwatched
                        if unwatched is True:
                            params['unwatched'] = 1
                        elif unwatched is False:
                            params['unwatched'] = 0
                        for key, value in \
                                (self._divert_filter_params() or {}).items():
                            params[key] = value
                        data = self._plex_client._request(
                            '/library/sections/{}/firstCharacter/{}'.format(
                                section['key'], urllib.parse.quote(letter)),
                            params)
                        md = plex_client.PlexClient._media_container(data).get(
                            'Metadata') or []
                        if md:
                            target_key = str(md[0].get('ratingKey') or '')
                    except Exception as e:
                        xbmc.log('Akasha Aura: AZ firstCharacter failed: {}'.format(e),
                                 xbmc.LOGWARNING)
                        target_key = None

                def find_index():
                    for i, item in enumerate(self._divert_items):
                        if target_key is not None:
                            if str(item.get('rating_key') or '') == target_key:
                                return i
                            continue
                        # Plex sorts by titleSort (articles stripped,
                        # diacritics folded): 'The Amateur' lives under 'A',
                        # 'À contre-sens' under 'A' too -- the rail must
                        # match that sort key or it lands on raw-title
                        # false positives.
                        title = (item.get('sort_title')
                                 or item.get('title') or '')
                        title = title.strip()
                        if not title:
                            continue
                        first = unicodedata.normalize('NFKD', title)[0].upper()
                        if letter == '#' and first.isdigit():
                            return i
                        if first == letter:
                            return i
                    return None

                target = find_index()
                # The rail must also reach items beyond the loaded window:
                # pull the list forward through the same fetch pipeline
                # (same filters and sort) until the letter appears or the
                # source is exhausted. 500-item chunks keep a 5k-title
                # library to ~10 requests instead of ~100; each chunk's
                # render is sliced so no single critical section starves
                # input reads for hundreds of ms.
                guard = 0
                while (target is None and paged is not None
                       and not paged.exhausted and guard < 40):
                    if self._closing or gen != self._view_load_gen:
                        return
                    try:
                        chunk = paged.fetch_page(len(paged.items), 500)
                    except Exception as e:
                        xbmc.log('Akasha Aura: AZ chunk fetch failed: {}'.format(e),
                                 xbmc.LOGWARNING)
                        break
                    page, _total = chunk if isinstance(chunk, tuple) \
                        else (chunk, None)
                    if not page:
                        paged.exhausted = True
                        break
                    for i in range(0, len(page), 100):
                        sl = page[i:i + 100]
                        with self._ui_lock:
                            if self._closing or gen != self._view_load_gen:
                                return
                            paged.items.extend(sl)
                            self._divert_items = paged.items
                            self._divert_append_new(sl)
                    target = find_index()
                    guard += 1
                if target is None:
                    return
                with self._ui_lock:
                    if self._closing or gen != self._view_load_gen:
                        return
                    try:
                        panel = self.getControl(DIVERT_PANEL_ID)
                        panel.selectItem(target)
                        self.setFocus(panel)
                    except RuntimeError:
                        pass
            finally:
                with self._ui_lock:
                    self._az_jump_active = False

        self._view_pool.submit(work)

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
            position = gui_guard.selpos(self, DIVERT_PANEL_ID)
        except RuntimeError:
            return
        paged = self._divert_paged
        paged.prefetch_async(
            position,
            lambda items: self._queue_pending_append(
                DIVERT_PANEL_ID, paged, items),
            on_error=lambda e: xbmc.log(
                'Akasha Aura: Divertissement pagination fetch failed: {}'
                .format(e), xbmc.LOGWARNING))

    def _divert_append_new(self, new_items):
        """Append freshly fetched items to the grid after swapping out the
        stale trailing placeholders they replace."""
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

    def _select_jeux_subtab(self, index, interactive=True):
        self._jeux_active_subtab = index
        self.setProperty('JeuxActiveSubtab', str(index))
        self._sync_navigation()

        if index == JEUX_SUBTAB_OTHERS:
            self._load_other_games()
            try:
                self.getControl(JEUX_STATUS_ID).setLabel(i18n.tr(33082))
            except RuntimeError:
                pass
            return

        if index == JEUX_SUBTAB_STEAMLINK:
            client = self._get_steam_client(prompt_if_missing=interactive)
            if not client or not client.is_configured():
                self._set_jeux_panel([], i18n.tr(33083))
                return
            try:
                games = client.owned_games_sorted_by_recent()
            except steam_client.SteamAPIError as e:
                xbmc.log('Akasha Aura: Steam load failed: {}'.format(e), xbmc.LOGERROR)
                self._set_jeux_panel([], i18n.tr(33084))
                return
            self._jeux_items = [
                {'title': g['name'], 'thumb_url': g['box_art_url'], 'source': 'steam'}
                for g in games
            ]
            self._set_jeux_panel(self._jeux_items, i18n.tr(33085).format(len(games)))
            if interactive and self._jeux_items:
                self._defer_focus(JEUX_PANEL_ID)
            return

        if index == JEUX_SUBTAB_MOONLIGHT:
            client = self._get_sunshine_client(prompt_if_missing=interactive)
            if not client or not client.is_configured():
                self._set_jeux_panel([], i18n.tr(33086))
                return
            try:
                apps = client.apps()
            except sunshine_client.SunshineAPIError as e:
                xbmc.log('Akasha Aura: Sunshine load failed: {}'.format(e), xbmc.LOGERROR)
                self._set_jeux_panel([], i18n.tr(33087))
                return
            self._jeux_items = [
                {'title': a['name'], 'thumb_url': a['box_art_url'], 'source': 'sunshine'}
                for a in apps
            ]
            self._set_jeux_panel(self._jeux_items, i18n.tr(33088).format(len(apps)))
            if interactive and self._jeux_items:
                self._defer_focus(JEUX_PANEL_ID)

    def _select_app_subtab(self, index):
        self._app_subtab = index
        self.setProperty('AppActiveSubtab', str(index))
        self._sync_navigation()
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
        return steam_client.SteamClient(api_key, steam_id, timeout=5)

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
        return sunshine_client.SunshineClient(server_url, username, password, timeout=5)

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
                status.setLabel(i18n.tr(33316))
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
            status.setLabel(i18n.tr(33317))

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
        # Keep the tab list's selected item aligned when the tab change
        # comes from code (Home press, programmatic focus) rather than
        # from left/right inside the list itself.
        try:
            tabs = self.getControl(TAB_LIST_ID)
            if gui_guard.pos(tabs) != index:
                tabs.selectItem(index)
            self._tab_list_pos = index
        except (RuntimeError, AttributeError):
            pass

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
        self._sync_navigation()

    def onFocus(self, controlID):
        self._last_focus_change = time.monotonic()
        # Focus changes that bypass onAction (programmatic setFocus,
        # Kodi restoring focus when a modal sub-window closes) must still
        # drive the bar retract/return animations.
        try:
            self._update_bar_focused()
        except RuntimeError:
            pass
        if controlID == DIVERT_PANEL_ID:
            # Same cache pre-warm as the reco rows, for the library grid.
            try:
                pos = gui_guard.selpos(self, DIVERT_PANEL_ID)
                items = (self._divert_paged.items
                         if self._divert_paged else [])
                if 0 <= pos < len(items):
                    self._prefetch_detail(items[pos])
            except RuntimeError:
                pass

    def _update_bar_focused(self):
        """Update the top-bar focused property used by the retract animation."""
        focused = self.getFocusId()
        is_bar_focused = focused in BAR_CONTROL_IDS
        self.setProperty('AuraBarFocused', 'true' if is_bar_focused else 'false')

    def _populate_tab_list(self):
        """Fill the module tab list. Static <content> items declared in the
        XML render but are not navigable inside a WindowXMLDialog, so the
        items are added from the script, like skinshortcuts does for the
        native main menu."""
        try:
            tabs = self.getControl(TAB_LIST_ID)
        except RuntimeError:
            return
        if tabs.size() == len(config.TABS):
            return
        tabs.reset()
        icons = ('tab-divertissement.png', 'tab-jeux.png', 'tab-app.png')
        for name, icon in zip(config.TABS, icons):
            item = xbmcgui.ListItem(name)
            item.setArt({'icon': icon})
            tabs.addItem(item)
        self._tab_list_pos = 0

    def _focus_tab(self, index):
        """Focus the module tab list on the given tab (the list widens its
        focused slot into the pill itself, like the native menu bar)."""
        try:
            tabs = self.getControl(TAB_LIST_ID)
            tabs.selectItem(index)
            self._tab_list_pos = index
            self.setFocus(tabs)
        except RuntimeError:
            pass

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_MOVE_UP, ACTION_MOVE_DOWN, ACTION_MOVE_LEFT,
                   ACTION_MOVE_RIGHT, ACTION_SELECT_ITEM,
                   ACTION_CONTEXT_MENU):
            # A real keypress cancels any pending deferred focus -- the
            # user's own navigation always wins over a stale target.
            self._focus_generation += 1
            # Render pages the async prefetch workers finished fetching
            # since the last keypress (keeps network latency off the
            # input path -- see PagedList.prefetch_async).
            self._drain_pending_appends()
        if aid == ACTION_MENU:
            self._open_settings_panel()
            return
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            # Plex two-level Back: from the content, Back moves focus to
            # the nav rail; from the nav it exits the app.
            if self.getFocusId() in _CONTENT_BACK_IDS:
                self._focus_sidebar()
                return
            self.close()
            return
        focused = self.getFocusId()
        # Plex long-press: content cards open an option sheet whose
        # entries depend on the element type (see
        # _open_item_context_menu); navigation elements (sidebar, genre
        # cards) keep the long-press == click parity.
        if aid == ACTION_CONTEXT_MENU:
            if focused in RECO_ALL_LIST_IDS:
                self._on_reco_context_menu(focused)
            elif focused == DIVERT_PANEL_ID:
                self._on_divert_context_menu()
            elif focused == CATEGORY_PANEL_ID:
                self._on_category_genre_selected()
            elif focused == DIVERT_SIDEBAR_ID:
                self._on_sidebar_item_selected()
            return
        # Sidebar kebab: Plex-style per-library '...' menu, reachable by
        # pressing Left on a sidebar library item (Left is otherwise a
        # dead key on the rail). Offers pin/unpin plus move up/down when
        # the library is pinned.
        if aid == ACTION_MOVE_LEFT and focused == DIVERT_SIDEBAR_ID:
            # A LEFT re-delivered to the sidebar right after a hop into it
            # (grid Left / chip Left / rail Left) must not pop the kebab.
            if (time.monotonic() -
                    getattr(self, '_last_focus_change', 0)) >= 0.05:
                self._sidebar_item_menu()
            self._update_bar_focused()
            return
        # A-Z rail: Left is self-pinned in the XML (a declared hop would
        # re-deliver the press into the grid, which would hop again to the
        # sidebar) -- the interception owns the exit.
        if aid == ACTION_MOVE_LEFT and focused == DIVERT_AZ_RAIL_ID:
            self._defer_focus(DIVERT_PANEL_ID)
            self._update_bar_focused()
            return
        # The A-Z rail's static <content> items carry no <onclick>, so Kodi
        # treats them as dead items and never dispatches GUI_MSG_CLICKED to
        # onClick() -- Select must be routed manually, like a long-press.
        if aid == ACTION_SELECT_ITEM and focused == DIVERT_AZ_RAIL_ID:
            self._divert_az_jump()
            return
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
        # Inside the tab list, focus stays on the same control while the
        # selected item changes -- the active tab follows the selection,
        # like the native main menu's Container().ListItem binding. The
        # selection-vs-edge decision is deferred until after
        # super().onAction() has processed the move: whether Kodi calls us
        # before or after the internal item move, comparing the position
        # across super() is the only ordering-agnostic way to tell "moved
        # to a neighbour item" apart from "stayed put at an edge exit".
        # (XML <onleft>/<onright> can't be used either: a list consumes
        # them on EVERY horizontal press, not just at the edges.)
        if focused == TAB_LIST_ID:
            if aid == ACTION_MOVE_DOWN:
                self._focus_first_subtab()
                self._update_bar_focused()
                return
            if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT):
                # Kodi may call onAction before OR after the internal item
                # move depending on the control path, so the position delta
                # alone can't tell "moved" from "stayed at an edge". Track
                # the last observed selection in _tab_list_pos instead: a
                # press that produced a new position is a move (sync the
                # module), a press that produced the same position at the
                # matching edge is an exit (search on the left, gear on the
                # right). XML <onleft>/<onright> can't be used: a list
                # consumes them on EVERY horizontal press.
                last_known = getattr(self, '_tab_list_pos', self.active_tab)
                super().onAction(action)
                try:
                    pos_after = gui_guard.selpos(self, TAB_LIST_ID)
                except RuntimeError:
                    pos_after = last_known
                last = len(config.TABS) - 1
                # Kodi lists wrap around and onAction can fire before OR
                # after the internal item move, so compare the final
                # position against the tracked one per direction. A press
                # that lands in the expected direction is an item move
                # (sync the module). Staying/wrapping past the tracked
                # edge is an exit -- search on the left, gear on the
                # right -- and the wrap is undone. IMPORTANT: a nav press
                # that transferred focus INTO the list (gear ->Left-> list)
                # is re-delivered here a second time without moving items;
                # the edge exit therefore only fires when the tracked
                # position was ALREADY at that edge, else a transferred
                # Left would eject to search from the middle of the bar.
                if aid == ACTION_MOVE_RIGHT and pos_after > last_known:
                    self._tab_list_pos = pos_after
                    if pos_after != self.active_tab:
                        self._show_tab(pos_after)
                elif aid == ACTION_MOVE_LEFT and pos_after < last_known:
                    self._tab_list_pos = pos_after
                    if pos_after != self.active_tab:
                        self._show_tab(pos_after)
                elif ((aid == ACTION_MOVE_RIGHT and last_known == last)
                        or (aid == ACTION_MOVE_LEFT and last_known == 0)):
                    tabs = self.getControl(TAB_LIST_ID)
                    edge = 0 if aid == ACTION_MOVE_LEFT else last
                    if pos_after != edge:
                        tabs.selectItem(edge)
                    self._tab_list_pos = edge
                    try:
                        self.setFocus(self.getControl(
                            MODULE_SEARCH_ID if aid == ACTION_MOVE_LEFT
                            else GEAR_BUTTON_ID))
                    except RuntimeError:
                        pass
                self._update_bar_focused()
                return
        if aid == ACTION_MOVE_UP and focused in (DIVERT_SUBTAB_IDS + JEUX_SUBTAB_IDS + APP_SUBTAB_IDS + HOME_TAB_IDS):
            # A native hop INTO the strip (e.g. the grid's edge-exit onup
            # on the Collections/Categories tab) makes Kodi re-deliver the
            # same press to the landed control; without the recency guard
            # a single Up would cascade grid -> tab -> bar.
            if (time.monotonic() -
                    getattr(self, '_last_focus_change', 0)) < 0.05:
                return
            self._focus_tab(self.active_tab)
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_DOWN and \
                focused in (DIVERT_SUBTAB_IDS + JEUX_SUBTAB_IDS +
                            APP_SUBTAB_IDS + HOME_TAB_IDS):
            # Same cascade, Down direction: a native hop from the tab bar
            # into the strip re-delivers the press and ondown ejects
            # straight to the content -- the strip must actually receive
            # focus (Plex: bar -> tab strip -> cards).
            if (time.monotonic() -
                    getattr(self, '_last_focus_change', 0)) < 0.05:
                return
        # Recommande row viewport (see RECO_SLOT_IDS): Plex pins the focused
        # row at a fixed screen position -- focus stays on a slot while its
        # contents slide by one hub when scrolling past an edge.
        if aid == ACTION_MOVE_DOWN and \
                focused in (RECO_LIST_IDS[-1], RECO_LANDSCAPE_IDS[-1]) \
                and self._reco_slot_has_row(len(RECO_SLOT_IDS)):
            self._reco_scroll(+1)
            self._defer_hero()
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_UP and \
                focused in (RECO_LIST_IDS[0], RECO_LANDSCAPE_IDS[0]) \
                and self._hub_offset > 0:
            self._reco_scroll(-1)
            self._defer_hero()
            self._update_bar_focused()
            return
        # Prevent Down landing on an empty slot when fewer hubs remain than
        # slots, and Up from the top slot reaching the right header control
        # (contextual tabs in a library, main tab bar on Accueil).
        slot = self._reco_slot_index(focused)
        # Between slots, Up/Down must be explicit: while a lower row holds
        # focus the exited rows above play their counter-slide + fade and
        # the viewport group slides up, so their *rendered* bounds sit
        # below the focused row. Kodi's geometric resolver then reads an
        # inverted order -- observed on-device: Down from slot 1 wrapped
        # back onto the slid-down row 0, and Up skipped a row entirely.
        # Chain both directions to filled neighbours deterministically.
        if aid == ACTION_MOVE_UP and slot > 0:
            prev = next((self._reco_slot_list_id(j)
                         for j in range(slot - 1, -1, -1)
                         if self._reco_list_has_items(
                             self._reco_slot_list_id(j))), None)
            if prev is not None:
                try:
                    self.setFocus(self.getControl(prev))
                except RuntimeError:
                    pass
            self._defer_hero()
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_DOWN and 0 <= slot < len(RECO_SLOT_IDS) - 1:
            nxt = next((self._reco_slot_list_id(j)
                        for j in range(slot + 1, len(RECO_SLOT_IDS))
                        if self._reco_list_has_items(
                            self._reco_slot_list_id(j))), None)
            if nxt is not None:
                try:
                    self.setFocus(self.getControl(nxt))
                except RuntimeError:
                    pass
            self._defer_hero()
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_UP and \
                focused in (RECO_LIST_IDS[0], RECO_LANDSCAPE_IDS[0]):
            if self._divert_view == 'library':
                self.setFocus(self.getControl(DIVERT_SUBTAB_IDS[0]))
            else:
                self.setFocus(self.getControl(HOME_TAB_IDS[self._home_tab]))
            self._update_bar_focused()
            return
        # NOTE (see docs/aura/decisions.md): pressing Up from
        # DIVERT_PANEL_ID's grid lands on the module tab list (2007)
        # instead of the Bibliotheque tab button (3100), even though the
        # grid's XML declares <onup>3100</onup> and 3100 is confirmed
        # visible/enabled at that moment -- Kodi's native navigation
        # resolves Up geometrically for this horizontal list rather than
        # honouring the explicit onup. Redirect Up *before* Kodi sees it:
        # on the grid's top row (6 columns of 283 px inside 1698 px),
        # focus the declared subtab and swallow the action so no
        # super()-driven hop to 2007 ever happens. Deeper rows still
        # delegate to super(), which moves Up a row inside the grid.
        # Chips sit between the tab strip and the grid; Up from the grid's
        # top row lands on the first chip, Up from any chip lands on the
        # Bibliotheque tab, Down goes back to the grid, Left on the first
        # chip exits to the sidebar rail. All four directions are self-pinned
        # in the XML: a declared hop moves focus mid-action and Kodi then
        # re-delivers the SAME press to the newly focused control, cascading
        # grid -> chip -> tab -> bar in a single Up (observed on-device).
        # The interception owns the hop via _defer_focus, and the
        # _last_focus_change guard swallows the re-delivered press itself:
        # it arrives ~0ms after the hop's onFocus, a real keypress never
        # lands that soon after a focus change.
        chip_ids = (DIVERT_FILTER_BUTTON_ID, DIVERT_SORT_BUTTON_ID,
                    DIVERT_CLEAR_BUTTON_ID, DIVERT_RESET_BUTTON_ID)
        if focused in chip_ids and aid in (ACTION_MOVE_UP,
                                         ACTION_MOVE_DOWN,
                                         ACTION_MOVE_LEFT):
            redelivered = (time.monotonic() -
                           getattr(self, '_last_focus_change', 0)) < 0.05
            if redelivered:
                return
            if aid == ACTION_MOVE_UP:
                self._defer_focus(3100)
            elif aid == ACTION_MOVE_DOWN:
                self._defer_focus(DIVERT_PANEL_ID)
            elif focused == DIVERT_FILTER_BUTTON_ID:
                self._defer_focus(DIVERT_SIDEBAR_ID)
            else:
                super().onAction(action)
            self._update_bar_focused()
            return
        # Grid top-edge exit is fully native: _sync_navigation() points the
        # panel's declared onup at the chips row (Bibliotheque tab) or the
        # active subtab, and Kodi only applies it at the top edge while
        # interior moves stay inside the panel. Kodi's selected-position
        # marker is stale after refill/refocus (observed 96 with the cursor
        # on item 1), so no Python-side row check can be trusted here.
        super().onAction(action)
        if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_MOVE_UP, ACTION_MOVE_DOWN):
            focused = self.getFocusId()
            # DIVERT_PANEL_ID is a wrapping grid (scrolls vertically), so
            # Up/Down are its primary scroll directions now -- Left/Right
            # only move a column within the currently loaded rows, kept
            # here too in case a future layout changes column count.
            if focused == DIVERT_PANEL_ID:
                self._maybe_load_more_divert()
            elif focused in RECO_ALL_LIST_IDS:
                if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT):
                    self._maybe_load_more_reco(focused)
                # The Plex hero follows the focused card on every move --
                # left/right within a row, up/down between rows.
                self._update_hero()
        self._update_bar_focused()

    def _first_subtab_id(self):
        """Control id of the contextual strip entry for the active module."""
        if self.active_tab == TAB_DIVERTISSEMENT:
            if self._divert_view == 'library':
                return DIVERT_SUBTAB_IDS[self._divert_library_tab]
            return HOME_TAB_IDS[self._home_tab]
        if self.active_tab == TAB_JEUX:
            return JEUX_SUBTAB_IDS[self._jeux_active_subtab]
        if self.active_tab == TAB_APP:
            return APP_SUBTAB_IDS[self._app_subtab]
        return None

    def _first_content_id(self):
        """Control id focused by Down from the top bar.

        Plex lands the user straight on the most obvious content
        ("Continuer à regarder", the library grid's first card, a game
        tile...) rather than the contextual sub-tab strip -- the strip is
        still reachable by pressing Up from the first row.
        """
        if self.active_tab == TAB_DIVERTISSEMENT:
            if self._divert_state is not None:
                return DIVERT_STATE_BUTTON_ID
            if self._divert_view == 'library' \
                    and self._divert_library_tab != DIVERT_SUBTAB_RECOMMANDE:
                return (CATEGORY_PANEL_ID
                        if self._divert_library_tab == DIVERT_SUBTAB_CATEGORIES
                        else DIVERT_PANEL_ID)
            return next((self._reco_slot_list_id(i)
                         for i in range(len(RECO_SLOT_IDS))
                         if self._reco_list_has_items(
                             self._reco_slot_list_id(i))),
                        DIVERT_SIDEBAR_ID)
        if self.active_tab == TAB_JEUX:
            return (JEUX_PANEL_ID if self._jeux_items
                    else JEUX_SUBTAB_IDS[self._jeux_active_subtab])
        if self.active_tab == TAB_APP:
            return (APP_TILE_IDS[0] if self._pinned_apps
                    else APP_SUBTAB_IDS[self._app_subtab])
        return None

    def _focus_first_subtab(self):
        """Move focus from the main tab to the first content element."""
        try:
            target = self._first_content_id()
            # Immediate setFocus AND a deferred re-apply: a same-tick
            # setFocus races Kodi's own post-action resolution of the source
            # control's undeclared direction and loses intermittently
            # (observed on-device: Down from the bar sometimes landed on the
            # chips row instead of the grid). When the immediate focus wins
            # the race the deferred apply is a silent no-op.
            if target is not None:
                self.setFocus(self.getControl(target))
                self._defer_focus(target)
        except Exception as e:
            xbmc.log('Akasha Aura: focus first content failed: {}'.format(e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID == TAB_LIST_ID:
            try:
                self._show_tab(gui_guard.selpos(self, TAB_LIST_ID))
            except RuntimeError:
                pass
        elif controlID in HOME_TAB_IDS:
            self._set_home_tab(HOME_TAB_IDS.index(controlID))
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
            self._open_more()
        elif controlID == DIVERT_PANEL_ID:
            self._on_divert_item_selected()
        elif controlID in RECO_ALL_LIST_IDS:
            self._on_reco_item_selected(controlID)
        elif controlID == CATEGORY_PANEL_ID:
            self._on_category_genre_selected()
        elif controlID == DIVERT_FILTER_BUTTON_ID:
            self._divert_open_filter_menu()
        elif controlID == DIVERT_CLEAR_BUTTON_ID:
            self._divert_reset_filters()
        elif controlID == DIVERT_SORT_BUTTON_ID:
            self._divert_open_sort_menu()
        elif controlID == DIVERT_PLAY_BUTTON_ID:
            self._divert_play_first()
        elif controlID == DIVERT_SHUFFLE_BUTTON_ID:
            self._divert_play_random()
        elif controlID == DIVERT_RESET_BUTTON_ID:
            self._divert_open_more_menu()
        elif controlID == DIVERT_AZ_RAIL_ID:
            self._divert_az_jump()
        elif controlID == DIVERT_STATE_BUTTON_ID:
            self._on_state_action()
        elif controlID == MODULE_SEARCH_ID:
            self._open_search()
        elif controlID == GEAR_BUTTON_ID:
            self._open_settings_menu()

    def _on_jeux_item_selected(self):
        try:
            pos = gui_guard.selpos(self, JEUX_PANEL_ID)
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

    def _on_sidebar_item_selected(self, pos=None):
        if pos is None:
            try:
                pos = gui_guard.selpos(self, DIVERT_SIDEBAR_ID)
            except RuntimeError:
                return
        if pos == DIVERT_SIDEBAR_PROFILE_INDEX:
            self._open_profile_menu()
            return
        if pos == DIVERT_SIDEBAR_LISTS_INDEX:
            self._open_my_lists()
            return
        if pos == DIVERT_SIDEBAR_SEARCH_INDEX:
            self._open_search()
            return
        if pos == DIVERT_SIDEBAR_HOME_INDEX:
            self._activate_home()
            return
        if pos == DIVERT_SIDEBAR_LIBS_HEADER_INDEX:
            return
        # More sits after the *displayed* sections -- tail-appended
        # pseudo-sections (live TV) populate no sidebar row, so they
        # must not shift the More/On Plex positions.
        display_count = sum(
            1 for s in self._divert_sections if s.get('type') != 'livetv')
        more_index = display_count + DIVERT_SIDEBAR_LIBS_OFFSET
        if pos == more_index:
            self._open_more()
            return
        if self._sidebar_onplex_index is not None:
            rel = pos - self._sidebar_onplex_index
            if rel == 0:
                return  # 'On Plex' divider
            if rel == 1:
                self._open_live_tv()
                return
            if rel == 2:
                self._open_discover()
                return
        section_index = pos - DIVERT_SIDEBAR_LIBS_OFFSET
        if 0 <= section_index < len(self._divert_sections):
            self._activate_library(section_index)

    def _open_profile_menu(self):
        """Sidebar profile row: Plex's left-anchored submenu sheet,
        all seven rows like the app. The cloud-only entries (Switch
        Profile, Notifications, Friends, Services) show a stub
        notification; the local ones map to real actions."""
        entries = [
            (i18n.tr(33610), 'icon-switch.png'),
            (i18n.tr(33592), 'icon-profile.png'),
            (i18n.tr(33611), 'icon-bell.png'),
            (i18n.tr(33612), 'icon-friends.png'),
            (i18n.tr(33614), 'icon-services.png'),
            (i18n.tr(33593), 'icon-server.png'),
            (i18n.tr(33019), 'icon-gear.png'),
        ]
        actions = [
            self._open_profile_picker,
            self._show_profile_info,
            self._cloud_stub,
            self._cloud_stub,
            self._cloud_stub,
            self._reconnect_connector,
            self._open_settings_panel,
        ]
        # Plex stacks its sheets: Back from Settings/Profile/the switcher
        # re-opens this menu with focus on the row that opened it
        # (official-live/52), not the home screen.
        focus = 0
        while True:
            self._menu_exit = False
            dlg = aura_menu.profilemenu(self, entries, focus=focus)
            idx = dlg.result
            if idx < 0:
                pick = getattr(dlg, 'rail_pick', -1)
                if pick >= 0:
                    self._activate_rail_index(pick)
                return
            focus = idx
            actions[idx]()
            if (getattr(self, '_menu_exit', False)
                    or getattr(self, 'playback_started', False)):
                return

    def _open_profile_picker(self):
        """Plex's 'Who's watching?' picker (aura_switch): list the Plex
        Home members, ask the PIN when the profile is protected, switch
        via plex.tv, then rebuild the client + home like a cold start."""
        import aura_switch
        client = self._plex_client
        if client is None:
            server_url = self.addon.getSetting('plex.server_url')
            token = self.addon.getSetting('plex.token')
            if not config.is_plex_configured(server_url, token):
                return
            client = plex_client.PlexClient(server_url, token, timeout=12)
        try:
            users = client.home_users()
        except Exception as e:
            xbmc.log('Akasha Aura: home users fetch failed: {}'.format(e),
                     xbmc.LOGWARNING)
            self._cloud_stub()
            return
        if not users:
            return
        users.append({'id': None, 'add': True,
                      'title': i18n.tr(33618),
                      'thumb': 'user-add.png'})
        pick = None
        token = None
        error = False
        while True:
            # Plex flow: picker -> PIN pad -> Back lands back on the
            # picker, not on the home screen; a wrong PIN reopens the
            # pad itself with the 'incorrect PIN' line.
            if pick is None:
                pick = aura_switch.pick_user(self, users)
                if pick is None:
                    return
                if pick.get('add'):
                    # Account creation lives on app.plex.tv.
                    self._cloud_stub()
                    return
            pin = None
            if pick.get('protected'):
                pin = aura_switch.ask_pin(self, error=error)
                error = False
                if pin is None:
                    pick = None  # Back on the pad: reopen the picker
                    continue
            try:
                token = client.switch_home_user(pick['id'], pin)
                break
            except Exception as e:
                xbmc.log('Akasha Aura: home user switch failed: {}'
                         .format(e), xbmc.LOGWARNING)
                if not pick.get('protected'):
                    xbmcgui.Dialog().notification(
                        'Akasha Aura', i18n.tr(33621),
                        xbmcgui.NOTIFICATION_ERROR, 3000)
                    return
                error = True  # wrong PIN: pad reopens with the error line
        self.addon.setSetting('plex.token', token)
        plex_client._read_cache.clear()
        self._plex_client = None
        self.setProperty('AuraUserName', pick.get('title') or '')
        self.setProperty('AuraAvatarRound', '')
        self.setProperty('AuraAvatar', pick.get('thumb') or '')
        xbmcgui.Window(10000).setProperty('AuraAvatar',
                                          pick.get('thumb') or '')
        self._load_divertissement()
        self._activate_home()
        # A completed switch lands on the new profile's home, not back on
        # the account menu the sheet stack would otherwise restore.
        self._menu_exit = True

    def _cloud_stub(self):
        """Cloud-only Plex menu rows have no server-local counterpart."""
        xbmcgui.Dialog().notification(
            'Akasha Aura', i18n.tr(33613),
            xbmcgui.NOTIFICATION_INFO, 2000)

    def _show_profile_info(self):
        """Plex's 'Profile' row opens the Account sheet
        (official-live/51): the settings panel pushed straight onto its
        'account' view, filled from plex.tv /api/v2/user."""
        user = {}
        client = self._plex_client
        if client is not None:
            try:
                user = client.user_info() or {}
            except Exception as e:
                xbmc.log('Akasha Aura: user_info failed: {}'.format(e),
                         xbmc.LOGINFO)
        self._open_settings_panel(start_view='account', account_user=user)

    def _open_my_lists(self):
        """Sidebar 'My Lists' row: Plex's watchlist+lists page. The cloud
        watchlist has no server-local API, so the local equivalent is the
        playlists pseudo-section (B10) -- open it like a library."""
        index = next(
            (i for i, s in enumerate(self._divert_sections)
             if s.get('type') == 'playlist'), None)
        if index is None:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33591),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        self._activate_library(index)

    def _open_search(self):
        """Module 0: Plex-style live search screen (AuraSearch.xml)."""
        search = self._get_sub_window(
            'search', aura_search.AuraSearchWindow, 'AuraSearch.xml')
        search.addon = self.addon
        search.client = self._connector_client or self._plex_client
        # Plex searches every server library, not only the pinned ones
        # (_divert_sections is the pinned subset). Pseudo-sections like
        # Playlists / Live TV have no library endpoint: passing them to
        # the per-section title filter would 404 on every keystroke.
        pool = self._all_divert_sections or self._divert_sections
        search.sections = [s for s in pool
                           if s.get('type') in ('movie', 'show', 'artist')]
        search.on_select = self._open_search_result
        search.on_person = self._open_person_page
        search.on_genre = self._open_genre_result
        # Cached instance: clear the flag a playback launch leaves set,
        # or closing the search later re-triggers the restore loop.
        search.playback_started = False
        search.doModal()
        if getattr(search, 'playback_started', False):
            self.playback_started = True
            self._playback_item = search._playback_item
            self.close()

    def _open_search_result(self, item):
        """Search hit dispatch (B16): music types route to the grid
        drill-in / direct playback, everything else to the detail page."""
        typ = item.get('type')
        if typ in ('artist', 'album'):
            self._open_music_node(item)
            self._divert_view = 'library'
            self.setProperty('DivertView', 'library')
            self.setProperty('DivertLibraryTab',
                             str(DIVERT_SUBTAB_BIBLIOTHEQUES))
            self._divert_library_tab = DIVERT_SUBTAB_BIBLIOTHEQUES
            self._sync_navigation()
            return
        if typ == 'track':
            self._play_track(item)
            return
        self._open_detail(item)

    def _open_genre_result(self, genre):
        """Genre search hit -> library view pre-filtered to that genre,
        same in-place navigation as the Categories tiles."""
        index = next(
            (i for i, s in enumerate(self._divert_sections)
             if s['key'] == genre.get('section_key')), None)
        if index is None:
            return
        self._divert_active_section = index
        self._divert_filter_genre = genre.get('name') or ''
        self._divert_search_query = ''
        self._select_library_tab(DIVERT_SUBTAB_BIBLIOTHEQUES, focus=False)
        self._load_divert_section_items(self._divert_sections[index])
        try:
            self.setFocus(self.getControl(3100))  # Bibliotheque tab button
        except RuntimeError:
            pass

    def _open_person_page(self, person):
        """People search hit -> person page (photo + filmography)."""
        client = self._plex_client
        if not client or not person.get('person_filter'):
            return
        try:
            filmography = client.person_filmography(
                person['person_filter'])
        except Exception as e:
            xbmc.log('Akasha Aura: filmography failed: {}'.format(e),
                     xbmc.LOGWARNING)
            filmography = []
        import aura_person
        page = aura_person.AuraPersonWindow(
            'AuraPerson.xml', self.addon.getAddonInfo('path'),
            'Default', '1080i')
        page.client = client
        page.addon_path = self.addon.getAddonInfo('path')
        page.person = person
        page.items = filmography
        page.doModal()
        # Playback launched from the page's option sheet closes it; the
        # same flag cascade the detail page uses carries it through.
        if getattr(page, 'playback_started', False):
            self.playback_started = True
            self._playback_item = page._playback_item
            self.close()

    def _run_unified_search(self, query):
        groups = []  # list of (category_label, [(result_label, callback), ...])

        groups.append((i18n.tr(33159), self._search_divert(query)))
        groups.append((i18n.tr(33003), self._search_games(query)))
        groups.append((i18n.tr(33319), self._search_apps(query)))
        groups.append((i18n.tr(33019), self._search_settings(query)))

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
                'Akasha Aura', i18n.tr(33072).format(query),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return

        choice = aura_menu.select(
            self, i18n.tr(33097).format(query), flat_labels)
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
            self._focus_tab(TAB_APP)
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
            (i18n.tr(33019), self._open_settings_panel),
            (i18n.tr(33327), self._reconnect_connector),
            (i18n.tr(33157), self._settings_sleep),
            (i18n.tr(33090), self._settings_restart_menu),
            (i18n.tr(33158), self._settings_shutdown),
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
            self._divert_sections = divert_source.parse_sections(connector.sections(), section_types=('movie', 'show', 'artist'))
        except connector_client.ConnectorAPIError as e:
            xbmc.log('Akasha Aura: connector reconnect failed: {}'.format(e), xbmc.LOGWARNING)
            self.addon.setSetting('connector.session_token', '')
            xbmcgui.Dialog().notification(
                'Akasha', i18n.tr(33074), xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        self._connector_client = connector
        self._plex_client = None
        xbmcgui.Dialog().notification(
            'Akasha', i18n.tr(33073), xbmcgui.NOTIFICATION_INFO, 3000)
        self._restore_divert_view(focus=False)

    def _open_settings_menu(self):
        """Settings gear: context menu (plan 04bda1b4 phase 3), rendered
        through the shared dark AuraMenu sheet for Plex parity."""
        options = self._settings_menu_options()
        choice = aura_menu.contextmenu(self, [label for label, _ in options])
        if choice < 0:
            return
        options[choice][1]()

    def _open_settings_panel(self, start_view=None, account_user=None):
        """Unified settings panel (plan a5a87f03): categories list + curated
        actions, replacing the old direct Kodi/LibreELEC/Akasha shortcuts.
        start_view='account' jumps straight to the Plex-style Account
        sheet (profile menu's Profile row, official-live/51)."""
        if getattr(self, 'playback_started', False) or xbmc.Player().isPlayingVideo():
            # The SettingsPressMonitor stays alive while this window is
            # closed for fullscreen playback, so a (possibly spurious)
            # gear-wheel press still lands here. Opening a modal
            # sub-dialog over the video -- or having it pop up the moment
            # Aura re-opens -- is the "settings opens by itself" bug.
            # playback_started covers the whole session, including the
            # ~1-2s not-playing gap between chained playlist episodes
            # where isPlayingVideo() alone would let a press through.
            # The fullscreen OSD has its own settings gear; drop the
            # press instead.
            xbmc.log('Akasha Aura: settings press ignored during playback',
                     xbmc.LOGINFO)
            return
        now = time.time()
        if now - self._settings_last_open < 3.0:
            # The remote emits occasional spurious gear-wheel events; a
            # burst of presses must not reopen the panel repeatedly (nor
            # right after the user closed it). Deliberate presses are
            # seconds apart, so a short cooldown is invisible.
            xbmc.log('Akasha Aura: settings press ignored (debounce)',
                     xbmc.LOGINFO)
            return
        self._settings_last_open = now
        win = self._get_sub_window(
            'settings_panel', aura_settings_panel.AuraSettingsPanelWindow,
            'AuraSettingsPanel.xml')
        win.start_view = start_view
        win.account_user = account_user or {}
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
        # Plex keeps the expanded rail readable behind its settings
        # sheet. Kodi dims the parent under a modal dialog, so the panel
        # draws a full-brightness rail replica from this snapshot; the
        # AuraSheetOpen property holds the real rail expanded for the
        # dialog's lifetime.
        win.rail_items, win.rail_props = aura_menu._sidebar_snapshot(self)
        try:
            self.setProperty('AuraSheetOpen', '1')
        except (AttributeError, RuntimeError):
            pass
        try:
            win.doModal()
        finally:
            try:
                self.clearProperty('AuraSheetOpen')
            except (AttributeError, RuntimeError):
                pass
        sel = getattr(win, 'rail_selection', -1)
        if sel >= 0:
            self._activate_rail_index(sel)

    def _activate_rail_index(self, pos):
        """Activate a real sidebar entry picked from a sheet's rail
        replica (Plex keeps the rail interactive under modal sheets)."""
        try:
            sidebar = self.getControl(DIVERT_SIDEBAR_ID)
            sidebar.selectItem(pos)
            self.setFocus(sidebar)
            self._on_sidebar_item_selected(pos)
        except RuntimeError:
            pass

    def _settings_sleep(self):
        # Reuses the exact same standby+wake-on-input script already used
        # by script.akasha.guide's "Mise en veille" entry, rather than
        # duplicating it -- see docs/aura/decisions.md.
        if not aura_menu.confirm(
                self, 'Akasha', i18n.tr(33089)):
            return
        script = '/storage/.kodi/scripts/akasha-sleep.py'
        try:
            subprocess.Popen([sys.executable, script],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            xbmc.log('Akasha Aura: sleep launch error: {}'.format(e), xbmc.LOGERROR)

    def _settings_restart_menu(self):
        choice = aura_menu.select(
            self, i18n.tr(33090), [i18n.tr(33091), i18n.tr(33093)])
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
        if not aura_menu.confirm(self, 'Akasha', i18n.tr(33092)):
            return
        try:
            with open('/tmp/.kodi-restart', 'w') as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
        subprocess.Popen(['systemctl', 'restart', 'kodi'], start_new_session=True)

    def _settings_restart_system(self):
        if not aura_menu.confirm(self, 'Akasha', i18n.tr(33094)):
            return
        subprocess.Popen(['systemctl', 'reboot'], start_new_session=True)

    def _settings_shutdown(self):
        # Same splash + CEC-TV-off sequence as script.akasha.guide/
        # script.akasha.settings' shutdown action.
        if not aura_menu.confirm(
                self, 'Akasha', i18n.tr(33095)):
            return
        subprocess.run(['/storage/.kodi/scripts/show-splash.sh',
                         '/storage/.kodi/media/splash-shutdown.png', '1'])
        subprocess.Popen(['systemctl', 'poweroff'], start_new_session=True)

    def _sidebar_item_menu(self):
        """Per-library '...' menu, opened by pressing Left on a sidebar
        library item: pin/unpin from favorites, plus move up/down when
        the item is pinned -- the two options Plex groups under the
        item's kebab."""
        try:
            sidebar = self.getControl(DIVERT_SIDEBAR_ID)
            pos = gui_guard.pos(sidebar)
        except RuntimeError:
            return
        section_index = pos - DIVERT_SIDEBAR_LIBS_OFFSET
        if not (0 <= section_index < len(self._divert_sections)):
            return
        section = self._divert_sections[section_index]
        # The playlists/live-TV pseudo-entries have no pin semantics.
        if section.get('type') in ('playlist', 'livetv'):
            return
        key = section['key']
        title = section['title']
        pinned_set = set(self._divert_pinned_libraries)
        pinned = key in pinned_set

        options = [i18n.tr(33078 if pinned else 33079).format(title)]
        actions = ['toggle']
        pinned_order = [s['key'] for s in self._all_divert_sections
                        if s['key'] in pinned_set]
        if pinned:
            i = pinned_order.index(key)
            if i > 0:
                options.append(i18n.tr(33080).format(title))
                actions.append('up')
            if i < len(pinned_order) - 1:
                options.append(i18n.tr(33081).format(title))
                actions.append('down')

        idx = aura_menu.contextmenu(self, options, keep_sidebar=True)
        if idx < 0 or idx >= len(actions):
            return

        if actions[idx] == 'toggle':
            if pinned:
                pinned_set.discard(key)
            else:
                pinned_set.add(key)
            self._divert_pinned_libraries = list(pinned_set)
            self.addon.setSetting(
                'divert.pinned_libraries',
                config.serialize_pinned(self._divert_pinned_libraries))
        else:
            # Swap inside the global order so unpinned entries keep
            # their slots.
            order = [s['key'] for s in self._all_divert_sections]
            i = pinned_order.index(key)
            other = pinned_order[i - 1 if actions[idx] == 'up'
                                 else i + 1]
            ai, bi = order.index(key), order.index(other)
            order[ai], order[bi] = order[bi], order[ai]
            self._divert_library_order = order
            self.addon.setSetting(
                'divert.library_order', config.serialize_pinned(order))

        self._load_divertissement()
        # Keep focus on the sidebar where the user was; when the item
        # just vanished (unpinned while the rail shows favorites only),
        # clamp to the same row index rather than jumping to Accueil.
        try:
            sidebar = self.getControl(DIVERT_SIDEBAR_ID)
            new_index = next(
                (i for i, s in enumerate(self._divert_sections)
                 if s['key'] == key), None)
            new_pos = (DIVERT_SIDEBAR_LIBS_OFFSET + new_index
                       if new_index is not None else pos)
            sidebar.selectItem(min(new_pos, sidebar.size() - 1))
            self.setFocus(sidebar)
        except RuntimeError:
            pass

    def _open_more(self):
        """Sidebar 'Plus': Plex's More screen lists the libraries NOT
        pinned to the rail; picking one navigates to it without pinning.
        Pin/reorder management lives on each library row's '...' kebab
        (_sidebar_item_menu). When everything is pinned Plex shows the
        'No Results / Your library is empty' state
        (navigation/more_screen_003.png)."""
        pinned = set(self._divert_pinned_libraries)
        unpinned = [s for s in self._all_divert_sections
                    if s['key'] not in pinned]
        if not unpinned:
            # Plex's empty More screen: 'No Results / Your library is
            # empty / Back' (navigation/more_screen_003.png).
            aura_menu.message(self, i18n.tr(33556), i18n.tr(33555),
                              button=i18n.tr(33020))
            return
        idx = aura_menu.select(
            self, i18n.tr(33007), [s['title'] for s in unpinned])
        if idx < 0:
            return
        # Append the unpicked section for this session so the existing
        # index-based activation path can open it; _load_divertissement()
        # restores the pinned-only list on the next reload. Pseudo-
        # sections (live TV) must stay tail-appended -- the sidebar only
        # renders real sections, so a pseudo entry left mid-list would
        # shift every pos->index mapping after it.
        livetv_tail = [s for s in self._divert_sections
                       if s.get('type') == 'livetv']
        self._divert_sections = [s for s in self._divert_sections
                                 if s.get('type') != 'livetv']
        self._divert_sections.append(unpinned[idx])
        self._divert_sections.extend(livetv_tail)
        self._populate_sidebar()
        self._activate_library(
            len(self._divert_sections) - 1 - len(livetv_tail))

    def _open_discover(self):
        """Sidebar 'Discover' (On Plex): Plex's cloud browse surface.
        The closest surface we render is the Accueil 'Tendances' tab,
        which already displays the Discover provider hubs."""
        self._activate_home()
        if self._home_tab != HOME_TAB_TRENDING:
            self._set_home_tab(HOME_TAB_TRENDING)
        # Ring the rail's Discover row rather than Accueil while the
        # cloud content is shown.
        self.setProperty('DivertActiveLibrary', i18n.tr(33625))
        if self._sidebar_onplex_index is not None:
            self._set_sidebar_selection(self._sidebar_onplex_index + 2)

    def _open_live_tv(self):
        """Sidebar 'Live TV' (On Plex): Plex's free linear channels.
        The grid pages over the prefetched lineup like the playlists
        pseudo-section; selecting a channel tunes its HLS URL."""
        if not self._plex_client:
            return
        if self._live_channels is None:
            try:
                self._live_channels = self._plex_client.live_channels()
            except Exception as e:
                xbmc.log('Akasha Aura: live channels fetch failed: {}'.format(e),
                         xbmc.LOGWARNING)
                self._live_channels = []
        if not self._live_channels:
            aura_menu.message(self, i18n.tr(33556), i18n.tr(33555),
                              button=i18n.tr(33020))
            return
        # Transient pseudo-section (same trick as _open_more) but the
        # sidebar is NOT repopulated: the rail entry stays under the
        # 'On Plex' divider instead of being re-listed as a library.
        # Kept tail-appended (see _open_more) so pos->index mapping is
        # unaffected by its presence.
        self._divert_sections = [s for s in self._divert_sections
                                 if s.get('type') != 'livetv']
        section = {'key': 'livetv', 'type': 'livetv',
                   'title': i18n.tr(33624)}
        self._divert_sections.append(section)
        index = len(self._divert_sections) - 1
        self._divert_view = 'library'
        self.setProperty('DivertView', 'library')
        self.setProperty('DivertActiveLibrary', section['title'])
        self.addon.setSetting('divert.last_view', 'library')
        self._select_divert_section(index)
        if self._sidebar_onplex_index is not None:
            self._set_sidebar_selection(self._sidebar_onplex_index + 1)
        self._sync_navigation()
        try:
            self.getControl(3400).setLabel(section['title'])
        except RuntimeError:
            pass
        self._select_library_tab(DIVERT_SUBTAB_BIBLIOTHEQUES)

    def _play_channel(self, item):
        """Linear Plex channel: tune the HLS URL. Needs
        inputstream.adaptive for demuxing -- absent on the LibreELEC
        build, so the stream drops back to the grid (documented
        limitation, same class as cloud trailers)."""
        url = item.get('tune_url')
        if not url:
            xbmcgui.Dialog().notification(
                'Akasha Aura', i18n.tr(33075),
                xbmcgui.NOTIFICATION_INFO, 2000)
            return
        li = xbmcgui.ListItem(item.get('title') or '')
        li.setMimeType('application/vnd.apple.mpegurl')
        self.playback_started = True
        self._playback_item = item
        self.close()
        xbmc.Player().play(url, li)

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
                i18n.tr(33078 if pinned else 33079).format(section['title']))
            actions.append(('toggle', key))
            idx = all_sections.index(section)
            if idx > 0:
                options.append(i18n.tr(33080).format(section['title']))
                actions.append(('up', key))
            if idx < len(all_sections) - 1:
                options.append(i18n.tr(33081).format(section['title']))
                actions.append(('down', key))

        idx = aura_menu.select(self, i18n.tr(33077), options)
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
        """Route show selections to the Plex-style detail page.

        Thin items (e.g. an episode card that only carries the show's
        rating key) are hydrated through /library/metadata first. Season
        cards open their parent show's page with that season's tab
        pre-selected, like Plex TV."""
        client = self._connector_client or self._plex_client
        if not client:
            xbmcgui.Dialog().notification(
                'Akasha Aura', item.get('title') or '', xbmcgui.NOTIFICATION_INFO, 2000)
            return
        season_index = None
        if item.get('type') == 'season' and item.get('cloud'):
            # A cloud season's parent show lives on the provider; the
            # local server only 404s the hex key.
            season_index = item.get('index')
            pk = item.get('parent_rating_key')
            if pk:
                try:
                    full = self._plex_client.provider_metadata(
                        '/library/metadata/{}'.format(pk))
                    if full:
                        full.setdefault('type', 'show')
                        item = full
                except Exception as e:
                    xbmc.log('Akasha Aura: cloud season parent '
                             'hydration failed: {}'.format(e),
                             xbmc.LOGWARNING)
        elif item.get('type') == 'season' and item.get('parent_rating_key') \
                and hasattr(client, 'metadata_item'):
            season_index = item.get('index')
            try:
                full = client.metadata_item(item['parent_rating_key'])
                if full:
                    full.setdefault('type', 'show')
                    item = full
            except Exception as e:
                xbmc.log('Akasha Aura: season parent hydration failed: {}'
                         .format(e), xbmc.LOGWARNING)
        elif not item.get('art_url') and item.get('rating_key') \
                and hasattr(client, 'metadata_item'):
            try:
                full = client.metadata_item(item['rating_key'])
                if full:
                    full.setdefault('type', 'show')
                    item = full
            except Exception as e:
                xbmc.log('Akasha Aura: show hydration failed: {}'.format(e),
                         xbmc.LOGWARNING)
        self._open_detail(item, season_index=season_index)

    def _on_divert_item_selected(self):
        try:
            pos = gui_guard.selpos(self, DIVERT_PANEL_ID)
        except RuntimeError:
            return
        if not (0 <= pos < len(self._divert_items)):
            return
        self._divert_open(self._divert_items[pos])

    def _divert_open(self, item):
        if item.get('type') == 'collection':
            self._open_collection(item)
            return
        if item.get('type') == 'playlist':
            self._open_playlist(item)
            return
        if item.get('type') == 'channel':
            self._play_channel(item)
            return
        if item.get('type') in ('artist', 'album'):
            self._open_music_node(item)
            return
        if item.get('type') == 'track':
            self._play_track(item)
            return

        section = self._divert_sections[self._divert_active_section]
        if section['type'] == 'show':
            self._open_show(item)
        else:
            self._open_detail(item)

    def _on_divert_context_menu(self):
        try:
            pos = gui_guard.selpos(self, DIVERT_PANEL_ID)
        except RuntimeError:
            return
        if not (0 <= pos < len(self._divert_items)):
            return
        item = self._divert_items[pos]
        self._open_item_context_menu(
            item, lambda: self._divert_open(item), DIVERT_PANEL_ID)

    # -- Long-press context menus (Plex option sheets) -------------------
    #
    # Plex's Android TV long-press opens a small action sheet whose
    # entries depend on the element under focus: playable items get
    # Play/Resume/Restart, everything gets Open, rateable entries get
    # Mark-as-watched + Rate, then the cloud-limited "Add to list" and a
    # File Info dump for media-bearing items. Navigation elements
    # (sidebar, genre cards) keep the plain long-press == click parity.

    def _open_item_context_menu(self, item, open_default, control_id):
        client = self._connector_client or self._plex_client
        context_sheet.open_sheet(
            self, client, item, control_id, open_default,
            on_removed=lambda pos: self._drop_card(control_id, pos))

    def _drop_card(self, control_id, pos):
        """Backing-store removal behind 'Remove from Continue
        Watching' -- the shared sheet handles the control itself."""
        row = self._reco_rows.get(control_id)
        if row and 0 <= pos < len(row[3].items):
            del row[3].items[pos]
        elif control_id == DIVERT_PANEL_ID \
                and 0 <= pos < len(self._divert_items):
            del self._divert_items[pos]

    def _sync_focused_card(self, item):
        """Refresh the focused card's watched/progress visuals from the
        (mutated) item dict -- detail-page actions stay local until the
        row reloads otherwise."""
        try:
            focused = self.getFocusId()
            if focused != DIVERT_PANEL_ID and focused not in RECO_ALL_LIST_IDS:
                return
            li = gui_guard.selitem(self, focused)
            if li is None:
                return
            tag = li.getVideoInfoTag()
            set_playcount = getattr(tag, 'setPlaycount', None) \
                or getattr(tag, 'setPlayCount', None)
            if set_playcount is not None:
                set_playcount(int(item.get('view_count') or 0))
        except (RuntimeError, TypeError):
            pass

    def _on_home_press_action(self, action):
        """React to a repeated Home press while Aura is already open.

        'single' -> return to the main Divertissement tab (close any sub-window).
        'double' -> open the minimal app switcher.
        """
        xbmc.log('Akasha Aura: home press action: {}'.format(action), xbmc.LOGINFO)
        if xbmc.Player().isPlayingVideo():
            # The window is closed while a video plays fullscreen: queue
            # the action for the re-open and leave fullscreen now -- Home
            # must always land the user back inside Aura.
            self._pending_home_action = action
            xbmc.Player().stop()
            return
        if action == 'single':
            self._close_sub_windows()
            self._show_tab(0)
            self._focus_tab(0)
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


def _format_duration(duration_ms):
    """Plex-style '1h 24m' / '24m' display for a millisecond duration."""
    if not duration_ms:
        return ''
    minutes = int(duration_ms) // 60000
    hours, minutes = divmod(minutes, 60)
    if hours:
        return '{}h {}m'.format(hours, minutes)
    return '{}m'.format(minutes)


_MONTHS_FR = ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.',
              'août', 'sept.', 'oct.', 'nov.', 'déc.')


def _format_date_fr(iso_date):
    """'2019-11-10' -> '10 nov. 2019' (Plex shows the release/air date)."""
    try:
        year, month, day = (int(p) for p in str(iso_date)[:10].split('-'))
        return '{} {} {}'.format(day, _MONTHS_FR[month - 1], year)
    except Exception:
        return ''


def _circle_avatar(url, size=80):
    """Download the plex.tv avatar and clip it to a circle, saved as a
    transparent PNG in the addon profile. Plex's rail shows a round
    avatar; Kodi can't clip a texture, so we bake the mask in. Returns ''
    on any failure (the caller then falls back to the square URL plus the
    cast-mask overlay)."""
    try:
        from PIL import Image, ImageDraw
        import io
        import urllib.request
        req = urllib.request.Request(
            url, headers={'User-Agent': 'AkashaOSAura/1.0'})
        raw = urllib.request.urlopen(req, timeout=12).read()
        im = Image.open(io.BytesIO(raw)).convert('RGBA')
        im = im.resize((size, size), Image.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        im.putalpha(mask)
        path = os.path.join(
            xbmc.translatePath('special://profile/addon_data/script.akasha.aura'),
            'avatar_circle.png')
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        im.save(path)
        return path
    except Exception:
        return ''


def _blur_hex(value):
    """Normalise an UltraBlurColors corner ('rrggbb' or '#rrggbb') to
    'RRGGBB' for setColorDiffuse, '' when absent."""
    s = str(value or '').lstrip('#')[-6:]
    return s.upper() if len(s) == 6 else ''


def _tint_hex(*values):
    """Boost a raw UltraBlurColors corner for the Plex field wash.

    Plex's blur palette is near-black by design ('040b03'), but the
    reference client paints a clearly saturated colored veil (~(123,37,43)
    measured on 53-home-for-you). Raw corners would tint invisibly, so
    the hue is kept while saturation/value are pulled up to the range the
    official client displays. Fallbacks are used when the preferred
    corner is near-neutral or absent (a forced hue would otherwise
    invent color out of quantization noise, e.g. '141314' -> magenta).
    """
    import colorsys
    best = None
    for value in values:
        hexs = _blur_hex(value)
        if not hexs:
            continue
        r, g, b = (int(hexs[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s >= 0.25:  # genuinely colored: take it and stop
            best = (h, max(s, 0.70))
            break
        if best is None:  # keep the first neutral as last resort
            best = (h, s)
    if best is None:
        return ''
    r, g, b = colorsys.hsv_to_rgb(best[0], best[1], 0.42)
    return '{:02X}{:02X}{:02X}'.format(int(round(r * 255)),
                                     int(round(g * 255)),
                                     int(round(b * 255)))


def _hub_title_fr(hub, server_name=''):
    """Localise the well-known Plex hub titles.

    The server reports hub titles in its own locale (English on Akasha),
    while the UI language is French -- so the standard hub identifiers are
    mapped here rather than trusting the raw title. Server-local rows are
    suffixed ' · {server}' like Plex ('Recently Released Movies · Akasha');
    'Continue Watching' and the cloud Discover rows are not.
    """
    identifier = (hub.get('identifier') or '').lower()
    context = (hub.get('context') or '').lower()
    title = hub.get('title') or ''
    title_lc = title.lower()
    # Section hubs use machine identifiers ('movie.inprogress'...), so the
    # raw English title is the reliable signal for standard Plex rows.
    standard = (
        'continue' in identifier or 'ondeck' in identifier
        or 'inprogress' in identifier or 'continue watching' in title_lc
        or 'on deck' in title_lc)
    if standard:
        # 'Continue Watching' is a global row: Plex shows no server suffix.
        return i18n.tr(33137), ''
    if 'recentlyadded' in identifier or 'recently added' in title_lc:
        base = i18n.tr(33138)
        if ' in ' in title:
            base += ' ' + i18n.tr(33141).format(title.rsplit(' in ', 1)[-1])
    elif 'recentlyreleased' in identifier or 'recently released' in title_lc:
        base = i18n.tr(33139)
        if 'Movies' in title:
            base += ' ' + i18n.tr(33141).format(i18n.tr(33051))
    elif 'recentlyviewed' in identifier or 'recentlywatched' in identifier \
            or 'recently viewed' in title_lc or 'recently watched' in title_lc:
        base = i18n.tr(33140)
    else:
        # Discover ("Tendances") provider hub identifiers.
        discover_titles = {
            'home.recently-released-trailers': i18n.tr(33185),
            'home.trending-trailers': i18n.tr(33186),
            'home.recommended-on-services': i18n.tr(33187),
            'home.top_watchlisted': i18n.tr(33188),
            'home.new-trailers': i18n.tr(33189),
            'home.watchlist-available': i18n.tr(33190),
            'home.coming-soon': i18n.tr(33191),
            'home.available-rentals': i18n.tr(33192),
            'home.genres': i18n.tr(33193),
            'home.historical-week': i18n.tr(33194),
            'home.blockbuster-trailers': i18n.tr(33195),
            'home.preferred-services': i18n.tr(33196),
        }
        base = discover_titles.get(identifier, title)
        # Cloud Discover rows ('Tendances') carry no server suffix; only
        # unmapped section hubs (genre/director spotlights...) fall here.
        if identifier in discover_titles:
            return base, ''

    if not server_name:
        return base, ''
    # Plex renders the suffix in a smaller, dimmer face than the row
    # title -- returned separately so the caller can render it in its
    # own label (Kodi labels cannot mix font sizes inline). A leading
    # U+00B7 is dropped by Kodi's label renderer, so the middle dot is
    # shielded by a non-breaking space (not trimmed by its ASCII trim).
    return base, ' · ' + server_name


# Plex Categories tiles: a fixed colour per genre, composited ~60% over a
# dimmed artwork. Colours sampled from the official 2026.19.1 client
# (docs/plex-parity/official-live/16-lib-categories.png); the genre
# vocabulary mirrors display_genre()'s translation table.
_GENRE_TILE_COLORS = {
    'action': '3A7174', 'action/adventure': '6E5B45',
    'adventure': '8F3849', 'animation': '46792A', 'anime': '4A5E8C',
    'biography': '7B2234', 'biographie': '7B2234',
    'children': '3E7A6E', 'enfants': '3E7A6E', 'kids': '3E7A6E',
    'comedy': '6E5F28', 'comedie': '6E5F28', 'comédie': '6E5F28',
    'comédie musicale': '8C5A3A', 'musical': '8C5A3A',
    'crime': '2E4263', 'documentary': 'A55F55', 'documentaire': 'A55F55',
    'drama': '70653A', 'drame': '70653A',
    'family': '8C4A78', 'familial': '8C4A78',
    'fantasy': '495628', 'fantastique': '495628',
    'film-noir': '3A3A3A', 'history': '434C1D', 'histoire': '434C1D',
    'horror': '3A2538', 'horreur': '3A2538',
    'independent': '4A5560', 'indépendant': '4A5560',
    'martial arts': '6B3A3A', 'arts martiaux': '6B3A3A',
    'mini-series': '4A6B8C', 'mini-série': '4A6B8C',
    'music': '7A3E6E', 'musique': '7A3E6E',
    'mystery': '37474F', 'mystère': '37474F',
    'romance': '8C3A4E', 'science fiction': '2E5E7A',
    'science-fiction': '2E5E7A', 'sci-fi': '2E5E7A',
    'sport': '3A6B5A', 'suspense': '3A3A55',
    'thriller': '2E3050', 'tv movie': '556B6E', 'téléfilm': '556B6E',
    'war': '7E3F74', 'guerre': '7E3F74',
    'western': '6E4B26', 'court-métrage': '5A5A6E', 'short': '5A5A6E',
    'japanimé': '5A4A7A', 'cuisine': '6E5A3A',
}


def _genre_tile_color(genre):
    """Plex Categories tile colour ('RRGGBB') for a genre name; unknown
    genres get a muted slate derived from the name so every tile still
    looks deliberate instead of defaulting to one flat navy."""
    color = _GENRE_TILE_COLORS.get((genre or '').strip().lower())
    if color:
        return color
    # Deterministic fallback: muted hue from the name's hash.
    h = sum(bytearray((genre or 'x').encode('utf-8', 'replace')))
    return '{:02X}{:02X}{:02X}'.format(
        0x34 + (h % 3) * 0x1A, 0x40 + ((h // 3) % 3) * 0x1A,
        0x50 + ((h // 9) % 3) * 0x1A)


def _hero_meta_line(item, compact=False):
    """Plex hero meta row: 'S18 • E6   10 nov. 2019   21m' for episodes,
    '2002   1h 50m   Comédie, Mystère' for movies (rating chip rendered
    separately). Matches docs/plex-parity/SPEC.md measurements.

    The library Recommande hero is the compact variant: no genres and no
    cast (official 13-library-films shows '2017   84m   G' only)."""
    parts = []
    item_type = item.get('type')
    unreleased = _unreleased_label(item)
    if item_type == 'episode':
        if item.get('season') is not None and item.get('index') is not None:
            parts.append('S{} • E{}'.format(item['season'], item['index']))
        elif item.get('index') is not None:
            parts.append('E{}'.format(item['index']))
        date = unreleased or _format_date_fr(
            item.get('originally_available_at'))
        if date:
            parts.append(date)
        duration = _format_duration(item.get('duration_ms'))
        if duration:
            parts.append(duration)
    elif item_type == 'movie':
        if unreleased:
            parts.append(unreleased)
        elif item.get('year'):
            parts.append(str(item['year']))
        duration = _format_duration(item.get('duration_ms'))
        if duration:
            parts.append(duration)
        genres = item.get('genres') or []
        if genres and not compact:
            parts.append(', '.join(genres[:2]))
    else:  # show / season / other
        if unreleased:
            parts.append(unreleased)
        elif item.get('year'):
            parts.append(str(item['year']))
        genres = item.get('genres') or []
        if genres and not compact:
            parts.append(', '.join(genres[:2]))
        duration = _format_duration(item.get('duration_ms'))
        if duration:
            parts.append(duration)
    return '   '.join(parts)


def _unreleased_label(item):
    """Plex's amber 'Releasing Oct 29' hero meta, shown in place of the
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
    return '[COLOR FFE5A00D]{}[/COLOR]'.format(
        i18n.tr(33600).format(i18n.fmt_air_date(str(oa)[:10])))


def _truncate_plot(text, limit=130):
    """Clamp the hero synopsis to roughly two lines (like Plex): cut at a
    word boundary and append an ellipsis when truncated."""
    text = ' '.join((text or '').split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].rstrip(',;:.')
    return cut + '…'


_KODI_MEDIA_TYPES = frozenset(
    ('video', 'movie', 'tvshow', 'season', 'episode', 'musicvideo', 'set'))


def _set_resume_point(li, item):
    """StartOffset is the only resume mechanism Player.play(url, li)
    honors (the videotag resume point is only read via the Kodi media
    DB); the rest is belt & suspenders -- see aura_detail's
    apply_resume_point."""
    offset = float(item['view_offset_ms']) / 1000.0
    try:
        li.getVideoInfoTag().setResumePoint(
            offset, float(item.get('duration_ms') or 0) / 1000.0)
    except Exception:
        pass
    li.setProperty('resumetime', str(offset))
    li.setProperty('totaltime',
                   str(float(item.get('duration_ms') or 0) / 1000.0))
    li.setProperty('StartOffset', str(offset))


def _build_divert_list_item(item):
    # Plex home rows carry no per-card text: the hero (driven by the focused
    # item, see Aura.xml "Plex hero" group) shows title/meta/plot. Labels are
    # still filled so grid-type views keep their two-line caption.
    li = xbmcgui.ListItem(i18n.ellipsize(item['title'], 22),
                          i18n.ellipsize(divert_source.item_subtitle(item), 19))
    art = {}
    if item.get('poster_url') or item.get('thumb_url'):
        art['poster'] = item.get('poster_url') or item.get('thumb_url')
        art['thumb'] = item.get('poster_url') or item.get('thumb_url')
    if item.get('fanart_url') or item.get('art_url'):
        art['fanart'] = item.get('fanart_url') or item.get('art_url')
    if item.get('landscape_url'):
        art['landscape'] = item['landscape_url']
    if item.get('logo_url'):
        art['clearlogo'] = item['logo_url']
    if art:
        li.setArt(art)

    # Kodi 20+ InfoTagVideo API (setInfo/resumetime are deprecated and warn
    # in kodi.log); the legacy path stays as fallback for stubbed test runs.
    try:
        _type = {'show': 'tvshow'}.get(item.get('type'), item.get('type'))
        tag = li.getVideoInfoTag()
        tag.setMediaType(
            _type if _type in _KODI_MEDIA_TYPES else 'video')
        tag.setTitle(item['title'])
        if item.get('summary'):
            tag.setPlot(item['summary'])
        if item.get('show_title'):
            tag.setTvShowTitle(item['show_title'])
        if item.get('year'):
            tag.setYear(int(item['year']))
        if item.get('duration_ms'):
            tag.setDuration(int(item['duration_ms']) // 1000)
        if item.get('season') is not None:
            tag.setSeason(int(item['season']))
        if item.get('index') is not None:
            tag.setEpisode(int(item['index']))
        if item.get('genres'):
            tag.setGenres(item['genres'])
        if item.get('rating'):
            tag.setRating(float(item['rating']), 0, 'plex', True)
        if item.get('content_rating'):
            tag.setMpaa(item['content_rating'])
        if item.get('directors'):
            tag.setDirectors(item['directors'])
        if item.get('writers'):
            tag.setWritingCredits(item['writers'])
        if item.get('studio'):
            tag.setStudio(item['studio'])
        if item.get('cast'):
            tag.setCast([xbmc.Actor(c['name'], c.get('role') or '')
                         for c in item['cast']])
        if item.get('view_count'):
            set_playcount = getattr(tag, 'setPlaycount', None) \
                or getattr(tag, 'setPlayCount', None)
            if set_playcount is not None:
                set_playcount(int(item['view_count']))
        if item.get('view_offset_ms') and item.get('duration_ms'):
            # No resume info on navigation cards: the card draws its own
            # Plex-style progress from AuraProgress, and playback items get
            # a real resume point later via apply_resume_point().
            pass
    except Exception:
        info = {
            'title': item['title'],
            'plot': item.get('summary') or '',
            'mediatype': item.get('type') or 'video',
        }
        if item.get('show_title'):
            info['tvshowtitle'] = item['show_title']
        if item.get('year'):
            info['year'] = item['year']
        if item.get('duration_ms'):
            info['duration'] = int(item['duration_ms']) // 1000
        if item.get('season') is not None:
            info['season'] = item['season']
        if item.get('index') is not None:
            info['episode'] = item['index']
        if item.get('genres'):
            info['genre'] = ' / '.join(item['genres'])
        if item.get('rating'):
            info['rating'] = float(item['rating'])
        if item.get('content_rating'):
            info['mpaa'] = item['content_rating']
        if item.get('directors'):
            info['director'] = ' / '.join(item['directors'])
        if item.get('writers'):
            info['writer'] = ' / '.join(item['writers'])
        if item.get('studio'):
            info['studio'] = item['studio']
        if item.get('cast'):
            info['cast'] = [(c['name'], c.get('role') or '') for c in item['cast']]
        if item.get('view_count'):
            info['playcount'] = item['view_count']
        li.setInfo('video', info)

        if item.get('view_offset_ms') and item.get('duration_ms'):
            li.setProperty('resumetime', str(float(item['view_offset_ms']) / 1000.0))
            li.setProperty('totaltime', str(float(item['duration_ms']) / 1000.0))

    if item.get('progress') is not None:
        li.setProperty('AuraProgress', str(int(item['progress'] * 100)))
    if item.get('content_rating'):
        li.setProperty('AuraContentRating', item['content_rating'])
    if item.get('audience_rating'):
        li.setProperty('AuraAudienceRating', '{:.1f}'.format(float(item['audience_rating'])))
    if item.get('rating'):
        li.setProperty('AuraCriticRating', '{:.1f}'.format(float(item['rating'])))
    if item.get('video_label'):
        li.setProperty('AuraVideoLabel', item['video_label'])
    if item.get('audio_label'):
        li.setProperty('AuraAudioLabel', item['audio_label'])
    if item.get('subtitle_label'):
        li.setProperty('AuraSubtitleLabel', item['subtitle_label'])
    if item.get('logo_url'):
        li.setProperty('AuraLogo', item['logo_url'])
    if item.get('tagline'):
        li.setProperty('AuraTagline', item['tagline'])
    if item.get('show_title'):
        li.setProperty('AuraShowTitle', item['show_title'])
    # Landscape card captions (hero-style rows): Plex heads an episode card
    # with the show title and details "S{s} · E{i} - {episode title}";
    # other types keep their own title + item_subtitle.
    land_title = item.get('show_title') or item['title']
    if item.get('show_title') and item.get('season') is not None \
            and item.get('index') is not None:
        land_sub = 'S{} · E{} - {}'.format(
            item['season'], item['index'], item['title'])
    else:
        land_sub = divert_source.item_subtitle(item)
    li.setProperty('AuraLandTitle', land_title)
    li.setProperty('AuraLandSubtitle', land_sub)
    li.setProperty('AuraDuration', _format_duration(item.get('duration_ms')))
    li.setProperty('AuraType', item.get('type') or 'video')
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
        pos = gui_guard.selpos(self, 100)
        if not (0 <= pos < len(self._actions)):
            return
        action = self._actions[pos]
        self.close()
        xbmc.executebuiltin(action)

