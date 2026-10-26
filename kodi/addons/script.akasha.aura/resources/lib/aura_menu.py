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
LIST_ID = 9010

_ROW_H = 64
_PANEL_W = 640
_PAD_V = 20
_TITLE_H = 72
_MAX_PANEL_H = 700


class AuraMenuWindow(xbmcgui.WindowXMLDialog):
    title = ''
    entries = []
    result = -1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = ''
        self.entries = []
        self.result = -1

    def onInit(self):
        count = len(self.entries)
        has_title = bool(self.title)
        list_h = min(count * _ROW_H, _MAX_PANEL_H)
        panel_h = list_h + _PAD_V * 2 + (_TITLE_H if has_title else 0)
        panel_top = max(0, (1080 - panel_h) // 2)
        list_top = panel_top + _PAD_V + (_TITLE_H if has_title else 0)
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


def _dialog(owner, title, entries):
    addon_path = getattr(owner, 'addon_path', None)
    if not addon_path and getattr(owner, 'addon', None) is not None:
        addon_path = owner.addon.getAddonInfo('path')
    addon_path = addon_path or ''
    dlg = AuraMenuWindow('AuraMenu.xml', addon_path, 'Default', '1080i')
    dlg.title = title or ''
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
