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
import plex_client
import steam_client
import sunshine_client

TAB_BUTTON_IDS = (2001, 2002, 2003)

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

DIVERT_SUBTAB_IDS = (3210, 3211, 3212, 3213, 3214, 3215, 3216, 3217, 3218)
DIVERT_STATUS_ID = 3220
DIVERT_PANEL_ID = 3230
DIVERT_ITEMS_LIMIT = 100

GAME_BUTTON_IDS = (2010, 2011, 2012)
APP_TILE_IDS = (2030, 2031, 2032, 2033)

JEUX_SUBTAB_IDS = (2050, 2051, 2052)
JEUX_STATUS_ID = 2055
JEUX_PANEL_ID = 2060
JEUX_SUBTAB_STEAMLINK = 0
JEUX_SUBTAB_MOONLIGHT = 1
JEUX_SUBTAB_OTHERS = 2
# Shortcuts launched from their own dedicated sub-tab, excluded from "Autres".
JEUX_DEDICATED_ACTIONS = ('steamlink', 'moonlight')


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
        self._divert_active_section = 0
        self._divert_items = []
        self._games = games_shortcuts.load_shortcuts(self.addon_path)
        self._other_games = [
            g for g in self._games
            if not any(a in (g.get('action') or '').lower() for a in JEUX_DEDICATED_ACTIONS)
        ]
        self._jeux_active_subtab = JEUX_SUBTAB_STEAMLINK
        self._jeux_items = []
        self._pinned_apps = []

    def onInit(self):
        try:
            self._show_tab(self.active_tab)
            self._load_divertissement()
            self._select_jeux_subtab(JEUX_SUBTAB_STEAMLINK)
            self._load_pinned_apps()
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
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

        for i, control_id in enumerate(DIVERT_SUBTAB_IDS):
            try:
                btn = self.getControl(control_id)
            except RuntimeError:
                continue
            if i < len(self._divert_sections):
                btn.setLabel(self._divert_sections[i]['title'])
            else:
                btn.setLabel('')

        if self._divert_sections:
            self._select_divert_section(0)

    def _select_divert_section(self, index):
        if index >= len(self._divert_sections):
            return
        self._divert_active_section = index
        section = self._divert_sections[index]

        try:
            if self._connector_client:
                raw = self._connector_client.section_items(
                    section['key'], sort='addedAt:desc', limit=DIVERT_ITEMS_LIMIT)
                self._divert_items = divert_source.parse_metadata_list(
                    raw, self._connector_client.image_url)
            else:
                self._divert_items = self._plex_client.section_items(
                    section['key'], sort='addedAt:desc', limit=DIVERT_ITEMS_LIMIT)
        except Exception as e:
            xbmc.log('Akasha Aura: section items load failed: {}'.format(e), xbmc.LOGERROR)
            self._divert_items = []

        try:
            status = self.getControl(DIVERT_STATUS_ID)
            status.setLabel('{} — {} element(s)'.format(section['title'], len(self._divert_items)))
        except RuntimeError:
            pass

        try:
            panel = self.getControl(DIVERT_PANEL_ID)
            panel.reset()
            for item in self._divert_items:
                li = xbmcgui.ListItem(item['title'], divert_source.item_subtitle(item))
                if item.get('thumb_url'):
                    li.setArt({'thumb': item['thumb_url']})
                panel.addItem(li)
        except Exception as e:
            xbmc.log('Akasha Aura: panel render error: {}'.format(e), xbmc.LOGERROR)

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

    def _show_tab(self, index):
        index = index % len(config.TABS)
        self.active_tab = index
        self.setProperty('AuraActiveTab', str(index))

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        if aid == ACTION_MOVE_LEFT and self.getFocusId() in TAB_BUTTON_IDS:
            self._show_tab(self.active_tab - 1)
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            return
        if aid == ACTION_MOVE_RIGHT and self.getFocusId() in TAB_BUTTON_IDS:
            self._show_tab(self.active_tab + 1)
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
            return
        super().onAction(action)

    def onClick(self, controlID):
        if controlID in TAB_BUTTON_IDS:
            self._show_tab(TAB_BUTTON_IDS.index(controlID))
        elif controlID == 3050:
            recommendations = aura_recommendations.AuraRecommendationsWindow(
                'AuraRecommendations.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
            recommendations.doModal()
            del recommendations
        elif controlID == 3100:
            library = aura_library.AuraLibraryWindow(
                'AuraLibrary.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
            library.doModal()
            del library
        elif controlID == 3060:
            genres = aura_genres.AuraGenresWindow(
                'AuraGenres.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
            genres.doModal()
            del genres
        elif controlID == 3200:
            xbmc.executebuiltin('ActivateWindow(Settings)')
        elif controlID in GAME_BUTTON_IDS:
            idx = GAME_BUTTON_IDS.index(controlID)
            if idx < len(self._other_games):
                action = self._other_games[idx]['action']
                if action:
                    xbmc.executebuiltin(action)
        elif controlID in JEUX_SUBTAB_IDS:
            self._select_jeux_subtab(JEUX_SUBTAB_IDS.index(controlID))
        elif controlID == JEUX_PANEL_ID:
            self._on_jeux_item_selected()
        elif controlID == 2041:
            app_window = aura_app.AuraAppWindow(
                'AuraApp.xml', self.addon_path, 'Default', '1080i')
            app_window.doModal()
            del app_window
            self._load_pinned_apps()
        elif controlID == 2042:
            store_window = aura_store.AuraStoreWindow(
                'AuraStore.xml', self.addon_path, 'Default', '1080i')
            store_window.doModal()
            del store_window
            self._load_pinned_apps()
        elif controlID in APP_TILE_IDS:
            idx = APP_TILE_IDS.index(controlID)
            if idx < len(self._pinned_apps):
                xbmc.executebuiltin('RunAddon({})'.format(self._pinned_apps[idx]['addonid']))
        elif controlID in DIVERT_SUBTAB_IDS:
            idx = DIVERT_SUBTAB_IDS.index(controlID)
            if idx < len(self._divert_sections):
                self._select_divert_section(idx)
        elif controlID == DIVERT_PANEL_ID:
            self._on_divert_item_selected()

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
            show_window = aura_show.AuraShowWindow(
                'AuraShow.xml', self.addon_path, 'Default', '1080i')
            show_window.client = self._plex_client
            show_window.show_title = item['title']
            show_window.show_rating_key = item['rating_key']
            show_window.doModal()
            del show_window
        else:
            # Playback delegation is not decided yet (see docs/aura/decisions.md);
            # for now just surface the title so selection feels responsive.
            xbmcgui.Dialog().notification(
                'Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)
