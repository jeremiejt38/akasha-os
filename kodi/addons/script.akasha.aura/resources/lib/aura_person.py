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

ACTION_MOVE_LEFT = 1
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117

PHOTO_ID = 7301
NAME_ID = 7302
ROW_TITLE_ID = 7305
FILMO_LIST_ID = 7310


def _set(window, prop, value):
    window.setProperty(prop, value or '')


class AuraPersonWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.person = {}
        self.items = []
        self.addon_path = ''

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
            count = len(self.items)
            self.getControl(ROW_TITLE_ID).setLabel(
                'Filmographie ({} titre{})'.format(
                    count, 's' if count != 1 else ''))
            _set(self, 'AuraPersonRowTitle', '1' if count else '')
            _set(self, 'AuraPersonEmpty',
                 '1' if not count else '')
            lst = self.getControl(FILMO_LIST_ID)
            lst.reset()
            for item in self.items:
                li = xbmcgui.ListItem(item.get('title') or '',
                                      str(item.get('year') or ''))
                li.setArt({'poster': item.get('poster_url')
                                   or item.get('thumb_url') or ''})
                li.setProperty('watched',
                               '1' if item.get('watched') else '0')
                lst.addItem(li)
        except RuntimeError:
            pass
        try:
            self.setFocus(self.getControl(FILMO_LIST_ID))
        except RuntimeError:
            pass

    def onClick(self, controlID):
        if controlID == FILMO_LIST_ID:
            self._open_item()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        if action.getId() == ACTION_CONTEXT_MENU:
            # Plex long-press parity: same as a plain click.
            try:
                self.onClick(self.getFocusId())
            except Exception:
                pass
            return
        if action.getId() == ACTION_MOVE_LEFT:
            try:
                if self.getFocusId() == FILMO_LIST_ID and \
                        self.getControl(FILMO_LIST_ID).getSelectedPosition() == 0:
                    self.close()
                    return
            except RuntimeError:
                pass
        super().onAction(action)

    def _open_item(self):
        try:
            pos = self.getControl(FILMO_LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self.items)):
            return
        item = self.items[pos]
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
