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
import aura_library
import config
import games_shortcuts
import plex_client

TAB_BUTTON_IDS = (2001, 2002, 2003)

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

ROW_IDS = ((3010, 3030), (3011, 3031), (3012, 3032))
ROW_LIST_IDS = tuple(list_id for _, list_id in ROW_IDS)


GAME_BUTTON_IDS = (2010, 2011, 2012)
APP_TILE_IDS = (2030, 2031, 2032, 2033)


class AuraWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        addon = xbmcaddon.Addon('script.akasha.aura')
        self.active_tab = config.default_tab_index(addon.getSetting('tab.default'))
        self.addon = addon
        self.addon_path = addon.getAddonInfo('path')
        self._rows = []
        self._games = games_shortcuts.load_shortcuts(self.addon_path)
        self._pinned_apps = []

    def onInit(self):
        try:
            self._show_tab(self.active_tab)
            self._load_plex_rows()
            self._load_games()
            self._load_pinned_apps()
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
        except Exception as e:
            xbmc.log('Akasha Aura: init error: {}'.format(e), xbmc.LOGERROR)

    def _load_plex_rows(self):
        server_url = self.addon.getSetting('plex.server_url')
        token = self.addon.getSetting('plex.token')
        if not config.is_plex_configured(server_url, token):
            xbmc.log('Akasha Aura: Plex not configured, skipping rows', xbmc.LOGINFO)
            return

        try:
            client = plex_client.PlexClient(server_url, token, timeout=15)
            self._rows = client.entertainment_rows()
            self._render_divertissement_rows()
        except Exception as e:
            xbmc.log('Akasha Aura: Plex row load failed: {}'.format(e), xbmc.LOGERROR)

    def _load_games(self):
        for i, control_id in enumerate(GAME_BUTTON_IDS):
            try:
                btn = self.getControl(control_id)
            except RuntimeError:
                continue
            if i < len(self._games):
                game = self._games[i]
                btn.setLabel(game['label'])
            else:
                btn.setLabel('')

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

    def _render_divertissement_rows(self):
        for i, (title_id, list_id) in enumerate(ROW_IDS):
            try:
                title_ctl = self.getControl(title_id)
                list_ctl = self.getControl(list_id)
            except RuntimeError:
                continue

            if i < len(self._rows):
                row = self._rows[i]
                title_ctl.setLabel(row['label'])
                list_ctl.reset()
                for item in row['items'][:20]:
                    li = xbmcgui.ListItem(item['title'])
                    if item.get('thumb_url'):
                        li.setArt({'thumb': item['thumb_url']})
                    list_ctl.addItem(li)
            else:
                title_ctl.setLabel('')
                list_ctl.reset()

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
        elif controlID == 3100:
            library = aura_library.AuraLibraryWindow(
                'AuraLibrary.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
            library.doModal()
            del library
        elif controlID == 3200:
            xbmc.executebuiltin('ActivateWindow(Settings)')
        elif controlID in GAME_BUTTON_IDS:
            idx = GAME_BUTTON_IDS.index(controlID)
            if idx < len(self._games):
                action = self._games[idx]['action']
                if action:
                    xbmc.executebuiltin(action)
        elif controlID == 2040:
            app_window = aura_app.AuraAppWindow(
                'AuraApp.xml', self.addon_path, 'Default', '1080i')
            app_window.doModal()
            del app_window
            self._load_pinned_apps()
        elif controlID in APP_TILE_IDS:
            idx = APP_TILE_IDS.index(controlID)
            if idx < len(self._pinned_apps):
                xbmc.executebuiltin('RunAddon({})'.format(self._pinned_apps[idx]['addonid']))
        elif controlID in ROW_LIST_IDS:
            self._on_row_item_selected(controlID)

    def _on_row_item_selected(self, controlID):
        row_index = ROW_LIST_IDS.index(controlID)
        if row_index >= len(self._rows):
            return
        try:
            pos = self.getControl(controlID).getSelectedPosition()
        except RuntimeError:
            return
        items = self._rows[row_index]['items']
        if 0 <= pos < len(items):
            # Playback delegation is not decided yet (see docs/aura/decisions.md);
            # for now just surface the title so selection feels responsive.
            xbmcgui.Dialog().notification(
                'Akasha Aura', items[pos]['title'], xbmcgui.NOTIFICATION_INFO, 2000)
