"""Akasha Aura — Plex-style person page (AuraPerson.xml).

Opened modally from the detail page's Cast & Crew row: a large circular
photo, the person's name, and their server-side filmography as a poster
row (PlexClient.person_filmography — every item tagged with the person's
filter across the video sections, newest first). Picking a card opens
that item's detail page on top of this dialog.

Caller sets before doModal():
- `client`     — PlexClient (None disables filmography loading)
- `person`     — {'name', 'thumb_url', 'role'} from the cast entry
- `items`      — pre-fetched filmography (normalised video dicts)
- `addon_path` — script.akasha.aura install dir (for sub-windows)
"""
import xbmc
import xbmcgui
import gui_guard
import i18n

ACTION_MOVE_LEFT = 1
ACTION_MOVE_DOWN = 4
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117

PHOTO_ID = 7301
NAME_ID = 7302
ROW_TITLE_ID = 7305
ROW_TITLE2_ID = 7306
FILMO_LIST_ID = 7310
FILMO_LIST2_ID = 7311


def _set(window, prop, value):
    window.setProperty(prop, value or '')


class AuraPersonWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.person = {}
        self.items = []
        self.addon_path = ''
        self._rows = {}

    def onInit(self):
        try:
            self._render()
        except Exception as e:
            xbmc.log('Akasha Aura Person: init error: {}'.format(e),
                     xbmc.LOGERROR)

    def _render(self):
        try:
            self.getControl(PHOTO_ID).setImage(
                self.person.get('thumb_url') or 'actor-fallback.png',
                useCache=False)
        except RuntimeError:
            pass
        try:
            self.getControl(NAME_ID).setLabel(self.person.get('name') or '')
        except RuntimeError:
            pass
        try:
            if getattr(self, 'row_title', None):
                # 'More Like This' keeps Plex's single mixed row.
                groups = [(self.row_title, self.items)]
            else:
                # Plex groups a person's filmography by media type.
                movies = [i for i in self.items
                          if i.get('type') != 'show']
                shows = [i for i in self.items
                         if i.get('type') == 'show']
                groups = []
                if movies:
                    groups.append((i18n.tr(33051), movies))
                if shows:
                    groups.append((i18n.tr(33050), shows))
            groups = [g for g in groups if g[1]]
            self._rows = {}
            slots = ((ROW_TITLE_ID, FILMO_LIST_ID),
                     (ROW_TITLE2_ID, FILMO_LIST2_ID))
            for (title_id, list_id), (title, items) in zip(
                    slots, groups):
                self._rows[list_id] = items
                try:
                    self.getControl(title_id).setLabel(title)
                except RuntimeError:
                    pass
                try:
                    lst = self.getControl(list_id)
                    lst.reset()
                    for item in items:
                        li = xbmcgui.ListItem(item.get('title') or '',
                                              str(item.get('year') or ''))
                        li.setArt({'poster': item.get('poster_url')
                                           or item.get('thumb_url') or ''})
                        li.setProperty(
                            'watched',
                            '1' if item.get('watched') else '0')
                        lst.addItem(li)
                except RuntimeError:
                    pass
            _set(self, 'AuraPersonRowTitle', '1' if groups else '')
            _set(self, 'AuraPersonRow2', '1' if len(groups) > 1 else '')
            _set(self, 'AuraPersonEmpty', '1' if not groups else '')
        except RuntimeError:
            pass
        gui_guard.focus(self,
                        FILMO_LIST_ID if FILMO_LIST_ID in self._rows
                        else FILMO_LIST2_ID)

    def onClick(self, controlID):
        if controlID in (FILMO_LIST_ID, FILMO_LIST2_ID):
            self._open_item()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        if action.getId() == ACTION_CONTEXT_MENU:
            # Plex long-press: filmography cards open the option
            # sheet, anything else keeps long-press == click parity.
            try:
                if self.getFocusId() in (FILMO_LIST_ID, FILMO_LIST2_ID):
                    self._filmography_sheet()
                    return
                self.onClick(self.getFocusId())
            except Exception:
                pass
            return
        if action.getId() == ACTION_MOVE_LEFT:
            try:
                focused = self.getFocusId()
                if focused in (FILMO_LIST_ID, FILMO_LIST2_ID) and \
                        gui_guard.selpos(self, focused) == 0:
                    self.close()
                    return
            except RuntimeError:
                pass
        if action.getId() == ACTION_MOVE_DOWN:
            try:
                # Without a second row the XML <ondown> still fires;
                # swallow it so the focus can't land on a hidden list.
                if self.getFocusId() == FILMO_LIST_ID and \
                        FILMO_LIST2_ID not in self._rows:
                    return
            except RuntimeError:
                pass
        super().onAction(action)

    def _filmography_sheet(self):
        try:
            lid = self.getFocusId()
            pos = gui_guard.selpos(self, lid)
        except RuntimeError:
            return
        items = self._rows.get(lid, [])
        if not (0 <= pos < len(items)):
            return
        import context_sheet
        context_sheet.open_sheet(
            self, self.client, items[pos], lid,
            self._open_item,
            on_removed=lambda p: items.pop(p)
            if p < len(items) else None)

    def _open_item(self):
        try:
            lid = self.getFocusId()
            pos = gui_guard.selpos(self, lid)
        except RuntimeError:
            return
        items = self._rows.get(lid, [])
        if not (0 <= pos < len(items)):
            return
        item = items[pos]
        # Hydrate like the reco rows do: hub/section items only carry
        # card-level fields, the detail page needs the full metadata.
        if self.client and item.get('rating_key'):
            try:
                item = self.client.metadata_item(item['rating_key']) or item
            except Exception:
                pass
        # Local import: aura_detail opens this window from its cast row.
        import aura_detail
        detail = aura_detail.AuraDetailWindow(
            'AuraDetail.xml', self.addon_path, 'Default', '1080i')
        detail.client = self.client
        detail.item = item
        detail.mode = 'show' if item.get('type') == 'show' else 'item'
        detail.doModal()
        # The detail page may have started playback: bubble it up so
        # our own callers can close the whole stack like Plex does.
        if getattr(detail, 'playback_started', False):
            self.playback_started = True
            self._playback_item = getattr(detail, '_playback_item', None)
            self.close()
