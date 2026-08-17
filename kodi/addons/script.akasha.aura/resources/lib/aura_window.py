"""Akasha Aura — main WindowXML orchestration.

Milestone 1 (socle, see docs/aura/roadmap.md): navigable 3-tab shell with
placeholder content. Later milestones fill each tab with real data
(Plex rows via plex_client.py, games tiles, installed-addons inventory via
addons_inventory.py, Akasha Store via store_manifest.py) without changing
this navigation skeleton.
"""
import xbmc
import xbmcaddon
import xbmcgui

import config

TAB_BUTTON_IDS = (2001, 2002, 2003)

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


class AuraWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        addon = xbmcaddon.Addon('script.akasha.aura')
        self.active_tab = config.default_tab_index(addon.getSetting('tab.default'))

    def onInit(self):
        try:
            self._show_tab(self.active_tab)
            self.setFocus(self.getControl(TAB_BUTTON_IDS[self.active_tab]))
        except Exception as e:
            xbmc.log('Akasha Aura: init error: {}'.format(e), xbmc.LOGERROR)

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
