"""Akasha Aura — library full-list view (search, sort, genre filter).

Milestone 3 (see docs/aura/roadmap.md): a separate WindowXML dialog that
lists every item of the first movie section, with search, sort and genre
filter controls.
"""
import xbmc
import xbmcaddon
import xbmcgui

import connector_client
import divert_source
import local_cache
import paged_list
import plex_client

ACTION_MOVE_RIGHT = 2
ACTION_MOVE_DOWN = 4
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

CACHE_TTL_SECONDS = 300

SORT_OPTIONS = [
    ('titleSort', 'Titre'),
    ('originallyAvailableAt:desc', 'Date de sortie'),
    ('addedAt:desc', 'Date d\'ajout'),
    ('rating:desc', 'Note'),
]


class AuraLibraryWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        addon = xbmcaddon.Addon('script.akasha.aura')
        self.server_url = addon.getSetting('plex.server_url')
        self.token = addon.getSetting('plex.token')
        self.client = plex_client.PlexClient(self.server_url, self.token)
        self.connector = None
        connector_url = addon.getSetting('connector.server_url')
        connector_token = addon.getSetting('connector.session_token')
        if connector_url and connector_token:
            self.connector = connector_client.ConnectorClient(connector_url, timeout=15)
            self.connector.token = connector_token
        self.section = None
        self.items = []
        self.sort = SORT_OPTIONS[0][0]
        self.filter_genre = None
        self.query = ''
        self._paged = None
        self._cache = local_cache.open_addon_cache(addon)
        # Optional: set by a caller (e.g. AuraGenresWindow) before doModal()
        # to open the library pre-scoped to a specific section/genre instead
        # of auto-detecting the first movie section.
        self.initial_section = None
        self.initial_genre = None

    def onInit(self):
        try:
            # This window instance is reused across opens (see the note in
            # aura_window.py about why), so search/genre/sort state from a
            # previous visit must never leak into the next one -- otherwise
            # reopening "Bibliotheque" after a search would silently keep
            # showing those stale search results instead of the full list.
            self.query = ''

            if self.initial_section:
                self.section = self.initial_section
                self.filter_genre = self.initial_genre
                self._load_items()
                return

            self.filter_genre = None
            self.sort = SORT_OPTIONS[0][0]
            sections = self._video_sections()
            for s in sections:
                if s['type'] == 'movie':
                    self.section = s
                    break
            if not self.section:
                xbmc.log('Akasha Aura Library: no movie section found', xbmc.LOGERROR)
                self.close()
                return
            self._load_items()
        except Exception as e:
            xbmc.log('Akasha Aura Library: init error: {}'.format(e), xbmc.LOGERROR)

    def _video_sections(self):
        if self.connector:
            try:
                return divert_source.parse_sections(self.connector.sections())
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Library: connector sections failed, falling back to '
                         'Plex direct: {}'.format(e), xbmc.LOGWARNING)
                self.connector = None
        return self.client.video_sections()

    def _section_items(self, **kwargs):
        """Return (items, total) for the current section/filters.

        `total` is the real total item count from the source's own
        pagination metadata (Plex `totalSize`), shown immediately instead of
        only "however many are loaded so far" -- see plan a3f9c2e1 in
        docs/aura/decisions.md.
        """
        if self.connector:
            try:
                raw = self.connector.section_items(self.section['key'], **kwargs)
                items = divert_source.parse_metadata_list(raw, self.connector.image_url)
                return items, divert_source.parse_total_size(raw)
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Library: connector section_items failed, falling back '
                         'to Plex direct: {}'.format(e), xbmc.LOGWARNING)
                self.connector = None
        # Direct Plex fallback: search/genre use their own dedicated endpoints.
        genre = kwargs.pop('genre', None)
        search = kwargs.pop('search', None)
        if search:
            return self.client.search_with_total(self.section['key'], search, **kwargs)
        if genre:
            return self.client.by_genre_with_total(self.section['key'], genre, **kwargs)
        return self.client.section_items_with_total(self.section['key'], **kwargs)

    def _section_genres(self):
        if self.connector:
            try:
                return divert_source.parse_genres(self.connector.section_genres(self.section['key']))
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Library: connector genres failed, falling back to Plex '
                         'direct: {}'.format(e), xbmc.LOGWARNING)
                self.connector = None
        return self.client.section_genres(self.section['key'])

    def _current_mode_key(self):
        if self.query:
            return ('search', self.query)
        if self.filter_genre:
            return ('genre', self.filter_genre)
        return ('sort', self.sort)

    def _fetch_page(self, offset, limit):
        mode, value = self._current_mode_key()
        cache_key = local_cache.page_cache_key(
            'library', self.section['key'], mode, value, offset, limit)
        return local_cache.get_or_set_page(
            self._cache, cache_key, CACHE_TTL_SECONDS,
            lambda: self._fetch_page_uncached(mode, value, offset, limit))

    def _fetch_page_uncached(self, mode, value, offset, limit):
        kwargs = {'offset': offset, 'limit': limit, mode: value}
        return self._section_items(**kwargs)

    def _load_items(self):
        self._paged = paged_list.PagedList(self._fetch_page)
        error = None
        try:
            self._paged.load_initial()
        except Exception as e:
            xbmc.log('Akasha Aura Library: items load failed: {}'.format(e), xbmc.LOGERROR)
            error = e
        self.items = self._paged.items
        self._render(error)

    def _maybe_load_more(self):
        if not self._paged:
            return
        try:
            position = self.getControl(4010).getSelectedPosition()
        except RuntimeError:
            return
        try:
            new_items = self._paged.maybe_load_more(position)
        except Exception as e:
            xbmc.log('Akasha Aura Library: pagination fetch failed: {}'.format(e), xbmc.LOGWARNING)
            return
        if not new_items:
            return
        self.items = self._paged.items
        try:
            lst = self.getControl(4010)
            lst.addItems([_build_list_item(item) for item in new_items])
        except Exception as e:
            xbmc.log('Akasha Aura Library: append render error: {}'.format(e), xbmc.LOGERROR)
        self._render_status()

    def _render_status(self):
        try:
            status = self.getControl(4020)
            count = self._paged.total if self._paged and self._paged.total is not None \
                else len(self.items)
            label = '{} resultat(s)'.format(count)
            if self.query:
                label += ' pour "{}"'.format(self.query)
            if self.filter_genre:
                label += ' (' + self.filter_genre + ')'
            status.setLabel(label)
        except RuntimeError:
            pass

    def _render(self, error=None):
        try:
            header = self.getControl(4000)
            header.setLabel('Bibliotheque — {}'.format(self.section['title']))
        except RuntimeError:
            pass

        if error:
            try:
                self.getControl(4020).setLabel('Erreur de chargement')
            except RuntimeError:
                pass
            return
        self._render_status()

        try:
            lst = self.getControl(4010)
            lst.reset()
            for item in self.items:
                lst.addItem(_build_list_item(item))
            if self.items:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura Library: render error: {}'.format(e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID == 4001:
            kb = xbmc.Keyboard(self.query, 'Rechercher')
            kb.doModal()
            if kb.isConfirmed():
                self.query = kb.getText()
                self.filter_genre = None
                self._load_items()

        elif controlID == 4002:
            idx = xbmcgui.Dialog().select(
                'Trier par',
                [label for _, label in SORT_OPTIONS],
            )
            if idx >= 0:
                self.sort = SORT_OPTIONS[idx][0]
                self._load_items()

        elif controlID == 4003:
            try:
                genres = self._section_genres()
            except Exception as e:
                xbmc.log('Akasha Aura Library: genre load failed: {}'.format(e), xbmc.LOGERROR)
                genres = []
            if not genres:
                return
            idx = xbmcgui.Dialog().select('Genre', ['Tous'] + genres)
            if idx == 0:
                self.filter_genre = None
            elif idx > 0:
                self.filter_genre = genres[idx - 1]
                self.query = ''
            self._load_items()

        elif controlID == 4010:
            pos = self.getControl(4010).getSelectedPosition()
            if 0 <= pos < len(self.items):
                xbmc.log('Akasha Aura Library: selected {}'.format(self.items[pos]['title']), xbmc.LOGINFO)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)
        # 4010 is a wrapping grid (panel): reaching the loaded end can happen
        # by moving down a row or right along the last row, so check both.
        if aid in (ACTION_MOVE_DOWN, ACTION_MOVE_RIGHT) and self.getFocusId() == 4010:
            self._maybe_load_more()


def _build_list_item(item):
    li = xbmcgui.ListItem(item['title'], divert_source.item_subtitle(item))
    if item.get('thumb_url'):
        li.setArt({'thumb': item['thumb_url']})
    return li
