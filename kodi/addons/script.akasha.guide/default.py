#!/usr/bin/env python3
"""Akasha Guide — custom overlay menu opened by the controller Guide button.

A second press on Guide closes the menu. The menu supports theme switching
with the Left/Right D-pad buttons while it is open.
"""
import os
import sys
import time
import threading
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
LOCK_FILE = '/tmp/akasha-guide.lock'
CLOSE_FILE = '/tmp/akasha-guide.close'
LOCK_TTL = 10  # seconds; refreshed while the menu is open

# Kodi action ids
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


class GuideWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.items = [
            ('Accueil', 'ActivateWindow(Home)', False),
            ('Akasha Settings', 'RunAddon(script.akasha.settings)', False),
            ('Activer / desactiver overlay systeme', '__overlay__', False),
            ('Redemarrer Kodi', 'RestartApp', True),
            ('Eteindre le systeme', 'Shutdown', True),
            ('Fermer', None, False),
        ]
        self.list = None
        self.preset = 0
        self.max_preset = 2
        self._closing = False
        super().__init__(*args, **kwargs)

    def onInit(self):
        self.setProperty('AkashaGuidePreset', str(self.preset))
        try:
            self.list = self.getControl(9000)
            self.list.reset()
            for label, action, confirm in self.items:
                item = xbmcgui.ListItem(label=label)
                self.list.addItem(item)
            self.setFocus(self.list)
        except Exception as e:
            xbmc.log('Akasha Guide: list init error: {}'.format(e), xbmc.LOGERROR)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close_safe()
            return
        if aid == ACTION_MOVE_LEFT:
            self._switch_preset(-1)
            return
        if aid == ACTION_MOVE_RIGHT:
            self._switch_preset(1)
            return
        # Let up/down be handled by the list control
        super().onAction(action)

    def onClick(self, controlID):
        if controlID == 9099:
            self.close_safe()
            return
        if controlID != 9000 or self.list is None:
            return
        idx = self.list.getSelectedPosition()
        if idx < 0 or idx >= len(self.items):
            return
        label, action, confirm = self.items[idx]
        self._run_action(label, action, confirm)

    def _switch_preset(self, delta):
        self.preset = (self.preset + delta) % (self.max_preset + 1)
        self.setProperty('AkashaGuidePreset', str(self.preset))
        xbmc.log('Akasha Guide: preset switched to {}'.format(self.preset), xbmc.LOGDEBUG)
        # Make sure navigation stays in the list after controls appear/disappear
        try:
            self.setFocus(self.list)
        except Exception:
            pass

    def _run_action(self, label, action, confirm):
        if action is None:
            self.close_safe()
            return

        if action == '__overlay__':
            try:
                settings = xbmcaddon.Addon('script.akasha.settings')
                current = settings.getSetting('overlay.enabled').lower() == 'true'
                new_state = 'false' if current else 'true'
                settings.setSetting('overlay.enabled', new_state)
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
            self.close_safe()
            return

        if confirm:
            messages = {
                'RestartApp': 'Redemarrer Kodi maintenant ?',
                'Shutdown': 'Eteindre le systeme maintenant ?',
            }
            if not xbmcgui.Dialog().yesno('Akasha Guide', messages.get(action, 'Continuer ?')):
                return

        xbmc.executebuiltin(action)
        self.close_safe()

    def close_safe(self):
        if self._closing:
            return
        self._closing = True
        try:
            self.close()
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


def _is_stale(path, ttl):
    try:
        if os.path.exists(path):
            return (time.time() - os.path.getmtime(path)) > ttl
    except Exception:
        pass
    return True


def _request_close():
    _touch(CLOSE_FILE)


def _wait_close():
    try:
        return os.path.exists(CLOSE_FILE)
    except Exception:
        return False


def main():
    # If already open, signal the existing window to close and exit.
    if os.path.exists(LOCK_FILE) and not _is_stale(LOCK_FILE, LOCK_TTL):
        _request_close()
        return

    _remove(LOCK_FILE)
    _remove(CLOSE_FILE)
    _touch(LOCK_FILE)

    try:
        # Path relative to addon root; XML is under resources/skins/Default/1080i
        window = GuideWindow('Guide.xml', ADDON.getAddonInfo('path'), 'Default', '1080i')

        # Background thread refreshes the lock and listens for a close request.
        stop_event = threading.Event()

        def watcher():
            while not stop_event.is_set():
                _touch(LOCK_FILE)
                if _wait_close():
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
    main()
