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
import plex_client

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

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
        # Optional: set by a caller (e.g. AuraGenresWindow) before doModal()
        # to open the library pre-scoped to a specific section/genre instead
        # of auto-detecting the first movie section.
        self.initial_section = None
        self.initial_genre = None

    def onInit(self):
        try:
            if self.initial_section:
                self.section = self.initial_section
                self.filter_genre = self.initial_genre
                self._load_items()
                return

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
        if self.connector:
            try:
                raw = self.connector.section_items(self.section['key'], **kwargs)
                return divert_source.parse_metadata_list(raw, self.connector.image_url)
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Library: connector section_items failed, falling back '
                         'to Plex direct: {}'.format(e), xbmc.LOGWARNING)
                self.connector = None
        return self.client.section_items(self.section['key'], **kwargs)

    def _section_genres(self):
        if self.connector:
            try:
                return divert_source.parse_genres(self.connector.section_genres(self.section['key']))
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Library: connector genres failed, falling back to Plex '
                         'direct: {}'.format(e), xbmc.LOGWARNING)
                self.connector = None
        return self.client.section_genres(self.section['key'])

    def _load_items(self):
        if self.query:
            if self.connector:
                self.items = self._section_items(search=self.query)
            else:
                self.items = self.client.search(self.section['key'], self.query)
        elif self.filter_genre:
            if self.connector:
                self.items = self._section_items(genre=self.filter_genre, limit=200)
            else:
                self.items = self.client.by_genre(self.section['key'], self.filter_genre, limit=200)
        else:
            self.items = self._section_items(sort=self.sort)
        self._render()

    def _render(self):
        try:
            header = self.getControl(4000)
            header.setLabel('Bibliotheque — {}'.format(self.section['title']))
        except RuntimeError:
            pass

        try:
            status = self.getControl(4020)
            label = '{} resultat(s)'.format(len(self.items))
            if self.query:
                label += ' pour "{}"'.format(self.query)
            if self.filter_genre:
                label += ' (' + self.filter_genre + ')'
            status.setLabel(label)
        except RuntimeError:
            pass

        try:
            lst = self.getControl(4010)
            lst.reset()
            for item in self.items:
                li = xbmcgui.ListItem(item['title'])
                lst.addItem(li)
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
