"""Akasha Aura — App tab: full addon inventory dialog.

Milestone 5 (see docs/aura/roadmap.md): a WindowXMLDialog listing installed
"app-like" addons (scripts, plugins), with pin/unpin, launch and uninstall
actions. Uninstall uses aura_store.uninstall_kodi_addon() — the native
AddonInformation window segfaults on this Kodi build, and no public
JSON-RPC uninstall method exists either.
"""
import json
import subprocess

import xbmc
import xbmcaddon
import xbmcgui
import gui_guard
import i18n
import aura_menu

import addons_inventory
import aura_store
import paged_list
import store_external
import store_registry

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4

PINNED_SETTING_ID = 'app.pinned'
APP_PAGE_SIZE = 30


class AuraAppWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self.addons = []
        self._all_addons = []
        self.pinned_ids = []
        self._paged = None
        # Reused across opens rather than a fresh instance each time -- see
        # the note in aura_window.py's AuraWindow.__init__ about why.
        self._store_window = None
        # ('run'|'store', payload): native actions are deferred until
        # doModal() returns -- see run_pending_native().
        self._pending = None

    def _fetch_page(self, offset, limit):
        """Local pagination: all addons are in memory; slice a page."""
        page = self._all_addons[offset:offset + limit]
        return page, len(self._all_addons)

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
        # Plan f4e069bb Phase 4 asks for a "Mes Applications" view showing
        # *only* Store-installed apps still present in the live catalogue
        # (tiles, logo, title on hover) -- deliberately NOT implemented as
        # a hard replacement of this tab's existing "every installed addon"
        # inventory (Milestone 5's own, already-shipped scope): hiding
        # every non-Store-installed addon here would be a real UX
        # regression for a feature already in daily use, and isn't a call
        # to make unilaterally without live-device verification. Each
        # addon installed via the Store is flagged instead (self.store_ids)
        # so the skin can badge it, and the strict filtered/tiled view
        # described by the plan is left as a follow-up needing an explicit
        # product decision -- see docs/aura/decisions.md.
        #
        # Web apps installed via the Store (`external-app`) are added as
        # synthetic entries alongside the real addon inventory: the user
        # explicitly asked to keep the complete inventory, so we never filter
        # it to Store-only apps. External apps have no real Kodi addon id, so
        # they are represented by a synthetic `external:<store_app_id>` id.
        try:
            registry = store_registry.load_registry()
            self.store_ids = store_registry.addon_id_to_store_id(registry)
            external = store_external.build_synthetic_addons(registry)
            self._all_addons = addons_inventory.sort_addons(
                all_addons + external, self.pinned_ids)
            for ext in external:
                self.store_ids[ext['addonid']] = ext['store_id']
        except Exception as e:
            xbmc.log('Akasha Aura App: store registry load failed: {}'.format(e),
                     xbmc.LOGWARNING)
            self.store_ids = {}
            self._all_addons = addons_inventory.sort_addons(
                all_addons, self.pinned_ids)

        # Optional strict view: 'apps.store_only' limits the tab to
        # Store-installed apps only (opt-in; the full inventory stays the
        # default). An empty registry keeps the full list -- hiding every
        # app on a transient registry failure would be worse than showing
        # the unfiltered inventory.
        if self.addon.getSetting('apps.store_only') == 'true' \
                and self.store_ids:
            self._all_addons = [a for a in self._all_addons
                                if a['addonid'] in self.store_ids]

        self._paged = paged_list.PagedList(
            self._fetch_page, page_size=APP_PAGE_SIZE)
        self._paged.load_initial()
        self.addons = self._paged.items
        self._render()

    def _render(self):
        try:
            status = self.getControl(5020)
            total = self._paged.total if self._paged else len(self.addons)
            status.setLabel(i18n.tr(33300).format(total))
        except RuntimeError:
            pass

        try:
            lst = self.getControl(5010)
            lst.reset()
            for addon in self.addons:
                lst.addItem(self._make_list_item(addon))
            if self.addons:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura App: render error: {}'.format(e), xbmc.LOGERROR)

    def _make_list_item(self, addon):
        """Card item for the installed-apps grid: clean name, version as
        the sub-line, provenance/state exposed as skin properties so the
        layout can badge pinned/Store/web apps without parsing text."""
        if addon.get('is_external'):
            source = i18n.tr(33322)
        elif addon['addonid'] in self.store_ids:
            source = i18n.tr(33013)
        else:
            source = ''
        li = xbmcgui.ListItem(addon['name'], 'v{}'.format(addon['version']))
        if addon.get('icon'):
            li.setArt({'icon': addon['icon'], 'thumb': addon['icon']})
        li.setProperty(
            'pinned', '1' if addon['addonid'] in self.pinned_ids else '0')
        li.setProperty(
            'fromstore', '1' if addon['addonid'] in self.store_ids else '0')
        li.setProperty(
            'is_external', '1' if addon.get('is_external') else '0')
        meta = 'v{}'.format(addon['version'])
        if source:
            meta = '{} • {}'.format(meta, source)
        li.setProperty('app_meta', meta)
        li.setProperty('app_desc', addon.get('summary', ''))
        return li

    def _selected_addon(self):
        try:
            pos = gui_guard.selpos(self, 5010)
        except RuntimeError:
            return None
        if 0 <= pos < len(self.addons):
            return self.addons[pos]
        return None

    def _launch_external_app(self, addon):
        source_url = addon.get('source_url', '')
        deep_link = addon.get('deep_link') or ''
        ok, err = store_external.validate_install(
            source_url, deep_link or None)
        if not ok:
            xbmc.log('Akasha Aura App: cannot launch {}: {}'
                     .format(addon.get('store_id', ''), err), xbmc.LOGERROR)
            return

        args = store_external.launch_command_args(
            source_url, addon['name'], deep_link=deep_link or None,
            app_id=addon.get('store_id'))
        try:
            # Detach from Kodi's cgroup: launch.sh stops kodi.service and
            # would otherwise kill this Python process with it.
            subprocess.Popen(args)
            xbmc.sleep(1000)
        except Exception as e:
            xbmc.log('Akasha Aura App: failed to launch {}: {}'
                     .format(addon.get('store_id', ''), e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID == 5001:
            addon = self._selected_addon()
            if addon:
                if addon.get('is_external'):
                    self._launch_external_app(addon)
                else:
                    # RunAddon() needs the addon's own windows/dialogs on
                    # top; they cannot open above this modal dialog (same
                    # constraint as InstallAddon() in aura_store.py), so
                    # defer it past doModal().
                    self._pending = ('run', addon['addonid'])
                    self.close()

        elif controlID == 5002:
            addon = self._selected_addon()
            if addon:
                self.pinned_ids = addons_inventory.toggle_pinned(self.pinned_ids, addon['addonid'])
                self.addon.setSetting(PINNED_SETTING_ID, addons_inventory.serialize_pinned(self.pinned_ids))
                self._reload()

        elif controlID == 5003:
            addon = self._selected_addon()
            if addon:
                if addon.get('is_external'):
                    if aura_menu.confirm(
                            self, i18n.tr(33319),
                            i18n.tr(33305).format(addon['name'])):
                        store_registry.record_uninstall(addon['store_id'])
                        self._reload()
                else:
                    # No AddonInformation route: it segfaults on this Kodi
                    # build -- see aura_store.uninstall_kodi_addon().
                    if aura_store.uninstall_kodi_addon(addon['addonid']):
                        store_app_id = self.store_ids.get(addon['addonid'])
                        if store_app_id:
                            # Optimistic bookkeeping, same caveat as
                            # aura_store.py's install/uninstall notes.
                            store_registry.record_uninstall(store_app_id)
                        xbmcgui.Dialog().notification(
                            i18n.tr(33319), i18n.tr(33308).format(addon['name']),
                            xbmcgui.NOTIFICATION_INFO, 3000)
                    else:
                        xbmcgui.Dialog().notification(
                            i18n.tr(33319), i18n.tr(33310).format(addon['name']),
                            xbmcgui.NOTIFICATION_ERROR, 4000)
                    self._reload()

        elif controlID == 5010:
            addon = self._selected_addon()
            if addon:
                xbmc.log('Akasha Aura App: selected {}'.format(addon['name']), xbmc.LOGINFO)

        elif controlID == 5004:
            if self._store_window is None:
                self._store_window = aura_store.AuraStoreWindow(
                    'AuraStore.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
            self._store_window.doModal()
            if self._store_window._pending:
                # The store was opened from this dialog: it cannot run its
                # deferred native action here either, so forward it up one
                # level -- the main window runs it after this doModal()
                # returns too.
                self._pending = ('store', self._store_window)
                self.close()
                return
            self._reload()

    def run_pending_native(self):
        """Run a deferred native addon action after doModal() has returned.

        RunAddon()/ActivateWindow(AddonInformation)/InstallAddon() all fail
        silently while an Aura WindowXMLDialog sits on the modal stack; the
        caller runs this once every nested dialog has been unwound.
        """
        pending, self._pending = self._pending, None
        if not pending:
            return
        verb, payload = pending
        if verb == 'run':
            xbmc.executebuiltin('RunAddon({})'.format(payload))
        elif verb == 'store':
            payload.run_pending_native()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_MOVE_UP, ACTION_MOVE_DOWN):
            try:
                pos = gui_guard.selpos(self, 5010)
            except RuntimeError:
                pos = 0
            if self._paged:
                new_items = self._paged.maybe_load_more(pos)
                if new_items:
                    self.addons = self._paged.items
                    self._append_items(new_items)
        super().onAction(action)

    def _append_items(self, new_items):
        """Append newly paged items to the panel without a full reset."""
        try:
            lst = self.getControl(5010)
            for addon in new_items:
                lst.addItem(self._make_list_item(addon))
        except Exception as e:
            xbmc.log('Akasha Aura App: append render error: {}'.format(e), xbmc.LOGERROR)
