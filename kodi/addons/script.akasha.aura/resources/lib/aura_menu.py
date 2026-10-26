"""Akasha Aura — Plex-style dark selection menu, shared across windows.

Replaces xbmcgui.Dialog().select()/.contextmenu() — the native light
dialogs clash with the whole dark theme. A centered dark rounded panel
with a scrollable entry list; the focused row gets Plex's light pill.

Usage:
    import aura_menu
    idx = aura_menu.select(win, title, entries)   # entries: [str]
    idx = aura_menu.contextmenu(win, entries)     # titleless
Both return the selected index or -1 on Back/dismiss.
"""

import xbmcgui

PANEL_ID = 9000
TITLE_ID = 9005
MESSAGE_ID = 9006
LIST_ID = 9010

_ROW_H = 64
_PANEL_W = 640
_PAD_V = 20
_TITLE_H = 72
_MSG_LINE_H = 34
_MSG_MAX_H = 300
_MAX_PANEL_H = 700


class AuraMenuWindow(xbmcgui.WindowXMLDialog):
    title = ''
    message = ''
    entries = []
    result = -1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = ''
        self.message = ''
        self.entries = []
        self.result = -1

    def onInit(self):
        count = len(self.entries)
        has_title = bool(self.title)
        msg_lines = (self.message.count('[CR]')
                     + self.message.count('\n') + 1
                     if self.message else 0)
        msg_h = min(msg_lines * _MSG_LINE_H + 16,
                    _MSG_MAX_H) if self.message else 0
        list_h = min(count * _ROW_H, _MAX_PANEL_H)
        panel_h = list_h + _PAD_V * 2 + msg_h + \
            (_TITLE_H if has_title else 0)
        panel_top = max(0, (1080 - panel_h) // 2)
        list_top = panel_top + _PAD_V + msg_h + \
            (_TITLE_H if has_title else 0)
        try:
            panel = self.getControl(PANEL_ID)
            panel.setPosition((1920 - _PANEL_W) // 2, panel_top)
            panel.setWidth(_PANEL_W)
            panel.setHeight(panel_h)
        except RuntimeError:
            pass
        if has_title:
            try:
                title = self.getControl(TITLE_ID)
                title.setPosition(
                    (1920 - _PANEL_W) // 2 + 40, panel_top + 18)
                title.setWidth(_PANEL_W - 80)
                title.setHeight(40)
                title.setLabel(self.title)
            except RuntimeError:
                pass
        if self.message:
            try:
                msg = self.getControl(MESSAGE_ID)
                msg.setPosition(
                    (1920 - _PANEL_W) // 2 + 40,
                    panel_top + _PAD_V +
                    (_TITLE_H if has_title else 0))
                msg.setWidth(_PANEL_W - 80)
                msg.setHeight(msg_h - 16)
                msg.setText(self.message)
            except RuntimeError:
                pass
        try:
            lst = self.getControl(LIST_ID)
            lst.setPosition((1920 - _PANEL_W) // 2, list_top)
            lst.setWidth(_PANEL_W)
            lst.setHeight(list_h)
            for entry in self.entries:
                lst.addItem(xbmcgui.ListItem(entry))
            self.setFocus(lst)
        except RuntimeError:
            pass

    def onClick(self, controlID):
        if controlID == LIST_ID:
            try:
                self.result = self.getControl(LIST_ID).getSelectedPosition()
            except RuntimeError:
                self.result = -1
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):  # previous menu / nav back
            self.close()


def _dialog(owner, title, entries, message=''):
    addon_path = getattr(owner, 'addon_path', None)
    if not addon_path and getattr(owner, 'addon', None) is not None:
        addon_path = owner.addon.getAddonInfo('path')
    addon_path = addon_path or ''
    dlg = AuraMenuWindow('AuraMenu.xml', addon_path, 'Default', '1080i')
    dlg.title = title or ''
    dlg.message = message or ''
    dlg.entries = list(entries)
    dlg.result = -1
    dlg.doModal()
    return dlg.result


def select(owner, title, entries):
    """Plex-styled replacement for xbmcgui.Dialog().select()."""
    return _dialog(owner, title, entries)


def contextmenu(owner, entries):
    """Plex-styled replacement for xbmcgui.Dialog().contextmenu()."""
    return _dialog(owner, '', entries)


def confirm(owner, title, message):
    """Plex-styled replacement for xbmcgui.Dialog().yesno(): the
    question goes in the multiline text area, Confirm/Cancel are the
    two list rows. Returns True only when Confirm is picked."""
    import i18n
    idx = _dialog(owner, title,
                  [i18n.tr(33587), i18n.tr(33564)], message=message)
    return idx == 0


def message(owner, title, text):
    """Plex-styled replacement for xbmcgui.Dialog().ok(): long text in
    the scrolling text area, a single OK row dismisses."""
    import i18n
    _dialog(owner, title, [i18n.tr(33588)], message=text)
