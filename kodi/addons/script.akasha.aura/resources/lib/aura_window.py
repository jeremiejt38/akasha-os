"""Akasha Aura — main WindowXML orchestration.

Milestone 1 (socle, see docs/aura/roadmap.md): navigable 3-tab shell with
placeholder content. Milestone 2 adds Plex entertainment rows via
plex_client.py. Later milestones fill the Games and App tabs
(addons_inventory.py, store_manifest.py) without changing this navigation
skeleton.
"""
import json

import xbmc
import xbmcaddon
import xbmcgui

import addons_inventory
import aura_app
import aura_genres
import aura_library
import aura_recommendations
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
import sunshine_client

TAB_BUTTON_IDS = (2001, 2002, 2003, 2004)

# Main-tab IDs in the same order as config.TABS.
TAB_DIVERTISSEMENT = 0
TAB_JEUX = 1
TAB_APP = 2
TAB_PARAMETRES = 3

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

DIVERT_SIDEBAR_ID = 3310
DIVERT_STATUS_ID = 3220
DIVERT_PANEL_ID = 3230
DIVERT_SIDEBAR_HOME_INDEX = 0
DIVERT_SIDEBAR_MORE_INDEX = 999  # placeholder, added dynamically
DIVERT_CACHE_TTL_SECONDS = 300

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

SETTINGS_BUTTON_IDS = (2100, 2101)

BAR_CONTROL_IDS = set(TAB_BUTTON_IDS + DIVERT_SUBTAB_IDS + JEUX_SUBTAB_IDS + APP_SUBTAB_IDS)


class AuraWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        addon = xbmcaddon.Addon('script.akasha.aura')
        self.active_tab = config.default_tab_index(addon.getSetting('tab.default'))
        self.addon = addon
        self.addon_path = addon.getAddonInfo('path')
        self._plex_client = None
        self._connector_client = None
        self._divert_sections = []
        self._all_divert_sections = []
        self._divert_active_section = 0
        self._divert_items = []
        self._divert_paged = None
        self._divert_subtab = config.default_subtab_index(
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

    def onInit(self):
        try:
            self._show_tab(self.active_tab)
            self._load_divertissement()
            self._divert_load_attempted = True
            self._select_divert_subtab(self._divert_subtab, focus=False)
            self._select_jeux_subtab(JEUX_SUBTAB_STEAMLINK)
            self._load_pinned_apps()
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            self._update_bar_focused()
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

    def _select_divert_subtab(self, index, focus=True):
        self._divert_subtab = index
        self.setProperty('DivertActiveSubtab', str(index))
        self.addon.setSetting('divert.last_subtab', str(index))

        if index == DIVERT_SUBTAB_RECOMMANDE:
            self._get_sub_window(
                'recommendations', aura_recommendations.AuraRecommendationsWindow,
                'AuraRecommendations.xml').doModal()
            return

        if index == DIVERT_SUBTAB_CATEGORIES:
            self._get_sub_window(
                'genres', aura_genres.AuraGenresWindow, 'AuraGenres.xml').doModal()
            return

        # Bibliotheques: focus sidebar and select the last-used library.
        if self._divert_sections:
            section_index = 0
            if self._divert_last_library_key:
                for i, section in enumerate(self._divert_sections):
                    if section['key'] == self._divert_last_library_key:
                        section_index = i
                        break
            self._select_divert_section(section_index)
            self._set_sidebar_selection(section_index + 1)
        if focus:
            try:
                self.setFocus(self.getControl(DIVERT_SIDEBAR_ID))
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
        connector = self._get_connector_client(prompt_if_missing=True)
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

        if self._divert_sections:
            self._select_divert_section(0)

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

    def _divert_section_page(self, section, offset, limit):
        key = local_cache.page_cache_key('divert', section['key'], offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, DIVERT_CACHE_TTL_SECONDS,
            lambda: self._divert_section_page_uncached(section, offset, limit))

    def _divert_section_page_uncached(self, section, offset, limit):
        if self._connector_client:
            raw = self._connector_client.section_items(
                section['key'], sort='addedAt:desc', limit=limit, offset=offset)
            items = divert_source.parse_metadata_list(raw, self._connector_client.image_url)
            return items, divert_source.parse_total_size(raw)
        return self._plex_client.section_items_with_total(
            section['key'], sort='addedAt:desc', limit=limit, offset=offset)

    def _select_divert_section(self, index):
        if index >= len(self._divert_sections):
            return
        self._divert_active_section = index
        section = self._divert_sections[index]
        self._divert_last_library_key = section['key']
        self.addon.setSetting('divert.last_library', section['key'])

        self._divert_paged = paged_list.PagedList(
            lambda offset, limit: self._divert_section_page(section, offset, limit))
        error = None
        try:
            self._divert_paged.load_initial()
        except Exception as e:
            xbmc.log('Akasha Aura: section items load failed: {}'.format(e), xbmc.LOGERROR)
            error = e
        self._divert_items = self._divert_paged.items

        self._render_divert_status(section, error)

        try:
            panel = self.getControl(DIVERT_PANEL_ID)
            panel.reset()
            for item in self._divert_items:
                panel.addItem(_build_divert_list_item(item))
        except Exception as e:
            xbmc.log('Akasha Aura: panel render error: {}'.format(e), xbmc.LOGERROR)

    def _render_divert_status(self, section, error=None):
        try:
            status = self.getControl(DIVERT_STATUS_ID)
            if error:
                status.setLabel('{} — erreur de chargement'.format(section['title']))
            else:
                count = self._divert_paged.total if self._divert_paged.total is not None \
                    else len(self._divert_items)
                status.setLabel('{} — {} element(s)'.format(section['title'], count))
        except RuntimeError:
            pass

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
            panel.addItems([_build_divert_list_item(item) for item in new_items])
        except Exception as e:
            xbmc.log('Akasha Aura: Divertissement append render error: {}'.format(e),
                     xbmc.LOGERROR)
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
        self.addon.setSetting('tab.default', str(index))

        if index == TAB_DIVERTISSEMENT:
            self._select_divert_subtab(self._divert_subtab, focus=False)
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

    def _update_bar_focused(self):
        """Update the top-bar focused property used by the retract animation."""
        focused = self.getFocusId()
        is_bar_focused = focused in BAR_CONTROL_IDS or focused in SETTINGS_BUTTON_IDS
        self.setProperty('AuraBarFocused', 'true' if is_bar_focused else 'false')

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        focused = self.getFocusId()
        if aid == ACTION_MOVE_LEFT and focused in TAB_BUTTON_IDS:
            self._show_tab(self.active_tab - 1)
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_RIGHT and focused in TAB_BUTTON_IDS:
            self._show_tab(self.active_tab + 1)
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_DOWN and focused in TAB_BUTTON_IDS:
            self._focus_first_subtab()
            self._update_bar_focused()
            return
        if aid == ACTION_MOVE_UP and focused in (DIVERT_SUBTAB_IDS + JEUX_SUBTAB_IDS + APP_SUBTAB_IDS):
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            self._update_bar_focused()
            return
        super().onAction(action)
        if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT) and self.getFocusId() == DIVERT_PANEL_ID:
            self._maybe_load_more_divert()
        self._update_bar_focused()

    def _focus_first_subtab(self):
        """Move focus from the main tab to the first sub-tab of the active tab."""
        if self.active_tab == TAB_DIVERTISSEMENT:
            self.setFocus(self.getControl(DIVERT_SUBTAB_IDS[self._divert_subtab]))
        elif self.active_tab == TAB_JEUX:
            self.setFocus(self.getControl(JEUX_SUBTAB_IDS[self._jeux_active_subtab]))
        elif self.active_tab == TAB_APP:
            self.setFocus(self.getControl(APP_SUBTAB_IDS[self._app_subtab]))

    def onClick(self, controlID):
        if controlID in TAB_BUTTON_IDS:
            self._show_tab(TAB_BUTTON_IDS.index(controlID))
        elif controlID in DIVERT_SUBTAB_IDS:
            self._select_divert_subtab(DIVERT_SUBTAB_IDS.index(controlID))
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
        elif controlID == DIVERT_PANEL_ID:
            self._on_divert_item_selected()
        elif controlID == 2100:
            xbmc.executebuiltin('RunAddon(script.akasha.settings)')
        elif controlID == 2101:
            xbmc.executebuiltin('ActivateWindow(Settings)')

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
            self._select_divert_subtab(DIVERT_SUBTAB_RECOMMANDE)
            return
        more_index = len(self._divert_sections) + 1
        if pos == more_index:
            self._manage_libraries()
            return
        section_index = pos - 1
        if 0 <= section_index < len(self._divert_sections):
            self._select_divert_section(section_index)

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
        self._select_divert_subtab(DIVERT_SUBTAB_BIBLIOTHEQUES)

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
            show_window = self._get_sub_window(
                'show', aura_show.AuraShowWindow, 'AuraShow.xml')
            show_window.client = self._plex_client
            show_window.show_title = item['title']
            show_window.show_rating_key = item['rating_key']
            show_window.doModal()
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
            _HomePressAppSwitcher(self).show()

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


class _HomePressAppSwitcher:
    """Minimal app switcher invoked by a double Home press inside Aura.

    Shows a native Kodi select dialog listing pinned apps and a few
    system/utility options. A skinned, full WindowXML-based switcher can
    replace this in a later milestone without changing the press-detection
    plumbing.
    """

    def __init__(self, aura_window):
        self._window = aura_window

    def show(self):
        try:
            panel = self._window.getControl(DIVERT_PANEL_ID)
            last_item = panel.getSelectedItem()
            last_title = last_item.getLabel() if last_item else ''
        except RuntimeError:
            last_title = ''

        items = []
        actions = []
        for app in self._window._pinned_apps:
            items.append(app['name'])
            actions.append(('runaddon', app['addonid']))
        items.append('Parametres Akasha')
        actions.append(('exec', 'RunAddon(script.akasha.settings)'))
        items.append('Guide Akasha')
        actions.append(('exec', 'RunScript(script.akasha.guide)'))
        items.append('Mode Ambiant')
        actions.append(('exec', 'RunScript(script.akasha.ambient)'))

        dialog = xbmcgui.Dialog()
        idx = dialog.select('Applications', items)
        if idx < 0:
            return
        kind, value = actions[idx]
        if kind == 'runaddon':
            xbmc.executebuiltin('RunAddon({})'.format(value))
        else:
            xbmc.executebuiltin(value)

