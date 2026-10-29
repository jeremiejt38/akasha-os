"""Akasha Aura -- Plex Home profile switcher ('Who's watching?').

Two dialogs mirroring the official Android TV flow:
- AuraWhoWatching.xml: centered row of round avatars, lock badge on
  PIN-protected members, a '+ Add user' ghost tile.
- AuraPinEntry.xml: four fill-in dots + 3-col numeric pad; remote digit
  keys are accepted too. PINs are 4 digits; the 4th auto-submits.

Usage:
    import aura_switch
    user = aura_switch.pick_user(owner, users)   # dict | None
    pin  = aura_switch.ask_pin(owner)            # '1234' | None
"""

import xbmc
import xbmcgui
import gui_guard

import i18n

USERS_PANEL = 9100
USERS_TITLE = 9101
PIN_PANEL = 9210
PIN_TITLE = 9201
PIN_ERROR = 9202

_TILE_W = 300
_PAD_COLS = 3


def _addon_path(owner):
    path = getattr(owner, 'addon_path', None)
    if not path and getattr(owner, 'addon', None) is not None:
        path = owner.addon.getAddonInfo('path')
    return path or ''


class AuraWhoWatchingWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.users = []
        self.pick = None

    def onInit(self):
        try:
            self.getControl(USERS_TITLE).setLabel(i18n.tr(33617))
        except RuntimeError:
            pass
        try:
            panel = self.getControl(USERS_PANEL)
            count = len(self.users)
            panel.setWidth(count * _TILE_W)
            panel.setPosition((1920 - count * _TILE_W) // 2, 266)
            for u in self.users:
                li = xbmcgui.ListItem(u.get('title') or ' ')
                li.setArt({'thumb': u.get('thumb') or 'avatar-plex.png'})
                if u.get('protected'):
                    li.setProperty('protected', '1')
                panel.addItem(li)
            self.setFocus(panel)
        except RuntimeError as e:
            xbmc.log('Akasha Aura Switch: picker populate failed: {}'
                     .format(e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID == USERS_PANEL:
            try:
                self.pick = self.users[
                    gui_guard.selpos(self, USERS_PANEL)]
            except (RuntimeError, IndexError):
                self.pick = None
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self.close()


class AuraPinWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.digits = ''
        self.pin = None
        self.error = False

    def _sync_dots(self):
        for i in range(4):
            try:
                self.setProperty('AuraPinDot{}'.format(i),
                                 '1' if i < len(self.digits) else '')
            except RuntimeError:
                pass

    def _push(self, ch):
        if self.pin is not None:
            return
        if ch == 'back':
            self.digits = self.digits[:-1]
        elif len(self.digits) < 4 and ch.isdigit():
            self.digits += ch
        self._sync_dots()
        if len(self.digits) == 4:
            self.pin = self.digits
            self.close()

    def onInit(self):
        try:
            self.getControl(PIN_TITLE).setLabel(i18n.tr(33619))
            if self.error:
                self.getControl(PIN_ERROR).setLabel(i18n.tr(33620))
        except RuntimeError:
            pass
        try:
            pad = self.getControl(PIN_PANEL)
            for key in ('1', '2', '3', '4', '5', '6', '7', '8', '9',
                        '0', 'back'):
                li = xbmcgui.ListItem('' if key == 'back' else key)
                if key == 'back':
                    li.setArt({'icon': 'icon-backspace.png'})
                pad.addItem(li)
            self.setFocus(pad)
        except RuntimeError as e:
            xbmc.log('Akasha Aura Switch: pin pad populate failed: {}'
                     .format(e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID == PIN_PANEL:
            try:
                pos = gui_guard.selpos(self, PIN_PANEL)
                key = ('1', '2', '3', '4', '5', '6', '7', '8', '9',
                       '0', 'back')[pos]
            except (RuntimeError, IndexError):
                return
            self._push(key)

    def onAction(self, action):
        aid = action.getId()
        if aid in (9, 10, 92):
            self.close()
            return
        # Remote digit keys: ACTION_NUMBER_1..9 = 58..66, 0 = 67;
        # ACTION_BACKSPACE = 110. On-screen pad stays the primary path.
        if 58 <= aid <= 66:
            self._push(str(aid - 57))
        elif aid == 67:
            self._push('0')
        elif aid == 110:
            self._push('back')


def pick_user(owner, users):
    """'Who's watching?' picker. `users` entries: {id, title, thumb,
    protected, add?}; returns the picked dict or None on Back."""
    dlg = AuraWhoWatchingWindow('AuraWhoWatching.xml', _addon_path(owner),
                                'Default', '1080i')
    dlg.users = list(users)
    dlg.doModal()
    return dlg.pick


def ask_pin(owner, error=False):
    """4-digit PIN pad; returns the PIN string, or None on Back.
    `error=True` reopens with the 'incorrect PIN' line shown."""
    dlg = AuraPinWindow('AuraPinEntry.xml', _addon_path(owner),
                        'Default', '1080i')
    dlg.error = error
    dlg.doModal()
    return dlg.pin
