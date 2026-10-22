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
import xml.etree.ElementTree as ET
import xbmc
import xbmcgui
import xbmcaddon

LOCK_FILE = '/tmp/akasha-guide.lock'
CLOSE_FILE = '/tmp/akasha-guide.close'
LOCK_TTL = 10  # seconds; refreshed while the menu is open
SLEEP_TIMER_STATE = '/storage/.config/akasha-os/sleep-timer.json'
SLEEP_TIMER_SCRIPT = '/storage/.kodi/scripts/akasha-sleep-timer.py'
CEC_DISABLED_FILE = '/storage/.config/akasha-os/CEC_DISABLED'
CEC_SETTINGS_FILE = '/storage/.kodi/userdata/peripheral_data/cec_CEC_Adapter.xml'
CEC_SERVICES = ('cec-tv.service', 'cec-wakeup.service', 'cec-wake-early.service')

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

OPTIONS = [
    ('Accueil', 'ActivateWindow(Home)', False),
    ('Akasha Settings', 'RunAddon(script.akasha.settings)', False),
    ('Temporisation', '__sleep_timer__', False),
    ('Options developpeurs', '__developer_options__', False),
    ('Redemarrer Akasha', 'RestartApp', True),
    ('Mise en veille', '__sleep__', True),
    ('Eteindre le systeme', 'Shutdown', True),
]

DEVELOPER_OPTIONS = [
    ('Lancer PM4K', '__launch_pm4k__', False),
    ('Extensions Kodi', '__addon_browser__', False),
    ('Activer / desactiver overlay systeme', '__overlay__', False),
    ('Mode Ambiant', 'RunScript(script.akasha.ambient)', False),
    ('Commande HDMI-CEC', '__cec_toggle__', False),
]
def _sleep_timer_state():
    try:
        with open(SLEEP_TIMER_STATE) as f:
            state = json.load(f)
        target = float(state['target'])
        pid = int(state['pid'])
        os.kill(pid, 0)
        if target <= time.time():
            return None
        return {'target': target, 'pid': pid}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _format_remaining(seconds):
    minutes = max(0, int(seconds + 59) // 60)
    hours, minutes = divmod(minutes, 60)
    return '{} h {:02d} min'.format(hours, minutes) if hours else '{} min'.format(minutes)


def _options(source=OPTIONS):
    timer = _sleep_timer_state()
    options = []
    for label, action, confirm in source:
        if action == '__sleep_timer__' and timer:
            target = time.localtime(timer['target'])
            remaining = _format_remaining(timer['target'] - time.time())
            label = 'Annuler temporisation - {:02d}:{:02d} (reste {})'.format(
                target.tm_hour, target.tm_min, remaining)
        elif action == '__cec_toggle__':
            label = 'Commande HDMI-CEC : {}'.format(
                'OFF' if os.path.exists(CEC_DISABLED_FILE) else 'ON')
        options.append((label, action, confirm))
    return options


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


def _cancel_sleep_timer(state):
    try:
        os.remove(SLEEP_TIMER_STATE)
    except OSError:
        pass
    xbmcgui.Dialog().notification(
        'Akasha Guide', 'Temporisation annulee', xbmcgui.NOTIFICATION_INFO, 2000)


def _sleep_timer():
    state = _sleep_timer_state()
    if state:
        target = time.localtime(state['target'])
        remaining = _format_remaining(state['target'] - time.time())
        if xbmcgui.Dialog().yesno(
                'Akasha Guide', 'Annuler la mise en veille prevue a {:02d}:{:02d} ?\nTemps restant : {}'.format(
                    target.tm_hour, target.tm_min, remaining)):
            _cancel_sleep_timer(state)
        return
    default = time.strftime('%H:%M', time.localtime(time.time() + 3600))
    selected = xbmcgui.Dialog().numeric(2, 'Heure de mise en veille', default)
    if not selected:
        return
    try:
        hour, minute = (int(part) for part in selected.split(':', 1))
        now = time.time()
        current = time.localtime(now)
        target = time.mktime((current.tm_year, current.tm_mon, current.tm_mday,
                              hour, minute, 0, current.tm_wday, current.tm_yday, current.tm_isdst))
        if target <= now:
            target += 86400
    except (TypeError, ValueError):
        xbmcgui.Dialog().notification(
            'Akasha Guide', 'Heure invalide', xbmcgui.NOTIFICATION_ERROR, 2000)
        return
    try:
        process = subprocess.Popen([sys.executable, SLEEP_TIMER_SCRIPT, str(target)],
                                   start_new_session=True, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        os.makedirs(os.path.dirname(SLEEP_TIMER_STATE), exist_ok=True)
        with open(SLEEP_TIMER_STATE, 'w') as f:
            json.dump({'target': target, 'pid': process.pid}, f)
        xbmcgui.Dialog().notification(
            'Akasha Guide', 'Veille a {:02d}:{:02d} - dans {}'.format(
                hour, minute, _format_remaining(target - now)), xbmcgui.NOTIFICATION_INFO, 4000)
    except Exception as e:
        xbmc.log('Akasha Guide: sleep timer launch error: {}'.format(e), xbmc.LOGERROR)


def _sleep():
    """Put the system/TV to sleep and wake on input."""
    if not xbmcgui.Dialog().yesno('Akasha Guide', 'Mettre l\'appareil et le televiseur en veille ?'):
        return
    script = '/storage/.kodi/scripts/akasha-sleep.py'
    try:
        subprocess.Popen([sys.executable, script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        xbmc.log('Akasha Guide: sleep launch error: {}'.format(e), xbmc.LOGERROR)


def _set_kodi_cec_activation(enabled):
    try:
        tree = ET.parse(CEC_SETTINGS_FILE)
        setting = tree.getroot().find("./setting[@id='activate_source']")
        if setting is None:
            return False
        setting.set('value', '1' if enabled else '0')
        tree.write(CEC_SETTINGS_FILE, encoding='UTF-8', xml_declaration=True)
        return True
    except (OSError, ET.ParseError):
        return False


def _toggle_cec():
    enabled = os.path.exists(CEC_DISABLED_FILE)
    try:
        os.makedirs(os.path.dirname(CEC_DISABLED_FILE), exist_ok=True)
        if enabled:
            os.remove(CEC_DISABLED_FILE)
            subprocess.run(['systemctl', 'enable'] + list(CEC_SERVICES),
                           timeout=10, check=False, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        else:
            with open(CEC_DISABLED_FILE, 'w') as f:
                f.write('disabled by Akasha Guide\n')
            subprocess.run(['systemctl', 'disable', '--now'] + list(CEC_SERVICES),
                           timeout=10, check=False, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        kodi_updated = _set_kodi_cec_activation(enabled)
        suffix = '' if kodi_updated else ' (reglage Kodi non modifie)'
        xbmcgui.Dialog().notification(
            'Akasha Guide', 'Commande HDMI-CEC : {}{}'.format(
                'ON' if enabled else 'OFF', suffix), xbmcgui.NOTIFICATION_INFO, 3000)
    except Exception as e:
        xbmc.log('Akasha Guide: CEC toggle error: {}'.format(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            'Akasha Guide', 'Echec du changement HDMI-CEC', xbmcgui.NOTIFICATION_ERROR, 3000)


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


def _launch_after_dialogs_close(action):
    def launch():
        xbmc.executebuiltin('Dialog.Close(all,true)')
        time.sleep(1)
        xbmc.executebuiltin(action)

    threading.Thread(target=launch).start()


def _run_builtin(action):
    if action == '__launch_pm4k__':
        _launch_after_dialogs_close('RunAddon(script.plexmod)')
        return
    if action == '__addon_browser__':
        _launch_after_dialogs_close('ActivateWindow(AddonBrowser)')
        return
    if action == '__overlay__':
        _toggle_overlay()
        return
    if action == '__sleep__':
        _sleep()
        return
    if action == '__sleep_timer__':
        _sleep_timer()
        return
    if action == '__cec_toggle__':
        _toggle_cec()
        return
    if action == '__developer_options__':
        _developer_menu()
        return
    if action == 'RestartApp':
        _restart_kodi()
        return
    if action == 'Shutdown':
        _shutdown_system()
        return
    xbmc.executebuiltin(action)


PRESET_COUNT = 3


class GuideWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.list = None
        self._closing = False
        self.preset = 0
        self.menu_options = OPTIONS
        super().__init__(*args, **kwargs)

    def onInit(self):
        try:
            self.list = self.getControl(9000)
            self.list.reset()
            for label, action, confirm in _options(self.menu_options):
                self.list.addItem(xbmcgui.ListItem(label=label))
            self.setFocus(self.list)
            self._set_preset(self.preset)
        except Exception as e:
            xbmc.log('Akasha Guide: custom window init error: {}'.format(e), xbmc.LOGERROR)

    def _set_preset(self, preset):
        self.preset = preset % PRESET_COUNT
        self.setProperty('AkashaGuidePreset', str(self.preset))

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close_safe()
            return
        if aid == ACTION_SELECT_ITEM:
            self._select_current()
            return
        if aid == ACTION_MOVE_LEFT:
            self._set_preset(self.preset - 1)
            return
        if aid == ACTION_MOVE_RIGHT:
            self._set_preset(self.preset + 1)
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
        options = _options(self.menu_options)
        if idx < 0 or idx >= len(options):
            return
        label, action, confirm = options[idx]
        self.close_safe()
        _run_builtin(action)

    def close_safe(self):
        if self._closing:
            return
        self._closing = True
        try:
            self.close()
        except Exception:
            pass


def _open_custom(menu_options=OPTIONS):
    addon = xbmcaddon.Addon('script.akasha.guide')
    path = addon.getAddonInfo('path')
    window = GuideWindow('Guide.xml', path, 'Default', '1080i')
    window.menu_options = menu_options
    return window


def _native_menu(style, menu_options=OPTIONS, title='Akasha Guide'):
    """Open a native dialog and return when closed."""
    dialog = xbmcgui.Dialog()
    options = _options(menu_options)
    labels = [opt[0] for opt in options]
    if style == 1:
        choice = dialog.select(title, labels, preselect=0)
    else:
        choice = dialog.contextmenu(labels)

    if choice < 0:
        return
    label, action, confirm = options[choice]
    _run_builtin(action)


def _guide_style():
    try:
        settings = xbmcaddon.Addon('script.akasha.settings')
        return int(settings.getSetting('guide.style') or '0')
    except Exception:
        return 0


def _developer_menu():
    style = _guide_style()
    if style != 2:
        _native_menu(style, DEVELOPER_OPTIONS, 'Options developpeurs')
        return
    window = _open_custom(DEVELOPER_OPTIONS)
    try:
        window.doModal()
    finally:
        del window


def main():
    # If a menu is already open, close it (Back) and exit.
    if _is_open():
        _send_back()
        return

    # Read chosen style from Akasha Settings
    style = _guide_style()

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
    elif len(sys.argv) > 1 and sys.argv[1] == 'launch_pm4k':
        _launch_after_dialogs_close('RunAddon(script.plexmod)')
    elif len(sys.argv) > 1 and sys.argv[1] == 'addon_browser':
        _launch_after_dialogs_close('ActivateWindow(AddonBrowser)')
    else:
        main()
