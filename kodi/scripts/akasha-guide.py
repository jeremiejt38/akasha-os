#!/usr/bin/env python3
"""Akasha Guide — quick-access menu triggered by the controller Guide button.

Style (context menu / select list / custom XML) is chosen in
Akasha Settings > Style du menu Guide.

A second press on Guide closes an already-open menu.
"""
import json
import os
import subprocess
import sys
import time
import threading
import xbmc
import xbmcgui
import xbmcaddon

LOCK_FILE = '/tmp/akasha-guide.lock'
CLOSE_FILE = '/tmp/akasha-guide.close'
LOCK_TTL = 10  # seconds; refreshed while the menu is open

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

OPTIONS = [
    ('Accueil', 'ActivateWindow(Home)', False),
    ('Akasha Settings', 'RunAddon(script.akasha.settings)', False),
    ('Activer / desactiver overlay systeme', '__overlay__', False),
    ('Redemarrer Akasha', 'RestartApp', True),
    ('Mise en veille', '__sleep__', True),
    ('Eteindre le systeme', 'Shutdown', True),
]
LABELS = [opt[0] for opt in OPTIONS]


def _send_back():
    """Send a Back action to close the topmost Kodi dialog."""
    payload = {'jsonrpc': '2.0', 'method': 'Input.Back', 'id': 1}
    try:
        xbmc.executeJSONRPC(json.dumps(payload))
    except Exception:
        pass


def _touch(path):
    try:
        with open(path, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _is_open():
    try:
        if os.path.exists(LOCK_FILE):
            age = time.time() - os.path.getmtime(LOCK_FILE)
            return age < LOCK_TTL
    except Exception:
        pass
    return False


def _sleep():
    """Put the system/TV to sleep and wake on input."""
    if not xbmcgui.Dialog().yesno('Akasha Guide', 'Mettre l\'appareil et le televiseur en veille ?'):
        return
    script = '/storage/.kodi/scripts/akasha-sleep.py'
    try:
        subprocess.Popen([sys.executable, script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        xbmc.log('Akasha Guide: sleep launch error: {}'.format(e), xbmc.LOGERROR)


def _toggle_overlay():
    try:
        addon = xbmcaddon.Addon('script.akasha.settings')
        current = addon.getSetting('overlay.enabled').lower() == 'true'
        new_state = 'false' if current else 'true'
        addon.setSetting('overlay.enabled', new_state)
        if new_state == 'true':
            xbmc.executebuiltin('Skin.SetBool(akasha_overlay)')
            xbmcgui.Dialog().notification(
                'Akasha Guide', 'Overlay systeme active',
                xbmcgui.NOTIFICATION_INFO, 1500
            )
        else:
            xbmc.executebuiltin('Skin.Reset(akasha_overlay)')
            xbmcgui.Dialog().notification(
                'Akasha Guide', 'Overlay systeme desactive',
                xbmcgui.NOTIFICATION_INFO, 1500
            )
    except Exception as e:
        xbmc.log('Akasha Guide: overlay toggle error: {}'.format(e), xbmc.LOGERROR)


def _restart_kodi():
    if not xbmcgui.Dialog().yesno('Akasha Guide', 'Redemarrer Akasha maintenant ?'):
        return
    # Show reboot splash in ExecStartPre when Kodi restarts (same flag as
    # script.akasha.settings, checked by show-splash-if-restart.sh).
    _touch('/tmp/.kodi-restart')
    subprocess.Popen(['systemctl', 'restart', 'kodi'], start_new_session=True)


def _shutdown_system():
    if not xbmcgui.Dialog().yesno('Akasha Guide', 'Eteindre le systeme maintenant ?\n(La TV sera aussi eteinte via CEC)'):
        return
    # Show the shutdown splash and turn the TV off via CEC before the system
    # shuts down. The matching systemd service will skip if already shown.
    subprocess.run(['/storage/.kodi/scripts/show-splash.sh', '/storage/.kodi/media/splash-shutdown.png', '1'])
    subprocess.Popen(['systemctl', 'poweroff'], start_new_session=True)


def _run_builtin(action):
    if action == '__overlay__':
        _toggle_overlay()
        return
    if action == '__sleep__':
        _sleep()
        return
    if action == 'RestartApp':
        _restart_kodi()
        return
    if action == 'Shutdown':
        _shutdown_system()
        return
    xbmc.executebuiltin(action)


class GuideWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.list = None
        self._closing = False
        super().__init__(*args, **kwargs)

    def onInit(self):
        try:
            self.list = self.getControl(9000)
            self.list.reset()
            for label, action, confirm in OPTIONS:
                self.list.addItem(xbmcgui.ListItem(label=label))
            self.setFocus(self.list)
        except Exception as e:
            xbmc.log('Akasha Guide: custom window init error: {}'.format(e), xbmc.LOGERROR)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close_safe()
            return
        if aid == ACTION_SELECT_ITEM:
            self._select_current()
            return
        # Let Kodi handle up/down for the list
        super().onAction(action)

    def onClick(self, controlID):
        if controlID == 9000:
            self._select_current()

    def _select_current(self):
        if self.list is None:
            return
        idx = self.list.getSelectedPosition()
        if idx < 0 or idx >= len(OPTIONS):
            return
        label, action, confirm = OPTIONS[idx]
        _run_builtin(action)
        self.close_safe()

    def close_safe(self):
        if self._closing:
            return
        self._closing = True
        try:
            self.close()
        except Exception:
            pass


def _open_custom():
    addon = xbmcaddon.Addon('script.akasha.guide')
    path = addon.getAddonInfo('path')
    return GuideWindow('Guide.xml', path, 'Default', '1080i')


def _native_menu(style):
    """Open a native dialog and return when closed."""
    dialog = xbmcgui.Dialog()
    if style == 1:
        choice = dialog.select('Akasha Guide', LABELS, preselect=0)
    else:
        choice = dialog.contextmenu(LABELS)

    if choice < 0:
        return
    label, action, confirm = OPTIONS[choice]
    _run_builtin(action)


def main():
    # If a menu is already open, close it (Back) and exit.
    if _is_open():
        _send_back()
        return

    # Read chosen style from Akasha Settings
    try:
        settings = xbmcaddon.Addon('script.akasha.settings')
        style = int(settings.getSetting('guide.style') or '0')
    except Exception:
        style = 0

    if style != 2:
        # Native dialog style (contextmenu / select)
        _touch(LOCK_FILE)
        try:
            _native_menu(style)
        finally:
            _remove(LOCK_FILE)
        return

    # Custom XML window
    _remove(LOCK_FILE)
    _remove(CLOSE_FILE)
    _touch(LOCK_FILE)

    try:
        window = _open_custom()
        stop_event = threading.Event()

        def watcher():
            while not stop_event.is_set():
                _touch(LOCK_FILE)
                if os.path.exists(CLOSE_FILE):
                    try:
                        window.close_safe()
                    except Exception:
                        pass
                    break
                time.sleep(0.5)

        t = threading.Thread(target=watcher, daemon=True)
        t.start()
        try:
            window.doModal()
        finally:
            stop_event.set()
            try:
                t.join(timeout=1)
            except Exception:
                pass
    finally:
        _remove(LOCK_FILE)
        _remove(CLOSE_FILE)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'overlay_toggle':
        _toggle_overlay()
    else:
        main()
