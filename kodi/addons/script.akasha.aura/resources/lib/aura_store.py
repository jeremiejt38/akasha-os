"""Akasha Aura — Akasha OS Store: browse and install apps from the real
akasha-os-store catalogue (plan f4e069bb).

Replaces the old bundled-curated-manifest version (store_manifest.py, still
kept for its unit tests/back-compat but no longer used here): entries now
come from the live akasha-os-store index.json (store_client.py, cached
locally with a 24h TTL + manual refresh), and a successful install is
recorded in the local registry (store_registry.py) so aura_app.py's "Mes
Applications" tab knows what to show.

Per-install-type behaviour (plan section 3, deliberately conservative --
see docs/aura/decisions.md for the full rationale):
- kodi-repo: delegated to Kodi's builtin InstallAddon(addon_id), same
  mechanism the previous curated-manifest version already used. Works
  outright for addons on Kodi's own official repo; for a third-party
  repository not yet known to this Kodi instance, InstallAddon fails with
  Kodi's own native "not found" notification -- a safe, non-destructive
  failure mode, not a crash. Actually adding an arbitrary unknown
  third-party repository from a manifest URL is deliberately NOT automated
  here: Kodi intentionally keeps that behind the "Unknown sources" toggle
  and its own file-manager install-from-zip flow as a security boundary,
  and scripting around that boundary unsupervised is out of scope for a
  first version.
- zip-url: downloaded and sha256-verified, then handed to InstallAddon
  the same way (same caveat as above for addons requiring "Unknown
  sources"). No current manifest actually uses this type.
- script / external-app: informative only in V1, per the plan's own
  wording -- no code from a manifest field is ever executed automatically.
"""
import datetime
import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import gui_guard
import aura_menu
import i18n

import paged_list
import store_client
import store_external
import store_registry

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4

HEADER_LABEL_ID = 6000
STORE_PAGE_SIZE = 30
INSTALL_BUTTON_ID = 6001
STATUS_LABEL_ID = 6020
LIST_ID = 6010
BACK_BUTTON_ID = 6030

# Overview dialog (AuraStoreDetail.xml)
DETAIL_PRIMARY_ID = 7001
DETAIL_SECONDARY_ID = 7002
DETAIL_BACK_ID = 7003

# Category chip strip: 6050 = "All", 6051..6055 = one chip per known
# catalogue category. Chips whose category has no entry are hidden by the
# skin (StoreCat_<slug> window property).
CHIP_IDS = (6050, 6051, 6052, 6053, 6054, 6055)
# (catalogue slug, label msgid, window-property suffix) in strip order.
KNOWN_CATEGORIES = (
    ('svod', 33329, 'svod'),
    ('replay', 33330, 'replay'),
    ('live-tv', 33331, 'livetv'),
    ('sport', 33332, 'sport'),
    ('musique', 33333, 'musique'),
)
_CATEGORY_MSGIDS = {slug: msgid for slug, msgid, _ in KNOWN_CATEGORIES}


def category_label(category):
    """Localized display name for a catalogue category slug; falls back to
    the raw slug for categories the skin doesn't know yet."""
    return i18n.tr(_CATEGORY_MSGIDS.get(category, 0)) \
        if category in _CATEGORY_MSGIDS else (category or '')


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def uninstall_kodi_addon(addon_id):
    """Remove a user-installed addon without the native AddonInformation
    window.

    ActivateWindow(AddonInformation, ...) segfaults on this Kodi build
    (SIGSEGV in CGUIDialogAddonInfo::BuildDependencyList -- confirmed
    2026-11-03 for every addon, modal dialog or not), so the native
    uninstall UI is unusable on the device. We instead delete the addon's
    folder under special://home/addons/ and ask Kodi to rescan:
    UpdateLocalAddons() syncs Addons33.db and the addon drops out of
    Addons.GetAddons -- equivalent to a native uninstall, orphaned
    dependencies included (native uninstall keeps them too).
    Returns False when the addon has no userdata folder (e.g. system
    addons -- the store only ever installs under userdata anyway).
    """
    path = xbmcvfs.translatePath('special://home/addons/{}/'.format(addon_id))
    if not xbmcvfs.exists(path):
        xbmc.log('Akasha Aura Store: no local addon dir for {}'
                 .format(addon_id), xbmc.LOGWARNING)
        return False
    xbmc.log('Akasha Aura Store: removing addon dir {}'
             .format(path), xbmc.LOGINFO)
    xbmcvfs.rmdir(path, True)
    xbmc.executebuiltin('UpdateLocalAddons')
    return True


class AuraStoreDetailWindow(xbmcgui.WindowXMLDialog):
    """App-page style overview sheet shown before installing an entry.

    Mirrors the Play Store app page: icon tile, name, meta line, action
    pills and a metadata block. The caller reads `action` after doModal():
    'primary' (install / launch / uninstall per entry state), 'secondary'
    (external-app uninstall) or None (closed without action).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = None
        self._armed_at = 0.0

    def set_entry(self, entry):
        """Populate the sheet for `entry`; call before doModal()."""
        install = entry.get('install', {})
        itype = install.get('type')
        installed = entry['installed']
        cat = category_label(entry.get('category', ''))
        state = i18n.tr(33302) if installed else i18n.tr(33303)

        self.setProperty('StoreDetName', entry.get('name', ''))
        self.setProperty('StoreDetMeta', '{} • v{} • {}'.format(
            cat, entry.get('version', '-'), state))
        self.setProperty('StoreDetDesc', entry.get('description', ''))
        icon = store_external.resolve_icon_url(
            entry['id'], entry.get('icon', ''))
        self.setProperty('StoreDetIcon', icon)

        details = [
            i18n.tr(33324).format(itype or '-'),
            i18n.tr(33325).format(install.get('source_url') or '-'),
            i18n.tr(33326).format(install.get('deep_link')
                                  or entry.get('deep_link') or '-'),
            i18n.tr(33337).format(entry.get('maintainer') or '-'),
        ]
        legal = (entry.get('legal_notice') or '').strip()
        if legal:
            details.append(legal)
        self.setProperty('StoreDetDetails', '\n'.join(details))

        if not installed:
            primary = '' if itype == 'script' else i18n.tr(33144)
        elif itype == 'external-app':
            primary = i18n.tr(33021)
        else:
            primary = i18n.tr(33023)
        self.setProperty('StoreDetPrimary', primary)
        self.setProperty('StoreDetSecondary',
                         '1' if installed and itype == 'external-app' else '')
        self.action = None

    def onInit(self):
        # The Select keypress that opened this dialog can be re-dispatched
        # into it and click the focused pill instantly; swallow clicks for
        # a short arming window.
        self._armed_at = time.monotonic() + 0.4
        try:
            if self.getProperty('StoreDetPrimary'):
                self.setFocus(self.getControl(DETAIL_PRIMARY_ID))
            else:
                self.setFocus(self.getControl(DETAIL_BACK_ID))
        except RuntimeError:
            pass

    def onClick(self, controlID):
        if time.monotonic() < self._armed_at:
            return
        if controlID == DETAIL_PRIMARY_ID:
            self.action = 'primary'
        elif controlID == DETAIL_SECONDARY_ID:
            self.action = 'secondary'
        self.close()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)


def _fetch_json(url):
    """Real network fetch (stdlib only), injected into store_client so it
    stays unit-testable without a real network call."""
    req = urllib.request.Request(url, headers={'User-Agent': 'AkashaOSAura/1.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


class AuraStoreWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self.entries = []
        self._all_entries = []
        self._filtered = []
        self._paged = None
        self._category_index = 0
        # ('install'|'uninstall', entry): native kodi-repo/zip-url actions are
        # deferred until doModal() returns -- see run_pending_native().
        self._pending = None

    def _fetch_page(self, offset, limit):
        """Local pagination: filtered catalogue is in memory; slice a page."""
        page = self._filtered[offset:offset + limit]
        return page, len(self._filtered)

    def onInit(self):
        try:
            self._reload()
        except Exception as e:
            xbmc.log('Akasha Aura Store: init error: {}'.format(e), xbmc.LOGERROR)

    def _fetch_installed_kodi_addon_ids(self):
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
            xbmc.log('Akasha Aura Store: installed ids lookup failed: {}'.format(e),
                     xbmc.LOGERROR)
            return set()

    def _reload(self, force_refresh=False):
        index = store_client.get_index(_fetch_json, force_refresh=force_refresh)
        installed_kodi_ids = self._fetch_installed_kodi_addon_ids()
        registry = store_registry.load_registry()

        self._all_entries = []
        for entry in index.get('entries', []):
            install = entry.get('install', {})
            if install.get('type') in ('kodi-repo', 'zip-url'):
                installed = install.get('addon_id') in installed_kodi_ids
            else:
                installed = entry['id'] in registry
            self._all_entries.append(dict(entry, installed=installed))

        # Category strip state: which categories actually have entries, and
        # whether the active filter still exists after a refresh.
        present = {e.get('category') for e in self._all_entries}
        for slug, _, prop_suffix in KNOWN_CATEGORIES:
            self.setProperty(
                'StoreCat_{}'.format(prop_suffix),
                '1' if slug in present else '')
        if (self._category_index > 0 and
                KNOWN_CATEGORIES[self._category_index - 1][0] not in present):
            self._category_index = 0
        self.setProperty('StoreCat', str(self._category_index))

        self._apply_category()

    def _apply_category(self):
        """Filter the catalogue by the active category chip and re-render."""
        slug = (KNOWN_CATEGORIES[self._category_index - 1][0]
                if self._category_index > 0 else '')
        self._filtered = store_client.filter_entries(self._all_entries, slug)
        self._paged = paged_list.PagedList(
            self._fetch_page, page_size=STORE_PAGE_SIZE)
        self._paged.load_initial()
        self.entries = self._paged.items
        self._render()

    def _select_category(self, index):
        if index != self._category_index:
            self._category_index = index
            self.setProperty('StoreCat', str(index))
            self._apply_category()
        if self.entries:
            try:
                self.setFocus(self.getControl(LIST_ID))
            except RuntimeError:
                pass

    @staticmethod
    def _make_list_item(entry):
        cat = category_label(entry.get('category', ''))
        state = i18n.tr(33302) if entry['installed'] else i18n.tr(33303)
        li = xbmcgui.ListItem(entry['name'], cat)
        icon = store_external.resolve_icon_url(entry['id'], entry.get('icon', ''))
        if icon:
            li.setArt({'icon': icon, 'thumb': icon})
        li.setProperty('installed', '1' if entry['installed'] else '0')
        li.setProperty('store_desc', entry.get('description', ''))
        li.setProperty('store_meta', '{} • v{} • {}'.format(
            cat, entry.get('version', '-'), state))
        return li

    def _render(self):
        try:
            status = self.getControl(STATUS_LABEL_ID)
            total = self._paged.total if self._paged else len(self.entries)
            status.setLabel(i18n.tr(33301).format(total))
        except RuntimeError:
            pass

        try:
            lst = self.getControl(LIST_ID)
            lst.reset()
            for entry in self.entries:
                lst.addItem(self._make_list_item(entry))
            if self.entries:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura Store: render error: {}'.format(e), xbmc.LOGERROR)

    def _selected_entry(self):
        try:
            pos = gui_guard.selpos(self, LIST_ID)
        except RuntimeError:
            return None
        if 0 <= pos < len(self.entries):
            return self.entries[pos]
        return None

    def _install(self, entry):
        """Install/uninstall a non-external entry, invoked from the
        overview sheet's primary pill."""
        install = entry.get('install', {})
        itype = install.get('type')
        xbmc.log('Akasha Aura Store: install requested for {} (type={})'
                  .format(entry['id'], itype), xbmc.LOGINFO)

        if entry['installed']:
            if aura_menu.confirm(
                    self, 'Akasha Store',
                    i18n.tr(33306).format(entry['name'])):
                self._uninstall(entry)
            return

        if itype == 'kodi-repo':
            # InstallAddon() opens a native confirmation/progress dialog
            # that cannot appear above this modal WindowXMLDialog -- it
            # silently no-ops while the store (or even its closing
            # transition) is on the dialog stack. Defer the whole flow to
            # run_pending_native(), which the caller runs once doModal()
            # has fully returned.
            self._pending = ('install', entry)
            self.close()
            return
        elif itype == 'zip-url':
            self._install_from_zip(entry, install)
        elif itype == 'external-app':
            self._install_external(entry)
        else:
            # 'script' and unknown types are informative only (the
            # overview sheet already shows every manifest field); never
            # execute anything from a manifest field automatically.
            xbmc.log('Akasha Aura Store: no install action for type {} ({})'
                      .format(itype, entry['id']), xbmc.LOGWARNING)

        self._reload()

    def _install_from_zip(self, entry, install):
        source_url = install.get('source_url')
        expected_sha256 = (install.get('sha256') or '').lower()
        try:
            req = urllib.request.Request(
                source_url, headers={'User-Agent': 'AkashaOSAura/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
        except Exception as e:
            xbmc.log('Akasha Aura Store: zip download failed for {}: {}'
                      .format(entry['id'], e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33311).format(entry['name']),
                xbmcgui.NOTIFICATION_ERROR, 3000)
            return

        actual_sha256 = hashlib.sha256(content).hexdigest()
        if expected_sha256 and actual_sha256 != expected_sha256:
            xbmc.log('Akasha Aura Store: sha256 mismatch for {} (expected {}, got {})'
                      .format(entry['id'], expected_sha256, actual_sha256), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33313).format(entry['name']),
                xbmcgui.NOTIFICATION_ERROR, 4000)
            return

        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
                f.write(content)
                zip_path = f.name
        except OSError as e:
            xbmc.log('Akasha Aura Store: failed to write temp zip for {}: {}'
                      .format(entry['id'], e), xbmc.LOGERROR)
            return

        # Kodi deliberately keeps "install from an arbitrary local zip"
        # behind the file-manager/"Unknown sources" flow as a security
        # boundary rather than a freely scriptable JSON-RPC call -- see
        # module docstring. Best-effort InstallAddon() attempt (works if
        # the addon_id happens to already be resolvable, e.g. it was also
        # published normally elsewhere); otherwise this at least leaves a
        # verified zip on disk and a clear log entry rather than silently
        # doing nothing.
        addon_id = install.get('addon_id')
        if addon_id:
            xbmc.executebuiltin('InstallAddon({})'.format(addon_id))
        xbmc.log('Akasha Aura Store: verified zip for {} saved to {}'
                  .format(entry['id'], zip_path), xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            'Akasha Store', i18n.tr(33312).format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)
        store_registry.record_install(
            entry['id'], entry.get('version', ''), _now_iso(), addon_id=addon_id)

    def _uninstall(self, entry):
        install = entry.get('install', {})
        addon_id = install.get('addon_id')
        if install.get('type') in ('kodi-repo', 'zip-url') and addon_id:
            if uninstall_kodi_addon(addon_id):
                # Give UpdateLocalAddons() a moment to drop the addon from
                # Addons.GetAddons before refreshing the badge.
                monitor = xbmc.Monitor()
                for _ in range(10):
                    if monitor.waitForAbort(1):
                        break
                    if addon_id not in self._fetch_installed_kodi_addon_ids():
                        break
                store_registry.record_uninstall(entry['id'])
                xbmcgui.Dialog().notification(
                    'Akasha Store', i18n.tr(33308).format(entry['name']),
                    xbmcgui.NOTIFICATION_INFO, 3000)
            else:
                xbmcgui.Dialog().notification(
                    'Akasha Store', i18n.tr(33310).format(entry['name']),
                    xbmcgui.NOTIFICATION_ERROR, 4000)
        else:
            store_registry.record_uninstall(entry['id'])
        self._reload()

    def run_pending_native(self):
        """Run a deferred native kodi-repo install ('install', entry).

        Must be called by the owner after this dialog's doModal() has
        returned: InstallAddon()'s native confirmation/progress dialog
        silently no-ops while an Aura WindowXMLDialog sits on the modal
        stack (or is still unwinding). Uninstall doesn't need deferral --
        uninstall_kodi_addon() opens no native dialog.
        """
        pending, self._pending = self._pending, None
        if not pending:
            return
        verb, entry = pending
        if verb != 'install':
            return
        addon_id = entry.get('install', {}).get('addon_id')
        xbmc.executebuiltin('InstallAddon({})'.format(addon_id))
        monitor = xbmc.Monitor()
        installed = False
        for _ in range(90):
            if monitor.waitForAbort(1):
                break
            if addon_id in self._fetch_installed_kodi_addon_ids():
                installed = True
                break
        if installed:
            store_registry.record_install(
                entry['id'], entry.get('version', ''), _now_iso(), addon_id=addon_id)
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33307).format(entry['name']),
                xbmcgui.NOTIFICATION_INFO, 3000)
        else:
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33310).format(entry['name']),
                xbmcgui.NOTIFICATION_ERROR, 4000)

    def _install_external(self, entry):
        install = entry.get('install', {})
        source_url = install.get('source_url')
        deep_link = entry.get('deep_link')
        ok, err = store_external.validate_install(source_url, deep_link)
        if not ok:
            xbmc.log('Akasha Aura Store: invalid external app {}: {}'
                     .format(entry['id'], err), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33123).format(entry['name']),
                xbmcgui.NOTIFICATION_ERROR, 4000)
            return

        persisted_install = dict(install)
        if deep_link:
            persisted_install['deep_link'] = deep_link
        store_registry.record_install(
            entry['id'], entry.get('version', ''), _now_iso(), addon_id=None,
            name=entry.get('name', ''), install=persisted_install,
            icon=store_external.resolve_icon_url(entry['id'], entry.get('icon', '')))
        xbmcgui.Dialog().notification(
            'Akasha Store', i18n.tr(33309).format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)

    def _launch_external(self, entry):
        install = entry.get('install', {})
        source_url = install.get('source_url', '')
        deep_link = entry.get('deep_link') or install.get('deep_link') or ''
        name = entry.get('name', i18n.tr(33321))

        ok, err = store_external.validate_install(source_url, deep_link or None)
        if not ok:
            xbmc.log('Akasha Aura Store: cannot launch {}: {}'
                     .format(entry['id'], err), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33123).format(name),
                xbmcgui.NOTIFICATION_ERROR, 4000)
            return

        args = store_external.launch_command_args(
            source_url, name, deep_link=deep_link or None, app_id=entry['id'])
        try:
            # Detach from Kodi's cgroup before launch.sh stops kodi.service.
            subprocess.Popen(args)
            xbmc.sleep(1000)
        except Exception as e:
            xbmc.log('Akasha Aura Store: failed to launch {}: {}'
                     .format(entry['id'], e), xbmc.LOGERROR)

    def _uninstall_external(self, entry):
        store_registry.record_uninstall(entry['id'])
        xbmcgui.Dialog().notification(
            'Akasha Store', i18n.tr(33308).format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)

    def onClick(self, controlID):
        if controlID == INSTALL_BUTTON_ID:
            self._reload(force_refresh=True)
            xbmcgui.Dialog().notification(
                'Akasha Store', i18n.tr(33314), xbmcgui.NOTIFICATION_INFO, 2000)
        elif controlID in CHIP_IDS:
            self._select_category(CHIP_IDS.index(controlID))
        elif controlID == LIST_ID:
            entry = self._selected_entry()
            if entry:
                self._open_overview(entry)

    def _open_overview(self, entry):
        """Show the app-page overview sheet, then run the action the user
        picked: install / launch / uninstall according to entry state."""
        detail = AuraStoreDetailWindow(
            'AuraStoreDetail.xml',
            self.addon.getAddonInfo('path'), 'Default', '1080i')
        detail.set_entry(entry)
        detail.doModal()
        action = detail.action
        if action is None:
            return

        install = entry.get('install', {})
        itype = install.get('type')
        if action == 'primary':
            if not entry['installed']:
                if itype == 'external-app':
                    self._install_external(entry)
                    self._reload()
                else:
                    self._install(entry)
            elif itype == 'external-app':
                self._launch_external(entry)
            elif aura_menu.confirm(
                    self, 'Akasha Store',
                    i18n.tr(33306).format(entry['name'])):
                self._uninstall(entry)
        elif action == 'secondary':
            if aura_menu.confirm(
                    self, 'Akasha Store',
                    i18n.tr(33306).format(entry['name'])):
                self._uninstall_external(entry)
                self._reload()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_MOVE_UP, ACTION_MOVE_DOWN):
            try:
                pos = gui_guard.selpos(self, LIST_ID)
            except RuntimeError:
                pos = 0
            if self._paged:
                new_items = self._paged.maybe_load_more(pos)
                if new_items:
                    self.entries = self._paged.items
                    self._append_items(new_items)
        super().onAction(action)

    def _append_items(self, new_items):
        """Append newly paged items to the panel without a full reset."""
        try:
            lst = self.getControl(LIST_ID)
            for entry in new_items:
                lst.addItem(self._make_list_item(entry))
        except Exception as e:
            xbmc.log('Akasha Aura Store: append render error: {}'.format(e), xbmc.LOGERROR)
