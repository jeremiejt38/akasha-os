"""Akasha Aura -- Unified Settings panel (plan a5a87f03).

Two-pane Android TV/Apple TV-style settings screen: a category list on the
left, a handful of curated actions for the selected category on the right.
Replaces the 3 separate "Parametres Kodi/LibreELEC/Akasha" entries in the
gear's context menu (plan 04bda1b4) with a single "Parametres" entry that
opens this panel instead.

Per the phase 0 audit (docs/settings/decisions.md): Kodi+LibreELEC+Akasha
expose 300+ individual settings between them. Rather than reimplementing
every one inside this panel (explicitly discouraged by the cahier's own
section 3), each category here surfaces a short list of curated actions
that either jump straight to the real native screen already responsible
for that setting (Kodi's own settings categories, LibreELEC's settings
addon, or a specific addon's own settings screen), or -- for the handful
of settings Akasha already manages itself (Mode Ambiant, veille/extinction)
-- reuse the existing script.akasha.settings entry points. Every action
here has a real effect on the real underlying setting; nothing is a purely
cosmetic placeholder.
"""
import xbmc
import xbmcgui

CATEGORY_LIST_ID = 100
DETAIL_LIST_ID = 200
HEADER_LABEL_ID = 10

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


def _run(builtin):
    def _action():
        xbmc.executebuiltin(builtin)
    return _action


# (category_id, label, [(row_label, row_action_callable), ...])
# Order and grouping mirror the cahier's section 2 proposal, refined by the
# real audit in docs/settings/decisions.md.
def _build_categories():
    return [
        ('network', 'Reseau & Connectivite', [
            ('Wi-Fi, Ethernet, VPN (LibreELEC)',
             _run('RunAddon(service.libreelec.settings)')),
            ('Proxy et bande passante (Kodi)',
             _run('ActivateWindow(systemsettings)')),
        ]),
        ('accounts', 'Comptes & Services', [
            ('Plex', _run('RunAddon(script.plexmod)')),
            ('Jellyfin', _run('RunAddon(plugin.video.jellyfin)')),
            ('YouTube Music', _run('RunAddon(plugin.video.youtube)')),
            ('Cloud gaming (Steam, Sunshine/Moonlight)',
             _run('Addon.OpenSettings(script.akasha.aura)')),
        ]),
        ('display', 'Affichage & Son', [
            ('Resolution, HDR, HDMI-CEC, sortie audio (Kodi)',
             _run('ActivateWindow(systemsettings)')),
        ]),
        ('controllers', 'Manettes & Telecommandes', [
            ('Appairage Bluetooth (LibreELEC)',
             _run('RunAddon(service.libreelec.settings)')),
            # Deliberately NOT ActivateWindow(peripheralsettings): reliably
            # crashes Kodi (SIGSEGV in CVariant::CVariant, native engine
            # bug unrelated to this addon -- reproduced both from here and
            # via a bare JSON-RPC GUI.ActivateWindow call) on this device.
            # See docs/settings/decisions.md.
        ]),
        ('library', 'Bibliotheque & Lecture', [
            ('Langue audio et sous-titres par defaut (Kodi)',
             _run('ActivateWindow(playersettings)')),
            ('Reglages de bibliotheque/lecture video (Kodi)',
             _run('ActivateWindow(mediasettings)')),
        ]),
        ('appearance', 'Apparence & Interface', [
            ('Langue de l\'interface, region, ecran de veille (Kodi)',
             _run('ActivateWindow(interfacesettings)')),
            ('Habillage du skin (Kodi)',
             _run('ActivateWindow(skinsettings)')),
            ('Overlay systeme, Mode Ambiant (Akasha)',
             _run('RunScript(script.akasha.settings)')),
        ]),
        ('storage', 'Stockage', [
            ('Sources et gestionnaire de fichiers (Kodi)',
             _run('ActivateWindow(filemanager)')),
        ]),
        ('power', 'Energie', [
            ('Veille ecran, extinction auto (Kodi)',
             _run('ActivateWindow(systemsettings)')),
            ('Delai veille/extinction, ventilateur (Akasha)',
             _run('RunScript(script.akasha.settings)')),
        ]),
        ('system', 'Systeme & Mises a jour', [
            ('Nom systeme, sauvegarde, MAJ LibreELEC',
             _run('RunAddon(service.libreelec.settings)')),
            ('Verifier les mises a jour Akasha OS',
             _run('RunScript(script.akasha.settings)')),
            ('Mises a jour et sources des extensions (Kodi)',
             _run('ActivateWindow(systemsettings)')),
        ]),
        ('profiles', 'Profils & Utilisateurs', [
            ('Gerer les profils (Kodi)', _run('ActivateWindow(profilesettings)')),
        ]),
        ('advanced', 'Avance', [
            ('Tous les parametres Kodi', _run('ActivateWindow(settings)')),
            ('Tous les parametres LibreELEC',
             _run('RunAddon(service.libreelec.settings)')),
        ]),
    ]


class AuraSettingsPanelWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = _build_categories()
        self._selected_category = 0
        # Set by AuraWindow._open_settings_panel() before doModal(): Aura's
        # own window, closed alongside this panel before firing a row's
        # action (see the comment there for why).
        self.parent_window = None

    def onInit(self):
        try:
            panel = self.getControl(CATEGORY_LIST_ID)
            panel.reset()
            for _, label, _ in self.categories:
                panel.addItem(xbmcgui.ListItem(label))
            self.setFocus(panel)
            self._show_category(0)
        except Exception as e:
            xbmc.log('Akasha Aura Settings: init error: {}'.format(e), xbmc.LOGERROR)

    def _show_category(self, index):
        if not (0 <= index < len(self.categories)):
            return
        self._selected_category = index
        _, label, rows = self.categories[index]
        try:
            self.getControl(HEADER_LABEL_ID).setLabel(label)
        except RuntimeError:
            pass
        try:
            detail = self.getControl(DETAIL_LIST_ID)
            detail.reset()
            for row_label, _ in rows:
                detail.addItem(xbmcgui.ListItem(row_label))
        except RuntimeError:
            pass

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            focused = self.getFocusId()
            if focused == DETAIL_LIST_ID:
                try:
                    self.setFocus(self.getControl(CATEGORY_LIST_ID))
                except RuntimeError:
                    self.close()
                return
            self.close()
            return
        super().onAction(action)
        if self.getFocusId() == CATEGORY_LIST_ID:
            try:
                pos = self.getControl(CATEGORY_LIST_ID).getSelectedPosition()
            except RuntimeError:
                return
            if pos != self._selected_category:
                self._show_category(pos)

    def onClick(self, controlID):
        if controlID == CATEGORY_LIST_ID:
            try:
                self.setFocus(self.getControl(DETAIL_LIST_ID))
            except RuntimeError:
                pass
        elif controlID == DETAIL_LIST_ID:
            self._run_selected_row()

    def _run_selected_row(self):
        _, _, rows = self.categories[self._selected_category]
        try:
            pos = self.getControl(DETAIL_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(rows)):
            return
        _, action = rows[pos]
        # Every row's action hands off to a real native screen. Both this
        # panel and Aura itself must close before firing it -- otherwise a
        # *base* window action (Kodi Settings/System/Profiles...) opens
        # invisibly underneath one of these still-open dialogs instead of
        # becoming visible (see the comment in
        # AuraWindow._open_settings_panel()).
        self.close()
        if self.parent_window is not None:
            try:
                self.parent_window.close()
            except Exception:
                pass
        try:
            action()
        except Exception as e:
            xbmc.log('Akasha Aura Settings: action failed: {}'.format(e), xbmc.LOGERROR)
