"""Akasha Aura — App tab: full addon inventory dialog.

Milestone 5 (see docs/aura/roadmap.md): a WindowXMLDialog listing installed
"app-like" addons (scripts, plugins), with pin/unpin, launch and uninstall
actions. Uninstall is delegated to the native AddonInformation window
(see docs/aura/decisions.md — no public JSON-RPC uninstall method exists).
"""
import json

import xbmc
import xbmcaddon
import xbmcgui

import addons_inventory
import aura_store

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

PINNED_SETTING_ID = 'app.pinned'


class AuraAppWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self.addons = []
        self.pinned_ids = []

    def onInit(self):
        try:
            self._reload()
        except Exception as e:
            xbmc.log('Akasha Aura App: init error: {}'.format(e), xbmc.LOGERROR)

    def _reload(self):
        self.pinned_ids = addons_inventory.parse_pinned(
            self.addon.getSetting(PINNED_SETTING_ID))
        request = addons_inventory.build_get_addons_request()
        raw_response = xbmc.executeJSONRPC(json.dumps(request))
        all_addons = addons_inventory.parse_get_addons_response(raw_response)
        self.addons = addons_inventory.sort_addons(all_addons, self.pinned_ids)
        self._render()

    def _render(self):
        try:
            status = self.getControl(5020)
            status.setLabel('{} application(s) installee(s)'.format(len(self.addons)))
        except RuntimeError:
            pass

        try:
            lst = self.getControl(5010)
            lst.reset()
            for addon in self.addons:
                marker = '* ' if addon['addonid'] in self.pinned_ids else '  '
                label = '{}{} (v{})'.format(marker, addon['name'], addon['version'])
                li = xbmcgui.ListItem(label)
                lst.addItem(li)
            if self.addons:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura App: render error: {}'.format(e), xbmc.LOGERROR)

    def _selected_addon(self):
        try:
            pos = self.getControl(5010).getSelectedPosition()
        except RuntimeError:
            return None
        if 0 <= pos < len(self.addons):
            return self.addons[pos]
        return None

    def onClick(self, controlID):
        if controlID == 5001:
            addon = self._selected_addon()
            if addon:
                xbmc.executebuiltin('RunAddon({})'.format(addon['addonid']))

        elif controlID == 5002:
            addon = self._selected_addon()
            if addon:
                self.pinned_ids = addons_inventory.toggle_pinned(self.pinned_ids, addon['addonid'])
                self.addon.setSetting(PINNED_SETTING_ID, addons_inventory.serialize_pinned(self.pinned_ids))
                self.addons = addons_inventory.sort_addons(self.addons, self.pinned_ids)
                self._render()

        elif controlID == 5003:
            addon = self._selected_addon()
            if addon:
                xbmc.executebuiltin(
                    'ActivateWindow(AddonInformation,{},return)'.format(addon['addonid']))

        elif controlID == 5010:
            addon = self._selected_addon()
            if addon:
                xbmc.log('Akasha Aura App: selected {}'.format(addon['name']), xbmc.LOGINFO)

        elif controlID == 5004:
            store = aura_store.AuraStoreWindow(
                'AuraStore.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
            store.doModal()
            del store
            self._reload()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)
