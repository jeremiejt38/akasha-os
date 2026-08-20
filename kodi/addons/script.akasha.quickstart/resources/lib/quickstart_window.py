"""Akasha Quick Start -- first-run setup wizard window.

Phase 1 (plan 3aba4284) built the generic navigation skeleton
(Suivant/Precedent/Passer, progress indicator, completion/step-progress
markers). Phases 2-6 (this file) fill in each step's real content:
real settings changes (Kodi JSON-RPC), real network scan/connect
(connman via quickstart_network.py), real remote-control test, and
delegating to the exact existing native/addon screen for anything that
genuinely needs its own interactive UI (LibreELEC Wi-Fi/Bluetooth,
Plex/Jellyfin/YouTube account linking, Kodi profile creation) rather
than reimplementing it -- consistent with the same philosophy already
applied to the unified settings panel (plan a5a87f03).
"""
import json
import subprocess

import xbmc
import xbmcaddon
import xbmcgui

import quickstart_network as net
import quickstart_state as state

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7

BTN_PREVIOUS = 100
BTN_NEXT = 101
BTN_SKIP = 102

STEP_TITLE_LABEL_ID = 11
STEP_PROGRESS_LABEL_ID = 12
SUMMARY_LABEL_ID = 1001

# Remote-test step (5): the 4 directions light up as they are pressed.
REMOTE_TEST_DIRECTIONS = {
    ACTION_MOVE_UP: 'Haut',
    ACTION_MOVE_DOWN: 'Bas',
    ACTION_MOVE_LEFT: 'Gauche',
    ACTION_MOVE_RIGHT: 'Droite',
    ACTION_SELECT_ITEM: 'OK',
}

CLOUD_GAMING_SERVICES = (
    'Steam Link', 'Moonlight', 'GeForce NOW', 'Xbox Cloud Gaming',
    'Amazon Luna', 'Boosteroid',
)

# Each step's content buttons chain Down into the footer (100/101/102),
# but the footer's own <onup> is a self-loop (it has to be static XML,
# shared across every step's differently-shaped content) -- so pressing
# Up from the footer needs a Python-side redirect to whichever control
# is actually first for the *current* step, or it would just dead-end.
FIRST_CONTROL_BY_STEP = {
    state.STEP_LANGUAGE: 210,
    state.STEP_NETWORK: 310,
    state.STEP_DISPLAY: 410,
    state.STEP_CONTROLLERS: 510,
    state.STEP_ACCOUNTS: 610,
    state.STEP_CLOUD_GAMING: 710,
    state.STEP_POWER: 810,
    state.STEP_PROFILE: 910,
}


def _jsonrpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        payload['params'] = params
    raw = xbmc.executeJSONRPC(json.dumps(payload))
    return json.loads(raw)


def _get_setting_options(setting_id, section, category):
    resp = _jsonrpc('Settings.GetSettings', {
        'filter': {'section': section, 'category': category}, 'level': 'expert'})
    for s in resp.get('result', {}).get('settings', []):
        if s.get('id') == setting_id:
            return s
    return None


def _set_setting(setting_id, value):
    resp = _jsonrpc('Settings.SetSettingValue', {'setting': setting_id, 'value': value})
    return bool(resp.get('result'))


class QuickStartWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.quickstart')
        self.step = state.STEP_WELCOME
        # Set by default.py before doModal(): STEP_WELCOME for a manual
        # "restart from scratch" relaunch, or the persisted last step to
        # resume an interrupted run (see default.py's own docstring).
        self.initial_step = state.STEP_WELCOME
        self._finished = False
        # Real choices made across steps, surfaced on the Recapitulatif
        # step (section 2 etape 10) -- filled in as the user goes, not
        # guessed at retroactively.
        self.results = {
            'language': None,
            'network': None,
            'display': [],
            'controllers': [],
            'accounts': [],
            'cloud_gaming': [],
            'power': [],
            'profile': None,
        }
        self._network_ok = False
        self._wifi_networks = []

    def onInit(self):
        self._show_step(self.initial_step, save=False)

    def _show_step(self, step_id, save=True):
        self.step = state.clamp_step(step_id)
        self.setProperty('QSStep', str(self.step))
        if save:
            state.save_step(self.step)

        try:
            self.getControl(STEP_TITLE_LABEL_ID).setLabel(state.step_title(self.step))
        except RuntimeError:
            pass
        try:
            self.getControl(STEP_PROGRESS_LABEL_ID).setLabel(
                'Etape {} sur {}'.format(self.step + 1, len(state.STEPS)))
        except RuntimeError:
            pass

        is_last = self.step == len(state.STEPS) - 1
        try:
            next_btn = self.getControl(BTN_NEXT)
            if is_last:
                next_btn.setLabel('Terminer')
            elif self.step == state.STEP_WELCOME:
                next_btn.setLabel('Commencer')
            else:
                next_btn.setLabel('Suivant')
        except RuntimeError:
            pass
        try:
            skip_btn = self.getControl(BTN_SKIP)
            skip_btn.setVisible(state.is_skippable(self.step) and not is_last)
        except RuntimeError:
            pass
        try:
            prev_btn = self.getControl(BTN_PREVIOUS)
            prev_btn.setVisible(self.step > state.STEP_WELCOME)
        except RuntimeError:
            pass

        if self.step == state.STEP_LANGUAGE:
            self._refresh_language_label()
        elif self.step == state.STEP_NETWORK:
            self._refresh_network_status()
        elif self.step == state.STEP_DISPLAY:
            self._refresh_display_summary()
        elif self.step == state.STEP_CLOUD_GAMING:
            self._refresh_cloud_gaming_summary()
        elif self.step == state.STEP_POWER:
            self._refresh_power_summary()
        elif self.step == state.STEP_SUMMARY:
            self._render_summary()

    # ------------------------------------------------------------------
    # Etape 2 -- Langue et region
    # ------------------------------------------------------------------
    def _refresh_language_label(self):
        try:
            resp = _jsonrpc('Settings.GetSettingValue', {'setting': 'locale.language'})
            current = resp.get('result', {}).get('value', '')
        except Exception:
            current = ''
        label = current.replace('resource.language.', '') if current else '-'
        try:
            self.getControl(212).setLabel(label)
        except RuntimeError:
            pass

    def _pick_language(self):
        try:
            resp = _jsonrpc('Addons.GetAddons', {
                'type': 'kodi.resource.language', 'properties': ['name']})
            addons = resp.get('result', {}).get('addons', [])
        except Exception as e:
            xbmc.log('Akasha Quick Start: language list failed: {}'.format(e), xbmc.LOGWARNING)
            addons = []
        if not addons:
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', 'Aucune langue disponible', xbmcgui.NOTIFICATION_ERROR)
            return
        names = [a.get('name', a['addonid']) for a in addons]
        idx = xbmcgui.Dialog().select('Langue de l\'interface', names)
        if idx < 0:
            return
        addonid = addons[idx]['addonid']
        if _set_setting('locale.language', addonid):
            self.results['language'] = names[idx]
            self._refresh_language_label()

    # ------------------------------------------------------------------
    # Etape 3 -- Connexion reseau (bloquant, section 3)
    # ------------------------------------------------------------------
    def _refresh_network_status(self):
        ethernet = net.ethernet_carrier_present()
        online = net.has_internet_access()
        self._network_ok = online
        try:
            status = self.getControl(301)
            if online and ethernet:
                status.setLabel('Connexion internet detectee (Ethernet).')
            elif online:
                status.setLabel('Connexion internet detectee (Wi-Fi).')
            else:
                status.setLabel(
                    "Aucun acces internet detecte. Configurez le Wi-Fi ci-dessous, "
                    "ou branchez un cable Ethernet puis retestez.")
        except RuntimeError:
            pass
        try:
            self.getControl(311).setLabel(
                'Configurer le Wi-Fi quand meme' if online else 'Configurer le Wi-Fi')
        except RuntimeError:
            pass
        if online:
            self.results['network'] = 'Ethernet' if ethernet else 'Wi-Fi'

    def _configure_wifi(self):
        try:
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', 'Recherche des reseaux Wi-Fi...',
                xbmcgui.NOTIFICATION_INFO, 2000)
            self._wifi_networks = net.list_wifi_networks()
        except Exception as e:
            xbmc.log('Akasha Quick Start: wifi scan failed: {}'.format(e), xbmc.LOGERROR)
            self._wifi_networks = []
        if not self._wifi_networks:
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', 'Aucun reseau Wi-Fi trouve', xbmcgui.NOTIFICATION_ERROR)
            return
        names = [n['name'] for n in self._wifi_networks]
        idx = xbmcgui.Dialog().select('Reseaux Wi-Fi disponibles', names)
        if idx < 0:
            return
        chosen = self._wifi_networks[idx]
        passphrase = None
        if not chosen['favorite']:
            kb = xbmc.Keyboard('', 'Mot de passe pour {}'.format(chosen['name']))
            kb.setHiddenInput(True)
            kb.doModal()
            if not kb.isConfirmed():
                return
            passphrase = kb.getText()
        ok, output = net.connect_wifi(chosen['service_id'], passphrase)
        if ok:
            self.results['network'] = 'Wi-Fi ({})'.format(chosen['name'])
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', 'Connecte a {}'.format(chosen['name']),
                xbmcgui.NOTIFICATION_INFO)
        else:
            xbmc.log('Akasha Quick Start: wifi connect failed: {}'.format(output), xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', "Echec de connexion, verifiez le mot de passe",
                xbmcgui.NOTIFICATION_ERROR)
        self._refresh_network_status()

    # ------------------------------------------------------------------
    # Etape 4 -- Affichage et son
    # ------------------------------------------------------------------
    def _refresh_display_summary(self):
        lines = []
        for setting_id, label in (
                ('videoscreen.resolution', 'Resolution'),
                ('audiooutput.audiodevice', 'Sortie audio')):
            try:
                resp = _jsonrpc('Settings.GetSettingValue', {'setting': setting_id})
                value = resp.get('result', {}).get('value', '-')
            except Exception:
                value = '-'
            lines.append('{}: {}'.format(label, value))
        try:
            self.getControl(401).setLabel('\n'.join(lines))
        except RuntimeError:
            pass

    def _pick_setting_from_options(self, setting_id, section, category, title):
        info = _get_setting_options(setting_id, section, category)
        if not info or not info.get('options'):
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', 'Reglage indisponible', xbmcgui.NOTIFICATION_ERROR)
            return None
        options = info['options']
        labels = [o.get('label', str(o.get('value'))) for o in options]
        idx = xbmcgui.Dialog().select(title, labels)
        if idx < 0:
            return None
        value = options[idx]['value']
        return value if _set_setting(setting_id, value) else None

    def _pick_resolution(self):
        try:
            previous = _jsonrpc(
                'Settings.GetSettingValue',
                {'setting': 'videoscreen.resolution'}).get('result', {}).get('value')
        except Exception:
            previous = None
        value = self._pick_setting_from_options(
            'videoscreen.resolution', 'system', 'display', 'Resolution')
        if value is None:
            return
        # Section 2 etape 4: confirm-or-revert within 10s, mirroring
        # Kodi's own native resolution-change safety net -- defaults to
        # "No" (revert) if the 10s autoclose elapses without an answer.
        if not xbmcgui.Dialog().yesno(
                'Akasha Quick Start', "Cet ecran est-il correct ?",
                nolabel='Revenir en arriere', yeslabel='Garder', autoclose=10000):
            if previous is not None:
                _set_setting('videoscreen.resolution', previous)
        else:
            self.results['display'].append('Resolution confirmee')
        self._refresh_display_summary()

    def _pick_audio_device(self):
        value = self._pick_setting_from_options(
            'audiooutput.audiodevice', 'system', 'audio', 'Peripherique de sortie audio')
        if value is not None:
            self.results['display'].append('Sortie audio configuree')
        self._refresh_display_summary()

    def _toggle_cec_sync(self):
        # Reuses the same real setting script.akasha.settings' "Mode
        # extinction : Shutdown + CEC" already applies (powermanagement.
        # shutdownstate = 0, Shutdown -- the only mode that also sends the
        # CEC standby signal to the TV) -- via JSON-RPC directly rather
        # than importing that addon's Python (cross-addon imports aren't
        # supported), same real effect.
        if _set_setting('powermanagement.shutdownstate', 0):
            self.results['display'].append('Veille synchronisee avec la TV (CEC)')
            xbmcgui.Dialog().notification(
                'Akasha Quick Start', 'Synchronisation CEC activee',
                xbmcgui.NOTIFICATION_INFO)
        self._refresh_display_summary()

    # ------------------------------------------------------------------
    # Etape 5 -- Manette et telecommande
    # ------------------------------------------------------------------
    def _remote_test_feedback(self, aid):
        direction = REMOTE_TEST_DIRECTIONS.get(aid)
        if not direction:
            return
        if direction not in self.results['controllers']:
            self.results['controllers'].append(direction)
        try:
            tested = ', '.join(self.results['controllers'])
            self.getControl(502).setLabel('Detecte : {}'.format(tested))
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    # Etape 6 -- Comptes de contenu (chacun optionnel individuellement)
    # ------------------------------------------------------------------
    def _open_account_addon(self, addonid, label):
        # Each account's own linking/login screen is a real addon UI (not
        # always a stackable dialog) -- closed first for the same reason
        # as _open_profiles() below; resumes at this exact step
        # afterward thanks to the persisted step marker.
        if label not in self.results['accounts']:
            self.results['accounts'].append(label)
        self.close()
        xbmc.executebuiltin('RunAddon({})'.format(addonid))

    # ------------------------------------------------------------------
    # Etape 7 -- Cloud gaming (choix multiple, pas de connexion ici)
    # ------------------------------------------------------------------
    def _refresh_cloud_gaming_summary(self):
        chosen = self.results.get('cloud_gaming') or []
        try:
            self.getControl(701).setLabel(
                'Selectionnes : {}'.format(', '.join(chosen)) if chosen
                else 'Aucun service selectionne pour le moment.')
        except RuntimeError:
            pass

    def _pick_cloud_gaming_services(self):
        preselect = [i for i, s in enumerate(CLOUD_GAMING_SERVICES)
                     if s in (self.results.get('cloud_gaming') or [])]
        indices = xbmcgui.Dialog().multiselect(
            'Services de cloud gaming a activer', list(CLOUD_GAMING_SERVICES),
            preselect=preselect)
        if indices is None:
            return
        chosen = [CLOUD_GAMING_SERVICES[i] for i in indices]
        self.results['cloud_gaming'] = chosen
        # Pre-activates the corresponding Jeux module tiles/shortcuts --
        # stored as an Aura addon setting, read by aura_window.py's own
        # Jeux tab logic to decide which "Autres" shortcuts to surface.
        try:
            aura_addon = xbmcaddon.Addon('script.akasha.aura')
            aura_addon.setSetting('quickstart.cloud_gaming_services', ','.join(chosen))
        except Exception as e:
            xbmc.log('Akasha Quick Start: saving cloud gaming choice failed: {}'.format(e),
                     xbmc.LOGWARNING)
        self._refresh_cloud_gaming_summary()

    # ------------------------------------------------------------------
    # Etape 8 -- Preferences energie
    # ------------------------------------------------------------------
    def _refresh_power_summary(self):
        try:
            shutdown_min = _jsonrpc(
                'Settings.GetSettingValue',
                {'setting': 'powermanagement.shutdowntime'}).get('result', {}).get('value', 30)
            screensaver_min = _jsonrpc(
                'Settings.GetSettingValue',
                {'setting': 'screensaver.time'}).get('result', {}).get('value', 5)
        except Exception:
            shutdown_min, screensaver_min = 30, 5
        try:
            self.getControl(801).setLabel(
                'Veille ecran : {} min\nExtinction auto : {} min'.format(
                    screensaver_min, shutdown_min))
        except RuntimeError:
            pass

    def _pick_delay(self, setting_id, title, choices_minutes):
        # Same real Kodi settings script.akasha.settings' own "Delai
        # ecran de veille"/"Delai extinction automatique" pickers already
        # use (powermanagement.shutdowntime / screensaver.time) -- via
        # JSON-RPC directly since cross-addon Python imports aren't
        # supported, same effect.
        labels = ['{} min'.format(m) for m in choices_minutes]
        idx = xbmcgui.Dialog().select(title, labels)
        if idx < 0:
            return
        if _set_setting(setting_id, choices_minutes[idx]):
            self.results['power'].append('{}: {} min'.format(title, choices_minutes[idx]))
        if setting_id == 'powermanagement.shutdowntime':
            _set_setting('powermanagement.shutdownstate', 0)  # Shutdown+CEC, see _toggle_cec_sync
        self._refresh_power_summary()

    def _pick_screensaver_delay(self):
        self._pick_delay('screensaver.time', 'Delai veille ecran', [1, 3, 5, 10, 15, 20, 30])

    def _pick_shutdown_delay(self):
        self._pick_delay('powermanagement.shutdowntime', 'Delai extinction auto',
                          [15, 30, 45, 60, 90, 120])

    # ------------------------------------------------------------------
    # Etape 9 -- Profil utilisateur
    # ------------------------------------------------------------------
    def _open_profiles(self):
        # No JSON-RPC method creates a profile (Profiles.* is read-only:
        # GetProfiles/GetCurrentProfile/LoadProfile) -- native Kodi screen
        # is the only real way to create one. This is a *base* window
        # (not a dialog), so it needs this wizard closed first to become
        # visible (see the same finding in aura_settings_panel.py) --
        # the user must reopen Quick Start manually afterward (Akasha
        # Settings > "Relancer l'assistant"), it resumes at this exact
        # step thanks to the persisted step marker.
        self.results['profile'] = 'Ouverture des profils Kodi'
        self.close()
        xbmc.executebuiltin('ActivateWindow(profilesettings)')

    # ------------------------------------------------------------------
    # Etape 10 -- Recapitulatif
    # ------------------------------------------------------------------
    def _render_summary(self):
        lines = []
        lines.append('Reseau : {}'.format(self.results.get('network') or 'non configure'))
        lines.append('Langue : {}'.format(self.results.get('language') or 'inchangee'))
        display = self.results.get('display') or []
        lines.append('Affichage/son : {}'.format(', '.join(display) if display else 'inchange'))
        controllers = self.results.get('controllers') or []
        lines.append('Telecommande testee : {}'.format(
            ', '.join(controllers) if controllers else 'non testee'))
        accounts = self.results.get('accounts') or []
        lines.append('Comptes ouverts : {}'.format(', '.join(accounts) if accounts else 'aucun'))
        cloud = self.results.get('cloud_gaming') or []
        lines.append('Cloud gaming : {}'.format(', '.join(cloud) if cloud else 'aucun'))
        power = self.results.get('power') or []
        lines.append('Energie : {}'.format(', '.join(power) if power else 'valeurs par defaut'))
        try:
            self.getControl(SUMMARY_LABEL_ID).setLabel('\n'.join(lines))
        except RuntimeError:
            pass

    def _next(self):
        if self.step == state.STEP_NETWORK and not self._network_ok:
            xbmcgui.Dialog().notification(
                'Akasha Quick Start',
                "Connexion internet requise pour continuer", xbmcgui.NOTIFICATION_ERROR)
            return
        if self.step == len(state.STEPS) - 1:
            self._finish()
            return
        self._show_step(self.step + 1)

    def _previous(self):
        if self.step == state.STEP_WELCOME:
            return
        self._show_step(self.step - 1)

    def _skip(self):
        if not state.is_skippable(self.step):
            return
        self._next()

    def _finish(self):
        state.mark_completed()
        self._finished = True
        self.close()
        xbmc.executebuiltin('RunScript(script.akasha.aura)')

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._confirm_exit()
            return
        if self.step == state.STEP_CONTROLLERS and aid in REMOTE_TEST_DIRECTIONS:
            self._remote_test_feedback(aid)
        if aid == ACTION_MOVE_UP and self.getFocusId() in (BTN_PREVIOUS, BTN_NEXT, BTN_SKIP):
            first_control = FIRST_CONTROL_BY_STEP.get(self.step)
            if first_control is not None:
                try:
                    self.setFocus(self.getControl(first_control))
                    return
                except RuntimeError:
                    pass
        super().onAction(action)

    def _confirm_exit(self):
        # Section 1: an early exit must NOT count as "completed" -- the
        # marker is only ever set from _finish() above, so simply closing
        # here (without calling it) already guarantees the wizard
        # re-appears next boot, resuming at this exact step (persisted
        # by _show_step()). Still ask for a clear confirmation instead
        # of exiting on a single stray Back press, per section 1's
        # "fermeture avec confirmation claire".
        if xbmcgui.Dialog().yesno(
                'Akasha Quick Start',
                "Quitter l'assistant ? Vos choix deja valides sont conserves, "
                "il reprendra a cette etape au prochain demarrage."):
            self.close()

    def onClick(self, controlID):
        if controlID == BTN_PREVIOUS:
            self._previous()
        elif controlID == BTN_NEXT:
            self._next()
        elif controlID == BTN_SKIP:
            self._skip()
        elif controlID == 210:
            self._pick_language()
        elif controlID == 211:
            self.close()
            xbmc.executebuiltin('ActivateWindow(interfacesettings)')
        elif controlID == 310:
            self._refresh_network_status()
        elif controlID == 311:
            self._configure_wifi()
        elif controlID == 410:
            self._pick_resolution()
        elif controlID == 411:
            self._pick_audio_device()
        elif controlID == 412:
            self._toggle_cec_sync()
        elif controlID == 510:
            self.close()
            xbmc.executebuiltin('RunAddon(service.libreelec.settings)')
        elif controlID == 610:
            self._open_account_addon('script.plexmod', 'Plex')
        elif controlID == 611:
            self._open_account_addon('plugin.video.jellyfin', 'Jellyfin')
        elif controlID == 612:
            self._open_account_addon('plugin.video.youtube', 'YouTube Music')
        elif controlID == 710:
            self._pick_cloud_gaming_services()
        elif controlID == 810:
            self._pick_screensaver_delay()
        elif controlID == 811:
            self._pick_shutdown_delay()
        elif controlID == 910:
            self._open_profiles()
