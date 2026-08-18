"""Akasha Aura — Akasha Store: install curated addons from Aura.

Milestone 6 (see docs/aura/roadmap.md): a WindowXMLDialog listing the
curated addon manifest (store_manifest.py) with an install status, and an
"Installer" action delegated to Kodi's builtin InstallAddon (which installs
from whichever repository already provides the addon, and shows Kodi's own
native progress/confirmation UI) — no direct addon file manipulation.
"""
import json

import xbmc
import xbmcaddon
import xbmcgui

import store_manifest

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


class AuraStoreWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self.addon_path = self.addon.getAddonInfo('path')
        self.entries = []

    def onInit(self):
        try:
            self._reload()
        except Exception as e:
            xbmc.log('Akasha Aura Store: init error: {}'.format(e), xbmc.LOGERROR)

    def _fetch_installed_ids(self):
        request = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddons',
            'params': {'installed': True},
        }
        try:
            raw_response = xbmc.executeJSONRPC(json.dumps(request))
            data = json.loads(raw_response)
            addons = data.get('result', {}).get('addons', [])
            return {a.get('addonid') for a in addons}
        except Exception as e:
            xbmc.log('Akasha Aura Store: installed ids lookup failed: {}'.format(e), xbmc.LOGERROR)
            return set()

    def _reload(self):
        manifest_entries = store_manifest.load_manifest(self.addon_path)
        installed_ids = self._fetch_installed_ids()
        self.entries = store_manifest.with_install_status(manifest_entries, installed_ids)
        self._render()

    def _render(self):
        try:
            status = self.getControl(6020)
            status.setLabel('{} application(s) proposee(s)'.format(len(self.entries)))
        except RuntimeError:
            pass

        try:
            lst = self.getControl(6010)
            lst.reset()
            for entry in self.entries:
                state = 'Installe' if entry['installed'] else 'Non installe'
                li = xbmcgui.ListItem(entry['name'], entry['summary'])
                li.setProperty('installed', '1' if entry['installed'] else '0')
                li.setLabel2('{} — {}'.format(entry['summary'], state))
                lst.addItem(li)
            if self.entries:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura Store: render error: {}'.format(e), xbmc.LOGERROR)

    def _selected_entry(self):
        try:
            pos = self.getControl(6010).getSelectedPosition()
        except RuntimeError:
            return None
        if 0 <= pos < len(self.entries):
            return self.entries[pos]
        return None

    def _install(self, entry):
        xbmc.log('Akasha Aura Store: install requested for {}'.format(entry['addonid']), xbmc.LOGINFO)
        if entry['installed']:
            xbmcgui.Dialog().notification(
                'Akasha Store', '{} est deja installe'.format(entry['name']),
                xbmcgui.NOTIFICATION_INFO, 3000)
            return

        xbmc.executebuiltin('InstallAddon({})'.format(entry['addonid']))
        xbmcgui.Dialog().notification(
            'Akasha Store',
            'Installation de {} lancee'.format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)

    def onClick(self, controlID):
        xbmc.log('Akasha Aura Store: onClick {}'.format(controlID), xbmc.LOGINFO)
        if controlID in (6001, 6010):
            entry = self._selected_entry()
            xbmc.log('Akasha Aura Store: selected entry = {}'.format(entry), xbmc.LOGINFO)
            if entry:
                self._install(entry)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)
