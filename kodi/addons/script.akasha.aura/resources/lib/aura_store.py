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
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

import store_client
import store_external
import store_registry

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

HEADER_LABEL_ID = 6000
INSTALL_BUTTON_ID = 6001
STATUS_LABEL_ID = 6020
LIST_ID = 6010
BACK_BUTTON_ID = 6030


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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

        self.entries = []
        for entry in index.get('entries', []):
            install = entry.get('install', {})
            if install.get('type') in ('kodi-repo', 'zip-url'):
                installed = install.get('addon_id') in installed_kodi_ids
            else:
                installed = entry['id'] in registry
            self.entries.append(dict(entry, installed=installed))
        self._render()

    def _render(self):
        try:
            status = self.getControl(STATUS_LABEL_ID)
            status.setLabel('{} application(s) proposee(s)'.format(len(self.entries)))
        except RuntimeError:
            pass

        try:
            lst = self.getControl(LIST_ID)
            lst.reset()
            for entry in self.entries:
                state = 'Installe' if entry['installed'] else 'Non installe'
                category = entry.get('category', '')
                li = xbmcgui.ListItem(entry['name'], entry.get('description', ''))
                li.setProperty('installed', '1' if entry['installed'] else '0')
                li.setLabel2('{} — {} — {}'.format(category, entry.get('description', ''), state))
                lst.addItem(li)
            if self.entries:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura Store: render error: {}'.format(e), xbmc.LOGERROR)

    def _selected_entry(self):
        try:
            pos = self.getControl(LIST_ID).getSelectedPosition()
        except RuntimeError:
            return None
        if 0 <= pos < len(self.entries):
            return self.entries[pos]
        return None

    def _show_detail(self, entry):
        install = entry.get('install', {})
        lines = [
            entry.get('description', ''),
            '',
            'Categorie : {}'.format(entry.get('category', '-')),
            'Version : {}'.format(entry.get('version', '-')),
            'Type d\'installation : {}'.format(install.get('type', '-')),
            'Source : {}'.format(install.get('source_url', '-')),
            'Lien profond : {}'.format(install.get('deep_link') or '-'),
            '',
            entry.get('legal_notice', ''),
        ]
        xbmcgui.Dialog().textviewer(entry['name'], '\n'.join(lines))

    def _install(self, entry):
        install = entry.get('install', {})
        itype = install.get('type')
        xbmc.log('Akasha Aura Store: install requested for {} (type={})'
                  .format(entry['id'], itype), xbmc.LOGINFO)

        if entry['installed']:
            if itype == 'external-app':
                self._manage_external(entry)
            else:
                if xbmcgui.Dialog().yesno(
                        'Akasha Store',
                        '{} est deja installe. Le desinstaller ?'.format(entry['name'])):
                    self._uninstall(entry)
            return

        if itype == 'kodi-repo':
            addon_id = install.get('addon_id')
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
                    'Akasha Store', '{} installe'.format(entry['name']),
                    xbmcgui.NOTIFICATION_INFO, 3000)
            else:
                xbmcgui.Dialog().notification(
                    'Akasha Store', 'Installation non confirmee : {}'.format(entry['name']),
                    xbmcgui.NOTIFICATION_ERROR, 4000)
        elif itype == 'zip-url':
            self._install_from_zip(entry, install)
        elif itype == 'external-app':
            self._manage_external(entry)
        elif itype == 'script':
            # Informative only in V1 (plan section 3): never execute
            # anything from a manifest field automatically.
            self._show_detail(entry)
        else:
            xbmc.log('Akasha Aura Store: unknown install type {} for {}'
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
                'Akasha Store', 'Telechargement echoue pour {}'.format(entry['name']),
                xbmcgui.NOTIFICATION_ERROR, 3000)
            return

        actual_sha256 = hashlib.sha256(content).hexdigest()
        if expected_sha256 and actual_sha256 != expected_sha256:
            xbmc.log('Akasha Aura Store: sha256 mismatch for {} (expected {}, got {})'
                      .format(entry['id'], expected_sha256, actual_sha256), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', 'Verification echouee pour {}'.format(entry['name']),
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
            'Akasha Store', 'Paquet verifie pour {}'.format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)
        store_registry.record_install(
            entry['id'], entry.get('version', ''), _now_iso(), addon_id=addon_id)

    def _uninstall(self, entry):
        install = entry.get('install', {})
        addon_id = install.get('addon_id')
        if install.get('type') in ('kodi-repo', 'zip-url') and addon_id:
            # No public JSON-RPC uninstall method exists (see aura_app.py's
            # own docstring) -- route through the native AddonInformation
            # window, same as the App tab's uninstall action.
            xbmc.executebuiltin(
                'ActivateWindow(AddonInformation,{},return)'.format(addon_id))
        store_registry.record_uninstall(entry['id'])
        self._reload()

    def _manage_external(self, entry):
        """Context menu for an `external-app` Store entry.

        Existing controls only give us a single list click, so we use a native
        Kodi context menu to distinguish install / launch / detail / uninstall
        as coherently as possible.
        """
        installed = entry['installed']
        if installed:
            options = ['Lancer', 'Voir les details', 'Desinstaller']
        else:
            options = ['Installer', 'Voir les details']

        choice = xbmcgui.Dialog().contextmenu(options)
        if choice < 0:
            return

        if options[choice] == 'Lancer':
            self._launch_external(entry)
        elif options[choice] == 'Voir les details':
            self._show_detail(entry)
        elif options[choice] == 'Installer':
            self._install_external(entry)
            self._reload()
        elif options[choice] == 'Desinstaller':
            self._uninstall_external(entry)
            self._reload()

    def _install_external(self, entry):
        install = entry.get('install', {})
        source_url = install.get('source_url')
        deep_link = entry.get('deep_link')
        ok, err = store_external.validate_install(source_url, deep_link)
        if not ok:
            xbmc.log('Akasha Aura Store: invalid external app {}: {}'
                     .format(entry['id'], err), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', 'URL invalide : {}'.format(entry['name']),
                xbmcgui.NOTIFICATION_ERROR, 4000)
            return

        persisted_install = dict(install)
        if deep_link:
            persisted_install['deep_link'] = deep_link
        store_registry.record_install(
            entry['id'], entry.get('version', ''), _now_iso(), addon_id=None,
            name=entry.get('name', ''), install=persisted_install)
        xbmcgui.Dialog().notification(
            'Akasha Store', '{} enregistre'.format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)

    def _launch_external(self, entry):
        install = entry.get('install', {})
        source_url = install.get('source_url', '')
        deep_link = entry.get('deep_link') or install.get('deep_link') or ''
        name = entry.get('name', 'Web App')

        ok, err = store_external.validate_install(source_url, deep_link or None)
        if not ok:
            xbmc.log('Akasha Aura Store: cannot launch {}: {}'
                     .format(entry['id'], err), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'Akasha Store', 'URL invalide : {}'.format(name),
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
            'Akasha Store', '{} retire'.format(entry['name']),
            xbmcgui.NOTIFICATION_INFO, 3000)

    def onClick(self, controlID):
        if controlID == INSTALL_BUTTON_ID:
            self._reload(force_refresh=True)
            xbmcgui.Dialog().notification(
                'Akasha Store', 'Catalogue actualise', xbmcgui.NOTIFICATION_INFO, 2000)
        elif controlID == LIST_ID:
            entry = self._selected_entry()
            if entry:
                self._install(entry)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)
