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

import xbmc
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

# Left-anchored sheet (Plex's profile submenu, AuraProfileMenu.xml):
# slides in right next to the expanded sidebar, taller icon rows.
# Geometry measured on the official client (48-account-menu):
# panel x437 y34 w398, 26px vertical padding, 76px row pitch.
_LEFT_X = 437
_LEFT_Y = 34
_LEFT_W = 398
_LEFT_PAD_V = 26
_LEFT_ROW_H = 76


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
        self.left_anchor = False
        self.rail_items = []
        self.rail_props = {}
        self.rail_pick = -1
        self.focus = 0

    def _populate_rail_replica(self):
        """Clone of the parent's expanded sidebar, drawn inside this
        dialog. Kodi dims the underlying window under a modal sheet --
        the replica keeps Plex's always-readable rail look."""
        try:
            rail = self.getControl(9020)
        except RuntimeError as e:
            xbmc.log('Akasha Aura: rail replica control 9020 missing: {}'.format(e), xbmc.LOGERROR)
            return
        try:
            rail.reset()
        except (AttributeError, RuntimeError):
            pass
        for it in self.rail_items:
            li = xbmcgui.ListItem(it.get('label', ''))
            if it.get('icon'):
                li.setArt({'icon': it['icon']})
            for prop in ('is_profile', 'is_header', 'is_library'):
                if it.get(prop):
                    li.setProperty(prop, it[prop])
            rail.addItem(li)
        for key, val in self.rail_props.items():
            try:
                self.setProperty(key, val)
            except RuntimeError:
                pass

    def onInit(self):
        if self.rail_items:
            self._populate_rail_replica()
        count = len(self.entries)
        has_title = bool(self.title)
        msg_lines = (self.message.count('[CR]')
                     + self.message.count('\n') + 1
                     if self.message else 0)
        msg_h = min(msg_lines * _MSG_LINE_H + 16,
                    _MSG_MAX_H) if self.message else 0
        if self.left_anchor:
            row_h = _LEFT_ROW_H
            panel_w, panel_left = _LEFT_W, _LEFT_X
            list_h = min(count * row_h, _MAX_PANEL_H)
            panel_h = list_h + _LEFT_PAD_V * 2 + msg_h + \
                (_TITLE_H if has_title else 0)
            panel_top = _LEFT_Y
        else:
            row_h = _ROW_H
            panel_w = _PANEL_W
            panel_left = (1920 - _PANEL_W) // 2
            list_h = min(count * row_h, _MAX_PANEL_H)
            panel_h = list_h + _PAD_V * 2 + msg_h + \
                (_TITLE_H if has_title else 0)
            panel_top = max(0, (1080 - panel_h) // 2)
        list_top = panel_top + \
            (_LEFT_PAD_V if self.left_anchor else _PAD_V) + msg_h + \
            (_TITLE_H if has_title else 0)
        try:
            panel = self.getControl(PANEL_ID)
            panel.setPosition(panel_left, panel_top)
            panel.setWidth(panel_w)
            panel.setHeight(panel_h)
        except RuntimeError:
            pass
        if has_title:
            try:
                title = self.getControl(TITLE_ID)
                title.setPosition(panel_left + 40, panel_top + 18)
                title.setWidth(panel_w - 80)
                title.setHeight(40)
                title.setLabel(self.title)
            except RuntimeError:
                pass
        if self.message:
            try:
                msg = self.getControl(MESSAGE_ID)
                msg.setPosition(
                    panel_left + 40,
                    panel_top + _PAD_V +
                    (_TITLE_H if has_title else 0))
                msg.setWidth(panel_w - 80)
                msg.setHeight(msg_h - 16)
                msg.setText(self.message)
            except RuntimeError:
                pass
        try:
            lst = self.getControl(LIST_ID)
            lst.setPosition(panel_left, list_top)
            lst.setWidth(panel_w)
            lst.setHeight(list_h)
            for entry in self.entries:
                # Tuple entries carry a leading icon (profile submenu).
                if isinstance(entry, tuple):
                    li = xbmcgui.ListItem(entry[0])
                    li.setArt({'icon': entry[1]})
                else:
                    li = xbmcgui.ListItem(entry)
                lst.addItem(li)
            self.setFocus(lst)
            # Stacked sheets (Settings over the account menu, 52-back-state)
            # restore focus on the row that opened them.
            if self.focus:
                lst.selectItem(min(self.focus, len(self.entries) - 1))
        except RuntimeError:
            pass

    def onClick(self, controlID):
        if controlID == 9020:
            # Rail replica row picked: Plex keeps the rail interactive
            # under its left-anchored sheets -- hand the index back so
            # the caller can activate the real sidebar entry.
            try:
                self.rail_pick = \
                    self.getControl(9020).getSelectedPosition()
            except RuntimeError:
                self.rail_pick = -1
            self.result = -1
            self.close()
            return
        if controlID == LIST_ID:
            try:
                self.result = self.getControl(LIST_ID).getSelectedPosition()
            except RuntimeError:
                self.result = -1
            self.close()
        elif controlID == 9001:
            # Dim backdrop: click-outside-to-dismiss, like Plex sheets.
            self.result = -1
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):  # previous menu / nav back
            self.close()


def _dialog(owner, title, entries, message='', skin='AuraMenu.xml',
            left_anchor=False, keep_sidebar=False,
            rail_items=None, rail_props=None, focus=0):
    addon_path = getattr(owner, 'addon_path', None)
    if not addon_path and getattr(owner, 'addon', None) is not None:
        addon_path = owner.addon.getAddonInfo('path')
    addon_path = addon_path or ''
    dlg = AuraMenuWindow(skin, addon_path, 'Default', '1080i')
    dlg.title = title or ''
    dlg.message = message or ''
    dlg.entries = list(entries)
    dlg.result = -1
    dlg.left_anchor = left_anchor
    dlg.rail_items = rail_items or []
    dlg.rail_props = rail_props or {}
    dlg.focus = focus
    # Plex keeps the rail expanded behind its left-anchored sheets: while
    # a rail-anchored dialog is modal the sidebar list loses focus and
    # would collapse to the icon pill. AuraSheetOpen holds the expanded
    # look (labels/panel/dim) for the dialog's lifetime.
    if keep_sidebar:
        try:
            owner.setProperty('AuraSheetOpen', '1')
        except (AttributeError, RuntimeError):
            pass
    try:
        dlg.doModal()
    finally:
        if keep_sidebar:
            try:
                owner.clearProperty('AuraSheetOpen')
            except (AttributeError, RuntimeError):
                pass
    return dlg


def select(owner, title, entries):
    """Plex-styled replacement for xbmcgui.Dialog().select()."""
    return _dialog(owner, title, entries).result


def contextmenu(owner, entries, keep_sidebar=False):
    """Plex-styled replacement for xbmcgui.Dialog().contextmenu()."""
    return _dialog(owner, '', entries, keep_sidebar=keep_sidebar).result


def _sidebar_snapshot(owner, list_id=3310):
    """Serialize the owner's sidebar list so a rail-anchored sheet can
    draw an undimmed replica (labels, icons, layout props)."""
    items = []
    try:
        sidebar = owner.getControl(list_id)
        for i in range(sidebar.size()):
            li = sidebar.getListItem(i)
            items.append({
                'label': li.getLabel(),
                'icon': li.getArt('icon'),
                'is_profile': li.getProperty('is_profile'),
                'is_header': li.getProperty('is_header'),
                'is_library': li.getProperty('is_library'),
            })
    except (AttributeError, RuntimeError) as e:
        xbmc.log('Akasha Aura: sidebar snapshot failed: {}'.format(e),
                 xbmc.LOGERROR)
    props = {}
    for key in ('AuraAvatar', 'AuraUserName', 'DivertActiveLibrary'):
        try:
            props[key] = owner.getProperty(key) or ''
        except (AttributeError, RuntimeError):
            pass
    return items, props


def profilemenu(owner, entries, focus=0):
    """Plex's sidebar profile submenu: a dark sheet anchored left of the
    screen, rows carry an icon -- entries are [(label, icon_name), ...].
    Returns the dialog (caller reads .result and .rail_pick)."""
    rail_items, rail_props = _sidebar_snapshot(owner)
    return _dialog(owner, '', entries, skin='AuraProfileMenu.xml',
                   left_anchor=True, keep_sidebar=True,
                   rail_items=rail_items, rail_props=rail_props,
                   focus=focus)


def confirm(owner, title, message):
    """Plex-styled replacement for xbmcgui.Dialog().yesno(): the
    question goes in the multiline text area, Confirm/Cancel are the
    two list rows. Returns True only when Confirm is picked."""
    import i18n
    idx = _dialog(owner, title,
                  [i18n.tr(33587), i18n.tr(33564)], message=message).result
    return idx == 0


def message(owner, title, text, button=None):
    """Plex-styled replacement for xbmcgui.Dialog().ok(): long text in
    the scrolling text area, a single row dismisses (OK by default)."""
    import i18n
    _dialog(owner, title, [button or i18n.tr(33588)], message=text)
