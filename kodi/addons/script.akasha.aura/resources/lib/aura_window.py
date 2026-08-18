"""Akasha Aura — main WindowXML orchestration.

Milestone 1 (socle, see docs/aura/roadmap.md): navigable 3-tab shell with
placeholder content. Milestone 2 adds Plex entertainment rows via
plex_client.py. Later milestones fill the Games and App tabs
(addons_inventory.py, store_manifest.py) without changing this navigation
skeleton.
"""
import xbmc
import xbmcaddon
import xbmcgui

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

ROW_LABEL_PAIRS = ((3010, 3020), (3011, 3021), (3012, 3022), (3013, 3023))


GAME_BUTTON_IDS = (2010, 2011, 2012)


class AuraWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        addon = xbmcaddon.Addon('script.akasha.aura')
        self.active_tab = config.default_tab_index(addon.getSetting('tab.default'))
        self.addon = addon
        self.addon_path = addon.getAddonInfo('path')
        self._rows = []
        self._games = games_shortcuts.load_shortcuts(self.addon_path)

    def onInit(self):
        try:
            self._show_tab(self.active_tab)
            self._load_plex_rows()
            self._load_games()
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

    def _render_divertissement_rows(self):
        for i, (title_id, content_id) in enumerate(ROW_LABEL_PAIRS):
            try:
                title_ctl = self.getControl(title_id)
                content_ctl = self.getControl(content_id)
            except RuntimeError:
                continue

            if i < len(self._rows):
                row = self._rows[i]
                title_ctl.setLabel(row['label'])
                titles = ' / '.join(item['title'] for item in row['items'][:8])
                content_ctl.setLabel(titles)
            else:
                title_ctl.setLabel('')
                content_ctl.setLabel('')

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
